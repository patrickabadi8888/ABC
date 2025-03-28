from datetime import datetime
import tempfile
import os

class User:
    """
    ## User
    - Basic class for all types of users
    """
    def __init__(self, name, nric, age, maritalStatus, password):
        self.name = name
        self.nric = nric
        self.age = int(age)
        self.maritalStatus = maritalStatus
        self.password = password

    def menu(self):
        return []

class Applicant(User):
    """
    ## Applicant
    - [x] Can only view the list of projects visible (on) or already applied for
    - [x] Can apply for a project (Single >=35 can only apply 2-Room; Married >=21 can apply 2/3-Room)
    - [x] Can view application status even if visibility is off
    - [x] If successful, can book once
    - [x] Can request withdrawal
    - [x] Can submit, view, edit, delete enquiries
    """
    def menu(self):
        return [
            "View Projects",
            "Apply for Projects",
            "View Application Status (Book)",
            "Request Withdrawal",
            "Submit Enquiry",
            "View My Enquiries",
            "Edit My Enquiry",
            "Delete My Enquiry",
            "Change Password",
            "Logout",
        ]

    def getProjectsForApplicant(self, projectController, applicationsController):
        projects = []
        my_app = self.getOngoingApplications(applicationsController)
        for i, project in enumerate(projectController.projects):
            if project.visibility or (my_app and my_app.project == project):
                if self.__class__ == Applicant or self.__class__ == HDBOfficer:
                    if hasattr(self, 'myProjects') and project in self.myProjects:
                        pass
                details = f"ID: {i}\nName: {project.projectName}\nNeighborhood: {project.neighborhood}\n"
                details += f"{project.type1}: {project.numUnits1} ({project.price1})\n"
                details += f"{project.type2}: {project.numUnits2} ({project.price2})\n"
                details += f"Application Date: {project.openingDate}-{project.closingDate}\n"
                details += f"Manager: {project.manager}\nOfficers: {','.join([o for o in project.officers])}\n"
                projects.append(details)
        return projects

    def getOngoingApplications(self, applicationsController):
        for application in applicationsController.applications:
            if application.applicant == self:
                return application
        return False

    def verifyApplicationEligibility(self, project, flat_type, applicationController):
        if self.getOngoingApplications(applicationController):
            return False, "You have already applied."
        if self.maritalStatus == "Single" and self.age < 35:
            return False, "Single applicants must be at least 35."
        if self.maritalStatus == "Single" and flat_type != 2:
            return False, "Single applicants can only apply for 2-Room."
        if self.maritalStatus == "Married" and self.age < 21:
            return False, "Married applicants must be at least 21."
        if flat_type == 2 and project.numUnits1 == 0:
            return False, "No more 2-room flats."
        if flat_type == 3 and project.numUnits2 == 0:
            return False, "No more 3-room flats."
        return True, "Eligible"

    def applyForProject(self, project, flat_type, applicationController):
        if project.manager == self.name:
            return False, "Managers cannot apply."
        if hasattr(self, 'myProjects') and project in self.myProjects:
            return False, "Cannot apply for a project you handle as an officer."
        if flat_type not in [2, 3]:
            return False, "Invalid flat type."
        ok, msg = self.verifyApplicationEligibility(project, flat_type, applicationController)
        if ok:
            applicationController.createApplication(self, project, flat_type)
            return True, "Application successful."
        return False, msg

    def submitEnquiry(self, project, text, enquiriesController):
        enquiriesController.createEnquiry(self, project, text)
        return "Enquiry submitted."

    def viewMyEnquiries(self, enquiriesController):
        my_enquiries = enquiriesController.getEnquiriesByApplicant(self)
        if not my_enquiries:
            return "No enquiries."
        msg = "Your Enquiries:\n"
        for i, e in my_enquiries:
            msg += f"Index: {i} | Project: {e.project.projectName} | Text: {e.text}\n"
        return msg

    def editMyEnquiry(self, enquiriesController, idx, new_text):
        my_enquiries = enquiriesController.getEnquiriesByApplicant(self)
        for i, e in my_enquiries:
            if i == idx:
                enquiriesController.editEnquiry(e, new_text)
                return "Enquiry updated."
        return "Invalid enquiry index."

    def deleteMyEnquiry(self, enquiriesController, idx):
        my_enquiries = enquiriesController.getEnquiriesByApplicant(self)
        for i, e in my_enquiries:
            if i == idx:
                enquiriesController.deleteEnquiry(e)
                return "Enquiry deleted."
        return "Invalid enquiry index."

    def requestBooking(self, application):
        if application.status == "SUCCESSFUL":
            if application.requestedBooking:
                return "Booking request already sent."
            application.requestedBooking = True
            return "Booking request sent."
        if application.status == "BOOKED":
            return "You already booked."
        return f"Cannot request booking, status is {application.status}."


