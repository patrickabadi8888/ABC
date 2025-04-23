package Controllers;

import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Scanner;
import java.util.stream.Collectors;
import java.util.Comparator;

import Enums.FlatType;
import Enums.MaritalStatus;
import Enums.OfficerRegistrationStatus;
import Enums.ApplicationStatus;
import Interfaces.Services.*; // Import all service interfaces
import Models.*; // Import all models
import Utils.DateUtils;
import Utils.InputUtils;

import Interfaces.Repositories.IUserRepository;
import Interfaces.Services.IProjectDisplayService;

public class ManagerController {

    private final Scanner scanner;
    private final User currentUser; // Should be HDBManager
    // Service Dependencies (Injected)
    private final IAuthService authService;
    private final IProjectService projectService;
    private final IApplicationService applicationService;
    private final IEnquiryService enquiryService;
    private final IEligibilityService eligibilityService;
    private final IFilterService filterService;
    private final IProjectDisplayService projectDisplayService;
    private final IOfficerRegistrationService officerRegistrationService;
    private final IReportService reportService;
    private final IUserRepository userRepository; // Needed for officer/applicant details

    public ManagerController(Scanner scanner, User currentUser, IAuthService authService,
                             IProjectService projectService, IApplicationService applicationService,
                             IEnquiryService enquiryService, IEligibilityService eligibilityService,
                             IFilterService filterService, IProjectDisplayService projectDisplayService,
                             IOfficerRegistrationService officerRegistrationService, IReportService reportService,
                             IUserRepository userRepository) {
        this.scanner = scanner;
        this.currentUser = currentUser;
        this.authService = authService;
        this.projectService = projectService;
        this.applicationService = applicationService;
        this.enquiryService = enquiryService;
        this.eligibilityService = eligibilityService;
        this.filterService = filterService;
        this.projectDisplayService = projectDisplayService;
        this.officerRegistrationService = officerRegistrationService;
        this.reportService = reportService;
        this.userRepository = userRepository;

        if (!(currentUser instanceof HDBManager)) {
            // This should not happen if controller is instantiated correctly
            throw new IllegalStateException("ManagerController initialized with non-manager user.");
        }
    }

    private HDBManager getCurrentManager() {
        return (HDBManager) currentUser;
    }

    public void createProject() {
        System.out.println("\n--- Create New BTO Project ---");

        String projectName;
        while (true) {
            projectName = InputUtils.getStringInput(scanner, "Enter Project Name: ", false);
            if (projectService.findProjectByName(projectName) != null) {
                System.out.println("Project name already exists. Please choose a unique name.");
            } else {
                break;
            }
        }

        String neighborhood = InputUtils.getStringInput(scanner, "Enter Neighborhood: ", false);

        Map<FlatType, FlatTypeDetails> flatTypes = new HashMap<>();
        System.out.println("--- Flat Type Details ---");
        int units2Room = InputUtils.getIntInput(scanner, "Enter total number of 2-Room units (0 if none): ", 0, 9999);
        if (units2Room > 0) {
            double price2Room = InputUtils.getDoubleInput(scanner, "Enter selling price for 2-Room units: $", 0, Double.MAX_VALUE);
            flatTypes.put(FlatType.TWO_ROOM, new FlatTypeDetails(units2Room, units2Room, price2Room)); // Available = Total initially
        }
        int units3Room = InputUtils.getIntInput(scanner, "Enter total number of 3-Room units (0 if none): ", 0, 9999);
        if (units3Room > 0) {
            double price3Room = InputUtils.getDoubleInput(scanner, "Enter selling price for 3-Room units: $", 0, Double.MAX_VALUE);
            flatTypes.put(FlatType.THREE_ROOM, new FlatTypeDetails(units3Room, units3Room, price3Room)); // Available = Total initially
        }

        if (flatTypes.isEmpty()) {
            System.out.println("Error: Project must have at least one type of flat (2-Room or 3-Room). Creation cancelled.");
            return;
        }

        Date openingDate;
        Date closingDate;
        while (true) {
            openingDate = InputUtils.getDateInput(scanner, "Enter Application Opening Date (yyyy-MM-dd): ", false);
            closingDate = InputUtils.getDateInput(scanner, "Enter Application Closing Date (yyyy-MM-dd): ", false);

            if (closingDate.before(openingDate)) {
                System.out.println("Closing date cannot be before opening date. Please re-enter.");
                continue;
            }

            // Check for overlap before proceeding
            Project tempProject = new Project("__temp__", "__temp__", flatTypes, openingDate, closingDate, getCurrentManager().getNric(), 1, List.of(), false);
            boolean overlaps = projectService.getAllProjects().stream()
                .filter(p -> p.getManagerNric().equals(getCurrentManager().getNric()))
                .anyMatch(existingProject -> projectService.checkDateOverlap(tempProject, existingProject));

            if (overlaps) {
                 System.out.println("Error: The specified application period overlaps with another project you manage. Please enter different dates.");
            } else {
                 break; // Dates are valid and don't overlap
            }
        }

        int maxOfficers = InputUtils.getIntInput(scanner, "Enter Maximum HDB Officer Slots (1-10): ", 1, 10);

        // Delegate creation to the service
        boolean success = projectService.createProject(projectName, neighborhood, flatTypes, openingDate, closingDate, getCurrentManager(), maxOfficers);
        // Success/error message printed by service
    }

