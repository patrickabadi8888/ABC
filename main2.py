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
        return super().menu() + [
            "Register for Project as Officer",
            "View My Officer Registrations",
            "Reply to Project Enquiry (Handled Project)",
            "Book a Flat for Applicant (Handled Project)",
            "Generate Booking Receipt",
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
    - [x] Can only handle one project within same period (but code below allows multiple if user desires)
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
        if n1: project.numUnits1 = n1
        if p1: project.price1 = p1
        if t2: project.type2 = t2
        if n2: project.numUnits2 = n2
        if p2: project.price2 = p2
        if openDate: project.openingDate = openDate
        if closeDate: project.closingDate = closeDate
        if officerSlot is not None: project.officerSlot = officerSlot
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
        result = []
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
            self.projects.append(Project(parts[0], parts[1], parts[2], int(parts[3]), int(parts[4]),
                                         parts[5], int(parts[6]), int(parts[7]), parts[8], parts[9],
                                         parts[10], parts[11], officer_list))

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
                proj = currentUser.createProject(name, neigh, t1, n1, p1, t2, n2, p2, od, cd, slot)
                projectsController.projects.append(proj)
                print("Project created.")

            elif option == "Edit Project":
                pid = int(input("Project ID: "))
                p = projectsController.projects[pid]
                print(currentUser.editProject(p, name=input("Name or blank: ") or None,
                                              neighborhood=input("Neighborhood or blank: ") or None,
                                              t1=input("Type1 label or blank: ") or None,
                                              n1=int(input("Num type1 or -1: ")) or None,
                                              p1=int(input("Price type1 or -1: ")) or None,
                                              t2=input("Type2 label or blank: ") or None,
                                              n2=int(input("Num type2 or -1: ")) or None,
                                              p2=int(input("Price type2 or -1: ")) or None,
                                              openDate=input("Open date or blank: ") or None,
                                              closeDate=input("Close date or blank: ") or None,
                                              officerSlot=int(input("Slots or -1: ")) or None))

            elif option == "Delete Project":
                pid = int(input("Project ID: "))
                p = projectsController.projects[pid]
                print(currentUser.deleteProject(p, projectsController))

            elif option == "Toggle Project Visibility":
                pid = int(input("Project ID: "))
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

            elif option == "Logout":
                currentUser = None
            else:
                print("Invalid choice")

if __name__ == "__main__":
    main()
