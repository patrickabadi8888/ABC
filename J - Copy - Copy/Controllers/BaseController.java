package Controllers;

import Enums.OfficerRegistrationStatus;
import Enums.FlatType;
import Enums.ApplicationStatus;
import Enums.MaritalStatus;
import Enums.UserRole;

import Models.User;
import Parsers.Dparse;
import Models.Project;
import Models.BTOApplication;
import Models.HDBManager;
import Models.HDBOfficer;
import Models.Applicant;
import Models.OfficerRegistration;
import Models.FlatTypeDetails;

import Services.IApplicationService;
import Services.IOfficerRegistrationService;
import Services.IProjectService;
import Services.IUserService;

import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Scanner;
import java.util.Comparator;
import java.util.stream.Collectors;

import Utils.DateUtils;

public abstract class BaseController {
    // Services are injected instead of raw data maps
    protected final IUserService userService;
    protected final IProjectService projectService;
    protected final IApplicationService applicationService;
    protected final IOfficerRegistrationService officerRegistrationService;
    // User, Scanner, AuthController remain
    protected final User currentUser;
    protected final Scanner scanner;
    protected final AuthController authController;

    // Filters remain as state within the controller instance (or potentially moved to a separate FilterState object)
    protected String filterLocation = null;
    protected FlatType filterFlatType = null;

    public BaseController(IUserService userService, IProjectService projectService,
                          IApplicationService applicationService, IOfficerRegistrationService officerRegistrationService,
                          User currentUser, Scanner scanner, AuthController authController) {
        this.userService = userService;
        this.projectService = projectService;
        this.applicationService = applicationService;
        this.officerRegistrationService = officerRegistrationService;
        this.currentUser = currentUser;
        this.scanner = scanner;
        this.authController = authController;
    }

    // Finding methods now use injected services
    protected Project findProjectByName(String name) {
        return projectService.findProjectByName(name);
    }

    protected BTOApplication findApplicationByApplicantAndProject(String nric, String projectName) {
        return applicationService.findApplicationByApplicantAndProject(nric, projectName);
    }

    // This logic relies on OfficerRegistrationService now
    public Project getOfficerHandlingProject(HDBOfficer officer) {
        if (officer == null)
            return null;
        Date today = DateUtils.getCurrentDate();
        OfficerRegistration approvedReg = officerRegistrationService.getApprovedRegistrationForOfficer(officer.getNric());

        if (approvedReg != null) {
            Project project = projectService.findProjectByName(approvedReg.getProjectName());
            // Additionally check if the project's application period is still active
            if (project != null && project.isApplicationPeriodActive(today)) {
                return project;
            }
        }
        return null;
    }

    // Date overlap logic remains the same
    protected boolean checkDateOverlap(Project p1, Project p2) {
        if (p1 == null || p2 == null || p1.getApplicationOpeningDate() == null || p1.getApplicationClosingDate() == null
                || p2.getApplicationOpeningDate() == null || p2.getApplicationClosingDate() == null) {
            return false;
        }
        // Check if p1 starts after p2 ends OR p1 ends before p2 starts
        boolean noOverlap = p1.getApplicationOpeningDate().after(p2.getApplicationClosingDate()) ||
                            p1.getApplicationClosingDate().before(p2.getApplicationOpeningDate());
        return !noOverlap; // Overlap exists if 'noOverlap' is false
    }

    // Filtering now operates on the list returned by the service
    protected List<Project> getFilteredProjects(boolean checkVisibility, boolean checkEligibility,
            boolean checkAvailability, boolean checkApplicationPeriod, boolean checkNotExpired) {
        Date currentDate = DateUtils.getCurrentDate();
        List<Project> allProjects = projectService.getAllProjects(); // Get all projects from the service

        return allProjects.stream()
                // Apply location and flat type filters first
                .filter(p -> filterLocation == null || p.getNeighborhood().equalsIgnoreCase(filterLocation))
                .filter(p -> filterFlatType == null || p.getFlatTypes().containsKey(filterFlatType))
                // Apply boolean checks passed as arguments
                .filter(p -> !checkVisibility || isProjectVisibleToCurrentUser(p))
                .filter(p -> !checkApplicationPeriod || p.isApplicationPeriodActive(currentDate))
                .filter(p -> !checkNotExpired || !p.isApplicationPeriodExpired(currentDate))
                // Apply eligibility and availability checks
                .filter(p -> {
                    if (!checkEligibility && !checkAvailability) return true; // Skip if not checking these
                    if (currentUser instanceof HDBManager) return true; // Managers see all regardless

                    // Check if current user is eligible for *any* flat type in this project
                    boolean eligibleForAnyType = p.getFlatTypes().keySet().stream()
                            .anyMatch(flatType -> this.canApplyForFlatType(flatType));
                    if (checkEligibility && !eligibleForAnyType) return false; // Filter out if eligibility check fails

                    if (!checkAvailability) return true; // Skip availability check if not required

                    // Check if there's at least one flat type that the user is eligible for AND has available units
                    boolean eligibleAndAvailableExists = p.getFlatTypes().entrySet().stream()
                            .anyMatch(entry -> {
                                FlatType type = entry.getKey();
                                FlatTypeDetails details = entry.getValue();
                                return canApplyForFlatType(type) && details.getAvailableUnits() > 0;
                            });
                    return eligibleAndAvailableExists; // Must satisfy both eligibility (if checked) and availability (if checked)
                })
                .sorted(Comparator.comparing(Project::getProjectName)) // Sort final filtered list
                .collect(Collectors.toList());
    }

