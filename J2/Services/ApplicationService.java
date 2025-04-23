package Services;

import java.util.Map;
import java.util.Objects;

import Enums.ApplicationStatus;
import Enums.FlatType;
import Interfaces.Repositories.IApplicationRepository;
import Interfaces.Repositories.IProjectRepository;
import Interfaces.Repositories.IUserRepository;
import Interfaces.Services.IApplicationService;
import Models.Applicant;
import Models.BTOApplication;
import Models.FlatTypeDetails;
import Models.Project;
import Models.User;
import Utils.DateUtils;

public class ApplicationService implements IApplicationService {

    private final IApplicationRepository applicationRepository;
    private final IProjectRepository projectRepository;
    private final IUserRepository userRepository; // Needed to update Applicant status

    public ApplicationService(IApplicationRepository applicationRepository, IProjectRepository projectRepository, IUserRepository userRepository) {
        this.applicationRepository = applicationRepository;
        this.projectRepository = projectRepository;
        this.userRepository = userRepository;
    }

    @Override
    public BTOApplication findApplicationByApplicantAndProject(String nric, String projectName) {
        if (nric == null || projectName == null) return null;
        String appId = BTOApplication.generateId(nric, projectName); // Use static method for consistency
        return applicationRepository.getAllApplications().get(appId);
    }

    @Override
    public boolean submitApplication(Applicant applicant, Project project, FlatType flatType) {
        if (applicant == null || project == null || flatType == null) return false;

        // Create new application
        BTOApplication newApplication = new BTOApplication(applicant.getNric(), project.getProjectName(),
                flatType, DateUtils.getCurrentDate());

        // Update application repository
        Map<String, BTOApplication> currentApplications = applicationRepository.getAllApplications();
        currentApplications.put(newApplication.getApplicationId(), newApplication);
        applicationRepository.saveApplications(currentApplications);

        // Update applicant's state
        applicant.setAppliedProjectName(project.getProjectName());
        applicant.setApplicationStatus(ApplicationStatus.PENDING);
        applicant.setBookedFlatType(null);
        // No need to save users here, assume user state is transient or saved elsewhere (e.g. on password change)
        // If user state needs persistence beyond login session, userRepository.saveUsers() would be needed.

        System.out.println("Application submitted successfully for project '" + project.getProjectName() + "' ("
                + flatType.getDisplayName() + "). Status: PENDING.");
        return true;
    }

    @Override
    public boolean requestWithdrawal(Applicant applicant) {
        if (applicant == null || applicant.getAppliedProjectName() == null) return false;

        BTOApplication application = findApplicationByApplicantAndProject(applicant.getNric(), applicant.getAppliedProjectName());
        if (application == null) {
            System.out.println("Error: Could not find the application record to request withdrawal.");
            return false;
        }

        ApplicationStatus currentStatus = application.getStatus();
        if (currentStatus != ApplicationStatus.PENDING &&
            currentStatus != ApplicationStatus.SUCCESSFUL &&
            currentStatus != ApplicationStatus.BOOKED) {
            System.out.println("Application status (" + currentStatus + ") is not eligible for withdrawal request.");
            return false;
        }

        // Update application status
        application.setStatus(ApplicationStatus.PENDING_WITHDRAWAL); // This also sets statusBeforeWithdrawal internally
        Map<String, BTOApplication> currentApplications = applicationRepository.getAllApplications();
        currentApplications.put(application.getApplicationId(), application); // Update map
        applicationRepository.saveApplications(currentApplications);

        // Update applicant's transient state
        applicant.setApplicationStatus(ApplicationStatus.PENDING_WITHDRAWAL);

        System.out.println("Withdrawal request submitted successfully. Status: PENDING_WITHDRAWAL.");
        return true;
    }