    public void editProject() {
        System.out.println("\n--- Edit BTO Project ---");
        // Get projects managed by this manager (filters applied by service)
        List<Project> myProjects = projectService.getManagedProjects(currentUser.getNric());
        if (myProjects.isEmpty()) {
            System.out.println("You are not managing any projects" + (!filterService.getCurrentFilterStatus().contains("Any") ? " matching the current filters." : "."));
            return;
        }

        projectDisplayService.displayProjectList(myProjects, "Select Project to Edit", currentUser);
        Project projectToEdit = projectDisplayService.selectProjectFromList(myProjects, scanner);
        if (projectToEdit == null) return;

        System.out.println("Editing Project: " + projectToEdit.getProjectName() + " (Leave blank to keep current value)");

        // --- Neighborhood ---
        System.out.print("Enter new Neighborhood [" + projectToEdit.getNeighborhood() + "]: ");
        String newNeighborhoodInput = scanner.nextLine().trim();
        String newNeighborhood = newNeighborhoodInput.isEmpty() ? null : newNeighborhoodInput; // Null if blank

        // --- Flat Types (Prices only) ---
        Map<FlatType, FlatTypeDetails> currentFlatTypes = projectToEdit.getFlatTypes();
        // Create a mutable copy to modify prices
        Map<FlatType, FlatTypeDetails> newFlatTypesMap = new HashMap<>();
        currentFlatTypes.forEach((type, details) -> newFlatTypesMap.put(type,
                new FlatTypeDetails(details.getTotalUnits(), details.getAvailableUnits(), details.getSellingPrice())));

        for (FlatType type : FlatType.values()) {
            FlatTypeDetails currentDetails = newFlatTypesMap.get(type);
            if (currentDetails != null) {
                System.out.println("--- Edit " + type.getDisplayName() + " ---");
                double currentPrice = currentDetails.getSellingPrice();
                System.out.print("Enter new selling price [" + String.format("%.2f", currentPrice)
                        + "] (leave blank to keep): $");
                String priceInput = scanner.nextLine().trim();
                if (!priceInput.isEmpty()) {
                    try {
                        double newPrice = Double.parseDouble(priceInput);
                        if (newPrice >= 0) {
                            currentDetails.setSellingPrice(newPrice); // Modify the copy
                        } else {
                            System.out.println("Price cannot be negative. Keeping original price.");
                        }
                    } catch (NumberFormatException e) {
                        System.out.println("Invalid price format. Keeping original price.");
                    }
                }
            }
        }
        // Use the modified map if prices changed, otherwise null
        Map<FlatType, FlatTypeDetails> newFlatTypes = newFlatTypesMap.equals(currentFlatTypes) ? null : newFlatTypesMap;


        // --- Dates ---
        Date originalOpening = projectToEdit.getApplicationOpeningDate();
        Date originalClosing = projectToEdit.getApplicationClosingDate();
        Date newOpeningDate = InputUtils.getDateInput(scanner, "Enter new Opening Date (yyyy-MM-dd) ["
                + DateUtils.formatDate(originalOpening) + "] (leave blank to keep): ", true); // Allow blank
        Date newClosingDate = InputUtils.getDateInput(scanner, "Enter new Closing Date (yyyy-MM-dd) ["
                + DateUtils.formatDate(originalClosing) + "] (leave blank to keep): ", true); // Allow blank

        // --- Max Officer Slots ---
        int currentMaxSlots = projectToEdit.getMaxOfficerSlots();
        int currentApprovedCount = projectToEdit.getApprovedOfficerNrics().size();
        System.out.print("Enter new Max Officer Slots [" + currentMaxSlots + "] (min " + currentApprovedCount
                + ", max 10, leave blank to keep): ");
        String slotsInput = scanner.nextLine().trim();
        int newMaxSlots = -1; // Indicate no change
        if (!slotsInput.isEmpty()) {
            try {
                int inputSlots = Integer.parseInt(slotsInput);
                 if (inputSlots >= currentApprovedCount && inputSlots <= 10) {
                     newMaxSlots = inputSlots;
                 } else {
                     System.out.println("Max slots must be between " + currentApprovedCount + " and 10. Keeping original value.");
                     newMaxSlots = -2; // Indicate invalid input, keep original
                 }
            } catch (NumberFormatException e) {
                System.out.println("Invalid number format. Max slots not changed.");
                newMaxSlots = -2; // Indicate invalid input, keep original
            }
        }
        if (newMaxSlots == -1 || newMaxSlots == -2) { // If blank or invalid
             newMaxSlots = projectToEdit.getMaxOfficerSlots(); // Keep original
        }


        // --- Call Service to Edit ---
        boolean success = projectService.editProjectDetails(projectToEdit, newNeighborhood, newFlatTypes, newOpeningDate, newClosingDate, newMaxSlots);
        // Success/error messages handled by service
    }

