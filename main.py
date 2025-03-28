class User:
    def __init__(self, name, nric, age, maritalStatus, password):
        self.name = name
        self.nric = nric
        self.age = int(age)
        self.maritalStatus = maritalStatus
        self.password = password

    def menu(self):
        ...
class Applicant(User):
    def __init__(self, name, nric, age, maritalStatus, password):
        super().__init__(name, nric, age, maritalStatus, password)

    def menu(self):
        return [
            "View Projects",
            "Apply for Projects",
            "View Application Status",
            "Request Withdrawl",
            "Submit Enquiry",
            "View My Enquiries",
            "Edit My Enquiry",
            "Delete My Enquiry",
            "Logout",
        ]
    
    def getAvailableProjects(self, projectController):
        projects = []
        for i, project in enumerate(projectController.projects):
            if project.visibility:
                projects.append(f"ID: {i}\nName: {project.projectName}\nNeighborhood: {project.neighborhood}\n{project.type1}: {project.numUnits1} ({project.price1})\n{project.type2}: {project.numUnits2} ({project.price2})\nApplication Date: {project.openingDate}-{project.closingDate}")
        return projects
    
    def getOngoingApplications(self, applicationsController):
        for application in applicationsController.applications:
            if application.applicant == self:
                return application
            
        return False
    
    def verifyApplicationEligibility(self, project, flat_type, applicationController):
        if self.getOngoingApplications(applicationController) != False:
            return False, "You have already applied for a flat"
        if self.maritalStatus == "Single" and self.age < 35:
            return False, "Single applicants must be at least 35 years old"
        elif self.maritalStatus == "Single" and flat_type != 2:
            return False, "Single applicants can only apply for 2-room flats"
        elif self.maritalStatus == "Married" and self.age < 21:
            return False, "Married applicants must be at least 21 years old"
        elif flat_type == 2 and project.numUnits1 == 0:
            return False, "No more 2-room flats available"
        elif flat_type == 3 and project.numUnits2 == 0:
            return False, "No more 3-room flats available"
        else:
            return True, "Eligible to apply for project"

    def applyForProject(self, project, flat_type, applicationController):
        if flat_type not in [2, 3]:
            return False, "Invalid flat type"
        eligibility, message = self.verifyApplicationEligibility(project, flat_type, applicationController)
        if eligibility:
            applicationController.createApplication(self, project, flat_type)
            return True, "Application successful"
        else:
            return False, message
        
    def submitEnquiry(self, project, text, enquiriesController):
        enquiriesController.createEnquiry(self, project, text)
        return "Enquiry submitted successfully"

    def viewMyEnquiries(self, enquiriesController):
        my_enquiries = enquiriesController.getEnquiriesByApplicant(self)
        if not my_enquiries:
            return "You have no enquiries"
        message = "Your Enquiries:\n"
        for i, enquiry in my_enquiries:
            message += f"Index: {i} | Project: {enquiry.project.projectName} | Text: {enquiry.text}\n"
        return message

    def editMyEnquiry(self, enquiriesController, enquiry_index, new_text):
        my_enquiries = enquiriesController.getEnquiriesByApplicant(self)
        for i, enquiry in my_enquiries:
            if i == enquiry_index:
                enquiriesController.editEnquiry(enquiry, new_text)
                return "Enquiry updated successfully"
        return "Invalid enquiry index"

    def deleteMyEnquiry(self, enquiriesController, enquiry_index):
        my_enquiries = enquiriesController.getEnquiriesByApplicant(self)
        for i, enquiry in my_enquiries:
            if i == enquiry_index:
                enquiriesController.deleteEnquiry(enquiry)
                return "Enquiry deleted"
        return "Invalid enquiry index"
class HDBOfficer(Applicant):
    def __init__(self, name, nric, age, maritalStatus, password):
        super().__init__(name, nric, age, maritalStatus, password)

    def menu(self):
        return [
            "View Projects",
            "Apply for Projects",
            "View Application Status",
            "Request Withdrawl",
            "Logout",
        ]

    def getAvailableProjects(self, projectController):
        return super().getAvailableProjects(projectController)
    
    def getOngoingApplications(self, applicationsController):
        return super().getOngoingApplications(applicationsController)
    
    def verifyApplicationEligibility(self, project, flat_type, applicationController):
        return super().verifyApplicationEligibility(project, flat_type, applicationController)
    
    def applyForProject(self, project, flat_type, applicationController):
        return super().applyForProject(project, flat_type, applicationController)
    
class HDBManager(User):
    def __init__(self, name, nric, age, maritalStatus, password):
        super().__init__(name, nric, age, maritalStatus, password)
    
    def menu(self):
        return [
            "View Projects",
            "Logout",
        ]
class Project:
    def __init__(self, projectName, neighborhood, type1, numUnits1, price1, type2, numUnits2, price2, openingDate, closingDate, manager, officerSlot, officer):
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
        self.officerSlot = officerSlot
        self.officer = officer
        self.visibility = True

