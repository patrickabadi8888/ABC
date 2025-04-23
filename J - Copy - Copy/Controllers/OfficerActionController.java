package Controllers;

import java.util.Comparator;
import java.util.Date;
import java.util.List;
import java.util.Scanner;
import java.util.stream.Collectors;
import java.util.Collections;

import Enums.OfficerRegistrationStatus;
import Models.HDBOfficer;
import Models.OfficerRegistration;
import Models.Project;
import Models.User;
import Services.IApplicationService;
import Services.IOfficerRegistrationService;
import Services.IProjectService;
import Services.IUserService;
import Utils.DateUtils;


// Handles officer-specific actions like registration and status viewing
public class OfficerActionController extends BaseController {

    public OfficerActionController(IUserService userService, IProjectService projectService,
                                   IApplicationService applicationService, IOfficerRegistrationService officerRegistrationService,
                                   User currentUser, Scanner scanner, AuthController authController) {
        super(userService, projectService, applicationService, officerRegistrationService, currentUser, scanner, authController);
    }

    public void registerForProject() {
        if (!(currentUser instanceof HDBOfficer)) {
             System.out.println("Error: Only HDB Officers can register to handle projects.");
             return;
        }
        HDBOfficer officer = (HDBOfficer) currentUser;
        Date currentDate = DateUtils.getCurrentDate();
        // Sync data is handled in BTOApp main loop

        // Check Officer's applicant status first
        if (officer.hasActiveApplication() || officer.hasBooked()) { // Check for booked status as well
            System.out.println("Error: Cannot register to handle a project while you have an active or booked BTO application ("
                    + officer.getAppliedProjectName() + ", Status: " + officer.getApplicationStatus() + ").");
            return;
        }
         if (officer.hasPendingWithdrawal()) {
            System.out.println("Error: Cannot register to handle a project while you have a pending withdrawal request for application '" + officer.getAppliedProjectName() + "'.");
            return;
        }


        System.out.println("\n--- Register to Handle Project ---");

        // Find project currently handled by this officer (if any)
        Project currentlyHandlingProject = getOfficerHandlingProject(officer); // Use BaseController method

        // Find projects this officer has PENDING registrations for
        List<Project> pendingRegistrationProjects = officerRegistrationService.getRegistrationsByOfficer(officer.getNric())
                .stream()
                .filter(reg -> reg.getStatus() == OfficerRegistrationStatus.PENDING)
                .map(reg -> projectService.findProjectByName(reg.getProjectName()))
                .filter(p -> p != null) // Filter out projects that might not exist anymore
                .collect(Collectors.toList());

        // Find projects available for registration
        List<Project> availableProjects = projectService.getAllProjects().stream()
                // 1. Project must have remaining slots
                .filter(p -> p.getRemainingOfficerSlots() > 0)
                // 2. Project's application period must not be expired
                .filter(p -> !p.isApplicationPeriodExpired(currentDate))
                // 3. Officer must not already have *any* registration (Pending, Approved, Rejected) for this project
                .filter(p -> officerRegistrationService.getRegistrationsByOfficer(officer.getNric())
                                .stream()
                                .noneMatch(reg -> reg.getProjectName().equals(p.getProjectName())))
                // 4. Project dates must not overlap with the currently handled project (if any)
                .filter(p -> currentlyHandlingProject == null || !checkDateOverlap(p, currentlyHandlingProject))
                // 5. Project dates must not overlap with any project the officer has a PENDING registration for
                .filter(p -> pendingRegistrationProjects.stream().noneMatch(pendingProject -> checkDateOverlap(p, pendingProject)))
                // 6. Officer must not have *any* past or present BTO application for this project
                .filter(p -> applicationService.getApplicationsByApplicant(officer.getNric())
                                .stream()
                                .noneMatch(app -> app.getProjectName().equals(p.getProjectName())))
                .sorted(Comparator.comparing(Project::getProjectName)) // Sort alphabetically
                .collect(Collectors.toList());

        if (availableProjects.isEmpty()) {
            System.out.println("No projects currently available for you to register for based on eligibility criteria:");
            System.out.println("- Project must have open officer slots and not be expired.");
            System.out.println("- You must not already have any registration (Pending/Approved/Rejected) for the project.");
            System.out.println("- You cannot have an active/booked BTO application or a pending withdrawal request.");
            System.out.println("- Project dates cannot overlap with a project you are already handling.");
            System.out.println("- Project dates cannot overlap with a project you have a PENDING registration for.");
            System.out.println("- You cannot register for a project you have previously applied for (any status).");
            return;
        }

        viewAndSelectProject(availableProjects, "Select Project to Register For");
        Project selectedProject = selectProjectFromList(availableProjects);

        if (selectedProject != null) {
            // Create registration - ID is generated internally based on NRIC and Project Name
            OfficerRegistration newRegistration = new OfficerRegistration(officer.getNric(),
                    selectedProject.getProjectName(), currentDate);
            officerRegistrationService.addRegistration(newRegistration); // Add via service
            System.out.println("Registration request submitted for project '" + selectedProject.getProjectName()
                    + "'. Status: PENDING approval by Manager.");
            // Save immediately
            officerRegistrationService.saveOfficerRegistrations(officerRegistrationService.getAllRegistrations());
        }
    }

