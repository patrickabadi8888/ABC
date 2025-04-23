package Repositories;

import java.io.File;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import Enums.MaritalStatus;
import Enums.UserRole;
import Interfaces.Repositories.IUserRepository;
import Models.Applicant;
import Models.HDBManager;
import Models.HDBOfficer;
import Models.User;
import Services.CsvRW; // Assuming CsvRW is in Services package
import Utils.NricValidator; // Assuming NricValidator is in Utils package

public class CsvUserRepository implements IUserRepository {
    private static final String DATA_DIR = "data";
    private static final String APPLICANT_LIST_FILE = DATA_DIR + File.separator + "ApplicantList.csv";
    private static final String OFFICER_LIST_FILE = DATA_DIR + File.separator + "OfficerList.csv";
    private static final String MANAGER_LIST_FILE = DATA_DIR + File.separator + "ManagerList.csv";
    private static final String DELIMITER = ",";

    private static final String[] APPLICANT_HEADER = { "Name", "NRIC", "Age", "Marital Status", "Password" };
    private static final String[] OFFICER_HEADER = { "Name", "NRIC", "Age", "Marital Status", "Password" };
    private static final String[] MANAGER_HEADER = { "Name", "NRIC", "Age", "Marital Status", "Password" };

    private Map<String, User> usersCache;

    public CsvUserRepository() {
        this.usersCache = null; // Load on demand
    }

    @Override
    public Map<String, User> loadUsers() {
        if (this.usersCache != null) {
            return new HashMap<>(this.usersCache); // Return copy
        }

        Map<String, User> loadedUsers = new HashMap<>();

        // Load Applicants
        CsvRW.readCsv(APPLICANT_LIST_FILE, APPLICANT_HEADER.length).forEach(data -> {
            try {
                String nric = data[1].trim().toUpperCase(); // Standardize NRIC case
                if (!NricValidator.isValidNric(nric) || loadedUsers.containsKey(nric)) {
                    if (loadedUsers.containsKey(nric))
                        System.err.println("Duplicate NRIC found in ApplicantList: " + nric + ". Skipping duplicate.");
                    else
                        System.err.println("Invalid NRIC format in ApplicantList: " + nric + ". Skipping.");
                    return;
                }
                int age = Integer.parseInt(data[2].trim());
                MaritalStatus status = MaritalStatus.valueOf(data[3].trim().toUpperCase());
                Applicant applicant = new Applicant(nric, data[4].trim(), data[0].trim(), age, status);
                loadedUsers.put(nric, applicant);
            } catch (Exception e) {
                System.err.println(
                        "Error parsing applicant data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });

        // Load Officers
        CsvRW.readCsv(OFFICER_LIST_FILE, OFFICER_HEADER.length).forEach(data -> {
            try {
                String nric = data[1].trim().toUpperCase(); // Standardize NRIC case
                if (!NricValidator.isValidNric(nric)) {
                    System.err.println("Invalid NRIC format in OfficerList: " + nric + ". Skipping.");
                    return;
                }
                int age = Integer.parseInt(data[2].trim());
                MaritalStatus status = MaritalStatus.valueOf(data[3].trim().toUpperCase());
                HDBOfficer officer = new HDBOfficer(nric, data[4].trim(), data[0].trim(), age, status);

                if (loadedUsers.containsKey(nric)) {
                    User existingUser = loadedUsers.get(nric);
                    if (existingUser instanceof HDBManager) {
                        System.err.println("Conflict: NRIC " + nric + " exists as Manager. Cannot overwrite with Officer role. Skipping Officer.");
                        return;
                    } else if (existingUser instanceof HDBOfficer) {
                         System.err.println("Duplicate NRIC found in OfficerList: " + nric + ". Skipping duplicate.");
                         return;
                    } else { // Existing is Applicant
                        System.out.println(
                            "Info: User " + nric + " found in Applicant list. Upgrading to Officer role.");
                    }
                }
                loadedUsers.put(nric, officer); // Add or overwrite Applicant
            } catch (Exception e) {
                System.err.println(
                        "Error parsing officer data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });

        // Load Managers
        CsvRW.readCsv(MANAGER_LIST_FILE, MANAGER_HEADER.length).forEach(data -> {
            try {
                String nric = data[1].trim().toUpperCase(); // Standardize NRIC case
                if (!NricValidator.isValidNric(nric)) {
                    System.err.println("Invalid NRIC format in ManagerList: " + nric + ". Skipping.");
                    return;
                }
                int age = Integer.parseInt(data[2].trim());
                MaritalStatus status = MaritalStatus.valueOf(data[3].trim().toUpperCase());
                HDBManager manager = new HDBManager(nric, data[4].trim(), data[0].trim(), age, status);

                if (loadedUsers.containsKey(nric)) {
                     User existingUser = loadedUsers.get(nric);
                     if (existingUser instanceof HDBManager) {
                          System.err.println("Duplicate NRIC found in ManagerList: " + nric + ". Skipping duplicate.");
                          return;
                     } else { // Existing is Applicant or Officer
                         System.out.println("Info: User " + nric + " found in other lists. Upgrading to Manager role.");
                     }
                }
                loadedUsers.put(nric, manager); // Add or overwrite Applicant/Officer
            } catch (Exception e) {
                System.err.println(
                        "Error parsing manager data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });

        this.usersCache = loadedUsers;
        System.out.println("Loaded " + this.usersCache.size() + " unique users from CSV.");
        return new HashMap<>(this.usersCache); // Return copy
    }

    @Override
    public void saveUsers(Map<String, User> usersToSave) {
        List<String[]> applicantData = new ArrayList<>();
        List<String[]> officerData = new ArrayList<>();
        List<String[]> managerData = new ArrayList<>();

        // Add headers
        applicantData.add(APPLICANT_HEADER);
        officerData.add(OFFICER_HEADER);
        managerData.add(MANAGER_HEADER);

        // Populate data lists based on role
        usersToSave.values().forEach(user -> {
            String[] userData = {
                    user.getName(),
                    user.getNric(),
                    String.valueOf(user.getAge()),
                    user.getMaritalStatus().name(),
                    user.getPassword() // Save current password
            };
            switch (user.getRole()) {
                case HDB_MANAGER:
                    managerData.add(userData);
                    break;
                case HDB_OFFICER:
                    // Officers are also Applicants, save in both lists if needed by design
                    // Or just save as Officer if roles are strictly hierarchical upgrade
                    // Current load logic implies upgrade, so save only in highest role file.
                    officerData.add(userData);
                    break;
                case APPLICANT:
                    // Only save here if they are *not* also an Officer or Manager
                    if (!(user instanceof HDBOfficer) && !(user instanceof HDBManager)) {
                         applicantData.add(userData);
                    }
                    break;
            }
        });

        // Write to CSV files
        CsvRW.writeCsv(APPLICANT_LIST_FILE, applicantData);
        CsvRW.writeCsv(OFFICER_LIST_FILE, officerData);
        CsvRW.writeCsv(MANAGER_LIST_FILE, managerData);

        this.usersCache = new HashMap<>(usersToSave); // Update cache
        System.out.println("Saved " + usersToSave.size() + " users to CSV.");
    }

     @Override
     public User findUserByNric(String nric) {
         if (nric == null) return null;
         if (this.usersCache == null) {
             loadUsers();
         }
         return this.usersCache.get(nric.toUpperCase()); // Use standardized case for lookup
     }

     @Override
     public Map<String, User> getAllUsers() {
         if (this.usersCache == null) {
             loadUsers();
         }
         // Return a defensive copy
         return new HashMap<>(this.usersCache);
     }
}