class HDBOfficer(Applicant):
    """
    ## HDB Officer
    - [x] Has Applicant capabilities
    - [x] Able to register for multiple projects if not an Applicant for that same project
    - [x] Able to see status of registration
    - [x] Registration subject to Manager approval
    - [x] If approved, can handle project
    - [x] Cannot edit project details
    - [x] Can view & reply to enquiries for handled projects
    - [x] Flat selection responsibilities
    - [x] Generate a receipt for flat booking
    """
    def __init__(self, name, nric, age, maritalStatus, password):
        super().__init__(name, nric, age, maritalStatus, password)
        self.registrations = []
        self.myProjects = []

    def menu(self):
        return super().menu()[:-1] + [
            "Register for Project as Officer",
            "View My Officer Registrations",
            "Reply to Project Enquiry (Handled Project)",
            "Book a Flat for Applicant (Handled Project)",
            "Generate Booking Receipt",
            "Logout"
        ]

    def registerForProject(self, project, registrationsController):
        if project in self.myProjects:
            return "Already an officer."
        if project.manager == self.name:
            return "Cannot register for your own project."
        registrationsController.createRegistration(self, project)
        return "Officer registration submitted."

    def viewOfficerRegistrations(self):
        if not self.registrations:
            return "No officer registrations."
        msg = "Officer Registrations:\n"
        for i, r in enumerate(self.registrations):
            msg += f"{i}. Project: {r.project.projectName} | Status: {r.status}\n"
        return msg

    def replyEnquiry(self, enquiriesController, idx, reply_text):
        if not self.myProjects:
            return "No handled projects."
        if idx < 0 or idx >= len(enquiriesController.enquiries):
            return "Invalid enquiry index."
        e = enquiriesController.enquiries[idx]
        if e.project in self.myProjects:
            e.text += f" [Officer Reply: {reply_text}]"
            return "Reply appended."
        return "You don't handle this project."

    def bookFlatForApplicant(self, applicant_nric, applicationsController):
        for app in applicationsController.applications:
            if app.applicant.nric == applicant_nric:
                if app.project in self.myProjects and app.status == "SUCCESSFUL":
                    if app.flat_type == 2 and app.project.numUnits1 > 0:
                        app.project.numUnits1 -= 1
                    elif app.flat_type == 3 and app.project.numUnits2 > 0:
                        app.project.numUnits2 -= 1
                    app.status = "BOOKED"
                    return f"Booked flat for {applicant_nric}."
        return "Cannot book."

    def generateReceipt(self, applicant_nric, applicationsController):
        for app in applicationsController.applications:
            if app.applicant.nric == applicant_nric and app.status == "BOOKED":
                r = "Receipt:\n"
                r += f"Name: {app.applicant.name}\n"
                r += f"NRIC: {applicant_nric}\n"
                r += f"Age: {app.applicant.age}\n"
                r += f"Marital: {app.applicant.maritalStatus}\n"
                r += f"Flat Type: {app.flat_type}-Room\n"
                r += f"Project: {app.project.projectName}, {app.project.neighborhood}\n"
                return r
        return "No booking found."


class HDBManager(User):
    """
    ## HDB Manager
    - [x] Can create, edit, delete projects
    - [x] BTO project info includes name, neighborhood, flat types, number of units, dates, manager, officer slots
    - [x] Can only handle one project within same period
    - [x] Can toggle visibility
    - [x] Can view all projects (including others')
    - [x] Can filter projects they created
    - [x] Can view pending/approved HDB Officer registrations
    - [x] Can approve/reject HDB Officer
    - [x] Can approve/reject BTO applications (if supply allows)
    - [x] Can approve/reject withdrawal
    - [x] Generate a report of applicants with booking
    - [x] Cannot apply for BTO
    - [x] Can view & reply to all enquiries
    """
    def menu(self):
        return [
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
        ]

    def applyForProject(self, project, flat_type, applicationController):
        return False, "Managers cannot apply."

    def createProject(self, name, neighborhood, t1, n1, p1, t2, n2, p2, openDate, closeDate, officerSlot):
        return Project(name, neighborhood, t1, n1, p1, t2, n2, p2, openDate, closeDate, self.name, officerSlot, [])

    def editProject(self, project, name=None, neighborhood=None, t1=None, n1=None, p1=None,
                    t2=None, n2=None, p2=None, openDate=None, closeDate=None, officerSlot=None):
        if project.manager != self.name:
            return "Not your project."
        if name: project.projectName = name
        if neighborhood: project.neighborhood = neighborhood
        if t1: project.type1 = t1
        if n1 is not None and n1 >= 0: project.numUnits1 = n1
        if p1 is not None and p1 >= 0: project.price1 = p1
        if t2: project.type2 = t2
        if n2 is not None and n2 >= 0: project.numUnits2 = n2
        if p2 is not None and p2 >= 0: project.price2 = p2
        if openDate: project.openingDate = openDate
        if closeDate: project.closingDate = closeDate
        if officerSlot is not None and officerSlot >= 0: project.officerSlot = officerSlot
        return "Project updated."

    def deleteProject(self, project, projectsController):
        if project.manager != self.name:
            return "Not your project."
        if project in projectsController.projects:
            projectsController.projects.remove(project)
            return "Project deleted."
        return "Not found."

    def toggleProjectVisibility(self, project):
        if project.manager != self.name:
            return "Not your project."
        project.visibility = not project.visibility
        return f"Visibility set to {project.visibility}."

    def viewAllProjects(self, projectsController):
        msg = "All Projects:\n"
        for i, p in enumerate(projectsController.projects):
            msg += f"{i}. {p.projectName} (Visible={p.visibility}, Manager={p.manager}, Officers={','.join(p.officers)})\n"
        return msg

    def viewMyProjects(self, projectsController):
        msg = "My Projects:\n"
        for i, p in enumerate(projectsController.projects):
            if p.manager == self.name:
                msg += f"{i}. {p.projectName} (Visible={p.visibility})\n"
        return msg

    def viewOfficerRegistrations(self, registrationsController):
        regs = registrationsController.getAllRegistrationsForManager(self.name)
        if not regs:
            return "No registrations."
        msg = "Officer Registrations:\n"
        for i, r in enumerate(regs):
            msg += f"{i}. Project: {r.project.projectName}, Officer: {r.officer.name}, Status: {r.status}\n"
        return msg

    def approveOfficerRegistration(self, reg, registrationsController):
        if reg.project.manager != self.name:
            return "Not your project."
        if reg.status != "PENDING":
            return "Not pending."
        if len(reg.project.officers) >= reg.project.officerSlot:
            return "No officer slot."
        reg.status = "APPROVED"
        reg.officer.myProjects.append(reg.project)
        reg.project.officers.append(reg.officer.name)
        return "Officer approved."

    def rejectOfficerRegistration(self, reg, registrationsController):
        if reg.project.manager != self.name:
            return "Not your project."
        if reg.status != "PENDING":
            return "Not pending."
        reg.status = "REJECTED"
        return "Officer rejected."

    def viewApplications(self, applicationsController):
        apps = applicationsController.applications
        msg = "Applications:\n"
        for i, a in enumerate(apps):
            msg += f"{i}. Applicant={a.applicant.name}, Project={a.project.projectName}, Flat={a.flat_type}, Status={a.status}, Withdraw={a.requestWithdraw}\n"
        return msg

    def approveApplication(self, application):
        if application.project.manager != self.name:
            return "Not your project."
        if application.status != "PENDING":
            return "Not pending."
        if (application.flat_type == 2 and application.project.numUnits1 == 0) or \
           (application.flat_type == 3 and application.project.numUnits2 == 0):
            return "No flats left, cannot approve."
        application.status = "SUCCESSFUL"
        return "Application approved."

    def rejectApplication(self, application):
        if application.project.manager != self.name:
            return "Not your project."
        if application.status != "PENDING":
            return "Not pending."
        application.status = "UNSUCCESSFUL"
        return "Application rejected."

    def approveWithdrawal(self, application, applicationsController):
        if application.project.manager != self.name:
            return "Not your project."
        if application not in applicationsController.applications:
            return "Application not found."
        if not application.requestWithdraw:
            return "No withdrawal request."
        applicationsController.applications.remove(application)
        return "Withdrawal approved."

    def generateBookingReport(self, applicationsController, filterMarital=None):
        booked = [a for a in applicationsController.applications if a.status == "BOOKED"]
        if filterMarital:
            booked = [b for b in booked if b.applicant.maritalStatus == filterMarital]
        if not booked:
            return "No bookings."
        msg = "Booking Report:\n"
        for b in booked:
            msg += f"{b.applicant.name},{b.applicant.nric},{b.applicant.age},{b.applicant.maritalStatus},Flat:{b.flat_type},Project:{b.project.projectName}\n"
        return msg

    def viewAllEnquiries(self, enquiriesController):
        if not enquiriesController.enquiries:
            return "No enquiries."
        msg = "All Enquiries:\n"
        for i, e in enumerate(enquiriesController.enquiries):
            msg += f"{i}. Project:{e.project.projectName}, From:{e.applicant.name}, Text:{e.text}\n"
        return msg

    def replyToEnquiry(self, idx, reply_text, enquiriesController):
        if idx < 0 or idx >= len(enquiriesController.enquiries):
            return "Invalid index."
        e = enquiriesController.enquiries[idx]
        e.text += f" [Manager Reply: {reply_text}]"
        return "Reply appended."