    @Override
    public boolean approveWithdrawal(BTOApplication application) {
        if (application == null || application.getStatus() != ApplicationStatus.PENDING_WITHDRAWAL) return false;

        Applicant applicant = findApplicant(application.getApplicantNric());
        if (applicant == null) return false; // Should not happen if data is consistent

        Project project = projectRepository.findProjectByName(application.getProjectName());
        // Allow withdrawal even if project is deleted? Current logic requires project for unit release.
        if (project == null) {
             System.err.println("Error: Project data not found for application "
                            + application.getApplicationId() + ". Cannot process withdrawal properly (unit release might fail).");
             // Decide whether to proceed or fail. Let's proceed but warn.
        }


        ApplicationStatus originalStatus = application.getStatusBeforeWithdrawal();
        // If original status wasn't stored (e.g., loaded from old CSV), infer it
        if (originalStatus == null) {
            originalStatus = inferStatusBeforeWithdrawal(application, applicant);
            System.out.println("Info: Inferred original status as " + originalStatus + " for withdrawal approval.");
        }

        ApplicationStatus finalStatus;
        boolean releasedUnit = false;

        if (originalStatus == ApplicationStatus.BOOKED) {
            finalStatus = ApplicationStatus.UNSUCCESSFUL; // Or maybe WITHDRAWN_PENALTY? Keep as UNSUCCESSFUL for now.
            FlatType bookedType = application.getFlatTypeApplied();
            if (bookedType != null && project != null) { // Check project exists for unit release
                FlatTypeDetails details = project.getMutableFlatTypeDetails(bookedType);
                if (details != null) {
                    if (details.incrementAvailableUnits()) {
                        releasedUnit = true;
                        System.out.println("Unit for " + bookedType.getDisplayName()
                                + " released back to project " + project.getProjectName());
                    } else {
                        System.err.println("Error: Could not increment available units for " + bookedType
                                + " during withdrawal approval (already at max?).");
                    }
                } else {
                    System.err.println("Error: Could not find flat details for " + bookedType
                            + " during withdrawal approval.");
                }
            } else if (bookedType == null) {
                System.err.println("Error: Cannot determine booked flat type to release unit during withdrawal approval.");
            }
        } else if (originalStatus == ApplicationStatus.SUCCESSFUL) {
            finalStatus = ApplicationStatus.UNSUCCESSFUL;
        } else { // Original was likely PENDING
            finalStatus = ApplicationStatus.WITHDRAWN;
        }

        // Update application
        application.setStatus(finalStatus); // This clears statusBeforeWithdrawal
        Map<String, BTOApplication> currentApplications = applicationRepository.getAllApplications();
        currentApplications.put(application.getApplicationId(), application);
        applicationRepository.saveApplications(currentApplications);

        // Update applicant state
        applicant.setApplicationStatus(finalStatus);
        applicant.setBookedFlatType(null); // Ensure booked type is cleared

        System.out.println("Withdrawal request Approved. Application status set to " + finalStatus + ".");

        // Save project if unit was released
        if (releasedUnit && project != null) {
            // Need to get the full list, update the specific project, and save the list
            List<Project> allProjects = projectRepository.getAllProjects();
            // Find the project in the list and update it (or replace it)
            for (int i = 0; i < allProjects.size(); i++) {
                if (allProjects.get(i).getProjectName().equals(project.getProjectName())) {
                    allProjects.set(i, project); // Replace with the modified project object
                    break;
                }
            }
            projectRepository.saveProjects(allProjects);
        }

        return true;
    }

    @Override
    public boolean rejectWithdrawal(BTOApplication application) {
        if (application == null || application.getStatus() != ApplicationStatus.PENDING_WITHDRAWAL) return false;

        Applicant applicant = findApplicant(application.getApplicantNric());
        if (applicant == null) return false;

        ApplicationStatus originalStatus = application.getStatusBeforeWithdrawal();
        if (originalStatus == null) {
             originalStatus = inferStatusBeforeWithdrawal(application, applicant);
             System.out.println("Info: Inferred original status as " + originalStatus + " for withdrawal rejection.");
        }

        // Revert application status
        application.setStatus(originalStatus); // This clears statusBeforeWithdrawal
        Map<String, BTOApplication> currentApplications = applicationRepository.getAllApplications();
        currentApplications.put(application.getApplicationId(), application);
        applicationRepository.saveApplications(currentApplications);

        // Revert applicant state
        applicant.setApplicationStatus(originalStatus);
        // Re-set booked flat type if original status was BOOKED
        if (originalStatus == ApplicationStatus.BOOKED) {
            applicant.setBookedFlatType(application.getFlatTypeApplied());
        }

        System.out.println("Withdrawal request Rejected. Application status reverted to " + originalStatus + ".");
        return true;
    }

