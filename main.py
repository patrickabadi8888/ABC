class User:
    def __init__(self, name, nric, age, maritalStatus, password):
        self.name = name
        self.nric = nric
        self.age = age
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
            "Logout",
        ]
    
    def getAvailableProjects(self, projectController):
        projects = []
        for i, project in enumerate(projectController.projects):
            if project.visibility:
                projects.append(f"ID: {i}\nName: {project.projectName}\nNeighborhood: {project.neighborhood}\n{project.type1}: {project.numUnits1} ({project.price1})\n{project.type2}: {project.numUnits2} ({project.price2})\nApplication Date: {project.openingDate}-{project.closingDate}")
        return projects
                
class HDBOfficer(Applicant):
    def __init__(self, name, nric, age, maritalStatus, password):
        super().__init__(name, nric, age, maritalStatus, password)

    def menu(self):
        return [
            "View Projects",
            "Apply for Projects",
            "View Application Status",
            "Logout",
        ]

class HDBManager(User):
    def __init__(self, name, nric, age, maritalStatus, password):
        super().__init__(name, nric, age, maritalStatus, password)
    
    def menu(self):
        return [
            "View Projects",
            "Apply for Projects",
            "View Application Status",
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

class ApplicantsController:
    ...

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


if __name__ == "__main__":
    usersController = UsersController('ApplicantList.csv', 'OfficerList.csv', 'ManagerList.csv')
    projectsController = ProjectsController('ProjectList.csv')

    currentUser = None
    while True:
        while not currentUser:
            nric = input("Enter NRIC: ")
            password = input("Enter password: ")
            currentUser = usersController.login(nric, password)
            if not currentUser:
                print("Invalid NRIC or password")

        print(f"Welcome, {currentUser.name} ({UsersController.getUserType(currentUser)})")

        while currentUser:
            for i, option in enumerate(currentUser.menu()):
                print(f"{i + 1}. {option}")
            choice = input("Enter choice: ")
            if choice == "1":
                projects = currentUser.getAvailableProjects(projectsController)
                for project in projects:
                    print(project)
                    print()
            elif choice == "2":
                print("Apply for Projects")
            elif choice == "3":
                print("View Application Status")
            elif choice == "4":
                print("Logout")
                currentUser = None
            else:
                print("Invalid choice")