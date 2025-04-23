package Services;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import java.util.Date;
import java.util.Comparator;
import java.io.File;

import Enums.MaritalStatus;
import Enums.OfficerRegistrationStatus;
import Enums.ApplicationStatus;

import Models.Project;
import Models.BTOApplication;
import Models.Enquiry;
import Models.OfficerRegistration;
import Models.User;
import Models.Applicant;
import Models.HDBOfficer;
import Models.HDBManager;


public class DataService {
    private static final String DATA_DIR = "data";
    private static final String APPLICANT_LIST_FILE = DATA_DIR + File.separator + "ApplicantList.csv";
    private static final String OFFICER_LIST_FILE = DATA_DIR + File.separator + "OfficerList.csv";
    private static final String MANAGER_LIST_FILE = DATA_DIR + File.separator + "ManagerList.csv";

    private static final String DELIMITER = ",";
    public static final SimpleDateFormat DATE_FORMAT = new SimpleDateFormat("yyyy-MM-dd");

    private static final String[] APPLICANT_HEADER = {"Name", "NRIC", "Age", "Marital Status", "Password"};
    private static final String[] OFFICER_HEADER = {"Name", "NRIC", "Age", "Marital Status", "Password"};
    private static final String[] MANAGER_HEADER = {"Name", "NRIC", "Age", "Marital Status", "Password"};
    public static final String NricValidator = null;


