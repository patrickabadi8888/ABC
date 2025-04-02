from datetime import datetime

def datesOverlap(start1, end1, start2, end2):
    return not (end1 < start2 or start1 > end2)

class User:
    def __init__(self, name, nric, age, maritalStatus, password):
        self.name = name
        self.nric = nric
        self.age = int(age)
        self.maritalStatus = maritalStatus
        self.password = password

    def menu(self):
        return []

class Applicant(User):
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
        my_app = applicationsController.getOngoingApplications(self)
        for i, project in enumerate(projectController.projects):
            if project.visibility or (my_app and my_app.project == project):
                if hasattr(self, 'myProjects') and project in self.myProjects:
                    pass
                details = f"ID: {i}\nName: {project.projectName}\nNeighborhood: {project.neighborhood}\n"
                details += f"{project.type1}: {project.numUnits1} ({project.price1})\n"
                details += f"{project.type2}: {project.numUnits2} ({project.price2})\n"
                details += f"Application Date: {project.openingDate}-{project.closingDate}\n"
                details += f"Manager: {project.manager}\nOfficers: {','.join([o for o in project.officers])}\n"
                projects.append(details)
        return projects

    def applyForProject(self, project, flat_type, applicationsController):
        return applicationsController.applyForProject(self, project, flat_type)

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

class HDBOfficer(Applicant):
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
        return registrationsController.registerForProject(self, project)

    def viewOfficerRegistrations(self):
        if not self.registrations:
            return "No officer registrations."
        msg = "Officer Registrations:\n"
        for i, r in enumerate(self.registrations):
            msg += f"{i}. Project: {r.project.projectName} | Status: {r.status}\n"
        return msg

    def replyEnquiry(self, idx, reply_text, enquiriesController):
        return enquiriesController.replyToProjectEnquiry(self, idx, reply_text)

    def bookFlatForApplicant(self, applicant_nric, applicationsController):
        return applicationsController.bookFlatForApplicant(self, applicant_nric)

    def generateReceipt(self, applicant_nric, applicationsController):
        return applicationsController.generateReceipt(self, applicant_nric)

class HDBManager(User):
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

    def createProject(self, name, neighborhood, t1, n1, p1, t2, n2, p2, od, cd, slot, projectsController):
        return projectsController.createProject(self, name, neighborhood, t1, n1, p1, t2, n2, p2, od, cd, slot)

    def editProject(self, project, name, neighborhood, t1, n1, p1, t2, n2, p2, openDate, closeDate, officerSlot, projectsController):
        return projectsController.editProject(
            self, project, name, neighborhood, t1, n1, p1, t2, n2, p2, openDate, closeDate, officerSlot
        )

    def deleteProject(self, project, projectsController):
        return projectsController.deleteProject(self, project)

    def toggleProjectVisibility(self, project, projectsController):
        return projectsController.toggleProjectVisibility(self, project)

    def viewAllProjects(self, projectsController):
        return projectsController.viewAllProjects()

    def viewMyProjects(self, projectsController):
        return projectsController.viewMyProjects(self)

    def viewOfficerRegistrations(self, registrationsController):
        regs = registrationsController.getAllRegistrationsForManager(self.name)
        if not regs:
            return "No registrations."
        msg = "Officer Registrations:\n"
        for i, r in enumerate(regs):
            msg += f"{i}. Project: {r.project.projectName}, Officer: {r.officer.name}, Status: {r.status}\n"
        return msg

    def approveOfficerRegistration(self, reg, registrationsController):
        return registrationsController.approveOfficerRegistration(self, reg)

    def rejectOfficerRegistration(self, reg, registrationsController):
        return registrationsController.rejectOfficerRegistration(self, reg)

    def viewApplications(self, applicationsController):
        return applicationsController.viewApplications()

    def approveApplication(self, application, applicationsController):
        return applicationsController.approveApplication(self, application)

    def rejectApplication(self, application, applicationsController):
        return applicationsController.rejectApplication(self, application)

    def approveWithdrawal(self, application, applicationsController):
        return applicationsController.approveWithdrawal(self, application)

    def generateBookingReport(self, applicationsController, filterMarital=None):
        return applicationsController.generateBookingReport(filterMarital)

    def viewAllEnquiries(self, enquiriesController):
        return enquiriesController.viewAllEnquiries()

    def replyToEnquiry(self, idx, reply_text, enquiriesController):
        return enquiriesController.replyToEnquiry(idx, reply_text)

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

    def createProject(self, manager, name, neighborhood, t1, n1, p1, t2, n2, p2, od, cd, slot):
        return Project(name, neighborhood, t1, n1, p1, t2, n2, p2, od, cd, manager.name, slot, [])

    def editProject(self, manager, project, name=None, neighborhood=None, t1=None, n1=None, p1=None,
                    t2=None, n2=None, p2=None, openDate=None, closeDate=None, officerSlot=None):
        if project.manager != manager.name:
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

    def deleteProject(self, manager, project):
        if project.manager != manager.name:
            return "Not your project."
        if project in self.projects:
            self.projects.remove(project)
            return "Project deleted."
        return "Not found."

    def toggleProjectVisibility(self, manager, project):
        if project.manager != manager.name:
            return "Not your project."
        project.visibility = not project.visibility
        return f"Visibility set to {project.visibility}."

    def viewAllProjects(self):
        msg = "All Projects:\n"
        for i, p in enumerate(self.projects):
            msg += f"{i}. {p.projectName} (Visible={p.visibility}, Manager={p.manager}, Officers={','.join(p.officers)})\n"
        return msg

    def viewMyProjects(self, manager):
        msg = "My Projects:\n"
        for i, p in enumerate(self.projects):
            if p.manager == manager.name:
                msg += f"{i}. {p.projectName} (Visible={p.visibility})\n"
        return msg

