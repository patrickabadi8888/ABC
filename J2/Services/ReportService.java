package Services;

import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;

import Enums.ApplicationStatus;
import Enums.FlatType;
import Enums.MaritalStatus;
import Interfaces.Repositories.IApplicationRepository;
import Interfaces.Repositories.IUserRepository;
import Interfaces.Services.IReportService;
import Models.BTOApplication;
import Models.User;

public class ReportService implements IReportService {

    private final IApplicationRepository applicationRepository;
    private final IUserRepository userRepository;

    public ReportService(IApplicationRepository applicationRepository, IUserRepository userRepository) {
        this.applicationRepository = applicationRepository;
        this.userRepository = userRepository;
    }

    @Override
    public List<BTOApplication> generateBookedApplicantReport(List<String> projectNames, FlatType filterFlatType,
                                                              MaritalStatus filterMaritalStatus, int minAge, int maxAge) {

        if (projectNames == null || projectNames.isEmpty()) {
            System.out.println("No projects specified for the report.");
            return List.of(); // Return empty list
        }

        // Fetch all applications once
        Map<String, BTOApplication> allApplications = applicationRepository.getAllApplications();
        Map<String, User> allUsers = userRepository.getAllUsers(); // Fetch users for filtering

        return allApplications.values().stream()
                // Filter by BOOKED status
                .filter(app -> app.getStatus() == ApplicationStatus.BOOKED)
                // Filter by specified project names
                .filter(app -> projectNames.contains(app.getProjectName()))
                // Filter by flat type (if specified)
                .filter(app -> filterFlatType == null || app.getFlatTypeApplied() == filterFlatType)
                // Filter by applicant details (marital status, age)
                .filter(app -> {
                    User user = allUsers.get(app.getApplicantNric());
                    if (user == null) return false; // Skip if user data not found

                    // Apply marital status filter
                    if (filterMaritalStatus != null && user.getMaritalStatus() != filterMaritalStatus) {
                        return false;
                    }
                    // Apply min age filter (maxAge=0 means no upper limit)
                    if (minAge > 0 && user.getAge() < minAge) {
                        return false;
                    }
                    // Apply max age filter (maxAge=0 means no upper limit)
                    if (maxAge > 0 && user.getAge() > maxAge) {
                        return false;
                    }
                    return true; // Passed all filters
                })
                // Sort the results
                .sorted(Comparator.comparing(BTOApplication::getProjectName)
                                  .thenComparing(BTOApplication::getApplicantNric))
                .collect(Collectors.toList());
    }

    @Override
    public void displayApplicantReport(List<BTOApplication> reportData, FlatType filterFlatType,
                                       MaritalStatus filterMaritalStatus, int minAge, int maxAge) {

        System.out.println("\n--- Report: Applicants with Flat Bookings ---");
        System.out.println("Filters Applied: Project(s) selected, FlatType="
                + (filterFlatType == null ? "Any" : filterFlatType.getDisplayName()) + ", MaritalStatus="
                + (filterMaritalStatus == null ? "Any" : filterMaritalStatus) + ", Age="
                + (minAge > 0 ? minAge : "Any") + "-" + (maxAge > 0 ? maxAge : "Any"));
        System.out.println("---------------------------------------------------------------------------------");
        System.out.printf("%-15s | %-15s | %-5s | %-10s | %-15s | %-8s\n",
                "Applicant NRIC", "Name", "Age", "Marital", "Project Name", "FlatType");
        System.out.println("---------------------------------------------------------------------------------");

        if (reportData == null || reportData.isEmpty()) {
            System.out.println("No matching booked applications found for the specified filters.");
        } else {
            // Fetch all users once to avoid repeated lookups inside the loop
            Map<String, User> allUsers = userRepository.getAllUsers();
            reportData.forEach(app -> {
                User user = allUsers.get(app.getApplicantNric());
                System.out.printf("%-15s | %-15s | %-5s | %-10s | %-15s | %-8s\n",
                        app.getApplicantNric(),
                        (user != null) ? user.getName() : "N/A",
                        (user != null) ? String.valueOf(user.getAge()) : "N/A", // Age as string
                        (user != null) ? user.getMaritalStatus().name() : "N/A",
                        app.getProjectName(),
                        (app.getFlatTypeApplied() != null) ? app.getFlatTypeApplied().getDisplayName() : "N/A");
            });
        }
        System.out.println("---------------------------------------------------------------------------------");
        System.out.println("Total matching booked applicants: " + (reportData == null ? 0 : reportData.size()));
        System.out.println("--- End of Report ---");
    }
}
