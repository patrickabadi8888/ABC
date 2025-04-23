package Controllers;

import java.util.Comparator;
import java.util.List;
import java.util.Scanner;
import java.util.stream.Collectors;

import Models.Enquiry;
import Models.Project;
import Models.User;
import Services.IApplicationService;
import Services.IEnquiryService;
import Services.IOfficerRegistrationService;
import Services.IProjectService;
import Services.IUserService;
import Utils.DateUtils;

// Handles applicant actions related to enquiries
public class EnquiryApplicantController extends BaseController {

    private final IEnquiryService enquiryService; // Specific service needed

    public EnquiryApplicantController(IUserService userService, IProjectService projectService,
                                      IApplicationService applicationService, IOfficerRegistrationService officerRegistrationService,
                                      IEnquiryService enquiryService, // Inject enquiry service
                                      User currentUser, Scanner scanner, AuthController authController) {
        super(userService, projectService, applicationService, officerRegistrationService, currentUser, scanner, authController);
        this.enquiryService = enquiryService;
    }

    public void submitEnquiry() {
        System.out.println("\n--- Submit Enquiry ---");
        // Get projects that are visible (don't need other filters for enquiry)
        List<Project> viewableProjects = getFilteredProjects(true, false, false, false, false);
        Project selectedProject = null;
        String projectNameInput;

        // Allow selecting from list or typing name
        if (!viewableProjects.isEmpty()) {
            viewAndSelectProject(viewableProjects, "Select Project to Enquire About (Optional)");
            selectedProject = selectProjectFromList(viewableProjects);
        }

        if (selectedProject != null) {
            projectNameInput = selectedProject.getProjectName();
            System.out.println("Enquiring about project: " + projectNameInput);
        } else {
            // Prompt for name if not selected or list was empty
            if (!viewableProjects.isEmpty()) {
                System.out.println("No project selected from list, or you chose to cancel selection.");
            }
            System.out.print("Enter the exact Project Name you want to enquire about (leave blank to cancel): ");
            projectNameInput = scanner.nextLine().trim();

            if (projectNameInput.isEmpty()) {
                System.out.println("Enquiry cancelled.");
                return;
            }
            // Check if the typed project name exists (optional warning)
            if (projectService.findProjectByName(projectNameInput) == null) {
                System.out.println("Warning: Project '" + projectNameInput
                        + "' not found in current listings. Ensure the name is correct before submitting.");
                // Ask for confirmation? For now, allow submitting anyway.
            }
        }

        // Get enquiry text
        System.out.print("Enter your enquiry text (cannot be empty): ");
        String text = scanner.nextLine().trim();

        if (!text.isEmpty()) {
            // Create Enquiry object - ID is generated internally
            Enquiry newEnquiry = new Enquiry(currentUser.getNric(), projectNameInput, text, DateUtils.getCurrentDate());
            enquiryService.addEnquiry(newEnquiry); // Add using service
            System.out.println("Enquiry submitted successfully (ID: " + newEnquiry.getEnquiryId() + ").");
            enquiryService.saveEnquiries(enquiryService.getAllEnquiries()); // Save immediately
        } else {
            System.out.println("Enquiry text cannot be empty. Enquiry not submitted.");
        }
    }

    public void viewMyEnquiries() {
        System.out.println("\n--- Your Enquiries ---");
        // Get enquiries using the service
        List<Enquiry> myEnquiries = enquiryService.getEnquiriesByApplicant(currentUser.getNric())
                .stream()
                // Sort by date descending (most recent first)
                .sorted(Comparator.comparing(Enquiry::getEnquiryDate).reversed())
                .collect(Collectors.toList());

        if (myEnquiries.isEmpty()) {
            System.out.println("You have not submitted any enquiries.");
            return;
        }

        // Display enquiries
        for (int i = 0; i < myEnquiries.size(); i++) {
            Enquiry e = myEnquiries.get(i);
            System.out.printf("%d. ID: %s | Project: %s | Date: %s\n",
                    i + 1, e.getEnquiryId(), e.getProjectName(), DateUtils.formatDate(e.getEnquiryDate()));
            System.out.println("   Enquiry: " + e.getEnquiryText());
            if (e.isReplied()) {
                System.out.printf("   Reply (by %s on %s): %s\n",
                        e.getRepliedByNric() != null ? e.getRepliedByNric() : "N/A", // Use N/A for null replier NRIC
                        e.getReplyDate() != null ? DateUtils.formatDate(e.getReplyDate()) : "N/A", // Use N/A for null reply date
                        e.getReplyText());
            } else {
                System.out.println("   Reply: (Pending)");
            }
            System.out.println("----------------------------------------"); // Separator
        }
    }