    public void deleteProject() {
        System.out.println("\n--- Delete BTO Project ---");
        // Get managed projects (ignoring filters for deletion)
        List<Project> myProjects = projectService.getAllProjects().stream()
                                     .filter(p -> p.getManagerNric().equals(currentUser.getNric()))
                                     .collect(Collectors.toList());
        if (myProjects.isEmpty()) {
            System.out.println("You are not managing any projects.");
            return;
        }

        projectDisplayService.displayProjectList(myProjects, "Select Project to Delete", currentUser);
        Project projectToDelete = projectDisplayService.selectProjectFromList(myProjects, scanner);
        if (projectToDelete == null) return;

        // Confirmation
        boolean confirm = InputUtils.getConfirmation(scanner, "Are you sure you want to permanently delete project '" + projectToDelete.getProjectName()
                + "'? This will also remove associated historical applications/registrations/enquiries.");

        if (confirm) {
            // Delegate deletion to the service (handles checks and cascading)
            boolean success = projectService.deleteProject(projectToDelete);
            // Success/error messages printed by service
        } else {
            System.out.println("Deletion cancelled.");
        }
    }

    public void toggleProjectVisibility() {
        System.out.println("\n--- Toggle Project Visibility ---");
        // Get managed projects (ignoring filters)
        List<Project> myProjects = projectService.getAllProjects().stream()
                                     .filter(p -> p.getManagerNric().equals(currentUser.getNric()))
                                     .collect(Collectors.toList());
        if (myProjects.isEmpty()) {
            System.out.println("You are not managing any projects.");
            return;
        }

        projectDisplayService.displayProjectList(myProjects, "Select Project to Toggle Visibility", currentUser);
        Project projectToToggle = projectDisplayService.selectProjectFromList(myProjects, scanner);
        if (projectToToggle == null) return;

        // Delegate toggle to service
        boolean success = projectService.toggleProjectVisibility(projectToToggle);
        // Message printed by service
    }

    public void viewAllProjects() {
        System.out.println("\n--- View All Projects (Manager View) ---");
        // Get all projects and apply current view filters
        List<Project> allProjects = projectService.getAllProjects();
        List<Project> filteredProjects = filterService.applyFilters(allProjects);
        projectDisplayService.displayProjectList(filteredProjects, "All BTO Projects", currentUser);
    }

    public void viewMyProjects() {
        System.out.println("\n--- View My Managed Projects ---");
        // Service method already gets managed projects and applies filters
        List<Project> myProjects = projectService.getManagedProjects(currentUser.getNric());
        projectDisplayService.displayProjectList(myProjects, "Projects Managed By You", currentUser);
         if (myProjects.isEmpty()) {
             System.out.println("You are not managing any projects" + (!filterService.getCurrentFilterStatus().contains("Any") ? " matching the current filters." : "."));
         }
    }

