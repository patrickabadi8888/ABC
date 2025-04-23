package Controllers;

import java.util.List;
import java.util.Scanner;
import java.util.stream.Collectors;
import java.util.Map;

import Enums.ApplicationStatus;
import Enums.FlatType;
import Enums.OfficerRegistrationStatus;
import Interfaces.Services.*; // Import all service interfaces
import Models.Applicant;
import Models.BTOApplication;
import Models.Enquiry;
import Models.HDBOfficer;
import Models.Project;
import Models.User;
import Utils.DateUtils;
import Utils.InputUtils; // Use InputUtils

public class ApplicantController {

    protected final Scanner scanner;
    protected final User currentUser;
    // Service Dependencies (Injected)
    protected final IAuthService authService;
    protected final IProjectService projectService;
    protected final IApplicationService applicationService;
    protected final IEnquiryService enquiryService;
    protected final IEligibilityService eligibilityService;
    protected final IFilterService filterService;
    protected final IProjectDisplayService projectDisplayService;
    // Officer specific service needed for apply check
    protected final IOfficerRegistrationService officerRegistrationService;


    public ApplicantController(Scanner scanner, User currentUser, IAuthService authService,
                               IProjectService projectService, IApplicationService applicationService,
                               IEnquiryService enquiryService, IEligibilityService eligibilityService,
                               IFilterService filterService, IProjectDisplayService projectDisplayService,
                               IOfficerRegistrationService officerRegistrationService) {
        this.scanner = scanner;
        this.currentUser = currentUser;
        this.authService = authService;
        this.projectService = projectService;
        this.applicationService = applicationService;
        this.enquiryService = enquiryService;
        this.eligibilityService = eligibilityService;
        this.filterService = filterService;
        this.projectDisplayService = projectDisplayService;
        this.officerRegistrationService = officerRegistrationService; // Added
    }

    public void viewOpenProjects() {
        System.out.println("\n--- Viewing Available BTO Projects ---");
        // Get projects that are visible, active, eligible, and have units
        List<Project> availableProjects = projectService.getOpenProjects(currentUser);
        projectDisplayService.displayProjectList(availableProjects, "Available BTO Projects", currentUser);
    }

    public void applyForProject() {
        // Ensure current user is an Applicant (or subclass like Officer)
        if (!(currentUser instanceof Applicant)) {
            System.out.println("Error: Only Applicants or Officers can apply for projects.");
            return;
        }
        Applicant applicant = (Applicant) currentUser;

        // Pre-checks using Applicant model state
        if (applicant.hasBooked()) {
            System.out.println("You have already booked a flat for project '" + applicant.getAppliedProjectName()
                    + "'. You cannot apply again.");
            return;
        }
        if (applicant.hasActiveApplication()) {
            System.out.println("You have an active application for project '" + applicant.getAppliedProjectName()
                    + "' with status: " + applicant.getApplicationStatus());
            System.out.println("You must withdraw (and have it approved) or be unsuccessful before applying again.");
            return;
        }
        if (applicant.hasPendingWithdrawal()) {
            System.out.println("You have a withdrawal request pending manager approval for project '"
                    + applicant.getAppliedProjectName() + "'.");
            System.out.println("You cannot apply for a new project until the withdrawal is processed.");
            return;
        }

        System.out.println("\n--- Apply for BTO Project ---");
        // Get projects eligible for application (Visible, Active, Eligible, Available Units)
        List<Project> eligibleProjects = projectService.getOpenProjects(currentUser);

        if (eligibleProjects.isEmpty()) {
            System.out.println(
                    "There are currently no open projects you are eligible to apply for based on filters, eligibility, and unit availability.");
            return;
        }

        // Display and select project
        projectDisplayService.displayProjectList(eligibleProjects, "Select Project to Apply For", currentUser);
        Project selectedProject = projectDisplayService.selectProjectFromList(eligibleProjects, scanner);
        if (selectedProject == null) return; // User cancelled

        // --- Officer-Specific Checks ---
        if (currentUser instanceof HDBOfficer) {
            HDBOfficer officer = (HDBOfficer) currentUser;
            // Check if officer is handling the selected project
            Project handlingProject = eligibilityService.getOfficerHandlingProject(officer);
            if (handlingProject != null && selectedProject.equals(handlingProject)) {
                System.out.println("Error: You cannot apply for a project you are currently handling as an Officer.");
                return;
            }
            // Check if officer has a pending registration for the selected project
            boolean hasPendingRegistration = officerRegistrationService.getRegistrationsByOfficer(officer.getNric())
                    .stream()
                    .anyMatch(reg -> reg.getProjectName().equals(selectedProject.getProjectName()) &&
                                    reg.getStatus() == OfficerRegistrationStatus.PENDING);
            if (hasPendingRegistration) {
                System.out.println("Error: You cannot apply for a project you have a pending registration for.");
                return;
            }
        }
        // --- End Officer Checks ---

        // Select Flat Type
        FlatType selectedFlatType = selectEligibleFlatType(selectedProject);
        if (selectedFlatType == null) return; // User cancelled or no eligible types

        // Submit application via service
        boolean success = applicationService.submitApplication(applicant, selectedProject, selectedFlatType);
        // Success message is printed within the service
    }

