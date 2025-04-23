package Controllers;

import java.util.List;
import java.util.Map;
import java.util.Scanner;
import java.util.stream.Collectors;
import java.util.Comparator;

import Enums.ApplicationStatus;
import Enums.FlatType;
import Enums.OfficerRegistrationStatus;
import Models.Applicant;
import Models.BTOApplication;
import Models.HDBOfficer;
import Models.Project;
import Models.User;
import Services.IApplicationService;
import Services.IOfficerRegistrationService;
import Services.IProjectService;
import Services.IUserService;
import Utils.DateUtils;

// Handles core applicant actions related to applications
public class ApplicantActionController extends BaseController {

    public ApplicantActionController(IUserService userService, IProjectService projectService,
                                     IApplicationService applicationService, IOfficerRegistrationService officerRegistrationService,
                                     User currentUser, Scanner scanner, AuthController authController) {
        super(userService, projectService, applicationService, officerRegistrationService, currentUser, scanner, authController);
    }

    public void viewOpenProjects() {
        System.out.println("\n--- Viewing Available BTO Projects ---");
        // Get projects that are visible, eligible, available, active period, and not expired
        List<Project> availableProjects = getFilteredProjects(true, true, true, true, true);
        viewAndSelectProject(availableProjects, "Available BTO Projects");
    }

    public void applyForProject() {
        // Ensure current user is an Applicant (or subclass like HDBOfficer)
        if (!(currentUser instanceof Applicant)) {
            System.out.println("Error: Only applicants can apply for projects.");
            return;
        }
        Applicant applicant = (Applicant) currentUser;

        // Check existing application status
        if (applicant.hasBooked()) {
            System.out.println("You have already booked a flat for project '" + applicant.getAppliedProjectName()
                    + "'. You cannot apply again.");
            return;
        }
        if (applicant.hasActiveApplication()) {
            System.out.println("You have an active application for project '" + applicant.getAppliedProjectName()
                    + "' with status: " + applicant.getApplicationStatus());
            System.out.println("You must withdraw (and have it approved) or be unsuccessful before applying again.");
            return;
        }
         if (applicant.hasPendingWithdrawal()) {
            System.out.println("You have a withdrawal request pending manager approval for project '"
                    + applicant.getAppliedProjectName() + "'.");
            System.out.println("You cannot apply for a new project until the withdrawal is processed.");
            return;
        }


        System.out.println("\n--- Apply for BTO Project ---");
        // Get projects eligible for application (visible, eligible, available, active period, not expired)
        List<Project> eligibleProjects = getFilteredProjects(true, true, true, true, true);

        if (eligibleProjects.isEmpty()) {
            System.out.println(
                    "There are currently no open projects you are eligible to apply for based on filters, eligibility, and unit availability.");
            return;
        }

        viewAndSelectProject(eligibleProjects, "Select Project to Apply For");
        Project selectedProject = selectProjectFromList(eligibleProjects);
        if (selectedProject == null) return; // User cancelled

        // Special check if the applicant is also an Officer
        if (currentUser instanceof HDBOfficer) {
            HDBOfficer officer = (HDBOfficer) currentUser;
            Project handlingProject = getOfficerHandlingProject(officer); // Use BaseController method
            // Check if officer is trying to apply for the project they are handling
            if (handlingProject != null && selectedProject.equals(handlingProject)) {
                System.out.println("Error: You cannot apply for a project you are currently handling as an Officer.");
                return;
            }
            // Check if officer has a PENDING registration for this project
            boolean hasPendingRegistration = officerRegistrationService.getRegistrationsByOfficer(officer.getNric())
                    .stream()
                    .anyMatch(reg -> reg.getProjectName().equals(selectedProject.getProjectName()) &&
                            reg.getStatus() == OfficerRegistrationStatus.PENDING);
            if (hasPendingRegistration) {
                System.out.println("Error: You cannot apply for a project you have a pending registration for.");
                return;
            }
        }

        // Select flat type
        FlatType selectedFlatType = selectEligibleFlatType(selectedProject);
        if (selectedFlatType == null) return; // User cancelled or no eligible types

        // Create and save application
        BTOApplication newApplication = new BTOApplication(currentUser.getNric(), selectedProject.getProjectName(),
                selectedFlatType, DateUtils.getCurrentDate());
        applicationService.addApplication(newApplication); // Add via service

        // Update applicant's status in memory (will be saved later or during sync)
        applicant.setAppliedProjectName(selectedProject.getProjectName());
        applicant.setApplicationStatus(ApplicationStatus.PENDING);
        applicant.setBookedFlatType(null); // Reset booked type

        System.out.println("Application submitted successfully for project '" + selectedProject.getProjectName() + "' ("
                + selectedFlatType.getDisplayName() + "). Status: PENDING.");

        // Save immediately after adding
        applicationService.saveApplications(applicationService.getAllApplications());
        // No need to save users here, sync handles it or final save does.
    }