    public void manageOfficerRegistrations() {
        System.out.println("\n--- Manage HDB Officer Registrations ---");
        // Get managed projects (ignore filters for selection)
        List<Project> myProjects = projectService.getAllProjects().stream()
                                     .filter(p -> p.getManagerNric().equals(currentUser.getNric()))
                                     .collect(Collectors.toList());
        if (myProjects.isEmpty()) {
            System.out.println("You are not managing any projects.");
            return;
        }

        System.out.println("Select project to manage registrations for:");
        projectDisplayService.displayProjectList(myProjects, "Select Project", currentUser);
        Project selectedProject = projectDisplayService.selectProjectFromList(myProjects, scanner);
        if (selectedProject == null) return;

        System.out.println("\n--- Registrations for Project: " + selectedProject.getProjectName() + " ---");
        System.out.println("Officer Slots: " + selectedProject.getApprovedOfficerNrics().size() + " / "
                + selectedProject.getMaxOfficerSlots() + " (Remaining: " + selectedProject.getRemainingOfficerSlots() + ")");

        // Get pending registrations for this project
        List<OfficerRegistration> pendingRegistrations = officerRegistrationService.getPendingRegistrationsForProject(selectedProject.getProjectName());

        System.out.println("\n--- Pending Registrations ---");
        if (pendingRegistrations.isEmpty()) {
            System.out.println("(None)");
        } else {
            Map<String, User> allUsers = userRepository.getAllUsers(); // Get users for name lookup
            for (int i = 0; i < pendingRegistrations.size(); i++) {
                OfficerRegistration reg = pendingRegistrations.get(i);
                User officerUser = allUsers.get(reg.getOfficerNric());
                System.out.printf("%d. NRIC: %s | Name: %-15s | Date: %s\n",
                        i + 1, reg.getOfficerNric(),
                        officerUser != null ? officerUser.getName() : "N/A",
                        DateUtils.formatDate(reg.getRegistrationDate()));
            }

            int choice = InputUtils.getIntInput(scanner, "Enter number to Approve/Reject (or 0 to skip): ", 0, pendingRegistrations.size());
            if (choice >= 1) {
                OfficerRegistration regToProcess = pendingRegistrations.get(choice - 1);
                User officerUser = userRepository.findUserByNric(regToProcess.getOfficerNric()); // Find specific user

                // Validate user is still an officer
                if (!(officerUser instanceof HDBOfficer)) {
                    System.out.println("Error: User " + regToProcess.getOfficerNric()
                            + " is no longer a valid Officer. Rejecting registration.");
                    officerRegistrationService.rejectRegistration(regToProcess);
                    return; // Exit after processing one
                }
                HDBOfficer officer = (HDBOfficer) officerUser;

                // Check for overlap before prompting A/R
                 if (eligibilityService.isOfficerHandlingOverlappingProject(officer, selectedProject)) {
                     System.out.println("Cannot approve. Officer is already handling another project with overlapping dates.");
                     // Optionally auto-reject or just prevent approval? Let's prevent and let manager decide.
                 } else {
                     System.out.print("Approve or Reject? (A/R): ");
                     String action = scanner.nextLine().trim().toUpperCase();

                     if (action.equals("A")) {
                         // Approve via service (handles slot check again, updates project and reg)
                         boolean success = officerRegistrationService.approveRegistration(regToProcess, selectedProject);
                         // Message printed by service
                     } else if (action.equals("R")) {
                         // Reject via service
                         boolean success = officerRegistrationService.rejectRegistration(regToProcess);
                         // Message printed by service
                     } else {
                         System.out.println("Invalid action.");
                     }
                 }
            }
        }

        // Display other statuses for context
        System.out.println("\n--- Approved Officers for this Project ---");
        List<String> approvedNrics = selectedProject.getApprovedOfficerNrics();
        if (approvedNrics.isEmpty()) {
            System.out.println("(None)");
        } else {
            Map<String, User> allUsers = userRepository.getAllUsers();
            approvedNrics.forEach(nric -> System.out.println("- NRIC: " + nric
                    + (allUsers.containsKey(nric) ? " (Name: " + allUsers.get(nric).getName() + ")" : " (Name: N/A)")));
        }

        System.out.println("\n--- Rejected Registrations for this Project ---");
        List<OfficerRegistration> rejected = officerRegistrationService.getRegistrationsByProject(selectedProject.getProjectName())
                .stream()
                .filter(r -> r.getStatus() == OfficerRegistrationStatus.REJECTED)
                .collect(Collectors.toList());
        if (rejected.isEmpty()) {
            System.out.println("(None)");
        } else {
            rejected.forEach(reg -> System.out.println(
                    "- NRIC: " + reg.getOfficerNric() + " | Date: " + DateUtils.formatDate(reg.getRegistrationDate())));
        }
    }

