import java.util.List;
import java.util.Map;
import java.util.Scanner;

// Models
import Models.User;
import Models.Project;
import Models.BTOApplication;
import Models.Enquiry;
import Models.OfficerRegistration;

// Controllers
import Controllers.ApplicantController;
import Controllers.OfficerController;
import Controllers.ManagerController;

// Views
import Views.ApplicantView;
import Views.BaseView;
import Views.OfficerView;
import Views.ManagerView;

// Services (Concrete Implementations)
import Services.ApplicationService;
import Services.AuthService;
import Services.DataSynchronizationService;
import Services.EligibilityService;
import Services.EnquiryService;
import Services.FilterService;
import Services.OfficerRegistrationService;
import Services.ProjectDisplayService;
import Services.ProjectService;
import Services.ReportService;

// Repositories (Concrete Implementations)
import Repositories.CsvApplicationRepository;
import Repositories.CsvEnquiryRepository;
import Repositories.CsvOfficerRegistrationRepository;
import Repositories.CsvProjectRepository;
import Repositories.CsvUserRepository;

// Interfaces
import Interfaces.Repositories.*;
import Interfaces.Services.*;

public class BTOApp {

    // Repositories (using Interfaces)
    private IUserRepository userRepository;
    private IProjectRepository projectRepository;
    private IApplicationRepository applicationRepository;
    private IEnquiryRepository enquiryRepository;
    private IOfficerRegistrationRepository officerRegistrationRepository;

    // Services (using Interfaces)
    private IAuthService authService;
    private IFilterService filterService;
    private IEligibilityService eligibilityService;
    private IProjectService projectService;
    private IApplicationService applicationService;
    private IOfficerRegistrationService officerRegService;
    private IEnquiryService enquiryService;
    private IProjectDisplayService projectDisplayService;
    private IReportService reportService;
    private IDataSynchronizationService dataSyncService;

    private Scanner scanner;

    public BTOApp() {
        scanner = new Scanner(System.in);
    }

    public void initialize() {
        System.out.println("Initializing BTO Management System...");

        // --- Instantiate Concrete Repositories ---
        userRepository = new CsvUserRepository();
        projectRepository = new CsvProjectRepository();
        applicationRepository = new CsvApplicationRepository();
        enquiryRepository = new CsvEnquiryRepository();
        officerRegistrationRepository = new CsvOfficerRegistrationRepository();

        // --- Load Initial Data (Repositories handle loading) ---
        // Trigger initial load by accessing getAll methods or specific load methods
        userRepository.getAllUsers();
        projectRepository.getAllProjects();
        applicationRepository.getAllApplications();
        enquiryRepository.getAllEnquiries();
        officerRegistrationRepository.getAllRegistrations();

        // --- Instantiate Concrete Services (Injecting Dependencies) ---
        // Services that only need their own repository
        authService = new AuthService(userRepository);
        filterService = new FilterService(); // No repository needed

        // Services needing multiple repositories/services
        eligibilityService = new EligibilityService(userRepository, officerRegistrationRepository, projectRepository);
        enquiryService = new EnquiryService(enquiryRepository); // Needs only its repo for basic ops
        applicationService = new ApplicationService(applicationRepository, projectRepository, userRepository);
        officerRegService = new OfficerRegistrationService(officerRegistrationRepository, projectRepository, eligibilityService);
        projectService = new ProjectService(projectRepository, eligibilityService, filterService, applicationService, officerRegService, enquiryService);
        projectDisplayService = new ProjectDisplayService(filterService, eligibilityService);
        reportService = new ReportService(applicationRepository, userRepository);
        dataSyncService = new DataSynchronizationService(userRepository, projectRepository, applicationRepository, officerRegistrationRepository, applicationService);

        // --- Perform Initial Data Synchronization ---
        dataSyncService.synchronizeAllData();

        System.out.println("Initialization complete. System ready.");
    }

    public void run() {
        User currentUser = null;
        while (true) {
             // Optional: Re-synchronize data before each login? Might be overkill.
             // dataSyncService.synchronizeAllData();

            currentUser = loginScreen();
            if (currentUser != null) {
                showRoleMenu(currentUser);
                currentUser = null; // Clear user on logout
                System.out.println("\nReturning to Login Screen...");
            } else {
                // Login failed message handled by authService
                System.out.print("Try again? (yes/no): ");
                String retry = scanner.nextLine().trim().toLowerCase();
                if (!retry.equals("yes")) {
                    break; // Exit loop if user doesn't want to retry
                }
            }
        }
        System.out.println("Exiting application.");
        // Optional: Save all data on exit? Repositories save on modification now.
    }

    private User loginScreen() {
        System.out.println("\n--- BTO Management System Login ---");
        System.out.print("Enter NRIC: ");
        String nric = scanner.nextLine(); // Let AuthService handle trimming/casing
        System.out.print("Enter Password: ");
        String password = scanner.nextLine();

        User user = authService.login(nric, password);
        if (user != null) {
            System.out.println("Login successful! Welcome, " + user.getName() + " (" + user.getRole() + ")");
        }
        // Error messages (invalid NRIC, wrong password, not found) handled by AuthService
        return user;
    }

    private void showRoleMenu(User user) {
        BaseView view;

        // Instantiate Controllers with necessary services
        switch (user.getRole()) {
            case APPLICANT:
                ApplicantController appController = new ApplicantController(scanner, user, authService,
                        projectService, applicationService, enquiryService, eligibilityService,
                        filterService, projectDisplayService, officerRegService);
                // Instantiate View with Controller and services needed by BaseView
                view = new ApplicantView(scanner, user, appController, authService, filterService);
                break;
            case HDB_OFFICER:
                 OfficerController offController = new OfficerController(scanner, user, authService,
                         projectService, applicationService, enquiryService, eligibilityService,
                         filterService, projectDisplayService, officerRegService, userRepository); // Pass user repo if needed
                 // Instantiate View with Controller and services needed by BaseView + OfficerView specific
                 view = new OfficerView(scanner, user, offController, authService, filterService, eligibilityService);
                break;
            case HDB_MANAGER:
                 ManagerController manController = new ManagerController(scanner, user, authService,
                         projectService, applicationService, enquiryService, eligibilityService,
                         filterService, projectDisplayService, officerRegService, reportService, userRepository);
                 // Instantiate View with Controller and services needed by BaseView
                 view = new ManagerView(scanner, user, manController, authService, filterService);
                break;
            default:
                System.err.println("FATAL Error: Unknown user role encountered: " + user.getRole());
                return; // Exit method if role is unknown
        }
        // Display the menu for the selected role
        view.displayMenu();
    }

    public static void main(String[] args) {
        BTOApp app = new BTOApp();
        try {
            app.initialize();
            app.run();
        } catch (Exception e) {
             // Catch unexpected errors during initialization or run
             System.err.println("\n!!! An unexpected critical error occurred: " + e.getMessage() + " !!!");
             e.printStackTrace(); // Print stack trace for debugging
             System.err.println("Application will now exit.");
        } finally {
            // Ensure scanner is closed if needed, though System.in usually isn't closed.
            // if (app.scanner != null) {
            //     app.scanner.close();
            // }
        }
         System.exit(1); // Exit with error code if exception occurred, 0 otherwise (handled by run loop exit)
    }
}
