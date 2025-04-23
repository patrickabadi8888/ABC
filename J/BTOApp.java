import java.util.List;
import java.util.Map;
import java.util.Scanner;

import Models.User;
import Models.Project;
import Models.BTOApplication;
import Models.Enquiry;
import Models.OfficerRegistration;

import Controllers.AuthController;
import Controllers.ApplicantController;
import Controllers.OfficerController;
import Controllers.ManagerController;
import Controllers.BaseController;

import Views.ApplicantView;
import Views.BaseView;
import Views.OfficerView;
import Views.ManagerView;
import Services.ApplicationService;
import Services.DataService;
import Services.EnquiryService;
import Services.OfficerRegistrationService;
import Services.ProjectService;
public class BTOApp {

    private Map<String, User> users;
    private List<Project> projects;
    private Map<String, BTOApplication> applications;
    private List<Enquiry> enquiries;
    private Map<String, OfficerRegistration> officerRegistrations;

    private AuthController authController;
    private Scanner scanner;

    public BTOApp() {
        scanner = new Scanner(System.in);
    }

    public void initialize() {
        System.out.println("Initializing BTO Management System...");
        users = DataService.loadUsers();
        projects = ProjectService.loadProjects(users);
        applications = ApplicationService.loadApplications(projects);
        enquiries = EnquiryService.loadEnquiries();
        officerRegistrations = OfficerRegistrationService.loadOfficerRegistrations(users, projects);

        DataService.synchronizeData(users, projects, applications, officerRegistrations);

        authController = new AuthController(users);
        System.out.println("Initialization complete. System ready.");
    }

    public void run() {
        User currentUser = null;
        while (true) {
             if (this.users != null && this.projects != null && this.applications != null && this.officerRegistrations != null) {
                DataService.synchronizeData(users, projects, applications, officerRegistrations);
             } else {
                  System.err.println("Warning: Data not fully loaded, skipping pre-login sync.");
             }

            currentUser = loginScreen();
            if (currentUser != null) {
                showRoleMenu(currentUser);
                currentUser = null;
                System.out.println("\nReturning to Login Screen...");
            } else {
                System.out.print("Login failed. Try again? (yes/no): ");
                String retry = scanner.nextLine().trim().toLowerCase();
                if (!retry.equals("yes")) {
                    break;
                }
            }
        }
        System.out.println("Exiting application.");
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
        BaseController controller;

        switch (user.getRole()) {
            case APPLICANT:
                ApplicantController appController = new ApplicantController(users, projects, applications, enquiries, officerRegistrations, user, scanner, authController);
                controller = appController;
                view = new ApplicantView(scanner, user, appController, authController);
                break;
            case HDB_OFFICER:
                 OfficerController offController = new OfficerController(users, projects, applications, enquiries, officerRegistrations, user, scanner, authController);
                 controller = offController;
                 view = new OfficerView(scanner, user, offController, authController);
                break;
            case HDB_MANAGER:
                 ManagerController manController = new ManagerController(users, projects, applications, enquiries, officerRegistrations, user, scanner, authController);
                 controller = manController;
                 view = new ManagerView(scanner, user, manController, authController);
                break;
            default:
                System.err.println("FATAL Error: Unknown user role encountered: " + user.getRole());
                return;
        }
        view.displayMenu();
    }

    public void shutdown() {
        System.out.println("\nShutting down BTO Management System...");
        if (scanner != null) {
            try {
                scanner.close();
                 System.out.println("Scanner closed.");
            } catch (IllegalStateException e) {
            }
        }
        System.out.println("System shutdown complete.");
    }


    public static void main(String[] args) {
        BTOApp app = new BTOApp();
        try {
            Runtime.getRuntime().addShutdownHook(new Thread(app::shutdown, "Shutdown-Thread"));


            app.initialize();

            app.run();

        } catch (Exception e) {
             System.err.println("An unexpected critical error occurred in the main application thread: " + e.getMessage());
             e.printStackTrace();
        }
         System.exit(0);
    }
}