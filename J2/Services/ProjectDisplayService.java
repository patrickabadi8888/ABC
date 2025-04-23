package Services;

import java.util.List;
import java.util.Map;
import java.util.Scanner;
import java.util.stream.Collectors;

import Enums.FlatType;
import Enums.UserRole;
import Interfaces.Services.IEligibilityService;
import Interfaces.Services.IFilterService;
import Interfaces.Services.IProjectDisplayService;
import Models.Applicant;
import Models.FlatTypeDetails;
import Models.Project;
import Models.User;
import Utils.DateUtils;

public class ProjectDisplayService implements IProjectDisplayService {

    private final IFilterService filterService; // To display current filters
    private final IEligibilityService eligibilityService; // To show eligibility marks

    public ProjectDisplayService(IFilterService filterService, IEligibilityService eligibilityService) {
        this.filterService = filterService;
        this.eligibilityService = eligibilityService;
    }

    @Override
    public void displayProjectList(List<Project> projectList, String prompt, User currentUser) {
        if (projectList == null) {
             System.out.println("No project list provided.");
             return;
        }
        if (projectList.isEmpty()) {
            System.out.println("No projects match the current criteria.");
            return;
        }

        System.out.println("\n--- " + prompt + " ---");
        System.out.println("Current Filters: " + filterService.getCurrentFilterStatus());
        System.out.println(
                "--------------------------------------------------------------------------------------------------------------------");
        System.out.printf("%-3s %-15s %-12s %-10s %-10s %-8s %-25s\n", "#", "Project Name", "Neighborhood", "Open",
                "Close", "Visible", "Flat Types (Available/Total, Price, Eligibility)");
        System.out.println(
                "--------------------------------------------------------------------------------------------------------------------");

        for (int i = 0; i < projectList.size(); i++) {
            Project p = projectList.get(i);
            // Check visibility again based on the current user, although the list might already be filtered
            boolean isVisible = eligibilityService.isProjectVisibleToUser(currentUser, p);

            System.out.printf("%-3d %-15s %-12s %-10s %-10s %-8s ",
                    i + 1,
                    p.getProjectName(),
                    p.getNeighborhood(),
                    DateUtils.formatDate(p.getApplicationOpeningDate()),
                    DateUtils.formatDate(p.getApplicationClosingDate()),
                    isVisible ? "On" : "Off"); // Display effective visibility

            // Generate flat details string
            String flatDetails = p.getFlatTypes().entrySet().stream()
                    .sorted(Map.Entry.comparingByKey()) // Sort by FlatType enum order
                    .map(entry -> {
                        FlatType type = entry.getKey();
                        FlatTypeDetails details = entry.getValue();
                        String eligibilityMark = "";
                        // Show eligibility only for Applicants/Officers (potential applicants)
                        if (currentUser != null && currentUser.getRole() != UserRole.HDB_MANAGER) {
                            if (!eligibilityService.canApplyForFlatType(currentUser, type)) {
                                eligibilityMark = " (Ineligible)";
                            } else if (details.getAvailableUnits() <= 0) {
                                eligibilityMark = " (No Units)";
                            }
                        }
                        return String.format("%s: %d/%d ($%.0f)%s",
                                type.getDisplayName(), details.getAvailableUnits(), details.getTotalUnits(),
                                details.getSellingPrice(), eligibilityMark);
                    })
                    .collect(Collectors.joining(", "));
            System.out.println(flatDetails);

            // Show manager/officer info only for Manager/Officer roles
            if (currentUser != null && currentUser.getRole() != UserRole.APPLICANT) {
                System.out.printf("%-3s %-15s %-12s %-10s %-10s %-8s %-25s\n", "", "", "", "", "", "", // Alignment placeholders
                        "Mgr: " + p.getManagerNric() + ", Officers: " + p.getApprovedOfficerNrics().size() + "/"
                                + p.getMaxOfficerSlots());
            }
            if (i < projectList.size() - 1)
                System.out.println("---"); // Separator between projects

        }
        System.out.println(
                "--------------------------------------------------------------------------------------------------------------------");
    }

    @Override
    public Project selectProjectFromList(List<Project> projectList, Scanner scanner) {
        if (projectList == null || projectList.isEmpty()) {
            return null; // No project to select
        }
        System.out.print("Enter the number of the project (or 0 to cancel): ");
        int choice;
        try {
            // Use InputUtils or handle directly
            String input = scanner.nextLine();
            choice = Integer.parseInt(input);

            if (choice == 0) {
                System.out.println("Operation cancelled.");
                return null;
            }
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
}
