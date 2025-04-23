package Controllers;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Scanner;
import java.util.stream.Collectors;

import Enums.ApplicationStatus;
import Enums.FlatType;
import Enums.OfficerRegistrationStatus;
import Models.BTOApplication;
import Models.Enquiry; // Corrected import case
import Models.FlatTypeDetails;
import Models.HDBManager;
import Models.OfficerRegistration;
import Models.Project;
import Models.User;
import Services.IApplicationService;
import Services.IEnquiryService;
import Services.IOfficerRegistrationService;
import Services.IProjectService;
import Services.IUserService;
import Utils.DateUtils;

// Handles Manager actions related to Project CRUD and visibility
public class ProjectManagerController extends BaseController {

     private final IEnquiryService enquiryService; // Needed for deletion cleanup

    public ProjectManagerController(IUserService userService, IProjectService projectService,
                                   IApplicationService applicationService, IOfficerRegistrationService officerRegistrationService,
                                   IEnquiryService enquiryService, // Inject enquiry service
                                   User currentUser, Scanner scanner, AuthController authController) {
        super(userService, projectService, applicationService, officerRegistrationService, currentUser, scanner, authController);
        this.enquiryService = enquiryService;
         if (!(currentUser instanceof HDBManager)) {
            throw new IllegalArgumentException("ProjectManagerController requires an HDBManager user.");
        }
    }

    public void createProject() {
        HDBManager manager = (HDBManager) currentUser; // Cast is safe due to constructor check

        System.out.println("\n--- Create New BTO Project ---");

        String projectName;
        while (true) {
            System.out.print("Enter Project Name: ");
            projectName = scanner.nextLine().trim();
            if (projectName.isEmpty()) {
                System.out.println("Project name cannot be empty.");
            } else if (projectService.findProjectByName(projectName) != null) { // Check using service
                System.out.println("Project name already exists. Please choose a unique name.");
            } else {
                break;
            }
        }

        System.out.print("Enter Neighborhood: ");
        String neighborhood = scanner.nextLine().trim();
        if (neighborhood.isEmpty()) {
            System.out.println("Neighborhood cannot be empty. Creation cancelled.");
            return;
        }

        // Get Flat Type Details
        Map<FlatType, FlatTypeDetails> flatTypes = new HashMap<>();
        System.out.println("--- Flat Type Details ---");
        int units2Room = getIntInput("Enter total number of 2-Room units (0 if none): ", 0, 9999);
        if (units2Room > 0) {
            double price2Room = getDoubleInput("Enter selling price for 2-Room units: $", 0, Double.MAX_VALUE);
            // Initial available units = total units
            flatTypes.put(FlatType.TWO_ROOM, new FlatTypeDetails(units2Room, units2Room, price2Room));
        }
        int units3Room = getIntInput("Enter total number of 3-Room units (0 if none): ", 0, 9999);
        if (units3Room > 0) {
            double price3Room = getDoubleInput("Enter selling price for 3-Room units: $", 0, Double.MAX_VALUE);
            // Initial available units = total units
            flatTypes.put(FlatType.THREE_ROOM, new FlatTypeDetails(units3Room, units3Room, price3Room));
        }

        if (flatTypes.isEmpty()) {
            System.out.println(
                    "Error: Project must have at least one type of flat (2-Room or 3-Room). Creation cancelled.");
            return;
        }

        // Get and Validate Dates, checking for overlap with manager's *other* projects
        Date openingDate;
        Date closingDate;
        while (true) {
            openingDate = getDateInput("Enter Application Opening Date (yyyy-MM-dd): ", false); // Not blank
            closingDate = getDateInput("Enter Application Closing Date (yyyy-MM-dd): ", false); // Not blank

            if (openingDate == null || closingDate == null) {
                // Should not happen with allowBlank=false, but check anyway
                System.out.println("Dates cannot be empty. Please re-enter.");
                continue;
            }
            if (closingDate.before(openingDate)) {
                System.out.println("Closing date cannot be before opening date. Please re-enter.");
                continue;
            }

            // Check overlap with *other* projects managed by the same manager
            Project proposedProjectDates = new Project("__temp__", "__temp__", flatTypes, openingDate, closingDate, manager.getNric(), 0, null, true); // Temporary project for date check
            boolean overlapsWithActive = projectService.getProjectsManagedBy(manager.getNric()) // Get manager's projects via service
                    .stream()
                    // No need to filter out the project being created as it doesn't exist yet
                    .anyMatch(existingProject -> checkDateOverlap(proposedProjectDates, existingProject)); // Use BaseController helper

            if (overlapsWithActive) {
                System.out.println("Error: The specified application period overlaps with another project you manage.");
                System.out.println("Please enter different dates or manage the visibility/dates of the existing project.");
            } else {
                break; // Dates are valid and don't overlap
            }
        }

        // Get Max Officer Slots
        int maxOfficers = getIntInput("Enter Maximum HDB Officer Slots (1-10): ", 1, 10);

        // Create Project object - initially no approved officers, visibility off
        Project newProject = new Project(projectName, neighborhood, flatTypes, openingDate, closingDate,
                manager.getNric(), maxOfficers, new ArrayList<>(), false); // Visibility false by default

        projectService.addProject(newProject); // Add via service
        System.out.println("Project '" + projectName + "' created successfully. Visibility is currently OFF.");
        projectService.saveProjects(projectService.getAllProjects()); // Save immediately
    }

