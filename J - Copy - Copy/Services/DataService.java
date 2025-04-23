package Services;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Date;
import java.util.Comparator;
import java.io.File;

import Enums.OfficerRegistrationStatus;
import Enums.ApplicationStatus;

import Models.Project;
import Models.BTOApplication;
import Models.OfficerRegistration;
import Models.User;
import Models.Applicant;
import Models.HDBOfficer;

// DataService retains static methods for coordination and user file I/O
public class DataService {
    private static final String DATA_DIR = "data";
    private static final String APPLICANT_LIST_FILE = DATA_DIR + File.separator + "ApplicantList.csv";
    private static final String OFFICER_LIST_FILE = DATA_DIR + File.separator + "OfficerList.csv";
    private static final String MANAGER_LIST_FILE = DATA_DIR + File.separator + "ManagerList.csv";

    public static final SimpleDateFormat DATE_FORMAT = new SimpleDateFormat("yyyy-MM-dd");

    private static final String[] APPLICANT_HEADER = { "Name", "NRIC", "Age", "Marital Status", "Password" };
    private static final String[] OFFICER_HEADER = { "Name", "NRIC", "Age", "Marital Status", "Password" };
    private static final String[] MANAGER_HEADER = { "Name", "NRIC", "Age", "Marital Status", "Password" };
    // NricValidator usage moved to where NRICs are actually processed (e.g., UserService, AuthController)

    // loadUsers is now primarily handled by UserService instance
    // This static method could potentially be removed or adapted if needed for a specific bootstrapping scenario.
    // For now, keep the saveUsers static method as it was used by AuthController.
    // And saveAllData for convenience during shutdown.

    public static void synchronizeData(IUserService userService, IProjectService projectService, IApplicationService applicationService, IOfficerRegistrationService officerRegistrationService) {
        System.out.println("Synchronizing loaded data...");

        Map<String, User> users = userService.getAllUsers();
        List<Project> projects = projectService.getAllProjects();
        Map<String, BTOApplication> applications = applicationService.getAllApplications();
        Map<String, OfficerRegistration> officerRegistrations = officerRegistrationService.getAllRegistrations();

        boolean registrationsModified = false;

        // Sync Applicant state from Applications
        users.values().stream()
                .filter(u -> u instanceof Applicant)
                .map(u -> (Applicant) u)
                .forEach(applicant -> {
                    BTOApplication relevantApp = applications.values().stream()
                            .filter(app -> app.getApplicantNric().equals(applicant.getNric()))
                            .max(Comparator.comparing(BTOApplication::getStatus,
                                    Comparator.comparingInt(s -> {
                                        // Explicit priority order
                                        switch (s) {
                                            case BOOKED: return 6;
                                            case SUCCESSFUL: return 5;
                                            case PENDING_WITHDRAWAL: return 4;
                                            case PENDING: return 3;
                                            case WITHDRAWN: return 2;
                                            case UNSUCCESSFUL: return 1;
                                            default: return 0;
                                        }
                                    })).thenComparing(BTOApplication::getApplicationDate, Comparator.reverseOrder())) // Prefer latest application for same status
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


        // Sync Project approved officers with Officer Registrations
        for (Project project : projects) {
            List<String> approvedNricsFromProject = new ArrayList<>(project.getApprovedOfficerNrics()); // Copy

            // Check officers listed in project against registrations
            for (String officerNric : approvedNricsFromProject) {
                User user = users.get(officerNric);
                if (!(user instanceof HDBOfficer)) {
                    System.err.println("Data Sync Warning: NRIC " + officerNric + " in project '"
                            + project.getProjectName()
                            + "' approved list is not a valid HDB Officer. Consider removing from project CSV.");
                    continue; // Skip this NRIC
                }

                // Check if an APPROVED registration exists for this officer+project
                String expectedRegId = officerNric + "_REG_" + project.getProjectName();
                OfficerRegistration existingReg = officerRegistrations.get(expectedRegId);

                if (existingReg == null || existingReg.getStatus() != OfficerRegistrationStatus.APPROVED) {
                    // If project says officer is approved, but no APPROVED registration exists, create/update one.
                    System.out.println("Info: Auto-creating/updating APPROVED registration for Officer " + officerNric
                            + " for Project '" + project.getProjectName() + "' based on project list.");

                    // Use a placeholder date or project start date
                    Date placeholderDate = project.getApplicationOpeningDate() != null
                            ? project.getApplicationOpeningDate()
                            : new Date(0); // Epoch as fallback

                    OfficerRegistration syncReg = new OfficerRegistration(expectedRegId, officerNric,
                            project.getProjectName(), OfficerRegistrationStatus.APPROVED, placeholderDate);
                    officerRegistrations.put(syncReg.getRegistrationId(), syncReg); // Update the map directly
                    registrationsModified = true;
                }
            }

             // Check approved registrations against the project list
             officerRegistrations.values().stream()
                .filter(reg -> reg.getProjectName().equals(project.getProjectName()) && reg.getStatus() == OfficerRegistrationStatus.APPROVED)
                .forEach(reg -> {
                    if (!project.getApprovedOfficerNrics().contains(reg.getOfficerNric())) {
                         System.err.println("Data Sync Warning: Approved registration " + reg.getRegistrationId()
                                + " exists, but officer " + reg.getOfficerNric() + " is NOT in project '"
                                + project.getProjectName()
                                + "' approved list. Project CSV might be outdated or registration status incorrect.");
                         // Optionally: could remove the officer from the registration here, or change status to pending?
                         // For now, just warn.
                    }
                });
        }

        // Note: Adjusting project available units based on booked applications
        // is now handled within ApplicationService.loadApplications.

        if (registrationsModified) {
            System.out.println("Saving updated officer registrations due to synchronization...");
            // Use the service instance to save the modified map
            officerRegistrationService.saveOfficerRegistrations(officerRegistrations);
        }
         // Saving projects or users happens elsewhere based on user actions or final save.

        System.out.println("Data synchronization complete.");
    }

    // Keep saveAllData for convenience, using the service instances
    public static void saveAllData(IUserService userService, IProjectService projectService, IApplicationService applicationService, IEnquiryService enquiryService, IOfficerRegistrationService officerRegistrationService) {
        System.out.println("Saving all data...");
        userService.saveUsers(userService.getAllUsers()); // Save the current state managed by userService
        projectService.saveProjects(projectService.getAllProjects());
        applicationService.saveApplications(applicationService.getAllApplications());
        enquiryService.saveEnquiries(enquiryService.getAllEnquiries());
        officerRegistrationService.saveOfficerRegistrations(officerRegistrationService.getAllRegistrations());
        System.out.println("All data saved.");
    }

     // Keep saveUsers static as AuthController uses it directly
     public static void saveUsers(Map<String, User> users) {
         // This static method now duplicates the logic in UserService.saveUsers.
         // Ideally, AuthController should use IUserService.
         // For minimal change, we keep this static version functional.
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
                 case HDB_MANAGER:
                     managerData.add(userData);
                     break;
                 case HDB_OFFICER:
                     officerData.add(userData);
                     break;
                 case APPLICANT:
                     applicantData.add(userData);
                     break;
             }
         });

         CsvRW.writeCsv(APPLICANT_LIST_FILE, applicantData);
         CsvRW.writeCsv(OFFICER_LIST_FILE, officerData);
         CsvRW.writeCsv(MANAGER_LIST_FILE, managerData);
         System.out.println("Saved users (via static DataService method).");
     }
}
