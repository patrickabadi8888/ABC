import java.util.Scanner;

import Models.User;

import Controllers.*;
import Services.*;

import Views.ApplicantView;
import Views.BaseView;
import Views.OfficerView;
import Views.ManagerView;

public class BTOApp {

    // ... (service declarations remain the same) ...
    private IUserService userService;
    private IProjectService projectService;
    private IApplicationService applicationService;
    private IEnquiryService enquiryService;
    private IOfficerRegistrationService officerRegistrationService;

    private AuthController authController;
    private Scanner scanner;

    public BTOApp() {
        scanner = new Scanner(System.in);
        // Instantiate services here
        userService = new UserService();
        projectService = new ProjectService();
        applicationService = new ApplicationService();
        enquiryService = new EnquiryService();
        officerRegistrationService = new OfficerRegistrationService();
    }

    public void initialize() {
        System.out.println("Initializing BTO Management System...");

        // --- Load Data ---
        // Load users first (needed by others)
        System.out.println("Loading users...");
        userService.loadUsers(); // Loads data into the userService instance

        // Load projects (needs users for validation)
        System.out.println("Loading projects...");
        projectService.loadProjects(userService.getAllUsers()); // Loads data into projectService

        // Load applications (needs projects for unit adjustment/validation)
        System.out.println("Loading applications...");
        applicationService.loadApplications(projectService.getAllProjects()); // Loads data into applicationService

        // Load officer registrations (needs users and projects for validation)
        System.out.println("Loading officer registrations...");
        officerRegistrationService.loadOfficerRegistrations(userService.getAllUsers(), projectService.getAllProjects()); // Loads data into officerRegService

        // Load enquiries (no explicit dependencies listed for loading)
        System.out.println("Loading enquiries...");
        enquiryService.loadEnquiries(); // Loads data into enquiryService

        // --- Synchronize Data (Optional cross-checks/updates after loading) ---
        System.out.println("Performing data synchronization...");
        DataService.synchronizeData(userService, projectService, applicationService, officerRegistrationService);

        // --- Initialize Authentication ---
        // AuthController needs userService, which should now be populated
        authController = new AuthController(userService);

        System.out.println("Initialization complete. System ready.");
    }

    // ... (run(), loginScreen(), showRoleMenu(), main() remain the same) ...
     public void run() {
        User currentUser = null;
        while (true) {
            // Synchronization before *each* login might be excessive,
            // but can help if data files are modified externally.
            // Consider if sync is only needed after specific actions or at start/end.
            // For now, keeping it as it was.
            DataService.synchronizeData(userService, projectService, applicationService, officerRegistrationService);

            currentUser = loginScreen();

            if (currentUser != null) {
                showRoleMenu(currentUser);
                // Reset user and filters after logout
                currentUser = null;
                // Resetting filters might be desired depending on requirements
                // Example: if BaseController had a resetFilters() method:
                // applicantController.resetFilters(); // Assuming controllers exist
                // officerController.resetFilters();
                // managerController.resetFilters();
                System.out.println("\nReturning to Login Screen...");
            } else {
                System.out.print("Login failed. Try again? (yes/no): ");
                String retry = scanner.nextLine().trim().toLowerCase();
                if (!retry.equals("yes")) {
                    break;
                }
            }
        }
    }

    private User loginScreen() {
        System.out.println("\n--- BTO Management System Login ---");
        System.out.print("Enter NRIC: ");
        String nric = scanner.nextLine().trim().toUpperCase();
        System.out.print("Enter Password: ");
        String password = scanner.nextLine();

        User user = authController.login(nric, password);
        if (user != null) {
            System.out.println("Login successful! Welcome, " + user.getName() + " (" + user.getRole() + ")");
        }
        return user;
    }

    private void showRoleMenu(User user) {
        BaseView view;
        // Create controllers *inside* this method or pass them down,
        // ensuring they use the *current* logged-in user.
        // The current structure creates controllers here, which is fine.

        switch (user.getRole()) {
            case APPLICANT:
                ApplicantController appController = new ApplicantController(
                        userService, projectService, applicationService, officerRegistrationService, enquiryService,
                        user, scanner, authController);
                view = new ApplicantView(scanner, user, appController, authController);
                break;
            case HDB_OFFICER:
                OfficerController offController = new OfficerController(
                        userService, projectService, applicationService, officerRegistrationService, enquiryService,
                        user, scanner, authController);
                view = new OfficerView(scanner, user, offController, authController);
                break;
            case HDB_MANAGER:
                ManagerController manController = new ManagerController(
                        userService, projectService, applicationService, officerRegistrationService, enquiryService,
                        user, scanner, authController);
                view = new ManagerView(scanner, user, manController, authController);
                break;
            default:
                System.err.println("FATAL Error: Unknown user role encountered: " + user.getRole());
                return; // Exit if role is unknown
        }
        view.displayMenu(); // Display the menu for the logged-in user
    }

     public static void main(String[] args) {
        BTOApp app = new BTOApp();
        try {
            app.initialize(); // Initialize loads data
            app.run(); // Run handles login loop and menus
        } catch (Exception e) {
            System.err.println("An unexpected error occurred: " + e.getMessage());
            e.printStackTrace(); // Print stack trace for debugging
            // Attempt to save data even if an error occurred during run()
        } finally {
             // Ensure scanner is closed
             if (app.scanner != null) {
                 app.scanner.close();
             }
        }
        System.out.println("Application terminated.");
        System.exit(1); // Exit with a non-zero code to indicate an issue occurred if caught exception
    }
}