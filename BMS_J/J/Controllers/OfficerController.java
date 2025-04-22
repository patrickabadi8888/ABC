package Controllers;

import java.util.stream.Collectors;
import java.util.List;
import java.util.Map;
import java.util.Comparator;
import java.util.Scanner;
import java.util.Date;
import java.util.Objects;
import java.util.Collections;

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
import Models.FlatTypeDetails;

import Services.DataService;


public class OfficerController extends ApplicantController {

    public OfficerController(Map<String, User> users, List<Project> projects, Map<String, BTOApplication> applications, List<Enquiry> enquiries, Map<String, OfficerRegistration> officerRegistrations, User currentUser, Scanner scanner, AuthController authController) {
        super(users, projects, applications, enquiries, officerRegistrations, currentUser, scanner, authController);
    }


    public void registerForProject() {
        HDBOfficer officer = (HDBOfficer) currentUser;
        Date currentDate = DataService.getCurrentDate();
        DataService.synchronizeData(users, projects, applications, officerRegistrations);

        if (officer.hasActiveApplication()) {
            System.out.println("Error: Cannot register to handle a project while you have an active BTO application (" + officer.getAppliedProjectName() + ", Status: " + officer.getApplicationStatus() + ").");
            return;
        }
        if (officer.hasPendingWithdrawal()) {
            System.out.println("Error: Cannot register to handle a project while you have a pending withdrawal request.");
            return;
        }


        System.out.println("\n--- Register to Handle Project ---");

         Project currentlyHandlingProject = getOfficerHandlingProject(officer);

        List<Project> pendingRegistrationProjects = officerRegistrations.values().stream()
            .filter(reg -> reg.getOfficerNric().equals(officer.getNric()) && reg.getStatus() == OfficerRegistrationStatus.PENDING)
            .map(reg -> findProjectByName(reg.getProjectName()))
            .filter(Objects::nonNull)
            .collect(Collectors.toList());


        List<Project> availableProjects = projects.stream()
                .filter(p -> p.getRemainingOfficerSlots() > 0)
                .filter(p -> !p.isApplicationPeriodExpired(currentDate))
                .filter(p -> officerRegistrations.values().stream()
                                .noneMatch(reg -> reg.getOfficerNric().equals(officer.getNric()) &&
                                                  reg.getProjectName().equals(p.getProjectName())))
                .filter(p -> currentlyHandlingProject == null || !checkDateOverlap(p, currentlyHandlingProject))
                .filter(p -> pendingRegistrationProjects.stream()
                                .noneMatch(pendingProject -> checkDateOverlap(p, pendingProject)))
                 .filter(p -> applications.values().stream()
                                .noneMatch(app -> app.getApplicantNric().equals(officer.getNric()) &&
                                                  app.getProjectName().equals(p.getProjectName())))
                .sorted(Comparator.comparing(Project::getProjectName))
                .collect(Collectors.toList());

        if (availableProjects.isEmpty()) {
            System.out.println("No projects currently available for you to register for based on eligibility criteria:");
            System.out.println("- Project must have open officer slots and not be expired.");
            System.out.println("- You must not already have a registration (Pending/Approved/Rejected) for the project.");
            System.out.println("- You cannot have an active BTO application (Pending/Successful) or Pending Withdrawal.");
            System.out.println("- You cannot register if the project's dates overlap with a project you are already handling or have a pending registration for.");
             System.out.println("- You cannot register for a project you have previously applied for.");
            return;
        }

        viewAndSelectProject(availableProjects, "Select Project to Register For");
        Project selectedProject = selectProjectFromList(availableProjects);

        if (selectedProject != null) {
            OfficerRegistration newRegistration = new OfficerRegistration(officer.getNric(), selectedProject.getProjectName(), currentDate);
            officerRegistrations.put(newRegistration.getRegistrationId(), newRegistration);
            System.out.println("Registration request submitted for project '" + selectedProject.getProjectName() + "'. Status: PENDING approval by Manager.");
            DataService.saveOfficerRegistrations(officerRegistrations);
        }
    }