    public void editMyEnquiry() {
        System.out.println("\n--- Edit Enquiry ---");
        // Get editable enquiries (own, not replied) using the service
        List<Enquiry> editableEnquiries = enquiryService.getEnquiriesByApplicant(currentUser.getNric())
                .stream()
                .filter(e -> !e.isReplied())
                .sorted(Comparator.comparing(Enquiry::getEnquiryDate).reversed())
                .collect(Collectors.toList());

        if (editableEnquiries.isEmpty()) {
            System.out.println("You have no enquiries that can be edited (must not be replied to yet).");
            return;
        }

        // Display editable enquiries for selection
        System.out.println("Select enquiry to edit:");
        for (int i = 0; i < editableEnquiries.size(); i++) {
            Enquiry e = editableEnquiries.get(i);
            // Truncate long text for display if needed
            String truncatedText = e.getEnquiryText().length() > 50 ? e.getEnquiryText().substring(0, 47) + "..." : e.getEnquiryText();
            System.out.printf("%d. ID: %s | Project: %s | Text: %s\n",
                    i + 1, e.getEnquiryId(), e.getProjectName(), truncatedText);
        }

        int choice = getIntInput("Enter choice (or 0 to cancel): ", 0, editableEnquiries.size());

        if (choice == 0) {
            System.out.println("Operation cancelled.");
            return;
        }

        Enquiry enquiryToEdit = editableEnquiries.get(choice - 1);
        System.out.println("Current text: " + enquiryToEdit.getEnquiryText());
        System.out.print("Enter new enquiry text (cannot be empty): ");
        String newText = scanner.nextLine().trim();

        // Attempt to set the new text using the Enquiry object's method
        if (enquiryToEdit.setEnquiryText(newText)) {
            System.out.println("Enquiry updated successfully.");
            enquiryService.saveEnquiries(enquiryService.getAllEnquiries()); // Save changes
        } else {
            // Error message is printed within setEnquiryText if failed
            System.out.println("Enquiry not updated.");
        }
    }

    public void deleteMyEnquiry() {
        System.out.println("\n--- Delete Enquiry ---");
        // Get deletable enquiries (own, not replied)
        List<Enquiry> deletableEnquiries = enquiryService.getEnquiriesByApplicant(currentUser.getNric())
                .stream()
                .filter(e -> !e.isReplied())
                .sorted(Comparator.comparing(Enquiry::getEnquiryDate).reversed())
                .collect(Collectors.toList());

        if (deletableEnquiries.isEmpty()) {
            System.out.println("You have no enquiries that can be deleted (must not be replied to yet).");
            return;
        }

        // Display deletable enquiries
        System.out.println("Select enquiry to delete:");
        for (int i = 0; i < deletableEnquiries.size(); i++) {
            Enquiry e = deletableEnquiries.get(i);
            String truncatedText = e.getEnquiryText().length() > 50 ? e.getEnquiryText().substring(0, 47) + "..." : e.getEnquiryText();
            System.out.printf("%d. ID: %s | Project: %s | Text: %s\n",
                    i + 1, e.getEnquiryId(), e.getProjectName(), truncatedText);
        }

        int choice = getIntInput("Enter choice (or 0 to cancel): ", 0, deletableEnquiries.size());

        if (choice == 0) {
            System.out.println("Operation cancelled.");
            return;
        }

        Enquiry enquiryToDelete = deletableEnquiries.get(choice - 1);
        System.out.print(
                "Are you sure you want to permanently delete enquiry " + enquiryToDelete.getEnquiryId() + "? (yes/no): ");
        String confirm = scanner.nextLine().trim().toLowerCase();

        if (confirm.equals("yes")) {
            // Remove using the service
            if (enquiryService.removeEnquiry(enquiryToDelete.getEnquiryId())) {
                System.out.println("Enquiry deleted successfully.");
                enquiryService.saveEnquiries(enquiryService.getAllEnquiries()); // Save changes
            } else {
                // This should ideally not happen if the enquiry was in the list
                System.err.println("Error: Failed to remove enquiry from service layer.");
            }
        } else {
            System.out.println("Deletion cancelled.");
        }
    }
}