     public void editProject() {
        System.out.println("\n--- Edit BTO Project ---");
        // Get projects managed by the current user (manager) using the service
        List<Project> myProjects = getManagedProjects(false); // Use helper that filters by manager NRIC
        if (myProjects.isEmpty()) {
            // Message is printed within getManagedProjects
            return;
        }

        viewAndSelectProject(myProjects, "Select Project to Edit");
        Project projectToEdit = selectProjectFromList(myProjects);
        if (projectToEdit == null) return; // User cancelled

        System.out.println("Editing Project: " + projectToEdit.getProjectName() + " (Leave blank to keep current value)");

        // Edit Neighborhood
        System.out.print("Enter new Neighborhood [" + projectToEdit.getNeighborhood() + "]: ");
        String newNeighborhood = scanner.nextLine().trim();
        if (!newNeighborhood.isEmpty()) {
            projectToEdit.setNeighborhood(newNeighborhood);
        }

        // Edit Flat Type Prices (cannot change types or total units easily after creation)
        // Get the read-only view to know which types exist
        Map<FlatType, FlatTypeDetails> existingFlatTypesView = projectToEdit.getFlatTypes();

        // Iterate through all possible FlatType enum values
        for (FlatType type : FlatType.values()) {
            // Check if the project actually has this flat type
            if (existingFlatTypesView.containsKey(type)) {
                 // Get the *mutable* details object for this specific type from the project
                FlatTypeDetails currentDetails = projectToEdit.getMutableFlatTypeDetails(type);
                if (currentDetails != null) { // Should exist if key is present, but safety check
                    System.out.println("--- Edit " + type.getDisplayName() + " ---");
                    System.out.print("Enter new selling price [" + String.format("%.2f", currentDetails.getSellingPrice())
                            + "] (leave blank to keep): $");
                    String priceInput = scanner.nextLine().trim();
                    if (!priceInput.isEmpty()) {
                        try {
                            double newPrice = Double.parseDouble(priceInput);
                            if (newPrice >= 0) {
                                // Update the selling price on the mutable details object
                                currentDetails.setSellingPrice(newPrice);
                            } else {
                                System.out.println("Price cannot be negative. Keeping original price.");
                            }
                        } catch (NumberFormatException e) {
                            System.out.println("Invalid price format. Keeping original price.");
                        }
                    }
                }
            }
        }
        // No need to call projectToEdit.setFlatTypes(...) as we modified the internal details directly

        // Edit Dates (check for overlap)
        Date originalOpening = projectToEdit.getApplicationOpeningDate();
        Date originalClosing = projectToEdit.getApplicationClosingDate();
        Date newOpeningDate = getDateInput("Enter new Opening Date (yyyy-MM-dd) ["
                + DateUtils.formatDate(originalOpening) + "] (leave blank to keep): ", true); // Allow blank
        Date newClosingDate = getDateInput("Enter new Closing Date (yyyy-MM-dd) ["
                + DateUtils.formatDate(originalClosing) + "] (leave blank to keep): ", true); // Allow blank

        // Determine final dates, considering blanks
        Date finalOpening = (newOpeningDate != null) ? newOpeningDate : originalOpening;
        Date finalClosing = (newClosingDate != null) ? newClosingDate : originalClosing;

        boolean datesChanged = (newOpeningDate != null || newClosingDate != null);
        boolean datesValid = true;

        // Validate final dates
        if (finalClosing.before(finalOpening)) {
            System.out.println("Error: Closing date cannot be before opening date. Dates not updated.");
            datesValid = false;
        }

        // If dates changed and are valid so far, check for overlap with *other* projects
        if (datesChanged && datesValid) {
            // Create a temporary project object with the new dates for overlap check
             Project proposedProjectDates = new Project(
                    projectToEdit.getProjectName(), projectToEdit.getNeighborhood(), projectToEdit.getFlatTypes(), // Use current types
                    finalOpening, finalClosing, projectToEdit.getManagerNric(), projectToEdit.getMaxOfficerSlots(),
                    projectToEdit.getApprovedOfficerNrics(), projectToEdit.isVisible());

            boolean overlapsWithOther = projectService.getProjectsManagedBy(currentUser.getNric())
                    .stream()
                    .filter(p -> !p.getProjectName().equals(projectToEdit.getProjectName())) // Exclude self
                    .anyMatch(otherProject -> checkDateOverlap(proposedProjectDates, otherProject)); // Use BaseController helper

            if (overlapsWithOther) {
                System.out.println("Error: The new application period overlaps with another project you manage. Dates not updated.");
                datesValid = false;
            }
        }

        // Apply date changes if valid
        if (datesValid) {
            if (newOpeningDate != null) projectToEdit.setApplicationOpeningDate(newOpeningDate);
            if (newClosingDate != null) projectToEdit.setApplicationClosingDate(newClosingDate);
            if (datesChanged) System.out.println("Application dates updated.");
        }

        // Edit Max Officer Slots
        int currentMaxSlots = projectToEdit.getMaxOfficerSlots();
        int currentApprovedCount = projectToEdit.getApprovedOfficerNrics().size();
        // Minimum allowed slots is the number currently approved
        int minSlots = currentApprovedCount;
        System.out.print("Enter new Max Officer Slots [" + currentMaxSlots + "] (min " + minSlots
                + ", max 10, leave blank to keep): ");
        String slotsInput = scanner.nextLine().trim();
        if (!slotsInput.isEmpty()) {
            try {
                int newMaxSlots = Integer.parseInt(slotsInput);
                // Use the project's setter which includes validation
                projectToEdit.setMaxOfficerSlots(newMaxSlots); // Setter handles check >= approved count and range 1-10
                 // If setter printed an error, that's fine. If it succeeded, update was done.
            } catch (NumberFormatException e) {
                System.out.println("Invalid number format. Max slots not changed.");
            }
        }

        System.out.println("Project details update attempt complete.");
        projectService.saveProjects(projectService.getAllProjects()); // Save changes
    }

