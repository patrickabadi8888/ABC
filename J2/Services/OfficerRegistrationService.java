package Services;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import Enums.OfficerRegistrationStatus;
import Interfaces.Repositories.IApplicationRepository;
import Interfaces.Repositories.IOfficerRegistrationRepository;
import Interfaces.Repositories.IProjectRepository;
import Interfaces.Services.IEligibilityService;
import Interfaces.Services.IOfficerRegistrationService;
import Models.HDBOfficer;
import Models.OfficerRegistration;
import Models.Project;
import Utils.DateUtils;

public class OfficerRegistrationService implements IOfficerRegistrationService {

    private final IOfficerRegistrationRepository registrationRepository;
    private final IProjectRepository projectRepository; // Needed for project access during approval
    private final IEligibilityService eligibilityService; // Needed for overlap checks

    // Constructor injection
    public OfficerRegistrationService(IOfficerRegistrationRepository registrationRepository,
                                      IProjectRepository projectRepository,
                                      IEligibilityService eligibilityService) {
        this.registrationRepository = registrationRepository;
        this.projectRepository = projectRepository;
        this.eligibilityService = eligibilityService;
    }

    @Override
    public boolean submitRegistration(HDBOfficer officer, Project project) {
        if (officer == null || project == null) return false;

        // Eligibility check should happen in the controller before calling this
        // Or could be re-checked here for safety

        OfficerRegistration newRegistration = new OfficerRegistration(officer.getNric(),
                project.getProjectName(), DateUtils.getCurrentDate());

        Map<String, OfficerRegistration> currentRegs = registrationRepository.getAllRegistrations();
        currentRegs.put(newRegistration.getRegistrationId(), newRegistration);
        registrationRepository.saveOfficerRegistrations(currentRegs);

        System.out.println("Registration request submitted for project '" + project.getProjectName()
                + "'. Status: PENDING approval by Manager.");
        return true;
    }

    @Override
    public boolean approveRegistration(OfficerRegistration registration, Project project) {
        if (registration == null || project == null || registration.getStatus() != OfficerRegistrationStatus.PENDING) {
            return false;
        }

        // Check for remaining slots
        if (project.getRemainingOfficerSlots() <= 0) {
            System.out.println("Cannot approve. No remaining officer slots for this project.");
            return false;
        }

        // Add officer to project's list *first*
        if (project.addApprovedOfficer(registration.getOfficerNric())) {
            // If successfully added to project, update registration status
            registration.setStatus(OfficerRegistrationStatus.APPROVED);

            // Save updated registration
            Map<String, OfficerRegistration> currentRegs = registrationRepository.getAllRegistrations();
            currentRegs.put(registration.getRegistrationId(), registration);
            registrationRepository.saveOfficerRegistrations(currentRegs);

            // Save updated project (with new officer in list)
            List<Project> allProjects = projectRepository.getAllProjects();
             for (int i = 0; i < allProjects.size(); i++) {
                 if (allProjects.get(i).getProjectName().equals(project.getProjectName())) {
                     allProjects.set(i, project); // Replace with the modified project object
                     break;
                 }
             }
            projectRepository.saveProjects(allProjects);


            System.out.println("Registration Approved. Officer " + registration.getOfficerNric() + " added to project.");
            return true;
        } else {
            // This might happen if the officer was somehow already in the list, or slots became zero concurrently
            System.err.println("Error: Failed to add officer " + registration.getOfficerNric() + " to project '" + project.getProjectName() + "' approved list (unexpected). Approval aborted.");
            return false;
        }
    }

    @Override
    public boolean rejectRegistration(OfficerRegistration registration) {
        if (registration == null || registration.getStatus() != OfficerRegistrationStatus.PENDING) {
            return false;
        }

        registration.setStatus(OfficerRegistrationStatus.REJECTED);

        Map<String, OfficerRegistration> currentRegs = registrationRepository.getAllRegistrations();
        currentRegs.put(registration.getRegistrationId(), registration);
        registrationRepository.saveOfficerRegistrations(currentRegs);

        System.out.println("Registration Rejected for officer " + registration.getOfficerNric() + " for project " + registration.getProjectName());
        return true;
    }

    @Override
    public List<OfficerRegistration> getRegistrationsByOfficer(String nric) {
        return registrationRepository.getAllRegistrations().values().stream()
                .filter(reg -> reg.getOfficerNric().equals(nric))
                .sorted(Comparator.comparing(OfficerRegistration::getRegistrationDate).reversed())
                .collect(Collectors.toList());
    }

    @Override
    public List<OfficerRegistration> getRegistrationsByProject(String projectName) {
        return registrationRepository.getAllRegistrations().values().stream()
                .filter(reg -> reg.getProjectName().equals(projectName))
                .sorted(Comparator.comparing(OfficerRegistration::getRegistrationDate))
                .collect(Collectors.toList());
    }

     @Override
     public List<OfficerRegistration> getPendingRegistrationsForProject(String projectName) {
          return registrationRepository.getAllRegistrations().values().stream()
                .filter(reg -> reg.getProjectName().equals(projectName) && reg.getStatus() == OfficerRegistrationStatus.PENDING)
                .sorted(Comparator.comparing(OfficerRegistration::getRegistrationDate))
                .collect(Collectors.toList());
     }

     @Override
     public void removeRegistrationsForProject(String projectName) {
         Map<String, OfficerRegistration> currentRegs = registrationRepository.getAllRegistrations();
         boolean changed = currentRegs.entrySet().removeIf(entry -> entry.getValue().getProjectName().equals(projectName));
         if (changed) {
             registrationRepository.saveOfficerRegistrations(currentRegs);
             System.out.println("Removed officer registrations associated with deleted project: " + projectName);
         }
     }
}