    public void manageApplications() {
        System.out.println("\n--- Manage BTO Applications ---");
        // Get managed projects (ignore filters for selection)
        List<Project> myProjects = projectService.getAllProjects().stream()
                                     .filter(p -> p.getManagerNric().equals(currentUser.getNric()))
                                     .collect(Collectors.toList());
        if (myProjects.isEmpty()) {
            System.out.println("You are not managing any projects.");
            return;
        }

        System.out.println("Select project to manage applications for:");
        projectDisplayService.displayProjectList(myProjects, "Select Project", currentUser);
        Project selectedProject = projectDisplayService.selectProjectFromList(myProjects, scanner);
        if (selectedProject == null) return;

        System.out.println("\n--- Applications for Project: " + selectedProject.getProjectName() + " ---");

        // Get all applications for the project
        List<BTOApplication> projectApplications = applicationService.getAllApplications().values().stream()
                .filter(app -> app.getProjectName().equals(selectedProject.getProjectName()))
                .sorted(Comparator.comparing(BTOApplication::getApplicationDate))
                .collect(Collectors.toList());

        if (projectApplications.isEmpty()) {
            System.out.println("No applications found for this project.");
            return;
        }

        // Filter for PENDING applications
        List<BTOApplication> pendingApps = projectApplications.stream()
                .filter(app -> app.getStatus() == ApplicationStatus.PENDING)
                .collect(Collectors.toList());

        System.out.println("--- Pending Applications ---");
        if (pendingApps.isEmpty()) {
            System.out.println("(None)");
        } else {
            Map<String, User> allUsers = userRepository.getAllUsers(); // For name lookup
            for (int i = 0; i < pendingApps.size(); i++) {
                BTOApplication app = pendingApps.get(i);
                User applicant = allUsers.get(app.getApplicantNric());
                System.out.printf("%d. NRIC: %s | Name: %-15s | Type: %-8s | Date: %s\n",
                        i + 1, app.getApplicantNric(),
                        applicant != null ? applicant.getName() : "N/A",
                        app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A",
                        DateUtils.formatDate(app.getApplicationDate()));
            }

            int choice = InputUtils.getIntInput(scanner, "Enter number to Approve/Reject (or 0 to skip): ", 0, pendingApps.size());
            if (choice >= 1) {
                BTOApplication appToProcess = pendingApps.get(choice - 1);
                User applicantUser = userRepository.findUserByNric(appToProcess.getApplicantNric());

                // Validate applicant exists and is Applicant type
                if (!(applicantUser instanceof Applicant)) {
                    System.out.println("Error: Applicant data not found or invalid for NRIC "
                            + appToProcess.getApplicantNric() + ". Rejecting application.");
                    applicationService.rejectApplication(appToProcess); // Reject via service
                    return; // Exit after processing one
                }
                // Applicant applicant = (Applicant) applicantUser; // Not strictly needed here

                System.out.print("Approve or Reject? (A/R): ");
                String action = scanner.nextLine().trim().toUpperCase();

                if (action.equals("A")) {
                    // Approve via service (handles checks)
                    boolean success = applicationService.approveApplication(appToProcess);
                    // Message printed by service
                } else if (action.equals("R")) {
                    // Reject via service
                    boolean success = applicationService.rejectApplication(appToProcess);
                    // Message printed by service
                } else {
                    System.out.println("Invalid action.");
                }
            }
        }

        // Display other statuses
        System.out.println("\n--- Other Application Statuses ---");
        Map<String, User> allUsers = userRepository.getAllUsers(); // For name lookup
        projectApplications.stream()
                .filter(app -> app.getStatus() != ApplicationStatus.PENDING)
                .forEach(app -> {
                    User applicant = allUsers.get(app.getApplicantNric());
                    System.out.printf("- NRIC: %s | Name: %-15s | Type: %-8s | Status: %s\n",
                            app.getApplicantNric(),
                            applicant != null ? applicant.getName() : "N/A",
                            app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A",
                            app.getStatus());
                });
    }

