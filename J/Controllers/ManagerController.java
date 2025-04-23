package Controllers;

import java.util.stream.Collectors;
import java.util.List;
import java.util.HashMap;
import java.util.ArrayList;
import java.util.Map;
import java.util.Comparator;
import java.util.Scanner;
import java.util.Date;

import Enums.FlatType;
import Enums.OfficerRegistrationStatus;
import Enums.ApplicationStatus;
import Enums.MaritalStatus;

import Models.Project;
import Models.BTOApplication;
import Models.Enquiry;
import Models.OfficerRegistration;
import Models.User;
import Models.Applicant;
import Models.HDBOfficer;
import Models.FlatTypeDetails;
import Models.HDBManager;
import Services.ApplicationService;
import Services.EnquiryService;
import Services.OfficerRegistrationService;
import Services.ProjectService;
import Utils.DateUtils;

public class ManagerController extends BaseController {

    public ManagerController(Map<String, User> users, List<Project> projects, Map<String, BTOApplication> applications,
            List<Enquiry> enquiries, Map<String, OfficerRegistration> officerRegistrations, User currentUser,
            Scanner scanner, AuthController authController) {
        super(users, projects, applications, enquiries, officerRegistrations, currentUser, scanner, authController);
    }

    public void createProject() {
        HDBManager manager = (HDBManager) currentUser;

        System.out.println("\n--- Create New BTO Project ---");

        String projectName;
        while (true) {
            System.out.print("Enter Project Name: ");
            projectName = scanner.nextLine().trim();
            if (projectName.isEmpty()) {
                System.out.println("Project name cannot be empty.");
            } else if (findProjectByName(projectName) != null) {
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

        Map<FlatType, FlatTypeDetails> flatTypes = new HashMap<>();
        System.out.println("--- Flat Type Details ---");
        int units2Room = getIntInput("Enter total number of 2-Room units (0 if none): ", 0, 9999);
        if (units2Room > 0) {
            double price2Room = getDoubleInput("Enter selling price for 2-Room units: $", 0, Double.MAX_VALUE);
            flatTypes.put(FlatType.TWO_ROOM, new FlatTypeDetails(units2Room, units2Room, price2Room));
        }
        int units3Room = getIntInput("Enter total number of 3-Room units (0 if none): ", 0, 9999);
        if (units3Room > 0) {
            double price3Room = getDoubleInput("Enter selling price for 3-Room units: $", 0, Double.MAX_VALUE);
            flatTypes.put(FlatType.THREE_ROOM, new FlatTypeDetails(units3Room, units3Room, price3Room));
        }

        if (flatTypes.isEmpty()) {
            System.out.println(
                    "Error: Project must have at least one type of flat (2-Room or 3-Room). Creation cancelled.");
            return;
        }

        Date openingDate;
        Date closingDate;

        while (true) {
            openingDate = getDateInput("Enter Application Opening Date (yyyy-MM-dd): ", false);
            closingDate = getDateInput("Enter Application Closing Date (yyyy-MM-dd): ", false);

            if (openingDate == null || closingDate == null) {
                System.out.println("Dates cannot be empty. Please re-enter.");
                continue;
            }
            if (closingDate.before(openingDate)) {
                System.out.println("Closing date cannot be before opening date. Please re-enter.");
                continue;
            }

            Project proposedProjectDates = new Project(
                    "__temp__", "__temp__", flatTypes, openingDate, closingDate, manager.getNric(), 0, null, true);

            boolean overlapsWithActive = projects.stream()
                    .filter(p -> p.getManagerNric().equals(manager.getNric()))
                    .anyMatch(existingActiveProject -> checkDateOverlap(proposedProjectDates, existingActiveProject));

            if (overlapsWithActive) {
                System.out.println(
                        "Error: The specified application period overlaps with another project you manage. Please enter different dates or manage the visibility/dates of the existing project.");
            } else {
                break;
            }
        }

        int maxOfficers = getIntInput("Enter Maximum HDB Officer Slots (1-10): ", 1, 10);

        Project newProject = new Project(projectName, neighborhood, flatTypes, openingDate, closingDate,
                currentUser.getNric(), maxOfficers, new ArrayList<>(), false);
        projects.add(newProject);

        System.out.println("Project '" + projectName + "' created successfully. Visibility is currently OFF.");
        ProjectService.saveProjects(projects);
    }

    public void editProject() {
        System.out.println("\n--- Edit BTO Project ---");
        List<Project> myProjects = getManagedProjects(false);
        if (myProjects.isEmpty()) {
            System.out.println("You are not managing any projects.");
            return;
        }

        viewAndSelectProject(myProjects, "Select Project to Edit");
        Project projectToEdit = selectProjectFromList(myProjects);
        if (projectToEdit == null)
            return;

        System.out
                .println("Editing Project: " + projectToEdit.getProjectName() + " (Leave blank to keep current value)");

        System.out.print("Enter new Neighborhood [" + projectToEdit.getNeighborhood() + "]: ");
        String newNeighborhood = scanner.nextLine().trim();
        if (!newNeighborhood.isEmpty())
            projectToEdit.setNeighborhood(newNeighborhood);

        Map<FlatType, FlatTypeDetails> currentFlatTypes = projectToEdit.getFlatTypes();
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
        projectToEdit.setFlatTypes(newFlatTypesMap);

        Date originalOpening = projectToEdit.getApplicationOpeningDate();
        Date originalClosing = projectToEdit.getApplicationClosingDate();
        Date newOpeningDate = getDateInput("Enter new Opening Date (yyyy-MM-dd) ["
                + DateUtils.formatDate(originalOpening) + "] (leave blank to keep): ", true);
        Date newClosingDate = getDateInput("Enter new Closing Date (yyyy-MM-dd) ["
                + DateUtils.formatDate(originalClosing) + "] (leave blank to keep): ", true);

        Date finalOpening = (newOpeningDate != null) ? newOpeningDate : originalOpening;
        Date finalClosing = (newClosingDate != null) ? newClosingDate : originalClosing;

        boolean datesChanged = (newOpeningDate != null || newClosingDate != null);
        boolean datesValid = true;

        if (finalClosing.before(finalOpening)) {
            System.out.println("Error: Closing date cannot be before opening date. Dates not updated.");
            datesValid = false;
        }

        if (datesChanged && datesValid) {
            Project proposedProjectDates = new Project(
                    projectToEdit.getProjectName(), projectToEdit.getNeighborhood(), projectToEdit.getFlatTypes(),
                    finalOpening, finalClosing, projectToEdit.getManagerNric(), projectToEdit.getMaxOfficerSlots(),
                    projectToEdit.getApprovedOfficerNrics(), projectToEdit.isVisible());

            boolean overlapsWithActive = projects.stream()
                    .filter(p -> p.getManagerNric().equals(currentUser.getNric()) && !p.equals(projectToEdit))
                    .anyMatch(existingActiveProject -> checkDateOverlap(proposedProjectDates, existingActiveProject));

            if (overlapsWithActive) {
                System.out.println(
                        "Error: The new application period overlaps with another project you manage. Dates not updated.");
                datesValid = false;
            }
        }

        if (datesValid) {
            if (newOpeningDate != null)
                projectToEdit.setApplicationOpeningDate(newOpeningDate);
            if (newClosingDate != null)
                projectToEdit.setApplicationClosingDate(newClosingDate);
            if (datesChanged)
                System.out.println("Application dates updated.");
        }

        int currentMaxSlots = projectToEdit.getMaxOfficerSlots();
        int currentApprovedCount = projectToEdit.getApprovedOfficerNrics().size();
        System.out.print("Enter new Max Officer Slots [" + currentMaxSlots + "] (min " + currentApprovedCount
                + ", max 10, leave blank to keep): ");
        String slotsInput = scanner.nextLine().trim();
        if (!slotsInput.isEmpty()) {
            try {
                int newMaxSlots = Integer.parseInt(slotsInput);
                if (newMaxSlots >= 1 && newMaxSlots <= 10) {
                    projectToEdit.setMaxOfficerSlots(newMaxSlots);
                } else {
                    System.out.println("Max slots must be between 1 and 10. Keeping original value.");
                }
            } catch (NumberFormatException e) {
                System.out.println("Invalid number format. Max slots not changed.");
            }
        }

        System.out.println("Project details update attempt complete.");
        ProjectService.saveProjects(projects);
    }

    public void deleteProject() {
        System.out.println("\n--- Delete BTO Project ---");
        List<Project> myProjects = getManagedProjects(false);
        if (myProjects.isEmpty()) {
            System.out.println("You are not managing any projects.");
            return;
        }

        viewAndSelectProject(myProjects, "Select Project to Delete");
        Project projectToDelete = selectProjectFromList(myProjects);
        if (projectToDelete == null)
            return;

        boolean hasActiveApplications = applications.values().stream()
                .anyMatch(app -> app.getProjectName().equals(projectToDelete.getProjectName()) &&
                        (app.getStatus() == ApplicationStatus.PENDING ||
                                app.getStatus() == ApplicationStatus.SUCCESSFUL ||
                                app.getStatus() == ApplicationStatus.BOOKED ||
                                app.getStatus() == ApplicationStatus.PENDING_WITHDRAWAL));

        boolean hasActiveRegistrations = officerRegistrations.values().stream()
                .anyMatch(reg -> reg.getProjectName().equals(projectToDelete.getProjectName()) &&
                        (reg.getStatus() == OfficerRegistrationStatus.PENDING ||
                                reg.getStatus() == OfficerRegistrationStatus.APPROVED));

        if (hasActiveApplications || hasActiveRegistrations) {
            System.out.println("Error: Cannot delete project '" + projectToDelete.getProjectName() + "'.");
            if (hasActiveApplications)
                System.out.println("- It has active BTO applications (Pending/Successful/Booked/PendingWithdrawal).");
            if (hasActiveRegistrations)
                System.out.println("- It has active Officer registrations (Pending/Approved).");
            System.out.println("Resolve these associations before deleting.");
            return;
        }

        System.out.print("Are you sure you want to permanently delete project '" + projectToDelete.getProjectName()
                + "'? This will also remove associated historical applications/registrations/enquiries. (yes/no): ");
        String confirm = scanner.nextLine().trim().toLowerCase();

        if (confirm.equals("yes")) {
            String deletedProjectName = projectToDelete.getProjectName();
            if (projects.remove(projectToDelete)) {
                System.out.println("Project deleted successfully.");
                boolean removedApps = applications.values()
                        .removeIf(app -> app.getProjectName().equals(deletedProjectName));
                boolean removedRegs = officerRegistrations.values()
                        .removeIf(reg -> reg.getProjectName().equals(deletedProjectName));
                boolean removedEnqs = enquiries.removeIf(enq -> enq.getProjectName().equals(deletedProjectName));

                if (removedApps)
                    System.out.println("Removed associated applications.");
                if (removedRegs)
                    System.out.println("Removed associated officer registrations.");
                if (removedEnqs)
                    System.out.println("Removed associated enquiries.");

                ProjectService.saveProjects(projects);
                if (removedApps)
                    ApplicationService.saveApplications(applications);
                if (removedRegs)
                    OfficerRegistrationService.saveOfficerRegistrations(officerRegistrations);
                if (removedEnqs)
                    EnquiryService.saveEnquiries(enquiries);

            } else {
                System.err.println("Error: Failed to remove project from list.");
            }
        } else {
            System.out.println("Deletion cancelled.");
        }
    }

    public void toggleProjectVisibility() {
        System.out.println("\n--- Toggle Project Visibility ---");
        List<Project> myProjects = getManagedProjects(false);
        if (myProjects.isEmpty()) {
            System.out.println("You are not managing any projects.");
            return;
        }

        viewAndSelectProject(myProjects, "Select Project to Toggle Visibility");
        Project projectToToggle = selectProjectFromList(myProjects);

        if (projectToToggle != null) {
            boolean currentVisibility = projectToToggle.isVisible();
            projectToToggle.setVisibility(!currentVisibility);
            System.out.println("Project '" + projectToToggle.getProjectName() + "' visibility toggled to "
                    + (projectToToggle.isVisible() ? "ON" : "OFF") + ".");
            ProjectService.saveProjects(projects);
        }
    }

    public void viewAllProjects() {
        System.out.println("\n--- View All Projects (Manager View) ---");
        List<Project> displayProjects = getFilteredProjects(false, false, false, false, false);
        viewAndSelectProject(displayProjects, "All BTO Projects");
    }

    public void viewMyProjects() {
        System.out.println("\n--- View My Managed Projects ---");
        List<Project> myProjects = getManagedProjects(true);
        viewAndSelectProject(myProjects, "Projects Managed By You");
    }

    private List<Project> getManagedProjects(boolean applyUserFilters) {
        List<Project> managed = projects.stream()
                .filter(p -> p.getManagerNric().equals(currentUser.getNric()))
                .filter(p -> !applyUserFilters || filterLocation == null
                        || p.getNeighborhood().equalsIgnoreCase(filterLocation))
                .filter(p -> !applyUserFilters || filterFlatType == null
                        || p.getFlatTypes().containsKey(filterFlatType))
                .sorted(
                        Comparator.comparing(project -> project.getProjectName()))
                .collect(Collectors.toList());
        if (managed.isEmpty() && applyUserFilters) {
            System.out.println("You are not managing any projects"
                    + (filterLocation != null || filterFlatType != null ? " matching the current filters." : "."));
        } else if (managed.isEmpty() && !applyUserFilters) {
        }
        return managed;
    }

    public void manageOfficerRegistrations() {
        System.out.println("\n--- Manage HDB Officer Registrations ---");
        List<Project> myProjects = getManagedProjects(false);
        if (myProjects.isEmpty()) {
            System.out.println("You are not managing any projects.");
            return;
        }

        System.out.println("Select project to manage registrations for:");
        viewAndSelectProject(myProjects, "Select Project");
        Project selectedProject = selectProjectFromList(myProjects);
        if (selectedProject == null)
            return;

        System.out.println("\n--- Registrations for Project: " + selectedProject.getProjectName() + " ---");
        System.out.println("Officer Slots: " + selectedProject.getApprovedOfficerNrics().size() + " / "
                + selectedProject.getMaxOfficerSlots() + " (Remaining: " + selectedProject.getRemainingOfficerSlots()
                + ")");

        List<OfficerRegistration> projectRegistrations = officerRegistrations.values().stream()
                .filter(reg -> reg.getProjectName().equals(selectedProject.getProjectName()))
                .sorted(
                        Comparator.comparing(reg -> reg.getRegistrationDate()))
                .collect(Collectors.toList());

        List<OfficerRegistration> pendingRegistrations = projectRegistrations.stream()
                .filter(reg -> reg.getStatus() == OfficerRegistrationStatus.PENDING)
                .collect(Collectors.toList());

        System.out.println("\n--- Pending Registrations ---");
        if (pendingRegistrations.isEmpty()) {
            System.out.println("(None)");
        } else {
            for (int i = 0; i < pendingRegistrations.size(); i++) {
                OfficerRegistration reg = pendingRegistrations.get(i);
                User officerUser = users.get(reg.getOfficerNric());
                System.out.printf("%d. NRIC: %s | Name: %-15s | Date: %s\n",
                        i + 1, reg.getOfficerNric(),
                        officerUser != null ? officerUser.getName() : "N/A",
                        DateUtils.formatDate(reg.getRegistrationDate()));
            }
            System.out.print("Enter number to Approve/Reject (or 0 to skip): ");
            try {
                int choice = Integer.parseInt(scanner.nextLine());
                if (choice >= 1 && choice <= pendingRegistrations.size()) {
                    OfficerRegistration regToProcess = pendingRegistrations.get(choice - 1);
                    User officerUser = users.get(regToProcess.getOfficerNric());

                    if (!(officerUser instanceof HDBOfficer)) {
                        System.out.println("Error: User " + regToProcess.getOfficerNric()
                                + " is no longer a valid Officer. Rejecting registration.");
                        regToProcess.setStatus(OfficerRegistrationStatus.REJECTED);
                        OfficerRegistrationService.saveOfficerRegistrations(officerRegistrations);
                        return;
                    }
                    HDBOfficer officer = (HDBOfficer) officerUser;

                    System.out.print("Approve or Reject? (A/R): ");
                    String action = scanner.nextLine().trim().toUpperCase();

                    if (action.equals("A")) {
                        if (selectedProject.getRemainingOfficerSlots() <= 0) {
                            System.out.println("Cannot approve. No remaining officer slots for this project.");
                        } else if (isOfficerHandlingOverlappingProject(officer, selectedProject)) {
                            System.out.println(
                                    "Cannot approve. Officer is already handling another project with overlapping dates.");
                        } else {
                            approveOfficerRegistration(regToProcess, selectedProject, officer);
                        }
                    } else if (action.equals("R")) {
                        regToProcess.setStatus(OfficerRegistrationStatus.REJECTED);
                        System.out.println("Registration Rejected.");
                        OfficerRegistrationService.saveOfficerRegistrations(officerRegistrations);
                    } else {
                        System.out.println("Invalid action.");
                    }
                } else if (choice != 0) {
                    System.out.println("Invalid choice.");
                }
            } catch (NumberFormatException e) {
                System.out.println("Invalid input.");
            }
        }

        System.out.println("\n--- Approved Officers for this Project ---");
        if (selectedProject.getApprovedOfficerNrics().isEmpty())
            System.out.println("(None)");
        else
            selectedProject.getApprovedOfficerNrics().forEach(nric -> System.out.println("- NRIC: " + nric
                    + (users.containsKey(nric) ? " (Name: " + users.get(nric).getName() + ")" : " (Name: N/A)")));

        System.out.println("\n--- Rejected Registrations for this Project ---");
        List<OfficerRegistration> rejected = projectRegistrations.stream()
                .filter(r -> r.getStatus() == OfficerRegistrationStatus.REJECTED).collect(Collectors.toList());
        if (rejected.isEmpty())
            System.out.println("(None)");
        else
            rejected.forEach(reg -> System.out.println(
                    "- NRIC: " + reg.getOfficerNric() + " | Date: " + DateUtils.formatDate(reg.getRegistrationDate())));
    }

    private boolean isOfficerHandlingOverlappingProject(HDBOfficer officer, Project targetProject) {
        return officerRegistrations.values().stream()
                .filter(reg -> reg.getOfficerNric().equals(officer.getNric()) &&
                        reg.getStatus() == OfficerRegistrationStatus.APPROVED &&
                        !reg.getProjectName().equals(targetProject.getProjectName()))
                .map(reg -> findProjectByName(reg.getProjectName()))
                .filter(obj -> obj != null)
                .anyMatch(otherProject -> checkDateOverlap(targetProject, otherProject));
    }

    private void approveOfficerRegistration(OfficerRegistration registration, Project project, HDBOfficer officer) {
        if (project.getRemainingOfficerSlots() <= 0) {
            System.out.println("Error: No remaining officer slots. Approval aborted.");
            return;
        }
        if (project.addApprovedOfficer(registration.getOfficerNric())) {
            registration.setStatus(OfficerRegistrationStatus.APPROVED);
            System.out
                    .println("Registration Approved. Officer " + registration.getOfficerNric() + " added to project.");
            OfficerRegistrationService.saveOfficerRegistrations(officerRegistrations);
            ProjectService.saveProjects(projects);
        } else {
            System.err
                    .println("Error: Failed to add officer to project's approved list (unexpected). Approval aborted.");
        }
    }

    public void manageApplications() {
        System.out.println("\n--- Manage BTO Applications ---");
        List<Project> myProjects = getManagedProjects(false);
        if (myProjects.isEmpty()) {
            System.out.println("You are not managing any projects.");
            return;
        }

        System.out.println("Select project to manage applications for:");
        viewAndSelectProject(myProjects, "Select Project");
        Project selectedProject = selectProjectFromList(myProjects);
        if (selectedProject == null)
            return;

        System.out.println("\n--- Applications for Project: " + selectedProject.getProjectName() + " ---");

        List<BTOApplication> projectApplications = applications.values().stream()
                .filter(app -> app.getProjectName().equals(selectedProject.getProjectName()))
                .sorted(
                        Comparator.comparing(application -> application.getApplicationDate()))
                .collect(Collectors.toList());

        if (projectApplications.isEmpty()) {
            System.out.println("No applications found for this project.");
            return;
        }

        List<BTOApplication> pendingApps = projectApplications.stream()
                .filter(app -> app.getStatus() == ApplicationStatus.PENDING)
                .collect(Collectors.toList());

        System.out.println("--- Pending Applications ---");
        if (pendingApps.isEmpty()) {
            System.out.println("(None)");
        } else {
            for (int i = 0; i < pendingApps.size(); i++) {
                BTOApplication app = pendingApps.get(i);
                User applicant = users.get(app.getApplicantNric());
                System.out.printf("%d. NRIC: %s | Name: %-15s | Type: %-8s | Date: %s\n",
                        i + 1, app.getApplicantNric(),
                        applicant != null ? applicant.getName() : "N/A",
                        app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A",
                        DateUtils.formatDate(app.getApplicationDate()));
            }
            System.out.print("Enter number to Approve/Reject (or 0 to skip): ");
            try {
                int choice = Integer.parseInt(scanner.nextLine());
                if (choice >= 1 && choice <= pendingApps.size()) {
                    BTOApplication appToProcess = pendingApps.get(choice - 1);
                    User applicantUser = users.get(appToProcess.getApplicantNric());

                    if (!(applicantUser instanceof Applicant)) {
                        System.out.println("Error: Applicant data not found or invalid for NRIC "
                                + appToProcess.getApplicantNric() + ". Rejecting application.");
                        appToProcess.setStatus(ApplicationStatus.UNSUCCESSFUL);
                        ApplicationService.saveApplications(applications);
                        return;
                    }
                    Applicant applicant = (Applicant) applicantUser;

                    System.out.print("Approve or Reject? (A/R): ");
                    String action = scanner.nextLine().trim().toUpperCase();

                    if (action.equals("A")) {
                        FlatType appliedType = appToProcess.getFlatTypeApplied();
                        if (appliedType == null) {
                            System.out.println("Error: Application has no specified flat type. Cannot approve.");
                            return;
                        }
                        FlatTypeDetails details = selectedProject.getFlatTypeDetails(appliedType);

                        if (details == null) {
                            System.out.println("Error: Applied flat type (" + appliedType.getDisplayName()
                                    + ") does not exist in this project. Rejecting application.");
                            appToProcess.setStatus(ApplicationStatus.UNSUCCESSFUL);
                            applicant.setApplicationStatus(ApplicationStatus.UNSUCCESSFUL);
                            ApplicationService.saveApplications(applications);
                            return;
                        }

                        long alreadySuccessfulOrBookedCount = applications.values().stream()
                                .filter(a -> a.getProjectName().equals(selectedProject.getProjectName()) &&
                                        a.getFlatTypeApplied() == appliedType &&
                                        (a.getStatus() == ApplicationStatus.SUCCESSFUL
                                                || a.getStatus() == ApplicationStatus.BOOKED))
                                .count();

                        if (alreadySuccessfulOrBookedCount < details.getTotalUnits()) {
                            appToProcess.setStatus(ApplicationStatus.SUCCESSFUL);
                            applicant.setApplicationStatus(ApplicationStatus.SUCCESSFUL);
                            System.out.println(
                                    "Application Approved (Status: SUCCESSFUL). Applicant can now book via Officer.");
                            ApplicationService.saveApplications(applications);
                        } else {
                            System.out.println(
                                    "Cannot approve. The number of successful/booked applications already meets or exceeds the total supply ("
                                            + details.getTotalUnits() + ") for " + appliedType.getDisplayName() + ".");
                        }
                    } else if (action.equals("R")) {
                        appToProcess.setStatus(ApplicationStatus.UNSUCCESSFUL);
                        applicant.setApplicationStatus(ApplicationStatus.UNSUCCESSFUL);
                        applicant.setBookedFlatType(null);
                        System.out.println("Application Rejected (Status: UNSUCCESSFUL).");
                        ApplicationService.saveApplications(applications);
                    } else {
                        System.out.println("Invalid action.");
                    }
                } else if (choice != 0) {
                    System.out.println("Invalid choice.");
                }
            } catch (NumberFormatException e) {
                System.out.println("Invalid input.");
            }
        }

        System.out.println("\n--- Other Application Statuses ---");
        projectApplications.stream()
                .filter(app -> app.getStatus() != ApplicationStatus.PENDING)
                .forEach(app -> {
                    User applicant = users.get(app.getApplicantNric());
                    System.out.printf("- NRIC: %s | Name: %-15s | Type: %-8s | Status: %s\n",
                            app.getApplicantNric(),
                            applicant != null ? applicant.getName() : "N/A",
                            app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A",
                            app.getStatus());
                });
    }

    public void manageWithdrawalRequests() {
        System.out.println("\n--- Manage Withdrawal Requests ---");
        List<Project> myProjects = getManagedProjects(false);
        if (myProjects.isEmpty()) {
            System.out.println("You are not managing any projects.");
            return;
        }
        List<String> myProjectNames = myProjects.stream().map(project -> project.getProjectName())
                .collect(Collectors.toList());

        List<BTOApplication> pendingWithdrawals = applications.values().stream()
                .filter(app -> app.getStatus() == ApplicationStatus.PENDING_WITHDRAWAL)
                .filter(app -> myProjectNames.contains(app.getProjectName()))
                .sorted(
                        Comparator.comparing(application -> application.getApplicationDate()))
                .collect(Collectors.toList());

        if (pendingWithdrawals.isEmpty()) {
            System.out.println("No pending withdrawal requests found for the projects you manage.");
            return;
        }

        System.out.println("--- Pending Withdrawal Requests ---");
        for (int i = 0; i < pendingWithdrawals.size(); i++) {
            BTOApplication app = pendingWithdrawals.get(i);
            User applicantUser = users.get(app.getApplicantNric());

            ApplicationStatus statusBefore = app.getStatusBeforeWithdrawal();
            if (statusBefore == null) {
                statusBefore = inferStatusBeforeWithdrawal(app,
                        (applicantUser instanceof Applicant) ? (Applicant) applicantUser : null);
                System.out.print(" (Inferred Original: " + statusBefore + ")");
            } else {
                System.out.print(" (Original: " + statusBefore + ")");
            }

            System.out.printf("\n%d. NRIC: %s | Name: %-15s | Project: %-15s | Type: %-8s | App Date: %s",
                    i + 1,
                    app.getApplicantNric(),
                    applicantUser != null ? applicantUser.getName() : "N/A",
                    app.getProjectName(),
                    app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A",
                    DateUtils.formatDate(app.getApplicationDate()));
            System.out.println();
        }

        System.out.print("Enter number to Approve/Reject withdrawal (or 0 to skip): ");
        try {
            int choice = Integer.parseInt(scanner.nextLine());
            if (choice >= 1 && choice <= pendingWithdrawals.size()) {
                BTOApplication appToProcess = pendingWithdrawals.get(choice - 1);
                User applicantUser = users.get(appToProcess.getApplicantNric());
                if (!(applicantUser instanceof Applicant)) {
                    System.out.println("Error: Applicant data not found or invalid for NRIC "
                            + appToProcess.getApplicantNric() + ". Cannot process withdrawal.");
                    return;
                }
                Applicant applicant = (Applicant) applicantUser;
                Project project = findProjectByName(appToProcess.getProjectName());
                if (project == null) {
                    System.out.println("Error: Project data not found for application "
                            + appToProcess.getApplicationId() + ". Cannot process withdrawal.");
                    return;
                }

                ApplicationStatus originalStatus = appToProcess.getStatusBeforeWithdrawal();
                if (originalStatus == null) {
                    originalStatus = inferStatusBeforeWithdrawal(appToProcess, applicant);
                }

                System.out.print("Approve or Reject withdrawal request? (A/R): ");
                String action = scanner.nextLine().trim().toUpperCase();

                if (action.equals("A")) {
                    ApplicationStatus finalStatus;
                    boolean releasedUnit = false;

                    if (originalStatus == ApplicationStatus.BOOKED) {
                        finalStatus = ApplicationStatus.UNSUCCESSFUL;
                        FlatType bookedType = appToProcess.getFlatTypeApplied();
                        if (bookedType != null) {
                            FlatTypeDetails details = project.getMutableFlatTypeDetails(bookedType);
                            if (details != null) {
                                if (details.incrementAvailableUnits()) {
                                    releasedUnit = true;
                                    System.out.println("Unit for " + bookedType.getDisplayName()
                                            + " released back to project " + project.getProjectName());
                                } else {
                                    System.err.println("Error: Could not increment available units for " + bookedType
                                            + " during withdrawal approval.");
                                }
                            } else {
                                System.err.println("Error: Could not find flat details for " + bookedType
                                        + " during withdrawal approval.");
                            }
                        } else {
                            System.err.println(
                                    "Error: Cannot determine booked flat type to release unit during withdrawal approval.");
                        }
                    } else if (originalStatus == ApplicationStatus.SUCCESSFUL) {
                        finalStatus = ApplicationStatus.UNSUCCESSFUL;
                    } else {
                        finalStatus = ApplicationStatus.WITHDRAWN;
                    }

                    appToProcess.setStatus(finalStatus);
                    applicant.setApplicationStatus(finalStatus);
                    applicant.setBookedFlatType(null);

                    System.out.println("Withdrawal request Approved. Application status set to " + finalStatus + ".");

                    ApplicationService.saveApplications(applications);
                    if (releasedUnit) {
                        ProjectService.saveProjects(projects);
                    }

                } else if (action.equals("R")) {
                    appToProcess.setStatus(originalStatus);
                    applicant.setApplicationStatus(originalStatus);

                    System.out.println(
                            "Withdrawal request Rejected. Application status reverted to " + originalStatus + ".");
                    ApplicationService.saveApplications(applications);

                } else {
                    System.out.println("Invalid action.");
                }
            } else if (choice != 0) {
                System.out.println("Invalid choice.");
            }
        } catch (NumberFormatException e) {
            System.out.println("Invalid input.");
        }
    }

    private ApplicationStatus inferStatusBeforeWithdrawal(BTOApplication app, Applicant applicant) {
        if (applicant != null && applicant.hasBooked() && app.getFlatTypeApplied() != null) {
            return ApplicationStatus.BOOKED;
        } else if (app.getFlatTypeApplied() != null) {
            if (applicant != null && applicant.getApplicationStatus() == ApplicationStatus.SUCCESSFUL) {
                return ApplicationStatus.SUCCESSFUL;
            } else {
                return ApplicationStatus.SUCCESSFUL;
            }
        }
        return ApplicationStatus.PENDING;
    }

    public void generateApplicantReport() {
        System.out.println("\n--- Generate Applicant Report (Booked Flats) ---");

        System.out.println("Filter by project:");
        System.out.println("1. All Projects Managed By You");
        System.out.println("2. A Specific Project Managed By You");
        System.out.println("0. Cancel");
        int projectFilterChoice = getIntInput("Enter choice: ", 0, 2);

        List<Project> projectsToReportOn = new ArrayList<>();
        if (projectFilterChoice == 0)
            return;
        if (projectFilterChoice == 1) {
            projectsToReportOn = getManagedProjects(true);
            if (projectsToReportOn.isEmpty()) {
                return;
            }
            System.out.println("Reporting on all projects you manage"
                    + (filterLocation != null || filterFlatType != null ? " (matching current view filters)." : "."));
        } else {
            List<Project> myProjects = getManagedProjects(false);
            if (myProjects.isEmpty()) {
                System.out.println("You are not managing any projects.");
                return;
            }
            viewAndSelectProject(myProjects, "Select Specific Project to Report On");
            Project specificProject = selectProjectFromList(myProjects);
            if (specificProject == null)
                return;
            projectsToReportOn.add(specificProject);
            System.out.println("Reporting specifically for project: " + specificProject.getProjectName());
        }
        final List<String> finalProjectNames = projectsToReportOn.stream().map(project -> project.getProjectName())
                .collect(Collectors.toList());

        System.out.print("Filter report by Flat Type (TWO_ROOM, THREE_ROOM, or leave blank for all): ");
        String typeStr = scanner.nextLine().trim();
        FlatType filterReportFlatType = null;
        if (!typeStr.isEmpty()) {
            try {
                filterReportFlatType = FlatType.fromString(typeStr);
                if (filterReportFlatType != null)
                    System.out.println("Filtering report for flat type: " + filterReportFlatType.getDisplayName());
                else
                    System.out.println("Invalid flat type entered. Reporting for all types.");
            } catch (IllegalArgumentException e) {
                System.out.println("Invalid flat type format. Reporting for all types.");
            }
        }

        System.out.print("Filter report by Marital Status (SINGLE, MARRIED, or leave blank for all): ");
        String maritalStr = scanner.nextLine().trim().toUpperCase();
        MaritalStatus filterMaritalStatus = null;
        if (!maritalStr.isEmpty()) {
            try {
                filterMaritalStatus = MaritalStatus.valueOf(maritalStr);
                System.out.println("Filtering report for marital status: " + filterMaritalStatus);
            } catch (IllegalArgumentException e) {
                System.out.println("Invalid marital status. Reporting for all statuses.");
            }
        }

        int minAge = getIntInput("Filter report by Minimum Age (e.g., 21, or 0 for no minimum): ", 0, 120);
        int maxAge = getIntInput("Filter report by Maximum Age (e.g., 40, or 0 for no maximum): ", 0, 120);
        if (minAge > 0 || maxAge > 0)
            System.out.println("Filtering report for age range: " + (minAge > 0 ? minAge : "Any") + " to "
                    + (maxAge > 0 ? maxAge : "Any"));

        final FlatType finalFilterReportFlatType = filterReportFlatType;
        final MaritalStatus finalFilterMaritalStatus = filterMaritalStatus;
        final int finalMinAge = minAge;
        final int finalMaxAge = maxAge;

        List<BTOApplication> bookedApplications = applications.values().stream()
                .filter(app -> app.getStatus() == ApplicationStatus.BOOKED)
                .filter(app -> finalProjectNames.contains(app.getProjectName()))
                .filter(app -> finalFilterReportFlatType == null
                        || app.getFlatTypeApplied() == finalFilterReportFlatType)
                .filter(app -> {
                    User user = users.get(app.getApplicantNric());
                    if (user == null)
                        return false;
                    if (finalFilterMaritalStatus != null && user.getMaritalStatus() != finalFilterMaritalStatus)
                        return false;
                    if (finalMinAge > 0 && user.getAge() < finalMinAge)
                        return false;
                    if (finalMaxAge > 0 && user.getAge() > finalMaxAge)
                        return false;
                    return true;
                })
                .sorted(
                        Comparator.comparing((BTOApplication app) -> app.getProjectName())
                                .thenComparing(app -> app.getApplicantNric()))
                .collect(Collectors.toList());

        System.out.println("\n--- Report: Applicants with Flat Bookings ---");
        System.out.println("Filters Applied: Project(s) selected, FlatType="
                + (finalFilterReportFlatType == null ? "Any" : finalFilterReportFlatType) + ", MaritalStatus="
                + (finalFilterMaritalStatus == null ? "Any" : finalFilterMaritalStatus) + ", Age="
                + (finalMinAge > 0 ? finalMinAge : "Any") + "-" + (finalMaxAge > 0 ? finalMaxAge : "Any"));
        System.out.println("---------------------------------------------------------------------------------");
        System.out.printf("%-15s | %-15s | %-5s | %-10s | %-15s | %-8s\n",
                "Applicant NRIC", "Name", "Age", "Marital", "Project Name", "FlatType");
        System.out.println("---------------------------------------------------------------------------------");

        if (bookedApplications.isEmpty()) {
            System.out.println("No matching booked applications found for the specified filters.");
        } else {
            bookedApplications.forEach(app -> {
                User user = users.get(app.getApplicantNric());
                System.out.printf("%-15s | %-15s | %-5d | %-10s | %-15s | %-8s\n",
                        app.getApplicantNric(),
                        user != null ? user.getName() : "N/A",
                        user != null ? user.getAge() : 0,
                        user != null ? user.getMaritalStatus() : "N/A",
                        app.getProjectName(),
                        app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A");
            });
        }
        System.out.println("---------------------------------------------------------------------------------");
        System.out.println("Total matching booked applicants: " + bookedApplications.size());
        System.out.println("--- End of Report ---");
    }

    public void viewAllEnquiries() {
        System.out.println("\n--- View Enquiries (ALL Projects) ---");
        if (enquiries.isEmpty()) {
            System.out.println("No enquiries found in the system.");
            return;
        }

        enquiries.stream()
                .sorted(
                        Comparator.comparing((Enquiry enquiry) -> enquiry.getProjectName())
                                .thenComparing(enquiry -> enquiry.getEnquiryDate()).reversed())

                .forEach(e -> {
                    printEnquiryDetails(e);
                    System.out.println("----------------------------------------");
                });
    }

    public void viewAndReplyToManagedEnquiries() {
        System.out.println("\n--- View/Reply Enquiries (Managed Projects) ---");
        List<String> myManagedProjectNames = getManagedProjects(true).stream()
                .map(project -> project.getProjectName())
                .collect(Collectors.toList());

        if (myManagedProjectNames.isEmpty()) {
            return;
        }

        List<Enquiry> managedEnquiries = enquiries.stream()
                .filter(e -> myManagedProjectNames.contains(e.getProjectName()))
                .sorted(Comparator.comparing((Enquiry enquiry) -> enquiry.getProjectName()).thenComparing((Enquiry enquiry) -> enquiry.getProjectName()).reversed())
                .collect(Collectors.toList());

        if (managedEnquiries.isEmpty()) {
            System.out.println("No enquiries found for the projects you manage"
                    + (filterLocation != null || filterFlatType != null ? " (matching filters)." : "."));
            return;
        }

        List<Enquiry> unrepliedEnquiries = managedEnquiries.stream()
                .filter(e -> !e.isReplied())
                .collect(Collectors.toList());

        System.out.println("--- Unreplied Enquiries (Managed Projects) ---");
        if (unrepliedEnquiries.isEmpty()) {
            System.out.println("(None)");
        } else {
            for (int i = 0; i < unrepliedEnquiries.size(); i++) {
                Enquiry e = unrepliedEnquiries.get(i);
                System.out.printf("%d. ", i + 1);
                printEnquiryDetails(e);
                System.out.println("---");
            }
            System.out.print("Enter the number of the enquiry to reply to (or 0 to skip): ");
            try {
                int choice = Integer.parseInt(scanner.nextLine());
                if (choice >= 1 && choice <= unrepliedEnquiries.size()) {
                    Enquiry enquiryToReply = unrepliedEnquiries.get(choice - 1);
                    System.out.print("Enter your reply: ");
                    String replyText = scanner.nextLine().trim();
                    if (enquiryToReply.setReply(replyText, currentUser.getNric(), DateUtils.getCurrentDate())) {
                        System.out.println("Reply submitted successfully.");
                        EnquiryService.saveEnquiries(enquiries);
                    }
                } else if (choice != 0) {
                    System.out.println("Invalid choice.");
                }
            } catch (NumberFormatException e) {
                System.out.println("Invalid input.");
            }
        }

        System.out.println("\n--- Replied Enquiries (Managed Projects) ---");
        List<Enquiry> repliedEnquiries = managedEnquiries.stream()
                .filter(enquiry -> enquiry.isReplied())
                .collect(Collectors.toList());
        if (repliedEnquiries.isEmpty()) {
            System.out.println("(None)");
        } else {
            for (Enquiry e : repliedEnquiries) {
                printEnquiryDetails(e);
                System.out.println("----------------------------------------");
            }
        }
    }

    private void printEnquiryDetails(Enquiry e) {
        System.out.printf("ID: %s | Project: %s | Applicant: %s | Date: %s\n",
                e.getEnquiryId(), e.getProjectName(), e.getApplicantNric(), DateUtils.formatDate(e.getEnquiryDate()));
        System.out.println("   Enquiry: " + e.getEnquiryText());
        if (e.isReplied()) {
            System.out.printf("   Reply (by %s on %s): %s\n",
                    e.getRepliedByNric() != null ? e.getRepliedByNric() : "N/A",
                    e.getReplyDate() != null ? DateUtils.formatDate(e.getReplyDate()) : "N/A",
                    e.getReplyText());
        } else {
            System.out.println("   Reply: (Pending)");
        }
    }
}