     public void deleteProject() {
        System.out.println("\n--- Delete BTO Project ---");
        List<Project> myProjects = getManagedProjects(false);
        if (myProjects.isEmpty()) return;

        viewAndSelectProject(myProjects, "Select Project to Delete");
        Project projectToDelete = selectProjectFromList(myProjects);
        if (projectToDelete == null) return;

        // Check for active associations using services
        boolean hasActiveApplications = applicationService.getApplicationsByProject(projectToDelete.getProjectName())
            .stream()
            .anyMatch(app -> app.getStatus() == ApplicationStatus.PENDING ||
                             app.getStatus() == ApplicationStatus.SUCCESSFUL ||
                             app.getStatus() == ApplicationStatus.BOOKED ||
                             app.getStatus() == ApplicationStatus.PENDING_WITHDRAWAL);

        boolean hasActiveRegistrations = officerRegistrationService.getRegistrationsByProject(projectToDelete.getProjectName())
             .stream()
             .anyMatch(reg -> reg.getStatus() == OfficerRegistrationStatus.PENDING ||
                              reg.getStatus() == OfficerRegistrationStatus.APPROVED);

        if (hasActiveApplications || hasActiveRegistrations) {
            System.out.println("Error: Cannot delete project '" + projectToDelete.getProjectName() + "'.");
            if (hasActiveApplications) System.out.println("- It has active BTO applications (Pending/Successful/Booked/PendingWithdrawal).");
            if (hasActiveRegistrations) System.out.println("- It has active Officer registrations (Pending/Approved).");
            System.out.println("Resolve these associations (e.g., reject applications/registrations, wait for booking/withdrawal) before deleting.");
            return;
        }

        // Confirmation
        System.out.print("Are you sure you want to permanently delete project '" + projectToDelete.getProjectName()
                + "'? This will also remove associated historical applications, registrations, and enquiries. (yes/no): ");
        String confirm = scanner.nextLine().trim().toLowerCase();

        if (confirm.equals("yes")) {
            String deletedProjectName = projectToDelete.getProjectName();

            // 1. Remove the project itself
            if (projectService.removeProject(projectToDelete)) { // Use service
                System.out.println("Project '" + deletedProjectName + "' deleted successfully.");
                projectService.saveProjects(projectService.getAllProjects()); // Save project list

                // 2. Remove associated applications
                List<String> appIdsToRemove = applicationService.getApplicationsByProject(deletedProjectName)
                                                .stream()
                                                .map((BTOApplication app) -> app.getApplicationId())
                                                .collect(Collectors.toList());
                int removedAppCount = 0;
                for (String appId : appIdsToRemove) {
                    if (applicationService.removeApplication(appId)) {
                        removedAppCount++;
                    }
                }
                if (removedAppCount > 0) {
                    System.out.println("Removed " + removedAppCount + " associated applications.");
                    applicationService.saveApplications(applicationService.getAllApplications()); // Save changes
                }

                // 3. Remove associated officer registrations
                List<String> regIdsToRemove = officerRegistrationService.getRegistrationsByProject(deletedProjectName)
                                                .stream()
                                                .map((OfficerRegistration oR) -> oR.getRegistrationId())
                                                .collect(Collectors.toList());
                int removedRegCount = 0;
                for (String regId : regIdsToRemove) {
                     if (officerRegistrationService.removeRegistration(regId)) {
                         removedRegCount++;
                     }
                }
                if (removedRegCount > 0) {
                    System.out.println("Removed " + removedRegCount + " associated officer registrations.");
                    officerRegistrationService.saveOfficerRegistrations(officerRegistrationService.getAllRegistrations()); // Save changes
                }

                // 4. Remove associated enquiries
                List<String> enqIdsToRemove = enquiryService.getEnquiriesByProject(deletedProjectName)
                                                .stream()
                                                .map((Enquiry e) -> e.getEnquiryId())
                                                .collect(Collectors.toList());
                int removedEnqCount = 0;
                 for (String enqId : enqIdsToRemove) {
                      if (enquiryService.removeEnquiry(enqId)) {
                          removedEnqCount++;
                      }
                 }
                if (removedEnqCount > 0) {
                    System.out.println("Removed " + removedEnqCount + " associated enquiries.");
                    enquiryService.saveEnquiries(enquiryService.getAllEnquiries()); // Save changes
                }

            } else {
                System.err.println("Error: Failed to remove project from service layer.");
            }
        } else {
            System.out.println("Deletion cancelled.");
        }
    }