    public void viewRegistrationStatus() {
        HDBOfficer officer = (HDBOfficer) currentUser;
        System.out.println("\n--- Your HDB Officer Registration Status ---");

        Project handlingProject = getOfficerHandlingProject(officer);
        if (handlingProject != null) {
             System.out.println("You are currently APPROVED and HANDLING project: " + handlingProject.getProjectName());
             System.out.println("----------------------------------------");
        }

        List<OfficerRegistration> myRegistrations = officerRegistrations.values().stream()
                .filter(reg -> reg.getOfficerNric().equals(officer.getNric()))
                .filter(reg -> handlingProject == null || !reg.getProjectName().equals(handlingProject.getProjectName()))
                .sorted(Comparator.comparing(OfficerRegistration::getRegistrationDate).reversed())
                .collect(Collectors.toList());

        if (myRegistrations.isEmpty() && handlingProject == null) {
            System.out.println("You have no past or pending registration requests.");
        } else if (!myRegistrations.isEmpty()) {
            System.out.println("Other Registration History/Requests:");
            for (OfficerRegistration reg : myRegistrations) {
                System.out.printf("- Project: %-15s | Status: %-10s | Date: %s\n",
                        reg.getProjectName(), reg.getStatus(), DataService.formatDate(reg.getRegistrationDate()));
            }
        }
    }

    public void viewHandlingProjectDetails() {
        HDBOfficer officer = (HDBOfficer) currentUser;
        Project project = getOfficerHandlingProject(officer);

        if (project == null) {
            System.out.println("You are not currently handling any project. Register for one first.");
            return;
        }

        System.out.println("\n--- Details for Handling Project: " + project.getProjectName() + " ---");
        viewAndSelectProject(Collections.singletonList(project), "Project Details");
    }

    public void viewAndReplyToEnquiries() {
         HDBOfficer officer = (HDBOfficer) currentUser;
         Project handlingProject = getOfficerHandlingProject(officer);

         if (handlingProject == null) {
             System.out.println("You need to be handling a project to view and reply to its enquiries.");
             return;
         }
         String handlingProjectName = handlingProject.getProjectName();

         System.out.println("\n--- Enquiries for Project: " + handlingProjectName + " ---");
         List<Enquiry> projectEnquiries = enquiries.stream()
                 .filter(e -> e.getProjectName().equalsIgnoreCase(handlingProjectName))
                 .sorted(Comparator.comparing(Enquiry::getEnquiryDate).reversed())
                 .collect(Collectors.toList());

         if (projectEnquiries.isEmpty()) {
             System.out.println("No enquiries found for this project.");
             return;
         }

         List<Enquiry> unrepliedEnquiries = projectEnquiries.stream()
                                                            .filter(e -> !e.isReplied())
                                                            .collect(Collectors.toList());

         System.out.println("--- Unreplied Enquiries ---");
         if (unrepliedEnquiries.isEmpty()) {
             System.out.println("(None)");
         } else {
             for (int i = 0; i < unrepliedEnquiries.size(); i++) {
                 Enquiry e = unrepliedEnquiries.get(i);
                 System.out.printf("%d. ID: %s | Applicant: %s | Date: %s\n",
                         i + 1, e.getEnquiryId(), e.getApplicantNric(), DataService.formatDate(e.getEnquiryDate()));
                 System.out.println("   Enquiry: " + e.getEnquiryText());
                 System.out.println("---");
             }
             System.out.print("Enter the number of the enquiry to reply to (or 0 to skip): ");
             try {
                 int choice = Integer.parseInt(scanner.nextLine());
                 if (choice >= 1 && choice <= unrepliedEnquiries.size()) {
                     Enquiry enquiryToReply = unrepliedEnquiries.get(choice - 1);
                     System.out.print("Enter your reply: ");
                     String replyText = scanner.nextLine().trim();
                     if (enquiryToReply.setReply(replyText, currentUser.getNric(), DataService.getCurrentDate())) {
                         System.out.println("Reply submitted successfully.");
                         DataService.saveEnquiries(enquiries);
                     }
                 } else if (choice != 0) {
                     System.out.println("Invalid choice.");
                 }
             } catch (NumberFormatException e) {
                 System.out.println("Invalid input.");
             }
         }

         System.out.println("\n--- Replied Enquiries ---");
         List<Enquiry> repliedEnquiries = projectEnquiries.stream()
                                                          .filter(Enquiry::isReplied)
                                                          .collect(Collectors.toList());
         if (repliedEnquiries.isEmpty()) {
             System.out.println("(None)");
         } else {
             for (Enquiry e : repliedEnquiries) {
                 System.out.printf("ID: %s | Applicant: %s | Enquiry Date: %s\n",
                         e.getEnquiryId(), e.getApplicantNric(), DataService.formatDate(e.getEnquiryDate()));
                 System.out.println("   Enquiry: " + e.getEnquiryText());
                 System.out.printf("   Reply (by %s on %s): %s\n",
                         e.getRepliedByNric(),
                         e.getReplyDate() != null ? DataService.formatDate(e.getReplyDate()) : "N/A",
                         e.getReplyText());
                 System.out.println("--------------------");
             }
         }
    }