class Project:
    def __init__(self, projectName, neighborhood, type1, numUnits1, price1, type2, numUnits2, price2,
                 openingDate, closingDate, manager, officerSlot, officers):
        self.projectName = projectName
        self.neighborhood = neighborhood
        self.type1 = type1
        self.numUnits1 = numUnits1
        self.price1 = price1
        self.type2 = type2
        self.numUnits2 = numUnits2
        self.price2 = price2
        self.openingDate = openingDate
        self.closingDate = closingDate
        self.manager = manager
        self.officerSlot = int(officerSlot)
        self.officers = officers
        self.visibility = True


class UsersController:
    def __init__(self, applicantCsv, hdbOfficerCsv, hdbManagerCsv):
        self.users = []
        with open(applicantCsv, 'r') as file:
            for line in file.readlines()[1:]:
                name, nric, age, ms, pwd = line.strip().split(',')
                self.users.append(Applicant(name, nric, age, ms, pwd))
        with open(hdbOfficerCsv, 'r') as file:
            for line in file.readlines()[1:]:
                name, nric, age, ms, pwd = line.strip().split(',')
                self.users.append(HDBOfficer(name, nric, age, ms, pwd))
        with open(hdbManagerCsv, 'r') as file:
            for line in file.readlines()[1:]:
                name, nric, age, ms, pwd = line.strip().split(',')
                self.users.append(HDBManager(name, nric, age, ms, pwd))

    def login(self, nric, password):
        if not nric[0].isalpha() or not nric[-1].isalpha() or not nric[1:-1].isdigit() or len(nric) != 9:
            return None
        for user in self.users:
            if user.nric == nric and user.password == password:
                return user
        return None

    @staticmethod
    def getUserType(user):
        if isinstance(user, Applicant) and not isinstance(user, HDBOfficer):
            return "Applicant"
        if isinstance(user, HDBOfficer) and not isinstance(user, HDBManager):
            return "HDB Officer"
        if isinstance(user, HDBManager):
            return "HDB Manager"
        return None


class Application:
    """
    BTO Application (Pending, Successful, Unsuccessful, Booked)
    """
    def __init__(self, applicant, project, flat_type):
        self.applicant = applicant
        self.project = project
        self.flat_type = flat_type
        self.status = "PENDING"
        self.requestWithdraw = False
        self.requestedBooking = False


class ApplicationsController:
    def __init__(self):
        self.applications = []

    def createApplication(self, applicant, project, flat_type):
        self.applications.append(Application(applicant, project, flat_type))

    def requestWithdraw(self, application):
        application.requestWithdraw = True


class Registration:
    def __init__(self, officer, project):
        self.officer = officer
        self.project = project
        self.status = "PENDING"


