package Services;

import java.util.Date;
import java.util.Objects;

import Enums.FlatType;
import Enums.MaritalStatus;
import Enums.OfficerRegistrationStatus;
import Enums.ApplicationStatus;
import Interfaces.Repositories.IOfficerRegistrationRepository;
import Interfaces.Repositories.IProjectRepository;
import Interfaces.Repositories.IUserRepository;
import Interfaces.Services.IEligibilityService;
import Models.Applicant;
import Models.HDBManager;
import Models.HDBOfficer;
import Models.OfficerRegistration;
import Models.Project;
import Models.User;
import Utils.DateUtils;

public class EligibilityService implements IEligibilityService {

    private final IUserRepository userRepository; // Needed for user details
    private final IOfficerRegistrationRepository officerRegistrationRepository;
    private final IProjectRepository projectRepository; // Needed to check project dates

    public EligibilityService(IUserRepository userRepository, IOfficerRegistrationRepository officerRegistrationRepository, IProjectRepository projectRepository) {
        this.userRepository = userRepository;
        this.officerRegistrationRepository = officerRegistrationRepository;
        this.projectRepository = projectRepository;
    }

    @Override
    public boolean canApplyForFlatType(User user, FlatType type) {
        if (user == null || type == null || user instanceof HDBManager) {
            return false; // Managers cannot apply
        }

        // Officers might be able to apply (handled by checks in controller/apply method)
        // This method checks basic age/marital status eligibility

        MaritalStatus maritalStatus = user.getMaritalStatus();
        int age = user.getAge();

        if (maritalStatus == MaritalStatus.SINGLE) {
            // Singles >= 35 can apply for 2-Room only
            return age >= 35 && type == FlatType.TWO_ROOM;
        } else if (maritalStatus == MaritalStatus.MARRIED) {
            // Married >= 21 can apply for 2-Room or 3-Room
            return age >= 21 && (type == FlatType.TWO_ROOM || type == FlatType.THREE_ROOM);
        }
        return false; // Should not happen if marital status is valid
    }

    @Override
    public boolean isProjectVisibleToUser(User user, Project project) {
        if (user == null || project == null) return false;

        // Managers see everything
        if (user instanceof HDBManager) return true;

        // Check explicit visibility flag
        if (project.isVisible()) return true;

        // Check if the user has an active/booked/pending-withdrawal application for this project
        if (user instanceof Applicant) {
            Applicant appUser = (Applicant) user;
            ApplicationStatus status = appUser.getApplicationStatus();
            if (project.getProjectName().equals(appUser.getAppliedProjectName()) &&
                status != null &&
                status != ApplicationStatus.UNSUCCESSFUL &&
                status != ApplicationStatus.WITHDRAWN)
            {
                return true;
            }
        }

        // Check if the user is an approved officer handling this project
        if (user instanceof HDBOfficer) {
            String regId = OfficerRegistration.generateId(user.getNric(), project.getProjectName());
            OfficerRegistration registration = officerRegistrationRepository.getAllRegistrations().get(regId);
            if (registration != null && registration.getStatus() == OfficerRegistrationStatus.APPROVED) {
                return true;
            }
        }

        // Otherwise, not visible
        return false;
    }

    @Override
    public boolean canOfficerRegisterForProject(HDBOfficer officer, Project project) {
        if (officer == null || project == null) return false;
        Date currentDate = DateUtils.getCurrentDate();

        // 1. Project must have slots and not be expired
        if (project.getRemainingOfficerSlots() <= 0 || project.isApplicationPeriodExpired(currentDate)) {
            return false;
        }

        // 2. Officer must not already have *any* registration (Pending/Approved/Rejected) for this project
        String regId = OfficerRegistration.generateId(officer.getNric(), project.getProjectName());
        if (officerRegistrationRepository.getAllRegistrations().containsKey(regId)) {
            return false;
        }

        // 3. Officer cannot have an active BTO application or pending withdrawal
        if (officer.hasActiveApplication() || officer.hasPendingWithdrawal()) {
            return false;
        }

        // 4. Project dates must not overlap with currently handled project (if any)
        Project currentlyHandling = getOfficerHandlingProject(officer);
        if (currentlyHandling != null && checkDateOverlap(project, currentlyHandling)) {
            return false;
        }

        // 5. Project dates must not overlap with other *pending* registrations
        boolean overlapsWithPending = officerRegistrationRepository.getAllRegistrations().values().stream()
            .filter(reg -> reg.getOfficerNric().equals(officer.getNric()) && reg.getStatus() == OfficerRegistrationStatus.PENDING)
            .map(reg -> projectRepository.findProjectByName(reg.getProjectName()))
            .filter(Objects::nonNull)
            .anyMatch(pendingProject -> checkDateOverlap(project, pendingProject));
        if (overlapsWithPending) {
            return false;
        }

        // 6. Officer cannot register for a project they have previously applied for (any status?)
        // Let's assume any application record prevents registration.
        boolean hasAppliedToProject = applicationRepository.getAllApplications().values().stream()
             .anyMatch(app -> app.getApplicantNric().equals(officer.getNric()) &&
                             app.getProjectName().equals(project.getProjectName()));
         if (hasAppliedToProject) {
             return false;
         }


        return true; // All checks passed
    }

     @Override
     public boolean isOfficerHandlingOverlappingProject(HDBOfficer officer, Project targetProject) {
         if (officer == null || targetProject == null) return false;

         return officerRegistrationRepository.getAllRegistrations().values().stream()
                 .filter(reg -> reg.getOfficerNric().equals(officer.getNric()) &&
                         reg.getStatus() == OfficerRegistrationStatus.APPROVED &&
                         !reg.getProjectName().equals(targetProject.getProjectName())) // Exclude target project itself
                 .map(reg -> projectRepository.findProjectByName(reg.getProjectName()))
                 .filter(Objects::nonNull) // Filter out registrations for non-existent projects
                 .anyMatch(otherProject -> checkDateOverlap(targetProject, otherProject));
     }

     @Override
     public Project getOfficerHandlingProject(HDBOfficer officer) {
         if (officer == null) return null;
         Date today = DateUtils.getCurrentDate();

         return officerRegistrationRepository.getAllRegistrations().values().stream()
                 .filter(reg -> reg.getOfficerNric().equals(officer.getNric())
                         && reg.getStatus() == OfficerRegistrationStatus.APPROVED)
                 .map(reg -> projectRepository.findProjectByName(reg.getProjectName()))
                 .filter(Objects::nonNull)
                 // Handling project must be currently active (not just approved registration)
                 .filter(p -> p.isApplicationPeriodActive(today))
                 .findFirst()
                 .orElse(null);
     }

     // Helper for date overlap check (could be in a Date utility if used more widely)
     private boolean checkDateOverlap(Project p1, Project p2) {
         if (p1 == null || p2 == null || p1.getApplicationOpeningDate() == null || p1.getApplicationClosingDate() == null
                 || p2.getApplicationOpeningDate() == null || p2.getApplicationClosingDate() == null) {
             return false; // Cannot overlap if dates are missing
         }
         // Overlap occurs if p1 starts before p2 ends AND p1 ends after p2 starts
         return !p1.getApplicationOpeningDate().after(p2.getApplicationClosingDate()) &&
                !p1.getApplicationClosingDate().before(p2.getApplicationOpeningDate());
     }
}
