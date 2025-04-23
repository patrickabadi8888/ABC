package Services;

import java.io.File;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import Enums.OfficerRegistrationStatus;
import Models.HDBOfficer;
import Models.OfficerRegistration;
import Models.Project;
import Models.User;
import Parsers.Dparse;
import Utils.DateUtils;

public class OfficerRegistrationService {
    private static final String DATA_DIR = "data";
    private static final String DELIMITER = ",";
    private static final String OFFICER_REGISTRATION_FILE = DATA_DIR + File.separator + "officer_registrations.csv";
    private static final String[] OFFICER_REGISTRATION_HEADER = {"RegistrationID", "OfficerNRIC", "ProjectName", "Status", "RegistrationDate"};
    public static Map<String, OfficerRegistration> loadOfficerRegistrations(Map<String, User> users, List<Project> projects) {
        Map<String, OfficerRegistration> registrations = new HashMap<>();

        CsvRW.readCsv(OFFICER_REGISTRATION_FILE, OFFICER_REGISTRATION_HEADER.length).forEach(data -> {
            try {
                String regId = data[0].trim();
                 if (regId.isEmpty() || registrations.containsKey(regId)) {
                     if (!regId.isEmpty()) System.err.println("Skipping duplicate registration ID: " + regId);
                    return;
                 }
                String officerNric = data[1].trim();
                String projectName = data[2].trim();
                OfficerRegistrationStatus status = OfficerRegistrationStatus.valueOf(data[3].trim().toUpperCase());
                Date regDate = Dparse.parseDate(data[4].trim());

                 if (regDate == null) {
                     System.err.println("Skipping registration with invalid date: " + regId);
                     return;
                 }

                 if (!users.containsKey(officerNric) || !(users.get(officerNric) instanceof HDBOfficer)) {
                     System.err.println("Warning: Registration " + regId + " refers to invalid or non-officer NRIC: " + officerNric + ". Skipping registration.");
                     return;
                 }
                 boolean projectExists = projects.stream().anyMatch(p -> p.getProjectName().equalsIgnoreCase(projectName));
                 if (!projectExists) {
                      System.err.println("Warning: Registration " + regId + " refers to non-existent project: " + projectName + ". Skipping registration.");
                      return;
                 }


                OfficerRegistration registration = new OfficerRegistration(regId, officerNric, projectName, status, regDate);
                registrations.put(registration.getRegistrationId(), registration);
            } catch (IllegalArgumentException e) {
                 System.err.println("Error parsing enum/data in officer registration data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            } catch (Exception e) {
                System.err.println("Error parsing officer registration data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });
        System.out.println("Loaded " + registrations.size() + " officer registrations.");
        return registrations;
    }

    public static void saveOfficerRegistrations(Map<String, OfficerRegistration> registrations) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(OFFICER_REGISTRATION_HEADER);
        registrations.values().stream()
            .sorted(Comparator.comparing(OfficerRegistration::getRegistrationId))
            .forEach(reg -> {
                dataList.add(new String[]{
                    reg.getRegistrationId(),
                    reg.getOfficerNric(),
                    reg.getProjectName(),
                    reg.getStatus().name(),
                    DateUtils.formatDate(reg.getRegistrationDate())
                });
            });
        CsvRW.writeCsv(OFFICER_REGISTRATION_FILE, dataList);
        System.out.println("Saved officer registrations.");
    }
}
