package Services;

import java.io.File;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import Enums.ApplicationStatus;
import Enums.FlatType;
import Models.BTOApplication;
import Models.FlatTypeDetails;
import Models.Project;
import Parsers.Dparse;
import Utils.DateUtils;

public class ApplicationService implements IApplicationService {
    private static final String DATA_DIR = "data";
    private static final String APPLICATION_FILE = DATA_DIR + File.separator + "applications.csv";
    private static final String[] APPLICATION_HEADER = { "ApplicationID", "ApplicantNRIC", "ProjectName",
            "FlatTypeApplied", "Status", "ApplicationDate" };
    private static final String DELIMITER = ",";

    private Map<String, BTOApplication> applications;

    public ApplicationService() {
        this.applications = new HashMap<>();
    }

    @Override
    public Map<String, BTOApplication> loadApplications(List<Project> projects) {
        this.applications.clear(); // Clear before loading
        Map<Project, Map<FlatType, Integer>> bookedCounts = new HashMap<>();

        CsvRW.readCsv(APPLICATION_FILE, APPLICATION_HEADER.length).forEach(data -> {
            try {
                String appId = data[0].trim();
                if (appId.isEmpty() || this.applications.containsKey(appId)) {
                    if (!appId.isEmpty())
                        System.err.println("Skipping duplicate application ID: " + appId);
                    return;
                }
                String applicantNric = data[1].trim();
                String projectName = data[2].trim();
                FlatType flatType = FlatType.fromString(data[3].trim());
                ApplicationStatus status = ApplicationStatus.valueOf(data[4].trim().toUpperCase());
                Date appDate = Dparse.parseDate(data[5].trim());

                if (appDate == null) {
                    System.err.println("Skipping application with invalid date: " + appId);
                    return;
                }
                if (flatType == null && (status == ApplicationStatus.BOOKED || status == ApplicationStatus.SUCCESSFUL
                        || status == ApplicationStatus.PENDING_WITHDRAWAL)) {
                    System.err.println("Warning: Application " + appId + " is " + status
                            + " but has invalid/missing flat type '" + data[3] + "'. Status might be inconsistent.");
                }
                if (status == ApplicationStatus.PENDING_WITHDRAWAL) {
                     // We can load it, but original status isn't stored persistently in this design
                     // The BTOApplication constructor warns about this.
                }

                BTOApplication application = new BTOApplication(appId, applicantNric, projectName, flatType, status,
                        appDate);
                this.applications.put(application.getApplicationId(), application);

                // Track booked counts to adjust project units later
                if (status == ApplicationStatus.BOOKED && flatType != null) {
                    Project project = projects.stream()
                            .filter(p -> p.getProjectName().equalsIgnoreCase(projectName))
                            .findFirst().orElse(null);
                    if (project != null) {
                        bookedCounts.computeIfAbsent(project, _ -> new HashMap<>())
                                .merge(flatType, 1, (a, b) -> a + b);
                    } else {
                        System.err.println("Warning: Booked application " + appId + " refers to non-existent project '"
                                + projectName + "'. Unit count cannot be adjusted.");
                    }
                }

            } catch (IllegalArgumentException e) {
                System.err.println("Error parsing enum/data in application data: " + String.join(DELIMITER, data)
                        + " - " + e.getMessage());
            } catch (Exception e) {
                System.err.println("Error parsing application data line: " + String.join(DELIMITER, data) + " - "
                        + e.getMessage());
            }
        });

        // Adjust available units in Project objects based on loaded booked applications
        bookedCounts.forEach((project, typeCounts) -> {
            typeCounts.forEach((type, count) -> {
                FlatTypeDetails details = project.getMutableFlatTypeDetails(type); // Use mutable getter
                if (details != null) {
                    int initialAvailable = details.getTotalUnits(); // Assume file loads total, derive available
                    int finalAvailable = Math.max(0, initialAvailable - count);
                    details.setAvailableUnits(finalAvailable); // Update the project object directly
                    if (count > details.getTotalUnits()) {
                        System.err.println("Error: More flats booked (" + count + ") than total units ("
                                + details.getTotalUnits() + ") for " + project.getProjectName() + "/"
                                + type.getDisplayName() + ". Available units set to 0.");
                    }
                } else {
                    System.err.println("Warning: Trying to adjust units for non-existent flat type "
                            + type.getDisplayName() + " in project " + project.getProjectName());
                }
            });
        });

        System.out.println("Loaded " + this.applications.size() + " applications.");
        return new HashMap<>(this.applications); // Return a copy
    }

    @Override
    public void saveApplications(Map<String, BTOApplication> applicationsToSave) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(APPLICATION_HEADER);
        applicationsToSave.values().stream()
                .sorted(Comparator.comparing((BTOApplication app) -> app.getApplicationId()))
                .forEach(app -> {
                    dataList.add(new String[] {
                            app.getApplicationId(),
                            app.getApplicantNric(),
                            app.getProjectName(),
                            app.getFlatTypeApplied() == null ? "" : app.getFlatTypeApplied().name(), // Use name() for consistency
                            app.getStatus().name(),
                            DateUtils.formatDate(app.getApplicationDate())
                    });
                });
        CsvRW.writeCsv(APPLICATION_FILE, dataList);
        System.out.println("Saved applications.");
        this.applications = new HashMap<>(applicationsToSave); // Update internal map
    }

     @Override
     public BTOApplication findApplicationById(String applicationId) {
         return this.applications.get(applicationId);
     }

     @Override
     public BTOApplication findApplicationByApplicantAndProject(String nric, String projectName) {
         if (nric == null || projectName == null) return null;
         String appId = nric + "_" + projectName;
         return findApplicationById(appId);
     }

     @Override
     public List<BTOApplication> getApplicationsByProject(String projectName) {
         if (projectName == null) return new ArrayList<>();
         return this.applications.values().stream()
             .filter(app -> projectName.equals(app.getProjectName()))
             .collect(Collectors.toList());
     }

     @Override
     public List<BTOApplication> getApplicationsByStatus(ApplicationStatus status) {
          if (status == null) return new ArrayList<>();
          return this.applications.values().stream()
              .filter(app -> status.equals(app.getStatus()))
              .collect(Collectors.toList());
     }

    @Override
     public List<BTOApplication> getApplicationsByApplicant(String nric) {
         if (nric == null) return new ArrayList<>();
         return this.applications.values().stream()
             .filter(app -> nric.equals(app.getApplicantNric()))
             .collect(Collectors.toList());
     }

     @Override
     public void addApplication(BTOApplication application) {
         if (application != null && !this.applications.containsKey(application.getApplicationId())) {
             this.applications.put(application.getApplicationId(), application);
         } else if (application != null) {
             System.err.println("Application with ID " + application.getApplicationId() + " already exists.");
         }
     }

     @Override
     public boolean removeApplication(String applicationId) {
         if (applicationId != null) {
             return this.applications.remove(applicationId) != null;
         }
         return false;
     }

     @Override
     public Map<String, BTOApplication> getAllApplications() {
         return new HashMap<>(this.applications); // Return copy
     }
}