    public void viewRegistrationStatus() {
        if (!(currentUser instanceof HDBOfficer)) return;
        HDBOfficer officer = (HDBOfficer) currentUser;
        System.out.println("\n--- Your HDB Officer Registration Status ---");

        // Check currently handled project first
        Project handlingProject = getOfficerHandlingProject(officer); // Use BaseController method
        if (handlingProject != null) {
            System.out.println("You are currently APPROVED and HANDLING project: " + handlingProject.getProjectName());
            System.out.println("  (Application Period: " + DateUtils.formatDate(handlingProject.getApplicationOpeningDate()) + " to " + DateUtils.formatDate(handlingProject.getApplicationClosingDate()) + ")");
            System.out.println("----------------------------------------");
        }

        // Get all other registrations (excluding the currently active 'approved' one if found)
        List<OfficerRegistration> myOtherRegistrations = officerRegistrationService.getRegistrationsByOfficer(officer.getNric())
                .stream()
                // Filter out the one identified as currently handling (if any)
                .filter(reg -> handlingProject == null || !reg.getProjectName().equals(handlingProject.getProjectName()))
                .sorted(Comparator.comparing(OfficerRegistration::getRegistrationDate).reversed()) // Sort by date descending
                .collect(Collectors.toList());

        if (myOtherRegistrations.isEmpty() && handlingProject == null) {
            System.out.println("You have no past or pending registration requests.");
        } else if (!myOtherRegistrations.isEmpty()) {
            System.out.println("Other Registration History/Requests:");
            for (OfficerRegistration reg : myOtherRegistrations) {
                System.out.printf("- Project: %-15s | Status: %-10s | Date: %s\n",
                        reg.getProjectName(), reg.getStatus(), DateUtils.formatDate(reg.getRegistrationDate()));
            }
        } else {
             // This case means handlingProject != null and myOtherRegistrations is empty.
             // The handling project info was already printed. No need to print anything else.
        }
    }

    public void viewHandlingProjectDetails() {
         if (!(currentUser instanceof HDBOfficer)) return;
         HDBOfficer officer = (HDBOfficer) currentUser;

        // Find the project the officer is currently handling
        Project project = getOfficerHandlingProject(officer); // Use BaseController method

        if (project == null) {
            System.out.println("You are not currently handling any active project. Register for one first or check registration status.");
            return;
        }

        System.out.println("\n--- Details for Handling Project: " + project.getProjectName() + " ---");
        // Use the viewAndSelectProject helper, passing a list containing only the handling project
        // This reuses the detailed project display format.
        viewAndSelectProject(Collections.singletonList(project), "Project Details");
    }
}
