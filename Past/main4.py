import csv
import os
from datetime import datetime, date

APPLICANT_CSV = 'ApplicantList.csv'
OFFICER_CSV = 'OfficerList.csv'
MANAGER_CSV = 'ManagerList.csv'
PROJECT_CSV = 'ProjectList.csv'
APPLICATION_CSV = 'ApplicationData.csv'
REGISTRATION_CSV = 'RegistrationData.csv'
ENQUIRY_CSV = 'EnquiryData.csv'

DATE_FORMAT = "%Y-%m-%d"


def _parse_date(date_str):
    """Safely parses a date string."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, DATE_FORMAT).date()
    except ValueError:
        return None

def _format_date(date_obj):
    """Formats a date object to string."""
    if date_obj is None:
        return ""
    return date_obj.strftime(DATE_FORMAT)

def dates_overlap(start1, end1, start2, end2):
    """Checks if two date ranges overlap."""
    if not all([start1, end1, start2, end2]):
        return False
    return not (end1 < start2 or start1 > end2)

def validate_nric(nric):
    """Validates NRIC format (S/T + 7 digits + Letter)."""
    if len(nric) != 9:
        return False
    if nric[0].upper() not in ('S', 'T'):
        return False
    if not nric[1:8].isdigit():
        return False
    if not nric[8].isalpha():
        return False
    return True


class User:
    def __init__(self, name, nric, age, marital_status, password):
        self.name = name
        self.nric = nric
        try:
            self.age = int(age)
        except (ValueError, TypeError):
            self.age = 0
        self.marital_status = marital_status
        self.password = password

    def __eq__(self, other):
        if not isinstance(other, User):
            return NotImplemented
        return self.nric == other.nric

    def __hash__(self):
        return hash(self.nric)

class Applicant(User):
    pass

class HDBOfficer(Applicant):
    def __init__(self, name, nric, age, marital_status, password):
        super().__init__(name, nric, age, marital_status, password)
        self.handled_project_names = []

class HDBManager(User):
    pass

class Project:
    def __init__(self, project_name, neighborhood, type1, num_units1, price1,
                 type2, num_units2, price2, opening_date_str, closing_date_str,
                 manager_nric, officer_slot, officer_nrics_str, visibility_str="True"):
        self.project_name = project_name
        self.neighborhood = neighborhood
        self.type1 = type1
        self.num_units1 = int(num_units1)
        self.price1 = int(price1)
        self.type2 = type2
        self.num_units2 = int(num_units2)
        self.price2 = int(price2)
        self.opening_date = _parse_date(opening_date_str)
        self.closing_date = _parse_date(closing_date_str)
        self.manager_nric = manager_nric
        self.officer_slot = int(officer_slot)
        self.officer_nrics = [nric.strip() for nric in officer_nrics_str.split(',') if nric.strip()]
        self.visibility = visibility_str.lower() == 'true'

    def is_active(self):
        """Checks if project is visible and within application period."""
        today = date.today()
        return self.visibility and self.opening_date and self.closing_date and (self.opening_date <= today <= self.closing_date)

    def get_flat_details(self, flat_type_room):
        """Returns (num_units, price) for a given flat type (e.g., 2 for 2-Room)."""
        if flat_type_room == 2 and self.type1 == "2-Room":
            return self.num_units1, self.price1
        elif flat_type_room == 3 and self.type2 == "3-Room":
            return self.num_units2, self.price2
        return 0, 0

    def decrease_unit_count(self, flat_type_room):
        """Decreases unit count for the booked flat type."""
        if flat_type_room == 2 and self.type1 == "2-Room":
            if self.num_units1 > 0:
                self.num_units1 -= 1
                return True
        elif flat_type_room == 3 and self.type2 == "3-Room":
            if self.num_units2 > 0:
                self.num_units2 -= 1
                return True
        return False

class Application:
    STATUS_PENDING = "PENDING"
    STATUS_SUCCESSFUL = "SUCCESSFUL"
    STATUS_UNSUCCESSFUL = "UNSUCCESSFUL"
    STATUS_BOOKED = "BOOKED"
    VALID_STATUSES = [STATUS_PENDING, STATUS_SUCCESSFUL, STATUS_UNSUCCESSFUL, STATUS_BOOKED]

    def __init__(self, applicant_nric, project_name, flat_type, status=STATUS_PENDING, request_withdrawal="False"):
        self.applicant_nric = applicant_nric
        self.project_name = project_name
        self.flat_type = int(flat_type)
        self.status = status if status in self.VALID_STATUSES else self.STATUS_PENDING
        self.request_withdrawal = request_withdrawal.lower() == 'true'

class Registration:
    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"
    VALID_STATUSES = [STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED]

    def __init__(self, officer_nric, project_name, status=STATUS_PENDING):
        self.officer_nric = officer_nric
        self.project_name = project_name
        self.status = status if status in self.VALID_STATUSES else self.STATUS_PENDING

class Enquiry:
    def __init__(self, enquiry_id, applicant_nric, project_name, text, reply=""):
        self.enquiry_id = enquiry_id
        self.applicant_nric = applicant_nric
        self.project_name = project_name
        self.text = text
        self.reply = reply

    def is_replied(self):
        return bool(self.reply)


class BaseController:
    """Base class for controllers handling CSV persistence."""
    def __init__(self, csv_file):
        self.csv_file = csv_file
        self.data = []
        self._load_data()

    def _load_data(self):
        """Loads data from CSV file. To be implemented by subclasses."""
        raise NotImplementedError

    def _save_data(self):
        """Saves the current state of self.data back to the CSV file."""
        raise NotImplementedError

    def _get_next_id(self):
        """Helper for controllers needing sequential IDs."""
        if not self.data:
            return 1
        try:
            return max(int(item.id) for item in self.data) + 1
        except AttributeError:
            try:
                 return max(int(item.enquiry_id) for item in self.data) + 1
            except AttributeError:
                 print(f"Warning: Cannot determine next ID for {self.__class__.__name__}. Defaulting to len+1.")
                 return len(self.data) + 1


class UsersController(BaseController):
    def __init__(self, applicant_csv, officer_csv, manager_csv):
        self.applicant_csv = applicant_csv
        self.officer_csv = officer_csv
        self.manager_csv = manager_csv
        self.users = {}
        self._load_data()

    def _load_data(self):
        self.users = {}
        self._load_user_type(self.applicant_csv, Applicant)
        self._load_user_type(self.officer_csv, HDBOfficer)
        self._load_user_type(self.manager_csv, HDBManager)
        print(f"Loaded {len(self.users)} users.")

    def _load_user_type(self, csv_file, user_class):
        if not os.path.exists(csv_file):
            print(f"Warning: User file not found: {csv_file}. Creating empty file.")
            try:
                with open(csv_file, 'w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(['Name', 'NRIC', 'Age', 'Marital Status', 'Password'])
            except IOError as e:
                print(f"Error creating user file {csv_file}: {e}")
            return

        try:
            with open(csv_file, 'r', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if not all(key in row for key in ['Name', 'NRIC', 'Age', 'Marital Status', 'Password']):
                        print(f"Warning: Skipping invalid row in {csv_file}: {row}")
                        continue
                    if not validate_nric(row['NRIC']):
                        print(f"Warning: Skipping user with invalid NRIC in {csv_file}: {row['NRIC']}")
                        continue
                    if row['NRIC'] in self.users:
                         print(f"Warning: Duplicate NRIC found {row['NRIC']} in {csv_file}. Keeping first entry.")
                         continue

                    user = user_class(
                        row['Name'], row['NRIC'], row['Age'],
                        row['Marital Status'], row['Password']
                    )
                    self.users[user.nric] = user
        except FileNotFoundError:
             print(f"Error: User file not found during load: {csv_file}")
        except Exception as e:
            print(f"Error loading users from {csv_file}: {e}")


    def _save_data(self):
        """Saves users back to their respective CSV files."""
        applicants = []
        officers = []
        managers = []
        for user in self.users.values():
            data_row = [user.name, user.nric, user.age, user.marital_status, user.password]
            if isinstance(user, HDBManager):
                managers.append(data_row)
            elif isinstance(user, HDBOfficer):
                officers.append(data_row)
            elif isinstance(user, Applicant):
                applicants.append(data_row)

        self._save_user_type(self.applicant_csv, applicants, ['Name', 'NRIC', 'Age', 'Marital Status', 'Password'])
        self._save_user_type(self.officer_csv, officers, ['Name', 'NRIC', 'Age', 'Marital Status', 'Password'])
        self._save_user_type(self.manager_csv, managers, ['Name', 'NRIC', 'Age', 'Marital Status', 'Password'])

    def _save_user_type(self, csv_file, user_data, header):
         try:
            with open(csv_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(header)
                writer.writerows(user_data)
         except IOError as e:
             print(f"Error saving user data to {csv_file}: {e}")

    def find_user_by_nric(self, nric):
        return self.users.get(nric)

    def login(self, nric, password):
        if not validate_nric(nric):
            return None, "Invalid NRIC format."
        user = self.find_user_by_nric(nric)
        if user and user.password == password:
            return user, "Login successful."
        elif user:
            return None, "Incorrect password."
        else:
            return None, "NRIC not found."

    def change_password(self, user, new_password):
        user.password = new_password
        self._save_data()

    def get_user_role(self, user):
        if isinstance(user, HDBManager):
            return "HDB Manager"
        elif isinstance(user, HDBOfficer):
            return "HDB Officer"
        elif isinstance(user, Applicant):
            return "Applicant"
        return "Unknown"

class ProjectsController(BaseController):
    def __init__(self, csv_file, users_controller):
        self.users_controller = users_controller
        super().__init__(csv_file)

    def _load_data(self):
        self.data = []
        if not os.path.exists(self.csv_file):
             print(f"Warning: Project file not found: {self.csv_file}. Creating empty file.")
             try:
                 with open(self.csv_file, 'w', newline='') as file:
                     writer = csv.writer(file)
                     writer.writerow([
                         'Project Name', 'Neighborhood', 'Type 1', 'Number of units for Type 1',
                         'Selling price for Type 1', 'Type 2', 'Number of units for Type 2',
                         'Selling price for Type 2', 'Application opening date',
                         'Application closing date', 'Manager', 'Officer Slot', 'Officer', 'Visibility'
                     ])
             except IOError as e:
                 print(f"Error creating project file {self.csv_file}: {e}")
             return

        try:
            with open(self.csv_file, 'r', newline='') as file:
                reader = csv.reader(file)
                header = next(reader)
                expected_header = [
                    'Project Name', 'Neighborhood', 'Type 1', 'Number of units for Type 1',
                    'Selling price for Type 1', 'Type 2', 'Number of units for Type 2',
                    'Selling price for Type 2', 'Application opening date',
                    'Application closing date', 'Manager', 'Officer Slot', 'Officer', 'Visibility'
                ]
                if len(header) < len(expected_header) -1:
                     print(f"Warning: Project file {self.csv_file} has unexpected header. Trying to load anyway.")

                for row in reader:
                    if len(row) < len(expected_header) - 1:
                        print(f"Warning: Skipping short row in {self.csv_file}: {row}")
                        continue

                    visibility_str = row[13] if len(row) > 13 else "True"
                    manager_nric = row[10]

                    manager_user = self.users_controller.find_user_by_nric(manager_nric)
                    if not manager_user or not isinstance(manager_user, HDBManager):
                        print(f"Warning: Skipping project '{row[0]}' due to invalid/missing Manager NRIC: {manager_nric}")
                        continue

                    try:
                        num_units1 = int(row[3])
                        price1 = int(row[4])
                        num_units2 = int(row[6])
                        price2 = int(row[7])
                        officer_slot = int(row[11])
                    except ValueError:
                        print(f"Warning: Skipping project '{row[0]}' due to invalid numeric data.")
                        continue

                    project = Project(
                        row[0], row[1], row[2], num_units1, price1,
                        row[5], num_units2, price2, row[8], row[9],
                        manager_nric, officer_slot, row[12], visibility_str
                    )
                    self.data.append(project)
            print(f"Loaded {len(self.data)} projects.")
        except FileNotFoundError:
             print(f"Error: Project file not found during load: {self.csv_file}")
        except StopIteration:
             print(f"Project file {self.csv_file} is empty or contains only a header.")
        except Exception as e:
            print(f"Error loading projects from {self.csv_file}: {e}")


    def _save_data(self):
        header = [
            'Project Name', 'Neighborhood', 'Type 1', 'Number of units for Type 1',
            'Selling price for Type 1', 'Type 2', 'Number of units for Type 2',
            'Selling price for Type 2', 'Application opening date',
            'Application closing date', 'Manager', 'Officer Slot', 'Officer', 'Visibility'
        ]
        try:
            with open(self.csv_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(header)
                for p in self.data:
                    writer.writerow([
                        p.project_name, p.neighborhood, p.type1, p.num_units1, p.price1,
                        p.type2, p.num_units2, p.price2, _format_date(p.opening_date),
                        _format_date(p.closing_date), p.manager_nric, p.officer_slot,
                        ','.join(p.officer_nrics), str(p.visibility)
                    ])
        except IOError as e:
            print(f"Error saving project data to {self.csv_file}: {e}")

    def find_project_by_name(self, name):
        for p in self.data:
            if p.project_name == name:
                return p
        return None

    def get_all_projects(self):
        return sorted(self.data, key=lambda p: p.project_name)

    def get_projects_by_manager(self, manager_nric):
         return sorted(
             [p for p in self.data if p.manager_nric == manager_nric],
             key=lambda p: p.project_name
         )

    def get_viewable_projects_for_applicant(self, applicant, applications_controller):
        """Gets projects viewable by a specific applicant based on rules."""
        viewable = []
        applicant_application = applications_controller.find_application_by_applicant(applicant.nric)
        today = date.today()

        for project in self.data:
            is_project_applied_for = applicant_application and applicant_application.project_name == project.project_name
            is_open_for_viewing = project.visibility or is_project_applied_for

            if not is_open_for_viewing:
                continue

            if not is_project_applied_for:
                 is_within_dates = project.opening_date and project.closing_date and (project.opening_date <= today <= project.closing_date)
                 if not project.visibility or not is_within_dates:
                     continue

                 can_view_any_flat = False
                 if applicant.marital_status == "Single" and applicant.age >= 35:
                     can_view_any_flat = True
                 elif applicant.marital_status == "Married" and applicant.age >= 21:
                     can_view_any_flat = True

                 if not can_view_any_flat:
                     continue

            viewable.append(project)

        return sorted(viewable, key=lambda p: p.project_name)

    def get_handled_projects_for_officer(self, officer_nric):
        """Gets projects an officer is approved to handle."""
        handled = []
        for project in self.data:
            if officer_nric in project.officer_nrics:
                 handled.append(project)
        return sorted(handled, key=lambda p: p.project_name)


    def filter_projects(self, projects, location=None, flat_type=None):
        """Filters a list of projects."""
        filtered = projects
        if location:
            filtered = [p for p in filtered if p.neighborhood.lower() == location.lower()]
        if flat_type:
            try:
                flat_type_room = int(flat_type)
                if flat_type_room == 2:
                    filtered = [p for p in filtered if p.type1 == "2-Room" and p.num_units1 > 0]
                elif flat_type_room == 3:
                     filtered = [p for p in filtered if p.type2 == "3-Room" and p.num_units2 > 0]
            except ValueError:
                pass
        return filtered

    def create_project(self, manager, name, neighborhood, n1, p1, n2, p2, od_str, cd_str, slot):
        if self.find_project_by_name(name):
            return None, f"Project name '{name}' already exists."

        od = _parse_date(od_str)
        cd = _parse_date(cd_str)
        if not od or not cd or cd < od:
            return None, "Invalid opening or closing date."
        if cd < date.today():
             return None, "Closing date cannot be in the past."

        for existing_project in self.get_projects_by_manager(manager.nric):
            if existing_project.is_active() and dates_overlap(od, cd, existing_project.opening_date, existing_project.closing_date):
                return None, f"Manager already handles an active project ('{existing_project.project_name}') during this period."

        if not (0 <= slot <= 10):
             return None, "Officer slots must be between 0 and 10."

        new_project = Project(
            name, neighborhood, "2-Room", n1, p1, "3-Room", n2, p2,
            od_str, cd_str, manager.nric, slot, "", "True"
        )
        self.data.append(new_project)
        self._save_data()
        return new_project, "Project created successfully."

    def edit_project(self, manager, project, updates):
        if project.manager_nric != manager.nric:
            return False, "You can only edit projects you manage."

        original_od = project.opening_date
        original_cd = project.closing_date
        new_od = original_od
        new_cd = original_cd

        if 'name' in updates and updates['name']:
             if updates['name'] != project.project_name and self.find_project_by_name(updates['name']):
                 return False, f"Project name '{updates['name']}' already exists."
             project.project_name = updates['name']
        if 'neighborhood' in updates and updates['neighborhood']:
            project.neighborhood = updates['neighborhood']
        if 'n1' in updates and updates['n1'] is not None and int(updates['n1']) >= 0:
            project.num_units1 = int(updates['n1'])
        if 'p1' in updates and updates['p1'] is not None and int(updates['p1']) >= 0:
            project.price1 = int(updates['p1'])
        if 'n2' in updates and updates['n2'] is not None and int(updates['n2']) >= 0:
            project.num_units2 = int(updates['n2'])
        if 'p2' in updates and updates['p2'] is not None and int(updates['p2']) >= 0:
            project.price2 = int(updates['p2'])
        if 'officerSlot' in updates and updates['officerSlot'] is not None:
             new_slot = int(updates['officerSlot'])
             if not (0 <= new_slot <= 10):
                 return False, "Officer slots must be between 0 and 10."
             if new_slot < len(project.officer_nrics):
                 return False, f"Cannot reduce slots below current number of assigned officers ({len(project.officer_nrics)})."
             project.officer_slot = new_slot

        if 'openDate' in updates and updates['openDate']:
            parsed_od = _parse_date(updates['openDate'])
            if not parsed_od: return False, "Invalid opening date format."
            new_od = parsed_od
        if 'closeDate' in updates and updates['closeDate']:
            parsed_cd = _parse_date(updates['closeDate'])
            if not parsed_cd: return False, "Invalid closing date format."
            new_cd = parsed_cd

        if new_cd < new_od: return False, "Closing date cannot be before opening date."
        if new_od != original_od or new_cd != original_cd:
            if new_cd < date.today(): return False, "Closing date cannot be set to the past."
            for other_project in self.get_projects_by_manager(manager.nric):
                if other_project != project and other_project.is_active() and \
                   dates_overlap(new_od, new_cd, other_project.opening_date, other_project.closing_date):
                    return False, f"Edited dates overlap with another active project ('{other_project.project_name}') you manage."
            project.opening_date = new_od
            project.closing_date = new_cd


        self._save_data()
        return True, "Project updated successfully."

    def delete_project(self, manager, project):
        if project.manager_nric != manager.nric:
            return False, "You can only delete projects you manage."


        if project in self.data:
            self.data.remove(project)
            self._save_data()
            return True, "Project deleted successfully. (Note: Related applications/enquiries may remain)"
        return False, "Project not found."

    def toggle_project_visibility(self, manager, project):
        if project.manager_nric != manager.nric:
            return False, "You can only toggle visibility for projects you manage."
        project.visibility = not project.visibility
        self._save_data()
        status = "ON" if project.visibility else "OFF"
        return True, f"Project visibility set to {status}."

    def add_officer_to_project(self, project_name, officer_nric):
        """Adds an officer NRIC to the project's list."""
        project = self.find_project_by_name(project_name)
        if project and officer_nric not in project.officer_nrics:
            if len(project.officer_nrics) < project.officer_slot:
                project.officer_nrics.append(officer_nric)
                self._save_data()
                return True
        return False

    def remove_officer_from_project(self, project_name, officer_nric):
         """Removes an officer NRIC from the project's list."""
         project = self.find_project_by_name(project_name)
         if project and officer_nric in project.officer_nrics:
             project.officer_nrics.remove(officer_nric)
             self._save_data()
             return True
         return False

