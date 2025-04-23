package Services;

import java.io.File;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import Enums.OfficerRegistrationStatus;
import Models.HDBOfficer;
import Models.OfficerRegistration;
import Models.Project;
import Models.User;
import Parsers.Dparse;
import Utils.DateUtils;

public class OfficerRegistrationService implements IOfficerRegistrationService {
    private static final String DATA_DIR = "data";
    private static final String DELIMITER = ",";
    private static final String OFFICER_REGISTRATION_FILE = DATA_DIR + File.separator + "officer_registrations.csv";
    private static final String[] OFFICER_REGISTRATION_HEADER = {"RegistrationID", "OfficerNRIC", "ProjectName", "Status", "RegistrationDate"};

    private Map<String, OfficerRegistration> registrations;

    public OfficerRegistrationService() {
        this.registrations = new HashMap<>();
    }

    @Override
    public Map<String, OfficerRegistration> loadOfficerRegistrations(Map<String, User> users, List<Project> projects) {
        this.registrations.clear(); // Clear before loading

        CsvRW.readCsv(OFFICER_REGISTRATION_FILE, OFFICER_REGISTRATION_HEADER.length).forEach(data -> {
            try {
                String regId = data[0].trim();
                 if (regId.isEmpty() || this.registrations.containsKey(regId)) {
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

                 // Validate Officer NRIC using the provided users map
                 if (!users.containsKey(officerNric) || !(users.get(officerNric) instanceof HDBOfficer)) {
                     System.err.println("Warning: Registration " + regId + " refers to invalid or non-officer NRIC: " + officerNric + ". Skipping registration.");
                     return;
                 }
                 // Validate Project Name using the provided projects list
                 boolean projectExists = projects.stream().anyMatch(p -> p.getProjectName().equalsIgnoreCase(projectName));
                 if (!projectExists) {
                      System.err.println("Warning: Registration " + regId + " refers to non-existent project: " + projectName + ". Skipping registration.");
                      return;
                 }

                // Use constructor accepting all fields
                OfficerRegistration registration = new OfficerRegistration(regId, officerNric, projectName, status, regDate);
                this.registrations.put(registration.getRegistrationId(), registration);
            } catch (IllegalArgumentException e) {
                 System.err.println("Error parsing enum/data in officer registration data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            } catch (Exception e) {
                System.err.println("Error parsing officer registration data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });
        System.out.println("Loaded " + this.registrations.size() + " officer registrations.");
        return new HashMap<>(this.registrations); // Return copy
    }

    @Override
    public void saveOfficerRegistrations(Map<String, OfficerRegistration> registrationsToSave) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(OFFICER_REGISTRATION_HEADER);
        registrationsToSave.values().stream()
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
        this.registrations = new HashMap<>(registrationsToSave); // Update internal map
    }

    @Override
    public OfficerRegistration findRegistrationById(String registrationId) {
        return this.registrations.get(registrationId);
    }

    @Override
    public List<OfficerRegistration> getRegistrationsByOfficer(String officerNric) {
        if (officerNric == null) return new ArrayList<>();
        return this.registrations.values().stream()
            .filter(reg -> officerNric.equals(reg.getOfficerNric()))
            .collect(Collectors.toList());
    }

    @Override
    public List<OfficerRegistration> getRegistrationsByProject(String projectName) {
        if (projectName == null) return new ArrayList<>();
        return this.registrations.values().stream()
            .filter(reg -> projectName.equals(reg.getProjectName()))
            .collect(Collectors.toList());
    }

     @Override
     public List<OfficerRegistration> getRegistrationsByStatus(OfficerRegistrationStatus status) {
          if (status == null) return new ArrayList<>();
          return this.registrations.values().stream()
              .filter(reg -> status.equals(reg.getStatus()))
              .collect(Collectors.toList());
     }

    @Override
    public OfficerRegistration getApprovedRegistrationForOfficer(String officerNric) {
         if (officerNric == null) return null;
         return this.registrations.values().stream()
            .filter(reg -> officerNric.equals(reg.getOfficerNric()) && reg.getStatus() == OfficerRegistrationStatus.APPROVED)
            .findFirst() // Assuming an officer can only be approved for one project at a time
            .orElse(null);
    }


    @Override
    public void addRegistration(OfficerRegistration registration) {
        if (registration != null && !this.registrations.containsKey(registration.getRegistrationId())) {
            this.registrations.put(registration.getRegistrationId(), registration);
        } else if (registration != null) {
             System.err.println("Registration with ID " + registration.getRegistrationId() + " already exists.");
        }
    }

    @Override
    public boolean removeRegistration(String registrationId) {
        if (registrationId != null) {
            return this.registrations.remove(registrationId) != null;
        }
        return false;
    }

    @Override
    public Map<String, OfficerRegistration> getAllRegistrations() {
        return new HashMap<>(this.registrations); // Return copy
    }
}