    @Override
    public boolean approveApplication(BTOApplication application) {
         if (application == null || application.getStatus() != ApplicationStatus.PENDING) return false;

         Applicant applicant = findApplicant(application.getApplicantNric());
         if (applicant == null) return false;

         Project project = projectRepository.findProjectByName(application.getProjectName());
         if (project == null) {
             System.err.println("Error: Project not found for application " + application.getApplicationId());
             return false;
         }

         FlatType appliedType = application.getFlatTypeApplied();
         if (appliedType == null) {
             System.out.println("Error: Application has no specified flat type. Cannot approve.");
             return false;
         }
         FlatTypeDetails details = project.getFlatTypeDetails(appliedType);
         if (details == null) {
             System.out.println("Error: Applied flat type (" + appliedType.getDisplayName()
                     + ") does not exist in this project. Rejecting application.");
             // Automatically reject if flat type doesn't exist in project
             return rejectApplication(application);
         }

         // Check against total units, not available units here. Booking handles availability.
         long alreadySuccessfulOrBookedCount = applicationRepository.getAllApplications().values().stream()
                 .filter(a -> a.getProjectName().equals(project.getProjectName()) &&
                         a.getFlatTypeApplied() == appliedType &&
                         (a.getStatus() == ApplicationStatus.SUCCESSFUL || a.getStatus() == ApplicationStatus.BOOKED))
                 .count();

         if (alreadySuccessfulOrBookedCount < details.getTotalUnits()) {
             application.setStatus(ApplicationStatus.SUCCESSFUL);
             Map<String, BTOApplication> currentApplications = applicationRepository.getAllApplications();
             currentApplications.put(application.getApplicationId(), application);
             applicationRepository.saveApplications(currentApplications);

             applicant.setApplicationStatus(ApplicationStatus.SUCCESSFUL);

             System.out.println("Application Approved (Status: SUCCESSFUL). Applicant can now book via Officer.");
             return true;
         } else {
             System.out.println("Cannot approve. The number of successful/booked applications already meets or exceeds the total supply ("
                             + details.getTotalUnits() + ") for " + appliedType.getDisplayName() + ".");
             // Should we auto-reject here? Or just prevent approval? Let's just prevent approval.
             return false;
         }
    }

    @Override
    public boolean rejectApplication(BTOApplication application) {
        if (application == null || application.getStatus() != ApplicationStatus.PENDING) return false;

        Applicant applicant = findApplicant(application.getApplicantNric());
        if (applicant == null) return false;

        application.setStatus(ApplicationStatus.UNSUCCESSFUL);
        Map<String, BTOApplication> currentApplications = applicationRepository.getAllApplications();
        currentApplications.put(application.getApplicationId(), application);
        applicationRepository.saveApplications(currentApplications);

        applicant.setApplicationStatus(ApplicationStatus.UNSUCCESSFUL);
        applicant.setBookedFlatType(null); // Ensure booked type is cleared

        System.out.println("Application Rejected (Status: UNSUCCESSFUL).");
        return true;
    }

     @Override
     public boolean bookFlat(BTOApplication application, Applicant applicant, Project project) {
         if (application == null || applicant == null || project == null ||
             application.getStatus() != ApplicationStatus.SUCCESSFUL ||
             applicant.hasBooked()) {
             System.err.println("Error: Pre-conditions for booking not met (App Status: " + application.getStatus() + ", Applicant Booked: " + applicant.hasBooked() + ")");
             return false;
         }

         FlatType appliedFlatType = application.getFlatTypeApplied();
         if (appliedFlatType == null) {
             System.err.println("Error: Application record does not have a valid flat type specified. Cannot book.");
             return false;
         }

         // Get mutable details directly from the project object passed in
         FlatTypeDetails details = project.getMutableFlatTypeDetails(appliedFlatType);
         if (details == null || details.getAvailableUnits() <= 0) {
             System.err.println("Error: No available units for the applied flat type ("
                     + appliedFlatType.getDisplayName() + ") at this moment. Booking cannot proceed.");
             return false;
         }

         // Decrement units
         if (!details.decrementAvailableUnits()) {
             System.err.println("Error: Failed to decrement unit count (possibly became zero concurrently?). Booking cancelled.");
             // No state change occurred yet, just return false
             return false;
         }

         // Update application status
         application.setStatus(ApplicationStatus.BOOKED);
         Map<String, BTOApplication> currentApplications = applicationRepository.getAllApplications();
         currentApplications.put(application.getApplicationId(), application);
         applicationRepository.saveApplications(currentApplications);

         // Update applicant state
         applicant.setApplicationStatus(ApplicationStatus.BOOKED);
         applicant.setBookedFlatType(appliedFlatType);

         // Save the project with updated unit count
         List<Project> allProjects = projectRepository.getAllProjects();
         for (int i = 0; i < allProjects.size(); i++) {
             if (allProjects.get(i).getProjectName().equals(project.getProjectName())) {
                 allProjects.set(i, project); // Replace with the modified project object
                 break;
             }
         }
         projectRepository.saveProjects(allProjects);

         System.out.println("Booking confirmed successfully!");
         System.out.println("Applicant status updated to BOOKED.");
         System.out.println("Remaining units for " + appliedFlatType.getDisplayName() + ": " + details.getAvailableUnits());

         // Receipt generation can be triggered by the controller after this returns true
         return true;
     }