    public void manageWithdrawalRequests() {
        System.out.println("\n--- Manage Withdrawal Requests ---");
        // Get names of projects managed by current user
        List<String> myProjectNames = projectService.getAllProjects().stream()
                .filter(p -> p.getManagerNric().equals(currentUser.getNric()))
                .map(Project::getProjectName)
                .collect(Collectors.toList());

        if (myProjectNames.isEmpty()) {
            System.out.println("You are not managing any projects.");
            return;
        }

        // Find applications pending withdrawal for managed projects
        List<BTOApplication> pendingWithdrawals = applicationService.getAllApplications().values().stream()
                .filter(app -> app.getStatus() == ApplicationStatus.PENDING_WITHDRAWAL)
                .filter(app -> myProjectNames.contains(app.getProjectName()))
                .sorted(Comparator.comparing(BTOApplication::getApplicationDate))
                .collect(Collectors.toList());

        if (pendingWithdrawals.isEmpty()) {
            System.out.println("No pending withdrawal requests found for the projects you manage.");
            return;
        }

        System.out.println("--- Pending Withdrawal Requests ---");
        Map<String, User> allUsers = userRepository.getAllUsers(); // For name lookup
        for (int i = 0; i < pendingWithdrawals.size(); i++) {
            BTOApplication app = pendingWithdrawals.get(i);
            User applicantUser = allUsers.get(app.getApplicantNric());
            ApplicationStatus statusBefore = app.getStatusBeforeWithdrawal(); // Get stored status

            System.out.printf("%d. NRIC: %s | Name: %-15s | Project: %-15s | Type: %-8s | App Date: %s | Original Status: %s\n",
                    i + 1,
                    app.getApplicantNric(),
                    applicantUser != null ? applicantUser.getName() : "N/A",
                    app.getProjectName(),
                    app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A",
                    DateUtils.formatDate(app.getApplicationDate()),
                    statusBefore != null ? statusBefore : "(Unknown/Infer)"); // Indicate if status was stored
        }

        int choice = InputUtils.getIntInput(scanner, "Enter number to Approve/Reject withdrawal (or 0 to skip): ", 0, pendingWithdrawals.size());
        if (choice >= 1) {
            BTOApplication appToProcess = pendingWithdrawals.get(choice - 1);
            User applicantUser = userRepository.findUserByNric(appToProcess.getApplicantNric());

            // Validate applicant
            if (!(applicantUser instanceof Applicant)) {
                System.out.println("Error: Applicant data not found or invalid for NRIC "
                        + appToProcess.getApplicantNric() + ". Cannot process withdrawal.");
                return; // Exit after processing one
            }
            // Applicant applicant = (Applicant) applicantUser; // Not needed directly here

            System.out.print("Approve or Reject withdrawal request? (A/R): ");
            String action = scanner.nextLine().trim().toUpperCase();

            if (action.equals("A")) {
                // Approve via service (handles unit release, status updates)
                boolean success = applicationService.approveWithdrawal(appToProcess);
                // Message printed by service
            } else if (action.equals("R")) {
                // Reject via service (handles reverting status)
                boolean success = applicationService.rejectWithdrawal(appToProcess);
                // Message printed by service
            } else {
                System.out.println("Invalid action.");
            }
        }
    }

