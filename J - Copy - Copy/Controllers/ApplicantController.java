package Controllers;

import java.util.Scanner;
import Models.User;
import Services.IApplicationService;
import Services.IEnquiryService;
import Services.IOfficerRegistrationService;
import Services.IProjectService;
import Services.IUserService;

// Main controller for Applicant role, delegates actions to specific controllers
public class ApplicantController extends BaseController {

    // Hold instances of the specialized controllers
    private final ApplicantActionController actionController;
    private final EnquiryApplicantController enquiryController;

    public ApplicantController(IUserService userService, IProjectService projectService,
                               IApplicationService applicationService, IOfficerRegistrationService officerRegistrationService,
                               IEnquiryService enquiryService, // Needs enquiry service for its child controller
                               User currentUser, Scanner scanner, AuthController authController) {
        super(userService, projectService, applicationService, officerRegistrationService, currentUser, scanner, authController);

        // Instantiate the specialized controllers, passing necessary dependencies
        this.actionController = new ApplicantActionController(userService, projectService, applicationService, officerRegistrationService, currentUser, scanner, authController);
        this.enquiryController = new EnquiryApplicantController(userService, projectService, applicationService, officerRegistrationService, enquiryService, currentUser, scanner, authController);

        // Assign filters from BaseController to sub-controllers if needed, or manage filters centrally.
        // Currently, filters are managed in BaseController and used by getFilteredProjects.
        // this.actionController.filterLocation = this.filterLocation; // Example if needed
        // this.actionController.filterFlatType = this.filterFlatType; // Example if needed
    }

    // --- Delegate methods to specialized controllers ---

    public void viewOpenProjects() {
        actionController.viewOpenProjects();
    }

    public void applyForProject() {
        actionController.applyForProject();
    }

    public void viewMyApplication() {
        actionController.viewMyApplication();
    }

    public void requestWithdrawal() {
        actionController.requestWithdrawal();
    }

    public void submitEnquiry() {
        enquiryController.submitEnquiry();
    }

    public void viewMyEnquiries() {
        enquiryController.viewMyEnquiries();
    }

    public void editMyEnquiry() {
        enquiryController.editMyEnquiry();
    }

    public void deleteMyEnquiry() {
        enquiryController.deleteMyEnquiry();
    }

    // applyFilters is handled by BaseController and accessed via ApplicantView
}