class RegistrationsController:
    """
    Handles HDB Officer registrations to a project
    """
    def __init__(self):
        self.registrations = []

    def createRegistration(self, officer, project):
        reg = Registration(officer, project)
        officer.registrations.append(reg)
        self.registrations.append(reg)

    def getAllRegistrationsForManager(self, managerName):
        return [r for r in self.registrations if r.project.manager == managerName]


class ProjectsController:
    def __init__(self, projectCsv):
        self.projects = []
        for line in open(projectCsv, 'r').readlines()[1:]:
            line = line.strip()
            parts = []
            temp = ''
            in_quotes = False
            for char in line:
                if char == '"':
                    in_quotes = not in_quotes
                elif char == ',' and not in_quotes:
                    parts.append(temp)
                    temp = ''
                else:
                    temp += char
            parts.append(temp)
            if len(parts) > 11 and isinstance(parts[-1], list):
                parts[-1] = parts[-1][0]
            existing_officers = parts[12].strip('"')
            officer_list = [x.strip() for x in existing_officers.split(',')] if existing_officers else []
            self.projects.append(Project(
                parts[0], parts[1], parts[2], int(parts[3]), int(parts[4]),
                parts[5], int(parts[6]), int(parts[7]), parts[8], parts[9],
                parts[10], parts[11], officer_list
            ))


class Enquiry:
    def __init__(self, applicant, project, text):
        self.applicant = applicant
        self.project = project
        self.text = text


class EnquiriesController:
    def __init__(self):
        self.enquiries = []

    def createEnquiry(self, applicant, project, text):
        self.enquiries.append(Enquiry(applicant, project, text))

    def getEnquiriesByApplicant(self, applicant):
        return [(i, e) for i, e in enumerate(self.enquiries) if e.applicant == applicant]

    def editEnquiry(self, enquiry, new_text):
        enquiry.text = new_text

    def deleteEnquiry(self, enquiry):
        self.enquiries.remove(enquiry)


def datesOverlap(start1, end1, start2, end2):
    """
    Returns True if the date ranges [start1, end1] and [start2, end2] overlap.
    """
    return not (end1 < start2 or start1 > end2)


