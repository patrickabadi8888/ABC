package Controllers;

import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Scanner;
import java.util.stream.Collectors;

import Enums.ApplicationStatus;
import Enums.FlatType;
import Interfaces.Services.*;
import Models.*;
import Utils.DateUtils;
import Utils.InputUtils;

import Interfaces.Repositories.IUserRepository;
public class OfficerController extends ApplicantController {
    IUserRepository userRepository;

    public OfficerController(Scanner scanner, User currentUser, IAuthService authService,
                             IProjectService projectService, IApplicationService applicationService,
                             IEnquiryService enquiryService, IEligibilityService eligibilityService,
                             IFilterService filterService, IProjectDisplayService projectDisplayService,
                             IOfficerRegistrationService officerRegistrationService,
                             IUserRepository userRepository) {
        super(scanner, currentUser, authService, projectService, applicationService, enquiryService,
              eligibilityService, filterService, projectDisplayService, officerRegistrationService);
        this.userRepository = userRepository;

         if (!(currentUser instanceof HDBOfficer)) {
            throw new IllegalStateException("OfficerController initialized with non-officer user.");
        }
    }

    private HDBOfficer getCurrentOfficer() {
        return (HDBOfficer) currentUser;
    }

    public void registerForProject() {
        HDBOfficer officer = getCurrentOfficer();

        if (officer.hasActiveApplication() || officer.hasPendingWithdrawal()) {
             System.out.println("Error: Cannot register to handle a project while you have an active BTO application or pending withdrawal.");
             return;
        }

        System.out.println("\n--- Register to Handle Project ---");

        List<Project> availableProjects = projectService.getAllProjects().stream()
                .filter(p -> eligibilityService.canOfficerRegisterForProject(officer, p))
                .sorted(Comparator.comparing(Project::getProjectName))
                .collect(Collectors.toList());

        if (availableProjects.isEmpty()) {
            System.out.println("No projects currently available for you to register for based on eligibility criteria:");
            System.out.println("- Project must have open officer slots and not be expired.");
            System.out.println("- You must not already have a registration (Pending/Approved/Rejected) for the project.");
            System.out.println("- You cannot have an active BTO application or Pending Withdrawal.");
            System.out.println("- Project dates cannot overlap with a project you handle or have a pending registration for.");
            System.out.println("- You cannot register for a project you have previously applied for.");
            return;
        }

        projectDisplayService.displayProjectList(availableProjects, "Select Project to Register For", currentUser);
        Project selectedProject = projectDisplayService.selectProjectFromList(availableProjects, scanner);

        if (selectedProject != null) {
            boolean success = officerRegistrationService.submitRegistration(officer, selectedProject);
        }
    }

    public void viewRegistrationStatus() {
        HDBOfficer officer = getCurrentOfficer();
        System.out.println("\n--- Your HDB Officer Registration Status ---");

        Project handlingProject = eligibilityService.getOfficerHandlingProject(officer);
        if (handlingProject != null) {
            System.out.println("You are currently APPROVED and HANDLING project: " + handlingProject.getProjectName());
            System.out.println("----------------------------------------");
        }

        List<OfficerRegistration> myRegistrations = officerRegistrationService.getRegistrationsByOfficer(officer.getNric());

        List<OfficerRegistration> otherRegistrations = myRegistrations.stream()
                .filter(reg -> handlingProject == null || !reg.getProjectName().equals(handlingProject.getProjectName()))
                .collect(Collectors.toList());

        if (otherRegistrations.isEmpty() && handlingProject == null) {
            System.out.println("You have no past or pending registration requests.");
        } else if (!otherRegistrations.isEmpty()) {
            System.out.println("Other Registration History/Requests:");
            for (OfficerRegistration reg : otherRegistrations) {
                System.out.printf("- Project: %-15s | Status: %-10s | Date: %s\n",
                        reg.getProjectName(), reg.getStatus(), DateUtils.formatDate(reg.getRegistrationDate()));
            }
        }
    }

