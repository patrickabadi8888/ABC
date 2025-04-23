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
import Models.HDBOfficer;
import Models.Project;
import Models.User;
import Services.IApplicationService;
import Services.IOfficerRegistrationService;
import Services.IProjectService;
import Services.IUserService;
import Utils.DateUtils;

// Handles Officer actions related to managing flat bookings
public class BookingOfficerController extends BaseController {

    public BookingOfficerController(IUserService userService, IProjectService projectService,
                                   IApplicationService applicationService, IOfficerRegistrationService officerRegistrationService,
                                   User currentUser, Scanner scanner, AuthController authController) {
        super(userService, projectService, applicationService, officerRegistrationService, currentUser, scanner, authController);
    }

    public void manageFlatBooking() {
        if (!(currentUser instanceof HDBOfficer)) return;
        HDBOfficer officer = (HDBOfficer) currentUser;

        // Find the project the officer is currently handling
        Project project = getOfficerHandlingProject(officer); // Use BaseController method

        if (project == null) {
            System.out.println("You need to be handling an active project to manage flat bookings.");
            return;
        }
        String handlingProjectName = project.getProjectName();

        System.out.println("\n--- Flat Booking Management for Project: " + handlingProjectName + " ---");

        // Get applications for this project with SUCCESSFUL status using the service
        List<BTOApplication> successfulApps = applicationService.getApplicationsByProject(handlingProjectName)
                .stream()
                .filter(app -> app.getStatus() == ApplicationStatus.SUCCESSFUL)
                .sorted(Comparator.comparing(app -> app.getApplicationDate())) // Sort by application date (FIFO)
                .collect(Collectors.toList());

        if (successfulApps.isEmpty()) {
            System.out.println("No applicants with status SUCCESSFUL found for this project (ready for booking).");
            return;
        }

        // Display successful applicants for selection
        System.out.println("Applicants with SUCCESSFUL status (ready for booking):");
        for (int i = 0; i < successfulApps.size(); i++) {
            BTOApplication app = successfulApps.get(i);
            User applicantUser = userService.findUserByNric(app.getApplicantNric()); // Find user via service
            System.out.printf("%d. NRIC: %s | Name: %-15s | Applied Type: %-8s | App Date: %s\n",
                    i + 1,
                    app.getApplicantNric(),
                    applicantUser != null ? applicantUser.getName() : "N/A",
                    app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A",
                    DateUtils.formatDate(app.getApplicationDate()));
        }

        // Prompt for selection
        int choice = getIntInput("Enter the number of the applicant to process booking for (or 0 to cancel): ", 0, successfulApps.size());

        if (choice == 0) {
            System.out.println("Operation cancelled.");
            return;
        }

        BTOApplication applicationToBook = successfulApps.get(choice - 1);
        User applicantUser = userService.findUserByNric(applicationToBook.getApplicantNric());

        // Validate applicant data
        if (!(applicantUser instanceof Applicant)) {
            System.out.println(
                    "Error: Applicant data not found or invalid for NRIC " + applicationToBook.getApplicantNric() + ". Cannot process booking.");
            return;
        }
        Applicant applicant = (Applicant) applicantUser;

        // --- Pre-booking Checks ---
        // Re-check application status (in case it changed since listing)
        // Refresh application object from service? Might be overkill if sync is frequent. Check current object's status.
        if (applicationToBook.getStatus() != ApplicationStatus.SUCCESSFUL) {
            System.out.println("Error: Applicant status is no longer SUCCESSFUL (Current: "
                    + applicationToBook.getStatus() + "). Cannot proceed with booking.");
            return;
        }
        // Check applicant profile status (redundant if sync works, but safe)
        if (applicant.hasBooked()) {
            System.out.println("Error: Applicant " + applicant.getNric()
                    + " has already booked a flat according to their profile. Booking cancelled.");
            return;
        }
        // Check flat type applied for
        FlatType appliedFlatType = applicationToBook.getFlatTypeApplied();
        if (appliedFlatType == null) {
            System.out.println("Error: Application record does not have a valid flat type specified. Cannot book.");
            return;
        }
        // Check unit availability using the *mutable* details from the Project object
        // Need to get the project object again as the one from getOfficerHandlingProject might be stale if units changed.
        Project currentProjectState = projectService.findProjectByName(handlingProjectName);
        if (currentProjectState == null) {
             System.out.println("Error: Could not retrieve current project state. Booking cancelled.");
             return;
        }
        FlatTypeDetails details = currentProjectState.getMutableFlatTypeDetails(appliedFlatType);
        if (details == null) {
             System.out.println("Error: Flat type details not found for " + appliedFlatType.getDisplayName() + " in project " + currentProjectState.getProjectName() +". Cannot book.");
             return;
        }
        if (details.getAvailableUnits() <= 0) {
            System.out.println("Error: No available units for the applied flat type ("
                    + appliedFlatType.getDisplayName() + ") at this moment. Booking cannot proceed.");
            // Consider suggesting checking back later or informing manager?
            return;
        }

        // --- Confirmation ---
        System.out.println("\n--- Confirm Booking ---");
        System.out.println("Applicant: " + applicant.getName() + " (" + applicant.getNric() + ")");
        System.out.println("Project: " + applicationToBook.getProjectName());
        System.out.println("Flat Type: " + appliedFlatType.getDisplayName());
        System.out.println("Available Units Before Booking: " + details.getAvailableUnits());
        System.out.printf("Selling Price: $%.2f\n", details.getSellingPrice());

        System.out.print("\nConfirm booking for this applicant? (yes/no): ");
        String confirm = scanner.nextLine().trim().toLowerCase();

        if (confirm.equals("yes")) {
            // --- Process Booking ---
            // 1. Decrement available units in the Project's FlatTypeDetails
            if (!details.decrementAvailableUnits()) {
                // This could happen in a concurrent scenario, or if the check above was somehow bypassed.
                System.out.println(
                        "Error: Failed to decrement unit count (Units might have just become zero). Booking cancelled.");
                return;
            }

            // 2. Update BTOApplication status
            applicationToBook.setStatus(ApplicationStatus.BOOKED);

            // 3. Update Applicant status and booked flat type
            applicant.setApplicationStatus(ApplicationStatus.BOOKED);
            applicant.setBookedFlatType(appliedFlatType);

            // --- Post-booking Actions ---
            System.out.println("Booking confirmed successfully!");
            System.out.println("Applicant status updated to BOOKED.");
            System.out.println("Remaining units for " + appliedFlatType.getDisplayName() + ": " + details.getAvailableUnits());

            // Generate receipt (uses current user NRIC as Officer NRIC)
            generateBookingReceipt(applicant, applicationToBook, currentProjectState); // Pass the up-to-date project state

            // Save updated data
            applicationService.saveApplications(applicationService.getAllApplications());
            projectService.saveProjects(projectService.getAllProjects()); // Save project because unit count changed
            // userService.saveUsers(userService.getAllUsers()); // Save user state change

        } else {
            System.out.println("Booking cancelled.");
        }
    }

