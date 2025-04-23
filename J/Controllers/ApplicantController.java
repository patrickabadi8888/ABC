package Controllers;

import java.util.stream.Collectors;
import java.util.List;
import java.util.Map;
import java.util.Comparator;
import java.util.Scanner;

import Enums.FlatType;
import Enums.OfficerRegistrationStatus;
import Enums.ApplicationStatus;

import Models.Project;
import Models.BTOApplication;
import Models.Enquiry;
import Models.OfficerRegistration;
import Models.User;
import Models.Applicant;
import Models.HDBOfficer;
import Services.ApplicationService;
import Services.DataService;
import Services.EnquiryService;
import Utils.DateUtils;

public class ApplicantController extends BaseController {

    public ApplicantController(Map<String, User> users, List<Project> projects, Map<String, BTOApplication> applications, List<Enquiry> enquiries, Map<String, OfficerRegistration> officerRegistrations, User currentUser, Scanner scanner, AuthController authController) {
        super(users, projects, applications, enquiries, officerRegistrations, currentUser, scanner, authController);
    }


    public void viewOpenProjects() {
        System.out.println("\n--- Viewing Available BTO Projects ---");
        List<Project> availableProjects = getFilteredProjects(true, true, true, true, true);
        viewAndSelectProject(availableProjects, "Available BTO Projects");
    }

    public void applyForProject() {
        Applicant applicant = (Applicant) currentUser;

        if (applicant.hasBooked()) {
             System.out.println("You have already booked a flat for project '" + applicant.getAppliedProjectName() + "'. You cannot apply again.");
             return;
         }
        if (applicant.hasActiveApplication()) {
            System.out.println("You have an active application for project '" + applicant.getAppliedProjectName() + "' with status: " + applicant.getApplicationStatus());
            System.out.println("You must withdraw (and have it approved) or be unsuccessful before applying again.");
            return;
        }
        if (applicant.hasPendingWithdrawal()) {
            System.out.println("You have a withdrawal request pending manager approval for project '" + applicant.getAppliedProjectName() + "'.");
            System.out.println("You cannot apply for a new project until the withdrawal is processed.");
            return;
        }


        System.out.println("\n--- Apply for BTO Project ---");
        List<Project> eligibleProjects = getFilteredProjects(true, true, true, true, true);

        if (eligibleProjects.isEmpty()) {
            System.out.println("There are currently no open projects you are eligible to apply for based on filters, eligibility, and unit availability.");
            return;
        }

        viewAndSelectProject(eligibleProjects, "Select Project to Apply For");
        Project selectedProject = selectProjectFromList(eligibleProjects);
        if (selectedProject == null) return;

         if (currentUser instanceof HDBOfficer) {
             HDBOfficer officer = (HDBOfficer) currentUser;
             Project handlingProject = getOfficerHandlingProject(officer);
             if (handlingProject != null && selectedProject.equals(handlingProject)) {
                 System.out.println("Error: You cannot apply for a project you are currently handling as an Officer.");
                 return;
             }
             boolean hasPendingRegistration = officerRegistrations.values().stream()
                 .anyMatch(reg -> reg.getOfficerNric().equals(officer.getNric()) &&
                                reg.getProjectName().equals(selectedProject.getProjectName()) &&
                                reg.getStatus() == OfficerRegistrationStatus.PENDING);
             if (hasPendingRegistration) {
                  System.out.println("Error: You cannot apply for a project you have a pending registration for.");
                  return;
             }
         }

        FlatType selectedFlatType = selectEligibleFlatType(selectedProject);
        if (selectedFlatType == null) return;

        BTOApplication newApplication = new BTOApplication(currentUser.getNric(), selectedProject.getProjectName(), selectedFlatType, DateUtils.getCurrentDate());
        applications.put(newApplication.getApplicationId(), newApplication);

        applicant.setAppliedProjectName(selectedProject.getProjectName());
        applicant.setApplicationStatus(ApplicationStatus.PENDING);
        applicant.setBookedFlatType(null);

        System.out.println("Application submitted successfully for project '" + selectedProject.getProjectName() + "' (" + selectedFlatType.getDisplayName() + "). Status: PENDING.");

        ApplicationService.saveApplications(applications);
    }

