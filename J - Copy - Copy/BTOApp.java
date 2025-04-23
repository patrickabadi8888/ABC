import java.util.Scanner;

import Models.User;

import Controllers.*; // Import all controllers
import Services.*; // Import all services (including interfaces)

import Views.ApplicantView;
import Views.BaseView;
import Views.OfficerView;
import Views.ManagerView;

public class BTOApp {

    // Service Instances
    private IUserService userService;
    private IProjectService projectService;
    private IApplicationService applicationService;
    private IEnquiryService enquiryService;
    private IOfficerRegistrationService officerRegistrationService;

    // AuthController and Scanner
    private AuthController authController;
    private Scanner scanner;

    public BTOApp() {
        scanner = new Scanner(System.in);
        // Instantiate services
        userService = new UserService();
        projectService = new ProjectService();
        applicationService = new ApplicationService();
        enquiryService = new EnquiryService();
        officerRegistrationService = new OfficerRegistrationService();
    }

    public void initialize() {
        System.out.println("Initializing BTO Management System...");

        // Load data using services
        // Pass projects to loadApplications for unit adjustments
        // Pass users and projects for validation during registration load

        // Perform initial data synchronization
        DataService.synchronizeData(userService, projectService, applicationService, officerRegistrationService);

        // Initialize AuthController with the user service
        authController = new AuthController(userService);

        System.out.println("Initialization complete. System ready.");
    }

    public void run() {
        User currentUser = null;
        while (true) {
             // Synchronize data before each menu display iteration
             // This ensures controllers operate on the latest consistent state
             DataService.synchronizeData(userService, projectService, applicationService, officerRegistrationService);

            currentUser = loginScreen(); // Attempt login

            if (currentUser != null) {
                // User logged in successfully, show the appropriate menu
                showRoleMenu(currentUser);
                // After menu loop finishes (logout), reset currentUser
                currentUser = null;
                System.out.println("\nReturning to Login Screen...");
            } else {
                // Login failed
                System.out.print("Login failed. Try again? (yes/no): ");
                String retry = scanner.nextLine().trim().toLowerCase();
                if (!retry.equals("yes")) {
                    break; // Exit the main loop if user doesn't want to retry
                }
            }
        }
        // Save all data on exit
        System.out.println("Exiting application and saving data...");
        DataService.saveAllData(userService, projectService, applicationService, enquiryService, officerRegistrationService);
        System.out.println("Exiting complete.");
    }

    private User loginScreen() {
        System.out.println("\n--- BTO Management System Login ---");
        System.out.print("Enter NRIC: ");
        String nric = scanner.nextLine().trim().toUpperCase();
        System.out.print("Enter Password: ");
        String password = scanner.nextLine(); // Read password

        // Perform login using AuthController
        User user = authController.login(nric, password);
        if (user != null) {
            System.out.println("Login successful! Welcome, " + user.getName() + " (" + user.getRole() + ")");
        }
        // Return the user object (null if login failed)
        return user;
    }

    // Show menu based on User Role
    private void showRoleMenu(User user) {
        BaseView view; // The view to display
        // No longer need a single BaseController instance here, as views take specific controllers

        switch (user.getRole()) {
            case APPLICANT:
                // Instantiate ApplicantController (which holds its sub-controllers)
                ApplicantController appController = new ApplicantController(
                        userService, projectService, applicationService, officerRegistrationService, enquiryService,
                        user, scanner, authController);
                // Pass the main ApplicantController to the ApplicantView
                view = new ApplicantView(scanner, user, appController, authController);
                break;
            case HDB_OFFICER:
                // Instantiate OfficerController (which holds its sub-controllers and inherits from ApplicantController)
                 OfficerController offController = new OfficerController(
                         userService, projectService, applicationService, officerRegistrationService, enquiryService,
                         user, scanner, authController);
                 // Pass the main OfficerController to the OfficerView
                 view = new OfficerView(scanner, user, offController, authController);
                break;
            case HDB_MANAGER:
                // Instantiate ManagerController (which holds its sub-controllers)
                 ManagerController manController = new ManagerController(
                         userService, projectService, applicationService, officerRegistrationService, enquiryService,
                         user, scanner, authController);
                 // Pass the main ManagerController to the ManagerView
                 view = new ManagerView(scanner, user, manController, authController);
                break;
            default:
                // Should not happen with defined roles
                System.err.println("FATAL Error: Unknown user role encountered: " + user.getRole());
                return; // Exit this method if role is unknown
        }
        // Display the menu using the selected view
        view.displayMenu();
    }

    public static void main(String[] args) {
        BTOApp app = new BTOApp();
        try {
            app.initialize(); // Load data and set up services
            app.run();        // Start the login and menu loop
        } catch (Exception e) {
             // Catch unexpected errors in the main flow
             System.err.println("An unexpected critical error occurred in the main application thread: " + e.getMessage());
             e.printStackTrace();
             // Optionally save data here as well in case of crash?
             // DataService.saveAllData(...);
        } finally {
             // Ensure scanner is closed if necessary, though System.in usually isn't closed.
             app.scanner.close();
        }
         System.exit(0); // Ensure application exits cleanly
    }
}