    // generateBookingReceipt remains a private helper method within this controller
    private void generateBookingReceipt(Applicant applicant, BTOApplication application, Project project) {
        System.out.println("\n================ BTO Booking Receipt ================");
        System.out.println(" Receipt Generated: " + DateUtils.formatDate(DateUtils.getCurrentDate()) + " by Officer " + currentUser.getNric());
        System.out.println("-----------------------------------------------------");
        System.out.println(" Applicant Details:");
        System.out.println("   Name:          " + applicant.getName());
        System.out.println("   NRIC:          " + applicant.getNric());
        System.out.println("   Age:           " + applicant.getAge());
        System.out.println("   Marital Status:" + applicant.getMaritalStatus());
        System.out.println("-----------------------------------------------------");
        System.out.println(" Booking Details:");
        System.out.println("   Project Name:  " + project.getProjectName());
        System.out.println("   Neighborhood:  " + project.getNeighborhood());
        System.out.println("   Booked Flat:   " + (application.getFlatTypeApplied() != null ? application.getFlatTypeApplied().getDisplayName() : "N/A"));
        // Get price from the project details passed in
        FlatTypeDetails details = project.getFlatTypeDetails(application.getFlatTypeApplied());
        if (details != null) {
            System.out.printf("   Selling Price: $%.2f\n", details.getSellingPrice());
        } else {
            System.out.println("   Selling Price: N/A"); // Should not happen if booking succeeded
        }
        System.out.println("   Booking Status:" + application.getStatus()); // Should be BOOKED
        System.out.println("   Application ID:" + application.getApplicationId());
        System.out.println("-----------------------------------------------------");
        System.out.println(" Thank you for choosing HDB!");
        System.out.println("=====================================================");
    }
}
