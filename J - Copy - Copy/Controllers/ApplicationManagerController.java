package Controllers;

import java.util.Comparator;
import java.util.List;
import java.util.Scanner;
import java.util.stream.Collectors;

import Enums.ApplicationStatus;
import Enums.FlatType;
import Models.Applicant;
import Models.BTOApplication;
import Models.FlatTypeDetails;
import Models.HDBManager;
import Models.Project;
import Models.User;
import Services.IApplicationService;
import Services.IEnquiryService;
import Services.IOfficerRegistrationService;
import Services.IProjectService;
import Services.IUserService;
import Utils.DateUtils;

// Handles Manager actions related to BTO Application approval/rejection
public class ApplicationManagerController extends BaseController {

    public ApplicationManagerController(IUserService userService, IProjectService projectService,
                                   IApplicationService applicationService, IOfficerRegistrationService officerRegistrationService,
                                   IEnquiryService enquiryService,
                                   User currentUser, Scanner scanner, AuthController authController) {
        super(userService, projectService, applicationService, officerRegistrationService, currentUser, scanner, authController);
         if (!(currentUser instanceof HDBManager)) {
            throw new IllegalArgumentException("ApplicationManagerController requires an HDBManager user.");
        }
    }

     public void manageApplications() {
        System.out.println("\n--- Manage BTO Applications ---");
        // Get projects managed by this manager
        List<Project> myProjects = projectService.getProjectsManagedBy(currentUser.getNric())
                                    .stream()
                                    .sorted(Comparator.comparing(project -> project.getProjectName()))
                                    .collect(Collectors.toList());
        if (myProjects.isEmpty()) {
            System.out.println("You are not managing any projects for which to manage applications.");
            return;
        }

        // Select project
        System.out.println("Select project to manage applications for:");
        viewAndSelectProject(myProjects, "Select Project");
        Project selectedProject = selectProjectFromList(myProjects);
        if (selectedProject == null) return;

        System.out.println("\n--- Applications for Project: " + selectedProject.getProjectName() + " ---");

        // Get all applications for this project via service
        List<BTOApplication> projectApplications = applicationService.getApplicationsByProject(selectedProject.getProjectName())
                .stream()
                .sorted(Comparator.comparing(app -> app.getApplicationDate())) // Sort by date
                .collect(Collectors.toList());

        if (projectApplications.isEmpty()) {
            System.out.println("No applications found for this project.");
            return;
        }

        // Filter for PENDING applications
        List<BTOApplication> pendingApps = projectApplications.stream()
                .filter(app -> app.getStatus() == ApplicationStatus.PENDING)
                .collect(Collectors.toList());

        // --- Process Pending Applications ---
        System.out.println("--- Pending Applications ---");
        if (pendingApps.isEmpty()) {
            System.out.println("(None)");
        } else {
            // Display pending applications for selection
            for (int i = 0; i < pendingApps.size(); i++) {
                BTOApplication app = pendingApps.get(i);
                User applicantUser = userService.findUserByNric(app.getApplicantNric()); // Get applicant details
                System.out.printf("%d. NRIC: %s | Name: %-15s | Type: %-8s | Date: %s\n",
                        i + 1, app.getApplicantNric(),
                        applicantUser != null ? applicantUser.getName() : "N/A",
                        app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A",
                        DateUtils.formatDate(app.getApplicationDate()));
            }

            // Prompt for action
            int choice = getIntInput("Enter number to Approve/Reject (or 0 to skip): ", 0, pendingApps.size());

            if (choice >= 1) {
                BTOApplication appToProcess = pendingApps.get(choice - 1);
                User applicantUser = userService.findUserByNric(appToProcess.getApplicantNric());

                // Validate applicant data
                if (!(applicantUser instanceof Applicant)) {
                    System.out.println("Error: Applicant data not found or invalid for NRIC "
                            + appToProcess.getApplicantNric() + ". Rejecting application.");
                    appToProcess.setStatus(ApplicationStatus.UNSUCCESSFUL); // Set status in application object
                    // Applicant profile status will be updated during next sync or manually if needed
                    applicationService.saveApplications(applicationService.getAllApplications()); // Save change
                    return; // Exit processing for this round
                }
                Applicant applicant = (Applicant) applicantUser;

                // Prompt for Approve/Reject
                System.out.print("Approve or Reject application for Applicant " + applicant.getName() + "? (A/R): ");
                String action = scanner.nextLine().trim().toUpperCase();

                if (action.equals("A")) {
                    // --- Approve Action ---
                    FlatType appliedType = appToProcess.getFlatTypeApplied();
                    if (appliedType == null) {
                        System.out.println("Error: Application has no specified flat type. Cannot approve. Rejecting.");
                        appToProcess.setStatus(ApplicationStatus.UNSUCCESSFUL);
                        applicant.setApplicationStatus(ApplicationStatus.UNSUCCESSFUL); // Update profile immediately
                        applicationService.saveApplications(applicationService.getAllApplications());
                        return;
                    }

                    // Get project details (refreshing might be good practice)
                    Project currentProjectState = projectService.findProjectByName(selectedProject.getProjectName());
                     if (currentProjectState == null) {
                          System.out.println("Error: Project details not found. Cannot approve. Rejecting.");
                          appToProcess.setStatus(ApplicationStatus.UNSUCCESSFUL);
                          applicant.setApplicationStatus(ApplicationStatus.UNSUCCESSFUL);
                          applicationService.saveApplications(applicationService.getAllApplications());
                          return;
                     }
                    FlatTypeDetails details = currentProjectState.getFlatTypeDetails(appliedType); // Use non-mutable getter is fine here

                    if (details == null) {
                        System.out.println("Error: Applied flat type (" + appliedType.getDisplayName()
                                + ") does not exist in this project configuration. Rejecting application.");
                        appToProcess.setStatus(ApplicationStatus.UNSUCCESSFUL);
                        applicant.setApplicationStatus(ApplicationStatus.UNSUCCESSFUL);
                        applicationService.saveApplications(applicationService.getAllApplications());
                        return;
                    }

                    // Check if approving exceeds total units (based on SUCCESSFUL or BOOKED apps)
                    long alreadySuccessfulOrBookedCount = applicationService.getApplicationsByProject(currentProjectState.getProjectName())
                            .stream()
                            .filter(a -> a.getFlatTypeApplied() == appliedType &&
                                    (a.getStatus() == ApplicationStatus.SUCCESSFUL || a.getStatus() == ApplicationStatus.BOOKED))
                            .count();

                    if (alreadySuccessfulOrBookedCount < details.getTotalUnits()) {
                        // Approve: Update application and applicant status
                        appToProcess.setStatus(ApplicationStatus.SUCCESSFUL);
                        applicant.setApplicationStatus(ApplicationStatus.SUCCESSFUL); // Update profile immediately
                        System.out.println("Application Approved (Status: SUCCESSFUL). Applicant can now book via Officer.");
                        applicationService.saveApplications(applicationService.getAllApplications()); // Save change
                        // userService.saveUsers(userService.getAllUsers()); // Optional immediate save of user profile
                    } else {
                        // Cannot approve due to capacity
                        System.out.println("Cannot approve. The number of successful/booked applications (" + alreadySuccessfulOrBookedCount + ") already meets or exceeds the total supply ("
                                + details.getTotalUnits() + ") for " + appliedType.getDisplayName() + ".");
                        System.out.println("Consider rejecting this application or managing existing successful/booked ones.");
                    }

                } else if (action.equals("R")) {
                    // --- Reject Action ---
                    appToProcess.setStatus(ApplicationStatus.UNSUCCESSFUL);
                    applicant.setApplicationStatus(ApplicationStatus.UNSUCCESSFUL); // Update profile immediately
                    applicant.setBookedFlatType(null); // Ensure booked type is cleared if they were somehow booked before
                    System.out.println("Application Rejected (Status: UNSUCCESSFUL).");
                    applicationService.saveApplications(applicationService.getAllApplications()); // Save change
                    // userService.saveUsers(userService.getAllUsers()); // Optional immediate save
                } else {
                    System.out.println("Invalid action ('A' or 'R' expected). No change made.");
                }
            } else if (choice != 0) {
                System.out.println("Invalid choice.");
            }
             // If choice is 0, skip processing
        }

        // --- Display Other Statuses ---
        System.out.println("\n--- Other Application Statuses ---");
        List<BTOApplication> otherApps = projectApplications.stream()
                .filter(app -> app.getStatus() != ApplicationStatus.PENDING)
                .collect(Collectors.toList());

        if (otherApps.isEmpty()) {
             System.out.println("(None)");
        } else {
            otherApps.forEach(app -> {
                User applicant = userService.findUserByNric(app.getApplicantNric());
                System.out.printf("- NRIC: %s | Name: %-15s | Type: %-8s | Status: %s\n",
                        app.getApplicantNric(),
                        applicant != null ? applicant.getName() : "N/A",
                        app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A",
                        app.getStatus());
            });
        }
    }
}