    private FlatType selectEligibleFlatType(Project project) {
        // Find types the user is eligible for AND have available units
        List<FlatType> eligibleAndAvailableTypes = project.getFlatTypes().entrySet().stream()
                .filter(entry -> eligibilityService.canApplyForFlatType(currentUser, entry.getKey())
                                 && entry.getValue().getAvailableUnits() > 0)
                .map(Map.Entry::getKey)
                .sorted() // Sort by enum order
                .collect(Collectors.toList());

        if (eligibleAndAvailableTypes.isEmpty()) {
            System.out.println("There are no flat types available in this project that you are eligible for.");
            return null;
        }

        if (eligibleAndAvailableTypes.size() == 1) {
            FlatType onlyOption = eligibleAndAvailableTypes.get(0);
            System.out.println("You will be applying for the only eligible and available type: "
                    + onlyOption.getDisplayName() + ".");
            return onlyOption;
        } else {
            System.out.println("Select the flat type you want to apply for:");
            for (int i = 0; i < eligibleAndAvailableTypes.size(); i++) {
                System.out.println((i + 1) + ". " + eligibleAndAvailableTypes.get(i).getDisplayName());
            }
            int typeChoice = InputUtils.getIntInput(scanner, "Enter choice (or 0 to cancel): ", 0, eligibleAndAvailableTypes.size());

            if (typeChoice == 0) {
                System.out.println("Application cancelled.");
                return null;
            }
            return eligibleAndAvailableTypes.get(typeChoice - 1);
        }
    }

    public void viewMyApplication() {
        if (!(currentUser instanceof Applicant)) return;
        Applicant applicant = (Applicant) currentUser;

        // Ensure applicant state is up-to-date (optional, depends on sync strategy)
        // applicationService.synchronizeApplicantStatus(applicant);

        String projectName = applicant.getAppliedProjectName();
        ApplicationStatus status = applicant.getApplicationStatus();

        if (projectName == null || status == null) {
            System.out.println("\nYou do not have any current or past BTO application records.");
            return;
        }

        // Find the detailed application record using the service
        BTOApplication application = applicationService.findApplicationByApplicantAndProject(applicant.getNric(), projectName);
        if (application == null) {
            // This indicates an inconsistency between Applicant object state and repository data
            System.err.println(
                    "Error: Your profile indicates an application, but the detailed record could not be found. Please contact support or try again later.");
            // Optionally clear the applicant's state?
            // applicant.clearApplicationState();
            return;
        }

        // Find project details (might be null if project was deleted)
        Project project = projectService.findProjectByName(projectName);

        System.out.println("\n--- Your BTO Application ---");
        System.out.println("Project Name: " + projectName);
        System.out.println("Neighborhood: " + (project != null ? project.getNeighborhood() : "(Project details not found)"));
        System.out.println("Flat Type Applied For: "
                + (application.getFlatTypeApplied() != null ? application.getFlatTypeApplied().getDisplayName() : "N/A"));
        System.out.println("Application Status: " + status); // Use status from Applicant object (should match application.getStatus())
        if (status == ApplicationStatus.BOOKED && applicant.getBookedFlatType() != null) {
            System.out.println("Booked Flat Type: " + applicant.getBookedFlatType().getDisplayName());
        }
        System.out.println("Application Date: " + DateUtils.formatDate(application.getApplicationDate()));
    }