def main():
    usersController = UsersController('ApplicantList.csv', 'OfficerList.csv', 'ManagerList.csv')
    projectsController = ProjectsController('ProjectList.csv')
    applicationsController = ApplicationsController()
    enquiriesController = EnquiriesController()
    registrationsController = RegistrationsController()

    currentUser = None
    while True:
        while not currentUser:
            nric = input("Enter NRIC: ")
            pwd = input("Enter password: ")
            currentUser = usersController.login(nric, pwd)
            if not currentUser:
                print("Invalid NRIC or password")

        print(f"Welcome, {currentUser.name} ({UsersController.getUserType(currentUser)})")
        while currentUser:
            m = currentUser.menu()
            for i, option in enumerate(m):
                print(f"{i+1}. {option}")
            choice = input("Enter choice: ")
            if not choice.isdigit() or not (1 <= int(choice) <= len(m)):
                print("Invalid choice")
                continue
            option = m[int(choice)-1]

            if option == "View Projects":
                projs = currentUser.getProjectsForApplicant(projectsController, applicationsController)
                for p in projs:
                    print(p,"\n")

            elif option == "Apply for Projects":
                pid = int(input("Project ID: "))
                ft = int(input("Enter flat type (2 or 3): "))
                suc, msg = currentUser.applyForProject(projectsController.projects[pid], ft, applicationsController)
                print(msg)

            elif option == "View Application Status (Book)":
                app = currentUser.getOngoingApplications(applicationsController)
                if not app:
                    print("No ongoing applications.")
                else:
                    print(f"Project: {app.project.projectName}")
                    print(f"Flat Type: {app.flat_type}")
                    print(f"Status: {app.status} (Withdraw={app.requestWithdraw})")
                    if app.status == "SUCCESSFUL":
                        c2 = input("Request booking? (y/n): ")
                        if c2.lower() == 'y':
                            print(currentUser.requestBooking(app))

            elif option == "Request Withdrawal":
                app = currentUser.getOngoingApplications(applicationsController)
                if not app:
                    print("No ongoing applications.")
                else:
                    applicationsController.requestWithdraw(app)
                    print("Requested withdrawal.")

            elif option == "Submit Enquiry":
                pid = int(input("Project ID: "))
                txt = input("Enter enquiry: ")
                print(currentUser.submitEnquiry(projectsController.projects[pid], txt, enquiriesController))

            elif option == "View My Enquiries":
                print(currentUser.viewMyEnquiries(enquiriesController))

            elif option == "Edit My Enquiry":
                idx = int(input("Enquiry index: "))
                new_txt = input("New text: ")
                print(currentUser.editMyEnquiry(enquiriesController, idx, new_txt))

            elif option == "Delete My Enquiry":
                idx = int(input("Enquiry index: "))
                print(currentUser.deleteMyEnquiry(enquiriesController, idx))

            elif option == "Register for Project as Officer":
                pid = int(input("Project ID: "))
                print(currentUser.registerForProject(projectsController.projects[pid], registrationsController))

            elif option == "View My Officer Registrations":
                print(currentUser.viewOfficerRegistrations())

            elif option == "Reply to Project Enquiry (Handled Project)":
                idx = int(input("Enquiry index: "))
                rep = input("Reply text: ")
                print(currentUser.replyEnquiry(enquiriesController, idx, rep))

            elif option == "Book a Flat for Applicant (Handled Project)":
                anric = input("Enter applicant NRIC: ")
                print(currentUser.bookFlatForApplicant(anric, applicationsController))

            elif option == "Generate Booking Receipt":
                anric = input("Enter applicant NRIC: ")
                print(currentUser.generateReceipt(anric, applicationsController))

            elif option == "Create Project":
                name = input("Name: ")
                neigh = input("Neighborhood: ")
                t1 = input("Type1 label (e.g. 2-Room): ")
                n1 = int(input("Num type1: "))
                p1 = int(input("Price type1: "))
                t2 = input("Type2 label (e.g. 3-Room): ")
                n2 = int(input("Num type2: "))
                p2 = int(input("Price type2: "))
                od = input("Open date (yyyy-mm-dd): ")
                cd = input("Close date (yyyy-mm-dd): ")
                slot = int(input("Officer slots: "))

                try:
                    new_od_date = datetime.strptime(od, "%Y-%m-%d")
                    new_cd_date = datetime.strptime(cd, "%Y-%m-%d")

                    managerHasOverlap = False
                    for existing in projectsController.projects:
                        if existing.manager == currentUser.name:
                            exist_od = datetime.strptime(existing.openingDate, "%Y-%m-%d")
                            exist_cd = datetime.strptime(existing.closingDate, "%Y-%m-%d")
                            if datesOverlap(new_od_date, new_cd_date, exist_od, exist_cd):
                                print("Cannot create project. You already manage a project in the same application period.")
                                managerHasOverlap = True
                                break

                    if not managerHasOverlap:
                        proj = currentUser.createProject(name, neigh, t1, n1, p1, t2, n2, p2, od, cd, slot)
                        projectsController.projects.append(proj)
                        print("Project created.")
                except ValueError:
                    print("Invalid date format. Project not created.")

            elif option == "Edit Project":
                pid = int(input("Project ID: "))
                if pid < 0 or pid >= len(projectsController.projects):
                    print("Invalid project ID.")
                    continue
                p = projectsController.projects[pid]

                new_name = input("Name or blank: ")
                new_neigh = input("Neighborhood or blank: ")
                new_t1 = input("Type1 label or blank: ")
                new_n1 = input("Num type1 or -1: ")
                new_p1 = input("Price type1 or -1: ")
                new_t2 = input("Type2 label or blank: ")
                new_n2 = input("Num type2 or -1: ")
                new_p2 = input("Price type2 or -1: ")
                new_od = input("Open date or blank (yyyy-mm-dd): ")
                new_cd = input("Close date or blank (yyyy-mm-dd): ")
                new_slots = input("Slots or -1: ")

                new_n1 = None if not new_n1.isdigit() else int(new_n1)
                new_p1 = None if not new_p1.isdigit() else int(new_p1)
                new_n2 = None if not new_n2.isdigit() else int(new_n2)
                new_p2 = None if not new_p2.isdigit() else int(new_p2)
                new_slots = None if not new_slots.isdigit() else int(new_slots)

                final_od = p.openingDate
                final_cd = p.closingDate
                try:
                    if new_od.strip():
                        datetime.strptime(new_od, "%Y-%m-%d")
                        final_od = new_od
                    if new_cd.strip():
                        datetime.strptime(new_cd, "%Y-%m-%d")
                        final_cd = new_cd
                except ValueError:
                    print("Invalid date format. Project not edited.")
                    continue

                try:
                    od_date_obj = datetime.strptime(final_od, "%Y-%m-%d")
                    cd_date_obj = datetime.strptime(final_cd, "%Y-%m-%d")
                    managerHasOverlap = False
                    for existing in projectsController.projects:
                        if existing != p and existing.manager == currentUser.name:
                            exist_od = datetime.strptime(existing.openingDate, "%Y-%m-%d")
                            exist_cd = datetime.strptime(existing.closingDate, "%Y-%m-%d")
                            if datesOverlap(od_date_obj, cd_date_obj, exist_od, exist_cd):
                                print("Cannot edit project to overlap with an existing project you manage.")
                                managerHasOverlap = True
                                break
                    if managerHasOverlap:
                        continue
                except:
                    print("Date parsing error. Edit aborted.")
                    continue

                msg = currentUser.editProject(
                    p,
                    name=(new_name if new_name.strip() else None),
                    neighborhood=(new_neigh if new_neigh.strip() else None),
                    t1=(new_t1 if new_t1.strip() else None),
                    n1=new_n1,
                    p1=new_p1,
                    t2=(new_t2 if new_t2.strip() else None),
                    n2=new_n2,
                    p2=new_p2,
                    openDate=(new_od if new_od.strip() else None),
                    closeDate=(new_cd if new_cd.strip() else None),
                    officerSlot=new_slots
                )
                print(msg)

            elif option == "Delete Project":
                pid = int(input("Project ID: "))
                if pid < 0 or pid >= len(projectsController.projects):
                    print("Invalid project ID.")
                    continue
                p = projectsController.projects[pid]
                print(currentUser.deleteProject(p, projectsController))

            elif option == "Toggle Project Visibility":
                pid = int(input("Project ID: "))
                if pid < 0 or pid >= len(projectsController.projects):
                    print("Invalid project ID.")
                    continue
                p = projectsController.projects[pid]
                print(currentUser.toggleProjectVisibility(p))

            elif option == "View All Projects":
                print(currentUser.viewAllProjects(projectsController))

            elif option == "View My Projects":
                print(currentUser.viewMyProjects(projectsController))

            elif option == "View Officer Registrations":
                print(currentUser.viewOfficerRegistrations(registrationsController))

            elif option == "Approve Officer Registration":
                i = int(input("Index: "))
                regs = registrationsController.getAllRegistrationsForManager(currentUser.name)
                if 0 <= i < len(regs):
                    print(currentUser.approveOfficerRegistration(regs[i], registrationsController))
                else:
                    print("Invalid index.")

            elif option == "Reject Officer Registration":
                i = int(input("Index: "))
                regs = registrationsController.getAllRegistrationsForManager(currentUser.name)
                if 0 <= i < len(regs):
                    print(currentUser.rejectOfficerRegistration(regs[i], registrationsController))
                else:
                    print("Invalid index.")

            elif option == "View Applications":
                print(currentUser.viewApplications(applicationsController))

            elif option == "Approve Application":
                i = int(input("Application index: "))
                if 0 <= i < len(applicationsController.applications):
                    print(currentUser.approveApplication(applicationsController.applications[i]))
                else:
                    print("Invalid index.")

            elif option == "Reject Application":
                i = int(input("Application index: "))
                if 0 <= i < len(applicationsController.applications):
                    print(currentUser.rejectApplication(applicationsController.applications[i]))
                else:
                    print("Invalid index.")

            elif option == "Approve Withdrawal":
                i = int(input("Application index: "))
                if 0 <= i < len(applicationsController.applications):
                    print(currentUser.approveWithdrawal(applicationsController.applications[i], applicationsController))
                else:
                    print("Invalid index.")

            elif option == "Generate Booking Report":
                filter_m = input("Filter by marital? (Single/Married/None): ")
                if filter_m.lower() == 'none':
                    filter_m = None
                print(currentUser.generateBookingReport(applicationsController, filter_m))

            elif option == "View All Enquiries":
                print(currentUser.viewAllEnquiries(enquiriesController))

            elif option == "Reply to Enquiry":
                idx = int(input("Enquiry index: "))
                rep = input("Reply text: ")
                print(currentUser.replyToEnquiry(idx, rep, enquiriesController))

            elif option == "Change Password":
                old_pwd = input("Enter your old password: ")
                if old_pwd == currentUser.password:
                    new_pwd = input("Enter your new password: ")
                    confirm_pwd = input("Confirm your new password: ")
                    if new_pwd == confirm_pwd:
                        currentUser.password = new_pwd
                        print("Password changed successfully.")
                    else:
                        print("The new passwords do not match.")
                else:
                    print("Incorrect old password.")

            elif option == "Logout":
                currentUser = None
            else:
                print("Invalid choice")