    public void generateApplicantReport() {
        System.out.println("\n--- Generate Applicant Report (Booked Flats) ---");

        System.out.println("Filter by project:");
        System.out.println("1. All Projects Managed By You (Respecting View Filters)");
        System.out.println("2. A Specific Project Managed By You");
        System.out.println("0. Cancel");
        int projectFilterChoice = InputUtils.getIntInput(scanner, "Enter choice: ", 0, 2);

        List<String> projectNamesToReportOn;
        if (projectFilterChoice == 0) return;

        if (projectFilterChoice == 1) {
            // Get managed projects respecting current view filters
            projectNamesToReportOn = projectService.getManagedProjects(currentUser.getNric())
                                        .stream()
                                        .map(Project::getProjectName)
                                        .collect(Collectors.toList());
            if (projectNamesToReportOn.isEmpty()) {
                 System.out.println("You are not managing any projects" + (!filterService.getCurrentFilterStatus().contains("Any") ? " matching the current filters." : "."));
                 return;
            }
            System.out.println("Reporting on all projects you manage"
                    + (!filterService.getCurrentFilterStatus().contains("Any") ? " (matching current view filters)." : "."));
        } else { // Specific project
            // Get managed projects ignoring view filters for selection
            List<Project> myProjectsAll = projectService.getAllProjects().stream()
                                     .filter(p -> p.getManagerNric().equals(currentUser.getNric()))
                                     .collect(Collectors.toList());
             if (myProjectsAll.isEmpty()) {
                System.out.println("You are not managing any projects.");
                return;
            }
            projectDisplayService.displayProjectList(myProjectsAll, "Select Specific Project to Report On", currentUser);
            Project specificProject = projectDisplayService.selectProjectFromList(myProjectsAll, scanner);
            if (specificProject == null) return;
            projectNamesToReportOn = List.of(specificProject.getProjectName());
            System.out.println("Reporting specifically for project: " + specificProject.getProjectName());
        }

        // Get report filters
        System.out.print("Filter report by Flat Type (TWO_ROOM, THREE_ROOM, or leave blank for all): ");
        String typeStr = scanner.nextLine().trim();
        FlatType filterReportFlatType = typeStr.isEmpty() ? null : FlatType.fromString(typeStr);
        if (!typeStr.isEmpty() && filterReportFlatType == null) {
            System.out.println("Invalid flat type entered. Reporting for all types.");
        }

        System.out.print("Filter report by Marital Status (SINGLE, MARRIED, or leave blank for all): ");
        String maritalStr = scanner.nextLine().trim().toUpperCase();
        MaritalStatus filterMaritalStatus = null;
        if (!maritalStr.isEmpty()) {
            try {
                filterMaritalStatus = MaritalStatus.valueOf(maritalStr);
            } catch (IllegalArgumentException e) {
                System.out.println("Invalid marital status. Reporting for all statuses.");
            }
        }

        int minAge = InputUtils.getIntInput(scanner, "Filter report by Minimum Age (e.g., 21, or 0 for no minimum): ", 0, 120);
        int maxAge = InputUtils.getIntInput(scanner, "Filter report by Maximum Age (e.g., 40, or 0 for no maximum): ", 0, 120);

        // Generate report data using service
        List<BTOApplication> reportData = reportService.generateBookedApplicantReport(
                projectNamesToReportOn, filterReportFlatType, filterMaritalStatus, minAge, maxAge);

        // Display report using service
        reportService.displayApplicantReport(reportData, filterReportFlatType, filterMaritalStatus, minAge, maxAge);
    }

    public void viewAllEnquiries() {
        System.out.println("\n--- View Enquiries (ALL Projects) ---");
        List<Enquiry> allEnquiries = enquiryService.getAllEnquiries(); // Already sorted by service

        if (allEnquiries.isEmpty()) {
            System.out.println("No enquiries found in the system.");
            return;
        }

        allEnquiries.forEach(e -> {
            printEnquiryDetails(e);
            System.out.println("----------------------------------------");
        });
    }

