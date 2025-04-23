package Repositories;

import java.io.File;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import Enums.OfficerRegistrationStatus;
import Interfaces.Repositories.IOfficerRegistrationRepository;
import Models.OfficerRegistration;
import Parsers.Dparse;
import Services.CsvRW; // Assuming CsvRW is in Services package
import Utils.DateUtils;

public class CsvOfficerRegistrationRepository implements IOfficerRegistrationRepository {
    private static final String DATA_DIR = "data";
    private static final String DELIMITER = ",";
    private static final String OFFICER_REGISTRATION_FILE = DATA_DIR + File.separator + "officer_registrations.csv";
    private static final String[] OFFICER_REGISTRATION_HEADER = {"RegistrationID", "OfficerNRIC", "ProjectName", "Status", "RegistrationDate"};

    private Map<String, OfficerRegistration> registrationsCache;

    public CsvOfficerRegistrationRepository() {
        this.registrationsCache = null; // Load on demand
    }

    @Override
    public Map<String, OfficerRegistration> loadOfficerRegistrations() {
        if (this.registrationsCache != null) {
            return new HashMap<>(this.registrationsCache); // Return copy
        }

        Map<String, OfficerRegistration> loadedRegistrations = new HashMap<>();
        List<String[]> rawData = CsvRW.readCsv(OFFICER_REGISTRATION_FILE, OFFICER_REGISTRATION_HEADER.length);

        for (String[] data : rawData) {
            try {
                String regId = data[0].trim();
                 if (regId.isEmpty() || loadedRegistrations.containsKey(regId)) {
                     if (!regId.isEmpty()) System.err.println("Skipping duplicate registration ID in CSV: " + regId);
                    continue;
                 }
                String officerNric = data[1].trim();
                String projectName = data[2].trim();
                OfficerRegistrationStatus status = OfficerRegistrationStatus.valueOf(data[3].trim().toUpperCase());
                Date regDate = Dparse.parseDate(data[4].trim());

                 if (regDate == null) {
                     System.err.println("Skipping registration with invalid date: " + regId);
                     return null;
                 }

                 // Basic validation - deeper validation (user exists, project exists) should be in DataSyncService
                 if (officerNric.isEmpty() || projectName.isEmpty()) {
                      System.err.println("Skipping registration with empty NRIC or Project Name: " + regId);
                      return null;
                 }

                OfficerRegistration registration = new OfficerRegistration(regId, officerNric, projectName, status, regDate);
                loadedRegistrations.put(registration.getRegistrationId(), registration);
            } catch (IllegalArgumentException e) {
                 System.err.println("Error parsing enum/data in officer registration data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            } catch (Exception e) {
                System.err.println("Error parsing officer registration data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        }
        this.registrationsCache = loadedRegistrations;
        System.out.println("Loaded " + this.registrationsCache.size() + " officer registrations from CSV.");
        return new HashMap<>(this.registrationsCache); // Return copy
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
        this.registrationsCache = new HashMap<>(registrationsToSave); // Update cache
        System.out.println("Saved " + registrationsToSave.size() + " officer registrations to CSV.");
    }

     @Override
     public Map<String, OfficerRegistration> getAllRegistrations() {
         if (this.registrationsCache == null) {
             loadOfficerRegistrations();
         }
         // Return a defensive copy
         return new HashMap<>(this.registrationsCache);
     }
}