class UsersController:
    def __init__(self, applicantCsv, hdbOfficerCsv, hdbManagerCsv):
        self.users = []
        with open(applicantCsv, 'r') as file:
            for line in file.readlines()[1:]:
                name, nric, age, maritalStatus, password = line.strip().split(',')
                self.users.append(Applicant(name, nric, age, maritalStatus, password))
        with open(hdbOfficerCsv, 'r') as file:
            for line in file.readlines()[1:]:
                name, nric, age, maritalStatus, password = line.strip().split(',')
                self.users.append(HDBOfficer(name, nric, age, maritalStatus, password))
        with open(hdbManagerCsv, 'r') as file:
            for line in file.readlines()[1:]:
                name, nric, age, maritalStatus, password = line.strip().split(',')
                self.users.append(HDBManager(name, nric, age, maritalStatus, password))
        
    def login(self, nric, password):
        for user in self.users:
            if user.nric == nric and user.password == password:
                return user
        return None
    
    @staticmethod
    def getUserType(user):
        if type(user) == Applicant:
            return "Applicant"
        elif type(user) == HDBOfficer:
            return "HDB Officer"
        elif type(user) == HDBManager:
            return "HDB Manager"
        else:
            return None

class Application: # Successful, unsuccessful, pending, booked
    def __init__(self, applicant, project, flat_type):
        self.applicant = applicant
        self.project = project
        self.flat_type = flat_type
        self.status = "PENDING"
        self.requestWithdraw = False
    
class ApplicationsController:
    def __init__(self):
        self.applications = []

    def createApplication(self, applicant, project, flat_type):
        self.applications.append(Application(applicant, project, flat_type))

    def requestWithdraw(self, application):
        application.requestWithdraw = True
    

class RegistrationsController:
    ...

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
            parts[-1] = parts[-1].split(',')
            result.append(parts)

        for parts in result:
            self.projects.append(Project(parts[0], parts[1], parts[2], int(parts[3]), int(parts[4]), parts[5], int(parts[6]), int(parts[7]), parts[8], parts[9], parts[10], parts[11], parts[12]))

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
        results = []
        for i, enquiry in enumerate(self.enquiries):
            if enquiry.applicant == applicant:
                results.append((i, enquiry))
        return results

    def editEnquiry(self, enquiry, new_text):
        enquiry.text = new_text

    def deleteEnquiry(self, enquiry):
        self.enquiries.remove(enquiry)

if __name__ == "__main__":
    usersController = UsersController('ApplicantList.csv', 'OfficerList.csv', 'ManagerList.csv')
    projectsController = ProjectsController('ProjectList.csv')
    applicationsController = ApplicationsController()
    enquiriesController = EnquiriesController()

    currentUser = None
    while True:
        while not currentUser:
            nric = input("Enter NRIC: ")
            password = input("Enter password: ")
            currentUser = usersController.login(nric, password)
            if not currentUser:
                print("Invalid NRIC or password")

        print(f"Welcome, {currentUser.name} ({UsersController.getUserType(currentUser)})")

        menu = currentUser.menu()
        while currentUser:
            for i, option in enumerate(menu):
                print(f"{i + 1}. {option}")
            choice = input("Enter choice: ")
            option = menu[int(choice) - 1]
            if option == "View Projects":
                projects = currentUser.getAvailableProjects(projectsController)
                for project in projects:
                    print(project)
                    print()
            elif option == "Apply for Projects":
                project_id = input("Enter project ID: ")
                project = projectsController.projects[int(project_id)]
                flat_type = input("Enter rooms (2 or 3): ")
                success, message = currentUser.applyForProject(project, int(flat_type), applicationsController)
                print(message)
                print()
            elif option == "View Application Status":
                application = currentUser.getOngoingApplications(applicationsController)
                if application == False:
                    print("No ongoing applications")
                else:
                    print(f"Project: {application.project.projectName}\nFlat Type: {application.flat_type}\nStatus: {application.status} (Withdrawing: {application.requestWithdraw})")
                print()
            elif option == "Request Withdrawl":
                application = currentUser.getOngoingApplications(applicationsController)
                if application == False:
                    print("No ongoing applications")
                else:
                    applicationsController.requestWithdraw(application)
                    print("Requested to withdraw application")
                print()
            elif option == "Submit Enquiry":
                project_id = input("Enter project ID to submit enquiry about: ")
                project = projectsController.projects[int(project_id)]
                text = input("Enter your enquiry text: ")
                response = currentUser.submitEnquiry(project, text, enquiriesController)
                print(response)
                print()
            elif option == "View My Enquiries":
                response = currentUser.viewMyEnquiries(enquiriesController)
                print(response)
                print()
            elif option == "Edit My Enquiry":
                enquiry_idx = int(input("Enter the index of the enquiry you want to edit: "))
                new_text = input("Enter new enquiry text: ")
                response = currentUser.editMyEnquiry(enquiriesController, enquiry_idx, new_text)
                print(response)
                print()
            elif option == "Delete My Enquiry":
                enquiry_idx = int(input("Enter the index of the enquiry you want to delete: "))
                response = currentUser.deleteMyEnquiry(enquiriesController, enquiry_idx)
                print(response)
                print()
            elif option == "Logout":
                print("Logout")
                currentUser = None
            else:
                print("Invalid choice")