    private FlatType selectEligibleFlatType(Project project) {
        // Filter flat types in the project: user must be eligible AND units must be available
        List<FlatType> eligibleAndAvailableTypes = project.getFlatTypes().entrySet().stream()
                .filter(entry -> canApplyForFlatType(entry.getKey()) && entry.getValue().getAvailableUnits() > 0)
                .map(Map.Entry::getKey)
                .sorted() // Sort by enum order
                .collect(Collectors.toList());

        if (eligibleAndAvailableTypes.isEmpty()) {
            System.out.println("There are no flat types available in this project that you are eligible for and have units remaining.");
            return null;
        }

        // If only one option, select it automatically
        if (eligibleAndAvailableTypes.size() == 1) {
            FlatType onlyOption = eligibleAndAvailableTypes.get(0);
            System.out.println("You will be applying for the only eligible and available type: "
                    + onlyOption.getDisplayName() + ".");
            return onlyOption;
        } else {
            // Present choices
            System.out.println("Select the flat type you want to apply for:");
            for (int i = 0; i < eligibleAndAvailableTypes.size(); i++) {
                System.out.println((i + 1) + ". " + eligibleAndAvailableTypes.get(i).getDisplayName());
            }
            // Get user choice using utility method
            int typeChoice = getIntInput("Enter choice (or 0 to cancel): ", 0, eligibleAndAvailableTypes.size());

            if (typeChoice == 0) {
                System.out.println("Application cancelled.");
                return null;
            }
            // Return the selected type (adjusting for 1-based index)
            return eligibleAndAvailableTypes.get(typeChoice - 1);
        }
    }

    public void viewMyApplication() {
        if (!(currentUser instanceof Applicant)) return;
        Applicant applicant = (Applicant) currentUser;
        // Sync might be good before viewing, but BTOApp handles sync before menu now.

        String projectName = applicant.getAppliedProjectName();
        ApplicationStatus status = applicant.getApplicationStatus();

        if (projectName == null || status == null) {
            System.out.println("You do not have any current or past BTO application records synced to your profile.");
             // Check the application service directly just in case sync missed something
             List<BTOApplication> historicalApps = applicationService.getApplicationsByApplicant(applicant.getNric());
             if (!historicalApps.isEmpty()) {
                 System.out.println("However, historical application records exist. The latest was:");
                 // Find the latest application by date
                 BTOApplication latestApp = historicalApps.stream()
                                                .max(Comparator.comparing(BTOApplication::getApplicationDate))
                                                .orElse(null);
                 if (latestApp != null) {
                      Project project = projectService.findProjectByName(latestApp.getProjectName());
                      System.out.println("Project Name: " + latestApp.getProjectName());
                      System.out.println("Neighborhood: " + (project != null ? project.getNeighborhood() : "(Project details not found)"));
                      System.out.println("Flat Type Applied For: " + (latestApp.getFlatTypeApplied() != null ? latestApp.getFlatTypeApplied().getDisplayName() : "N/A"));
                      System.out.println("Application Status: " + latestApp.getStatus());
                      System.out.println("Application Date: " + DateUtils.formatDate(latestApp.getApplicationDate()));
                 }
             }
            return;
        }

        // Find the application record using the service
        BTOApplication application = applicationService.findApplicationByApplicantAndProject(applicant.getNric(), projectName);
        if (application == null) {
            // This case indicates an inconsistency between the Applicant object's state and the application records
            System.out.println(
                    "Error: Your profile indicates an application for '" + projectName + "', but the detailed record could not be found. Please contact support.");
            return;
        }

        // Find project details using the service
        Project project = projectService.findProjectByName(projectName);

        System.out.println("\n--- Your BTO Application ---");
        System.out.println("Project Name: " + projectName);
        System.out.println("Neighborhood: " + (project != null ? project.getNeighborhood() : "(Project details not found)"));
        System.out.println("Flat Type Applied For: " + (application.getFlatTypeApplied() != null ? application.getFlatTypeApplied().getDisplayName() : "N/A"));
        System.out.println("Application Status: " + status); // Display status from Applicant object (should match application object after sync)
        // Display booked flat type if applicable
        if (status == ApplicationStatus.BOOKED && applicant.getBookedFlatType() != null) {
            System.out.println("Booked Flat Type: " + applicant.getBookedFlatType().getDisplayName());
        }
        System.out.println("Application Date: " + DateUtils.formatDate(application.getApplicationDate()));
    }