    public void toggleProjectVisibility() {
        System.out.println("\n--- Toggle Project Visibility ---");
        List<Project> myProjects = getManagedProjects(false); // Get only managed projects
        if (myProjects.isEmpty()) return;

        viewAndSelectProject(myProjects, "Select Project to Toggle Visibility");
        Project projectToToggle = selectProjectFromList(myProjects);

        if (projectToToggle != null) {
            boolean currentVisibility = projectToToggle.isVisible();
            projectToToggle.setVisibility(!currentVisibility); // Toggle the state
            System.out.println("Project '" + projectToToggle.getProjectName() + "' visibility toggled to "
                    + (projectToToggle.isVisible() ? "ON" : "OFF") + ".");
            projectService.saveProjects(projectService.getAllProjects()); // Save the change
        }
    }

     public void viewAllProjects() {
        System.out.println("\n--- View All Projects (Manager View) ---");
        // Manager view ignores visibility, eligibility, availability, period checks
        List<Project> displayProjects = getFilteredProjects(false, false, false, false, false);
        viewAndSelectProject(displayProjects, "All BTO Projects (Manager View)");
    }

    public void viewMyProjects() {
        System.out.println("\n--- View My Managed Projects ---");
        // Use the helper that applies filters *and* manager NRIC
        List<Project> myProjects = getManagedProjects(true);
        viewAndSelectProject(myProjects, "Projects Managed By You");
    }

    // Helper specific to Manager context to get their projects, optionally applying user filters
    private List<Project> getManagedProjects(boolean applyUserFilters) {
        // Get all projects managed by current user (Manager)
        List<Project> managed = projectService.getProjectsManagedBy(currentUser.getNric());

        // Apply view filters (location, flat type) if requested
        if (applyUserFilters) {
            managed = managed.stream()
                .filter(p -> filterLocation == null || p.getNeighborhood().equalsIgnoreCase(filterLocation))
                .filter(p -> filterFlatType == null || p.getFlatTypes().containsKey(filterFlatType))
                .collect(Collectors.toList());
        }

        // Sort the result
        managed.sort(Comparator.comparing((Project p) -> p.getProjectName())); // Sort by project name

        // Print message if list is empty
        if (managed.isEmpty()) {
            String filterMsg = (applyUserFilters && (filterLocation != null || filterFlatType != null))
                                ? " matching the current filters."
                                : ".";
            System.out.println("You are not managing any projects" + filterMsg);
        }
        return managed;
    }
}