    private FlatType selectEligibleFlatType(Project project) {
        List<FlatType> eligibleAndAvailableTypes = project.getFlatTypes().entrySet().stream()
            .filter(entry -> canApplyForFlatType(entry.getKey()) && entry.getValue().getAvailableUnits() > 0)
            .map(Map.Entry::getKey)
            .sorted()
            .collect(Collectors.toList());

        if (eligibleAndAvailableTypes.isEmpty()) {
             System.out.println("There are no flat types available in this project that you are eligible for.");
             return null;
        }

        if (eligibleAndAvailableTypes.size() == 1) {
            FlatType onlyOption = eligibleAndAvailableTypes.get(0);
            System.out.println("You will be applying for the only eligible and available type: " + onlyOption.getDisplayName() + ".");
            return onlyOption;
        } else {
            System.out.println("Select the flat type you want to apply for:");
            for (int i = 0; i < eligibleAndAvailableTypes.size(); i++) {
                System.out.println((i + 1) + ". " + eligibleAndAvailableTypes.get(i).getDisplayName());
            }
            System.out.print("Enter choice (or 0 to cancel): ");
            try {
                int typeChoice = Integer.parseInt(scanner.nextLine());
                 if (typeChoice == 0) {
                     System.out.println("Application cancelled.");
                     return null;
                 }
                if (typeChoice >= 1 && typeChoice <= eligibleAndAvailableTypes.size()) {
                    return eligibleAndAvailableTypes.get(typeChoice - 1);
                } else {
                    System.out.println("Invalid choice.");
                    return null;
                }
            } catch (NumberFormatException e) {
                System.out.println("Invalid input.");
                return null;
            }
        }
    }


    public void viewMyApplication() {
        Applicant applicant = (Applicant) currentUser;
        DataService.synchronizeData(users, projects, applications, officerRegistrations);

        String projectName = applicant.getAppliedProjectName();
        ApplicationStatus status = applicant.getApplicationStatus();

        if (projectName == null || status == null) {
            System.out.println("You do not have any current or past BTO application records.");
            return;
        }

        BTOApplication application = findApplicationByApplicantAndProject(applicant.getNric(), projectName);
        if (application == null) {
             System.out.println("Error: Your profile indicates an application, but the detailed record could not be found. Please contact support.");
             return;
        }


        Project project = findProjectByName(projectName);

        System.out.println("\n--- Your BTO Application ---");
        System.out.println("Project Name: " + projectName);
        if (project != null) {
            System.out.println("Neighborhood: " + project.getNeighborhood());
        } else {
            System.out.println("Neighborhood: (Project details not found)");
        }
        System.out.println("Flat Type Applied For: " + (application.getFlatTypeApplied() != null ? application.getFlatTypeApplied().getDisplayName() : "N/A"));
        System.out.println("Application Status: " + status);
         if (status == ApplicationStatus.BOOKED && applicant.getBookedFlatType() != null) {
             System.out.println("Booked Flat Type: " + applicant.getBookedFlatType().getDisplayName());
         }
         System.out.println("Application Date: " + DateUtils.formatDate(application.getApplicationDate()));
    }

