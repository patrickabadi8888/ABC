package Controllers;

import java.util.Comparator;
import java.util.List;
import java.util.Scanner;
import java.util.stream.Collectors;

import Models.Enquiry;
import Models.HDBManager;
import Models.Project;
import Models.User;
import Services.IApplicationService;
import Services.IEnquiryService;
import Services.IOfficerRegistrationService;
import Services.IProjectService;
import Services.IUserService;
import Utils.DateUtils;

// Handles Manager actions related to Enquiries (View All, View/Reply Managed)
public class EnquiryManagerController extends BaseController {

    private final IEnquiryService enquiryService;

    public EnquiryManagerController(IUserService userService, IProjectService projectService,
                                    IApplicationService applicationService, IOfficerRegistrationService officerRegistrationService,
                                    IEnquiryService enquiryService, // Inject enquiry service
                                    User currentUser, Scanner scanner, AuthController authController) {
        super(userService, projectService, applicationService, officerRegistrationService, currentUser, scanner, authController);
        this.enquiryService = enquiryService;
        if (!(currentUser instanceof HDBManager)) {
            throw new IllegalArgumentException("EnquiryManagerController requires an HDBManager user.");
        }
    }

    public void viewAllEnquiries() {
        System.out.println("\n--- View Enquiries (ALL Projects) ---");
        List<Enquiry> allEnquiries = enquiryService.getAllEnquiries(); // Get all from service

        if (allEnquiries.isEmpty()) {
            System.out.println("No enquiries found in the system.");
            return;
        }

        // Sort by Project Name, then by Date (reversed, newest first)
        allEnquiries.stream()
            .sorted(Comparator.comparing(Enquiry::getProjectName)
                              .thenComparing(Enquiry::getEnquiryDate, Comparator.reverseOrder()))
            .forEach(e -> {
                printEnquiryDetails(e); // Use helper to print
                System.out.println("----------------------------------------");
            });
    }

    public void viewAndReplyToManagedEnquiries() {
        System.out.println("\n--- View/Reply Enquiries (Managed Projects) ---");
        // Get names of projects managed by the current manager
        List<String> myManagedProjectNames = projectService.getProjectsManagedBy(currentUser.getNric())
                .stream()
                // Apply view filters (optional, but consistent with menu description)
                .filter(p -> filterLocation == null || p.getNeighborhood().equalsIgnoreCase(filterLocation))
                .filter(p -> filterFlatType == null || p.getFlatTypes().containsKey(filterFlatType))
                .map(Project::getProjectName)
                .collect(Collectors.toList());

        if (myManagedProjectNames.isEmpty()) {
            // Check if filters caused this
            String filterMsg = (filterLocation != null || filterFlatType != null) ? " matching the current filters." : ".";
            System.out.println("You are not managing any projects" + filterMsg + " For which to view enquiries.");
            return;
        }

        // Get all enquiries and filter by managed project names
        List<Enquiry> managedEnquiries = enquiryService.getAllEnquiries().stream()
                .filter(e -> myManagedProjectNames.contains(e.getProjectName()))
                // Sort by Project Name, then Date Descending
                .sorted(Comparator.comparing(Enquiry::getProjectName)
                                  .thenComparing(Enquiry::getEnquiryDate, Comparator.reverseOrder()))
                .collect(Collectors.toList());

        if (managedEnquiries.isEmpty()) {
            String filterMsg = (filterLocation != null || filterFlatType != null) ? " (matching filters)." : ".";
            System.out.println("No enquiries found for the projects you manage" + filterMsg);
            return;
        }

        // Separate unreplied and replied managed enquiries
        List<Enquiry> unrepliedEnquiries = managedEnquiries.stream()
                .filter(e -> !e.isReplied())
                .collect(Collectors.toList());
        List<Enquiry> repliedEnquiries = managedEnquiries.stream()
                .filter(Enquiry::isReplied)
                .collect(Collectors.toList());

        // --- Handle Unreplied Managed Enquiries ---
        System.out.println("--- Unreplied Enquiries (Managed Projects" + ((filterLocation != null || filterFlatType != null) ? " - Filtered" : "") + ") ---");
        if (unrepliedEnquiries.isEmpty()) {
            System.out.println("(None)");
        } else {
            // Display for selection
            for (int i = 0; i < unrepliedEnquiries.size(); i++) {
                Enquiry e = unrepliedEnquiries.get(i);
                System.out.printf("%d. ", i + 1); // Print number first
                printEnquiryDetails(e); // Use helper
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
                    System.out.println("Reply not submitted.");
                }
            } else if (choice != 0) {
                 System.out.println("Invalid choice.");
            }
             // If choice is 0, do nothing (skip)
        }

        // --- Display Replied Managed Enquiries ---
        System.out.println("\n--- Replied Enquiries (Managed Projects" + ((filterLocation != null || filterFlatType != null) ? " - Filtered" : "") + ") ---");
        if (repliedEnquiries.isEmpty()) {
            System.out.println("(None)");
        } else {
            for (Enquiry e : repliedEnquiries) {
                printEnquiryDetails(e); // Use helper
                System.out.println("----------------------------------------"); // Separator
            }
        }
    }

    // Helper method to print enquiry details consistently
    private void printEnquiryDetails(Enquiry e) {
         User applicant = userService.findUserByNric(e.getApplicantNric());
         String applicantName = applicant != null ? applicant.getName() : "N/A";
        System.out.printf("ID: %s | Project: %-15s | Applicant: %s (%s) | Date: %s\n",
                e.getEnquiryId(),
                e.getProjectName(),
                e.getApplicantNric(),
                applicantName, // Show name if found
                DateUtils.formatDate(e.getEnquiryDate()));
        System.out.println("   Enquiry: " + e.getEnquiryText());
        if (e.isReplied()) {
             User replier = userService.findUserByNric(e.getRepliedByNric());
             String replierRole = replier != null ? " (" + replier.getRole().toString().replace("HDB_", "") + ")" : ""; // Show role briefly

            System.out.printf("   Reply (by %s%s on %s): %s\n",
                    e.getRepliedByNric() != null ? e.getRepliedByNric() : "N/A",
                    replierRole, // Add role info
                    e.getReplyDate() != null ? DateUtils.formatDate(e.getReplyDate()) : "N/A",
                    e.getReplyText());
        } else {
            System.out.println("   Reply: (Pending)");
        }
    }
}
