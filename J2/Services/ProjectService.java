package Services;

import java.util.Comparator;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import Enums.FlatType;
import Interfaces.Repositories.IApplicationRepository;
import Interfaces.Repositories.IEnquiryRepository;
import Interfaces.Repositories.IOfficerRegistrationRepository;
import Interfaces.Repositories.IProjectRepository;
import Interfaces.Services.IApplicationService;
import Interfaces.Services.IEligibilityService;
import Interfaces.Services.IEnquiryService;
import Interfaces.Services.IFilterService;
import Interfaces.Services.IOfficerRegistrationService;
import Interfaces.Services.IProjectService;
import Models.FlatTypeDetails;
import Models.HDBManager;
import Models.Project;
import Models.User;
import Utils.DateUtils;

public class ProjectService implements IProjectService {

    private final IProjectRepository projectRepository;
    private final IEligibilityService eligibilityService; // Needed for visibility/overlap checks
    private final IFilterService filterService; // Needed to apply filters for views
    // Services needed for cascading deletes or checks
    private final IApplicationService applicationService;
    private final IOfficerRegistrationService officerRegistrationService;
    private final IEnquiryService enquiryService;


    public ProjectService(IProjectRepository projectRepository,
                          IEligibilityService eligibilityService,
                          IFilterService filterService,
                          IApplicationService applicationService,
                          IOfficerRegistrationService officerRegistrationService,
                          IEnquiryService enquiryService) {
        this.projectRepository = projectRepository;
        this.eligibilityService = eligibilityService;
        this.filterService = filterService;
        this.applicationService = applicationService;
        this.officerRegistrationService = officerRegistrationService;
        this.enquiryService = enquiryService;
    }

    @Override
    public Project findProjectByName(String name) {
        return projectRepository.findProjectByName(name); // Delegate to repository
    }

    @Override
    public List<Project> getAllProjects() {
        return projectRepository.getAllProjects().stream()
               .sorted(Comparator.comparing(Project::getProjectName))
               .collect(Collectors.toList());
    }

    @Override
    public List<Project> getVisibleProjects(User currentUser) {
        // Get all projects, then filter by visibility for the specific user
        return projectRepository.getAllProjects().stream()
                .filter(p -> eligibilityService.isProjectVisibleToUser(currentUser, p))
                .sorted(Comparator.comparing(Project::getProjectName))
                .collect(Collectors.toList());
    }

     @Override
     public List<Project> getOpenProjects(User currentUser) {
         Date currentDate = DateUtils.getCurrentDate();
         // Get all projects and apply multiple filters
         return projectRepository.getAllProjects().stream()
                 // 1. Apply general location/type filters first
                 .filter(p -> filterService.getLocationFilter() == null || p.getNeighborhood().equalsIgnoreCase(filterService.getLocationFilter()))
                 .filter(p -> filterService.getFlatTypeFilter() == null || p.getFlatTypes().containsKey(filterService.getFlatTypeFilter()))
                 // 2. Check visibility for the current user
                 .filter(p -> eligibilityService.isProjectVisibleToUser(currentUser, p))
                 // 3. Check if application period is active
                 .filter(p -> p.isApplicationPeriodActive(currentDate))
                 // 4. Check eligibility and availability for the user
                 .filter(p -> {
                     // Check if user is eligible for *any* flat type in the project
                     boolean eligibleForAny = p.getFlatTypes().keySet().stream()
                             .anyMatch(flatType -> eligibilityService.canApplyForFlatType(currentUser, flatType));
                     if (!eligibleForAny) return false;

                     // Check if there's at least one flat type they are eligible for AND has units available
                     boolean availableAndEligibleExists = p.getFlatTypes().entrySet().stream()
                             .anyMatch(entry -> eligibilityService.canApplyForFlatType(currentUser, entry.getKey())
                                     && entry.getValue().getAvailableUnits() > 0);
                     return availableAndEligibleExists;
                 })
                 .sorted(Comparator.comparing(Project::getProjectName))
                 .collect(Collectors.toList());
     }


    @Override
    public List<Project> getManagedProjects(String managerNric) {
        // Get all projects, filter by manager NRIC, then apply view filters
        List<Project> allProjects = projectRepository.getAllProjects();
        List<Project> managed = allProjects.stream()
                .filter(p -> p.getManagerNric().equals(managerNric))
                .collect(Collectors.toList());
        // Apply current view filters (location/type) to the managed list
        return filterService.applyFilters(managed).stream()
                .sorted(Comparator.comparing(Project::getProjectName))
                .collect(Collectors.toList());
    }

