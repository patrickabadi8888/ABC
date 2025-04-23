package Controllers;

import java.util.Comparator;
import java.util.List;
import java.util.Scanner;
import java.util.stream.Collectors;

import Models.Enquiry;
import Models.HDBOfficer;
import Models.Project;
import Models.User;
import Services.IApplicationService;
import Services.IEnquiryService;
import Services.IOfficerRegistrationService;
import Services.IProjectService;
import Services.IUserService;
import Utils.DateUtils;

// Handles Officer actions related to enquiries for their handled project
public class EnquiryOfficerController extends BaseController {

    private final IEnquiryService enquiryService;

    public EnquiryOfficerController(IUserService userService, IProjectService projectService,
                                    IApplicationService applicationService, IOfficerRegistrationService officerRegistrationService,
                                    IEnquiryService enquiryService, // Inject enquiry service
                                    User currentUser, Scanner scanner, AuthController authController) {
        super(userService, projectService, applicationService, officerRegistrationService, currentUser, scanner, authController);
        this.enquiryService = enquiryService;
    }

    public void viewAndReplyToEnquiries() {
        if (!(currentUser instanceof HDBOfficer)) return;
        HDBOfficer officer = (HDBOfficer) currentUser;

        // Find the project the officer is currently handling
        Project handlingProject = getOfficerHandlingProject(officer); // Use BaseController method

        if (handlingProject == null) {
            System.out.println("You need to be handling an active project to view and reply to its enquiries.");
            return;
        }
        String handlingProjectName = handlingProject.getProjectName();

        System.out.println("\n--- Enquiries for Project: " + handlingProjectName + " ---");
        // Get enquiries for this specific project using the service
        List<Enquiry> projectEnquiries = enquiryService.getEnquiriesByProject(handlingProjectName)
                .stream()
                .sorted(Comparator.comparing(Enquiry::getEnquiryDate).reversed()) // Sort by date desc
                .collect(Collectors.toList());

        if (projectEnquiries.isEmpty()) {
            System.out.println("No enquiries found for this project.");
            return;
        }

        // Separate unreplied and replied
        List<Enquiry> unrepliedEnquiries = projectEnquiries.stream()
                .filter(e -> !e.isReplied())
                .collect(Collectors.toList());
        List<Enquiry> repliedEnquiries = projectEnquiries.stream()
                .filter(Enquiry::isReplied)
                .collect(Collectors.toList());

        // --- Handle Unreplied Enquiries ---
        System.out.println("--- Unreplied Enquiries ---");
        if (unrepliedEnquiries.isEmpty()) {
            System.out.println("(None)");
        } else {
            // Display unreplied enquiries for selection
            for (int i = 0; i < unrepliedEnquiries.size(); i++) {
                Enquiry e = unrepliedEnquiries.get(i);
                System.out.printf("%d. ID: %s | Applicant: %s | Date: %s\n",
                        i + 1, e.getEnquiryId(), e.getApplicantNric(), DateUtils.formatDate(e.getEnquiryDate()));
                System.out.println("   Enquiry: " + e.getEnquiryText());
                System.out.println("---"); // Separator
            }
            // Prompt for reply
            int choice = getIntInput("Enter the number of the enquiry to reply to (or 0 to skip): ", 0, unrepliedEnquiries.size());

            if (choice >= 1) {
                Enquiry enquiryToReply = unrepliedEnquiries.get(choice - 1);
                System.out.print("Enter your reply: ");
                String replyText = scanner.nextLine().trim();
                // Set reply using Enquiry object's method
                if (enquiryToReply.setReply(replyText, currentUser.getNric(), DateUtils.getCurrentDate())) {
                    System.out.println("Reply submitted successfully.");
                    enquiryService.saveEnquiries(enquiryService.getAllEnquiries()); // Save changes
                } else {
                    // Error message printed within setReply
                    System.out.println("Reply not submitted.");
                }
            } else if (choice != 0) {
                System.out.println("Invalid choice.");
            }
            // If choice is 0, do nothing (skip)
        }

        // --- Display Replied Enquiries ---
        System.out.println("\n--- Replied Enquiries ---");
        if (repliedEnquiries.isEmpty()) {
            System.out.println("(None)");
        } else {
            for (Enquiry e : repliedEnquiries) {
                System.out.printf("ID: %s | Applicant: %s | Enquiry Date: %s\n",
                        e.getEnquiryId(), e.getApplicantNric(), DateUtils.formatDate(e.getEnquiryDate()));
                System.out.println("   Enquiry: " + e.getEnquiryText());
                System.out.printf("   Reply (by %s on %s): %s\n",
                        e.getRepliedByNric() != null ? e.getRepliedByNric() : "N/A",
                        e.getReplyDate() != null ? DateUtils.formatDate(e.getReplyDate()) : "N/A",
                        e.getReplyText());
                System.out.println("--------------------"); // Separator
            }
        }
    }
}
