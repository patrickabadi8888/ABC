package Services;

import java.io.File;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import Enums.ApplicationStatus;
import Enums.FlatType;
import Models.BTOApplication;
import Models.Enquiry;
import Models.FlatTypeDetails;
import Models.Project;
import Parsers.Dparse;
import Utils.DateUtils;

public class ApplicationService {
    private static final String DATA_DIR = "data";
    private static final String APPLICATION_FILE = DATA_DIR + File.separator + "applications.csv";
    private static final String[] APPLICATION_HEADER = {"ApplicationID", "ApplicantNRIC", "ProjectName", "FlatTypeApplied", "Status", "ApplicationDate"};
    private static final String DELIMITER = ",";
    private static final String ENQUIRY_FILE = DATA_DIR + File.separator + "enquiries.csv";
    private static final String[] ENQUIRY_HEADER = {"EnquiryID", "ApplicantNRIC", "ProjectName", "EnquiryText", "ReplyText", "RepliedByNRIC", "EnquiryDate", "ReplyDate"};
    public static Map<String, BTOApplication> loadApplications(List<Project> projects) {
        Map<String, BTOApplication> applications = new HashMap<>();
        Map<Project, Map<FlatType, Integer>> bookedCounts = new HashMap<>();

        CsvRW.readCsv(APPLICATION_FILE, APPLICATION_HEADER.length).forEach(data -> {
            try {
                String appId = data[0].trim();
                if (appId.isEmpty() || applications.containsKey(appId)) {
                     if (!appId.isEmpty()) System.err.println("Skipping duplicate application ID: " + appId);
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
                 if (flatType == null && (status == ApplicationStatus.BOOKED || status == ApplicationStatus.SUCCESSFUL || status == ApplicationStatus.PENDING_WITHDRAWAL)) {
                     System.err.println("Warning: Application " + appId + " is " + status + " but has invalid/missing flat type '" + data[3] + "'. Status might be inconsistent.");
                 }
                 if (status == ApplicationStatus.PENDING_WITHDRAWAL) {
                      System.out.println("Info: Application " + appId + " loaded with PENDING_WITHDRAWAL status.");
                 }


                BTOApplication application = new BTOApplication(appId, applicantNric, projectName, flatType, status, appDate);
                applications.put(application.getApplicationId(), application);

                if (status == ApplicationStatus.BOOKED && flatType != null) {
                    Project project = projects.stream()
                                            .filter(p -> p.getProjectName().equalsIgnoreCase(projectName))
                                            .findFirst().orElse(null);
                    if (project != null) {
                        bookedCounts.computeIfAbsent(project, ProjKey -> new HashMap<>())
                                    .merge(flatType, 1, Integer::sum);
                    } else {
                         System.err.println("Warning: Booked application " + appId + " refers to non-existent project '" + projectName + "'. Unit count cannot be adjusted.");
                    }
                }

            } catch (IllegalArgumentException e) {
                 System.err.println("Error parsing enum/data in application data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            } catch (Exception e) {
                System.err.println("Error parsing application data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });

        bookedCounts.forEach((project, typeCounts) -> {
            typeCounts.forEach((type, count) -> {
                FlatTypeDetails details = project.getMutableFlatTypeDetails(type);
                if (details != null) {
                    int initialAvailable = details.getTotalUnits();
                    int finalAvailable = Math.max(0, initialAvailable - count);
                    if (finalAvailable != details.getAvailableUnits()) {
                         details.setAvailableUnits(finalAvailable);
                    }
                     if (count > details.getTotalUnits()) {
                         System.err.println("Error: More flats booked (" + count + ") than total units (" + details.getTotalUnits() + ") for " + project.getProjectName() + "/" + type.getDisplayName() + ". Available units set to 0.");
                     }
                } else {
                     System.err.println("Warning: Trying to adjust units for non-existent flat type " + type.getDisplayName() + " in project " + project.getProjectName());
                }
            });
        });


        System.out.println("Loaded " + applications.size() + " applications.");
        return applications;
    }

    public static void saveApplications(Map<String, BTOApplication> applications) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(APPLICATION_HEADER);
        applications.values().stream()
            .sorted(Comparator.comparing(BTOApplication::getApplicationId))
            .forEach(app -> {
                dataList.add(new String[]{
                    app.getApplicationId(),
                    app.getApplicantNric(),
                    app.getProjectName(),
                    app.getFlatTypeApplied() == null ? "" : app.getFlatTypeApplied().name(),
                    app.getStatus().name(),
                    DateUtils.formatDate(app.getApplicationDate())
                });
            });
        CsvRW.writeCsv(APPLICATION_FILE, dataList);
        System.out.println("Saved applications.");
    }

    public static void saveEnquiries(List<Enquiry> enquiries) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(ENQUIRY_HEADER);
        enquiries.stream()
            .sorted(Comparator.comparing(Enquiry::getEnquiryId))
            .forEach(enq -> {
                dataList.add(new String[]{
                    enq.getEnquiryId(),
                    enq.getApplicantNric(),
                    enq.getProjectName(),
                    enq.getEnquiryText(),
                    enq.getReplyText() == null ? "" : enq.getReplyText(),
                    enq.getRepliedByNric() == null ? "" : enq.getRepliedByNric(),
                    DateUtils.formatDate(enq.getEnquiryDate()),
                    DateUtils.formatDate(enq.getReplyDate())
                });
            });
        CsvRW.writeCsv(ENQUIRY_FILE, dataList);
        System.out.println("Saved enquiries.");
    }
}