    public void requestWithdrawal() {
        if (!(currentUser instanceof Applicant)) return;
        Applicant applicant = (Applicant) currentUser;

        // Ensure applicant state is up-to-date before checking eligibility
        // applicationService.synchronizeApplicantStatus(applicant);

        String currentProject = applicant.getAppliedProjectName();
        ApplicationStatus currentStatus = applicant.getApplicationStatus();

        if (currentProject == null || currentStatus == null) {
            System.out.println("You do not have an application to withdraw.");
            return;
        }

        // Check eligibility based on current status
        if (currentStatus != ApplicationStatus.PENDING &&
            currentStatus != ApplicationStatus.SUCCESSFUL &&
            currentStatus != ApplicationStatus.BOOKED) {
            System.out.println("Your application status (" + currentStatus + ") is not eligible for withdrawal request.");
            System.out.println("You can only request withdrawal if your status is PENDING, SUCCESSFUL, or BOOKED.");
            return;
        }

        // Confirm with user
        System.out.println("\n--- Request Application Withdrawal ---");
        System.out.println("Project: " + currentProject);
        System.out.println("Current Status: " + currentStatus);
        boolean confirm = InputUtils.getConfirmation(scanner, "Are you sure you want to request withdrawal for this application? Manager approval is required.");

        if (confirm) {
            // Delegate withdrawal request to the service
            boolean success = applicationService.requestWithdrawal(applicant);
            // Success/error message printed within the service
        } else {
            System.out.println("Withdrawal request cancelled.");
        }
    }

    public void submitEnquiry() {
        System.out.println("\n--- Submit Enquiry ---");
        // Get projects visible to the user (not necessarily open/active)
        List<Project> viewableProjects = projectService.getVisibleProjects(currentUser);
        Project selectedProject = null;

        if (!viewableProjects.isEmpty()) {
            projectDisplayService.displayProjectList(viewableProjects, "Select Project to Enquire About (Optional)", currentUser);
            selectedProject = projectDisplayService.selectProjectFromList(viewableProjects, scanner);
        } else {
            System.out.println("No projects currently visible to you.");
        }

        String projectNameInput;
        if (selectedProject != null) {
            projectNameInput = selectedProject.getProjectName();
            System.out.println("Enquiring about: " + projectNameInput);
        } else {
            if (!viewableProjects.isEmpty()) {
                System.out.println("No project selected from list, or you cancelled.");
            }
            // Allow manual entry even if no projects are visible/selected
            projectNameInput = InputUtils.getStringInput(scanner, "Enter the exact Project Name you want to enquire about: ", false);
            if (projectService.findProjectByName(projectNameInput) == null) {
                System.out.println("Warning: Project '" + projectNameInput
                        + "' not found in current listings, but submitting enquiry anyway.");
            }
        }

        String text = InputUtils.getStringInput(scanner, "Enter your enquiry text: ", false);

        // Submit via service
        boolean success = enquiryService.submitEnquiry(currentUser, projectNameInput, text);
        // Success message printed within service
    }

    public void viewMyEnquiries() {
        System.out.println("\n--- Your Enquiries ---");
        List<Enquiry> myEnquiries = enquiryService.getEnquiriesByApplicant(currentUser.getNric());

        if (myEnquiries.isEmpty()) {
            System.out.println("You have not submitted any enquiries.");
            return;
        }

        for (int i = 0; i < myEnquiries.size(); i++) {
            Enquiry e = myEnquiries.get(i);
            System.out.printf("%d. ID: %s | Project: %s | Date: %s\n",
                    i + 1, e.getEnquiryId(), e.getProjectName(), DateUtils.formatDate(e.getEnquiryDate()));
            System.out.println("   Enquiry: " + e.getEnquiryText());
            if (e.isReplied()) {
                System.out.printf("   Reply (by %s on %s): %s\n",
                        e.getRepliedByNric() != null ? e.getRepliedByNric() : "N/A",
                        e.getReplyDate() != null ? DateUtils.formatDate(e.getReplyDate()) : "N/A",
                        e.getReplyText());
            } else {
                System.out.println("   Reply: (Pending)");
            }
            System.out.println("----------------------------------------");
        }
    }

    public void editMyEnquiry() {
        System.out.println("\n--- Edit Enquiry ---");
        // Get user's unreplied enquiries
        List<Enquiry> editableEnquiries = enquiryService.getEnquiriesByApplicant(currentUser.getNric())
                .stream()
                .filter(e -> !e.isReplied())
                .collect(Collectors.toList()); // Already sorted by date descending from getEnquiriesByApplicant

        if (editableEnquiries.isEmpty()) {
            System.out.println("You have no enquiries that can be edited (must not be replied to yet).");
            return;
        }

        System.out.println("Select enquiry to edit:");
        for (int i = 0; i < editableEnquiries.size(); i++) {
            Enquiry e = editableEnquiries.get(i);
            // Limit text display length if needed
            String snippet = e.getEnquiryText().length() > 50 ? e.getEnquiryText().substring(0, 47) + "..." : e.getEnquiryText();
            System.out.printf("%d. ID: %s | Project: %s | Text: %s\n",
                    i + 1, e.getEnquiryId(), e.getProjectName(), snippet);
        }

        int choice = InputUtils.getIntInput(scanner, "Enter choice (or 0 to cancel): ", 0, editableEnquiries.size());
        if (choice == 0) {
            System.out.println("Operation cancelled.");
            return;
        }

        Enquiry enquiryToEdit = editableEnquiries.get(choice - 1);
        String newText = InputUtils.getStringInput(scanner, "Enter new enquiry text: ", false);

        // Edit via service
        boolean success = enquiryService.editEnquiry(enquiryToEdit, newText);
        // Success/error message printed within service
    }

