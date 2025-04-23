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


// Handles Manager actions related to Withdrawal Requests
public class WithdrawalManagerController extends BaseController {

    public WithdrawalManagerController(IUserService userService, IProjectService projectService,
                                   IApplicationService applicationService, IOfficerRegistrationService officerRegistrationService,
                                   IEnquiryService enquiryService,
                                   User currentUser, Scanner scanner, AuthController authController) {
        super(userService, projectService, applicationService, officerRegistrationService, currentUser, scanner, authController);
        if (!(currentUser instanceof HDBManager)) {
            throw new IllegalArgumentException("WithdrawalManagerController requires an HDBManager user.");
        }
    }

     public void manageWithdrawalRequests() {
        System.out.println("\n--- Manage Withdrawal Requests ---");
        // Get names of projects managed by this manager
        List<String> myProjectNames = projectService.getProjectsManagedBy(currentUser.getNric())
                .stream()
                .map(Project::getProjectName)
                .collect(Collectors.toList());

        if (myProjectNames.isEmpty()) {
            System.out.println("You are not managing any projects to have withdrawal requests.");
            return;
        }

        // Find PENDING_WITHDRAWAL applications for the managed projects
        List<BTOApplication> pendingWithdrawals = applicationService.getAllApplications().values().stream()
                .filter(app -> app.getStatus() == ApplicationStatus.PENDING_WITHDRAWAL)
                .filter(app -> myProjectNames.contains(app.getProjectName())) // Filter by managed projects
                .sorted(Comparator.comparing(BTOApplication::getApplicationDate)) // Sort by date
                .collect(Collectors.toList());

        if (pendingWithdrawals.isEmpty()) {
            System.out.println("No pending withdrawal requests found for the projects you manage.");
            return;
        }

        // --- Display Pending Withdrawals ---
        System.out.println("--- Pending Withdrawal Requests ---");
        for (int i = 0; i < pendingWithdrawals.size(); i++) {
            BTOApplication app = pendingWithdrawals.get(i);
            User applicantUser = userService.findUserByNric(app.getApplicantNric()); // Get applicant info

            // Determine the status *before* withdrawal request was made
            ApplicationStatus statusBefore = app.getStatusBeforeWithdrawal();
            if (statusBefore == null) {
                 // statusBeforeWithdrawal should be set when status becomes PENDING_WITHDRAWAL
                 // If it's null here, it's an inconsistency, but we can try to infer.
                 statusBefore = inferStatusBeforeWithdrawal(app, (applicantUser instanceof Applicant) ? (Applicant) applicantUser : null);
                 System.out.print(" (Inferred Original: " + statusBefore + ")");
            } else {
                System.out.print(" (Original: " + statusBefore + ")");
            }

            // Print application details
            System.out.printf("\n%d. NRIC: %s | Name: %-15s | Project: %-15s | Type: %-8s | App Date: %s",
                    i + 1,
                    app.getApplicantNric(),
                    applicantUser != null ? applicantUser.getName() : "N/A",
                    app.getProjectName(),
                    app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A",
                    DateUtils.formatDate(app.getApplicationDate()));
            System.out.println(); // Newline after printing details
        }

        // Prompt for action
        int choice = getIntInput("Enter number to Approve/Reject withdrawal (or 0 to skip): ", 0, pendingWithdrawals.size());

        if (choice >= 1) {
            BTOApplication appToProcess = pendingWithdrawals.get(choice - 1);
            User applicantUser = userService.findUserByNric(appToProcess.getApplicantNric());

            // Validate Applicant
            if (!(applicantUser instanceof Applicant)) {
                System.out.println("Error: Applicant data not found or invalid for NRIC "
                        + appToProcess.getApplicantNric() + ". Cannot process withdrawal.");
                return;
            }
            Applicant applicant = (Applicant) applicantUser;

            // Validate Project
            Project project = projectService.findProjectByName(appToProcess.getProjectName());
            if (project == null) {
                System.out.println("Error: Project data not found for application "
                        + appToProcess.getApplicationId() + ". Cannot process withdrawal.");
                return;
            }

            // Determine original status (use stored value if available, otherwise infer)
            ApplicationStatus originalStatus = appToProcess.getStatusBeforeWithdrawal();
            if (originalStatus == null) {
                originalStatus = inferStatusBeforeWithdrawal(appToProcess, applicant);
                 System.out.println("Note: Original status inferred as " + originalStatus + " due to missing data.");
            }

             // Double check current status is still PENDING_WITHDRAWAL
             if (appToProcess.getStatus() != ApplicationStatus.PENDING_WITHDRAWAL) {
                  System.out.println("Error: Application status is no longer PENDING_WITHDRAWAL (Current: " + appToProcess.getStatus() + "). Cannot process.");
                  return;
             }


            // Prompt for Approve/Reject
            System.out.print("Approve or Reject withdrawal request for Applicant " + applicant.getName() + "? (A/R): ");
            String action = scanner.nextLine().trim().toUpperCase();

            if (action.equals("A")) {
                // --- Approve Withdrawal ---
                ApplicationStatus finalStatus;
                boolean releasedUnit = false;

                // Determine final status based on original status
                if (originalStatus == ApplicationStatus.BOOKED) {
                    finalStatus = ApplicationStatus.UNSUCCESSFUL; // Penalize booked withdrawal
                    FlatType bookedType = appToProcess.getFlatTypeApplied(); // Type that was booked
                    if (bookedType != null) {
                        FlatTypeDetails details = project.getMutableFlatTypeDetails(bookedType); // Get mutable details
                        if (details != null) {
                            // Increment available units for the released flat
                            if (details.incrementAvailableUnits()) {
                                releasedUnit = true;
                                System.out.println("Unit for " + bookedType.getDisplayName()
                                        + " released back to project " + project.getProjectName() + ". Available: " + details.getAvailableUnits());
                            } else {
                                // Should not happen if units were correctly decremented on booking
                                System.err.println("Error: Could not increment available units for " + bookedType.getDisplayName() + " (already at max?). Check data consistency.");
                            }
                        } else {
                            System.err.println("Error: Could not find flat details for " + bookedType.getDisplayName() + " during withdrawal approval.");
                        }
                    } else {
                        System.err.println("Error: Cannot determine booked flat type to release unit during withdrawal approval.");
                    }
                } else if (originalStatus == ApplicationStatus.SUCCESSFUL) {
                    finalStatus = ApplicationStatus.UNSUCCESSFUL; // Penalize successful withdrawal
                } else { // Original was PENDING or unknown/inferred as PENDING
                    finalStatus = ApplicationStatus.WITHDRAWN; // No penalty, just withdrawn
                }

                // Update application status
                appToProcess.setStatus(finalStatus); // This also clears statusBeforeWithdrawal

                // Update applicant profile
                applicant.setApplicationStatus(finalStatus);
                applicant.setBookedFlatType(null); // Clear booked type regardless of original status

                System.out.println("Withdrawal request Approved. Application status set to " + finalStatus + ".");

                // Save changes
                applicationService.saveApplications(applicationService.getAllApplications());
                if (releasedUnit) {
                    projectService.saveProjects(projectService.getAllProjects()); // Save project if unit was released
                }
                // userService.saveUsers(userService.getAllUsers()); // Save user profile change

            } else if (action.equals("R")) {
                // --- Reject Withdrawal ---
                // Revert application status to original status
                appToProcess.setStatus(originalStatus); // This clears statusBeforeWithdrawal

                // Revert applicant profile status
                applicant.setApplicationStatus(originalStatus);
                // Note: We don't need to reset bookedFlatType here, as it wouldn't have been cleared yet.

                System.out.println("Withdrawal request Rejected. Application status reverted to " + originalStatus + ".");
                applicationService.saveApplications(applicationService.getAllApplications()); // Save the reverted status
                // userService.saveUsers(userService.getAllUsers()); // Save reverted user status

            } else {
                System.out.println("Invalid action ('A' or 'R' expected). No change made.");
            }
        } else if (choice != 0) {
            System.out.println("Invalid choice.");
        }
         // If choice is 0, skip processing
    }