    public void requestWithdrawal() {
        Applicant applicant = (Applicant) currentUser;
        DataService.synchronizeData(users, projects, applications, officerRegistrations);

        String currentProject = applicant.getAppliedProjectName();
        ApplicationStatus currentStatus = applicant.getApplicationStatus();

        if (currentProject == null || currentStatus == null) {
             System.out.println("You do not have an application to withdraw.");
             return;
        }

        if (currentStatus != ApplicationStatus.PENDING &&
            currentStatus != ApplicationStatus.SUCCESSFUL &&
            currentStatus != ApplicationStatus.BOOKED) {
            System.out.println("Your application status (" + currentStatus + ") is not eligible for withdrawal request.");
            System.out.println("You can only request withdrawal if your status is PENDING, SUCCESSFUL, or BOOKED.");
            return;
        }

        BTOApplication application = findApplicationByApplicantAndProject(applicant.getNric(), currentProject);
        if (application == null) {
             System.out.println("Error: Could not find the application record to request withdrawal. Please contact support.");
             return;
        }

        System.out.println("\n--- Request Application Withdrawal ---");
        System.out.println("Project: " + application.getProjectName());
        System.out.println("Current Status: " + currentStatus);
        System.out.print("Are you sure you want to request withdrawal for this application? Manager approval is required. (yes/no): ");
        String confirm = scanner.nextLine().trim().toLowerCase();

        if (confirm.equals("yes")) {
            application.setStatus(ApplicationStatus.PENDING_WITHDRAWAL);

            applicant.setApplicationStatus(ApplicationStatus.PENDING_WITHDRAWAL);

            System.out.println("Withdrawal request submitted successfully.");
            System.out.println("Your application status is now PENDING_WITHDRAWAL and requires Manager approval.");

            ApplicationService.saveApplications(applications);

        } else {
            System.out.println("Withdrawal request cancelled.");
        }
    }


    public void submitEnquiry() {
        System.out.println("\n--- Submit Enquiry ---");
        List<Project> viewableProjects = getFilteredProjects(true, false, false, false, false);
        Project selectedProject = null;

        if (!viewableProjects.isEmpty()) {
            viewAndSelectProject(viewableProjects, "Select Project to Enquire About (Optional)");
            selectedProject = selectProjectFromList(viewableProjects);
        }

        String projectNameInput;
        if (selectedProject != null) {
            projectNameInput = selectedProject.getProjectName();
            System.out.println("Enquiring about: " + projectNameInput);
        } else {
             if (!viewableProjects.isEmpty()) System.out.println("No project selected from list.");
             System.out.print("Enter the exact Project Name you want to enquire about: ");
             projectNameInput = scanner.nextLine().trim();
             if (findProjectByName(projectNameInput) == null) {
                 System.out.println("Warning: Project '" + projectNameInput + "' not found in current listings, but submitting enquiry anyway.");
             }
             if (projectNameInput.isEmpty()) {
                  System.out.println("Project name cannot be empty. Enquiry cancelled.");
                  return;
             }
        }


        System.out.print("Enter your enquiry text (cannot be empty): ");
        String text = scanner.nextLine().trim();

        if (!text.isEmpty()) {
            Enquiry newEnquiry = new Enquiry(currentUser.getNric(), projectNameInput, text, DateUtils.getCurrentDate());
            enquiries.add(newEnquiry);
            System.out.println("Enquiry submitted successfully (ID: " + newEnquiry.getEnquiryId() + ").");
            EnquiryService.saveEnquiries(enquiries);
        } else {
            System.out.println("Enquiry text cannot be empty. Enquiry not submitted.");
        }
    }

    public void viewMyEnquiries() {
        System.out.println("\n--- Your Enquiries ---");
        List<Enquiry> myEnquiries = enquiries.stream()
                                            .filter(e -> e.getApplicantNric().equals(currentUser.getNric()))
                                            .sorted(Comparator.comparing(Enquiry::getEnquiryDate).reversed())
                                            .collect(Collectors.toList());

        if (myEnquiries.isEmpty()) {
            System.out.println("You have not submitted any enquiries.");
            return;
        }

        for (int i = 0; i < myEnquiries.size(); i++) {
            Enquiry e = myEnquiries.get(i);
            System.out.printf("%d. ID: %s | Project: %s | Date: %s\n",
                    i + 1, e.getEnquiryId(), e.getProjectName(), DateUtils.formatDate(e.getEnquiryDate()));
            System.out.println("   Enquiry: " + e.getEnquiryText());
            if (e.isReplied()) {
                System.out.printf("   Reply (by %s on %s): %s\n",
                        e.getRepliedByNric() != null ? e.getRepliedByNric() : "N/A",
                        e.getReplyDate() != null ? DateUtils.formatDate(e.getReplyDate()) : "N/A",
                        e.getReplyText());
            } else {
                System.out.println("   Reply: (Pending)");
            }
             System.out.println("----------------------------------------");
        }
    }