class ApplicationsController(BaseController):
    def __init__(self, csv_file, users_controller, projects_controller):
        self.users_controller = users_controller
        self.projects_controller = projects_controller
        super().__init__(csv_file)

    def _load_data(self):
        self.data = []
        if not os.path.exists(self.csv_file):
             print(f"Warning: Application file not found: {self.csv_file}. Creating empty file.")
             try:
                 with open(self.csv_file, 'w', newline='') as file:
                     writer = csv.writer(file)
                     writer.writerow(['ApplicantNRIC', 'ProjectName', 'FlatType', 'Status', 'RequestWithdrawal'])
             except IOError as e:
                 print(f"Error creating application file {self.csv_file}: {e}")
             return

        try:
            with open(self.csv_file, 'r', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if not all(key in row for key in ['ApplicantNRIC', 'ProjectName', 'FlatType', 'Status', 'RequestWithdrawal']):
                        print(f"Warning: Skipping invalid row in {self.csv_file}: {row}")
                        continue
                    if not self.users_controller.find_user_by_nric(row['ApplicantNRIC']):
                        print(f"Warning: Skipping application for non-existent user {row['ApplicantNRIC']}")
                        continue
                    if not self.projects_controller.find_project_by_name(row['ProjectName']):
                         print(f"Warning: Skipping application for non-existent project {row['ProjectName']}")
                         continue
                    try:
                        flat_type = int(row['FlatType'])
                        if flat_type not in [2, 3]: raise ValueError("Invalid flat type")
                    except ValueError:
                         print(f"Warning: Skipping application with invalid flat type: {row}")
                         continue

                    app = Application(
                        row['ApplicantNRIC'], row['ProjectName'], flat_type,
                        row['Status'], row['RequestWithdrawal']
                    )
                    self.data.append(app)
            print(f"Loaded {len(self.data)} applications.")
        except FileNotFoundError:
             print(f"Error: Application file not found during load: {self.csv_file}")
        except Exception as e:
            print(f"Error loading applications from {self.csv_file}: {e}")

    def _save_data(self):
        header = ['ApplicantNRIC', 'ProjectName', 'FlatType', 'Status', 'RequestWithdrawal']
        try:
            with open(self.csv_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(header)
                for app in self.data:
                    writer.writerow([
                        app.applicant_nric, app.project_name, app.flat_type,
                        app.status, str(app.request_withdrawal)
                    ])
        except IOError as e:
            print(f"Error saving application data to {self.csv_file}: {e}")

    def find_application_by_applicant(self, applicant_nric):
        """Finds the current (non-withdrawn/non-unsuccessful?) application for an applicant."""
        for app in self.data:
            if app.applicant_nric == applicant_nric and app.status != Application.STATUS_UNSUCCESSFUL:
                return app
        return None

    def get_applications_for_project(self, project_name):
        return [app for app in self.data if app.project_name == project_name]

    def get_all_applications(self):
        return self.data

    def _check_eligibility(self, applicant, project, flat_type):
        """Internal eligibility check."""
        today = date.today()
        if not project.opening_date or not project.closing_date or not (project.opening_date <= today <= project.closing_date):
             return False, "Project application period is closed or invalid."
        if not project.visibility:
             return False, "Project is not currently visible for application."

        if self.find_application_by_applicant(applicant.nric):
            return False, "You already have an active BTO application."

        if applicant.marital_status == "Single":
            if applicant.age < 35:
                return False, "Single applicants must be at least 35 years old."
            if flat_type != 2:
                return False, "Single applicants can only apply for 2-Room flats."
        elif applicant.marital_status == "Married":
            if applicant.age < 21:
                return False, "Married applicants must be at least 21 years old."
            if flat_type not in [2, 3]:
                 return False, "Invalid flat type selected."
        else:
            return False, "Invalid marital status for application."

        units, _ = project.get_flat_details(flat_type)
        if units <= 0:
            return False, f"No {flat_type}-Room units available in this project."

        return True, "Eligible."

    def apply_for_project(self, applicant, project, flat_type, registrations_controller):
        if isinstance(applicant, HDBManager):
            return False, "HDB Managers cannot apply for BTO projects."

        if isinstance(applicant, HDBOfficer):
             reg = registrations_controller.find_registration(applicant.nric, project.project_name)
             if reg and reg.status == Registration.STATUS_APPROVED:
                 return False, "You cannot apply for a project you are an approved officer for."
             if applicant.nric in project.officer_nrics:
                  return False, "You cannot apply for a project you are an approved officer for."


        is_eligible, msg = self._check_eligibility(applicant, project, flat_type)
        if not is_eligible:
            return False, msg

        new_application = Application(applicant.nric, project.project_name, flat_type)
        self.data.append(new_application)
        self._save_data()
        return True, "Application submitted successfully."

    def request_withdrawal(self, applicant_nric):
        application = self.find_application_by_applicant(applicant_nric)
        if not application:
            return False, "No active application found to withdraw."
        if application.status == Application.STATUS_BOOKED:
             application.request_withdrawal = True
             self._save_data()
             return True, "Withdrawal requested. Pending Manager approval."
        elif application.status in [Application.STATUS_PENDING, Application.STATUS_SUCCESSFUL]:
             application.request_withdrawal = True
             self._save_data()
             return True, "Withdrawal requested. Pending Manager approval."
        else:
            return False, f"Cannot request withdrawal for an application with status '{application.status}'."

    def approve_application(self, manager, application):
        project = self.projects_controller.find_project_by_name(application.project_name)
        if not project or project.manager_nric != manager.nric:
            return False, "You can only approve applications for projects you manage."
        if application.status != Application.STATUS_PENDING:
            return False, f"Application status is not {Application.STATUS_PENDING}."
        if application.request_withdrawal:
             return False, "Cannot approve an application with a pending withdrawal request."

        units, _ = project.get_flat_details(application.flat_type)
        if units <= 0:
            application.status = Application.STATUS_UNSUCCESSFUL
            self._save_data()
            return False, f"No {application.flat_type}-Room units available. Application automatically rejected."

        application.status = Application.STATUS_SUCCESSFUL
        self._save_data()
        return True, "Application approved successfully."

    def reject_application(self, manager, application):
        project = self.projects_controller.find_project_by_name(application.project_name)
        if not project or project.manager_nric != manager.nric:
            return False, "You can only reject applications for projects you manage."
        if application.status != Application.STATUS_PENDING:
            return False, f"Application status is not {Application.STATUS_PENDING}."

        application.status = Application.STATUS_UNSUCCESSFUL
        self._save_data()
        return True, "Application rejected successfully."

    def approve_withdrawal(self, manager, application):
        project = self.projects_controller.find_project_by_name(application.project_name)
        if not project or project.manager_nric != manager.nric:
            return False, "You can only approve withdrawals for projects you manage."
        if not application.request_withdrawal:
            return False, "No withdrawal request is pending for this application."

        original_status = application.status
        application.status = Application.STATUS_UNSUCCESSFUL
        application.request_withdrawal = False


        self._save_data()
        return True, "Withdrawal approved. Application status set to Unsuccessful."

    def reject_withdrawal(self, manager, application):
        project = self.projects_controller.find_project_by_name(application.project_name)
        if not project or project.manager_nric != manager.nric:
            return False, "You can only reject withdrawals for projects you manage."
        if not application.request_withdrawal:
            return False, "No withdrawal request is pending for this application."

        application.request_withdrawal = False
        self._save_data()
        return True, "Withdrawal request rejected."

    def book_flat_for_applicant(self, officer, applicant_nric):
        application = self.find_application_by_applicant(applicant_nric)
        if not application:
            return None, "No active application found for this NRIC."

        project = self.projects_controller.find_project_by_name(application.project_name)
        if not project:
             return None, "Project associated with application not found."

        if officer.nric not in project.officer_nrics:
             return None, "You do not handle the project for this application."

        if application.status != Application.STATUS_SUCCESSFUL:
            return None, f"Application status must be '{Application.STATUS_SUCCESSFUL}' to book. Current status: '{application.status}'."

        if not project.decrease_unit_count(application.flat_type):
             application.status = Application.STATUS_UNSUCCESSFUL
             self._save_data()
             self.projects_controller._save_data()
             return None, f"Booking failed: No {application.flat_type}-Room units available anymore. Application marked unsuccessful."


        application.status = Application.STATUS_BOOKED
        self._save_data()
        self.projects_controller._save_data()

        applicant = self.users_controller.find_user_by_nric(applicant_nric)
        receipt_data = {
            "Name": applicant.name if applicant else "N/A",
            "NRIC": applicant_nric,
            "Age": applicant.age if applicant else "N/A",
            "Marital Status": applicant.marital_status if applicant else "N/A",
            "Flat Type": f"{application.flat_type}-Room",
            "Project Name": project.project_name,
            "Neighborhood": project.neighborhood
        }
        return receipt_data, "Flat booked successfully and unit count updated."

    def generate_booking_report(self, filter_marital=None, filter_project=None, filter_flat_type=None):
        report_data = []
        booked_apps = [app for app in self.data if app.status == Application.STATUS_BOOKED]

        for app in booked_apps:
            applicant = self.users_controller.find_user_by_nric(app.applicant_nric)
            project = self.projects_controller.find_project_by_name(app.project_name)
            if not applicant or not project: continue

            if filter_marital and applicant.marital_status != filter_marital:
                continue
            if filter_project and project.project_name != filter_project:
                 continue
            if filter_flat_type:
                 try:
                     if app.flat_type != int(filter_flat_type):
                         continue
                 except ValueError:
                     pass

            report_data.append({
                "Applicant Name": applicant.name,
                "NRIC": applicant.nric,
                "Age": applicant.age,
                "Marital Status": applicant.marital_status,
                "Flat Type": f"{app.flat_type}-Room",
                "Project Name": project.project_name,
                "Neighborhood": project.neighborhood
            })
        return report_data


class RegistrationsController(BaseController):
    def __init__(self, csv_file, users_controller, projects_controller, applications_controller):
        self.users_controller = users_controller
        self.projects_controller = projects_controller
        self.applications_controller = applications_controller
        super().__init__(csv_file)

    def _load_data(self):
        self.data = []
        if not os.path.exists(self.csv_file):
             print(f"Warning: Registration file not found: {self.csv_file}. Creating empty file.")
             try:
                 with open(self.csv_file, 'w', newline='') as file:
                     writer = csv.writer(file)
                     writer.writerow(['OfficerNRIC', 'ProjectName', 'Status'])
             except IOError as e:
                 print(f"Error creating registration file {self.csv_file}: {e}")
             return

        try:
            with open(self.csv_file, 'r', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if not all(key in row for key in ['OfficerNRIC', 'ProjectName', 'Status']):
                        print(f"Warning: Skipping invalid row in {self.csv_file}: {row}")
                        continue
                    if not self.users_controller.find_user_by_nric(row['OfficerNRIC']):
                        print(f"Warning: Skipping registration for non-existent officer {row['OfficerNRIC']}")
                        continue
                    if not self.projects_controller.find_project_by_name(row['ProjectName']):
                         print(f"Warning: Skipping registration for non-existent project {row['ProjectName']}")
                         continue

                    reg = Registration(row['OfficerNRIC'], row['ProjectName'], row['Status'])
                    self.data.append(reg)
            print(f"Loaded {len(self.data)} registrations.")
        except FileNotFoundError:
             print(f"Error: Registration file not found during load: {self.csv_file}")
        except Exception as e:
            print(f"Error loading registrations from {self.csv_file}: {e}")

    def _save_data(self):
        header = ['OfficerNRIC', 'ProjectName', 'Status']
        try:
            with open(self.csv_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(header)
                for reg in self.data:
                    writer.writerow([reg.officer_nric, reg.project_name, reg.status])
        except IOError as e:
            print(f"Error saving registration data to {self.csv_file}: {e}")

    def find_registration(self, officer_nric, project_name):
        for reg in self.data:
            if reg.officer_nric == officer_nric and reg.project_name == project_name:
                return reg
        return None

    def get_registrations_by_officer(self, officer_nric):
        return [reg for reg in self.data if reg.officer_nric == officer_nric]

    def get_registrations_for_project(self, project_name, status_filter=None):
        regs = [reg for reg in self.data if reg.project_name == project_name]
        if status_filter:
            regs = [reg for reg in regs if reg.status == status_filter]
        return regs

    def register_for_project(self, officer, project):
        if self.find_registration(officer.nric, project.project_name):
            return False, "You have already submitted a registration for this project."

        if project.manager_nric == officer.nric:
            return False, "Managers cannot register as officers for their own projects."

        application = self.applications_controller.find_application_by_applicant(officer.nric)
        if application and application.project_name == project.project_name:
            return False, "You cannot register as an officer for a project you have applied for."

        today = date.today()
        target_od = project.opening_date
        target_cd = project.closing_date
        if not target_od or not target_cd:
             return False, "Target project has invalid application dates."

        for reg in self.get_registrations_by_officer(officer.nric):
            if reg.status == Registration.STATUS_APPROVED:
                other_project = self.projects_controller.find_project_by_name(reg.project_name)
                if other_project and other_project.opening_date and other_project.closing_date:
                     if dates_overlap(target_od, target_cd, other_project.opening_date, other_project.closing_date):
                         return False, f"You are already an approved officer for another project ('{other_project.project_name}') with an overlapping application period."

        new_registration = Registration(officer.nric, project.project_name)
        self.data.append(new_registration)
        self._save_data()
        return True, "Registration submitted successfully. Pending Manager approval."

    def approve_officer_registration(self, manager, registration):
        project = self.projects_controller.find_project_by_name(registration.project_name)
        if not project or project.manager_nric != manager.nric:
            return False, "You can only approve registrations for projects you manage."
        if registration.status != Registration.STATUS_PENDING:
            return False, f"Registration status is not {Registration.STATUS_PENDING}."

        approved_count = len(self.get_registrations_for_project(project.project_name, status_filter=Registration.STATUS_APPROVED))
        if approved_count >= project.officer_slot:
            return False, "No available officer slots in this project."

        registration.status = Registration.STATUS_APPROVED
        added = self.projects_controller.add_officer_to_project(project.project_name, registration.officer_nric)
        if not added:
             registration.status = Registration.STATUS_PENDING
             return False, "Failed to add officer to project list, approval aborted."

        self._save_data()
        return True, "Officer registration approved."

    def reject_officer_registration(self, manager, registration):
        project = self.projects_controller.find_project_by_name(registration.project_name)
        if not project or project.manager_nric != manager.nric:
            return False, "You can only reject registrations for projects you manage."
        if registration.status != Registration.STATUS_PENDING:
            return False, f"Registration status is not {Registration.STATUS_PENDING}."

        registration.status = Registration.STATUS_REJECTED
        self.projects_controller.remove_officer_from_project(project.project_name, registration.officer_nric)
        self._save_data()
        return True, "Officer registration rejected."


class EnquiriesController(BaseController):
    def __init__(self, csv_file, users_controller, projects_controller):
        self.users_controller = users_controller
        self.projects_controller = projects_controller
        self.next_id = 1
        super().__init__(csv_file)
        self.next_id = self._get_next_id()

    def _load_data(self):
        self.data = []
        if not os.path.exists(self.csv_file):
             print(f"Warning: Enquiry file not found: {self.csv_file}. Creating empty file.")
             try:
                 with open(self.csv_file, 'w', newline='') as file:
                     writer = csv.writer(file)
                     writer.writerow(['EnquiryID', 'ApplicantNRIC', 'ProjectName', 'Text', 'Reply'])
             except IOError as e:
                 print(f"Error creating enquiry file {self.csv_file}: {e}")
             return

        try:
            with open(self.csv_file, 'r', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if not all(key in row for key in ['EnquiryID', 'ApplicantNRIC', 'ProjectName', 'Text']):
                        print(f"Warning: Skipping invalid row in {self.csv_file}: {row}")
                        continue
                    if not self.users_controller.find_user_by_nric(row['ApplicantNRIC']):
                        print(f"Warning: Skipping enquiry for non-existent user {row['ApplicantNRIC']}")
                        continue
                    if not self.projects_controller.find_project_by_name(row['ProjectName']):
                         print(f"Warning: Skipping enquiry for non-existent project {row['ProjectName']}")
                         continue
                    try:
                        enquiry_id = int(row['EnquiryID'])
                    except ValueError:
                         print(f"Warning: Skipping enquiry with invalid ID: {row}")
                         continue

                    reply = row.get('Reply', '')

                    enq = Enquiry(enquiry_id, row['ApplicantNRIC'], row['ProjectName'], row['Text'], reply)
                    self.data.append(enq)

            print(f"Loaded {len(self.data)} enquiries.")
        except FileNotFoundError:
             print(f"Error: Enquiry file not found during load: {self.csv_file}")
        except Exception as e:
            print(f"Error loading enquiries from {self.csv_file}: {e}")

    def _save_data(self):
        header = ['EnquiryID', 'ApplicantNRIC', 'ProjectName', 'Text', 'Reply']
        try:
            with open(self.csv_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(header)
                for enq in self.data:
                    writer.writerow([
                        enq.enquiry_id, enq.applicant_nric, enq.project_name,
                        enq.text, enq.reply
                    ])
        except IOError as e:
            print(f"Error saving enquiry data to {self.csv_file}: {e}")

    def find_enquiry_by_id(self, enquiry_id):
        try:
            target_id = int(enquiry_id)
            for enq in self.data:
                if enq.enquiry_id == target_id:
                    return enq
        except ValueError:
            pass
        return None

    def get_enquiries_by_applicant(self, applicant_nric):
        return [enq for enq in self.data if enq.applicant_nric == applicant_nric]

    def get_enquiries_for_project(self, project_name):
        return [enq for enq in self.data if enq.project_name == project_name]

    def get_all_enquiries(self):
        return self.data

    def submit_enquiry(self, applicant, project, text):
        if not text or text.isspace():
            return None, "Enquiry text cannot be empty."

        enquiry_id = self.next_id
        self.next_id += 1
        new_enquiry = Enquiry(enquiry_id, applicant.nric, project.project_name, text)
        self.data.append(new_enquiry)
        self._save_data()
        return new_enquiry, "Enquiry submitted successfully."

    def edit_enquiry(self, applicant, enquiry_id, new_text):
        enquiry = self.find_enquiry_by_id(enquiry_id)
        if not enquiry:
            return False, "Enquiry not found."
        if enquiry.applicant_nric != applicant.nric:
            return False, "You can only edit your own enquiries."
        if enquiry.is_replied():
            return False, "Cannot edit an enquiry that has already been replied to."
        if not new_text or new_text.isspace():
            return False, "Enquiry text cannot be empty."

        enquiry.text = new_text
        self._save_data()
        return True, "Enquiry updated successfully."

    def delete_enquiry(self, applicant, enquiry_id):
        enquiry = self.find_enquiry_by_id(enquiry_id)
        if not enquiry:
            return False, "Enquiry not found."
        if enquiry.applicant_nric != applicant.nric:
            return False, "You can only delete your own enquiries."
        if enquiry.is_replied():
            return False, "Cannot delete an enquiry that has already been replied to."

        self.data.remove(enquiry)
        self._save_data()
        return True, "Enquiry deleted successfully."

    def reply_to_enquiry(self, replier_user, enquiry_id, reply_text):
        enquiry = self.find_enquiry_by_id(enquiry_id)
        if not enquiry:
            return False, "Enquiry not found."
        if not reply_text or reply_text.isspace():
            return False, "Reply text cannot be empty."
        if enquiry.is_replied():
             pass

        project = self.projects_controller.find_project_by_name(enquiry.project_name)
        if not project:
             return False, "Project associated with enquiry not found."

        replier_role = ""
        can_reply = False

        if isinstance(replier_user, HDBManager):
            replier_role = "Manager"
            if project.manager_nric == replier_user.nric:
                can_reply = True
            else:
                 return False, "Managers can only reply to enquiries for projects they manage."

        elif isinstance(replier_user, HDBOfficer):
            replier_role = "Officer"
            if replier_user.nric in project.officer_nrics:
                 can_reply = True
            else:
                 return False, "Officers can only reply to enquiries for projects they handle."

        if not can_reply:
             return False, "You do not have permission to reply to this enquiry."


        enquiry.reply = f"[{replier_role} - {replier_user.name}]: {reply_text}"
        self._save_data()
        return True, "Reply submitted successfully."



class ConsoleView:
    def display_message(self, message, error=False):
        prefix = "ERROR: " if error else ""
        print(f"\n{prefix}{message}")

    def get_input(self, prompt):
        return input(f"{prompt}: ").strip()

    def get_password(self, prompt="Enter password"):
        return input(f"{prompt}: ").strip()

    def display_menu(self, title, options):
        print(f"\n--- {title} ---")
        for i, option in enumerate(options):
            print(f"{i + 1}. {option}")
        print("--------------------")
        while True:
            choice = self.get_input("Enter your choice")
            if choice.isdigit() and 1 <= int(choice) <= len(options):
                return int(choice)
            else:
                self.display_message("Invalid choice, please enter a number from the list.", error=True)

    def display_list(self, title, items, empty_message="No items to display."):
        print(f"\n--- {title} ---")
        if not items:
            print(empty_message)
        else:
            for i, item in enumerate(items):
                print(f"{i + 1}. {item}")
        print("--------------------")

    def display_project_details(self, project, applicant=None):
        """Displays project details, potentially hiding info for singles."""
        print(f"\n--- Project: {project.project_name} ---")
        print(f"  Neighborhood: {project.neighborhood}")
        print(f"  Managed by NRIC: {project.manager_nric}")
        print(f"  Application Period: {_format_date(project.opening_date)} to {_format_date(project.closing_date)}")
        print(f"  Visibility: {'ON' if project.visibility else 'OFF'}")

        show_3_room = True
        if applicant and applicant.marital_status == "Single":
            show_3_room = False

        if project.type1 == "2-Room":
             print(f"  {project.type1}: {project.num_units1} units available at ${project.price1}")
        if project.type2 == "3-Room" and show_3_room:
             print(f"  {project.type2}: {project.num_units2} units available at ${project.price2}")

        print(f"  Officer Slots: {len(project.officer_nrics)} / {project.officer_slot}")
        print("-" * (len(project.project_name) + 14))


    def display_application_status(self, application, project, applicant):
         print("\n--- Your Application Status ---")
         print(f"  Applicant: {applicant.name} ({applicant.nric})")
         print(f"  Project: {project.project_name} ({project.neighborhood})")
         print(f"  Flat Type: {application.flat_type}-Room")
         print(f"  Status: {application.status}")
         if application.request_withdrawal:
             print("  Withdrawal Requested: Yes (Pending Manager Action)")
         print("-----------------------------")

    def display_enquiry(self, enquiry, project, applicant):
         print(f"\n--- Enquiry ID: {enquiry.enquiry_id} ---")
         print(f"  Project: {project.project_name}")
         print(f"  Submitted by: {applicant.name} ({applicant.nric})")
         print(f"  Enquiry: {enquiry.text}")
         if enquiry.is_replied():
             print(f"  Reply: {enquiry.reply}")
         else:
             print("  Reply: (No reply yet)")
         print("--------------------------")

    def display_registration(self, registration, project, officer):
         print(f"\n--- Officer Registration ---")
         print(f"  Officer: {officer.name} ({officer.nric})")
         print(f"  Project: {project.project_name}")
         print(f"  Status: {registration.status}")
         print("----------------------------")

    def display_receipt(self, receipt_data):
        print("\n--- Booking Receipt ---")
        for key, value in receipt_data.items():
            print(f"  {key}: {value}")
        print("-----------------------")

    def display_report(self, title, report_data, headers):
        print(f"\n--- {title} ---")
        if not report_data:
            print("No data found for this report.")
            return

        widths = {header: len(header) for header in headers}
        for row in report_data:
            for header in headers:
                widths[header] = max(widths[header], len(str(row.get(header, ''))))

        header_line = " | ".join(f"{header:<{widths[header]}}" for header in headers)
        print(header_line)
        print("-" * len(header_line))

        for row in report_data:
            print(" | ".join(f"{str(row.get(header, '')):<{widths[header]}}" for header in headers))
        print("--------------------")

    def prompt_login(self):
        nric = self.get_input("Enter NRIC")
        password = self.get_password()
        return nric, password

    def prompt_change_password(self, current_password):
         old_pwd = self.get_password("Enter your current password")
         if old_pwd != current_password:
             self.display_message("Incorrect current password.", error=True)
             return None
         new_pwd = self.get_password("Enter your new password")
         confirm_pwd = self.get_password("Confirm your new password")
         if new_pwd != confirm_pwd:
             self.display_message("New passwords do not match.", error=True)
             return None
         if not new_pwd:
              self.display_message("Password cannot be empty.", error=True)
              return None
         return new_pwd

    def prompt_project_filters(self):
        location = self.get_input("Filter by Neighborhood (leave blank for all)")
        flat_type = self.get_input("Filter by Flat Type (2 or 3, leave blank for all)")
        return {'location': location, 'flat_type': flat_type}

    def prompt_project_selection(self, projects):
        """Displays projects with indices and prompts for selection."""
        if not projects:
            self.display_message("No projects available for selection.", error=True)
            return None

        print("\n--- Select Project ---")
        for i, p in enumerate(projects):
            print(f"{i + 1}. {p.project_name} ({p.neighborhood}) - Visible: {p.visibility}")
        print("--------------------")

        while True:
            choice = self.get_input("Enter the number of the project (or 0 to cancel)")
            if choice == '0':
                return None
            if choice.isdigit():
                index = int(choice) - 1
                if 0 <= index < len(projects):
                    return projects[index]
            self.display_message("Invalid selection.", error=True)

    def prompt_flat_type_selection(self, project, applicant):
         """Prompts for flat type based on eligibility."""
         available_types = []
         if project.type1 == "2-Room" and project.num_units1 > 0:
             if (applicant.marital_status == "Single" and applicant.age >= 35) or \
                (applicant.marital_status == "Married" and applicant.age >= 21):
                 available_types.append(2)
         if project.type2 == "3-Room" and project.num_units2 > 0:
             if applicant.marital_status == "Married" and applicant.age >= 21:
                 available_types.append(3)

         if not available_types:
             self.display_message("No suitable flat types available for you in this project.", error=True)
             return None
         elif len(available_types) == 1:
              selected_type = available_types[0]
              self.display_message(f"Automatically selecting {selected_type}-Room flat.")
              return selected_type
         else:
             while True:
                 choice = self.get_input(f"Select flat type ({' or '.join(map(str, available_types))})")
                 if choice.isdigit() and int(choice) in available_types:
                     return int(choice)
                 self.display_message("Invalid flat type selection.", error=True)

    def prompt_enquiry_selection(self, enquiries):
        """Displays enquiries with IDs and prompts for selection by ID."""
        if not enquiries:
            self.display_message("No enquiries available for selection.", error=True)
            return None

        print("\n--- Select Enquiry (by ID) ---")
        for enq in enquiries:
             print(f"  ID: {enq.enquiry_id} | Project: {enq.project_name} | Text: {enq.text[:50]}...")
        print("-----------------------------")

        while True:
            choice = self.get_input("Enter the ID of the enquiry (or 0 to cancel)")
            if choice == '0':
                return None
            if choice.isdigit():
                 selected_enquiry = next((enq for enq in enquiries if enq.enquiry_id == int(choice)), None)
                 if selected_enquiry:
                     return selected_enquiry
            self.display_message("Invalid enquiry ID.", error=True)

    def prompt_registration_selection(self, registrations):
        """Displays registrations with indices and prompts for selection."""
        if not registrations:
            self.display_message("No registrations available for selection.", error=True)
            return None

        print("\n--- Select Registration ---")
        for i, reg in enumerate(registrations):
            officer = self.users_controller.find_user_by_nric(reg.officer_nric)
            officer_name = officer.name if officer else "Unknown Officer"
            print(f"{i + 1}. Project: {reg.project_name} | Officer: {officer_name} ({reg.officer_nric}) | Status: {reg.status}")
        print("-------------------------")

        while True:
            choice = self.get_input("Enter the number of the registration (or 0 to cancel)")
            if choice == '0':
                return None
            if choice.isdigit():
                index = int(choice) - 1
                if 0 <= index < len(registrations):
                    return registrations[index]
            self.display_message("Invalid selection.", error=True)

    def prompt_application_selection(self, applications):
        """Displays applications with indices and prompts for selection."""
        if not applications:
            self.display_message("No applications available for selection.", error=True)
            return None

        print("\n--- Select Application ---")
        for i, app in enumerate(applications):
            applicant = self.users_controller.find_user_by_nric(app.applicant_nric)
            applicant_name = applicant.name if applicant else "Unknown Applicant"
            print(f"{i + 1}. Project: {app.project_name} | Applicant: {applicant_name} ({app.applicant_nric}) | Type: {app.flat_type}-Room | Status: {app.status} | Withdraw Req: {app.request_withdrawal}")
        print("--------------------------")

        while True:
            choice = self.get_input("Enter the number of the application (or 0 to cancel)")
            if choice == '0':
                return None
            if choice.isdigit():
                index = int(choice) - 1
                if 0 <= index < len(applications):
                    return applications[index]
            self.display_message("Invalid selection.", error=True)

    def prompt_create_project_details(self):
        details = {}
        details['name'] = self.get_input("Enter Project Name")
        details['neighborhood'] = self.get_input("Enter Neighborhood")
        details['n1'] = self.get_input("Enter Number of 2-Room units")
        details['p1'] = self.get_input("Enter Selling Price for 2-Room")
        details['n2'] = self.get_input("Enter Number of 3-Room units")
        details['p2'] = self.get_input("Enter Selling Price for 3-Room")
        details['od_str'] = self.get_input(f"Enter Application Opening Date ({DATE_FORMAT})")
        details['cd_str'] = self.get_input(f"Enter Application Closing Date ({DATE_FORMAT})")
        details['slot'] = self.get_input("Enter Max Officer Slots (0-10)")

        try:
            details['n1'] = int(details['n1'])
            details['p1'] = int(details['p1'])
            details['n2'] = int(details['n2'])
            details['p2'] = int(details['p2'])
            details['slot'] = int(details['slot'])
            if not (0 <= details['slot'] <= 10): raise ValueError("Slot out of range")
            if any(n < 0 for n in [details['n1'], details['p1'], details['n2'], details['p2']]): raise ValueError("Numbers cannot be negative")
        except ValueError as e:
            self.display_message(f"Invalid numeric input: {e}. Please try again.", error=True)
            return None
        return details

    def prompt_edit_project_details(self, project):
        print(f"\nEditing Project: {project.project_name}. Leave blank to keep current value.")
        updates = {}
        updates['name'] = self.get_input(f"New Project Name [{project.project_name}]")
        updates['neighborhood'] = self.get_input(f"New Neighborhood [{project.neighborhood}]")
        updates['n1'] = self.get_input(f"New Number of 2-Room units [{project.num_units1}]")
        updates['p1'] = self.get_input(f"New Selling Price for 2-Room [{project.price1}]")
        updates['n2'] = self.get_input(f"New Number of 3-Room units [{project.num_units2}]")
        updates['p2'] = self.get_input(f"New Selling Price for 3-Room [{project.price2}]")
        updates['openDate'] = self.get_input(f"New Opening Date ({DATE_FORMAT}) [{_format_date(project.opening_date)}]")
        updates['closeDate'] = self.get_input(f"New Closing Date ({DATE_FORMAT}) [{_format_date(project.closing_date)}]")
        updates['officerSlot'] = self.get_input(f"New Max Officer Slots [{project.officer_slot}]")

        for key in ['n1', 'p1', 'n2', 'p2', 'officerSlot']:
             if updates[key]:
                 try:
                     updates[key] = int(updates[key])
                     if key == 'officerSlot' and not (0 <= updates[key] <= 10):
                          raise ValueError("Slots must be 0-10")
                     if key in ['n1','p1','n2','p2'] and updates[key] < 0:
                          raise ValueError("Units/Prices cannot be negative")
                 except ValueError as e:
                     self.display_message(f"Invalid input for {key}: {e}. Change ignored.", error=True)
                     updates[key] = None
             else:
                 updates[key] = None

        return {k: v for k, v in updates.items() if v is not None}

    def prompt_report_filters(self):
        filters = {}
        filters['filter_marital'] = self.get_input("Filter by Marital Status (Single/Married, leave blank for all)")
        filters['filter_project'] = self.get_input("Filter by Project Name (leave blank for all)")
        filters['filter_flat_type'] = self.get_input("Filter by Flat Type (2/3, leave blank for all)")

        for key in filters:
            if not filters[key]:
                filters[key] = None
        return filters



class ApplicationController:
    def __init__(self):
        self.view = ConsoleView()
        self.users_controller = UsersController(APPLICANT_CSV, OFFICER_CSV, MANAGER_CSV)
        self.projects_controller = ProjectsController(PROJECT_CSV, self.users_controller)
        self.applications_controller = ApplicationsController(APPLICATION_CSV, self.users_controller, self.projects_controller)
        self.registrations_controller = RegistrationsController(REGISTRATION_CSV, self.users_controller, self.projects_controller, self.applications_controller)
        self.enquiries_controller = EnquiriesController(ENQUIRY_CSV, self.users_controller, self.projects_controller)

        self.view.users_controller = self.users_controller

        self.current_user = None
        self.user_filters = {}

    def run(self):
        """Main application loop."""
        while True:
            if not self.current_user:
                self.handle_login()
            else:
                self.show_main_menu()

    def handle_login(self):
        self.view.display_message("Welcome to the BTO Management System")
        while not self.current_user:
            nric, password = self.view.prompt_login()
            user, message = self.users_controller.login(nric, password)
            if user:
                self.current_user = user
                self.user_filters = {}
                role = self.users_controller.get_user_role(user)
                self.view.display_message(f"Login successful. Welcome, {user.name} ({role})!")
            else:
                self.view.display_message(message, error=True)
                choice = self.view.get_input("Login failed. Try again? (y/n)")
                if choice.lower() != 'y':
                    self.shutdown()

    def handle_logout(self):
        self.view.display_message(f"Logging out user {self.current_user.name}.")
        self.current_user = None
        self.user_filters = {}

    def shutdown(self):
        self.view.display_message("Exiting BTO Management System. Goodbye!")
        exit()

    def show_main_menu(self):
        """Displays the appropriate menu based on the current user's role."""
        role = self.users_controller.get_user_role(self.current_user)
        actions = self._get_available_actions(role)
        options = list(actions.keys())

        choice_index = self.view.display_menu(f"{role} Menu", options) - 1
        selected_action_name = options[choice_index]
        action_method = actions[selected_action_name]

        action_method()

    def _get_available_actions(self, role):
        """Returns a dictionary of {action_name: method_to_call} for the role."""
        common_actions = {
            "Change Password": self.handle_change_password,
            "Logout": self.handle_logout,
        }
        applicant_actions = {
            "View Projects (Apply Filters)": self.handle_view_projects,
            "Apply for Project": self.handle_apply_for_project,
            "View My Application Status": self.handle_view_application_status,
            "Request Application Withdrawal": self.handle_request_withdrawal,
            "Submit Enquiry": self.handle_submit_enquiry,
            "View My Enquiries": self.handle_view_my_enquiries,
            "Edit My Enquiry": self.handle_edit_my_enquiry,
            "Delete My Enquiry": self.handle_delete_my_enquiry,
            **common_actions
        }
        officer_actions = {
            **{k: v for k, v in applicant_actions.items() if k not in common_actions},
            "Register for Project as Officer": self.handle_register_for_project,
            "View My Officer Registrations": self.handle_view_my_registrations,
            "View Handled Projects Details": self.handle_view_handled_projects,
            "Reply to Enquiry (Handled Project)": self.handle_reply_enquiry_officer,
            "Book Flat for Applicant (Handled Project)": self.handle_book_flat,
            "Generate Booking Receipt": self.handle_generate_receipt,
            **common_actions
        }
        manager_actions = {
            "Create Project": self.handle_create_project,
            "Edit Project": self.handle_edit_project,
            "Delete Project": self.handle_delete_project,
            "Toggle Project Visibility": self.handle_toggle_visibility,
            "View All Projects (Apply Filters)": self.handle_view_all_projects,
            "View My Projects": self.handle_view_my_projects,
            "View Officer Registrations (Project)": self.handle_view_officer_registrations,
            "Approve Officer Registration": self.handle_approve_officer_registration,
            "Reject Officer Registration": self.handle_reject_officer_registration,
            "View Applications (Project)": self.handle_view_applications,
            "Approve Application": self.handle_approve_application,
            "Reject Application": self.handle_reject_application,
            "Approve Withdrawal Request": self.handle_approve_withdrawal,
            "Reject Withdrawal Request": self.handle_reject_withdrawal,
            "Generate Booking Report": self.handle_generate_booking_report,
            "View All Enquiries": self.handle_view_all_enquiries,
            "Reply to Enquiry (Handled Project)": self.handle_reply_enquiry_manager,
            **common_actions
        }

        if role == "HDB Manager":
            return manager_actions
        elif role == "HDB Officer":
            return officer_actions
        elif role == "Applicant":
            return applicant_actions
        else:
            return common_actions


    def handle_change_password(self):
        new_password = self.view.prompt_change_password(self.current_user.password)
        if new_password:
            self.users_controller.change_password(self.current_user, new_password)
            self.view.display_message("Password changed successfully.")

    def handle_view_projects(self):
        projects = self.projects_controller.get_viewable_projects_for_applicant(
            self.current_user, self.applications_controller
        )

        filtered_projects = self.projects_controller.filter_projects(
            projects,
            location=self.user_filters.get('location'),
            flat_type=self.user_filters.get('flat_type')
        )

        self.view.display_message(f"Current Filters: {self.user_filters or 'None'}")
        if not filtered_projects:
             self.view.display_message("No projects match your criteria or eligibility.")
        else:
             self.view.display_message("Displaying projects you are eligible to view/apply for:")
             for project in filtered_projects:
                 self.view.display_project_details(project, self.current_user)

        if self.view.get_input("Update filters? (y/n)").lower() == 'y':
            self.user_filters = self.view.prompt_project_filters()
            self.view.display_message("Filters updated. View projects again to see changes.")

    def handle_apply_for_project(self):
        application = self.applications_controller.find_application_by_applicant(self.current_user.nric)
        if application:
             self.view.display_message("You already have an active application.", error=True)
             return

        potential_projects = self.projects_controller.get_viewable_projects_for_applicant(
            self.current_user, self.applications_controller
        )
        today = date.today()
        selectable_projects = [
            p for p in potential_projects
            if p.visibility and p.opening_date and p.closing_date and (p.opening_date <= today <= p.closing_date)
        ]

        project_to_apply = self.view.prompt_project_selection(selectable_projects)
        if not project_to_apply:
            return

        flat_type = self.view.prompt_flat_type_selection(project_to_apply, self.current_user)
        if flat_type is None:
            return

        success, message = self.applications_controller.apply_for_project(
            self.current_user, project_to_apply, flat_type, self.registrations_controller
        )
        self.view.display_message(message, error=not success)

    def handle_view_application_status(self):
        application = self.applications_controller.find_application_by_applicant(self.current_user.nric)
        if not application:
            self.view.display_message("You do not have an active BTO application.")
            return

        project = self.projects_controller.find_project_by_name(application.project_name)
        if not project:
             self.view.display_message("Error: Project associated with your application not found.", error=True)
             return

        self.view.display_application_status(application, project, self.current_user)

    def handle_request_withdrawal(self):
        application = self.applications_controller.find_application_by_applicant(self.current_user.nric)
        if not application:
            self.view.display_message("You do not have an active BTO application.", error=True)
            return

        if application.request_withdrawal:
             self.view.display_message("You have already requested withdrawal for this application.", error=True)
             return

        confirm = self.view.get_input(f"Request withdrawal for application to '{application.project_name}'? (y/n)")
        if confirm.lower() == 'y':
            success, message = self.applications_controller.request_withdrawal(self.current_user.nric)
            self.view.display_message(message, error=not success)

    def handle_submit_enquiry(self):
        viewable_projects = self.projects_controller.get_viewable_projects_for_applicant(
            self.current_user, self.applications_controller
        )
        project_to_enquire = self.view.prompt_project_selection(viewable_projects)
        if not project_to_enquire:
            return

        text = self.view.get_input("Enter your enquiry text")
        enquiry, message = self.enquiries_controller.submit_enquiry(self.current_user, project_to_enquire, text)
        self.view.display_message(message, error=not enquiry)

    def handle_view_my_enquiries(self):
        my_enquiries = self.enquiries_controller.get_enquiries_by_applicant(self.current_user.nric)
        if not my_enquiries:
            self.view.display_message("You have not submitted any enquiries.")
            return

        self.view.display_message("Your Submitted Enquiries:")
        for enquiry in my_enquiries:
            project = self.projects_controller.find_project_by_name(enquiry.project_name)
            applicant = self.users_controller.find_user_by_nric(enquiry.applicant_nric)
            if project and applicant:
                 self.view.display_enquiry(enquiry, project, applicant)
            else:
                 self.view.display_message(f"Could not display details for Enquiry ID {enquiry.enquiry_id} (missing project/user data?)", error=True)


    def handle_edit_my_enquiry(self):
        my_enquiries = self.enquiries_controller.get_enquiries_by_applicant(self.current_user.nric)
        editable_enquiries = [e for e in my_enquiries if not e.is_replied()]

        enquiry_to_edit = self.view.prompt_enquiry_selection(editable_enquiries)
        if not enquiry_to_edit:
            return

        new_text = self.view.get_input("Enter the new enquiry text")
        success, message = self.enquiries_controller.edit_enquiry(self.current_user, enquiry_to_edit.enquiry_id, new_text)
        self.view.display_message(message, error=not success)

    def handle_delete_my_enquiry(self):
        my_enquiries = self.enquiries_controller.get_enquiries_by_applicant(self.current_user.nric)
        deletable_enquiries = [e for e in my_enquiries if not e.is_replied()]

        enquiry_to_delete = self.view.prompt_enquiry_selection(deletable_enquiries)
        if not enquiry_to_delete:
            return

        confirm = self.view.get_input(f"Are you sure you want to delete Enquiry ID {enquiry_to_delete.enquiry_id}? (y/n)")
        if confirm.lower() == 'y':
            success, message = self.enquiries_controller.delete_enquiry(self.current_user, enquiry_to_delete.enquiry_id)
            self.view.display_message(message, error=not success)

    def handle_register_for_project(self):
        all_projects = self.projects_controller.get_all_projects()
        my_regs = {reg.project_name for reg in self.registrations_controller.get_registrations_by_officer(self.current_user.nric)}
        my_app = self.applications_controller.find_application_by_applicant(self.current_user.nric)
        my_app_project = my_app.project_name if my_app else None

        selectable_projects = [
            p for p in all_projects
            if p.project_name not in my_regs and \
               p.project_name != my_app_project and \
               p.manager_nric != self.current_user.nric
        ]

        project_to_register = self.view.prompt_project_selection(selectable_projects)
        if not project_to_register:
            return

        success, message = self.registrations_controller.register_for_project(self.current_user, project_to_register)
        self.view.display_message(message, error=not success)

    def handle_view_my_registrations(self):
        my_registrations = self.registrations_controller.get_registrations_by_officer(self.current_user.nric)
        if not my_registrations:
            self.view.display_message("You have no officer registrations.")
            return

        self.view.display_message("Your Officer Registrations:")
        for reg in my_registrations:
            project = self.projects_controller.find_project_by_name(reg.project_name)
            officer = self.users_controller.find_user_by_nric(reg.officer_nric)
            if project and officer:
                 self.view.display_registration(reg, project, officer)
            else:
                 self.view.display_message(f"Could not display details for registration to {reg.project_name} (missing project/user data?)", error=True)

    def handle_view_handled_projects(self):
        """Allows officer to view full details of projects they handle, ignoring visibility."""
        handled_projects = []
        my_approved_regs = [
            reg for reg in self.registrations_controller.get_registrations_by_officer(self.current_user.nric)
            if reg.status == Registration.STATUS_APPROVED
        ]
        handled_project_names = {reg.project_name for reg in my_approved_regs}

        for p in self.projects_controller.get_all_projects():
             if self.current_user.nric in p.officer_nrics:
                  handled_project_names.add(p.project_name)


        for name in handled_project_names:
             project = self.projects_controller.find_project_by_name(name)
             if project:
                  handled_projects.append(project)

        if not handled_projects:
             self.view.display_message("You are not currently handling any projects.")
             return

        self.view.display_message("Projects You Handle:")
        sorted_handled = sorted(handled_projects, key=lambda p: p.project_name)
        for project in sorted_handled:
             self.view.display_project_details(project)


    def _get_enquiries_for_handled_projects(self, user):
         """Helper to get enquiries for projects handled by officer/manager."""
         handled_enquiries = []
         handled_project_names = set()

         if isinstance(user, HDBManager):
              handled_project_names = {p.project_name for p in self.projects_controller.get_projects_by_manager(user.nric)}
         elif isinstance(user, HDBOfficer):
              approved_regs = [r for r in self.registrations_controller.get_registrations_by_officer(user.nric) if r.status == Registration.STATUS_APPROVED]
              handled_project_names = {r.project_name for r in approved_regs}
              for p in self.projects_controller.get_all_projects():
                   if user.nric in p.officer_nrics:
                        handled_project_names.add(p.project_name)


         for enquiry in self.enquiries_controller.get_all_enquiries():
             if enquiry.project_name in handled_project_names:
                 handled_enquiries.append(enquiry)
         return handled_enquiries

    def handle_reply_enquiry_officer(self):
        handled_enquiries = self._get_enquiries_for_handled_projects(self.current_user)
        unreplied_enquiries = [e for e in handled_enquiries if not e.is_replied()]

        enquiry_to_reply = self.view.prompt_enquiry_selection(unreplied_enquiries)
        if not enquiry_to_reply:
            return

        reply_text = self.view.get_input("Enter your reply")
        success, message = self.enquiries_controller.reply_to_enquiry(self.current_user, enquiry_to_reply.enquiry_id, reply_text)
        self.view.display_message(message, error=not success)

    def handle_book_flat(self):
        applicant_nric = self.view.get_input("Enter Applicant's NRIC to book flat for")
        if not validate_nric(applicant_nric):
            self.view.display_message("Invalid NRIC format.", error=True)
            return

        applicant = self.users_controller.find_user_by_nric(applicant_nric)
        if not applicant:
            self.view.display_message(f"Applicant with NRIC {applicant_nric} not found.", error=True)
            return

        receipt_data, message = self.applications_controller.book_flat_for_applicant(self.current_user, applicant_nric)

        self.view.display_message(message, error=not receipt_data)
        if receipt_data:
            self.view.display_receipt(receipt_data)

    def handle_generate_receipt(self):
        applicant_nric = self.view.get_input("Enter Applicant's NRIC to generate receipt for")
        if not validate_nric(applicant_nric):
            self.view.display_message("Invalid NRIC format.", error=True)
            return

        application = self.applications_controller.find_application_by_applicant(applicant_nric)
        if not application or application.status != Application.STATUS_BOOKED:
            self.view.display_message(f"No booked application found for NRIC {applicant_nric}.", error=True)
            return

        project = self.projects_controller.find_project_by_name(application.project_name)
        applicant = self.users_controller.find_user_by_nric(applicant_nric)

        if not project or self.current_user.nric not in project.officer_nrics:
             self.view.display_message("You do not handle the project for this booked application.", error=True)
             return

        if not applicant:
             self.view.display_message("Applicant data not found.", error=True)
             return


        receipt_data = {
            "Name": applicant.name, "NRIC": applicant.nric, "Age": applicant.age,
            "Marital Status": applicant.marital_status, "Flat Type": f"{application.flat_type}-Room",
            "Project Name": project.project_name, "Neighborhood": project.neighborhood
        }
        self.view.display_receipt(receipt_data)


    def handle_create_project(self):
        details = self.view.prompt_create_project_details()
        if not details: return

        project, message = self.projects_controller.create_project(
            self.current_user, details['name'], details['neighborhood'],
            details['n1'], details['p1'], details['n2'], details['p2'],
            details['od_str'], details['cd_str'], details['slot']
        )
        self.view.display_message(message, error=not project)

    def handle_edit_project(self):
        my_projects = self.projects_controller.get_projects_by_manager(self.current_user.nric)
        project_to_edit = self.view.prompt_project_selection(my_projects)
        if not project_to_edit: return

        updates = self.view.prompt_edit_project_details(project_to_edit)
        if not updates:
             self.view.display_message("No changes entered.")
             return

        success, message = self.projects_controller.edit_project(self.current_user, project_to_edit, updates)
        self.view.display_message(message, error=not success)

    def handle_delete_project(self):
        my_projects = self.projects_controller.get_projects_by_manager(self.current_user.nric)
        project_to_delete = self.view.prompt_project_selection(my_projects)
        if not project_to_delete: return

        confirm = self.view.get_input(f"WARNING: Deleting '{project_to_delete.project_name}' cannot be undone. Proceed? (y/n)")
        if confirm.lower() == 'y':
            success, message = self.projects_controller.delete_project(self.current_user, project_to_delete)
            self.view.display_message(message, error=not success)

    def handle_toggle_visibility(self):
        my_projects = self.projects_controller.get_projects_by_manager(self.current_user.nric)
        project_to_toggle = self.view.prompt_project_selection(my_projects)
        if not project_to_toggle: return

        success, message = self.projects_controller.toggle_project_visibility(self.current_user, project_to_toggle)
        self.view.display_message(message, error=not success)

    def handle_view_all_projects(self):
        all_projects = self.projects_controller.get_all_projects()

        filtered_projects = self.projects_controller.filter_projects(
            all_projects,
            location=self.user_filters.get('location'),
            flat_type=self.user_filters.get('flat_type')
        )

        self.view.display_message(f"Current Filters: {self.user_filters or 'None'}")
        if not filtered_projects:
             self.view.display_message("No projects match your criteria.")
        else:
             self.view.display_message("Displaying All Projects:")
             for project in filtered_projects:
                 self.view.display_project_details(project)

        if self.view.get_input("Update filters? (y/n)").lower() == 'y':
            self.user_filters = self.view.prompt_project_filters()
            self.view.display_message("Filters updated. View projects again to see changes.")

    def handle_view_my_projects(self):
        my_projects = self.projects_controller.get_projects_by_manager(self.current_user.nric)
        if not my_projects:
             self.view.display_message("You are not managing any projects.")
             return

        self.view.display_message("Projects You Manage:")
        for project in my_projects:
             self.view.display_project_details(project)

    def handle_view_officer_registrations(self):
        my_projects = self.projects_controller.get_projects_by_manager(self.current_user.nric)
        project_to_view = self.view.prompt_project_selection(my_projects)
        if not project_to_view: return

        registrations = self.registrations_controller.get_registrations_for_project(project_to_view.project_name)
        if not registrations:
            self.view.display_message(f"No officer registrations found for project '{project_to_view.project_name}'.")
            return

        self.view.display_message(f"Officer Registrations for '{project_to_view.project_name}':")
        for reg in registrations:
            officer = self.users_controller.find_user_by_nric(reg.officer_nric)
            if officer:
                 self.view.display_registration(reg, project_to_view, officer)
            else:
                 self.view.display_message(f"Could not display details for registration by {reg.officer_nric} (missing user data?)", error=True)

    def _select_pending_registration(self):
        """Helper for manager to select a PENDING registration."""
        my_projects = self.projects_controller.get_projects_by_manager(self.current_user.nric)
        all_pending_regs = []
        for project in my_projects:
            all_pending_regs.extend(
                self.registrations_controller.get_registrations_for_project(project.project_name, status_filter=Registration.STATUS_PENDING)
            )

        if not all_pending_regs:
            self.view.display_message("No pending officer registrations found for your projects.")
            return None

        return self.view.prompt_registration_selection(all_pending_regs)


    def handle_approve_officer_registration(self):
        registration_to_approve = self._select_pending_registration()
        if not registration_to_approve: return

        success, message = self.registrations_controller.approve_officer_registration(self.current_user, registration_to_approve)
        self.view.display_message(message, error=not success)

    def handle_reject_officer_registration(self):
        registration_to_reject = self._select_pending_registration()
        if not registration_to_reject: return

        success, message = self.registrations_controller.reject_officer_registration(self.current_user, registration_to_reject)
        self.view.display_message(message, error=not success)

    def handle_view_applications(self):
        my_projects = self.projects_controller.get_projects_by_manager(self.current_user.nric)
        project_to_view = self.view.prompt_project_selection(my_projects)
        if not project_to_view: return

        applications = self.applications_controller.get_applications_for_project(project_to_view.project_name)
        if not applications:
            self.view.display_message(f"No applications found for project '{project_to_view.project_name}'.")
            return

        self.view.display_message(f"Applications for '{project_to_view.project_name}':")
        self.view.prompt_application_selection(applications)


    def _select_pending_application(self):
        """Helper for manager to select a PENDING application."""
        my_projects = self.projects_controller.get_projects_by_manager(self.current_user.nric)
        all_pending_apps = []
        for project in my_projects:
            apps = self.applications_controller.get_applications_for_project(project.project_name)
            all_pending_apps.extend([app for app in apps if app.status == Application.STATUS_PENDING and not app.request_withdrawal])

        if not all_pending_apps:
            self.view.display_message("No pending applications found for your projects (excluding those with withdrawal requests).")
            return None

        return self.view.prompt_application_selection(all_pending_apps)

    def handle_approve_application(self):
        application_to_approve = self._select_pending_application()
        if not application_to_approve: return

        success, message = self.applications_controller.approve_application(self.current_user, application_to_approve)
        self.view.display_message(message, error=not success)

    def handle_reject_application(self):
        application_to_reject = self._select_pending_application()
        if not application_to_reject: return

        success, message = self.applications_controller.reject_application(self.current_user, application_to_reject)
        self.view.display_message(message, error=not success)

    def _select_application_with_withdrawal_request(self):
        """Helper for manager to select an application with a withdrawal request."""
        my_projects = self.projects_controller.get_projects_by_manager(self.current_user.nric)
        apps_with_request = []
        for project in my_projects:
            apps = self.applications_controller.get_applications_for_project(project.project_name)
            apps_with_request.extend([app for app in apps if app.request_withdrawal])

        if not apps_with_request:
            self.view.display_message("No applications with pending withdrawal requests found for your projects.")
            return None

        return self.view.prompt_application_selection(apps_with_request)

    def handle_approve_withdrawal(self):
        application_to_action = self._select_application_with_withdrawal_request()
        if not application_to_action: return

        success, message = self.applications_controller.approve_withdrawal(self.current_user, application_to_action)
        self.view.display_message(message, error=not success)

    def handle_reject_withdrawal(self):
        application_to_action = self._select_application_with_withdrawal_request()
        if not application_to_action: return

        success, message = self.applications_controller.reject_withdrawal(self.current_user, application_to_action)
        self.view.display_message(message, error=not success)

    def handle_generate_booking_report(self):
        filters = self.view.prompt_report_filters()
        report_data = self.applications_controller.generate_booking_report(**filters)
        headers = ["Applicant Name", "NRIC", "Age", "Marital Status", "Flat Type", "Project Name", "Neighborhood"]
        self.view.display_report("Booking Report", report_data, headers)

    def handle_view_all_enquiries(self):
        all_enquiries = self.enquiries_controller.get_all_enquiries()
        if not all_enquiries:
            self.view.display_message("There are no enquiries in the system.")
            return

        self.view.display_message("All System Enquiries:")
        for enquiry in all_enquiries:
            project = self.projects_controller.find_project_by_name(enquiry.project_name)
            applicant = self.users_controller.find_user_by_nric(enquiry.applicant_nric)
            if project and applicant:
                 self.view.display_enquiry(enquiry, project, applicant)
            else:
                 self.view.display_message(f"Could not display details for Enquiry ID {enquiry.enquiry_id} (missing project/user data?)", error=True)

    def handle_reply_enquiry_manager(self):
        handled_enquiries = self._get_enquiries_for_handled_projects(self.current_user)
        unreplied_enquiries = [e for e in handled_enquiries if not e.is_replied()]

        enquiry_to_reply = self.view.prompt_enquiry_selection(unreplied_enquiries)
        if not enquiry_to_reply:
            return

        reply_text = self.view.get_input("Enter your reply")
        success, message = self.enquiries_controller.reply_to_enquiry(self.current_user, enquiry_to_reply.enquiry_id, reply_text)
        self.view.display_message(message, error=not success)



if __name__ == "__main__":

    app = ApplicationController()
    try:
        app.run()
    except KeyboardInterrupt:
        print("\nApplication interrupted. Exiting.")
    except Exception as e:
         print(f"\nAn unexpected error occurred: {e}")
         print("Exiting.")