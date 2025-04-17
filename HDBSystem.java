import java.io.File;
import java.io.FileNotFoundException;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Scanner;
import java.util.stream.Collectors;

public class HDBSystem {

    static DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd");

    public static boolean datesOverlap(LocalDate start1, LocalDate end1, LocalDate start2, LocalDate end2) {
        return !(end1.isBefore(start2) || start1.isAfter(end2));
    }

    static class User {
        public String name;
        public String nric;
        public int age;
        public String maritalStatus;
        public String password;

        public User(String name, String nric, String age, String maritalStatus, String password) {
            this.name = name;
            this.nric = nric;
            try {
                this.age = Integer.parseInt(age);
            } catch (NumberFormatException e) {
                System.err.println("Warning: Could not parse age '" + age + "' for user " + name + ". Setting age to 0.");
                this.age = 0;
            }
            this.maritalStatus = maritalStatus;
            this.password = password;
        }

        public List<String> menu() {
            return new ArrayList<>();
        }

        @Override
        public String toString() {
            return "User{" + "name='" + name + '\'' + ", nric='" + nric + '\'' + '}';
        }
         @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            User user = (User) o;
            return java.util.Objects.equals(nric, user.nric);
        }

        @Override
        public int hashCode() {
            return java.util.Objects.hash(nric);
        }
    }

    static class Applicant extends User {
        public Applicant(String name, String nric, String age, String maritalStatus, String password) {
            super(name, nric, age, maritalStatus, password);
        }

        @Override
        public List<String> menu() {
            return new ArrayList<>(Arrays.asList(
                    "View Projects",
                    "Apply for Projects",
                    "View Application Status (Book)",
                    "Request Withdrawal",
                    "Submit Enquiry",
                    "View My Enquiries",
                    "Edit My Enquiry",
                    "Delete My Enquiry",
                    "Change Password",
                    "Logout"
            ));
        }

        public List<String> getProjectsForApplicant(ProjectsController projectController, ApplicationsController applicationsController) {
            List<String> projectsOutput = new ArrayList<>();
            Application myApp = applicationsController.getOngoingApplications(this);

            for (int i = 0; i < projectController.projects.size(); i++) {
                Project project = projectController.projects.get(i);
                boolean isMyProjectAsOfficer = false;
                if (this instanceof HDBOfficer) {
                     isMyProjectAsOfficer = ((HDBOfficer)this).myProjects.contains(project);
                }

                if (project.visibility || (myApp != null && myApp.project.equals(project))) {
                    if (isMyProjectAsOfficer) {
                         if (myApp == null || !myApp.project.equals(project)) {
                             continue;
                         }
                    }
                    String details = "ID: " + i + "\nName: " + project.projectName + "\nNeighborhood: " + project.neighborhood + "\n";
                    details += project.type1 + ": " + project.numUnits1 + " (" + project.price1 + ")\n";
                    details += project.type2 + ": " + project.numUnits2 + " (" + project.price2 + ")\n";
                    details += "Application Date: " + project.openingDate + "-" + project.closingDate + "\n";
                    details += "Manager: " + project.manager + "\nOfficers: " + String.join(",", project.officers) + "\n";
                    projectsOutput.add(details);
                }
            }
            return projectsOutput;
        }

        public Pair<Boolean, String> applyForProject(Project project, int flatType, ApplicationsController applicationsController) {
            return applicationsController.applyForProject(this, project, flatType);
        }

        public Pair<Boolean, String> submitEnquiry(Project project, String text, EnquiriesController enquiriesController) {
            return enquiriesController.createEnquiry(this, project, text);
        }

        public String viewMyEnquiries(EnquiriesController enquiriesController) {
            List<Pair<Integer, Enquiry>> myEnquiries = enquiriesController.getEnquiriesByApplicant(this);
            if (myEnquiries.isEmpty()) {
                return "No enquiries.";
            }
            StringBuilder msg = new StringBuilder("Your Enquiries:\n");
            for (Pair<Integer, Enquiry> pair : myEnquiries) {
                msg.append("Index: ").append(pair.first).append(" | Project: ").append(pair.second.project.projectName).append(" | Text: ").append(pair.second.text).append("\n");
            }
            return msg.toString();
        }

        public Pair<Boolean, String> editMyEnquiry(EnquiriesController enquiriesController, int idx, String newText) {
            List<Pair<Integer, Enquiry>> myEnquiries = enquiriesController.getEnquiriesByApplicant(this);
            for (Pair<Integer, Enquiry> pair : myEnquiries) {
                if (pair.first == idx) {
                    return enquiriesController.editEnquiry(pair.second, newText);
                }
            }
            return new Pair<>(false, "Invalid enquiry index.");
        }

        public Pair<Boolean, String> deleteMyEnquiry(EnquiriesController enquiriesController, int idx) {
            List<Pair<Integer, Enquiry>> myEnquiries = enquiriesController.getEnquiriesByApplicant(this);
            for (Pair<Integer, Enquiry> pair : myEnquiries) {
                if (pair.first == idx) {
                    return enquiriesController.deleteEnquiry(pair.second);
                }
            }
            return new Pair<>(false, "Invalid enquiry index.");
        }
    }

    static class HDBOfficer extends Applicant {
        public List<Registration> registrations = new ArrayList<>();
        public List<Project> myProjects = new ArrayList<>();

        public HDBOfficer(String name, String nric, String age, String maritalStatus, String password) {
            super(name, nric, age, maritalStatus, password);
        }

        @Override
        public List<String> menu() {
            List<String> officerMenu = new ArrayList<>(super.menu());
            officerMenu.remove("Logout");
            officerMenu.addAll(Arrays.asList(
                    "Register for Project as Officer",
                    "View My Officer Registrations",
                    "Reply to Project Enquiry (Handled Project)",
                    "Book a Flat for Applicant (Handled Project)",
                    "Generate Booking Receipt",
                    "Logout"
            ));
            return officerMenu;
        }

        public Pair<Boolean, String> registerForProject(Project project, RegistrationsController registrationsController) {
            return registrationsController.registerForProject(this, project);
        }

        public String viewOfficerRegistrations() {
            if (registrations.isEmpty()) {
                return "No officer registrations.";
            }
            StringBuilder msg = new StringBuilder("Officer Registrations:\n");
            for (int i = 0; i < registrations.size(); i++) {
                Registration r = registrations.get(i);
                msg.append(i).append(". Project: ").append(r.project.projectName).append(" | Status: ").append(r.status).append("\n");
            }
            return msg.toString();
        }

        public Pair<Boolean, String> replyEnquiry(int idx, String replyText, EnquiriesController enquiriesController) {
            return enquiriesController.replyToProjectEnquiry(this, idx, replyText);
        }

        public Pair<Boolean, String> bookFlatForApplicant(String applicantNric, ApplicationsController applicationsController) {
            return applicationsController.bookFlatForApplicant(this, applicantNric);
        }

        public Pair<Boolean, String> generateReceipt(String applicantNric, ApplicationsController applicationsController) {
            return applicationsController.generateReceipt(this, applicantNric);
        }
    }

    static class HDBManager extends User {
        public HDBManager(String name, String nric, String age, String maritalStatus, String password) {
            super(name, nric, age, maritalStatus, password);
        }

        @Override
        public List<String> menu() {
            return new ArrayList<>(Arrays.asList(
                    "Create Project",
                    "Edit Project",
                    "Delete Project",
                    "Toggle Project Visibility",
                    "View All Projects",
                    "View My Projects",
                    "View Officer Registrations",
                    "Approve Officer Registration",
                    "Reject Officer Registration",
                    "View Applications",
                    "Approve Application",
                    "Reject Application",
                    "Approve Withdrawal",
                    "Generate Booking Report",
                    "View All Enquiries",
                    "Reply to Enquiry",
                    "Change Password",
                    "Logout"
            ));
        }

        public Pair<Boolean, Project> createProject(String name, String neighborhood, int n1, int p1, int n2, int p2, String od, String cd, int slot, ProjectsController projectsController) {
            return projectsController.createProject(this, name, neighborhood, n1, p1, n2, p2, od, cd, slot);
        }

        public Pair<Boolean, String> editProject(Project project, String name, String neighborhood, Integer n1, Integer p1, Integer n2, Integer p2, String openDate, String closeDate, Integer officerSlot, ProjectsController projectsController) {
            return projectsController.editProject(this, project, name, neighborhood, n1, p1, n2, p2, openDate, closeDate, officerSlot);
        }

        public Pair<Boolean, String> deleteProject(Project project, ProjectsController projectsController) {
            return projectsController.deleteProject(this, project);
        }

        public Pair<Boolean, String> toggleProjectVisibility(Project project, ProjectsController projectsController) {
            return projectsController.toggleProjectVisibility(this, project);
        }

        public String viewAllProjects(ProjectsController projectsController) {
            return projectsController.viewAllProjects();
        }

        public String viewMyProjects(ProjectsController projectsController) {
            return projectsController.viewMyProjects(this);
        }

        public String viewOfficerRegistrations(RegistrationsController registrationsController) {
            List<Registration> regs = registrationsController.getAllRegistrationsForManager(this.name);
            if (regs.isEmpty()) {
                return "No registrations.";
            }
            StringBuilder msg = new StringBuilder("Officer Registrations:\n");
            for (int i = 0; i < regs.size(); i++) {
                Registration r = regs.get(i);
                msg.append(i).append(". Project: ").append(r.project.projectName).append(", Officer: ").append(r.officer.name).append(", Status: ").append(r.status).append("\n");
            }
            return msg.toString();
        }

        public Pair<Boolean, String> approveOfficerRegistration(Registration reg, RegistrationsController registrationsController) {
            return registrationsController.approveOfficerRegistration(this, reg);
        }

        public Pair<Boolean, String> rejectOfficerRegistration(Registration reg, RegistrationsController registrationsController) {
            return registrationsController.rejectOfficerRegistration(this, reg);
        }

        public String viewApplications(ApplicationsController applicationsController) {
            return applicationsController.viewApplications();
        }

        public Pair<Boolean, String> approveApplication(Application application, ApplicationsController applicationsController) {
            return applicationsController.approveApplication(this, application);
        }

        public Pair<Boolean, String> rejectApplication(Application application, ApplicationsController applicationsController) {
            return applicationsController.rejectApplication(this, application);
        }

        public Pair<Boolean, String> approveWithdrawal(Application application, ApplicationsController applicationsController) {
            return applicationsController.approveWithdrawal(this, application);
        }

        public String generateBookingReport(ApplicationsController applicationsController, String filterMarital) {
            return applicationsController.generateBookingReport(filterMarital);
        }

        public String viewAllEnquiries(EnquiriesController enquiriesController) {
            return enquiriesController.viewAllEnquiries();
        }

        public Pair<Boolean, String> replyToEnquiry(int idx, String replyText, EnquiriesController enquiriesController) {
            return enquiriesController.replyToEnquiry(idx, replyText);
        }
    }

    static class Project {
        public String projectName;
        public String neighborhood;
        public String type1;
        public int numUnits1;
        public int price1;
        public String type2;
        public int numUnits2;
        public int price2;
        public String openingDate;
        public String closingDate;
        public String manager;
        public int officerSlot;
        public List<String> officers;
        public boolean visibility = true;

        public Project(String projectName, String neighborhood, String type1, int numUnits1, int price1, String type2, int numUnits2, int price2, String openingDate, String closingDate, String manager, int officerSlot, List<String> officers) {
            this.projectName = projectName;
            this.neighborhood = neighborhood;
            this.type1 = type1;
            this.numUnits1 = numUnits1;
            this.price1 = price1;
            this.type2 = type2;
            this.numUnits2 = numUnits2;
            this.price2 = price2;
            this.openingDate = openingDate;
            this.closingDate = closingDate;
            this.manager = manager;
            this.officerSlot = officerSlot;
            this.officers = new ArrayList<>(officers);
        }

        public LocalDate getOpeningLocalDate() {
            try {
                return LocalDate.parse(openingDate, DATE_FORMATTER);
            } catch (DateTimeParseException e) { return null; }
        }
        public LocalDate getClosingLocalDate() {
            try {
                return LocalDate.parse(closingDate, DATE_FORMATTER);
            } catch (DateTimeParseException e) { return null; }
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            Project project = (Project) o;
            return java.util.Objects.equals(projectName, project.projectName) &&
                   java.util.Objects.equals(manager, project.manager);
        }

        @Override
        public int hashCode() {
            return java.util.Objects.hash(projectName, manager);
        }

        @Override
        public String toString() {
            return "Project{" + "projectName='" + projectName + '\'' + '}';
        }
    }

    static class Application {
        public Applicant applicant;
        public Project project;
        public int flatType;
        public String status;
        public boolean requestWithdraw = false;
        public boolean requestedBooking = false;

        public Application(Applicant applicant, Project project, int flatType) {
            this.applicant = applicant;
            this.project = project;
            this.flatType = flatType;
            this.status = "PENDING";
        }
         @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            Application that = (Application) o;
            return java.util.Objects.equals(applicant, that.applicant);
        }

        @Override
        public int hashCode() {
            return java.util.Objects.hash(applicant);
        }
    }

    static class Registration {
        public HDBOfficer officer;
        public Project project;
        public String status;

        public Registration(HDBOfficer officer, Project project) {
            this.officer = officer;
            this.project = project;
            this.status = "PENDING";
        }
         @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            Registration that = (Registration) o;
            return java.util.Objects.equals(officer, that.officer) &&
                   java.util.Objects.equals(project, that.project);
        }

        @Override
        public int hashCode() {
            return java.util.Objects.hash(officer, project);
        }
    }

    static class Enquiry {
        public Applicant applicant;
        public Project project;
        public String text;

        public Enquiry(Applicant applicant, Project project, String text) {
            this.applicant = applicant;
            this.project = project;
            this.text = text;
        }
    }

    static class ProjectsController {
        public List<Project> projects = new ArrayList<>();

        public ProjectsController(String projectCsv) {
            File file = new File(projectCsv);
            try (Scanner scanner = new Scanner(file)) {
                if (scanner.hasNextLine()) {
                    scanner.nextLine();
                }
                while (scanner.hasNextLine()) {
                    String line = scanner.nextLine().trim();
                    if (line.isEmpty()) continue;
                    String[] parts = line.split(",");
                    if (parts.length < 12) {
                         System.err.println("Warning: Skipping malformed project line: " + line);
                         continue;
                    }
                    try {
                        String projectName = parts[0];
                        String neighborhood = parts[1];
                        String type1 = parts[2];
                        int numUnits1 = Integer.parseInt(parts[3]);
                        int price1 = Integer.parseInt(parts[4]);
                        String type2 = parts[5];
                        int numUnits2 = Integer.parseInt(parts[6]);
                        int price2 = Integer.parseInt(parts[7]);
                        String openingDate = parts[8];
                        String closingDate = parts[9];
                        String manager = parts[10];
                        int officerSlot = Integer.parseInt(parts[11]);
                        List<String> officerList = new ArrayList<>();
                        if (parts.length > 12 && !parts[12].isEmpty()) {
                            String officersStr = parts[12].replace("\"", "");
                             officerList.addAll(Arrays.asList(officersStr.split("\\s*,\\s*")));
                        }

                        projects.add(new Project(projectName, neighborhood, type1, numUnits1, price1, type2, numUnits2, price2, openingDate, closingDate, manager, officerSlot, officerList));
                    } catch (NumberFormatException | ArrayIndexOutOfBoundsException e) {
                        System.err.println("Warning: Error parsing project line: " + line + " - " + e.getMessage());
                    }
                }
            } catch (FileNotFoundException e) {
                System.err.println("Error: Project CSV file not found: " + projectCsv);
            }
        }

        public Pair<Boolean, Project> createProject(HDBManager manager, String name, String neighborhood, int n1, int p1, int n2, int p2, String od, String cd, int slot) {
            Project proj = new Project(name, neighborhood, "2-Room", n1, p1, "3-Room", n2, p2, od, cd, manager.name, slot, new ArrayList<>());
            return new Pair<>(true, proj);
        }

        public Pair<Boolean, String> editProject(HDBManager manager, Project project, String name, String neighborhood, Integer n1, Integer p1, Integer n2, Integer p2, String openDate, String closeDate, Integer officerSlot) {
            if (!project.manager.equals(manager.name)) {
                return new Pair<>(false, "Not your project.");
            }
            if (name != null && !name.isEmpty()) project.projectName = name;
            if (neighborhood != null && !neighborhood.isEmpty()) project.neighborhood = neighborhood;
            if (n1 != null && n1 >= 0) project.numUnits1 = n1;
            if (p1 != null && p1 >= 0) project.price1 = p1;
            if (n2 != null && n2 >= 0) project.numUnits2 = n2;
            if (p2 != null && p2 >= 0) project.price2 = p2;
            if (openDate != null && !openDate.isEmpty()) project.openingDate = openDate;
            if (closeDate != null && !closeDate.isEmpty()) project.closingDate = closeDate;
            if (officerSlot != null && officerSlot >= 0) project.officerSlot = officerSlot;
            return new Pair<>(true, "Project updated.");
        }

        public Pair<Boolean, String> deleteProject(HDBManager manager, Project project) {
            if (!project.manager.equals(manager.name)) {
                return new Pair<>(false, "Not your project.");
            }
            if (projects.remove(project)) {
                System.out.println("Warning: Deleting project. Associated applications/registrations/enquiries might need manual cleanup or cascading delete logic.");
                return new Pair<>(true, "Project deleted.");
            }
            return new Pair<>(false, "Project not found in controller list.");
        }

        public Pair<Boolean, String> toggleProjectVisibility(HDBManager manager, Project project) {
            if (!project.manager.equals(manager.name)) {
                return new Pair<>(false, "Not your project.");
            }
            project.visibility = !project.visibility;
            return new Pair<>(true, "Visibility set to " + project.visibility + ".");
        }

        public String viewAllProjects() {
            StringBuilder msg = new StringBuilder("All Projects:\n");
            if (projects.isEmpty()) return "No projects available.";
            for (int i = 0; i < projects.size(); i++) {
                Project p = projects.get(i);
                msg.append(i).append(". ").append(p.projectName)
                   .append(" (Visible=").append(p.visibility)
                   .append(", Manager=").append(p.manager)
                   .append(", Officers=").append(String.join(",", p.officers))
                   .append(")\n");
            }
            return msg.toString();
        }

        public String viewMyProjects(HDBManager manager) {
            StringBuilder msg = new StringBuilder("My Projects:\n");
            boolean found = false;
            for (int i = 0; i < projects.size(); i++) {
                Project p = projects.get(i);
                if (p.manager.equals(manager.name)) {
                    msg.append(i).append(". ").append(p.projectName)
                       .append(" (Visible=").append(p.visibility)
                       .append(")\n");
                    found = true;
                }
            }
            if (!found) return "You are not managing any projects.";
            return msg.toString();
        }
    }

    static class ApplicationsController {
        public List<Application> applications = new ArrayList<>();

        public Pair<Boolean, String> verifyApplicationEligibility(Applicant applicant, Project project, int flatType) {
            if (getOngoingApplications(applicant) != null) {
                return new Pair<>(false, "You have already applied for a project.");
            }
            if ("Single".equals(applicant.maritalStatus) && applicant.age < 35) {
                return new Pair<>(false, "Single applicants must be at least 35.");
            }
            if ("Single".equals(applicant.maritalStatus) && flatType != 2) {
                return new Pair<>(false, "Single applicants can only apply for 2-Room.");
            }
            if ("Married".equals(applicant.maritalStatus) && applicant.age < 21) {
                return new Pair<>(false, "Married applicants must be at least 21.");
            }
            if (flatType == 2 && project.numUnits1 <= 0) {
                return new Pair<>(false, "No more 2-room flats available in this project.");
            }
            if (flatType == 3 && project.numUnits2 <= 0) {
                return new Pair<>(false, "No more 3-room flats available in this project.");
            }
            return new Pair<>(true, "Eligible");
        }

        public Pair<Boolean, String> applyForProject(Applicant applicant, Project project, int flatType) {
             if (applicant instanceof HDBOfficer) {
                 HDBOfficer officer = (HDBOfficer) applicant;
                 if (officer.myProjects.contains(project)) {
                     return new Pair<>(false, "Cannot apply for a project you handle as an officer.");
                 }
             }
             if (project.manager.equals(applicant.name)) {
                  return new Pair<>(false, "Managers cannot apply for projects.");
             }

            if (flatType != 2 && flatType != 3) {
                return new Pair<>(false, "Invalid flat type. Must be 2 or 3.");
            }

            Pair<Boolean, String> eligibility = verifyApplicationEligibility(applicant, project, flatType);
            if (!eligibility.first) {
                return eligibility;
            }

            createApplication(applicant, project, flatType);
            return new Pair<>(true, "Application successful.");
        }

        private void createApplication(Applicant applicant, Project project, int flatType) {
            applications.add(new Application(applicant, project, flatType));
        }

        public Application getOngoingApplications(Applicant applicant) {
            for (Application application : applications) {
                if (application.applicant.equals(applicant)) {
                    return application;
                }
            }
            return null;
        }

        public void requestWithdraw(Application application) {
            application.requestWithdraw = true;
        }

        public Pair<Boolean, String> requestBooking(Applicant applicant, Application application) {
            if (application == null || !application.applicant.equals(applicant)) {
                 return new Pair<>(false, "Application not found for this user.");
            }
            if ("SUCCESSFUL".equals(application.status)) {
                if (application.requestedBooking) {
                    return new Pair<>(false, "Booking request already sent.");
                }
                application.requestedBooking = true;
                return new Pair<>(true, "Booking request sent. An officer will process it.");
            }
            if ("BOOKED".equals(application.status)) {
                return new Pair<>(false, "You have already booked a flat for this application.");
            }
            return new Pair<>(false, "Cannot request booking. Application status is: " + application.status);
        }

        public Pair<Boolean, String> bookFlatForApplicant(HDBOfficer officer, String applicantNric) {
            Application appToBook = null;
            for (Application app : applications) {
                if (app.applicant.nric.equals(applicantNric)) {
                    appToBook = app;
                    break;
                }
            }

            if (appToBook == null) {
                return new Pair<>(false, "No application found for NRIC: " + applicantNric);
            }

            if (!officer.myProjects.contains(appToBook.project)) {
                 return new Pair<>(false, "You do not handle the project for this application ("+ appToBook.project.projectName +").");
            }

            if (!"SUCCESSFUL".equals(appToBook.status)) {
                 return new Pair<>(false, "Cannot book flat. Application status is not SUCCESSFUL (Current: " + appToBook.status + ").");
            }

            if (appToBook.flatType == 2) {
                if (appToBook.project.numUnits1 > 0) {
                    appToBook.project.numUnits1--;
                } else {
                    return new Pair<>(false, "Booking failed: No more 2-room units available in " + appToBook.project.projectName);
                }
            } else if (appToBook.flatType == 3) {
                if (appToBook.project.numUnits2 > 0) {
                    appToBook.project.numUnits2--;
                } else {
                    return new Pair<>(false, "Booking failed: No more 3-room units available in " + appToBook.project.projectName);
                }
            } else {
                 return new Pair<>(false, "Internal Error: Invalid flat type in application.");
            }

            appToBook.status = "BOOKED";
            appToBook.requestedBooking = false;
            return new Pair<>(true, "Booked " + appToBook.flatType + "-Room flat for " + appToBook.applicant.name + " (NRIC: " + applicantNric + ") in project " + appToBook.project.projectName + ".");
        }

        public Pair<Boolean, String> generateReceipt(HDBOfficer officer, String applicantNric) {
             Application bookedApp = null;
             for (Application app : applications) {
                 if (app.applicant.nric.equals(applicantNric) && "BOOKED".equals(app.status)) {
                     if (officer.myProjects.contains(app.project)) {
                         bookedApp = app;
                         break;
                     } else {
                         return new Pair<>(false, "Booking found for " + applicantNric + ", but you do not handle project " + app.project.projectName + ".");
                     }
                 }
             }

            if (bookedApp == null) {
                return new Pair<>(false, "No confirmed booking found for NRIC: " + applicantNric + " that you handle.");
            }

            StringBuilder r = new StringBuilder("--- Booking Receipt ---\n");
            r.append("Applicant Name: ").append(bookedApp.applicant.name).append("\n");
            r.append("NRIC:           ").append(bookedApp.applicant.nric).append("\n");
            r.append("Age:            ").append(bookedApp.applicant.age).append("\n");
            r.append("Marital Status: ").append(bookedApp.applicant.maritalStatus).append("\n");
            r.append("----------------------\n");
            r.append("Project Name:   ").append(bookedApp.project.projectName).append("\n");
            r.append("Neighborhood:   ").append(bookedApp.project.neighborhood).append("\n");
            r.append("Booked Flat:    ").append(bookedApp.flatType).append("-Room\n");
            int price = (bookedApp.flatType == 2) ? bookedApp.project.price1 : bookedApp.project.price2;
            r.append("Price:          SGD ").append(price).append("\n");
            r.append("----------------------\n");
            r.append("Booking Officer: ").append(officer.name).append("\n");
            r.append("Booking Date:    ").append(LocalDate.now().format(DATE_FORMATTER)).append("\n");
            r.append("--- End of Receipt ---\n");

            return new Pair<>(true, r.toString());
        }


        public String viewApplications() {
            if (applications.isEmpty()) {
                return "No applications submitted yet.";
            }
            StringBuilder msg = new StringBuilder("Applications:\n");
            for (int i = 0; i < applications.size(); i++) {
                Application a = applications.get(i);
                msg.append(i).append(". Applicant=").append(a.applicant.name)
                   .append(" (").append(a.applicant.nric).append(")")
                   .append(", Project=").append(a.project.projectName)
                   .append(", Flat=").append(a.flatType).append("-Room")
                   .append(", Status=").append(a.status)
                   .append(", Withdraw Req=").append(a.requestWithdraw)
                   .append(", Booking Req=").append(a.requestedBooking)
                   .append("\n");
            }
            return msg.toString();
        }

        public Pair<Boolean, String> approveApplication(HDBManager manager, Application application) {
            if (!application.project.manager.equals(manager.name)) {
                return new Pair<>(false, "Not the manager of this project.");
            }
            if (!"PENDING".equals(application.status)) {
                return new Pair<>(false, "Application is not in PENDING state (Current: " + application.status + ").");
            }
            if (application.flatType == 2 && application.project.numUnits1 <= 0) {
                return new Pair<>(false, "Cannot approve: No more 2-room flats available.");
            }
            if (application.flatType == 3 && application.project.numUnits2 <= 0) {
                return new Pair<>(false, "Cannot approve: No more 3-room flats available.");
            }

            application.status = "SUCCESSFUL";
            return new Pair<>(true, "Application approved (Status set to SUCCESSFUL).");
        }

        public Pair<Boolean, String> rejectApplication(HDBManager manager, Application application) {
            if (!application.project.manager.equals(manager.name)) {
                return new Pair<>(false, "Not the manager of this project.");
            }
            if (!"PENDING".equals(application.status)) {
                return new Pair<>(false, "Application is not in PENDING state (Current: " + application.status + ").");
            }
            application.status = "UNSUCCESSFUL";
            return new Pair<>(true, "Application rejected (Status set to UNSUCCESSFUL).");
        }

        public Pair<Boolean, String> approveWithdrawal(HDBManager manager, Application application) {
             if (!application.project.manager.equals(manager.name)) {
                 return new Pair<>(false, "Not the manager of this project.");
             }
             if (!application.requestWithdraw) {
                 return new Pair<>(false, "Applicant has not requested withdrawal for this application.");
             }
             if (!applications.contains(application)) {
                  return new Pair<>(false, "Application not found in the list (internal error?).");
             }

             boolean removed = applications.remove(application);
             if (removed) {
                  if ("BOOKED".equals(application.status)) {
                      if (application.flatType == 2) application.project.numUnits1++;
                      else if (application.flatType == 3) application.project.numUnits2++;
                      System.out.println("Note: Flat unit returned to inventory due to withdrawal approval after booking.");
                  }
                 return new Pair<>(true, "Withdrawal approved and application removed.");
             } else {
                 return new Pair<>(false, "Failed to remove application (internal error?).");
             }
        }

        public String generateBookingReport(String filterMarital) {
            List<Application> booked = applications.stream()
                    .filter(a -> "BOOKED".equals(a.status))
                    .collect(Collectors.toList());

            if (filterMarital != null && !filterMarital.equalsIgnoreCase("None") && !filterMarital.isEmpty()) {
                booked = booked.stream()
                        .filter(b -> b.applicant.maritalStatus.equalsIgnoreCase(filterMarital))
                        .collect(Collectors.toList());
            }

            if (booked.isEmpty()) {
                return "No bookings found" + ((filterMarital != null && !filterMarital.equalsIgnoreCase("None") && !filterMarital.isEmpty()) ? " matching filter '" + filterMarital + "'." : ".");
            }

            StringBuilder msg = new StringBuilder("--- Booking Report ---\n");
             if (filterMarital != null && !filterMarital.equalsIgnoreCase("None") && !filterMarital.isEmpty()) {
                 msg.append("Filter: Marital Status = ").append(filterMarital).append("\n");
             }
             msg.append("----------------------\n");
             msg.append("Applicant Name,NRIC,Age,Marital Status,Flat Type,Project Name,Neighborhood\n");
            for (Application b : booked) {
                msg.append(b.applicant.name).append(",")
                   .append(b.applicant.nric).append(",")
                   .append(b.applicant.age).append(",")
                   .append(b.applicant.maritalStatus).append(",")
                   .append(b.flatType).append("-Room,")
                   .append(b.project.projectName).append(",")
                   .append(b.project.neighborhood).append("\n");
            }
             msg.append("--- End of Report ---\n");
            return msg.toString();
        }
    }

    static class RegistrationsController {
        public List<Registration> registrations = new ArrayList<>();

        public Pair<Boolean, String> registerForProject(HDBOfficer officer, Project project) {
            if (officer.myProjects.contains(project)) {
                return new Pair<>(false, "You are already an approved officer for this project.");
            }
            if (project.manager.equals(officer.name)) {
                return new Pair<>(false, "Managers cannot register as officers for their own projects.");
            }
            for(Registration existingReg : registrations) {
                if (existingReg.officer.equals(officer) && existingReg.project.equals(project)) {
                    return new Pair<>(false, "You already have a registration (" + existingReg.status + ") for this project.");
                }
            }

            Registration reg = new Registration(officer, project);
            officer.registrations.add(reg);
            this.registrations.add(reg);
            return new Pair<>(true, "Officer registration submitted for project " + project.projectName + " (Status: PENDING).");
        }

        public List<Registration> getAllRegistrationsForManager(String managerName) {
            return registrations.stream()
                    .filter(r -> r.project.manager.equals(managerName))
                    .collect(Collectors.toList());
        }

        public Pair<Boolean, String> approveOfficerRegistration(HDBManager manager, Registration reg) {
            if (!reg.project.manager.equals(manager.name)) {
                return new Pair<>(false, "Not the manager of this project.");
            }
            if (!"PENDING".equals(reg.status)) {
                return new Pair<>(false, "Registration is not PENDING (Current: " + reg.status + ").");
            }
            if (reg.project.officers.size() >= reg.project.officerSlot) {
                return new Pair<>(false, "No available officer slots for project " + reg.project.projectName + " (Slots: " + reg.project.officerSlot + ").");
            }
            reg.status = "APPROVED";
            reg.officer.myProjects.add(reg.project);
            reg.project.officers.add(reg.officer.name);
            return new Pair<>(true, "Officer " + reg.officer.name + " approved for project " + reg.project.projectName + ".");
        }

        public Pair<Boolean, String> rejectOfficerRegistration(HDBManager manager, Registration reg) {
            if (!reg.project.manager.equals(manager.name)) {
                return new Pair<>(false, "Not the manager of this project.");
            }
            if (!"PENDING".equals(reg.status)) {
                return new Pair<>(false, "Registration is not PENDING (Current: " + reg.status + ").");
            }
            reg.status = "REJECTED";
            reg.officer.myProjects.remove(reg.project);
            reg.project.officers.remove(reg.officer.name);
            return new Pair<>(true, "Officer registration for " + reg.officer.name + " rejected for project " + reg.project.projectName + ".");
        }
    }

    static class EnquiriesController {
        public List<Enquiry> enquiries = new ArrayList<>();

        public Pair<Boolean, String> createEnquiry(Applicant applicant, Project project, String text) {
            if (text == null || text.trim().isEmpty()) {
                 return new Pair<>(false, "Enquiry text cannot be empty.");
            }
            enquiries.add(new Enquiry(applicant, project, text));
            return new Pair<>(true, "Enquiry submitted successfully.");
        }

        public List<Pair<Integer, Enquiry>> getEnquiriesByApplicant(Applicant applicant) {
            List<Pair<Integer, Enquiry>> result = new ArrayList<>();
            for (int i = 0; i < enquiries.size(); i++) {
                Enquiry e = enquiries.get(i);
                if (e.applicant.equals(applicant)) {
                    result.add(new Pair<>(i, e));
                }
            }
            return result;
        }

        public Pair<Boolean, String> editEnquiry(Enquiry enquiry, String newText) {
             if (newText == null || newText.trim().isEmpty()) {
                 return new Pair<>(false, "New enquiry text cannot be empty.");
             }
             if (enquiry.text.contains("[Officer Reply:") || enquiry.text.contains("[Manager Reply:")) {
             }
            enquiry.text = newText;
            return new Pair<>(true, "Enquiry updated successfully.");
        }

        public Pair<Boolean, String> deleteEnquiry(Enquiry enquiry) {
            if (enquiries.remove(enquiry)) {
                return new Pair<>(true, "Enquiry deleted successfully.");
            }
            return new Pair<>(false, "Enquiry not found (internal error?).");
        }

        public Pair<Boolean, String> replyToProjectEnquiry(HDBOfficer officer, int idx, String replyText) {
            if (officer.myProjects.isEmpty()) {
                return new Pair<>(false, "You do not handle any projects.");
            }
            if (idx < 0 || idx >= enquiries.size()) {
                return new Pair<>(false, "Invalid enquiry index.");
            }
             if (replyText == null || replyText.trim().isEmpty()) {
                 return new Pair<>(false, "Reply text cannot be empty.");
             }

            Enquiry e = enquiries.get(idx);
            if (officer.myProjects.contains(e.project)) {
                e.text += "\n[Officer Reply (" + officer.name + " @ " + LocalDate.now().format(DATE_FORMATTER) + "): " + replyText + "]";
                return new Pair<>(true, "Reply appended to enquiry " + idx + ".");
            }
            return new Pair<>(false, "You do not handle the project (" + e.project.projectName + ") for this enquiry.");
        }

        public String viewAllEnquiries() {
            if (enquiries.isEmpty()) {
                return "No enquiries submitted system-wide.";
            }
            StringBuilder msg = new StringBuilder("All Enquiries:\n");
            for (int i = 0; i < enquiries.size(); i++) {
                Enquiry e = enquiries.get(i);
                msg.append(i).append(". Project: ").append(e.project.projectName)
                   .append(", From: ").append(e.applicant.name)
                   .append(" (").append(e.applicant.nric).append(")")
                   .append("\n   Text: ").append(e.text.replace("\n", "\n         "))
                   .append("\n");
            }
            return msg.toString();
        }

        public Pair<Boolean, String> replyToEnquiry(int idx, String replyText) {
            if (idx < 0 || idx >= enquiries.size()) {
                return new Pair<>(false, "Invalid enquiry index.");
            }
             if (replyText == null || replyText.trim().isEmpty()) {
                 return new Pair<>(false, "Reply text cannot be empty.");
             }
            Enquiry e = enquiries.get(idx);
            e.text += "\n[Manager Reply (@ " + LocalDate.now().format(DATE_FORMATTER) + "): " + replyText + "]";
            return new Pair<>(true, "Manager reply appended to enquiry " + idx + ".");
        }
    }

    static class UsersController {
        public List<User> users = new ArrayList<>();

        public UsersController(String applicantCsv, String hdbOfficerCsv, String hdbManagerCsv) {
            loadUsers(applicantCsv, "Applicant");
            loadUsers(hdbOfficerCsv, "HDBOfficer");
            loadUsers(hdbManagerCsv, "HDBManager");
        }

        private void loadUsers(String csvFile, String userType) {
            File file = new File(csvFile);
            try (Scanner scanner = new Scanner(file)) {
                if (scanner.hasNextLine()) {
                    scanner.nextLine();
                }
                while (scanner.hasNextLine()) {
                    String line = scanner.nextLine().trim();
                     if (line.isEmpty()) continue;
                    String[] parts = line.split(",");
                    if (parts.length < 5) {
                         System.err.println("Warning: Skipping malformed user line in " + csvFile + ": " + line);
                         continue;
                    }
                    String name = parts[0];
                    String nric = parts[1];
                    String age = parts[2];
                    String ms = parts[3];
                    String pwd = parts[4];

                    User user = null;
                    switch (userType) {
                        case "Applicant":
                            user = new Applicant(name, nric, age, ms, pwd);
                            break;
                        case "HDBOfficer":
                            user = new HDBOfficer(name, nric, age, ms, pwd);
                            break;
                        case "HDBManager":
                            user = new HDBManager(name, nric, age, ms, pwd);
                            break;
                    }
                    if (user != null) {
                        boolean exists = users.stream().anyMatch(u -> u.nric.equals(nric));
                        if (!exists) {
                            users.add(user);
                        } else {
                             System.err.println("Warning: Duplicate NRIC found, skipping user: " + nric + " from file " + csvFile);
                        }
                    }
                }
            } catch (FileNotFoundException e) {
                System.err.println("Error: User CSV file not found: " + csvFile);
            }
        }

        public User login(String nric, String password) {
            if (nric == null || nric.length() != 9 || !Character.isLetter(nric.charAt(0)) || !Character.isLetter(nric.charAt(8))) {
                 System.out.println("Invalid NRIC format. Must be 9 characters, start/end with a letter.");
                return null;
            }
            for (int i = 1; i < 8; i++) {
                if (!Character.isDigit(nric.charAt(i))) {
                     System.out.println("Invalid NRIC format. Middle 7 characters must be digits.");
                    return null;
                }
            }

            for (User user : users) {
                if (user.nric.equalsIgnoreCase(nric) && user.password.equals(password)) {
                    return user;
                }
            }
            return null;
        }

        public static String getUserType(User user) {
            if (user instanceof HDBManager) {
                return "HDB Manager";
            } else if (user instanceof HDBOfficer) {
                return "HDB Officer";
            } else if (user instanceof Applicant) {
                return "Applicant";
            }
            return "Unknown User Type";
        }
    }

    static class Pair<U, V> {
        public final U first;
        public final V second;

        public Pair(U first, V second) {
            this.first = first;
            this.second = second;
        }
    }


    public static void main(String[] args) {
        Scanner inputScanner = new Scanner(System.in);
        UsersController usersController = new UsersController("ApplicantList.csv", "OfficerList.csv", "ManagerList.csv");
        ProjectsController projectsController = new ProjectsController("ProjectList.csv");
        ApplicationsController applicationsController = new ApplicationsController();
        EnquiriesController enquiriesController = new EnquiriesController();
        RegistrationsController registrationsController = new RegistrationsController();

        User currentUser = null;

        System.out.println("--- Welcome to the HDB Application System ---");

        while (true) {
            while (currentUser == null) {
                System.out.print("Enter NRIC: ");
                String nric = inputScanner.nextLine().trim();
                System.out.print("Enter password: ");
                String pwd = inputScanner.nextLine().trim();
                currentUser = usersController.login(nric, pwd);
                if (currentUser == null) {
                    System.out.println("Invalid NRIC or password. Please try again.");
                } else {
                     System.out.println("\nLogin successful!");
                }
            }

            System.out.println("\nWelcome, " + currentUser.name + " (" + UsersController.getUserType(currentUser) + ")");
            while (currentUser != null) {
                List<String> menuOptions = currentUser.menu();
                System.out.println("\n--- Menu ---");
                for (int i = 0; i < menuOptions.size(); i++) {
                    System.out.println((i + 1) + ". " + menuOptions.get(i));
                }
                System.out.print("Enter choice: ");
                String choiceStr = inputScanner.nextLine().trim();
                int choice = -1;
                try {
                    choice = Integer.parseInt(choiceStr);
                } catch (NumberFormatException e) {
                    System.out.println("Invalid input. Please enter a number.");
                    continue;
                }

                if (choice < 1 || choice > menuOptions.size()) {
                    System.out.println("Invalid choice number.");
                    continue;
                }

                String selectedOption = menuOptions.get(choice - 1);
                System.out.println("\n>> Executing: " + selectedOption);

                try {
                    switch (selectedOption) {
                        case "View Projects":
                            if (currentUser instanceof Applicant) {
                                List<String> projs = ((Applicant) currentUser).getProjectsForApplicant(projectsController, applicationsController);
                                if (projs.isEmpty()) {
                                    System.out.println("No projects available to view.");
                                } else {
                                    projs.forEach(System.out::println);
                                }
                            }
                            break;

                        case "Apply for Projects":
                             if (currentUser instanceof Applicant && !(currentUser instanceof HDBManager)) {
                                System.out.print("Enter Project ID to apply for: ");
                                int pid = Integer.parseInt(inputScanner.nextLine().trim());
                                if (pid < 0 || pid >= projectsController.projects.size()) {
                                    System.out.println("Invalid Project ID.");
                                    break;
                                }
                                System.out.print("Enter flat type (2 for 2-Room, 3 for 3-Room): ");
                                int ft = Integer.parseInt(inputScanner.nextLine().trim());

                                Pair<Boolean, String> result = ((Applicant) currentUser).applyForProject(projectsController.projects.get(pid), ft, applicationsController);
                                System.out.println(result.second);
                            } else {
                                 System.out.println("Only Applicants/Officers can apply. Managers cannot apply.");
                            }
                            break;

                        case "View Application Status (Book)":
                             if (currentUser instanceof Applicant) {
                                Application app = applicationsController.getOngoingApplications((Applicant) currentUser);
                                if (app == null) {
                                    System.out.println("No ongoing applications found.");
                                } else {
                                    System.out.println("Project: " + app.project.projectName);
                                    System.out.println("Flat Type: " + app.flatType + "-Room");
                                    System.out.println("Status: " + app.status + " (Withdrawal Requested: " + app.requestWithdraw + ", Booking Requested: " + app.requestedBooking + ")");
                                    if ("SUCCESSFUL".equals(app.status) && !app.requestedBooking) {
                                        System.out.print("Your application is successful. Request booking slot now? (y/n): ");
                                        String c2 = inputScanner.nextLine().trim().toLowerCase();
                                        if ("y".equals(c2)) {
                                            Pair<Boolean, String> bookResult = applicationsController.requestBooking((Applicant) currentUser, app);
                                            System.out.println(bookResult.second);
                                        }
                                    } else if ("SUCCESSFUL".equals(app.status) && app.requestedBooking) {
                                         System.out.println("You have already requested a booking slot. Please wait for an officer to process it.");
                                    }
                                }
                            }
                            break;

                        case "Request Withdrawal":
                             if (currentUser instanceof Applicant) {
                                Application app = applicationsController.getOngoingApplications((Applicant) currentUser);
                                if (app == null) {
                                    System.out.println("No ongoing applications to withdraw.");
                                } else {
                                    applicationsController.requestWithdraw(app);
                                    System.out.println("Withdrawal requested for application for project: " + app.project.projectName + ". A manager needs to approve this.");
                                }
                            }
                            break;

                        case "Submit Enquiry":
                             if (currentUser instanceof Applicant) {
                                System.out.print("Enter Project ID for enquiry: ");
                                int pid = Integer.parseInt(inputScanner.nextLine().trim());
                                if (pid < 0 || pid >= projectsController.projects.size()) {
                                    System.out.println("Invalid Project ID.");
                                    break;
                                }
                                System.out.print("Enter your enquiry text: ");
                                String txt = inputScanner.nextLine().trim();
                                Pair<Boolean, String> result = ((Applicant) currentUser).submitEnquiry(projectsController.projects.get(pid), txt, enquiriesController);
                                System.out.println(result.second);
                            }
                            break;

                        case "View My Enquiries":
                             if (currentUser instanceof Applicant) {
                                System.out.println(((Applicant) currentUser).viewMyEnquiries(enquiriesController));
                            }
                            break;

                        case "Edit My Enquiry":
                             if (currentUser instanceof Applicant) {
                                System.out.print("Enter Enquiry index to edit: ");
                                int idx = Integer.parseInt(inputScanner.nextLine().trim());
                                System.out.print("Enter new enquiry text: ");
                                String newTxt = inputScanner.nextLine().trim();
                                Pair<Boolean, String> result = ((Applicant) currentUser).editMyEnquiry(enquiriesController, idx, newTxt);
                                System.out.println(result.second);
                            }
                            break;

                        case "Delete My Enquiry":
                             if (currentUser instanceof Applicant) {
                                System.out.print("Enter Enquiry index to delete: ");
                                int idx = Integer.parseInt(inputScanner.nextLine().trim());
                                Pair<Boolean, String> result = ((Applicant) currentUser).deleteMyEnquiry(enquiriesController, idx);
                                System.out.println(result.second);
                            }
                            break;

                        case "Register for Project as Officer":
                            if (currentUser instanceof HDBOfficer) {
                                System.out.print("Enter Project ID to register for: ");
                                int pid = Integer.parseInt(inputScanner.nextLine().trim());
                                if (pid < 0 || pid >= projectsController.projects.size()) {
                                    System.out.println("Invalid Project ID.");
                                    break;
                                }
                                Pair<Boolean, String> result = ((HDBOfficer) currentUser).registerForProject(projectsController.projects.get(pid), registrationsController);
                                System.out.println(result.second);
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "View My Officer Registrations":
                            if (currentUser instanceof HDBOfficer) {
                                System.out.println(((HDBOfficer) currentUser).viewOfficerRegistrations());
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "Reply to Project Enquiry (Handled Project)":
                            if (currentUser instanceof HDBOfficer) {
                                System.out.print("Enter Enquiry index to reply to: ");
                                int idx = Integer.parseInt(inputScanner.nextLine().trim());
                                System.out.print("Enter your reply text: ");
                                String rep = inputScanner.nextLine().trim();
                                Pair<Boolean, String> result = ((HDBOfficer) currentUser).replyEnquiry(idx, rep, enquiriesController);
                                System.out.println(result.second);
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "Book a Flat for Applicant (Handled Project)":
                            if (currentUser instanceof HDBOfficer) {
                                System.out.print("Enter applicant NRIC to book flat for: ");
                                String anric = inputScanner.nextLine().trim();
                                Pair<Boolean, String> result = ((HDBOfficer) currentUser).bookFlatForApplicant(anric, applicationsController);
                                System.out.println(result.second);
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "Generate Booking Receipt":
                             if (currentUser instanceof HDBOfficer) {
                                System.out.print("Enter applicant NRIC to generate receipt for: ");
                                String anric = inputScanner.nextLine().trim();
                                Pair<Boolean, String> result = ((HDBOfficer) currentUser).generateReceipt(anric, applicationsController);
                                System.out.println(result.second);
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "Create Project":
                            if (currentUser instanceof HDBManager) {
                                HDBManager manager = (HDBManager) currentUser;
                                System.out.print("Project Name: "); String name = inputScanner.nextLine().trim();
                                System.out.print("Neighborhood: "); String neigh = inputScanner.nextLine().trim();
                                System.out.print("Number of 2-Room units: "); int n1 = Integer.parseInt(inputScanner.nextLine().trim());
                                System.out.print("Price for 2-Room: "); int p1 = Integer.parseInt(inputScanner.nextLine().trim());
                                System.out.print("Number of 3-Room units: "); int n2 = Integer.parseInt(inputScanner.nextLine().trim());
                                System.out.print("Price for 3-Room: "); int p2 = Integer.parseInt(inputScanner.nextLine().trim());
                                System.out.print("Opening date (yyyy-mm-dd): "); String odStr = inputScanner.nextLine().trim();
                                System.out.print("Closing date (yyyy-mm-dd): "); String cdStr = inputScanner.nextLine().trim();
                                System.out.print("Number of officer slots: "); int slot = Integer.parseInt(inputScanner.nextLine().trim());

                                LocalDate newOdDate = null, newCdDate = null;
                                try {
                                    newOdDate = LocalDate.parse(odStr, DATE_FORMATTER);
                                    newCdDate = LocalDate.parse(cdStr, DATE_FORMATTER);
                                    if (newCdDate.isBefore(newOdDate)) {
                                        System.out.println("Error: Closing date cannot be before opening date.");
                                        break;
                                    }
                                } catch (DateTimeParseException e) {
                                    System.out.println("Invalid date format. Use yyyy-mm-dd. Project not created.");
                                    break;
                                }

                                boolean managerHasOverlap = false;
                                for (Project existing : projectsController.projects) {
                                    if (existing.manager.equals(manager.name)) {
                                        LocalDate existOd = existing.getOpeningLocalDate();
                                        LocalDate existCd = existing.getClosingLocalDate();
                                        if (existOd != null && existCd != null && datesOverlap(newOdDate, newCdDate, existOd, existCd)) {
                                            System.out.println("Error: Cannot create project. The application period overlaps with your existing project '" + existing.projectName + "' (" + existing.openingDate + " to " + existing.closingDate + ").");
                                            managerHasOverlap = true;
                                            break;
                                        }
                                    }
                                }

                                if (!managerHasOverlap) {
                                    Pair<Boolean, Project> result = manager.createProject(name, neigh, n1, p1, n2, p2, odStr, cdStr, slot, projectsController);
                                    if (result.first) {
                                        projectsController.projects.add(result.second);
                                        System.out.println("Project '" + result.second.projectName + "' created successfully.");
                                    } else {
                                        System.out.println("Project creation failed: " + result.second);
                                    }
                                }
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "Edit Project":
                             if (currentUser instanceof HDBManager) {
                                HDBManager manager = (HDBManager) currentUser;
                                System.out.print("Enter Project ID to edit: ");
                                int pid = Integer.parseInt(inputScanner.nextLine().trim());
                                if (pid < 0 || pid >= projectsController.projects.size()) {
                                    System.out.println("Invalid Project ID.");
                                    break;
                                }
                                Project p = projectsController.projects.get(pid);
                                if (!p.manager.equals(manager.name)) {
                                     System.out.println("Error: You are not the manager of this project.");
                                     break;
                                }

                                System.out.println("Editing Project: " + p.projectName + " (Enter new value or leave blank to keep current)");
                                System.out.print("New Name [" + p.projectName + "]: "); String newName = inputScanner.nextLine().trim();
                                System.out.print("New Neighborhood [" + p.neighborhood + "]: "); String newNeigh = inputScanner.nextLine().trim();
                                System.out.print("New Num 2-Room [" + p.numUnits1 + "] (-1 to keep): "); String n1Str = inputScanner.nextLine().trim();
                                System.out.print("New Price 2-Room [" + p.price1 + "] (-1 to keep): "); String p1Str = inputScanner.nextLine().trim();
                                System.out.print("New Num 3-Room [" + p.numUnits2 + "] (-1 to keep): "); String n2Str = inputScanner.nextLine().trim();
                                System.out.print("New Price 3-Room [" + p.price2 + "] (-1 to keep): "); String p2Str = inputScanner.nextLine().trim();
                                System.out.print("New Open Date (yyyy-mm-dd) [" + p.openingDate + "]: "); String newOdStr = inputScanner.nextLine().trim();
                                System.out.print("New Close Date (yyyy-mm-dd) [" + p.closingDate + "]: "); String newCdStr = inputScanner.nextLine().trim();
                                System.out.print("New Officer Slots [" + p.officerSlot + "] (-1 to keep): "); String slotStr = inputScanner.nextLine().trim();

                                Integer newN1 = n1Str.equals("-1") || n1Str.isEmpty() ? null : Integer.parseInt(n1Str);
                                Integer newP1 = p1Str.equals("-1") || p1Str.isEmpty() ? null : Integer.parseInt(p1Str);
                                Integer newN2 = n2Str.equals("-1") || n2Str.isEmpty() ? null : Integer.parseInt(n2Str);
                                Integer newP2 = p2Str.equals("-1") || p2Str.isEmpty() ? null : Integer.parseInt(p2Str);
                                Integer newSlots = slotStr.equals("-1") || slotStr.isEmpty() ? null : Integer.parseInt(slotStr);

                                String finalOdStr = newOdStr.isEmpty() ? p.openingDate : newOdStr;
                                String finalCdStr = newCdStr.isEmpty() ? p.closingDate : newCdStr;
                                LocalDate finalOdDate = null, finalCdDate = null;

                                try {
                                    finalOdDate = LocalDate.parse(finalOdStr, DATE_FORMATTER);
                                    finalCdDate = LocalDate.parse(finalCdStr, DATE_FORMATTER);
                                     if (finalCdDate.isBefore(finalOdDate)) {
                                        System.out.println("Error: Closing date cannot be before opening date.");
                                        break;
                                    }
                                } catch (DateTimeParseException e) {
                                    System.out.println("Invalid date format entered. Use yyyy-mm-dd. Project not edited.");
                                    break;
                                }

                                boolean managerHasOverlap = false;
                                for (Project existing : projectsController.projects) {
                                    if (!existing.equals(p) && existing.manager.equals(manager.name)) {
                                        LocalDate existOd = existing.getOpeningLocalDate();
                                        LocalDate existCd = existing.getClosingLocalDate();
                                        if (existOd != null && existCd != null && datesOverlap(finalOdDate, finalCdDate, existOd, existCd)) {
                                            System.out.println("Error: Cannot edit project. The new application period overlaps with your other project '" + existing.projectName + "' (" + existing.openingDate + " to " + existing.closingDate + ").");
                                            managerHasOverlap = true;
                                            break;
                                        }
                                    }
                                }

                                if (!managerHasOverlap) {
                                     Pair<Boolean, String> result = manager.editProject(p,
                                         (newName.isEmpty() ? null : newName),
                                         (newNeigh.isEmpty() ? null : newNeigh),
                                         newN1, newP1, newN2, newP2,
                                         (newOdStr.isEmpty() ? null : newOdStr),
                                         (newCdStr.isEmpty() ? null : newCdStr),
                                         newSlots,
                                         projectsController);
                                     System.out.println(result.second);
                                }

                            } else { System.out.println("Permission denied."); }
                            break;

                        case "Delete Project":
                             if (currentUser instanceof HDBManager) {
                                System.out.print("Enter Project ID to delete: ");
                                int pid = Integer.parseInt(inputScanner.nextLine().trim());
                                if (pid < 0 || pid >= projectsController.projects.size()) {
                                    System.out.println("Invalid Project ID.");
                                    break;
                                }
                                Project p = projectsController.projects.get(pid);
                                System.out.print("Are you sure you want to delete project '" + p.projectName + "'? This cannot be undone. (y/n): ");
                                if (inputScanner.nextLine().trim().equalsIgnoreCase("y")) {
                                     Pair<Boolean, String> result = ((HDBManager) currentUser).deleteProject(p, projectsController);
                                     System.out.println(result.second);
                                } else {
                                     System.out.println("Deletion cancelled.");
                                }
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "Toggle Project Visibility":
                             if (currentUser instanceof HDBManager) {
                                System.out.print("Enter Project ID to toggle visibility: ");
                                int pid = Integer.parseInt(inputScanner.nextLine().trim());
                                if (pid < 0 || pid >= projectsController.projects.size()) {
                                    System.out.println("Invalid Project ID.");
                                    break;
                                }
                                Project p = projectsController.projects.get(pid);
                                Pair<Boolean, String> result = ((HDBManager) currentUser).toggleProjectVisibility(p, projectsController);
                                System.out.println(result.second);
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "View All Projects":
                            if (currentUser instanceof HDBManager) {
                                System.out.println(((HDBManager) currentUser).viewAllProjects(projectsController));
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "View My Projects":
                            if (currentUser instanceof HDBManager) {
                                System.out.println(((HDBManager) currentUser).viewMyProjects(projectsController));
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "View Officer Registrations":
                            if (currentUser instanceof HDBManager) {
                                System.out.println(((HDBManager) currentUser).viewOfficerRegistrations(registrationsController));
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "Approve Officer Registration":
                             if (currentUser instanceof HDBManager) {
                                System.out.println(((HDBManager) currentUser).viewOfficerRegistrations(registrationsController));
                                List<Registration> regs = registrationsController.getAllRegistrationsForManager(currentUser.name);
                                if (regs.isEmpty()) break;
                                System.out.print("Enter Registration index to approve: ");
                                int idx = Integer.parseInt(inputScanner.nextLine().trim());
                                if (idx >= 0 && idx < regs.size()) {
                                     Pair<Boolean, String> result = ((HDBManager) currentUser).approveOfficerRegistration(regs.get(idx), registrationsController);
                                     System.out.println(result.second);
                                } else {
                                    System.out.println("Invalid index.");
                                }
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "Reject Officer Registration":
                             if (currentUser instanceof HDBManager) {
                                System.out.println(((HDBManager) currentUser).viewOfficerRegistrations(registrationsController));
                                List<Registration> regs = registrationsController.getAllRegistrationsForManager(currentUser.name);
                                 if (regs.isEmpty()) break;
                                System.out.print("Enter Registration index to reject: ");
                                int idx = Integer.parseInt(inputScanner.nextLine().trim());
                                if (idx >= 0 && idx < regs.size()) {
                                     Pair<Boolean, String> result = ((HDBManager) currentUser).rejectOfficerRegistration(regs.get(idx), registrationsController);
                                     System.out.println(result.second);
                                } else {
                                    System.out.println("Invalid index.");
                                }
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "View Applications":
                            if (currentUser instanceof HDBManager) {
                                System.out.println(((HDBManager) currentUser).viewApplications(applicationsController));
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "Approve Application":
                             if (currentUser instanceof HDBManager) {
                                System.out.println(((HDBManager) currentUser).viewApplications(applicationsController));
                                if (applicationsController.applications.isEmpty()) break;
                                System.out.print("Enter Application index to approve: ");
                                int idx = Integer.parseInt(inputScanner.nextLine().trim());
                                if (idx >= 0 && idx < applicationsController.applications.size()) {
                                     Pair<Boolean, String> result = ((HDBManager) currentUser).approveApplication(applicationsController.applications.get(idx), applicationsController);
                                     System.out.println(result.second);
                                } else {
                                    System.out.println("Invalid index.");
                                }
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "Reject Application":
                             if (currentUser instanceof HDBManager) {
                                System.out.println(((HDBManager) currentUser).viewApplications(applicationsController));
                                if (applicationsController.applications.isEmpty()) break;
                                System.out.print("Enter Application index to reject: ");
                                int idx = Integer.parseInt(inputScanner.nextLine().trim());
                                if (idx >= 0 && idx < applicationsController.applications.size()) {
                                     Pair<Boolean, String> result = ((HDBManager) currentUser).rejectApplication(applicationsController.applications.get(idx), applicationsController);
                                     System.out.println(result.second);
                                } else {
                                    System.out.println("Invalid index.");
                                }
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "Approve Withdrawal":
                             if (currentUser instanceof HDBManager) {
                                System.out.println(((HDBManager) currentUser).viewApplications(applicationsController));
                                if (applicationsController.applications.isEmpty()) break;
                                System.out.print("Enter Application index to approve withdrawal for: ");
                                int idx = Integer.parseInt(inputScanner.nextLine().trim());
                                if (idx >= 0 && idx < applicationsController.applications.size()) {
                                     Pair<Boolean, String> result = ((HDBManager) currentUser).approveWithdrawal(applicationsController.applications.get(idx), applicationsController);
                                     System.out.println(result.second);
                                } else {
                                    System.out.println("Invalid index.");
                                }
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "Generate Booking Report":
                            if (currentUser instanceof HDBManager) {
                                System.out.print("Filter by marital status? (Single/Married/Leave blank for None): ");
                                String filterM = inputScanner.nextLine().trim();
                                System.out.println(((HDBManager) currentUser).generateBookingReport(applicationsController, filterM));
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "View All Enquiries":
                            if (currentUser instanceof HDBManager) {
                                System.out.println(((HDBManager) currentUser).viewAllEnquiries(enquiriesController));
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "Reply to Enquiry":
                            if (currentUser instanceof HDBManager) {
                                System.out.println(((HDBManager) currentUser).viewAllEnquiries(enquiriesController));
                                if (enquiriesController.enquiries.isEmpty()) break;
                                System.out.print("Enter Enquiry index to reply to: ");
                                int idx = Integer.parseInt(inputScanner.nextLine().trim());
                                System.out.print("Enter your reply text: ");
                                String rep = inputScanner.nextLine().trim();
                                Pair<Boolean, String> result = ((HDBManager) currentUser).replyToEnquiry(idx, rep, enquiriesController);
                                System.out.println(result.second);
                            } else { System.out.println("Permission denied."); }
                            break;

                        case "Change Password":
                            System.out.print("Enter your current password: ");
                            String oldPwd = inputScanner.nextLine().trim();
                            if (oldPwd.equals(currentUser.password)) {
                                System.out.print("Enter your new password: ");
                                String newPwd = inputScanner.nextLine().trim();
                                System.out.print("Confirm your new password: ");
                                String confirmPwd = inputScanner.nextLine().trim();
                                if (newPwd.equals(confirmPwd)) {
                                    if (newPwd.isEmpty()) {
                                         System.out.println("Password cannot be empty.");
                                    } else {
                                         currentUser.password = newPwd;
                                         System.out.println("Password changed successfully.");
                                    }
                                } else {
                                    System.out.println("New passwords do not match. Password not changed.");
                                }
                            } else {
                                System.out.println("Incorrect current password. Password not changed.");
                            }
                            break;

                        case "Logout":
                            System.out.println("Logging out " + currentUser.name + "...");
                            currentUser = null;
                            break;

                        default:
                            System.out.println("This option is not implemented yet.");
                            break;
                    }
                } catch (NumberFormatException e) {
                    System.out.println("Invalid number input: " + e.getMessage());
                } catch (IndexOutOfBoundsException e) {
                     System.out.println("Invalid index entered: " + e.getMessage());
                } catch (Exception e) {
                    System.err.println("An unexpected error occurred: " + e.getMessage());
                    e.printStackTrace();
                }

                if (currentUser != null) {
                    System.out.println("\nPress Enter to continue...");
                    inputScanner.nextLine();
                }
            }
        }
    }
}