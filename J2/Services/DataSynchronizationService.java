package Services;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import Enums.OfficerRegistrationStatus;
import Interfaces.Repositories.IApplicationRepository;
import Interfaces.Repositories.IOfficerRegistrationRepository;
import Interfaces.Repositories.IProjectRepository;
import Interfaces.Repositories.IUserRepository;
import Interfaces.Services.IApplicationService;
import Interfaces.Services.IDataSynchronizationService;
import Models.Applicant;
import Models.HDBOfficer;
import Models.OfficerRegistration;
import Models.Project;
import Models.User;

public class DataSynchronizationService implements IDataSynchronizationService {

    private final IUserRepository userRepository;
    private final IProjectRepository projectRepository;
    private final IApplicationRepository applicationRepository;
    private final IOfficerRegistrationRepository officerRegistrationRepository;
    private final IApplicationService applicationService; // Needed for adjustUnitsOnLoad and syncApplicantStatus

    public DataSynchronizationService(
            IUserRepository userRepository,
            IProjectRepository projectRepository,
            IApplicationRepository applicationRepository,
            IOfficerRegistrationRepository officerRegistrationRepository,
            IApplicationService applicationService) {
        this.userRepository = userRepository;
        this.projectRepository = projectRepository;
        this.applicationRepository = applicationRepository;
        this.officerRegistrationRepository = officerRegistrationRepository;
        this.applicationService = applicationService;
    }

    @Override
    public void synchronizeAllData() {
        System.out.println("Synchronizing loaded data...");

        // Load all data first
        Map<String, User> users = userRepository.getAllUsers();
        List<Project> projects = projectRepository.getAllProjects();
        Map<String, OfficerRegistration> registrations = officerRegistrationRepository.getAllRegistrations();
        // Applications are loaded implicitly by applicationService methods if needed

        boolean registrationsModified = false;
        boolean projectsModified = false; // Track if projects need saving due to officer list changes

        // 1. Synchronize Applicant Status based on Applications
        users.values().stream()
                .filter(u -> u instanceof Applicant)
                .map(u -> (Applicant) u)
                .forEach(applicationService::synchronizeApplicantStatus);
        // Note: User saving is typically handled elsewhere (e.g., password change)

        // 2. Synchronize Project Officer Lists and Registrations
        for (Project project : projects) {
            List<String> currentApprovedNrics = new ArrayList<>(project.getApprovedOfficerNrics()); // Modifiable copy
            List<String> nricsToRemoveFromProject = new ArrayList<>();
            boolean projectOfficerListChanged = false;

            // Check existing officers in the project list
            for (String officerNric : currentApprovedNrics) {
                User user = users.get(officerNric);
                // If user doesn't exist or is not an officer, remove from project list
                if (!(user instanceof HDBOfficer)) {
                    System.err.println("Data Sync Warning: NRIC " + officerNric + " in project '"
                            + project.getProjectName()
                            + "' approved list is not a valid HDB Officer. Removing from project.");
                    nricsToRemoveFromProject.add(officerNric);
                    projectOfficerListChanged = true;
                    continue; // Move to next NRIC in project list
                }

                // Check if a corresponding APPROVED registration exists
                String expectedRegId = OfficerRegistration.generateId(officerNric, project.getProjectName());
                OfficerRegistration existingReg = registrations.get(expectedRegId);

                if (existingReg == null || existingReg.getStatus() != OfficerRegistrationStatus.APPROVED) {
                    System.out.println("Info (Sync): Auto-creating/updating APPROVED registration for Officer " + officerNric
                            + " for Project '" + project.getProjectName() + "' based on project's officer list.");

                    // Use project opening date as a placeholder if registration date is unknown
                    Date placeholderDate = project.getApplicationOpeningDate() != null
                            ? project.getApplicationOpeningDate()
                            : new Date(0); // Epoch as fallback

                    OfficerRegistration syncReg = new OfficerRegistration(expectedRegId, officerNric,
                            project.getProjectName(), OfficerRegistrationStatus.APPROVED, placeholderDate);
                    registrations.put(syncReg.getRegistrationId(), syncReg);
                    registrationsModified = true;
                }
            }

            // Remove invalid officers found above from the project's list
            if (!nricsToRemoveFromProject.isEmpty()) {
                 project.internal_setApprovedOfficers(
                     currentApprovedNrics.stream()
                         .filter(nric -> !nricsToRemoveFromProject.contains(nric))
                         .collect(Collectors.toList())
                 );
                 projectsModified = true;
            }

             // Check officer count vs slots after cleanup
             if (project.getApprovedOfficerNrics().size() > project.getMaxOfficerSlots()) {
                  System.err.println("Warning (Sync): Project '" + project.getProjectName() + "' still has more approved officers ("+project.getApprovedOfficerNrics().size()+") than slots ("+project.getMaxOfficerSlots()+") after cleanup. Data inconsistency exists.");
             }
        }


        // 3. Check Registrations against Projects and Users
        List<String> regIdsToRemove = new ArrayList<>();
        for (OfficerRegistration reg : registrations.values()) {
            User user = users.get(reg.getOfficerNric());
            Project project = projects.stream()
                                    .filter(p -> p.getProjectName().equals(reg.getProjectName()))
                                    .findFirst().orElse(null);

            // If user doesn't exist or isn't an officer, mark registration for removal
            if (!(user instanceof HDBOfficer)) {
                 System.err.println("Data Sync Warning: Registration " + reg.getRegistrationId()
                            + " refers to invalid or non-officer NRIC: " + reg.getOfficerNric() + ". Removing registration.");
                 regIdsToRemove.add(reg.getRegistrationId());
                 registrationsModified = true;
                 continue;
            }

            // If project doesn't exist, mark registration for removal
            if (project == null) {
                 System.err.println("Data Sync Warning: Registration " + reg.getRegistrationId()
                            + " refers to a non-existent project '" + reg.getProjectName()
                            + "'. Removing registration.");
                 regIdsToRemove.add(reg.getRegistrationId());
                 registrationsModified = true;
                 continue;
            }

            // If registration is APPROVED but officer is NOT in project list, log warning (don't auto-remove registration, project list might be wrong)
            if (reg.getStatus() == OfficerRegistrationStatus.APPROVED && !project.getApprovedOfficerNrics().contains(reg.getOfficerNric())) {
                 System.err.println("Data Sync Warning: Approved registration " + reg.getRegistrationId()
                            + " exists, but officer " + reg.getOfficerNric() + " is NOT in project '"
                            + project.getProjectName()
                            + "' approved list. Data inconsistency exists.");
                 // Potential action: Change registration status to PENDING? Or just warn? Just warning for now.
            }
        }

        // Remove invalid registrations found above
        if (!regIdsToRemove.isEmpty()) {
            regIdsToRemove.forEach(registrations::remove);
            registrationsModified = true;
        }

        // 4. Adjust Project Available Units based on Booked Applications
        // This modifies project objects in the 'projects' list
        applicationService.adjustUnitsOnLoad(); // This now reads projects/apps via repositories

        // 5. Save modified data
        if (registrationsModified) {
            System.out.println("Saving updated officer registrations due to synchronization...");
            officerRegistrationRepository.saveOfficerRegistrations(registrations);
        }
        // Check if projects were modified by unit sync OR officer list cleanup
        // The adjustUnitsOnLoad method now saves projects internally if needed.
        // We only need to save if the officer list was changed here.
        if (projectsModified) {
             System.out.println("Saving updated projects due to officer list synchronization...");
             projectRepository.saveProjects(projects); // Save the potentially modified list
        }


        System.out.println("Data synchronization complete.");
    }
}
