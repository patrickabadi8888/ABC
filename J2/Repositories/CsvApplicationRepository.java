package Repositories;

import java.io.File;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import Enums.ApplicationStatus;
import Enums.FlatType;
import Interfaces.Repositories.IApplicationRepository;
import Models.BTOApplication;
import Parsers.Dparse;
import Services.CsvRW; // Assuming CsvRW is in Services package
import Utils.DateUtils;

public class CsvApplicationRepository implements IApplicationRepository {
    private static final String DATA_DIR = "data";
    private static final String APPLICATION_FILE = DATA_DIR + File.separator + "applications.csv";
    private static final String[] APPLICATION_HEADER = { "ApplicationID", "ApplicantNRIC", "ProjectName",
            "FlatTypeApplied", "Status", "ApplicationDate" };
    private static final String DELIMITER = ",";

    private Map<String, BTOApplication> applicationsCache; // Cache loaded data

    public CsvApplicationRepository() {
        this.applicationsCache = null; // Load on demand
    }

    @Override
    public Map<String, BTOApplication> loadApplications() {
        if (this.applicationsCache != null) {
            return new HashMap<>(this.applicationsCache); // Return copy
        }

        Map<String, BTOApplication> loadedApplications = new HashMap<>();
        List<String[]> rawData = CsvRW.readCsv(APPLICATION_FILE, APPLICATION_HEADER.length);

        for (String[] data : rawData) {
            try {
                String appId = data[0].trim();
                if (appId.isEmpty() || loadedApplications.containsKey(appId)) {
                    if (!appId.isEmpty())
                        System.err.println("Skipping duplicate application ID in CSV: " + appId);
                    continue;
                }
                String applicantNric = data[1].trim();
                String projectName = data[2].trim();
                FlatType flatType = FlatType.fromString(data[3].trim());
                ApplicationStatus status = ApplicationStatus.valueOf(data[4].trim().toUpperCase());
                Date appDate = Dparse.parseDate(data[5].trim());

                if (appDate == null) {
                    System.err.println("Skipping application with invalid date: " + appId);
                    continue;
                }
                if (flatType == null && (status == ApplicationStatus.BOOKED || status == ApplicationStatus.SUCCESSFUL
                        || status == ApplicationStatus.PENDING_WITHDRAWAL)) {
                    System.err.println("Warning: Application " + appId + " is " + status
                            + " but has invalid/missing flat type '" + data[3] + "'. Status might be inconsistent.");
                }
                if (status == ApplicationStatus.PENDING_WITHDRAWAL) {
                     // Handled in BTOApplication constructor now
                    // System.out.println("Info: Application " + appId + " loaded with PENDING_WITHDRAWAL status.");
                }

                BTOApplication application = new BTOApplication(appId, applicantNric, projectName, flatType, status,
                        appDate);
                loadedApplications.put(application.getApplicationId(), application);

            } catch (IllegalArgumentException e) {
                System.err.println("Error parsing enum/data in application data: " + String.join(DELIMITER, data)
                        + " - " + e.getMessage());
            } catch (Exception e) {
                System.err.println("Error parsing application data line: " + String.join(DELIMITER, data) + " - "
                        + e.getMessage());
            }
        }
        this.applicationsCache = loadedApplications;
        System.out.println("Loaded " + this.applicationsCache.size() + " applications from CSV.");
        return new HashMap<>(this.applicationsCache); // Return copy
    }

    @Override
    public void saveApplications(Map<String, BTOApplication> applicationsToSave) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(APPLICATION_HEADER);
        applicationsToSave.values().stream()
                .sorted(Comparator.comparing(BTOApplication::getApplicationId))
                .forEach(app -> {
                    dataList.add(new String[] {
                            app.getApplicationId(),
                            app.getApplicantNric(),
                            app.getProjectName(),
                            app.getFlatTypeApplied() == null ? "" : app.getFlatTypeApplied().name(), // Use name() for saving consistency
                            app.getStatus().name(),
                            DateUtils.formatDate(app.getApplicationDate())
                    });
                });
        CsvRW.writeCsv(APPLICATION_FILE, dataList);
        this.applicationsCache = new HashMap<>(applicationsToSave); // Update cache
        System.out.println("Saved " + applicationsToSave.size() + " applications to CSV.");
    }

     @Override
     public Map<String, BTOApplication> getAllApplications() {
         if (this.applicationsCache == null) {
             loadApplications();
         }
         // Return a defensive copy to prevent external modification of the cache
         return new HashMap<>(this.applicationsCache);
     }
}
