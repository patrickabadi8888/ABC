package Controllers;

import java.util.Scanner;
import Models.User;
import Services.IApplicationService;
import Services.IEnquiryService;
import Services.IOfficerRegistrationService;
import Services.IProjectService;
import Services.IUserService;

public class ApplicantController extends BaseController {

    private final ApplicantActionController actionController;
    private final EnquiryApplicantController enquiryController;
    public ApplicantController(IUserService userService, IProjectService projectService,
            IApplicationService applicationService, IOfficerRegistrationService officerRegistrationService,
            IEnquiryService enquiryService,
            User currentUser, Scanner scanner, AuthController authController) {
        super(userService, projectService, applicationService, officerRegistrationService, currentUser, scanner,
                authController);

        this.actionController = new ApplicantActionController(userService, projectService, applicationService,
                officerRegistrationService, currentUser, scanner, authController);
        this.enquiryController = new EnquiryApplicantController(userService, projectService, applicationService,
                officerRegistrationService, enquiryService, currentUser, scanner, authController);

    }

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

}