    @Override
    public boolean createProject(String projectName, String neighborhood, Map<FlatType, FlatTypeDetails> flatTypes,
                                 Date openingDate, Date closingDate, HDBManager manager, int maxOfficers) {

        // 1. Validate Inputs (Basic)
        if (projectName == null || projectName.trim().isEmpty() || neighborhood == null || neighborhood.trim().isEmpty() ||
            flatTypes == null || flatTypes.isEmpty() || openingDate == null || closingDate == null || manager == null || maxOfficers < 1) {
            System.err.println("Error: Invalid parameters for creating project.");
            return false;
        }
        if (closingDate.before(openingDate)) {
             System.err.println("Error: Closing date cannot be before opening date.");
             return false;
        }
        if (maxOfficers > 10) { // Assuming max 10 based on original code
             System.err.println("Error: Maximum officer slots cannot exceed 10.");
             return false;
        }


        // 2. Check for duplicate project name
        if (projectRepository.findProjectByName(projectName) != null) {
            System.err.println("Error: Project name '" + projectName + "' already exists.");
            return false;
        }

        // 3. Check for date overlap with other projects managed by the same manager
        Project proposedProject = new Project(projectName, neighborhood, flatTypes, openingDate, closingDate, manager.getNric(), maxOfficers, List.of(), false); // Temp object for overlap check
        boolean overlaps = projectRepository.getAllProjects().stream()
                .filter(p -> p.getManagerNric().equals(manager.getNric()))
                .anyMatch(existingProject -> eligibilityService.checkDateOverlap(proposedProject, existingProject)); // Use eligibility service for check

        if (overlaps) {
            System.err.println("Error: The specified application period overlaps with another project you manage.");
            return false;
        }

        // 4. Create and Save Project
        // Visibility is false by default on creation
        Project newProject = new Project(projectName.trim(), neighborhood.trim(), flatTypes, openingDate, closingDate,
                                         manager.getNric(), maxOfficers, List.of(), false); // Empty officer list initially

        List<Project> currentProjects = projectRepository.getAllProjects();
        currentProjects.add(newProject);
        projectRepository.saveProjects(currentProjects);

        System.out.println("Project '" + newProject.getProjectName() + "' created successfully. Visibility is currently OFF.");
        return true;
    }

    @Override
    public boolean editProjectDetails(Project project, String newNeighborhood, Map<FlatType, FlatTypeDetails> newFlatTypes,
                                      Date newOpeningDate, Date newClosingDate, int newMaxSlots) {
        if (project == null) return false;

        // Store original values for comparison/revert if needed
        String originalNeighborhood = project.getNeighborhood();
        Map<FlatType, FlatTypeDetails> originalFlatTypes = project.getFlatTypes(); // Get unmodifiable map
        Date originalOpening = project.getApplicationOpeningDate();
        Date originalClosing = project.getApplicationClosingDate();
        int originalMaxSlots = project.getMaxOfficerSlots();

        // Apply changes tentatively
        boolean changed = false;
        if (newNeighborhood != null && !newNeighborhood.trim().isEmpty() && !newNeighborhood.trim().equals(originalNeighborhood)) {
            project.setNeighborhood(newNeighborhood.trim());
            changed = true;
        }
        if (newFlatTypes != null && !newFlatTypes.equals(originalFlatTypes)) { // Simple equality check might work for maps if FlatTypeDetails has proper equals
            project.setFlatTypes(newFlatTypes); // Assumes FlatTypeDetails are correctly updated by caller
            changed = true;
        }

        Date finalOpening = (newOpeningDate != null) ? newOpeningDate : originalOpening;
        Date finalClosing = (newClosingDate != null) ? newClosingDate : originalClosing;
        boolean datesChanged = !finalOpening.equals(originalOpening) || !finalClosing.equals(originalClosing);
        boolean datesValid = true;

        if (datesChanged) {
            if (finalClosing.before(finalOpening)) {
                System.err.println("Error: New closing date cannot be before new opening date. Dates not updated.");
                datesValid = false;
            } else {
                // Check for overlap ONLY if dates changed and are valid relative to each other
                Project proposedProjectDates = new Project( // Temp object for check
                        project.getProjectName(), project.getNeighborhood(), project.getFlatTypes(),
                        finalOpening, finalClosing, project.getManagerNric(), project.getMaxOfficerSlots(),
                        project.getApprovedOfficerNrics(), project.isVisible());

                boolean overlaps = projectRepository.getAllProjects().stream()
                        .filter(p -> p.getManagerNric().equals(project.getManagerNric()) && !p.getProjectName().equals(project.getProjectName())) // Exclude self
                        .anyMatch(existingProject -> eligibilityService.checkDateOverlap(proposedProjectDates, existingProject));

                if (overlaps) {
                    System.err.println("Error: The new application period overlaps with another project you manage. Dates not updated.");
                    datesValid = false;
                }
            }
        }

        if (datesChanged && datesValid) {
            project.setApplicationOpeningDate(finalOpening);
            project.setApplicationClosingDate(finalClosing);
            changed = true;
            System.out.println("Application dates updated.");
        }

        if (newMaxSlots >= 0 && newMaxSlots != originalMaxSlots) {
             // setMaxOfficerSlots has internal validation against current approved count
            if (project.setMaxOfficerSlots(newMaxSlots)) {
                 changed = true;
            } else {
                 // Error message printed within setMaxOfficerSlots
            }
        }

        // If any valid change occurred, save the project list
        if (changed) {
            List<Project> allProjects = projectRepository.getAllProjects();
             for (int i = 0; i < allProjects.size(); i++) {
                 if (allProjects.get(i).getProjectName().equals(project.getProjectName())) {
                     allProjects.set(i, project); // Replace with the modified project object
                     break;
                 }
             }
            projectRepository.saveProjects(allProjects);
            System.out.println("Project details update attempt complete.");
            return true;
        } else {
            System.out.println("No changes detected or changes were invalid. Project not saved.");
            // Revert changes if necessary? The project object was modified directly.
            // If validation failed, the setters might have prevented bad state, or we might need explicit revert.
            // For simplicity, assume setters handled invalid states or the caller handles the object state.
            return false;
        }
    }

