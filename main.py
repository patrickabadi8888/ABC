class User:
    def __init__(self, name, nric, age, maritalStatus, password):
        self.name = name
        self.nric = nric
        self.age = age
        self.maritalStatus = maritalStatus
        self.password = password

class Applicant(User):
    def __init__(self, name, nric, age, maritalStatus, password):
        super().__init__(name, nric, age, maritalStatus, password)

class HDBOfficer(Applicant):
    def __init__(self, name, nric, age, maritalStatus, password):
        super().__init__(name, nric, age, maritalStatus, password)

class HDBManager(User):
    def __init__(self, name, nric, age, maritalStatus, password):
        super().__init__(name, nric, age, maritalStatus, password)

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

        for line in open(projectCsv, 'r').readlines():
            line = line.split()
            row = []
            current = ""
            inside_quotes = False
            for char in line:
                if char == '"' and not inside_quotes:
                    inside_quotes = True
                elif char == '"' and inside_quotes:
                    inside_quotes = False
                elif char == ',' and not inside_quotes:
                    row.append(current)
                    current = ""
                else:
                    current += char
            row.append(current)
            self.projects.append(Project(current[0], current[1], current[2], current[3], current[4], current[5], current[6], current[7], current[8], current[9], current[10], current[11], current[12]))
        

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

        break