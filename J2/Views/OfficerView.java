package Views;

import Controllers.OfficerController;
import Interfaces.Services.IAuthService; // Needed for BaseView
import Interfaces.Services.IFilterService; // Needed for BaseView
import Interfaces.Services.IEligibilityService; // Needed to display handling project
import Models.HDBOfficer;
import Models.Project;
import Models.User;

import java.util.Scanner;

public class OfficerView extends BaseView {
    private final OfficerController officerController;
    private final IEligibilityService eligibilityService; // Inject service needed for display

    public OfficerView(Scanner scanner, User currentUser, OfficerController controller,
                       IAuthService authService, IFilterService filterService,
                       IEligibilityService eligibilityService) { // Inject eligibility service
        super(scanner, currentUser, authService, filterService); // Pass base services
        this.officerController = controller;
        this.eligibilityService = eligibilityService; // Store eligibility service
    }

    @Override
    public void displayMenu() {
        boolean logout = false;
        while (!logout) {
            System.out.println("\n=========== HDB Officer Menu ===========");
            System.out.println("Welcome, Officer " + currentUser.getName() + "!");

            // Display currently handling project using injected service
            Project handlingProject = eligibilityService.getOfficerHandlingProject((HDBOfficer)currentUser);
            if (handlingProject != null) {
                 System.out.println("--> Currently Handling Project: " + handlingProject.getProjectName() + " <--");
            } else {
                 System.out.println("--> Not currently handling any project <--");
            }

            System.out.println("--- Officer Actions ---");
            System.out.println(" 1. Register to Handle Project");
            System.out.println(" 2. View My Registration Status");
            System.out.println(" 3. View Handling Project Details");
            System.out.println(" 4. View/Reply Enquiries (Handling Project)");
            System.out.println(" 5. Manage Flat Booking (Process Successful Applicants)");
            System.out.println("--- Applicant Actions (Inherited) ---");
            System.out.println(" 6. View Available BTO Projects");
            System.out.println(" 7. Apply for BTO Project");
            System.out.println(" 8. View My Application Status");
            System.out.println(" 9. Request Application Withdrawal");
            System.out.println("10. Submit Enquiry");
            System.out.println("11. View My Enquiries");
            System.out.println("12. Edit My Enquiry");
            System.out.println("13. Delete My Enquiry");
            System.out.println("--- Common Actions ---");
            System.out.println("14. Apply/Clear Project Filters");
            System.out.println("15. Change Password");
            System.out.println(" 0. Logout");
            System.out.println("========================================");

            int choice = getMenuChoice(0, 15); // Use BaseView method

            switch (choice) {
                // Officer Actions
                case 1: officerController.registerForProject(); break;
                case 2: officerController.viewRegistrationStatus(); break;
                case 3: officerController.viewHandlingProjectDetails(); break;
                case 4: officerController.viewAndReplyToEnquiries(); break;
                case 5: officerController.manageFlatBooking(); break;
                // Applicant Actions (Inherited - OfficerController extends ApplicantController)
                case 6: officerController.viewOpenProjects(); break;
                case 7: officerController.applyForProject(); break;
                case 8: officerController.viewMyApplication(); break;
                case 9: officerController.requestWithdrawal(); break;
                case 10: officerController.submitEnquiry(); break;
                case 11: officerController.viewMyEnquiries(); break;
                case 12: officerController.editMyEnquiry(); break;
                case 13: officerController.deleteMyEnquiry(); break;
                // Common Actions
                case 14: applyFilters(); break; // Call BaseView method
                case 15:
                    if (changePassword()) { // Call BaseView method
                        logout = true; // Log out after successful password change
                    }
                    break;
                case 0:
                    logout = true;
                    System.out.println("Logging out...");
                    break;
                default: System.out.println("Invalid choice."); break;
            }
             if (!logout && choice != 0) {
                 pause(); // Use BaseView pause method
             }
        }
    }
}