    public void requestWithdrawal() {
         if (!(currentUser instanceof Applicant)) return;
         Applicant applicant = (Applicant) currentUser;
         // Sync data before processing withdrawal request
         // DataService.synchronizeData(users, projects, applications, officerRegistrations); // Sync done in BTOApp loop

        String currentProject = applicant.getAppliedProjectName();
        ApplicationStatus currentStatus = applicant.getApplicationStatus();

        if (currentProject == null || currentStatus == null) {
            System.out.println("You do not have an application to withdraw.");
            return;
        }

        // Check if the application is eligible for withdrawal request
        if (currentStatus != ApplicationStatus.PENDING &&
                currentStatus != ApplicationStatus.SUCCESSFUL &&
                currentStatus != ApplicationStatus.BOOKED) {
            System.out.println("Your application status (" + currentStatus + ") is not eligible for withdrawal request.");
            System.out.println("You can only request withdrawal if your status is PENDING, SUCCESSFUL, or BOOKED.");
            return;
        }

        // Find the corresponding BTOApplication object
        BTOApplication application = applicationService.findApplicationByApplicantAndProject(applicant.getNric(), currentProject);
        if (application == null) {
            System.out.println(
                    "Error: Could not find the application record for project '" + currentProject + "' to request withdrawal. Please contact support.");
            return;
        }
        // Double-check the status in the application record matches the applicant profile
         if (application.getStatus() != currentStatus) {
             System.out.println("Error: Application status mismatch between profile (" + currentStatus + ") and record (" + application.getStatus() + "). Please re-login or contact support.");
             return;
         }

        System.out.println("\n--- Request Application Withdrawal ---");
        System.out.println("Project: " + application.getProjectName());
        System.out.println("Current Status: " + currentStatus);
        System.out.print(
                "Are you sure you want to request withdrawal for this application? Manager approval is required. (yes/no): ");
        String confirm = scanner.nextLine().trim().toLowerCase();

        if (confirm.equals("yes")) {
            // Update the status in the BTOApplication object
            application.setStatus(ApplicationStatus.PENDING_WITHDRAWAL); // This now also sets statusBeforeWithdrawal internally

            // Update the status in the Applicant object
            applicant.setApplicationStatus(ApplicationStatus.PENDING_WITHDRAWAL);

            System.out.println("Withdrawal request submitted successfully.");
            System.out.println("Your application status is now PENDING_WITHDRAWAL and requires Manager approval.");

            // Save the updated application state
            applicationService.saveApplications(applicationService.getAllApplications());
             // Save user state? Not strictly necessary if relying on sync, but safer.
             // userService.saveUsers(userService.getAllUsers()); // Requires userService injection

        } else {
            System.out.println("Withdrawal request cancelled.");
        }
    }
}