    public void viewHandlingProjectDetails() {
        HDBOfficer officer = getCurrentOfficer();
        Project project = eligibilityService.getOfficerHandlingProject(officer);

        if (project == null) {
            System.out.println("You are not currently handling any project. Register for one first.");
            return;
        }

        System.out.println("\n--- Details for Handling Project: " + project.getProjectName() + " ---");
        projectDisplayService.displayProjectList(Collections.singletonList(project), "Project Details", currentUser);
    }

    public void viewAndReplyToEnquiries() {
        HDBOfficer officer = getCurrentOfficer();
        Project handlingProject = eligibilityService.getOfficerHandlingProject(officer);

        if (handlingProject == null) {
            System.out.println("You need to be handling a project to view and reply to its enquiries.");
            return;
        }
        String handlingProjectName = handlingProject.getProjectName();

        System.out.println("\n--- Enquiries for Project: " + handlingProjectName + " ---");

        List<Enquiry> unrepliedEnquiries = enquiryService.getAllEnquiries().stream()
                .filter(e -> e.getProjectName().equalsIgnoreCase(handlingProjectName) && !e.isReplied())
                .sorted(Comparator.comparing(Enquiry::getEnquiryDate))
                .collect(Collectors.toList());

        System.out.println("--- Unreplied Enquiries ---");
        if (unrepliedEnquiries.isEmpty()) {
            System.out.println("(None)");
        } else {
            for (int i = 0; i < unrepliedEnquiries.size(); i++) {
                Enquiry e = unrepliedEnquiries.get(i);
                printOfficerEnquiryDetails(e);
                System.out.println("---");
            }
            int choice = InputUtils.getIntInput(scanner, "Enter the number of the enquiry to reply to (or 0 to skip): ", 0, unrepliedEnquiries.size());
            if (choice >= 1) {
                Enquiry enquiryToReply = unrepliedEnquiries.get(choice - 1);
                String replyText = InputUtils.getStringInput(scanner, "Enter your reply: ", false);
                boolean success = enquiryService.replyToEnquiry(enquiryToReply, replyText, currentUser);
            }
        }

        List<Enquiry> repliedEnquiries = enquiryService.getAllEnquiries().stream()
                .filter(e -> e.getProjectName().equalsIgnoreCase(handlingProjectName) && e.isReplied())
                .sorted(Comparator.comparing(Enquiry::getReplyDate).reversed())
                .collect(Collectors.toList());

        System.out.println("\n--- Replied Enquiries ---");
        if (repliedEnquiries.isEmpty()) {
            System.out.println("(None)");
        } else {
            repliedEnquiries.forEach(e -> {
                printOfficerEnquiryDetails(e);
                System.out.println("--------------------");
            });
        }
    }

    private void printOfficerEnquiryDetails(Enquiry e) {
         if (e == null) return;
         System.out.printf("ID: %s | Applicant: %s | Date: %s\n",
                 e.getEnquiryId(), e.getApplicantNric(), DateUtils.formatDate(e.getEnquiryDate()));
         System.out.println("   Enquiry: " + e.getEnquiryText());
         if (e.isReplied()) {
             System.out.printf("   Reply (by %s on %s): %s\n",
                     e.getRepliedByNric() != null ? e.getRepliedByNric() : "N/A",
                     e.getReplyDate() != null ? DateUtils.formatDate(e.getReplyDate()) : "N/A",
                     e.getReplyText());
         } else {
             System.out.println("   Reply: (Pending)");
         }
    }


