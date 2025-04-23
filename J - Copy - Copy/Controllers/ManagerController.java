package Controllers;

import java.util.Scanner;
import Models.User;
import Services.IApplicationService;
import Services.IEnquiryService;
import Services.IOfficerRegistrationService;
import Services.IProjectService;
import Services.IUserService;

// Main controller for Manager role, delegates actions to specific controllers
public class ManagerController extends BaseController {

    // Hold instances of the specialized controllers
    private final ProjectManagerController projectManagerController;
    private final OfficerRegistrationManagerController officerRegManagerController;
    private final ApplicationManagerController applicationManagerController;
    private final WithdrawalManagerController withdrawalManagerController;
    private final ReportManagerController reportManagerController;
    private final EnquiryManagerController enquiryManagerController;

    public ManagerController(IUserService userService, IProjectService projectService,
                             IApplicationService applicationService, IOfficerRegistrationService officerRegistrationService,
                             IEnquiryService enquiryService, // Enquiry service needed by multiple sub-controllers
                             User currentUser, Scanner scanner, AuthController authController) {
        super(userService, projectService, applicationService, officerRegistrationService, currentUser, scanner, authController);

        // Instantiate the specialized controllers, passing necessary dependencies
        this.projectManagerController = new ProjectManagerController(userService, projectService, applicationService, officerRegistrationService, enquiryService, currentUser, scanner, authController);
        this.officerRegManagerController = new OfficerRegistrationManagerController(userService, projectService, applicationService, officerRegistrationService, enquiryService, currentUser, scanner, authController);
        this.applicationManagerController = new ApplicationManagerController(userService, projectService, applicationService, officerRegistrationService, enquiryService, currentUser, scanner, authController);
        this.withdrawalManagerController = new WithdrawalManagerController(userService, projectService, applicationService, officerRegistrationService, enquiryService, currentUser, scanner, authController);
        this.reportManagerController = new ReportManagerController(userService, projectService, applicationService, officerRegistrationService, enquiryService, currentUser, scanner, authController);
        this.enquiryManagerController = new EnquiryManagerController(userService, projectService, applicationService, officerRegistrationService, enquiryService, currentUser, scanner, authController);

         // Propagate filters if needed (though BaseController handles filter application)
         // this.projectManagerController.filterFlatType = this.filterFlatType;
         // ... etc for other controllers if they use filters directly ...
    }

    // --- Delegate methods to specialized controllers ---

    public void createProject() {
        projectManagerController.createProject();
    }

    public void editProject() {
        projectManagerController.editProject();
    }

    public void deleteProject() {
        projectManagerController.deleteProject();
    }

    public void toggleProjectVisibility() {
        projectManagerController.toggleProjectVisibility();
    }

    public void viewAllProjects() {
        projectManagerController.viewAllProjects();
    }

    public void viewMyProjects() {
        projectManagerController.viewMyProjects();
    }

    public void manageOfficerRegistrations() {
        officerRegManagerController.manageOfficerRegistrations();
    }

    public void manageApplications() {
        applicationManagerController.manageApplications();
    }

    public void manageWithdrawalRequests() {
        withdrawalManagerController.manageWithdrawalRequests();
    }

    public void generateApplicantReport() {
        reportManagerController.generateApplicantReport();
    }

    public void viewAllEnquiries() {
        enquiryManagerController.viewAllEnquiries();
    }

    public void viewAndReplyToManagedEnquiries() {
        enquiryManagerController.viewAndReplyToManagedEnquiries();
    }

    // applyFilters is handled by BaseController and accessed via ManagerView
}