    @Override
    public boolean deleteProject(Project projectToDelete) {
        if (projectToDelete == null) return false;
        String projectName = projectToDelete.getProjectName();

        // 1. Check for active applications (using ApplicationService might be cleaner)
         boolean hasActiveApplications = applicationService.getAllApplications().values().stream()
                .anyMatch(app -> app.getProjectName().equals(projectName) &&
                        (app.getStatus() == ApplicationStatus.PENDING ||
                         app.getStatus() == ApplicationStatus.SUCCESSFUL ||
                         app.getStatus() == ApplicationStatus.BOOKED ||
                         app.getStatus() == ApplicationStatus.PENDING_WITHDRAWAL));

        // 2. Check for active officer registrations (using OfficerRegService might be cleaner)
         boolean hasActiveRegistrations = officerRegistrationService.getAllRegistrations().values().stream()
                .anyMatch(reg -> reg.getProjectName().equals(projectName) &&
                        (reg.getStatus() == OfficerRegistrationStatus.PENDING ||
                         reg.getStatus() == OfficerRegistrationStatus.APPROVED));


        if (hasActiveApplications || hasActiveRegistrations) {
            System.out.println("Error: Cannot delete project '" + projectName + "'.");
            if (hasActiveApplications)
                System.out.println("- It has active BTO applications (Pending/Successful/Booked/PendingWithdrawal).");
            if (hasActiveRegistrations)
                System.out.println("- It has active Officer registrations (Pending/Approved).");
            System.out.println("Resolve these associations before deleting.");
            return false;
        }

        // 3. Remove the project from the repository
        List<Project> currentProjects = projectRepository.getAllProjects();
        boolean removed = currentProjects.removeIf(p -> p.getProjectName().equals(projectName));

        if (removed) {
            projectRepository.saveProjects(currentProjects);
            System.out.println("Project '" + projectName + "' deleted successfully.");

            // 4. Cascade delete related data using other services
            applicationService.removeApplicationsForProject(projectName);
            officerRegistrationService.removeRegistrationsForProject(projectName);
            enquiryService.removeEnquiriesForProject(projectName);

            return true;
        } else {
            System.err.println("Error: Failed to remove project '" + projectName + "' from list (not found?).");
            return false;
        }
    }

    @Override
    public boolean toggleProjectVisibility(Project project) {
        if (project == null) return false;

        boolean currentVisibility = project.isVisible();
        project.setVisibility(!currentVisibility); // Toggle the state

        // Save the updated project list
        List<Project> allProjects = projectRepository.getAllProjects();
         for (int i = 0; i < allProjects.size(); i++) {
             if (allProjects.get(i).getProjectName().equals(project.getProjectName())) {
                 allProjects.set(i, project); // Replace with the modified project object
                 break;
             }
         }
        projectRepository.saveProjects(allProjects);

        System.out.println("Project '" + project.getProjectName() + "' visibility toggled to "
                + (project.isVisible() ? "ON" : "OFF") + ".");
        return true;
    }

     @Override
     public boolean checkDateOverlap(Project p1, Project p2) {
         // Delegate to eligibility service which already has this logic
         return eligibilityService.checkDateOverlap(p1, p2);
     }
}
