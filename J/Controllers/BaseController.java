package Controllers;

import Enums.OfficerRegistrationStatus;
import Enums.FlatType;
import Enums.ApplicationStatus;
import Enums.MaritalStatus;
import Enums.UserRole;

import Models.User;
import Parsers.Dparse;
import Models.Project;
import Models.BTOApplication;
import Models.Enquiry;
import Models.HDBManager;
import Models.HDBOfficer;
import Models.Applicant;
import Models.OfficerRegistration;
import Models.FlatTypeDetails;

import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Scanner;
import java.util.Comparator;
import java.util.stream.Collectors;

import Utils.DateUtils;

public abstract class BaseController {
    protected final Map<String, User> users;
    protected final List<Project> projects;
    protected final Map<String, BTOApplication> applications;
    protected final List<Enquiry> enquiries;
    protected final Map<String, OfficerRegistration> officerRegistrations;
    protected final User currentUser;
    protected final Scanner scanner;
    protected final AuthController authController;

    protected String filterLocation = null;
    protected FlatType filterFlatType = null;

    public BaseController(Map<String, User> users, List<Project> projects, Map<String, BTOApplication> applications, List<Enquiry> enquiries, Map<String, OfficerRegistration> officerRegistrations, User currentUser, Scanner scanner, AuthController authController) {
        this.users = users;
        this.projects = projects;
        this.applications = applications;
        this.enquiries = enquiries;
        this.officerRegistrations = officerRegistrations;
        this.currentUser = currentUser;
        this.scanner = scanner;
        this.authController = authController;
    }


    protected Project findProjectByName(String name) {
        if (name == null || name.trim().isEmpty()) return null;
        return projects.stream()
                       .filter(p -> p.getProjectName().equalsIgnoreCase(name.trim()))
                       .findFirst()
                       .orElse(null);
    }

     protected BTOApplication findApplicationByApplicantAndProject(String nric, String projectName) {
         if (nric == null || projectName == null) return null;
        String appId = nric + "_" + projectName;
        return applications.get(appId);
    }

    public Project getOfficerHandlingProject(HDBOfficer officer) {
        if (officer == null) return null;
        Date today = DateUtils.getCurrentDate();
        return officerRegistrations.values().stream()
            .filter(reg -> reg.getOfficerNric().equals(officer.getNric()) && reg.getStatus() == OfficerRegistrationStatus.APPROVED)
            .map(reg -> findProjectByName(reg.getProjectName()))
            .filter(Objects::nonNull)
            .filter(p -> p.isApplicationPeriodActive(today))
            .findFirst()
            .orElse(null);
    }

    protected boolean checkDateOverlap(Project p1, Project p2) {
        if (p1 == null || p2 == null || p1.getApplicationOpeningDate() == null || p1.getApplicationClosingDate() == null || p2.getApplicationOpeningDate() == null || p2.getApplicationClosingDate() == null) {
            return false;
        }
        return !p1.getApplicationOpeningDate().after(p2.getApplicationClosingDate()) &&
               !p1.getApplicationClosingDate().before(p2.getApplicationOpeningDate());
    }



     protected List<Project> getFilteredProjects(boolean checkVisibility, boolean checkEligibility, boolean checkAvailability, boolean checkApplicationPeriod, boolean checkNotExpired) {
        Date currentDate = DateUtils.getCurrentDate();
        return projects.stream()
                .filter(p -> filterLocation == null || p.getNeighborhood().equalsIgnoreCase(filterLocation))
                .filter(p -> filterFlatType == null || p.getFlatTypes().containsKey(filterFlatType))

                .filter(p -> !checkVisibility || isProjectVisibleToCurrentUser(p))

                .filter(p -> !checkApplicationPeriod || p.isApplicationPeriodActive(currentDate))

                .filter(p -> !checkNotExpired || !p.isApplicationPeriodExpired(currentDate))

                .filter(p -> {
                    if (!checkEligibility && !checkAvailability) return true;

                    if (currentUser instanceof HDBManager) return true;

                    boolean eligibleForAnyType = p.getFlatTypes().keySet().stream()
                                                  .anyMatch(this::canApplyForFlatType);

                    if (checkEligibility && !eligibleForAnyType) {
                         return false;
                    }

                    if (!checkAvailability) return true;

                    boolean eligibleAndAvailableExists = p.getFlatTypes().entrySet().stream()
                        .anyMatch(entry -> {
                            FlatType type = entry.getKey();
                            FlatTypeDetails details = entry.getValue();
                            return canApplyForFlatType(type) && details.getAvailableUnits() > 0;
                        });

                    return eligibleAndAvailableExists;
                })
                .sorted(Comparator.comparing(Project::getProjectName))
                .collect(Collectors.toList());
    }