    public void deleteMyEnquiry() {
        System.out.println("\n--- Delete Enquiry ---");
        // Get user's unreplied enquiries
        List<Enquiry> deletableEnquiries = enquiryService.getEnquiriesByApplicant(currentUser.getNric())
                .stream()
                .filter(e -> !e.isReplied())
                .collect(Collectors.toList()); // Already sorted

        if (deletableEnquiries.isEmpty()) {
            System.out.println("You have no enquiries that can be deleted (must not be replied to yet).");
            return;
        }

        System.out.println("Select enquiry to delete:");
         for (int i = 0; i < deletableEnquiries.size(); i++) {
            Enquiry e = deletableEnquiries.get(i);
            String snippet = e.getEnquiryText().length() > 50 ? e.getEnquiryText().substring(0, 47) + "..." : e.getEnquiryText();
            System.out.printf("%d. ID: %s | Project: %s | Text: %s\n",
                    i + 1, e.getEnquiryId(), e.getProjectName(), snippet);
        }

        int choice = InputUtils.getIntInput(scanner, "Enter choice (or 0 to cancel): ", 0, deletableEnquiries.size());
        if (choice == 0) {
            System.out.println("Operation cancelled.");
            return;
        }

        Enquiry enquiryToDelete = deletableEnquiries.get(choice - 1);
        boolean confirm = InputUtils.getConfirmation(scanner, "Are you sure you want to delete enquiry " + enquiryToDelete.getEnquiryId() + "?");

        if (confirm) {
            // Delete via service
            boolean success = enquiryService.deleteEnquiry(enquiryToDelete);
            // Success/error message printed within service
        } else {
            System.out.println("Deletion cancelled.");
        }
    }

    // Method to apply filters (delegated to FilterService)
    public void applyFilters() {
        System.out.println("\n--- Apply/Clear Filters ---");
        System.out.print("Enter neighborhood to filter by (current: "
                + (filterService.getLocationFilter() == null ? "Any" : filterService.getLocationFilter()) + ", leave blank to clear): ");
        String loc = scanner.nextLine().trim();
        filterService.setLocationFilter(loc); // Service handles empty string logic

        System.out.print("Enter flat type to filter by (TWO_ROOM, THREE_ROOM, current: "
                + (filterService.getFlatTypeFilter() == null ? "Any" : filterService.getFlatTypeFilter()) + ", leave blank to clear): ");
        String typeStr = scanner.nextLine().trim();
        if (typeStr.isEmpty()) {
            filterService.setFlatTypeFilter(null);
        } else {
            try {
                FlatType parsedType = FlatType.fromString(typeStr); // Use enum parser
                if (parsedType != null) {
                    filterService.setFlatTypeFilter(parsedType);
                } else {
                    System.out.println("Invalid flat type entered. Filter not changed.");
                }
            } catch (IllegalArgumentException e) {
                // Should not happen with fromString returning null, but good practice
                System.out.println("Invalid flat type format. Filter not changed.");
            }
        }
        System.out.println("Filters updated. Current filters: " + filterService.getCurrentFilterStatus());
    }

     // Method to change password (delegated to AuthService)
     public boolean changePassword() {
         System.out.println("\n--- Change Password ---");
         System.out.print("Enter current password: ");
         String oldPassword = scanner.nextLine();
         System.out.print("Enter new password: ");
         String newPassword = scanner.nextLine();
         System.out.print("Confirm new password: ");
         String confirmPassword = scanner.nextLine();

         if (!newPassword.equals(confirmPassword)) {
             System.out.println("New passwords do not match. Password not changed.");
             return false;
         }
         // Other checks (empty, same as old) handled by AuthService.changePassword

         // Delegate to auth service
         return authService.changePassword(currentUser, oldPassword, newPassword);
         // Success/error messages printed within service
     }
}