class Application:
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

    def verifyApplicationEligibility(self, applicant, project, flat_type):
        if self.getOngoingApplications(applicant):
            return False, "You have already applied."
        if applicant.maritalStatus == "Single" and applicant.age < 35:
            return False, "Single applicants must be at least 35."
        if applicant.maritalStatus == "Single" and flat_type != 2:
            return False, "Single applicants can only apply for 2-Room."
        if applicant.maritalStatus == "Married" and applicant.age < 21:
            return False, "Married applicants must be at least 21."
        if flat_type == 2 and project.numUnits1 == 0:
            return False, "No more 2-room flats."
        if flat_type == 3 and project.numUnits2 == 0:
            return False, "No more 3-room flats."
        return True, "Eligible"

    def applyForProject(self, applicant, project, flat_type):
        if hasattr(applicant, 'myProjects') and project in applicant.myProjects:
            return False, "Cannot apply for a project you handle as an officer."
        if project.manager == applicant.name:
            return False, "Managers cannot apply."
        if flat_type not in [2, 3]:
            return False, "Invalid flat type."
        ok, msg = self.verifyApplicationEligibility(applicant, project, flat_type)
        if ok:
            self.createApplication(applicant, project, flat_type)
            return True, "Application successful."
        return False, msg

    def createApplication(self, applicant, project, flat_type):
        self.applications.append(Application(applicant, project, flat_type))

    def getOngoingApplications(self, applicant):
        for application in self.applications:
            if application.applicant == applicant:
                return application
        return False

    def requestWithdraw(self, application):
        application.requestWithdraw = True

    def requestBooking(self, applicant, application):
        if application.status == "SUCCESSFUL":
            if application.requestedBooking:
                return "Booking request already sent."
            application.requestedBooking = True
            return "Booking request sent."
        if application.status == "BOOKED":
            return "You already booked."
        return f"Cannot request booking, status is {application.status}."

    def bookFlatForApplicant(self, officer, applicant_nric):
        for app in self.applications:
            if app.applicant.nric == applicant_nric:
                if app.project in officer.myProjects and app.status == "SUCCESSFUL":
                    if app.flat_type == 2 and app.project.numUnits1 > 0:
                        app.project.numUnits1 -= 1
                    elif app.flat_type == 3 and app.project.numUnits2 > 0:
                        app.project.numUnits2 -= 1
                    app.status = "BOOKED"
                    return f"Booked flat for {applicant_nric}."
        return "Cannot book."

    def generateReceipt(self, officer, applicant_nric):
        for app in self.applications:
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

    def viewApplications(self):
        msg = "Applications:\n"
        for i, a in enumerate(self.applications):
            msg += f"{i}. Applicant={a.applicant.name}, Project={a.project.projectName}, Flat={a.flat_type}, Status={a.status}, Withdraw={a.requestWithdraw}\n"
        return msg

    def approveApplication(self, manager, application):
        if application.project.manager != manager.name:
            return "Not your project."
        if application.status != "PENDING":
            return "Not pending."
        if (application.flat_type == 2 and application.project.numUnits1 == 0) or \
           (application.flat_type == 3 and application.project.numUnits2 == 0):
            return "No flats left, cannot approve."
        application.status = "SUCCESSFUL"
        return "Application approved."

    def rejectApplication(self, manager, application):
        if application.project.manager != manager.name:
            return "Not your project."
        if application.status != "PENDING":
            return "Not pending."
        application.status = "UNSUCCESSFUL"
        return "Application rejected."

    def approveWithdrawal(self, manager, application):
        if application.project.manager != manager.name:
            return "Not your project."
        if application not in self.applications:
            return "Application not found."
        if not application.requestWithdraw:
            return "No withdrawal request."
        self.applications.remove(application)
        return "Withdrawal approved."

    def generateBookingReport(self, filterMarital=None):
        booked = [a for a in self.applications if a.status == "BOOKED"]
        if filterMarital:
            booked = [b for b in booked if b.applicant.maritalStatus == filterMarital]
        if not booked:
            return "No bookings."
        msg = "Booking Report:\n"
        for b in booked:
            msg += f"{b.applicant.name},{b.applicant.nric},{b.applicant.age},{b.applicant.maritalStatus},Flat:{b.flat_type},Project:{b.project.projectName}\n"
        return msg