    public void manageFlatBooking() {
        HDBOfficer officer = (HDBOfficer) currentUser;
        Project project = getOfficerHandlingProject(officer);

        if (project == null) {
            System.out.println("You need to be handling a project to manage flat bookings.");
            return;
        }
        String handlingProjectName = project.getProjectName();

        System.out.println("\n--- Flat Booking Management for Project: " + handlingProjectName + " ---");

        List<BTOApplication> successfulApps = applications.values().stream()
            .filter(app -> app.getProjectName().equals(handlingProjectName) && app.getStatus() == ApplicationStatus.SUCCESSFUL)
            .sorted(Comparator.comparing(BTOApplication::getApplicationDate))
            .collect(Collectors.toList());

        if (successfulApps.isEmpty()) {
            System.out.println("No applicants with status SUCCESSFUL found for this project.");
            return;
        }

        System.out.println("Applicants with SUCCESSFUL status (ready for booking):");
        for (int i = 0; i < successfulApps.size(); i++) {
             BTOApplication app = successfulApps.get(i);
             User applicantUser = users.get(app.getApplicantNric());
             System.out.printf("%d. NRIC: %s | Name: %-15s | Applied Type: %s | App Date: %s\n",
                     i + 1,
                     app.getApplicantNric(),
                     applicantUser != null ? applicantUser.getName() : "N/A",
                     app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A",
                     DataService.formatDate(app.getApplicationDate()));
        }

        System.out.print("Enter the number of the applicant to process booking for (or 0 to cancel): ");
        int choice;
         try {
             choice = Integer.parseInt(scanner.nextLine());
              if (choice == 0) {
                  System.out.println("Operation cancelled.");
                  return;
              }
             if (choice < 1 || choice > successfulApps.size()) {
                  System.out.println("Invalid choice number.");
                  return;
             }
         } catch (NumberFormatException e) {
             System.out.println("Invalid input. Please enter a number.");
             return;
         }

        BTOApplication applicationToBook = successfulApps.get(choice - 1);
        User applicantUser = users.get(applicationToBook.getApplicantNric());

        if (!(applicantUser instanceof Applicant)) {
            System.out.println("Error: Applicant data not found or invalid for NRIC " + applicationToBook.getApplicantNric());
            return;
        }
        Applicant applicant = (Applicant) applicantUser;

        if (applicationToBook.getStatus() != ApplicationStatus.SUCCESSFUL) {
            System.out.println("Error: Applicant status is no longer SUCCESSFUL (Current: " + applicationToBook.getStatus() + "). Cannot proceed.");
            return;
        }
         if (applicant.hasBooked()) {
             System.out.println("Error: Applicant " + applicant.getNric() + " has already booked a flat according to their profile.");
             return;
         }

        FlatType appliedFlatType = applicationToBook.getFlatTypeApplied();
        if (appliedFlatType == null) {
             System.out.println("Error: Application record does not have a valid flat type specified. Cannot book.");
             return;
        }

        FlatTypeDetails details = project.getMutableFlatTypeDetails(appliedFlatType);
        if (details == null || details.getAvailableUnits() <= 0) {
            System.out.println("Error: No available units for the applied flat type (" + appliedFlatType.getDisplayName() + ") at this moment. Booking cannot proceed.");
            return;
        }

        System.out.println("\n--- Confirm Booking ---");
        System.out.println("Applicant: " + applicant.getName() + " (" + applicant.getNric() + ")");
        System.out.println("Project: " + applicationToBook.getProjectName());
        System.out.println("Flat Type: " + appliedFlatType.getDisplayName());
        System.out.println("Available Units Before Booking: " + details.getAvailableUnits());
        System.out.printf("Selling Price: $%.2f\n", details.getSellingPrice());

        System.out.print("\nConfirm booking for this applicant? (yes/no): ");
        String confirm = scanner.nextLine().trim().toLowerCase();

        if (confirm.equals("yes")) {
            if (!details.decrementAvailableUnits()) {
                 System.out.println("Error: Failed to decrement unit count (possibly became zero just now). Booking cancelled.");
                 return;
            }

            applicationToBook.setStatus(ApplicationStatus.BOOKED);

            applicant.setApplicationStatus(ApplicationStatus.BOOKED);
            applicant.setBookedFlatType(appliedFlatType);

            System.out.println("Booking confirmed successfully!");
            System.out.println("Applicant status updated to BOOKED.");
            System.out.println("Remaining units for " + appliedFlatType.getDisplayName() + ": " + details.getAvailableUnits());

            generateBookingReceipt(applicant, applicationToBook, project);

            DataService.saveApplications(applications);
            DataService.saveProjects(projects);

        } else {
            System.out.println("Booking cancelled.");
        }
    }