    public void manageFlatBooking() {
        HDBOfficer officer = getCurrentOfficer();
        Project project = eligibilityService.getOfficerHandlingProject(officer);

        if (project == null) {
            System.out.println("You need to be handling a project to manage flat bookings.");
            return;
        }
        String handlingProjectName = project.getProjectName();

        System.out.println("\n--- Flat Booking Management for Project: " + handlingProjectName + " ---");

        List<BTOApplication> successfulApps = applicationService.getAllApplications().values().stream()
                .filter(app -> app.getProjectName().equals(handlingProjectName)
                        && app.getStatus() == ApplicationStatus.SUCCESSFUL)
                .sorted(Comparator.comparing(BTOApplication::getApplicationDate))
                .collect(Collectors.toList());

        if (successfulApps.isEmpty()) {
            System.out.println("No applicants with status SUCCESSFUL found for this project.");
            return;
        }

        System.out.println("Applicants with SUCCESSFUL status (ready for booking):");
        Map<String, User> allUsers = userRepository.getAllUsers();
        for (int i = 0; i < successfulApps.size(); i++) {
            BTOApplication app = successfulApps.get(i);
            User applicantUser = allUsers.get(app.getApplicantNric());
            System.out.printf("%d. NRIC: %s | Name: %-15s | Applied Type: %s | App Date: %s\n",
                    i + 1,
                    app.getApplicantNric(),
                    applicantUser != null ? applicantUser.getName() : "N/A",
                    app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A",
                    DateUtils.formatDate(app.getApplicationDate()));
        }

        int choice = InputUtils.getIntInput(scanner, "Enter the number of the applicant to process booking for (or 0 to cancel): ", 0, successfulApps.size());
        if (choice == 0) {
            System.out.println("Operation cancelled.");
            return;
        }

        BTOApplication applicationToBook = successfulApps.get(choice - 1);
        User applicantUser = userRepository.findUserByNric(applicationToBook.getApplicantNric());

        if (!(applicantUser instanceof Applicant)) {
            System.out.println("Error: Applicant data not found or invalid for NRIC " + applicationToBook.getApplicantNric());
            return;
        }
        Applicant applicant = (Applicant) applicantUser;

        applicationService.synchronizeApplicantStatus(applicant);
        if (applicationToBook.getStatus() != ApplicationStatus.SUCCESSFUL) {
            System.out.println("Error: Applicant status is no longer SUCCESSFUL (Current: "
                    + applicationToBook.getStatus() + "). Cannot proceed.");
            return;
        }
        if (applicant.hasBooked()) {
            System.out.println("Error: Applicant " + applicant.getNric()
                    + " has already booked a flat according to their profile.");
            return;
        }

        FlatType appliedFlatType = applicationToBook.getFlatTypeApplied();
        if (appliedFlatType == null) {
            System.out.println("Error: Application record does not have a valid flat type specified. Cannot book.");
            return;
        }

        FlatTypeDetails details = project.getMutableFlatTypeDetails(appliedFlatType);
        if (details == null || details.getAvailableUnits() <= 0) {
            System.out.println("Error: No available units for the applied flat type ("
                    + appliedFlatType.getDisplayName() + ") at this moment. Booking cannot proceed.");
            return;
        }

        System.out.println("\n--- Confirm Booking ---");
        System.out.println("Applicant: " + applicant.getName() + " (" + applicant.getNric() + ")");
        System.out.println("Project: " + applicationToBook.getProjectName());
        System.out.println("Flat Type: " + appliedFlatType.getDisplayName());
        System.out.println("Available Units Before Booking: " + details.getAvailableUnits());
        System.out.printf("Selling Price: $%.2f\n", details.getSellingPrice());

        boolean confirm = InputUtils.getConfirmation(scanner, "\nConfirm booking for this applicant?");

        if (confirm) {
            boolean success = applicationService.bookFlat(applicationToBook, applicant, project);

            if (success) {
                generateBookingReceipt(applicant, applicationToBook, project);
            } else {
                System.out.println("Booking failed.");
            }
        } else {
            System.out.println("Booking cancelled.");
        }
    }

    private void generateBookingReceipt(Applicant applicant, BTOApplication application, Project project) {
        System.out.println("\n================ BTO Booking Receipt ================");
        System.out.println(" Receipt Generated: " + DateUtils.formatDate(DateUtils.getCurrentDate()) + " by Officer "
                + currentUser.getNric());
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
        System.out.println("   Booked Flat:   "
                + (application.getFlatTypeApplied() != null ? application.getFlatTypeApplied().getDisplayName() : "N/A"));
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