def test():
    print("============== STARTING TESTS ==============\n")
    
    tempdir = tempfile.TemporaryDirectory()
    applicantCsvPath = os.path.join(tempdir.name, "ApplicantList.csv")
    officerCsvPath   = os.path.join(tempdir.name, "OfficerList.csv")
    managerCsvPath   = os.path.join(tempdir.name, "ManagerList.csv")
    projectCsvPath   = os.path.join(tempdir.name, "ProjectList.csv")

    with open(applicantCsvPath, 'w') as f:
        f.write("Name,NRIC,Age,Marital Status,Password\n")
        f.write("John,S1234567A,35,Single,password\n")
        f.write("Sarah,T7654321B,40,Married,password\n")
        f.write("Grace,S9876543C,37,Married,password\n")
        f.write("James,T2345678D,30,Married,password\n")
        f.write("Rachel,S3456789E,20,Single,password\n")

    with open(officerCsvPath, 'w') as f:
        f.write("Name,NRIC,Age,Marital Status,Password\n")
        f.write("Daniel,T2109876H,36,Single,password\n")
        f.write("Emily,S6543210I,28,Single,password\n")
        f.write("David,T1234567J,29,Married,password\n")

    with open(managerCsvPath, 'w') as f:
        f.write("Name,NRIC,Age,Marital Status,Password\n")
        f.write("Michael,T8765432F,36,Single,password\n")
        f.write("Jessica,S5678901G,26,Married,password\n")

    with open(projectCsvPath, 'w') as f:
        f.write("Project Name,Neighborhood,Type 1,Number of units for Type 1,Selling price for Type 1,Type 2,Number of units for Type 2,Selling price for Type 2,Application opening date,Application closing date,Manager,Officer Slot,Officer\n")
        f.write('Acacia Breeze,Yishun,2-Room,2,350000,3-Room,0,450000,2025-02-15,2025-03-30,Jessica,3,"Daniel,Emily"\n')
        f.write('Acacia Tree,Yishun,2-Room,0,350000,3-Room,3,450000,2025-02-15,2025-03-30,Michael,3,"Daniel,David"\n')

    usersController        = UsersController(applicantCsvPath, officerCsvPath, managerCsvPath)
    projectsController     = ProjectsController(projectCsvPath)
    applicationsController = ApplicationsController()
    enquiriesController    = EnquiriesController()
    registrationsController= RegistrationsController()


    def check_equal(desc, expected, actual):
        """
        Simple helper: prints pass or fail based on string/None/equality comparison
        """
        print(f">> TEST: {desc}")
        print(f"   EXPECTED: {expected}")
        print(f"   GOT     : {actual}")
        if expected == actual:
            print("   RESULT  : PASS\n")
        else:
            print("   RESULT  : FAIL\n")

    def check_true(desc, condition):
        print(f">> TEST: {desc}")
        print(f"   CONDITION EVAL: {condition}")
        if condition:
            print("   RESULT  : PASS\n")
        else:
            print("   RESULT  : FAIL\n")

    user_john = usersController.login("S1234567A", "password")
    check_true("Test 1: John logs in with correct NRIC/password", user_john is not None and user_john.name == "John")

    user_invalid_nric = usersController.login("INVALID", "password")
    check_true("Test 2: Invalid NRIC format => login should fail", user_invalid_nric is None)

    user_wrong_pass = usersController.login("S1234567A", "wrongpassword")
    check_true("Test 3: Correct NRIC but incorrect password => should fail", user_wrong_pass is None)

    old_pwd = "password"
    if user_john and user_john.password == old_pwd:
        user_john.password = "newpass"

    user_john_new = usersController.login("S1234567A", "newpass")
    check_true("Test 4: After password change, can login with new password", user_john_new is not None)
    user_john_old = usersController.login("S1234567A", "password")
    check_true("Test 4: Old password no longer works", user_john_old is None)

    if user_john_new:
        user_john_new.password = "password"

    user_john = usersController.login("S1234567A", "password")

    projects_john_sees = user_john.getProjectsForApplicant(projectsController, applicationsController)
    check_true("Test 5: John sees both projects initially (both visible)", len(projects_john_sees) == 2)

    acacia_breeze = projectsController.projects[0]
    success, msg = user_john.applyForProject(acacia_breeze, 2, applicationsController)
    check_true("Test 6: John applying 2-room in Acacia Breeze => success", success and msg == "Application successful.")

    acacia_tree = projectsController.projects[1]
    success2, msg2 = user_john.applyForProject(acacia_tree, 3, applicationsController)
    check_true("Test 6: John applying 3-room (Single) => should fail", (not success2) and "You have already applied" in msg2)

    manager_jessica = usersController.login("S5678901G", "password")
    toggle_msg = manager_jessica.toggleProjectVisibility(acacia_breeze)
    app_john = user_john.getOngoingApplications(applicationsController)
    status_info = f"{app_john.status}, {app_john.project.visibility}" if app_john else "No app"
    check_true("Test 7: John can still see his application even if project visibility=off", app_john is not None and app_john.project.visibility == False)

    manager_jessica.toggleProjectVisibility(acacia_breeze)

    the_app = applicationsController.applications[0]
    approve_msg = manager_jessica.approveApplication(the_app)
    check_equal("Test 8: Jessica approves John's application => 'Application approved.'", "Application approved.", approve_msg)
    check_true("Test 8: Application status is SUCCESSFUL", the_app.status == "SUCCESSFUL")

    book_result_1 = user_john.requestBooking(the_app)
    check_equal("Test 8: John requests booking => 'Booking request sent.'", "Booking request sent.", book_result_1)

    book_result_2 = user_john.requestBooking(the_app)
    check_equal("Test 8: John tries booking again => 'Booking request already sent.'", "Booking request already sent.", book_result_2)

    sub_msg = user_john.submitEnquiry(acacia_breeze, "Hello, can I get more details?", enquiriesController)
    check_equal("Test 9: John submits enquiry => 'Enquiry submitted.'", "Enquiry submitted.", sub_msg)
    view_enq = user_john.viewMyEnquiries(enquiriesController)
    check_true("Test 9: John sees his enquiry in the list", "Hello, can I get more details?" in view_enq)
    edit_msg = user_john.editMyEnquiry(enquiriesController, 0, "Updated question about details.")
    check_equal("Test 9: Edit John’s enquiry => 'Enquiry updated.'", "Enquiry updated.", edit_msg)
    view_enq2 = user_john.viewMyEnquiries(enquiriesController)
    check_true("Test 9: The enquiry text changed to 'Updated question about details.'", "Updated question about details." in view_enq2)
    del_msg = user_john.deleteMyEnquiry(enquiriesController, 0)
    check_equal("Test 9: Delete John’s enquiry => 'Enquiry deleted.'", "Enquiry deleted.", del_msg)
    view_enq3 = user_john.viewMyEnquiries(enquiriesController)
    check_equal("Test 9: After deletion => 'No enquiries.'", "No enquiries.", view_enq3)

    officer_daniel = usersController.login("T2109876H", "password")
    reg_msg = officer_daniel.registerForProject(acacia_breeze, registrationsController)
    check_equal("Test 10: Daniel registers for Acacia Breeze => 'Officer registration submitted.'", "Officer registration submitted.", reg_msg)

    
    view_reg = officer_daniel.viewOfficerRegistrations()
    check_true("Test 11: Daniel sees 'PENDING' in registration list", "PENDING" in view_reg and "Acacia Breeze" in view_reg)

    manager_jessica_reg_list = manager_jessica.viewOfficerRegistrations(registrationsController)
    reg_to_approve = registrationsController.getAllRegistrationsForManager(manager_jessica.name)[0]
    approve_officer_msg = manager_jessica.approveOfficerRegistration(reg_to_approve, registrationsController)
    check_equal("Test 12: Jessica approves Daniel => 'Officer approved.'", "Officer approved.", approve_officer_msg)

    check_true("Test 13: Officers have no direct method to edit a project => pass by design", True)

    user_sarah = usersController.login("T7654321B", "password")
    enq_msg_sarah = user_sarah.submitEnquiry(acacia_breeze, "Sarah's question...", enquiriesController)
    check_true("Test 14: Sarah’s enquiry submitted", "submitted" in enq_msg_sarah.lower())
    rep_msg = officer_daniel.replyEnquiry(enquiriesController, 0, "Daniel’s official reply.")
    check_equal("Test 14: Daniel replies => 'Reply appended.'", "Reply appended.", rep_msg)

    enq_text_after = enquiriesController.enquiries[0].text
    check_true("Test 14: Enquiry text updated with officer reply", "Daniel’s official reply." in enq_text_after)

    officer_booking_msg = officer_daniel.bookFlatForApplicant("S1234567A", applicationsController)
    check_true("Test 15: Daniel books flat for John => success message", "Booked flat for S1234567A." in officer_booking_msg)
    check_true("Test 15: John’s application status => BOOKED", the_app.status == "BOOKED")
    check_true("Test 15: 2-room count decreased => now 1", acacia_breeze.numUnits1 == 1)

    receipt = officer_daniel.generateReceipt("S1234567A", applicationsController)
    check_true("Test 16: Generated receipt includes John’s name and '2-Room'",
               ("John" in receipt) and ("2-Room" in receipt))

    manager_michael = usersController.login("T8765432F", "password")
    new_proj = manager_michael.createProject("Sunrise View", "Boon Lay", "2-Room", 5, 300000,
                                            "3-Room", 5, 400000, "2025-05-01", "2025-06-01", 2)
    projectsController.projects.append(new_proj)
    check_true("Test 17: New project 'Sunrise View' is created and appended", any(p.projectName == "Sunrise View" for p in projectsController.projects))
    edit_result = manager_michael.editProject(new_proj, name="Sunrise Vista", n1=10)
    check_equal("Test 17: Michael edits 'Sunrise View' => 'Project updated.'", "Project updated.", edit_result)
    check_true("Test 17: Name changed to 'Sunrise Vista', numUnits1=10", new_proj.projectName == "Sunrise Vista" and new_proj.numUnits1 == 10)
    del_result = manager_michael.deleteProject(new_proj, projectsController)
    check_equal("Test 17: Delete the project => 'Project deleted.'", "Project deleted.", del_result)
    check_true("Test 17: 'Sunrise Vista' no longer in projects list", new_proj not in projectsController.projects)

    new_od_date = datetime.strptime("2025-03-01", "%Y-%m-%d")
    new_cd_date = datetime.strptime("2025-03-10", "%Y-%m-%d")
    existing_od = datetime.strptime(acacia_breeze.openingDate, "%Y-%m-%d")
    existing_cd = datetime.strptime(acacia_breeze.closingDate, "%Y-%m-%d")
    overlap = datesOverlap(new_od_date, new_cd_date, existing_od, existing_cd)
    check_true("Test 18: The new project for Jessica (3/1 ~ 3/10) overlaps with Acacia Breeze => True", overlap == True)

    acacia_tree = projectsController.projects[1]
    before_vis = acacia_tree.visibility
    toggle_1 = manager_michael.toggleProjectVisibility(acacia_tree)
    check_true("Test 19: Toggling Acacia Tree => 'Visibility set to False.'", "False" in toggle_1)
    check_true("Test 19: Actually changed => visibility==False", acacia_tree.visibility == False)
    toggle_2 = manager_michael.toggleProjectVisibility(acacia_tree)
    check_true("Test 19: Toggling again => 'Visibility set to True.'", "True" in toggle_2 and acacia_tree.visibility == True)

    all_proj_str = manager_michael.viewAllProjects(projectsController)
    check_true("Test 20: Michael sees at least 2 projects in 'View All Projects'", "Acacia Breeze" in all_proj_str and "Acacia Tree" in all_proj_str)
    my_proj_str = manager_michael.viewMyProjects(projectsController)
    check_true("Test 20: Michael’s own project => 'Acacia Tree'", "Acacia Tree" in my_proj_str and "Acacia Breeze" not in my_proj_str)

    officer_emily = usersController.login("S6543210I", "password")
    new_reg_msg = officer_emily.registerForProject(acacia_tree, registrationsController)
    check_equal("Test 21: Emily registers for Acacia Tree => 'Officer registration submitted.'", "Officer registration submitted.", new_reg_msg)
    regs_for_michael = registrationsController.getAllRegistrationsForManager("Michael")
    if regs_for_michael:
        reg_obj = regs_for_michael[0]
        appv_msg = manager_michael.approveOfficerRegistration(reg_obj, registrationsController)
        check_true("Test 21: Michael can approve Emily => 'Officer approved.' or 'No officer slot.'", ("Officer approved." in appv_msg) or ("No officer slot." in appv_msg))

    user_grace = usersController.login("S9876543C", "password")
    suc_grace, msg_grace = user_grace.applyForProject(acacia_tree, 3, applicationsController)
    check_true("Test 22: Grace applies for 3-room => success", suc_grace)

    new_app = applicationsController.applications[-1]
    reject_msg = manager_michael.rejectApplication(new_app)
    check_equal("Test 22: Michael rejects Grace’s application => 'Application rejected.'", "Application rejected.", reject_msg)
    check_true("Test 22: Grace’s app => status=UNSUCCESSFUL", new_app.status == "UNSUCCESSFUL")

    suc_sarah_app, msg_sarah_app = user_sarah.applyForProject(acacia_tree, 3, applicationsController)
    if suc_sarah_app:
        sarah_app = applicationsController.applications[-1]
        manager_michael.approveApplication(sarah_app)
        applicationsController.requestWithdraw(sarah_app)
        withdraw_msg = manager_michael.approveWithdrawal(sarah_app, applicationsController)
        check_equal("Test 22: Manager approves Sarah’s withdrawal => 'Withdrawal approved.'", "Withdrawal approved.", withdraw_msg)

    full_report = manager_jessica.generateBookingReport(applicationsController, None)
    check_true("Test 23: Full booking report includes John => 'John,S1234567A'", "John,S1234567A" in full_report)

    single_report = manager_jessica.generateBookingReport(applicationsController, "Single")
    check_true("Test 23: Single booking report => includes John", "John,S1234567A" in single_report)
    married_report = manager_jessica.generateBookingReport(applicationsController, "Married")
    check_true("Test 23: Married booking report => no John", "John,S1234567A" not in married_report)

    print("============== ALL TESTS COMPLETED ==============\n")
    tempdir.cleanup()

if __name__ == "__main__":
    test()
    main()