class Registration:
    def __init__(self, officer, project):
        self.officer = officer
        self.project = project
        self.status = "PENDING"

class RegistrationsController:
    def __init__(self):
        self.registrations = []

    def registerForProject(self, officer, project):
        if project in officer.myProjects:
            return "Already an officer."
        if project.manager == officer.name:
            return "Cannot register for your own project."
        reg = Registration(officer, project)
        officer.registrations.append(reg)
        self.registrations.append(reg)
        return "Officer registration submitted."

    def getAllRegistrationsForManager(self, managerName):
        return [r for r in self.registrations if r.project.manager == managerName]

    def approveOfficerRegistration(self, manager, reg):
        if reg.project.manager != manager.name:
            return "Not your project."
        if reg.status != "PENDING":
            return "Not pending."
        if len(reg.project.officers) >= reg.project.officerSlot:
            return "No officer slot."
        reg.status = "APPROVED"
        reg.officer.myProjects.append(reg.project)
        reg.project.officers.append(reg.officer.name)
        return "Officer approved."

    def rejectOfficerRegistration(self, manager, reg):
        if reg.project.manager != manager.name:
            return "Not your project."
        if reg.status != "PENDING":
            return "Not pending."
        reg.status = "REJECTED"
        return "Officer rejected."

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

    def replyToProjectEnquiry(self, officer, idx, reply_text):
        if not officer.myProjects:
            return "No handled projects."
        if idx < 0 or idx >= len(self.enquiries):
            return "Invalid enquiry index."
        e = self.enquiries[idx]
        if e.project in officer.myProjects:
            e.text += f" [Officer Reply: {reply_text}]"
            return "Reply appended."
        return "You don't handle this project."

    def viewAllEnquiries(self):
        if not self.enquiries:
            return "No enquiries."
        msg = "All Enquiries:\n"
        for i, e in enumerate(self.enquiries):
            msg += f"{i}. Project:{e.project.projectName}, From:{e.applicant.name}, Text:{e.text}\n"
        return msg

    def replyToEnquiry(self, idx, reply_text):
        if idx < 0 or idx >= len(self.enquiries):
            return "Invalid index."
        e = self.enquiries[idx]
        e.text += f" [Manager Reply: {reply_text}]"
        return "Reply appended."

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
        from_types = {
            Applicant: "Applicant",
            HDBOfficer: "HDB Officer",
            HDBManager: "HDB Manager",
        }
        # Specific check order so that a Manager won't be wrongly identified as an Officer
        if isinstance(user, HDBManager):
            return from_types[HDBManager]
        elif isinstance(user, HDBOfficer):
            return from_types[HDBOfficer]
        elif isinstance(user, Applicant):
            return from_types[Applicant]
        return None

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
                app = applicationsController.getOngoingApplications(currentUser)
                if not app:
                    print("No ongoing applications.")
                else:
                    print(f"Project: {app.project.projectName}")
                    print(f"Flat Type: {app.flat_type}")
                    print(f"Status: {app.status} (Withdraw={app.requestWithdraw})")
                    if app.status == "SUCCESSFUL":
                        c2 = input("Request booking? (y/n): ")
                        if c2.lower() == 'y':
                            print(applicationsController.requestBooking(currentUser, app))

            elif option == "Request Withdrawal":
                app = applicationsController.getOngoingApplications(currentUser)
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
                print(currentUser.replyEnquiry(idx, rep, enquiriesController))

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
                        proj = currentUser.createProject(
                            name, neigh, t1, n1, p1, t2, n2, p2, od, cd, slot, 
                            projectsController
                        )
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
                    officerSlot=new_slots,
                    projectsController=projectsController
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
                print(currentUser.toggleProjectVisibility(p, projectsController))

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
                    print(currentUser.approveApplication(applicationsController.applications[i], applicationsController))
                else:
                    print("Invalid index.")

            elif option == "Reject Application":
                i = int(input("Application index: "))
                if 0 <= i < len(applicationsController.applications):
                    print(currentUser.rejectApplication(applicationsController.applications[i], applicationsController))
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

if __name__ == "__main__":
    main()