    public static Map<String, User> loadUsers() {
        Map<String, User> users = new HashMap<>();

        CsvRW.readCsv(APPLICANT_LIST_FILE, APPLICANT_HEADER.length).forEach(data -> {
            try {
                String nric = data[1].trim();
                if (!Utils.NricValidator.isValidNric(nric) || users.containsKey(nric)) {
                    if(users.containsKey(nric)) System.err.println("Duplicate NRIC found in ApplicantList: " + nric + ". Skipping duplicate.");
                    else System.err.println("Invalid NRIC format in ApplicantList: " + nric + ". Skipping.");
                    return;
                }
                int age = Integer.parseInt(data[2].trim());
                MaritalStatus status = MaritalStatus.valueOf(data[3].trim().toUpperCase());
                Applicant applicant = new Applicant(nric, data[4].trim(), data[0].trim(), age, status);
                users.put(nric, applicant);
            } catch (Exception e) {
                System.err.println("Error parsing applicant data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });

        CsvRW.readCsv(OFFICER_LIST_FILE, OFFICER_HEADER.length).forEach(data -> {
            try {
                String nric = data[1].trim();
                 if (!Utils.NricValidator.isValidNric(nric)) {
                     System.err.println("Invalid NRIC format in OfficerList: " + nric + ". Skipping.");
                     return;
                 }
                int age = Integer.parseInt(data[2].trim());
                MaritalStatus status = MaritalStatus.valueOf(data[3].trim().toUpperCase());
                HDBOfficer officer = new HDBOfficer(nric, data[4].trim(), data[0].trim(), age, status);
                if (users.containsKey(nric) && !(users.get(nric) instanceof HDBOfficer)) {
                     System.out.println("Info: User " + nric + " found in both Applicant and Officer lists. Using Officer role.");
                } else if (users.containsKey(nric)) {
                     System.err.println("Duplicate NRIC found in OfficerList: " + nric + ". Skipping duplicate.");
                     return;
                }
                users.put(nric, officer);
            } catch (Exception e) {
                System.err.println("Error parsing officer data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });

        CsvRW.readCsv(MANAGER_LIST_FILE, MANAGER_HEADER.length).forEach(data -> {
            try {
                String nric = data[1].trim();
                 if (!Utils.NricValidator.isValidNric(nric)) {
                     System.err.println("Invalid NRIC format in ManagerList: " + nric + ". Skipping.");
                     return;
                 }
                int age = Integer.parseInt(data[2].trim());
                MaritalStatus status = MaritalStatus.valueOf(data[3].trim().toUpperCase());
                HDBManager manager = new HDBManager(nric, data[4].trim(), data[0].trim(), age, status);
                if (users.containsKey(nric) && !(users.get(nric) instanceof HDBManager)) {
                     System.out.println("Info: User " + nric + " found in other lists. Using Manager role.");
                } else if (users.containsKey(nric)) {
                     System.err.println("Duplicate NRIC found in ManagerList: " + nric + ". Skipping duplicate.");
                     return;
                }
                users.put(nric, manager);
            } catch (Exception e) {
                System.err.println("Error parsing manager data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });

        System.out.println("Loaded " + users.size() + " unique users.");
        return users;
    }


    public static void synchronizeData(Map<String, User> users, List<Project> projects, Map<String, BTOApplication> applications, Map<String, OfficerRegistration> officerRegistrations) {
        System.out.println("Synchronizing loaded data...");
        boolean registrationsModified = false;

        users.values().stream()
             .filter(u -> u instanceof Applicant)
             .map(u -> (Applicant) u)
             .forEach(applicant -> {
                 BTOApplication relevantApp = applications.values().stream()
                     .filter(app -> app.getApplicantNric().equals(applicant.getNric()))
                     .max(Comparator.comparing(BTOApplication::getStatus, Comparator.comparingInt(s -> {
                         switch (s) {
                             case BOOKED: return 6;
                             case SUCCESSFUL: return 5;
                             case PENDING_WITHDRAWAL: return 4;
                             case PENDING: return 3;
                             case WITHDRAWN: return 2;
                             case UNSUCCESSFUL: return 1;
                             default: return 0;
                         }
                     })).thenComparing(BTOApplication::getApplicationDate).reversed())
                     .orElse(null);

                 if (relevantApp != null) {
                     applicant.setAppliedProjectName(relevantApp.getProjectName());
                     applicant.setApplicationStatus(relevantApp.getStatus());
                     if (relevantApp.getStatus() == ApplicationStatus.BOOKED) {
                         applicant.setBookedFlatType(relevantApp.getFlatTypeApplied());
                     } else {
                         applicant.setBookedFlatType(null);
                     }
                 } else {
                     applicant.clearApplicationState();
                 }
             });

        for (Project project : projects) {
            List<String> approvedNrics = new ArrayList<>(project.getApprovedOfficerNrics());

            for (String officerNric : approvedNrics) {
                User user = users.get(officerNric);
                if (!(user instanceof HDBOfficer)) {
                    System.err.println("Data Sync Warning: NRIC " + officerNric + " in project '" + project.getProjectName() + "' approved list is not a valid HDB Officer. Consider removing from project CSV.");
                    continue;
                }

                String expectedRegId = officerNric + "_REG_" + project.getProjectName();
                OfficerRegistration existingReg = officerRegistrations.get(expectedRegId);

                if (existingReg == null || existingReg.getStatus() != OfficerRegistrationStatus.APPROVED) {
                    System.out.println("Info: Auto-creating/updating APPROVED registration for Officer " + officerNric + " for Project '" + project.getProjectName() + "' based on project list.");

                    Date placeholderDate = project.getApplicationOpeningDate() != null ? project.getApplicationOpeningDate() : new Date(0);

                    OfficerRegistration syncReg = new OfficerRegistration(expectedRegId, officerNric, project.getProjectName(), OfficerRegistrationStatus.APPROVED, placeholderDate);
                    officerRegistrations.put(syncReg.getRegistrationId(), syncReg);
                    registrationsModified = true;
                }
            }
        }

        for (OfficerRegistration reg : officerRegistrations.values()) {
            if (reg.getStatus() == OfficerRegistrationStatus.APPROVED) {
                Project project = projects.stream()
                                        .filter(p -> p.getProjectName().equals(reg.getProjectName()))
                                        .findFirst().orElse(null);
                if (project == null) {
                    System.err.println("Data Sync Warning: Approved registration " + reg.getRegistrationId() + " refers to a non-existent project '" + reg.getProjectName() + "'. Consider removing registration.");
                } else if (!project.getApprovedOfficerNrics().contains(reg.getOfficerNric())) {
                    System.err.println("Data Sync Warning: Approved registration " + reg.getRegistrationId() + " exists, but officer " + reg.getOfficerNric() + " is NOT in project '" + project.getProjectName() + "' approved list. Registration status might be outdated or project list incorrect.");
                }
            }
        }



        if (registrationsModified) {
            System.out.println("Saving updated officer registrations due to synchronization...");
            OfficerRegistrationService.saveOfficerRegistrations(officerRegistrations);
        }

        System.out.println("Data synchronization complete.");
    }



    public static void saveAllData(Map<String, User> users, List<Project> projects, Map<String, BTOApplication> applications, List<Enquiry> enquiries, Map<String, OfficerRegistration> officerRegistrations) {
        System.out.println("Saving all data...");
        saveUsers(users);
        ProjectService.saveProjects(projects);
        ApplicationService.saveApplications(applications);
        EnquiryService.saveEnquiries(enquiries);
        OfficerRegistrationService.saveOfficerRegistrations(officerRegistrations);
        System.out.println("All data saved.");
    }

    public static void saveUsers(Map<String, User> users) {
        List<String[]> applicantData = new ArrayList<>();
        List<String[]> officerData = new ArrayList<>();
        List<String[]> managerData = new ArrayList<>();

        applicantData.add(APPLICANT_HEADER);
        officerData.add(OFFICER_HEADER);
        managerData.add(MANAGER_HEADER);

        users.values().forEach(user -> {
            String[] userData = {
                user.getName(),
                user.getNric(),
                String.valueOf(user.getAge()),
                user.getMaritalStatus().name(),
                user.getPassword()
            };
            switch (user.getRole()) {
                case HDB_MANAGER: managerData.add(userData); break;
                case HDB_OFFICER: officerData.add(userData); break;
                case APPLICANT: applicantData.add(userData); break;
            }
        });

        CsvRW.writeCsv(APPLICANT_LIST_FILE, applicantData);
        CsvRW.writeCsv(OFFICER_LIST_FILE, officerData);
        CsvRW.writeCsv(MANAGER_LIST_FILE, managerData);
        System.out.println("Saved users.");
    }
}