    @Override
    public void synchronizeApplicantStatus(Applicant applicant) {
        // Find the most relevant application for this applicant
        BTOApplication relevantApp = applicationRepository.getAllApplications().values().stream()
                .filter(app -> app.getApplicantNric().equals(applicant.getNric()))
                .max(Comparator.comparing((BTOApplication application) -> application.getStatus(),
                        Comparator.comparingInt(ApplicationStatus::getPriority).reversed()) // Use priority enum method
                        .thenComparing(BTOApplication::getApplicationDate).reversed())
                .orElse(null);

        if (relevantApp != null) {
            applicant.setAppliedProjectName(relevantApp.getProjectName());
            applicant.setApplicationStatus(relevantApp.getStatus());
            if (relevantApp.getStatus() == ApplicationStatus.BOOKED) {
                applicant.setBookedFlatType(relevantApp.getFlatTypeApplied());
            } else {
                applicant.setBookedFlatType(null);
            }
        } else {
            applicant.clearApplicationState();
        }
    }

     @Override
     public void adjustUnitsOnLoad() {
         Map<Project, Map<FlatType, Integer>> bookedCounts = new HashMap<>();
         List<Project> projects = projectRepository.getAllProjects(); // Get current projects

         // Count booked applications for existing projects
         applicationRepository.getAllApplications().values().stream()
             .filter(app -> app.getStatus() == ApplicationStatus.BOOKED && app.getFlatTypeApplied() != null)
             .forEach(app -> {
                 Project project = projects.stream() // Find project in the current list
                     .filter(p -> p.getProjectName().equalsIgnoreCase(app.getProjectName()))
                     .findFirst().orElse(null);
                 if (project != null) {
                     bookedCounts.computeIfAbsent(project, k -> new HashMap<>())
                                 .merge(app.getFlatTypeApplied(), 1, Integer::sum);
                 } else {
                      System.err.println("Warning (Unit Sync): Booked application " + app.getApplicationId() + " refers to non-existent project '"
                                + app.getProjectName() + "'. Unit count cannot be adjusted.");
                 }
             });

         // Adjust available units in the project objects
         final boolean[] projectModified = {false}; // Use array to modify in lambda
         bookedCounts.forEach((project, typeCounts) -> {
             typeCounts.forEach((type, count) -> {
                 FlatTypeDetails details = project.getMutableFlatTypeDetails(type);
                 if (details != null) {
                     int initialAvailable = details.getTotalUnits(); // Start from total
                     int finalAvailable = Math.max(0, initialAvailable - count);
                     if (finalAvailable != details.getAvailableUnits()) {
                         details.setAvailableUnits(finalAvailable); // Use the setter for validation
                         projectModified[0] = true;
                         System.out.println("Info (Unit Sync): Adjusted available units for " + project.getProjectName() + "/" + type.getDisplayName() + " to " + finalAvailable);
                     }
                     if (count > details.getTotalUnits()) {
                         System.err.println("Error (Unit Sync): More flats booked (" + count + ") than total units ("
                                 + details.getTotalUnits() + ") for " + project.getProjectName() + "/"
                                 + type.getDisplayName() + ". Available units set to 0.");
                     }
                 } else {
                     System.err.println("Warning (Unit Sync): Trying to adjust units for non-existent flat type "
                             + type.getDisplayName() + " in project " + project.getProjectName());
                 }
             });
         });

         // Persist projects ONLY if any were modified
         if (projectModified[0]) {
              System.out.println("Info (Unit Sync): Saving projects due to available unit adjustments.");
              projectRepository.saveProjects(projects);
         }
     }

     @Override
     public void removeApplicationsForProject(String projectName) {
         Map<String, BTOApplication> currentApps = applicationRepository.getAllApplications();
         boolean changed = currentApps.entrySet().removeIf(entry -> entry.getValue().getProjectName().equals(projectName));
         if (changed) {
             applicationRepository.saveApplications(currentApps);
             System.out.println("Removed applications associated with deleted project: " + projectName);
         }
     }


    // Helper to find applicant (avoids saving users just for status updates)
    private Applicant findApplicant(String nric) {
        User user = userRepository.findUserByNric(nric);
        if (user instanceof Applicant) {
            return (Applicant) user;
        }
        System.err.println("Error: Could not find valid Applicant record for NRIC: " + nric);
        return null;
    }

     // Helper to infer status before withdrawal if not explicitly stored
     private ApplicationStatus inferStatusBeforeWithdrawal(BTOApplication app, Applicant applicant) {
         // Check if applicant object reflects booked status (might be slightly out of sync, but best guess)
         if (applicant != null && applicant.hasBooked() && Objects.equals(app.getFlatTypeApplied(), applicant.getBookedFlatType())) {
             return ApplicationStatus.BOOKED;
         }
         // If flat type exists, assume it was at least successful (or pending if flat type is null?)
         // This is ambiguous. Let's prioritize BOOKED if applicant state suggests it, otherwise SUCCESSFUL if flat type exists.
         if (app.getFlatTypeApplied() != null) {
             return ApplicationStatus.SUCCESSFUL;
         }
         // Default fallback
         return ApplicationStatus.PENDING;
     }
}
