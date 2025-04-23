package Controllers;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Scanner;
import java.util.stream.Collectors;

import Enums.ApplicationStatus;
import Enums.FlatType;
import Enums.MaritalStatus;
import Models.BTOApplication;
import Models.HDBManager;
import Models.Project;
import Models.User;
import Services.IApplicationService;
import Services.IEnquiryService;
import Services.IOfficerRegistrationService;
import Services.IProjectService;
import Services.IUserService;

// Handles Manager action for generating reports
public class ReportManagerController extends BaseController {

    public ReportManagerController(IUserService userService, IProjectService projectService,
                                   IApplicationService applicationService, IOfficerRegistrationService officerRegistrationService,
                                   IEnquiryService enquiryService,
                                   User currentUser, Scanner scanner, AuthController authController) {
        super(userService, projectService, applicationService, officerRegistrationService, currentUser, scanner, authController);
         if (!(currentUser instanceof HDBManager)) {
            throw new IllegalArgumentException("ReportManagerController requires an HDBManager user.");
        }
    }

     public void generateApplicantReport() {
        System.out.println("\n--- Generate Applicant Report (Booked Flats) ---");

        // --- Filter by Project ---
        System.out.println("Filter by project:");
        System.out.println("1. All Projects Managed By You (Respecting View Filters)");
        System.out.println("2. A Specific Project Managed By You");
        System.out.println("0. Cancel");
        int projectFilterChoice = getIntInput("Enter choice: ", 0, 2);

        List<Project> projectsToReportOn = new ArrayList<>();
        if (projectFilterChoice == 0) return; // Cancel

        if (projectFilterChoice == 1) {
            // Get managed projects, applying current view filters (location/type)
            projectsToReportOn = getManagedProjectsApplyingFilters(); // Use helper
            if (projectsToReportOn.isEmpty()) {
                // Message printed by helper if empty
                return;
            }
            System.out.println("Reporting on all projects you manage"
                    + (filterLocation != null || filterFlatType != null ? " (matching current view filters)." : "."));
        } else { // Choice is 2
            // Get managed projects without applying view filters for selection
            List<Project> allMyProjects = projectService.getProjectsManagedBy(currentUser.getNric());
            if (allMyProjects.isEmpty()) {
                System.out.println("You are not managing any projects.");
                return;
            }
            // Let user select one specific project
            viewAndSelectProject(allMyProjects.stream().sorted(Comparator.comparing(Project::getProjectName)).collect(Collectors.toList()), "Select Specific Project to Report On");
            Project specificProject = selectProjectFromList(allMyProjects);
            if (specificProject == null) return; // Cancelled selection
            projectsToReportOn.add(specificProject);
            System.out.println("Reporting specifically for project: " + specificProject.getProjectName());
        }

        // Get list of names of projects to include in the report
        final List<String> finalProjectNames = projectsToReportOn.stream()
                .map(Project::getProjectName)
                .collect(Collectors.toList());

        // --- Filter by Flat Type ---
        System.out.print("Filter report by Flat Type (TWO_ROOM, THREE_ROOM, or leave blank for all): ");
        String typeStr = scanner.nextLine().trim();
        FlatType filterReportFlatType = null;
        if (!typeStr.isEmpty()) {
            filterReportFlatType = FlatType.fromString(typeStr); // Use enum parser
            if (filterReportFlatType != null) {
                System.out.println("Filtering report for flat type: " + filterReportFlatType.getDisplayName());
            } else {
                System.out.println("Invalid flat type entered. Reporting for all types.");
            }
        }

        // --- Filter by Marital Status ---
        System.out.print("Filter report by Marital Status (SINGLE, MARRIED, or leave blank for all): ");
        String maritalStr = scanner.nextLine().trim().toUpperCase();
        MaritalStatus filterMaritalStatus = null;
        if (!maritalStr.isEmpty()) {
            try {
                filterMaritalStatus = MaritalStatus.valueOf(maritalStr); // Use enum valueOf
                System.out.println("Filtering report for marital status: " + filterMaritalStatus);
            } catch (IllegalArgumentException e) {
                System.out.println("Invalid marital status. Reporting for all statuses.");
            }
        }

        // --- Filter by Age Range ---
        int minAge = getIntInput("Filter report by Minimum Age (e.g., 21, or 0 for no minimum): ", 0, 120);
        int maxAge = getIntInput("Filter report by Maximum Age (e.g., 65, or 0 for no maximum): ", 0, 120);
        if (minAge > 0 || maxAge > 0) {
            System.out.println("Filtering report for age range: "
                    + (minAge > 0 ? minAge : "Any") + " to "
                    + (maxAge > 0 ? maxAge : "Any"));
        }
         // Add validation: maxAge should not be less than minAge if both are specified > 0
         if (minAge > 0 && maxAge > 0 && maxAge < minAge) {
             System.out.println("Warning: Maximum age cannot be less than minimum age. Ignoring age filters.");
             minAge = 0;
             maxAge = 0;
         }

        // --- Final Filter Variables --- (effectively final for lambda)
        final FlatType finalFilterReportFlatType = filterReportFlatType;
        final MaritalStatus finalFilterMaritalStatus = filterMaritalStatus;
        final int finalMinAge = minAge;
        final int finalMaxAge = maxAge;

        // --- Generate Report Data ---
        List<BTOApplication> bookedApplications = applicationService.getAllApplications().values().stream()
                // 1. Filter by Status = BOOKED
                .filter(app -> app.getStatus() == ApplicationStatus.BOOKED)
                // 2. Filter by selected Project(s)
                .filter(app -> finalProjectNames.contains(app.getProjectName()))
                // 3. Filter by selected Flat Type (if any)
                .filter(app -> finalFilterReportFlatType == null || app.getFlatTypeApplied() == finalFilterReportFlatType)
                // 4. Filter by Applicant Demographics (Marital Status, Age)
                .filter(app -> {
                    User user = userService.findUserByNric(app.getApplicantNric());
                    if (user == null) return false; // Skip if user data not found

                    // Apply Marital Status filter
                    if (finalFilterMaritalStatus != null && user.getMaritalStatus() != finalFilterMaritalStatus) return false;
                    // Apply Min Age filter
                    if (finalMinAge > 0 && user.getAge() < finalMinAge) return false;
                    // Apply Max Age filter
                    if (finalMaxAge > 0 && user.getAge() > finalMaxAge) return false;

                    return true; // Include if all filters pass
                })
                // Sort the results (e.g., by Project Name then Applicant NRIC)
                .sorted(Comparator.comparing(BTOApplication::getProjectName)
                                  .thenComparing(BTOApplication::getApplicantNric))
                .collect(Collectors.toList());

        // --- Display Report ---
        System.out.println("\n--- Report: Applicants with Flat Bookings ---");
        // Display applied filters
        System.out.println("Filters Applied: Projects=" + String.join(", ", finalProjectNames)
                         + ", FlatType=" + (finalFilterReportFlatType == null ? "Any" : finalFilterReportFlatType.getDisplayName())
                         + ", MaritalStatus=" + (finalFilterMaritalStatus == null ? "Any" : finalFilterMaritalStatus)
                         + ", Age=" + (finalMinAge > 0 ? finalMinAge : "Any") + "-" + (finalMaxAge > 0 ? finalMaxAge : "Any"));
        System.out.println("---------------------------------------------------------------------------------");
        System.out.printf("%-15s | %-15s | %-5s | %-10s | %-15s | %-8s\n",
                "Applicant NRIC", "Name", "Age", "Marital", "Project Name", "FlatType");
        System.out.println("---------------------------------------------------------------------------------");

        if (bookedApplications.isEmpty()) {
            System.out.println("No matching booked applications found for the specified filters.");
        } else {
            // Print each booked application row
            bookedApplications.forEach(app -> {
                User user = userService.findUserByNric(app.getApplicantNric()); // Fetch user details again
                System.out.printf("%-15s | %-15s | %-5s | %-10s | %-15s | %-8s\n",
                        app.getApplicantNric(),
                        user != null ? user.getName() : "N/A",
                        user != null ? String.valueOf(user.getAge()) : "N/A", // Age as string
                        user != null ? user.getMaritalStatus().name() : "N/A", // Marital status name
                        app.getProjectName(),
                        app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A");
            });
        }
        System.out.println("---------------------------------------------------------------------------------");
        System.out.println("Total matching booked applicants: " + bookedApplications.size());
        System.out.println("--- End of Report ---");
    }

     // Helper to get managed projects, applying view filters
     private List<Project> getManagedProjectsApplyingFilters() {
        return projectService.getProjectsManagedBy(currentUser.getNric())
            .stream()
            .filter(p -> filterLocation == null || p.getNeighborhood().equalsIgnoreCase(filterLocation))
            .filter(p -> filterFlatType == null || p.getFlatTypes().containsKey(filterFlatType))
            .sorted(Comparator.comparing(Project::getProjectName))
            .collect(Collectors.toList());
     }
}