    // Visibility check needs OfficerRegistrationService
    protected boolean isProjectVisibleToCurrentUser(Project project) {
        if (currentUser instanceof HDBManager) return true; // Managers see everything

        boolean appliedToThis = false;
        if (currentUser instanceof Applicant) {
            Applicant appUser = (Applicant) currentUser;
            // Check if applicant applied to *this* project and status is relevant (not failed/withdrawn)
            appliedToThis = project.getProjectName().equals(appUser.getAppliedProjectName()) &&
                            appUser.getApplicationStatus() != null &&
                            appUser.getApplicationStatus() != ApplicationStatus.UNSUCCESSFUL &&
                            appUser.getApplicationStatus() != ApplicationStatus.WITHDRAWN;
        }

        boolean isHandlingOfficer = false;
        if (currentUser instanceof HDBOfficer) {
            // Check registrations service if this officer is approved for this project
             isHandlingOfficer = officerRegistrationService.getRegistrationsByOfficer(currentUser.getNric())
                                    .stream()
                                    .anyMatch(reg -> reg.getProjectName().equals(project.getProjectName()) &&
                                            reg.getStatus() == OfficerRegistrationStatus.APPROVED);

        }

        // Visible if globally visible OR user applied OR user is handling officer
        return project.isVisible() || appliedToThis || isHandlingOfficer;
    }

    // Eligibility check remains based on user type, age, marital status
    protected boolean canApplyForFlatType(FlatType type) {
        if (currentUser instanceof HDBManager) return false; // Managers cannot apply

        // Based on HDB rules (simplified)
        if (currentUser.getMaritalStatus() == MaritalStatus.SINGLE) {
            // Singles >= 35 can apply for 2-Room Flexi (represented as TWO_ROOM here)
            return currentUser.getAge() >= 35 && type == FlatType.TWO_ROOM;
        } else if (currentUser.getMaritalStatus() == MaritalStatus.MARRIED) {
            // Married couples >= 21 can apply for 2-Room or 3-Room
            return currentUser.getAge() >= 21 && (type == FlatType.TWO_ROOM || type == FlatType.THREE_ROOM);
        }
        // Other cases (e.g., divorced, widowed) might have different rules, not covered here
        return false;
    }

    // applyFilters method remains the same, modifying the controller's internal state
    public void applyFilters() {
        System.out.println("\n--- Apply/Clear Filters ---");
        System.out.print("Enter neighborhood to filter by (current: "
                + (filterLocation == null ? "Any" : filterLocation) + ", leave blank to clear): ");
        String loc = scanner.nextLine().trim();
        filterLocation = loc.isEmpty() ? null : loc;

        System.out.print("Enter flat type to filter by (TWO_ROOM, THREE_ROOM, current: "
                + (filterFlatType == null ? "Any" : filterFlatType) + ", leave blank to clear): ");
        String typeStr = scanner.nextLine().trim();
        if (typeStr.isEmpty()) {
            filterFlatType = null;
        } else {
            try {
                FlatType parsedType = FlatType.fromString(typeStr); // Use the enum's parser
                if (parsedType != null) {
                    filterFlatType = parsedType;
                } else {
                    System.out.println("Invalid flat type entered. Filter not changed.");
                }
            } catch (IllegalArgumentException e) {
                // This catch might not be needed if fromString returns null for invalid input
                System.out.println("Invalid flat type format. Filter not changed.");
            }
        }
        System.out.println(
                "Filters updated. Current filters: Location=" + (filterLocation == null ? "Any" : filterLocation)
                        + ", FlatType=" + (filterFlatType == null ? "Any" : filterFlatType));
    }