    protected boolean isProjectVisibleToCurrentUser(Project project) {
        if (currentUser instanceof HDBManager) return true;

        boolean appliedToThis = false;
        if (currentUser instanceof Applicant) {
            Applicant appUser = (Applicant) currentUser;
            appliedToThis = project.getProjectName().equals(appUser.getAppliedProjectName()) &&
                            appUser.getApplicationStatus() != null &&
                            appUser.getApplicationStatus() != ApplicationStatus.UNSUCCESSFUL &&
                            appUser.getApplicationStatus() != ApplicationStatus.WITHDRAWN;
        }


        boolean isHandlingOfficer = false;
        if (currentUser instanceof HDBOfficer) {
            isHandlingOfficer = officerRegistrations.values().stream()
                .anyMatch(reg -> reg.getOfficerNric().equals(currentUser.getNric()) &&
                                 reg.getProjectName().equals(project.getProjectName()) &&
                                 reg.getStatus() == OfficerRegistrationStatus.APPROVED);
        }

        return project.isVisible() || appliedToThis || isHandlingOfficer;
    }


     protected boolean canApplyForFlatType(FlatType type) {
         if (currentUser instanceof HDBManager) return false;

         if (currentUser.getMaritalStatus() == MaritalStatus.SINGLE) {
             return currentUser.getAge() >= 35 && type == FlatType.TWO_ROOM;
         } else if (currentUser.getMaritalStatus() == MaritalStatus.MARRIED) {
             return currentUser.getAge() >= 21 && (type == FlatType.TWO_ROOM || type == FlatType.THREE_ROOM);
         }
         return false;
     }


     public void applyFilters() {
         System.out.println("\n--- Apply/Clear Filters ---");
         System.out.print("Enter neighborhood to filter by (current: " + (filterLocation == null ? "Any" : filterLocation) + ", leave blank to clear): ");
         String loc = scanner.nextLine().trim();
         filterLocation = loc.isEmpty() ? null : loc;

         System.out.print("Enter flat type to filter by (TWO_ROOM, THREE_ROOM, current: " + (filterFlatType == null ? "Any" : filterFlatType) + ", leave blank to clear): ");
         String typeStr = scanner.nextLine().trim();
         if (typeStr.isEmpty()) {
             filterFlatType = null;
         } else {
             try {
                 FlatType parsedType = FlatType.fromString(typeStr);
                 if (parsedType != null) {
                    filterFlatType = parsedType;
                 } else {
                    System.out.println("Invalid flat type entered. Filter not changed.");
                 }
             } catch (IllegalArgumentException e) {
                 System.out.println("Invalid flat type format. Filter not changed.");
             }
         }
         System.out.println("Filters updated. Current filters: Location=" + (filterLocation == null ? "Any" : filterLocation) + ", FlatType=" + (filterFlatType == null ? "Any" : filterFlatType));
     }