    public void viewAndReplyToManagedEnquiries() {
        System.out.println("\n--- View/Reply Enquiries (Managed Projects) ---");
        // Get names of projects managed by current user, respecting view filters
        List<String> myManagedProjectNames = projectService.getManagedProjects(currentUser.getNric())
                                                .stream()
                                                .map(Project::getProjectName)
                                                .collect(Collectors.toList());

        if (myManagedProjectNames.isEmpty()) {
             System.out.println("You are not managing any projects" + (!filterService.getCurrentFilterStatus().contains("Any") ? " matching the current filters." : "."));
            return;
        }

        // Get unreplied enquiries for these projects
        List<Enquiry> unrepliedEnquiries = enquiryService.getUnrepliedEnquiriesForProjects(myManagedProjectNames);

        System.out.println("--- Unreplied Enquiries (Managed Projects" + (!filterService.getCurrentFilterStatus().contains("Any") ? " - Filtered" : "") + ") ---");
        if (unrepliedEnquiries.isEmpty()) {
            System.out.println("(None)");
        } else {
            for (int i = 0; i < unrepliedEnquiries.size(); i++) {
                Enquiry e = unrepliedEnquiries.get(i);
                System.out.printf("%d. ", i + 1);
                printEnquiryDetails(e); // Use helper to print
                System.out.println("---");
            }
            int choice = InputUtils.getIntInput(scanner, "Enter the number of the enquiry to reply to (or 0 to skip): ", 0, unrepliedEnquiries.size());
            if (choice >= 1) {
                Enquiry enquiryToReply = unrepliedEnquiries.get(choice - 1);
                String replyText = InputUtils.getStringInput(scanner, "Enter your reply: ", false);
                // Reply via service
                boolean success = enquiryService.replyToEnquiry(enquiryToReply, replyText, currentUser);
                // Message printed by service
            }
        }

        // Get replied enquiries for these projects
        List<Enquiry> repliedEnquiries = enquiryService.getRepliedEnquiriesForProjects(myManagedProjectNames);
        System.out.println("\n--- Replied Enquiries (Managed Projects" + (!filterService.getCurrentFilterStatus().contains("Any") ? " - Filtered" : "") + ") ---");
        if (repliedEnquiries.isEmpty()) {
            System.out.println("(None)");
        } else {
            repliedEnquiries.forEach(e -> {
                printEnquiryDetails(e);
                System.out.println("----------------------------------------");
            });
        }
    }

    // Helper method to print enquiry details consistently
    private void printEnquiryDetails(Enquiry e) {
        if (e == null) return;
        // Optional: Look up applicant name
        User applicant = userRepository.findUserByNric(e.getApplicantNric());
        String applicantNameInfo = (applicant != null) ? " (" + applicant.getName() + ")" : "";

        System.out.printf("ID: %s | Project: %s | Applicant: %s%s | Date: %s\n",
                e.getEnquiryId(), e.getProjectName(), e.getApplicantNric(), applicantNameInfo, DateUtils.formatDate(e.getEnquiryDate()));
        System.out.println("   Enquiry: " + e.getEnquiryText());
        if (e.isReplied()) {
             // Optional: Look up replier name
             User replier = userRepository.findUserByNric(e.getRepliedByNric());
             String replierNameInfo = (replier != null) ? " (" + replier.getName() + ")" : "";
            System.out.printf("   Reply (by %s%s on %s): %s\n",
                    e.getRepliedByNric() != null ? e.getRepliedByNric() : "N/A",
                    replierNameInfo,
                    e.getReplyDate() != null ? DateUtils.formatDate(e.getReplyDate()) : "N/A",
                    e.getReplyText());
        } else {
            System.out.println("   Reply: (Pending)");
        }
    }

    // Method to apply filters (delegated to FilterService)
    public void applyFilters() {
        // Same implementation as in ApplicantController
        System.out.println("\n--- Apply/Clear Filters ---");
        System.out.print("Enter neighborhood to filter by (current: "
                + (filterService.getLocationFilter() == null ? "Any" : filterService.getLocationFilter()) + ", leave blank to clear): ");
        String loc = scanner.nextLine().trim();
        filterService.setLocationFilter(loc);

        System.out.print("Enter flat type to filter by (TWO_ROOM, THREE_ROOM, current: "
                + (filterService.getFlatTypeFilter() == null ? "Any" : filterService.getFlatTypeFilter()) + ", leave blank to clear): ");
        String typeStr = scanner.nextLine().trim();
        if (typeStr.isEmpty()) {
            filterService.setFlatTypeFilter(null);
        } else {
            try {
                FlatType parsedType = FlatType.fromString(typeStr);
                if (parsedType != null) {
                    filterService.setFlatTypeFilter(parsedType);
                } else {
                    System.out.println("Invalid flat type entered. Filter not changed.");
                }
            } catch (IllegalArgumentException e) {
                System.out.println("Invalid flat type format. Filter not changed.");
            }
        }
        System.out.println("Filters updated. Current filters: " + filterService.getCurrentFilterStatus());
    }

     // Method to change password (delegated to AuthService)
     public boolean changePassword() {
         // Same implementation as in ApplicantController
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

         return authService.changePassword(currentUser, oldPassword, newPassword);
     }
}