    // UI Helper: viewAndSelectProject remains largely the same, but uses canApplyForFlatType
    protected void viewAndSelectProject(List<Project> projectList, String prompt) {
        if (projectList.isEmpty()) {
            System.out.println("No projects match the current criteria.");
            return;
        }

        System.out.println("\n--- " + prompt + " ---");
        System.out.println("Current Filters: Location=" + (filterLocation == null ? "Any" : filterLocation)
                + ", FlatType=" + (filterFlatType == null ? "Any" : filterFlatType));
        System.out.println(
                "--------------------------------------------------------------------------------------------------------------------");
        System.out.printf("%-3s %-15s %-12s %-10s %-10s %-8s %-25s\n", "#", "Project Name", "Neighborhood", "Open",
                "Close", "Visible", "Flat Types (Available/Total, Price, Eligibility)");
        System.out.println(
                "--------------------------------------------------------------------------------------------------------------------");

        for (int i = 0; i < projectList.size(); i++) {
            Project p = projectList.get(i);
            System.out.printf("%-3d %-15s %-12s %-10s %-10s %-8s ",
                    i + 1,
                    p.getProjectName(),
                    p.getNeighborhood(),
                    DateUtils.formatDate(p.getApplicationOpeningDate()),
                    DateUtils.formatDate(p.getApplicationClosingDate()),
                    p.isVisible() ? "On" : "Off");

            // Generate flat details string including eligibility check
            String flatDetails = p.getFlatTypes().entrySet().stream()
                    .sorted(Map.Entry.comparingByKey()) // Sort by FlatType enum order
                    .map(entry -> {
                        FlatType type = entry.getKey();
                        FlatTypeDetails details = entry.getValue();
                        String eligibilityMark = "";
                        // Show eligibility only for Applicant/Officer roles
                        if (currentUser instanceof Applicant) { // Includes HDBOfficer
                            if (!canApplyForFlatType(type)) {
                                eligibilityMark = " (Ineligible)";
                            } else if (details.getAvailableUnits() <= 0) { // Check non-negative available units
                                eligibilityMark = " (No Units)";
                            }
                        }
                        // Format: TypeName: Avail/Total ($Price) EligibilityMark
                        return String.format("%s: %d/%d ($%.0f)%s",
                                type.getDisplayName(), details.getAvailableUnits(), details.getTotalUnits(),
                                details.getSellingPrice(), eligibilityMark);
                    })
                    .collect(Collectors.joining(", "));
            System.out.println(flatDetails);

            // Show Manager/Officer info only if user is not just an Applicant
            if (currentUser.getRole() != UserRole.APPLICANT) {
                 int approvedCount = p.getApprovedOfficerNrics().size(); // Get current count
                System.out.printf("%-3s %-15s %-12s %-10s %-10s %-8s %-25s\n", "", "", "", "", "", "", // Align under previous line
                        "Mgr: " + p.getManagerNric() + ", Officers: " + approvedCount + "/" + p.getMaxOfficerSlots());
            }
             if (i < projectList.size() - 1)
                 System.out.println("---"); // Separator between projects

        }
        System.out.println(
                "--------------------------------------------------------------------------------------------------------------------");
    }

    // UI Helper: selectProjectFromList remains the same
    protected Project selectProjectFromList(List<Project> projectList) {
        if (projectList == null || projectList.isEmpty()) return null; // Handle empty list case

        System.out.print("Enter the number of the project (or 0 to cancel): ");
        int choice;
        try {
            choice = Integer.parseInt(scanner.nextLine());
            if (choice == 0) {
                System.out.println("Operation cancelled.");
                return null;
            }
            // Validate choice is within the list bounds (1 to list size)
            if (choice >= 1 && choice <= projectList.size()) {
                return projectList.get(choice - 1); // Adjust for 0-based index
            } else {
                System.out.println("Invalid choice number.");
                return null;
            }
        } catch (NumberFormatException e) {
            System.out.println("Invalid input. Please enter a number.");
            return null;
        }
    }

    // UI Helper: getIntInput remains the same
    protected int getIntInput(String prompt, int min, int max) {
        int value = -1; // Initialize outside the loop
        while (true) {
            System.out.print(prompt); // Print the prompt
            String input = scanner.nextLine(); // Read the whole line
            try {
                value = Integer.parseInt(input);
                if (value >= min && value <= max) {
                    break; // Valid input, exit loop
                } else {
                    System.out.println("Input must be between " + min + " and " + max + ".");
                }
            } catch (NumberFormatException e) {
                System.out.println("Invalid input. Please enter a whole number.");
            }
        }
        return value;
    }

    // UI Helper: getDoubleInput remains the same
    protected double getDoubleInput(String prompt, double min, double max) {
        double value = -1.0; // Initialize outside the loop
        while (true) {
            System.out.print(prompt); // Print the prompt
            String input = scanner.nextLine(); // Read the whole line
            try {
                value = Double.parseDouble(input);
                if (value >= min && value <= max) {
                    break; // Valid input, exit loop
                } else {
                    System.out.println("Input must be between " + min + " and " + max + ".");
                }
            } catch (NumberFormatException e) {
                System.out.println("Invalid input. Please enter a number.");
            }
        }
        return value;
    }

    // UI Helper: getDateInput remains the same
    protected Date getDateInput(String prompt, boolean allowBlank) {
        Date date = null;
        while (true) {
            System.out.print(prompt); // Print the prompt
            String input = scanner.nextLine().trim();
            if (input.isEmpty() && allowBlank) {
                return null; // Return null if blank is allowed and input is empty
            }
            if (input.isEmpty() && !allowBlank) {
                 System.out.println("Input cannot be empty.");
                 continue; // Ask again if blank is not allowed
            }
            // Use the Dparse utility to parse the date
            date = Dparse.parseDate(input);
            if (date != null) {
                break; // Valid date parsed, exit loop
            }
            // Dparse already prints an error message, so just loop again
        }
        return date;
    }
}