     // Helper to infer original status if statusBeforeWithdrawal wasn't set correctly
    private ApplicationStatus inferStatusBeforeWithdrawal(BTOApplication app, Applicant applicant) {
         // If applicant profile shows BOOKED and the application matches the flat type, assume BOOKED.
         if (applicant != null && applicant.hasBooked() && applicant.getBookedFlatType() == app.getFlatTypeApplied()) {
             return ApplicationStatus.BOOKED;
         }
         // If applicant profile shows SUCCESSFUL for this project, assume SUCCESSFUL.
         // (Checking project name might be needed if applicant could have multiple non-booked apps somehow)
         else if (applicant != null && applicant.getApplicationStatus() == ApplicationStatus.SUCCESSFUL && applicant.getAppliedProjectName().equals(app.getProjectName())) {
              return ApplicationStatus.SUCCESSFUL;
         }
         // If the application itself has a flat type (likely from PENDING or SUCCESSFUL state), lean towards SUCCESSFUL as the most likely state before withdrawal if not BOOKED.
         else if (app.getFlatTypeApplied() != null) {
              // This is ambiguous. Could have been PENDING or SUCCESSFUL.
              // Let's default to SUCCESSFUL if a flat type exists, assuming approval happened.
              // This matches the old logic.
              return ApplicationStatus.SUCCESSFUL;
         }
         // Default fallback: assume it was PENDING.
         return ApplicationStatus.PENDING;
    }
}