    private void generateBookingReceipt(Applicant applicant, BTOApplication application, Project project) {
        System.out.println("\n================ BTO Booking Receipt ================");
        System.out.println(" Receipt Generated: " + DataService.formatDate(DataService.getCurrentDate()) + " by Officer " + currentUser.getNric());
        System.out.println("-----------------------------------------------------");
        System.out.println(" Applicant Details:");
        System.out.println("   Name:          " + applicant.getName());
        System.out.println("   NRIC:          " + applicant.getNric());
        System.out.println("   Age:           " + applicant.getAge());
        System.out.println("   Marital Status:" + applicant.getMaritalStatus());
        System.out.println("-----------------------------------------------------");
        System.out.println(" Booking Details:");
        System.out.println("   Project Name:  " + project.getProjectName());
        System.out.println("   Neighborhood:  " + project.getNeighborhood());
        System.out.println("   Booked Flat:   " + (application.getFlatTypeApplied() != null ? application.getFlatTypeApplied().getDisplayName() : "N/A"));
        FlatTypeDetails details = project.getFlatTypeDetails(application.getFlatTypeApplied());
        if (details != null) {
             System.out.printf("   Selling Price: $%.2f\n", details.getSellingPrice());
        } else {
             System.out.println("   Selling Price: N/A");
        }
        System.out.println("   Booking Status:" + application.getStatus());
        System.out.println("   Application ID:" + application.getApplicationId());
        System.out.println("-----------------------------------------------------");
        System.out.println(" Thank you for choosing HDB!");
        System.out.println("=====================================================");
    }
}