    public void editMyEnquiry() {
        System.out.println("\n--- Edit Enquiry ---");
        List<Enquiry> editableEnquiries = enquiries.stream()
                                                .filter(e -> e.getApplicantNric().equals(currentUser.getNric()) && !e.isReplied())
                                                .sorted(Comparator.comparing(Enquiry::getEnquiryDate).reversed())
                                                .collect(Collectors.toList());

        if (editableEnquiries.isEmpty()) {
            System.out.println("You have no enquiries that can be edited (must not be replied to yet).");
            return;
        }

        System.out.println("Select enquiry to edit:");
         for (int i = 0; i < editableEnquiries.size(); i++) {
            Enquiry e = editableEnquiries.get(i);
            System.out.printf("%d. ID: %s | Project: %s | Text: %s\n",
                    i + 1, e.getEnquiryId(), e.getProjectName(), e.getEnquiryText());
        }
         System.out.print("Enter choice (or 0 to cancel): ");
         try {
             int choice = Integer.parseInt(scanner.nextLine());
              if (choice == 0) {
                  System.out.println("Operation cancelled.");
                  return;
              }
             if (choice >= 1 && choice <= editableEnquiries.size()) {
                 Enquiry enquiryToEdit = editableEnquiries.get(choice - 1);
                 System.out.print("Enter new enquiry text: ");
                 String newText = scanner.nextLine().trim();
                 if (enquiryToEdit.setEnquiryText(newText)) {
                     System.out.println("Enquiry updated successfully.");
                     EnquiryService.saveEnquiries(enquiries);
                 }
             } else {
                 System.out.println("Invalid choice.");
             }
         } catch (NumberFormatException e) {
             System.out.println("Invalid input.");
         }
    }

    public void deleteMyEnquiry() {
         System.out.println("\n--- Delete Enquiry ---");
        List<Enquiry> deletableEnquiries = enquiries.stream()
                                                .filter(e -> e.getApplicantNric().equals(currentUser.getNric()) && !e.isReplied())
                                                .sorted(Comparator.comparing(Enquiry::getEnquiryDate).reversed())
                                                .collect(Collectors.toList());

        if (deletableEnquiries.isEmpty()) {
            System.out.println("You have no enquiries that can be deleted (must not be replied to yet).");
            return;
        }

        System.out.println("Select enquiry to delete:");
         for (int i = 0; i < deletableEnquiries.size(); i++) {
            Enquiry e = deletableEnquiries.get(i);
            System.out.printf("%d. ID: %s | Project: %s | Text: %s\n",
                    i + 1, e.getEnquiryId(), e.getProjectName(), e.getEnquiryText());
        }
         System.out.print("Enter choice (or 0 to cancel): ");
         try {
             int choice = Integer.parseInt(scanner.nextLine());
              if (choice == 0) {
                  System.out.println("Operation cancelled.");
                  return;
              }
             if (choice >= 1 && choice <= deletableEnquiries.size()) {
                 Enquiry enquiryToDelete = deletableEnquiries.get(choice - 1);
                 System.out.print("Are you sure you want to delete enquiry " + enquiryToDelete.getEnquiryId() + "? (yes/no): ");
                 String confirm = scanner.nextLine().trim().toLowerCase();
                 if (confirm.equals("yes")) {
                     if (enquiries.remove(enquiryToDelete)) {
                         System.out.println("Enquiry deleted successfully.");
                         EnquiryService.saveEnquiries(enquiries);
                     } else {
                          System.err.println("Error: Failed to remove enquiry from list.");
                     }
                 } else {
                     System.out.println("Deletion cancelled.");
                 }
             } else {
                 System.out.println("Invalid choice.");
             }
         } catch (NumberFormatException e) {
             System.out.println("Invalid input.");
         }
    }
}

