package Controllers;

import java.util.Scanner;
import Models.User;
import Services.IApplicationService;
import Services.IEnquiryService;
import Services.IOfficerRegistrationService;
import Services.IProjectService;
import Services.IUserService;

// Main controller for Officer role, delegates actions to specific controllers
// Inherits from ApplicantController to provide Applicant functionalities
public class OfficerController extends ApplicantController {

    // Hold instances of the specialized Officer controllers
    private final OfficerActionController officerActionController;
    private final EnquiryOfficerController enquiryOfficerController;
    private final BookingOfficerController bookingOfficerController;

    public OfficerController(IUserService userService, IProjectService projectService,
                             IApplicationService applicationService, IOfficerRegistrationService officerRegistrationService,
                             IEnquiryService enquiryService, // Enquiry service needed for both Applicant and Officer parts
                             User currentUser, Scanner scanner, AuthController authController) {
        // Call ApplicantController constructor, which in turn calls BaseController constructor
        super(userService, projectService, applicationService, officerRegistrationService, enquiryService, currentUser, scanner, authController);

        // Instantiate Officer-specific controllers
        this.officerActionController = new OfficerActionController(userService, projectService, applicationService, officerRegistrationService, currentUser, scanner, authController);
        this.enquiryOfficerController = new EnquiryOfficerController(userService, projectService, applicationService, officerRegistrationService, enquiryService, currentUser, scanner, authController);
        this.bookingOfficerController = new BookingOfficerController(userService, projectService, applicationService, officerRegistrationService, currentUser, scanner, authController);
    }

    // --- Delegate Officer-specific methods ---

    public void registerForProject() {
        officerActionController.registerForProject();
    }

    public void viewRegistrationStatus() {
        officerActionController.viewRegistrationStatus();
    }

    public void viewHandlingProjectDetails() {
        officerActionController.viewHandlingProjectDetails();
    }

    public void viewAndReplyToEnquiries() { // Note: This is the Officer version
        enquiryOfficerController.viewAndReplyToEnquiries();
    }

    public void manageFlatBooking() {
        bookingOfficerController.manageFlatBooking();
    }

    // --- Inherited Applicant methods (viewOpenProjects, applyForProject, etc.) ---
    // These are available directly via inheritance from ApplicantController.
    // For example, calling officerController.viewOpenProjects() will execute
    // the viewOpenProjects method defined in ApplicantActionController (via ApplicantController).
    // Similarly, Officer's own enquiry actions (submit, view my, edit my, delete my)
    // are handled by the EnquiryApplicantController instance held by the parent ApplicantController.
}