     protected void viewAndSelectProject(List<Project> projectList, String prompt) {
         if (projectList.isEmpty()) {
             System.out.println("No projects match the current criteria.");
             return;
         }

         System.out.println("\n--- " + prompt + " ---");
         System.out.println("Current Filters: Location=" + (filterLocation == null ? "Any" : filterLocation) + ", FlatType=" + (filterFlatType == null ? "Any" : filterFlatType));
         System.out.println("--------------------------------------------------------------------------------------------------------------------");
         System.out.printf("%-3s %-15s %-12s %-10s %-10s %-8s %-25s\n", "#", "Project Name", "Neighborhood", "Open", "Close", "Visible", "Flat Types (Available/Total, Price, Eligibility)");
         System.out.println("--------------------------------------------------------------------------------------------------------------------");

         for (int i = 0; i < projectList.size(); i++) {
             Project p = projectList.get(i);
             System.out.printf("%-3d %-15s %-12s %-10s %-10s %-8s ",
                     i + 1,
                     p.getProjectName(),
                     p.getNeighborhood(),
                     DateUtils.formatDate(p.getApplicationOpeningDate()),
                     DateUtils.formatDate(p.getApplicationClosingDate()),
                     p.isVisible() ? "On" : "Off");

             String flatDetails = p.getFlatTypes().entrySet().stream()
                 .sorted(Map.Entry.comparingByKey())
                 .map(entry -> {
                     FlatType type = entry.getKey();
                     FlatTypeDetails details = entry.getValue();
                     String eligibilityMark = "";
                     if (currentUser instanceof Applicant) {
                         if (!canApplyForFlatType(type)) {
                             eligibilityMark = " (Ineligible)";
                         } else if (details.getAvailableUnits() == 0) {
                              eligibilityMark = " (No Units)";
                         }
                     }
                     return String.format("%s: %d/%d ($%.0f)%s",
                             type.getDisplayName(), details.getAvailableUnits(), details.getTotalUnits(), details.getSellingPrice(), eligibilityMark);
                 })
                 .collect(Collectors.joining(", "));
             System.out.println(flatDetails);

             if (currentUser.getRole() != UserRole.APPLICANT) {
                  System.out.printf("%-3s %-15s %-12s %-10s %-10s %-8s %-25s\n", "", "", "", "", "", "",
                    "Mgr: " + p.getManagerNric() + ", Officers: " + p.getApprovedOfficerNrics().size() + "/" + p.getMaxOfficerSlots());
             }
             if (i < projectList.size() - 1) System.out.println("---");

         }
         System.out.println("--------------------------------------------------------------------------------------------------------------------");
     }

     protected Project selectProjectFromList(List<Project> projectList) {
         if (projectList == null || projectList.isEmpty()) return null;
         System.out.print("Enter the number of the project (or 0 to cancel): ");
         int choice;
         try {
             choice = Integer.parseInt(scanner.nextLine());
             if (choice == 0) {
                 System.out.println("Operation cancelled.");
                 return null;
             }
             if (choice >= 1 && choice <= projectList.size()) {
                 return projectList.get(choice - 1);
             } else {
                 System.out.println("Invalid choice number.");
                 return null;
             }
         } catch (NumberFormatException e) {
             System.out.println("Invalid input. Please enter a number.");
             return null;
         }
     }

    protected int getIntInput(String prompt, int min, int max) {
        int value = -1;
        while (true) {
            System.out.print(prompt + " ");
            try {
                value = Integer.parseInt(scanner.nextLine());
                if (value >= min && value <= max) {
                    break;
                } else {
                    System.out.println("Input must be between " + min + " and " + max + ".");
                }
            } catch (NumberFormatException e) {
                System.out.println("Invalid input. Please enter a whole number.");
            }
        }
        return value;
    }

     protected double getDoubleInput(String prompt, double min, double max) {
        double value = -1.0;
        while (true) {
            System.out.print(prompt + " ");
            try {
                value = Double.parseDouble(scanner.nextLine());
                 if (value >= min && value <= max) {
                    break;
                } else {
                     System.out.println("Input must be between " + min + " and " + max + ".");
                }
            } catch (NumberFormatException e) {
                System.out.println("Invalid input. Please enter a number.");
            }
        }
        return value;
    }

     protected Date getDateInput(String prompt, boolean allowBlank) {
        Date date = null;
        while (true) {
            System.out.print(prompt + " ");
            String input = scanner.nextLine().trim();
             if (input.isEmpty() && allowBlank) {
                 return null;
             }
             date = Dparse.parseDate(input);
             if (date != null) {
                 break;
             }
        }
        return date;
    }
}

