import os
import csv
from datetime import datetime, date

APPLICANT_CSV = 'ApplicantList.csv'
OFFICER_CSV = 'OfficerList.csv'
MANAGER_CSV = 'ManagerList.csv'
PROJECT_CSV = 'ProjectList.csv'
APPLICATION_CSV = 'ApplicationData.csv'
REGISTRATION_CSV = 'RegistrationData.csv'
ENQUIRY_CSV = 'EnquiryData.csv'

DATE_FORMAT = "%Y-%m-%d"

class Utils:
    @staticmethod
    def parse_date(date_str):
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, DATE_FORMAT).date()
        except ValueError:
            return None

    @staticmethod
    def format_date(date_obj):
        if date_obj is None:
            return ""
        return date_obj.strftime(DATE_FORMAT)

    @staticmethod
    def dates_overlap(start1, end1, start2, end2):
        if not all([start1, end1, start2, end2]):
            return False
        start1, end1 = min(start1, end1), max(start1, end1)
        start2, end2 = min(start2, end2), max(start2, end2)
        return not (end1 < start2 or start1 > end2)

    @staticmethod
    def validate_nric(nric):
        if not isinstance(nric, str) or len(nric) != 9:
            return False
        if nric[0].upper() not in ('S', 'T'):
            return False
        if not nric[1:8].isdigit():
            return False
        if not nric[8].isalpha():
            return False
        return True

    @staticmethod
    def get_valid_integer_input(prompt, min_val=None, max_val=None):
        while True:
            try:
                value = int(input(f"{prompt}: ").strip())
                if (min_val is not None and value < min_val) or \
                   (max_val is not None and value > max_val):
                    range_msg = ""
                    if min_val is not None and max_val is not None:
                        range_msg = f" between {min_val} and {max_val}"
                    elif min_val is not None:
                        range_msg = f" >= {min_val}"
                    elif max_val is not None:
                        range_msg = f" <= {max_val}"
                    print(f"ERROR: Input must be an integer{range_msg}.")
                else:
                    return value
            except ValueError:
                print("ERROR: Invalid input. Please enter an integer.")

    @staticmethod
    def get_valid_date_input(prompt):
        while True:
            date_str = input(f"{prompt} ({DATE_FORMAT}): ").strip()
            parsed = Utils.parse_date(date_str)
            if parsed:
                return parsed
            else:
                print(f"ERROR: Invalid date format. Please use {DATE_FORMAT}.")

    @staticmethod
    def get_non_empty_input(prompt):
        while True:
            value = input(f"{prompt}: ").strip()
            if value:
                return value
            else:
                print("ERROR: Input cannot be empty.")

    @staticmethod
    def get_yes_no_input(prompt):
        while True:
            choice = input(f"{prompt} (y/n): ").strip().lower()
            if choice in ['y', 'n']:
                return choice == 'y'
            print("ERROR: Please enter 'y' or 'n'.")

class DataLoadError(Exception):
    pass

class DataSaveError(Exception):
    pass

class IntegrityError(Exception):
    pass

class OperationError(Exception):
    pass

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

    def get_role(self):
        return "User"

class Applicant(User):
    def __init__(self, name, nric, age, marital_status, password):
        super().__init__(name, nric, age, marital_status, password)
    def get_role(self):
        return "Applicant"

class HDBOfficer(Applicant):
    def __init__(self, name, nric, age, marital_status, password):
        super().__init__(name, nric, age, marital_status, password)

    def get_role(self):
        return "HDB Officer"

class HDBManager(User):
    def __init__(self, name, nric, age, marital_status, password):
        super().__init__(name, nric, age, marital_status, password)
    
    def get_role(self):
        return "HDB Manager"

class Project:
    def __init__(self, project_name, neighborhood, type1, num_units1, price1,
                 type2, num_units2, price2, opening_date, closing_date,
                 manager_nric, officer_slot, officer_nrics=None, visibility=True):
        self.project_name = project_name
        self.neighborhood = neighborhood
        self.type1 = type1
        self.num_units1 = int(num_units1)
        self.price1 = int(price1)
        self.type2 = type2
        self.num_units2 = int(num_units2)
        self.price2 = int(price2)
        self.opening_date = opening_date
        self.closing_date = closing_date
        self.manager_nric = manager_nric
        self.officer_slot = int(officer_slot)
        self.officer_nrics = officer_nrics if officer_nrics is not None else []
        self.visibility = visibility

    def is_active_period(self, check_date):
        return self.opening_date and self.closing_date and (self.opening_date <= check_date <= self.closing_date)

    def is_currently_active_for_application(self):
        """Checks if the project is visible AND within its application period right now."""
        return self.visibility and self.is_active_period(date.today())

    def get_flat_details(self, flat_type_room):
        if flat_type_room == 2:
            return self.num_units1, self.price1
        elif flat_type_room == 3:
            return self.num_units2, self.price2
        return 0, 0

    def decrease_unit_count(self, flat_type_room):
        if flat_type_room == 2:
            if self.num_units1 > 0:
                self.num_units1 -= 1
                return True
        elif flat_type_room == 3:
            if self.num_units2 > 0:
                self.num_units2 -= 1
                return True
        return False

    def increase_unit_count(self, flat_type_room):
        if flat_type_room == 2:
            self.num_units1 += 1
            return True
        elif flat_type_room == 3:
            self.num_units2 += 1
            return True
        return False

    def can_add_officer(self):
        return len(self.officer_nrics) < self.officer_slot

class Application:
    STATUS_PENDING = "PENDING"
    STATUS_SUCCESSFUL = "SUCCESSFUL"
    STATUS_UNSUCCESSFUL = "UNSUCCESSFUL"
    STATUS_BOOKED = "BOOKED"
    VALID_STATUSES = [STATUS_PENDING, STATUS_SUCCESSFUL, STATUS_UNSUCCESSFUL, STATUS_BOOKED]

    def __init__(self, applicant_nric, project_name, flat_type, status=STATUS_PENDING, request_withdrawal=False):
        self.applicant_nric = applicant_nric
        self.project_name = project_name
        self.flat_type = int(flat_type)
        self.status = status if status in self.VALID_STATUSES else self.STATUS_PENDING
        self.request_withdrawal = request_withdrawal

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
        self.enquiry_id = int(enquiry_id)
        self.applicant_nric = applicant_nric
        self.project_name = project_name
        self.text = text
        self.reply = reply

    def is_replied(self):
        return bool(self.reply)

class BaseRepository:
    def __init__(self, csv_file, model_class, required_headers):
        self.csv_file = csv_file
        self.model_class = model_class
        self.required_headers = required_headers
        self.data = {}
        self._load_data()

    def _ensure_file_exists(self):
        if not os.path.exists(self.csv_file):
            print(f"Warning: Data file not found: {self.csv_file}. Creating empty file.")
            try:
                with open(self.csv_file, 'w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(self.required_headers)
            except IOError as e:
                raise DataSaveError(f"Error creating data file {self.csv_file}: {e}")

    def _load_data(self):
        self._ensure_file_exists()
        self.data = {}
        try:
            with open(self.csv_file, 'r', newline='') as file:
                reader = csv.reader(file)
                header = next(reader, None)

                if not header or not all(h in header for h in self.required_headers):
                    raise DataLoadError(f"Invalid or missing headers in {self.csv_file}. Expected: {self.required_headers}, Found: {header}")

                header_map = {h: i for i, h in enumerate(header)}

                for i, row in enumerate(reader):
                    if len(row) < len(header):
                        print(f"Warning: Skipping short row {i+1} in {self.csv_file}: {row}")
                        continue

                    row_dict = {}
                    valid_row = True
                    for req_h in self.required_headers:
                        try:
                            idx = header_map[req_h]
                            row_dict[req_h] = row[idx]
                        except (IndexError, KeyError):
                            print(f"Warning: Missing expected column '{req_h}' in row {i+1} of {self.csv_file}. Skipping.")
                            valid_row = False
                            break
                    if not valid_row:
                        continue

                    try:
                        instance = self._create_instance(row_dict)
                        key = self._get_key(instance)
                        if key in self.data:
                            if self.model_class in [User, Project, Applicant, HDBOfficer, HDBManager]:
                                raise IntegrityError(f"Duplicate key '{key}' found for critical data in {self.csv_file}. Aborting load.")
                            else:
                                print(f"Warning: Duplicate key '{key}' found in {self.csv_file}. Overwriting with row {i+1}.")
                        self.data[key] = instance
                    except (ValueError, TypeError, IndexError, IntegrityError) as e:
                        print(f"Warning: Error processing row {i+1} in {self.csv_file}: {row}. Error: {e}. Skipping.")
                    except Exception as e:
                        print(f"Warning: Unexpected error processing row {i+1} in {self.csv_file}: {row}. Error: {e}. Skipping.")

        except FileNotFoundError:
            print(f"Info: Data file {self.csv_file} was not found, created empty.")
        except StopIteration:
            print(f"Info: Data file {self.csv_file} is empty or contains only a header.")
        except IOError as e:
            raise DataLoadError(f"Error reading data file {self.csv_file}: {e}")
        except IntegrityError as e:
             raise DataLoadError(f"Fatal integrity error loading {self.csv_file}: {e}")
        except Exception as e:
            raise DataLoadError(f"Unexpected error loading data from {self.csv_file}: {e}")
        print(f"Loaded {len(self.data)} items from {self.csv_file}.")

    def save_data(self):
        try:
            with open(self.csv_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(self.required_headers)
                sorted_keys = sorted(self.data.keys())
                for key in sorted_keys:
                    writer.writerow(self._get_row_data(self.data[key]))
        except IOError as e:
            raise DataSaveError(f"Error saving data to {self.csv_file}: {e}")
        except Exception as e:
            raise DataSaveError(f"Unexpected error saving data to {self.csv_file}: {e}")

    def get_all(self):
        return list(self.data.values())

    def find_by_key(self, key):
        return self.data.get(key)

    def add(self, item):
        key = self._get_key(item)
        if key in self.data:
            raise IntegrityError(f"Item with key '{key}' already exists in {self.csv_file}.")
        self.data[key] = item
        self.save_data()

    def update(self, item):
        key = self._get_key(item)
        if key not in self.data:
            raise IntegrityError(f"Item with key '{key}' not found for update in {self.csv_file}.")
        self.data[key] = item
        self.save_data()

    def delete(self, key):
        if key not in self.data:
            raise IntegrityError(f"Item with key '{key}' not found for deletion in {self.csv_file}.")
        del self.data[key]
        self.save_data()

class UserRepository:
    def __init__(self):
        self.applicant_repo = self._create_sub_repo(APPLICANT_CSV, Applicant, ['Name', 'NRIC', 'Age', 'Marital Status', 'Password'])
        self.officer_repo = self._create_sub_repo(OFFICER_CSV, HDBOfficer, ['Name', 'NRIC', 'Age', 'Marital Status', 'Password'])
        self.manager_repo = self._create_sub_repo(MANAGER_CSV, HDBManager, ['Name', 'NRIC', 'Age', 'Marital Status', 'Password'])
        self._merge_users()

    def _create_sub_repo(self, csv_file, model_class, headers):
        class SubUserRepository(BaseRepository):
            def _get_key(self, item):
                return item.nric
            def _create_instance(self, row_dict):
                if not Utils.validate_nric(row_dict['NRIC']):
                    raise ValueError(f"Invalid NRIC format: {row_dict['NRIC']}")
                return model_class(
                    row_dict['Name'], row_dict['NRIC'], row_dict['Age'],
                    row_dict['Marital Status'], row_dict['Password']
                )
            def _get_row_data(self, item):
                return [item.name, item.nric, str(item.age), item.marital_status, item.password]
        return SubUserRepository(csv_file, model_class, headers)

    def _merge_users(self):
        self.users = {}
        self.users.update(self.applicant_repo.data)
        self.users.update(self.officer_repo.data)
        self.users.update(self.manager_repo.data)
        total_unique = len(self.applicant_repo.data) + len(self.officer_repo.data) + len(self.manager_repo.data)
        if len(self.users) != total_unique:
             print("Warning: Duplicate NRICs found across different user type files. Check data integrity.")
        print(f"Total unique users loaded: {len(self.users)}")

    def find_user_by_nric(self, nric):
        return self.users.get(nric)

    def get_all_users(self):
        return list(self.users.values())

    def save_user(self, user):
        if isinstance(user, HDBManager):
            repo = self.manager_repo
        elif isinstance(user, HDBOfficer):
            repo = self.officer_repo
        elif isinstance(user, Applicant):
            repo = self.applicant_repo
        else:
            raise TypeError("Unknown user type cannot be saved.")

        try:
            repo.update(user)
            self.users[user.nric] = user
        except IntegrityError:
             raise OperationError(f"Failed to save user {user.nric}. User not found in specific repository.")
        except Exception as e:
             raise DataSaveError(f"Failed to save user {user.nric}: {e}")

class ProjectRepository(BaseRepository):
    def __init__(self, csv_file=PROJECT_CSV):
        headers = [
            'Project Name', 'Neighborhood', 'Type 1', 'Number of units for Type 1',
            'Selling price for Type 1', 'Type 2', 'Number of units for Type 2',
            'Selling price for Type 2', 'Application opening date',
            'Application closing date', 'Manager', 'Officer Slot', 'Officer', 'Visibility'
        ]
        super().__init__(csv_file, Project, headers)

    def _get_key(self, item):
        return item.project_name

    def _create_instance(self, row_dict):
        opening_date = Utils.parse_date(row_dict['Application opening date'])
        closing_date = Utils.parse_date(row_dict['Application closing date'])
        visibility = row_dict.get('Visibility', 'True').lower() == 'true'
        officer_nrics = [nric.strip() for nric in row_dict.get('Officer', '').split(',') if nric.strip()]

        return Project(
            row_dict['Project Name'], row_dict['Neighborhood'],
            row_dict['Type 1'], int(row_dict['Number of units for Type 1']), int(row_dict['Selling price for Type 1']),
            row_dict['Type 2'], int(row_dict['Number of units for Type 2']), int(row_dict['Selling price for Type 2']),
            opening_date, closing_date,
            row_dict['Manager'], int(row_dict['Officer Slot']),
            officer_nrics, visibility
        )

    def _get_row_data(self, item):
        return [
            item.project_name, item.neighborhood,
            item.type1, str(item.num_units1), str(item.price1),
            item.type2, str(item.num_units2), str(item.price2),
            Utils.format_date(item.opening_date), Utils.format_date(item.closing_date),
            item.manager_nric, str(item.officer_slot),
            ','.join(item.officer_nrics), str(item.visibility)
        ]

    def find_by_name(self, name):
        return self.find_by_key(name)

    def delete_by_name(self, name):
        self.delete(name)

class ApplicationRepository(BaseRepository):
    def __init__(self, csv_file=APPLICATION_CSV):
        headers = ['ApplicantNRIC', 'ProjectName', 'FlatType', 'Status', 'RequestWithdrawal']
        super().__init__(csv_file, Application, headers)

    def _get_key(self, item):
        return f"{item.applicant_nric}-{item.project_name}"

    def _create_instance(self, row_dict):
        flat_type = int(row_dict['FlatType'])
        if flat_type not in [2, 3]: raise ValueError("Invalid flat type")
        request_withdrawal = row_dict.get('RequestWithdrawal', 'False').lower() == 'true'
        return Application(
            row_dict['ApplicantNRIC'], row_dict['ProjectName'], flat_type,
            row_dict['Status'], request_withdrawal
        )

    def _get_row_data(self, item):
        return [
            item.applicant_nric, item.project_name, str(item.flat_type),
            item.status, str(item.request_withdrawal)
        ]


    def find_by_applicant_nric(self, nric):
        for app in self.data.values():
            if app.applicant_nric == nric and app.status != Application.STATUS_UNSUCCESSFUL:
                return app
        return None

    def find_by_project_name(self, project_name):
        return [app for app in self.data.values() if app.project_name == project_name]

    def add(self, item):
        existing_active = self.find_by_applicant_nric(item.applicant_nric)
        if existing_active:
            raise IntegrityError(f"Applicant {item.applicant_nric} already has an active application for project {existing_active.project_name}.")
        super().add(item)

class RegistrationRepository(BaseRepository):
    def __init__(self, csv_file=REGISTRATION_CSV):
        headers = ['OfficerNRIC', 'ProjectName', 'Status']
        super().__init__(csv_file, Registration, headers)

    def _get_key(self, item):
        return f"{item.officer_nric}-{item.project_name}"

    def _create_instance(self, row_dict):
        return Registration(row_dict['OfficerNRIC'], row_dict['ProjectName'], row_dict['Status'])

    def _get_row_data(self, item):
        return [item.officer_nric, item.project_name, item.status]


    def find_by_officer_and_project(self, officer_nric, project_name):
        key = f"{officer_nric}-{project_name}"
        return self.find_by_key(key)

    def find_by_officer(self, officer_nric):
        return [reg for reg in self.data.values() if reg.officer_nric == officer_nric]

    def find_by_project(self, project_name, status_filter=None):
        regs = [reg for reg in self.data.values() if reg.project_name == project_name]
        if status_filter:
            regs = [reg for reg in regs if reg.status == status_filter]
        return regs

class EnquiryRepository(BaseRepository):
    def __init__(self, csv_file=ENQUIRY_CSV):
        headers = ['EnquiryID', 'ApplicantNRIC', 'ProjectName', 'Text', 'Reply']
        super().__init__(csv_file, Enquiry, headers)
        self.next_id = self._calculate_next_id()

    def _calculate_next_id(self):
        if not self.data:
            return 1
        return max(int(k) for k in self.data.keys()) + 1

    def _get_key(self, item):
        return item.enquiry_id

    def _create_instance(self, row_dict):
        return Enquiry(
            int(row_dict['EnquiryID']), row_dict['ApplicantNRIC'], row_dict['ProjectName'],
            row_dict['Text'], row_dict.get('Reply', '')
        )

    def _get_row_data(self, item):
        return [
            str(item.enquiry_id), item.applicant_nric, item.project_name,
            item.text, item.reply
        ]

    def add(self, item):
        item.enquiry_id = self.next_id
        super().add(item)
        self.next_id += 1

    def find_by_id(self, enquiry_id):
        try:
            return self.find_by_key(int(enquiry_id))
        except ValueError:
            return None

    def find_by_applicant(self, applicant_nric):
        return [enq for enq in self.data.values() if enq.applicant_nric == applicant_nric]

    def find_by_project(self, project_name):
        return [enq for enq in self.data.values() if enq.project_name == project_name]

    def delete_by_id(self, enquiry_id):
        try:
            self.delete(int(enquiry_id))
        except ValueError:
            raise IntegrityError(f"Invalid Enquiry ID format for deletion: {enquiry_id}")
        except IntegrityError:
             raise IntegrityError(f"Enquiry with ID '{enquiry_id}' not found for deletion.")

class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def login(self, nric, password):
        if not Utils.validate_nric(nric):
            raise OperationError("Invalid NRIC format.")
        user = self.user_repository.find_user_by_nric(nric)
        if user and user.password == password:
            return user
        elif user:
            raise OperationError("Incorrect password.")
        else:
            raise OperationError("NRIC not found.")

    def change_password(self, user: User, new_password):
        if not new_password:
            raise OperationError("Password cannot be empty.")
        user.password = new_password
        try:
            self.user_repository.save_user(user)
        except Exception as e:
            raise OperationError(f"Failed to save new password: {e}")

    def get_user_role(self, user: User):
        if isinstance(user, HDBManager):
            return "HDB Manager"
        elif isinstance(user, HDBOfficer):
            return "HDB Officer"
        elif isinstance(user, Applicant):
            return "Applicant"
        return "Unknown"

class ProjectService:
    def __init__(self, project_repository: ProjectRepository,
                 registration_repository: RegistrationRepository):
        self.project_repository = project_repository
        self.registration_repository = registration_repository

    def find_project_by_name(self, name):
        return self.project_repository.find_by_name(name)

    def get_all_projects(self):
        return sorted(self.project_repository.get_all(), key=lambda p: p.project_name)

    def get_projects_by_manager(self, manager_nric):
        return sorted(
            [p for p in self.get_all_projects() if p.manager_nric == manager_nric],
            key=lambda p: p.project_name
        )

    def get_handled_project_names_for_officer(self, officer_nric):
        """Gets names of projects an officer is approved for or assigned to."""
        handled_project_names = set()
        approved_regs = self.registration_repository.find_by_project(None, status_filter=Registration.STATUS_APPROVED)
        handled_project_names.update(reg.project_name for reg in approved_regs if reg.officer_nric == officer_nric)
        for p in self.get_all_projects():
            if officer_nric in p.officer_nrics:
                handled_project_names.add(p.project_name)
        return handled_project_names

    def get_viewable_projects_for_applicant(self, applicant: Applicant, current_application: Application = None):
        viewable = []
        applicant_applied_project_name = current_application.project_name if current_application else None

        for project in self.get_all_projects():
            is_project_applied_for = project.project_name == applicant_applied_project_name

            if is_project_applied_for:
                viewable.append(project)
                continue

            if not project.is_currently_active_for_application():
                continue

            can_view_any_flat = False
            if applicant.marital_status == "Single" and applicant.age >= 35:
                can_view_any_flat = True
            elif applicant.marital_status == "Married" and applicant.age >= 21:
                 can_view_any_flat = True

            if not can_view_any_flat and project.num_units1 == 0:
                continue
            if can_view_any_flat and project.num_units2 == 0 and project.num_units1 == 0:
                continue

            viewable.append(project)

        return sorted(list({p.project_name: p for p in viewable}.values()), key=lambda p: p.project_name)

    def filter_projects(self, projects, location=None, flat_type=None):
        filtered = list(projects)
        if location:
            filtered = [p for p in filtered if p.neighborhood.lower() == location.lower()]
        if flat_type:
            try:
                flat_type_room = int(flat_type)
                if flat_type_room == 2:
                    filtered = [p for p in filtered if p.num_units1 > 0]
                elif flat_type_room == 3:
                    filtered = [p for p in filtered if p.num_units2 > 0]
            except ValueError:
                print(f"Warning: Invalid flat type filter '{flat_type}'. Ignoring filter.")
                pass
        return filtered

    def check_manager_project_overlap(self, manager_nric, new_opening_date, new_closing_date, project_to_exclude=None):
        for existing_project in self.get_projects_by_manager(manager_nric):
            if existing_project == project_to_exclude:
                continue

            is_existing_active_today = existing_project.visibility and existing_project.is_active_period(date.today())

            if is_existing_active_today and \
               Utils.dates_overlap(new_opening_date, new_closing_date,
                                   existing_project.opening_date, existing_project.closing_date):
                return existing_project
        return None

    def create_project(self, manager: HDBManager, name, neighborhood, n1, p1, n2, p2, od, cd, slot):
        if self.find_project_by_name(name):
            raise OperationError(f"Project name '{name}' already exists.")
        if not (isinstance(od, date) and isinstance(cd, date) and cd >= od):
            raise OperationError("Invalid opening or closing date (must be Date objects, close >= open).")
        if not (0 <= slot <= 10):
            raise OperationError("Officer slots must be between 0 and 10.")
        if any(n < 0 for n in [n1, p1, n2, p2]):
            raise OperationError("Unit counts and prices cannot be negative.")

        conflicting_project = self.check_manager_project_overlap(manager.nric, od, cd)
        if conflicting_project:
            raise OperationError(f"Manager already handles an active project ('{conflicting_project.project_name}') during this period.")

        new_project = Project(
            name, neighborhood, "2-Room", n1, p1, "3-Room", n2, p2,
            od, cd, manager.nric, slot, [], True
        )
        try:
            self.project_repository.add(new_project)
            return new_project
        except Exception as e:
            raise OperationError(f"Failed to create project: {e}")

    def edit_project(self, manager: HDBManager, project: Project, updates: dict):
        if project.manager_nric != manager.nric:
            raise OperationError("You can only edit projects you manage.")

        original_name = project.project_name
        new_name = updates.get('name', project.project_name)
        if new_name != original_name and self.find_project_by_name(new_name):
            raise OperationError(f"Project name '{new_name}' already exists.")

        project.project_name = new_name
        project.neighborhood = updates.get('neighborhood', project.neighborhood)

        n1 = updates.get('n1', project.num_units1)
        p1 = updates.get('p1', project.price1)
        n2 = updates.get('n2', project.num_units2)
        p2 = updates.get('p2', project.price2)
        slot = updates.get('officerSlot', project.officer_slot)

        if any(val is not None and val < 0 for val in [n1, p1, n2, p2]):
            raise OperationError("Unit counts and prices cannot be negative.")
        if slot is not None and not (0 <= slot <= 10):
            raise OperationError("Officer slots must be between 0 and 10.")
        if slot is not None and slot < len(project.officer_nrics):
            raise OperationError(f"Cannot reduce slots below current number of assigned officers ({len(project.officer_nrics)}).")

        project.num_units1 = n1 if n1 is not None else project.num_units1
        project.price1 = p1 if p1 is not None else project.price1
        project.num_units2 = n2 if n2 is not None else project.num_units2
        project.price2 = p2 if p2 is not None else project.price2
        project.officer_slot = slot if slot is not None else project.officer_slot

        new_od = updates.get('openDate', project.opening_date)
        new_cd = updates.get('closeDate', project.closing_date)
        if not (isinstance(new_od, date) and isinstance(new_cd, date) and new_cd >= new_od):
            raise OperationError("Invalid opening or closing date (must be Date objects, close >= open).")

        if new_od != project.opening_date or new_cd != project.closing_date:
            conflicting_project = self.check_manager_project_overlap(manager.nric, new_od, new_cd, project_to_exclude=project)
            if conflicting_project:
                raise OperationError(f"Edited dates overlap with another active project ('{conflicting_project.project_name}') you manage.")

        project.opening_date = new_od
        project.closing_date = new_cd

        try:
            if project.project_name != original_name:
                self.project_repository.delete_by_name(original_name)
                self.project_repository.add(project)
            else:
                self.project_repository.update(project)
        except Exception as e:
            raise OperationError(f"Failed to save project updates: {e}")

    def delete_project(self, manager: HDBManager, project: Project):
        if project.manager_nric != manager.nric:
            raise OperationError("You can only delete projects you manage.")
        try:
            self.project_repository.delete_by_name(project.project_name)
        except Exception as e:
            raise OperationError(f"Failed to delete project: {e}")

    def toggle_project_visibility(self, manager: HDBManager, project: Project):
        if project.manager_nric != manager.nric:
            raise OperationError("You can only toggle visibility for projects you manage.")
        project.visibility = not project.visibility
        try:
            self.project_repository.update(project)
            return "ON" if project.visibility else "OFF"
        except Exception as e:
            project.visibility = not project.visibility
            raise OperationError(f"Failed to update project visibility: {e}")

    def add_officer_to_project(self, project: Project, officer_nric):
        """Adds an officer NRIC directly to the project's list (manager action)."""
        if officer_nric not in project.officer_nrics:
            if project.can_add_officer():
                project.officer_nrics.append(officer_nric)
                try:
                    self.project_repository.update(project)
                    return True
                except Exception as e:
                    project.officer_nrics.remove(officer_nric)
                    print(f"Error saving project after adding officer: {e}")
                    return False
            else:
                print(f"Warning: Cannot add officer {officer_nric}, no slots available in {project.project_name}.")
                return False
        return True

    def remove_officer_from_project(self, project: Project, officer_nric):
        """Removes an officer NRIC directly from the project's list (manager action)."""
        if officer_nric in project.officer_nrics:
            project.officer_nrics.remove(officer_nric)
            try:
                self.project_repository.update(project)
                return True
            except Exception as e:
                project.officer_nrics.append(officer_nric)
                print(f"Error saving project after removing officer: {e}")
                return False
        return True

class ApplicationService:
    def __init__(self, application_repository: ApplicationRepository,
                 project_service: ProjectService,
                 registration_service: 'RegistrationService'):
        self.application_repository = application_repository
        self.project_service = project_service
        self.registration_service = registration_service

    def find_application_by_applicant(self, applicant_nric):
        return self.application_repository.find_by_applicant_nric(applicant_nric)

    def get_applications_for_project(self, project_name):
        return self.application_repository.find_by_project_name(project_name)

    def get_all_applications(self):
        return self.application_repository.get_all()

    def _check_applicant_eligibility(self, applicant: Applicant, project: Project, flat_type: int):
        if not project.is_currently_active_for_application():
            raise OperationError("Project is not currently open for applications.")

        if self.find_application_by_applicant(applicant.nric):
            raise OperationError("You already have an active BTO application.")

        if applicant.marital_status == "Single":
            if applicant.age < 35:
                raise OperationError("Single applicants must be at least 35 years old.")
            if flat_type != 2:
                raise OperationError("Single applicants can only apply for 2-Room flats.")
        elif applicant.marital_status == "Married":
            if applicant.age < 21:
                raise OperationError("Married applicants must be at least 21 years old.")
            if flat_type not in [2, 3]:
                raise OperationError("Invalid flat type selected.")
        else:
            raise OperationError("Invalid marital status for application.")

        units, _ = project.get_flat_details(flat_type)
        if units <= 0:
            raise OperationError(f"No {flat_type}-Room units available in this project.")

        if isinstance(applicant, HDBOfficer):
            existing_registration = self.registration_service.find_registration(applicant.nric, project.project_name)
            if existing_registration:
                raise OperationError("You cannot apply for a project you have registered (or been approved) as an officer for.")

    def apply_for_project(self, applicant: Applicant, project: Project, flat_type: int):
        if isinstance(applicant, HDBManager):
            raise OperationError("HDB Managers cannot apply for BTO projects.")

        self._check_applicant_eligibility(applicant, project, flat_type)

        new_application = Application(applicant.nric, project.project_name, flat_type)
        try:
            self.application_repository.add(new_application)
            return new_application
        except IntegrityError as e:
            raise OperationError(f"Failed to submit application: {e}")
        except Exception as e:
            raise OperationError(f"An unexpected error occurred during application submission: {e}")

    def request_withdrawal(self, application: Application):
        if application.status not in [Application.STATUS_PENDING, Application.STATUS_SUCCESSFUL, Application.STATUS_BOOKED]:
            raise OperationError(f"Cannot request withdrawal for an application with status '{application.status}'.")
        if application.request_withdrawal:
            raise OperationError("Withdrawal already requested for this application.")

        application.request_withdrawal = True
        try:
            self.application_repository.update(application)
        except Exception as e:
            application.request_withdrawal = False
            raise OperationError(f"Failed to save withdrawal request: {e}")

    def _manager_can_manage_app(self, manager: HDBManager, application: Application):
        project = self.project_service.find_project_by_name(application.project_name)
        return project and project.manager_nric == manager.nric

    def manager_approve_application(self, manager: HDBManager, application: Application):
        if not self._manager_can_manage_app(manager, application):
            raise OperationError("You can only approve applications for projects you manage.")
        if application.status != Application.STATUS_PENDING:
            raise OperationError(f"Application status is not {Application.STATUS_PENDING}.")
        if application.request_withdrawal:
            raise OperationError("Cannot approve an application with a pending withdrawal request.")

        project = self.project_service.find_project_by_name(application.project_name)
        if not project:
             raise IntegrityError(f"Project {application.project_name} not found for application.")

        units, _ = project.get_flat_details(application.flat_type)
        if units <= 0:
            application.status = Application.STATUS_UNSUCCESSFUL
            self.application_repository.update(application)
            raise OperationError(f"No {application.flat_type}-Room units available. Application automatically rejected.")

        application.status = Application.STATUS_SUCCESSFUL
        try:
            self.application_repository.update(application)
        except Exception as e:
            application.status = Application.STATUS_PENDING
            raise OperationError(f"Failed to save application approval: {e}")

    def manager_reject_application(self, manager: HDBManager, application: Application):
        if not self._manager_can_manage_app(manager, application):
            raise OperationError("You can only reject applications for projects you manage.")
        if application.status != Application.STATUS_PENDING:
            raise OperationError(f"Application status is not {Application.STATUS_PENDING}.")

        application.status = Application.STATUS_UNSUCCESSFUL
        try:
            self.application_repository.update(application)
        except Exception as e:
            application.status = Application.STATUS_PENDING
            raise OperationError(f"Failed to save application rejection: {e}")

    def manager_approve_withdrawal(self, manager: HDBManager, application: Application):
        if not self._manager_can_manage_app(manager, application):
            raise OperationError("You can only approve withdrawals for projects you manage.")
        if not application.request_withdrawal:
            raise OperationError("No withdrawal request is pending for this application.")

        original_status = application.status
        application.status = Application.STATUS_UNSUCCESSFUL
        application.request_withdrawal = False
        try:
            self.application_repository.update(application)
        except Exception as e:
            application.status = original_status
            application.request_withdrawal = True
            raise OperationError(f"Failed to save withdrawal approval: {e}")

    def manager_reject_withdrawal(self, manager: HDBManager, application: Application):
        if not self._manager_can_manage_app(manager, application):
            raise OperationError("You can only reject withdrawals for projects you manage.")
        if not application.request_withdrawal:
            raise OperationError("No withdrawal request is pending for this application.")

        application.request_withdrawal = False
        try:
            self.application_repository.update(application)
        except Exception as e:
            application.request_withdrawal = True
            raise OperationError(f"Failed to save withdrawal rejection: {e}")

    def officer_book_flat(self, officer: HDBOfficer, application: Application):
        project = self.project_service.find_project_by_name(application.project_name)
        if not project:
            raise OperationError("Project associated with application not found.")

        handled_project_names = self.project_service.get_handled_project_names_for_officer(officer.nric)
        if project.project_name not in handled_project_names:
            raise OperationError("You do not handle the project for this application.")

        if application.status != Application.STATUS_SUCCESSFUL:
            raise OperationError(f"Application status must be '{Application.STATUS_SUCCESSFUL}' to book. Current status: '{application.status}'.")

        original_status = application.status
        unit_decreased = project.decrease_unit_count(application.flat_type)

        if not unit_decreased:
            application.status = Application.STATUS_UNSUCCESSFUL
            try:
                self.application_repository.update(application)
            except Exception as e:
                print(f"CRITICAL ERROR: Failed to mark application unsuccessful after booking failure: {e}")
            raise OperationError(f"Booking failed: No {application.flat_type}-Room units available anymore. Application marked unsuccessful.")

        application.status = Application.STATUS_BOOKED
        try:
            self.project_service.project_repository.update(project)
            try:
                self.application_repository.update(application)
            except Exception as app_save_e:
                print(f"ERROR: Failed to save application status update after booking: {app_save_e}. Attempting project revert.")
                project.increase_unit_count(application.flat_type)
                try:
                    self.project_service.project_repository.update(project)
                except Exception as proj_revert_e:
                    print(f"CRITICAL ERROR: Failed to revert project unit count after application save failure: {proj_revert_e}")
                application.status = original_status
                raise OperationError(f"Booking partially failed: Unit count updated, but application status save failed: {app_save_e}")

        except Exception as proj_save_e:
            project.increase_unit_count(application.flat_type)
            application.status = original_status
            print(f"ERROR: Failed to save project unit count update during booking: {proj_save_e}")
            raise OperationError(f"Booking failed: Could not update project unit count: {proj_save_e}")

        return project

class RegistrationService:
    def __init__(self, registration_repository: RegistrationRepository,
                 project_service: ProjectService,
                 application_repository: ApplicationRepository):
        self.registration_repository = registration_repository
        self.project_service = project_service
        self.application_repository = application_repository

    def find_registration(self, officer_nric, project_name):
        return self.registration_repository.find_by_officer_and_project(officer_nric, project_name)

    def get_registrations_by_officer(self, officer_nric):
        return self.registration_repository.find_by_officer(officer_nric)

    def get_registrations_for_project(self, project_name, status_filter=None):
        return self.registration_repository.find_by_project(project_name, status_filter)

    def is_approved_officer_for_project(self, officer_nric, project_name):
        reg = self.find_registration(officer_nric, project_name)
        return reg and reg.status == Registration.STATUS_APPROVED

    def _check_officer_registration_eligibility(self, officer: HDBOfficer, project: Project):
        if self.find_registration(officer.nric, project.project_name):
            raise OperationError("You have already submitted a registration for this project.")

        if project.manager_nric == officer.nric:
            raise OperationError("Managers cannot register as officers for their own projects.")

        application = self.application_repository.find_by_applicant_nric(officer.nric)
        if application and application.project_name == project.project_name:
            raise OperationError("You cannot register as an officer for a project you have applied for.")

        target_od = project.opening_date
        target_cd = project.closing_date
        if not target_od or not target_cd:
            raise OperationError("Target project has invalid application dates.")

        for reg in self.get_registrations_by_officer(officer.nric):
            if reg.status == Registration.STATUS_APPROVED:
                other_project = self.project_service.find_project_by_name(reg.project_name)
                if other_project and other_project.opening_date and other_project.closing_date:
                    if Utils.dates_overlap(target_od, target_cd, other_project.opening_date, other_project.closing_date):
                        raise OperationError(f"You are already an approved officer for another project ('{other_project.project_name}') with an overlapping application period.")

    def officer_register_for_project(self, officer: HDBOfficer, project: Project):
        self._check_officer_registration_eligibility(officer, project)

        new_registration = Registration(officer.nric, project.project_name)
        try:
            self.registration_repository.add(new_registration)
            return new_registration
        except Exception as e:
            raise OperationError(f"Failed to submit registration: {e}")

    def _manager_can_manage_reg(self, manager: HDBManager, registration: Registration):
        project = self.project_service.find_project_by_name(registration.project_name)
        return project and project.manager_nric == manager.nric

    def manager_approve_officer_registration(self, manager: HDBManager, registration: Registration):
        if not self._manager_can_manage_reg(manager, registration):
            raise OperationError("You can only approve registrations for projects you manage.")
        if registration.status != Registration.STATUS_PENDING:
            raise OperationError(f"Registration status is not {Registration.STATUS_PENDING}.")

        project = self.project_service.find_project_by_name(registration.project_name)
        if not project:
            raise OperationError(f"Project '{registration.project_name}' not found.")

        if not project.can_add_officer():
            raise OperationError("No available officer slots in this project.")

        target_od = project.opening_date
        target_cd = project.closing_date
        if not target_od or not target_cd:
             raise OperationError("Target project has invalid application dates.")

        for other_reg in self.get_registrations_by_officer(registration.officer_nric):
            if other_reg != registration and other_reg.status == Registration.STATUS_APPROVED:
                other_project = self.project_service.find_project_by_name(other_reg.project_name)
                if other_project and other_project.opening_date and other_project.closing_date:
                    if Utils.dates_overlap(target_od, target_cd, other_project.opening_date, other_project.closing_date):
                        raise OperationError(f"Officer is already approved for another project ('{other_project.project_name}') with an overlapping period.")

        original_status = registration.status
        registration.status = Registration.STATUS_APPROVED

        added_to_project = self.project_service.add_officer_to_project(project, registration.officer_nric)

        if not added_to_project:
            registration.status = original_status
            raise OperationError("Failed to add officer to project list (save failed?), approval aborted.")

        try:
            self.registration_repository.update(registration)
        except Exception as e:
            print(f"ERROR: Failed to save registration status after approval: {e}. Attempting project revert.")
            self.project_service.remove_officer_from_project(project, registration.officer_nric)
            registration.status = original_status
            raise OperationError(f"Approval partially failed: Officer added to project, but registration save failed: {e}")

    def manager_reject_officer_registration(self, manager: HDBManager, registration: Registration):
        if not self._manager_can_manage_reg(manager, registration):
            raise OperationError("You can only reject registrations for projects you manage.")
        if registration.status != Registration.STATUS_PENDING:
            raise OperationError(f"Registration status is not {Registration.STATUS_PENDING}.")

        registration.status = Registration.STATUS_REJECTED
        try:
            self.registration_repository.update(registration)
        except Exception as e:
            registration.status = Registration.STATUS_PENDING
            raise OperationError(f"Failed to save registration rejection: {e}")

class EnquiryService:
    def __init__(self, enquiry_repository: EnquiryRepository,
                 project_service: ProjectService,
                 user_repository: UserRepository):
        self.enquiry_repository = enquiry_repository
        self.project_service = project_service
        self.user_repository = user_repository

    def find_enquiry_by_id(self, enquiry_id):
        return self.enquiry_repository.find_by_id(enquiry_id)

    def get_enquiries_by_applicant(self, applicant_nric):
        return sorted(self.enquiry_repository.find_by_applicant(applicant_nric), key=lambda e: e.enquiry_id)

    def get_enquiries_for_project(self, project_name):
        return sorted(self.enquiry_repository.find_by_project(project_name), key=lambda e: e.enquiry_id)

    def get_all_enquiries(self):
        return sorted(self.enquiry_repository.get_all(), key=lambda e: e.enquiry_id)

    def submit_enquiry(self, applicant: Applicant, project: Project, text: str):
        if not text or text.isspace():
            raise OperationError("Enquiry text cannot be empty.")

        viewable_projects = self.project_service.get_viewable_projects_for_applicant(applicant)
        if project not in viewable_projects:
             current_app = self.application_repository.find_by_applicant_nric(applicant.nric)
             if not (current_app and current_app.project_name == project.project_name):
                  raise OperationError("You cannot submit an enquiry for a project you cannot view.")


        new_enquiry = Enquiry(0, applicant.nric, project.project_name, text)
        try:
            self.enquiry_repository.add(new_enquiry)
            return new_enquiry
        except Exception as e:
            raise OperationError(f"Failed to submit enquiry: {e}")

    def edit_enquiry(self, applicant: Applicant, enquiry: Enquiry, new_text: str):
        if enquiry.applicant_nric != applicant.nric:
            raise OperationError("You can only edit your own enquiries.")
        if enquiry.is_replied():
            raise OperationError("Cannot edit an enquiry that has already been replied to.")
        if not new_text or new_text.isspace():
            raise OperationError("Enquiry text cannot be empty.")

        enquiry.text = new_text
        try:
            self.enquiry_repository.update(enquiry)
        except Exception as e:
            raise OperationError(f"Failed to update enquiry: {e}")

    def delete_enquiry(self, applicant: Applicant, enquiry: Enquiry):
        if enquiry.applicant_nric != applicant.nric:
            raise OperationError("You can only delete your own enquiries.")
        if enquiry.is_replied():
            raise OperationError("Cannot delete an enquiry that has already been replied to.")

        try:
            self.enquiry_repository.delete_by_id(enquiry.enquiry_id)
        except Exception as e:
            raise OperationError(f"Failed to delete enquiry: {e}")

    def reply_to_enquiry(self, replier_user: User, enquiry: Enquiry, reply_text: str):
        if not reply_text or reply_text.isspace():
            raise OperationError("Reply text cannot be empty.")

        project = self.project_service.find_project_by_name(enquiry.project_name)
        if not project:
            raise OperationError("Project associated with enquiry not found.")

        can_reply = False
        replier_role = ""

        if isinstance(replier_user, HDBManager):
            replier_role = "Manager"
            if project.manager_nric == replier_user.nric:
                can_reply = True
            else:
                raise OperationError("Managers can only reply to enquiries for projects they manage.")
        elif isinstance(replier_user, HDBOfficer):
            replier_role = "Officer"
            handled_names = self.project_service.get_handled_project_names_for_officer(replier_user.nric)
            if project.project_name in handled_names:
                can_reply = True
            else:
                raise OperationError("Officers can only reply to enquiries for projects they handle.")
        else:
            raise OperationError("Only Managers or Officers can reply to enquiries.")


        replier_name = replier_user.name
        enquiry.reply = f"[{replier_role} - {replier_name}]: {reply_text}"
        try:
            self.enquiry_repository.update(enquiry)
        except Exception as e:
            enquiry.reply = ""
            raise OperationError(f"Failed to save reply: {e}")

class ReportService:
    def __init__(self, application_repository: ApplicationRepository,
                 project_service: ProjectService,
                 user_repository: UserRepository):
        self.application_repository = application_repository
        self.project_service = project_service
        self.user_repository = user_repository

    def generate_booking_report_data(self, filter_project_name=None, filter_flat_type_str=None, filter_marital=None):
        report_data = []
        all_apps = self.application_repository.get_all()
        booked_apps = [app for app in all_apps if app.status == Application.STATUS_BOOKED]

        filter_flat_type = None
        if filter_flat_type_str:
            try: filter_flat_type = int(filter_flat_type_str)
            except ValueError: pass

        filter_marital_lower = filter_marital.lower() if filter_marital else None

        for app in booked_apps:
            project = self.project_service.find_project_by_name(app.project_name)
            if not project: continue

            applicant = self.user_repository.find_user_by_nric(app.applicant_nric)
            if not applicant: continue

            if filter_project_name and project.project_name != filter_project_name: continue
            if filter_flat_type and app.flat_type != filter_flat_type: continue
            if filter_marital_lower and applicant.marital_status.lower() != filter_marital_lower: continue

            report_data.append({
                "NRIC": app.applicant_nric,
                "Applicant Name": applicant.name,
                "Age": applicant.age,
                "Marital Status": applicant.marital_status,
                "Flat Type": f"{app.flat_type}-Room",
                "Project Name": project.project_name,
                "Neighborhood": project.neighborhood
            })
        return report_data

class BaseView:
    def display_message(self, message, error=False, info=False, warning=False):
        prefix = "ERROR: " if error else ("INFO: " if info else ("WARNING: " if warning else ""))
        print(f"\n{prefix}{message}")

    def get_input(self, prompt):
        return input(f"{prompt}: ").strip()

    def get_password(self, prompt="Enter password"):
        return input(f"{prompt}: ").strip()

    def display_menu(self, title, options):
        print(f"\n--- {title} ---")
        if not options:
            print("No options available.")
            return None
        for i, option in enumerate(options):
            print(f"{i + 1}. {option}")
        print("--------------------")
        choice = Utils.get_valid_integer_input("Enter your choice", min_val=1, max_val=len(options))
        return choice

    def display_list(self, title, items, empty_message="No items to display."):
        print(f"\n--- {title} ---")
        if not items:
            print(empty_message)
        else:
            for i, item in enumerate(items):
                print(f"{i + 1}. {item}")
        print("--------------------")

    def display_dict(self, title, data_dict):
        print(f"\n--- {title} ---")
        if not data_dict:
            print("(No details)")
        else:
            max_key_len = max(len(k) for k in data_dict.keys()) if data_dict else 0
            for key, value in data_dict.items():
                print(f"  {key:<{max_key_len}} : {value}")
        print("-" * (len(title) + 6))

class AuthView(BaseView):
    def prompt_login(self):
        self.display_message("\n--- Login ---", info=True)
        nric = self.get_input("Enter NRIC")
        password = self.get_password()
        return nric, password

    def prompt_change_password(self, current_password):
        self.display_message("\n--- Change Password ---", info=True)
        old_pwd = self.get_password("Enter your current password")
        if old_pwd != current_password:
            self.display_message("Incorrect current password.", error=True)
            return None

        new_pwd = self.get_password("Enter your new password")
        confirm_pwd = self.get_password("Confirm your new password")

        if not new_pwd:
            self.display_message("New password cannot be empty.", error=True)
            return None
        if new_pwd != confirm_pwd:
            self.display_message("New passwords do not match.", error=True)
            return None

        return new_pwd

class ProjectView(BaseView):
    def display_project_details(self, project: Project, user_role="Applicant", is_single_applicant=False):
        details = {
            "Neighborhood": project.neighborhood,
            "Managed by NRIC": project.manager_nric,
            "Application Period": f"{Utils.format_date(project.opening_date)} to {Utils.format_date(project.closing_date)}",
            "Visibility": "ON" if project.visibility else "OFF",
            "Status": "Active" if project.is_currently_active_for_application() else "Inactive/Closed"
        }

        details["2-Room Flats"] = f"{project.num_units1} units @ ${project.price1}"
        if not is_single_applicant:
            details["3-Room Flats"] = f"{project.num_units2} units @ ${project.price2}"
        else:
            details["3-Room Flats"] = "(Not applicable for single applicants)"


        if user_role in ["HDB Officer", "HDB Manager"]:
            details["Officer Slots"] = f"{len(project.officer_nrics)} / {project.officer_slot}"
            if project.officer_nrics:
                details["Assigned Officers (NRIC)"] = ", ".join(project.officer_nrics)
            else:
                 details["Assigned Officers (NRIC)"] = "None"


        self.display_dict(f"Project: {project.project_name}", details)

    def prompt_project_filters(self, current_filters):
        self.display_message(f"Current Filters: {current_filters or 'None'}", info=True)
        location = self.get_input("Filter by Neighborhood (leave blank to keep/remove)")
        flat_type = self.get_input("Filter by Flat Type (2 or 3, leave blank to keep/remove)")

        new_filters = current_filters.copy()
        if location is not None:
            new_filters['location'] = location if location else None
        if flat_type is not None:
            if flat_type in ['2', '3']:
                new_filters['flat_type'] = flat_type
            elif flat_type == '':
                new_filters['flat_type'] = None
            else:
                self.display_message("Invalid flat type filter. Keeping previous.", warning=True)

        return {k: v for k, v in new_filters.items() if v is not None}

    def select_project(self, projects, action_verb="view details for"):
        if not projects:
            self.display_message("No projects available for selection.", info=True)
            return None

        print(f"\n--- Select Project to {action_verb} ---")
        project_map = {}
        for i, p in enumerate(projects):
            visibility_status = "Visible" if p.visibility else "Hidden"
            active_status = "Active" if p.is_currently_active_for_application() else "Inactive/Closed"
            print(f"{i + 1}. {p.project_name} ({p.neighborhood}) - Status: {active_status}, View: {visibility_status}")
            project_map[i + 1] = p
        print(" 0. Cancel")
        print("-------------------------------------")

        while True:
            choice_str = self.get_input("Enter the number of the project (or 0 to cancel)")
            if choice_str == '0':
                return None
            try:
                index = int(choice_str)
                if index in project_map:
                    return project_map[index]
                else:
                    self.display_message("Invalid selection.", error=True)
            except ValueError:
                self.display_message("Invalid input. Please enter a number.", error=True)

    def prompt_create_project_details(self):
        self.display_message("\n--- Create New Project ---", info=True)
        details = {}
        details['name'] = Utils.get_non_empty_input("Enter Project Name")
        details['neighborhood'] = Utils.get_non_empty_input("Enter Neighborhood")
        details['n1'] = Utils.get_valid_integer_input("Enter Number of 2-Room units", min_val=0)
        details['p1'] = Utils.get_valid_integer_input("Enter Selling Price for 2-Room", min_val=0)
        details['n2'] = Utils.get_valid_integer_input("Enter Number of 3-Room units", min_val=0)
        details['p2'] = Utils.get_valid_integer_input("Enter Selling Price for 3-Room", min_val=0)
        details['od'] = Utils.get_valid_date_input("Enter Application Opening Date")
        details['cd'] = Utils.get_valid_date_input("Enter Application Closing Date")
        details['slot'] = Utils.get_valid_integer_input("Enter Max Officer Slots", min_val=0, max_val=10)
        return details

    def prompt_edit_project_details(self, project: Project):
        self.display_message(f"\n--- Editing Project: {project.project_name} ---", info=True)
        print("(Leave input blank to keep the current value)")
        updates = {}

        updates['name'] = self.get_input(f"New Project Name [{project.project_name}]") or project.project_name
        updates['neighborhood'] = self.get_input(f"New Neighborhood [{project.neighborhood}]") or project.neighborhood

        n1_str = self.get_input(f"New Number of 2-Room units [{project.num_units1}]")
        updates['n1'] = int(n1_str) if n1_str.isdigit() else None
        p1_str = self.get_input(f"New Selling Price for 2-Room [{project.price1}]")
        updates['p1'] = int(p1_str) if p1_str.isdigit() else None
        n2_str = self.get_input(f"New Number of 3-Room units [{project.num_units2}]")
        updates['n2'] = int(n2_str) if n2_str.isdigit() else None
        p2_str = self.get_input(f"New Selling Price for 3-Room [{project.price2}]")
        updates['p2'] = int(p2_str) if p2_str.isdigit() else None
        slot_str = self.get_input(f"New Max Officer Slots [{project.officer_slot}]")
        updates['officerSlot'] = int(slot_str) if slot_str.isdigit() else None

        od_str = self.get_input(f"New Opening Date ({DATE_FORMAT}) [{Utils.format_date(project.opening_date)}]")
        updates['openDate'] = Utils.parse_date(od_str) if od_str else project.opening_date

        cd_str = self.get_input(f"New Closing Date ({DATE_FORMAT}) [{Utils.format_date(project.closing_date)}]")
        updates['closeDate'] = Utils.parse_date(cd_str) if cd_str else project.closing_date

        return {k: v for k, v in updates.items() if v is not None or k in ['name', 'neighborhood', 'openDate', 'closeDate']}


class ApplicationView(BaseView):
    def display_application_status(self, application: Application, project: Project, applicant: Applicant):
        details = {
            "Applicant": f"{applicant.name} ({applicant.nric})",
            "Project": f"{project.project_name} ({project.neighborhood})",
            "Flat Type Applied For": f"{application.flat_type}-Room",
            "Status": application.status
        }
        if application.request_withdrawal:
            details["Withdrawal Requested"] = "Yes (Pending Manager Action)"

        self.display_dict("Your Application Status", details)

    def select_application(self, applications, user_service: AuthService, action_verb="view"):
        if not applications:
            self.display_message("No applications available for selection.", info=True)
            return None

        print(f"\n--- Select Application to {action_verb} ---")
        app_map = {}
        for i, app in enumerate(applications):
            applicant = user_service.user_repository.find_user_by_nric(app.applicant_nric)
            applicant_name = applicant.name if applicant else "Unknown Applicant"
            req_status = " (Withdrawal Requested)" if app.request_withdrawal else ""
            print(f"{i + 1}. Project: {app.project_name} | Applicant: {applicant_name} ({app.applicant_nric}) | Type: {app.flat_type}-Room | Status: {app.status}{req_status}")
            app_map[i + 1] = app
        print(" 0. Cancel")
        print("------------------------------------")

        while True:
            choice_str = self.get_input("Enter the number of the application (or 0 to cancel)")
            if choice_str == '0':
                return None
            try:
                index = int(choice_str)
                if index in app_map:
                    return app_map[index]
                else:
                    self.display_message("Invalid selection.", error=True)
            except ValueError:
                self.display_message("Invalid input. Please enter a number.", error=True)

    def prompt_flat_type_selection(self, project: Project, applicant: Applicant):
        available_types = []
        units2, _ = project.get_flat_details(2)
        units3, _ = project.get_flat_details(3)

        can_apply_2_room = (applicant.marital_status == "Single" and applicant.age >= 35) or \
                           (applicant.marital_status == "Married" and applicant.age >= 21)
        can_apply_3_room = (applicant.marital_status == "Married" and applicant.age >= 21)

        if units2 > 0 and can_apply_2_room:
            available_types.append(2)
        if units3 > 0 and can_apply_3_room:
            available_types.append(3)

        if not available_types:
            self.display_message("No suitable or available flat types for you in this project.", error=True)
            return None
        elif len(available_types) == 1:
            selected_type = available_types[0]
            self.display_message(f"Automatically selecting {selected_type}-Room flat (only option available/eligible).", info=True)
            return selected_type
        else:
            options_str = ' or '.join(map(str, available_types))
            while True:
                choice_str = self.get_input(f"Select flat type ({options_str})")
                try:
                    choice = int(choice_str)
                    if choice in available_types:
                        return choice
                    else:
                        self.display_message(f"Invalid choice. Please enter one of: {options_str}", error=True)
                except ValueError:
                    self.display_message("Invalid input. Please enter a number.", error=True)

class EnquiryView(BaseView):
    def display_enquiry(self, enquiry: Enquiry, project_name: str, applicant_name: str):
        details = {
            "Project": project_name,
            "Submitted by": f"{applicant_name} ({enquiry.applicant_nric})",
            "Enquiry Text": enquiry.text,
            "Reply": enquiry.reply if enquiry.is_replied() else "(No reply yet)"
        }
        self.display_dict(f"Enquiry ID: {enquiry.enquiry_id}", details)

    def select_enquiry(self, enquiries, action_verb="view"):
        if not enquiries:
            self.display_message("No enquiries available for selection.", info=True)
            return None

        print(f"\n--- Select Enquiry (by ID) to {action_verb} ---")
        enquiry_map = {}
        for enq in enquiries:
            reply_status = "Replied" if enq.is_replied() else "Unreplied"
            text_preview = (enq.text[:47] + '...') if len(enq.text) > 50 else enq.text
            print(f"  ID: {enq.enquiry_id:<4} | Project: {enq.project_name:<15} | Status: {reply_status:<9} | Text: {text_preview}")
            enquiry_map[enq.enquiry_id] = enq
        print("  ID: 0    | Cancel")
        print("--------------------------------------------------")

        while True:
            id_str = self.get_input("Enter the ID of the enquiry (or 0 to cancel)")
            if id_str == '0':
                return None
            try:
                enquiry_id = int(id_str)
                if enquiry_id in enquiry_map:
                    return enquiry_map[enquiry_id]
                else:
                    self.display_message("Invalid enquiry ID.", error=True)
            except ValueError:
                self.display_message("Invalid input. Please enter a number.", error=True)

    def prompt_enquiry_text(self, current_text=None):
        prompt = "Enter enquiry text" if current_text is None else f"Enter new enquiry text [{current_text[:30]}...]"
        return Utils.get_non_empty_input(prompt)

    def prompt_reply_text(self):
        return Utils.get_non_empty_input("Enter reply text")

class OfficerView(BaseView):
    def display_registration(self, registration: Registration, project_name: str, officer_name: str):
        details = {
            "Officer": f"{officer_name} ({registration.officer_nric})",
            "Project": project_name,
            "Status": registration.status
        }
        self.display_dict("Officer Registration Details", details)

    def select_registration(self, registrations, user_service: AuthService, action_verb="view"):
        if not registrations:
            self.display_message("No registrations available for selection.", info=True)
            return None

        print(f"\n--- Select Registration to {action_verb} ---")
        reg_map = {}
        for i, reg in enumerate(registrations):
            officer = user_service.user_repository.find_user_by_nric(reg.officer_nric)
            officer_name = officer.name if officer else "Unknown Officer"
            print(f"{i + 1}. Project: {reg.project_name} | Officer: {officer_name} ({reg.officer_nric}) | Status: {reg.status}")
            reg_map[i + 1] = reg
        print(" 0. Cancel")
        print("------------------------------------")

        while True:
            choice_str = self.get_input("Enter the number of the registration (or 0 to cancel)")
            if choice_str == '0':
                return None
            try:
                index = int(choice_str)
                if index in reg_map:
                    return reg_map[index]
                else:
                    self.display_message("Invalid selection.", error=True)
            except ValueError:
                self.display_message("Invalid input. Please enter a number.", error=True)

    def prompt_applicant_nric(self, purpose="action"):
         while True:
             nric = self.get_input(f"Enter Applicant's NRIC for {purpose}")
             if Utils.validate_nric(nric):
                 return nric
             else:
                 self.display_message("Invalid NRIC format. Please try again.", error=True)

    def display_receipt(self, receipt_data):
        self.display_dict("Booking Receipt", receipt_data)

class ManagerView(BaseView):
    pass

class ReportView(BaseView):
    def display_report(self, title, report_data, headers):
        print(f"\n--- {title} ---")
        if not report_data:
            print("No data found for this report.")
            return

        widths = {header: len(header) for header in headers}
        for row in report_data:
            for header in headers:
                value_str = str(row.get(header, ''))
                widths[header] = max(widths[header], len(value_str))

        header_line = " | ".join(f"{header:<{widths[header]}}" for header in headers)
        print(header_line)
        print("-" * len(header_line))

        for row in report_data:
            row_line = " | ".join(f"{str(row.get(header, '')):<{widths[header]}}" for header in headers)
            print(row_line)
        print("-" * len(header_line))
        print(f"Total Records: {len(report_data)}")

    def prompt_report_filters(self):
        self.display_message("\n--- Generate Booking Report Filters ---", info=True)
        filters = {}
        filters['filter_marital'] = self.get_input("Filter by Marital Status (Single/Married, leave blank for all)")
        filters['filter_project_name'] = self.get_input("Filter by Project Name (leave blank for all)")
        filters['filter_flat_type_str'] = self.get_input("Filter by Flat Type (2/3, leave blank for all)")

        clean_filters = {}
        marital = filters['filter_marital'].strip().lower()
        if marital in ['single', 'married']:
            clean_filters['filter_marital'] = marital.capitalize()
        elif marital:
            self.display_message("Invalid marital status filter. Ignoring.", warning=True)

        project_name = filters['filter_project_name'].strip()
        if project_name:
            clean_filters['filter_project_name'] = project_name

        flat_type = filters['filter_flat_type_str'].strip()
        if flat_type in ['2', '3']:
            clean_filters['filter_flat_type_str'] = flat_type
        elif flat_type:
            self.display_message("Invalid flat type filter. Ignoring.", warning=True)

        return clean_filters

class BaseRoleController:
    def __init__(self, current_user, services, views):
        self.current_user = current_user
        self.services = services
        self.views = views
        self.user_filters = {}

    def _get_common_actions(self):
        return {
            "Change Password": self.handle_change_password,
            "Logout": self._signal_logout,
            "Exit System": self._signal_exit,
        }

    def handle_change_password(self):
        auth_service = self.services['auth']
        auth_view = self.views['auth']
        new_password = auth_view.prompt_change_password(self.current_user.password)
        if new_password:
            try:
                auth_service.change_password(self.current_user, new_password)
                auth_view.display_message("Password changed successfully.", info=True)
            except OperationError as e:
                 auth_view.display_message(str(e), error=True)

    def _signal_logout(self):
        return "LOGOUT"

    def _signal_exit(self):
        return "EXIT"

    def _prepare_receipt_data(self, application, project, applicant):
        """Helper to format data for receipt display/generation."""
        return {
            "Applicant Name": applicant.name,
            "NRIC": applicant.nric,
            "Age": applicant.age,
            "Marital Status": applicant.marital_status,
            "Flat Type Booked": f"{application.flat_type}-Room",
            "Project Name": project.project_name,
            "Neighborhood": project.neighborhood
        }

class ApplicantController(BaseRoleController):
    def run_menu(self):
        actions = {
            "View/Filter Projects": self.handle_view_projects,
            "Apply for Project": self.handle_apply_for_project,
            "View My Application Status": self.handle_view_application_status,
            "Request Application Withdrawal": self.handle_request_withdrawal,
            "Submit Enquiry": self.handle_submit_enquiry,
            "View My Enquiries": self.handle_view_my_enquiries,
            "Edit My Enquiry": self.handle_edit_my_enquiry,
            "Delete My Enquiry": self.handle_delete_my_enquiry,
            **self._get_common_actions()
        }
        options = list(actions.keys())
        base_view = self.views['base']

        choice_index = base_view.display_menu("Applicant Menu", options)
        if choice_index is None: return None

        selected_action_name = options[choice_index - 1]
        action_method = actions[selected_action_name]

        return action_method()

    def handle_view_projects(self):
        project_service = self.services['project']
        app_service = self.services['app']
        project_view = self.views['project']
        base_view = self.views['base']

        current_app = app_service.find_application_by_applicant(self.current_user.nric)
        projects = project_service.get_viewable_projects_for_applicant(self.current_user, current_app)

        filtered_projects = project_service.filter_projects(
            projects, **self.user_filters
        )

        base_view.display_message(f"Current Filters: {self.user_filters or 'None'}", info=True)
        if not filtered_projects:
            base_view.display_message("No projects match your criteria or eligibility.")
        else:
            base_view.display_message("Displaying projects you are eligible to view/apply for:")
            is_single = self.current_user.marital_status == "Single"
            for project in filtered_projects:
                project_view.display_project_details(project, user_role="Applicant", is_single_applicant=is_single)

        if Utils.get_yes_no_input("Update filters?"):
            self.user_filters = project_view.prompt_project_filters(self.user_filters)
            base_view.display_message("Filters updated. View projects again to see changes.", info=True)

    def handle_apply_for_project(self):
        app_service = self.services['app']
        project_service = self.services['project']
        project_view = self.views['project']
        app_view = self.views['app']
        base_view = self.views['base']

        if app_service.find_application_by_applicant(self.current_user.nric):
            raise OperationError("You already have an active application.")

        potential_projects = project_service.get_viewable_projects_for_applicant(self.current_user)
        selectable_projects = [p for p in potential_projects if p.is_currently_active_for_application()]

        project_to_apply = project_view.select_project(selectable_projects, action_verb="apply for")
        if not project_to_apply: return

        flat_type = app_view.prompt_flat_type_selection(project_to_apply, self.current_user)
        if flat_type is None: return

        app_service.apply_for_project(self.current_user, project_to_apply, flat_type)
        base_view.display_message("Application submitted successfully.", info=True)

    def handle_view_application_status(self):
        app_service = self.services['app']
        project_service = self.services['project']
        app_view = self.views['app']
        base_view = self.views['base']

        application = app_service.find_application_by_applicant(self.current_user.nric)
        if not application:
            base_view.display_message("You do not have an active BTO application.")
            return

        project = project_service.find_project_by_name(application.project_name)
        if not project:
            raise IntegrityError(f"Error: Project '{application.project_name}' associated with your application not found.")

        app_view.display_application_status(application, project, self.current_user)

    def handle_request_withdrawal(self):
        app_service = self.services['app']
        base_view = self.views['base']

        application = app_service.find_application_by_applicant(self.current_user.nric)
        if not application:
            raise OperationError("You do not have an active BTO application.")

        if application.request_withdrawal:
            raise OperationError("You have already requested withdrawal for this application.")

        if Utils.get_yes_no_input(f"Request withdrawal for application to '{application.project_name}'?"):
            app_service.request_withdrawal(application)
            base_view.display_message("Withdrawal requested. Pending Manager approval.", info=True)

    def handle_submit_enquiry(self):
        enq_service = self.services['enq']
        project_service = self.services['project']
        app_service = self.services['app']
        project_view = self.views['project']
        enq_view = self.views['enq']
        base_view = self.views['base']

        current_app = app_service.find_application_by_applicant(self.current_user.nric)
        viewable_projects = project_service.get_viewable_projects_for_applicant(self.current_user, current_app)

        project_to_enquire = project_view.select_project(viewable_projects, action_verb="submit enquiry for")
        if not project_to_enquire: return

        text = enq_view.prompt_enquiry_text()
        enq_service.submit_enquiry(self.current_user, project_to_enquire, text)
        base_view.display_message("Enquiry submitted successfully.", info=True)

    def handle_view_my_enquiries(self):
        enq_service = self.services['enq']
        project_service = self.services['project']
        enq_view = self.views['enq']
        base_view = self.views['base']

        my_enquiries = enq_service.get_enquiries_by_applicant(self.current_user.nric)
        if not my_enquiries:
            base_view.display_message("You have not submitted any enquiries.")
            return

        base_view.display_message("Your Submitted Enquiries:", info=True)
        for enquiry in my_enquiries:
            project = project_service.find_project_by_name(enquiry.project_name)
            project_name = project.project_name if project else f"Unknown Project ({enquiry.project_name})"
            enq_view.display_enquiry(enquiry, project_name, self.current_user.name)

    def handle_edit_my_enquiry(self):
        enq_service = self.services['enq']
        enq_view = self.views['enq']
        base_view = self.views['base']

        my_enquiries = enq_service.get_enquiries_by_applicant(self.current_user.nric)
        editable_enquiries = [e for e in my_enquiries if not e.is_replied()]

        enquiry_to_edit = enq_view.select_enquiry(editable_enquiries, action_verb="edit")
        if not enquiry_to_edit: return

        new_text = enq_view.prompt_enquiry_text(current_text=enquiry_to_edit.text)
        enq_service.edit_enquiry(self.current_user, enquiry_to_edit, new_text)
        base_view.display_message("Enquiry updated successfully.", info=True)

    def handle_delete_my_enquiry(self):
        enq_service = self.services['enq']
        enq_view = self.views['enq']
        base_view = self.views['base']

        my_enquiries = enq_service.get_enquiries_by_applicant(self.current_user.nric)
        deletable_enquiries = [e for e in my_enquiries if not e.is_replied()]

        enquiry_to_delete = enq_view.select_enquiry(deletable_enquiries, action_verb="delete")
        if not enquiry_to_delete: return

        if Utils.get_yes_no_input(f"Are you sure you want to delete Enquiry ID {enquiry_to_delete.enquiry_id}?"):
            enq_service.delete_enquiry(self.current_user, enquiry_to_delete)
            base_view.display_message("Enquiry deleted successfully.", info=True)

class OfficerController(ApplicantController):
    def run_menu(self):
        officer_actions = {
            "Register for Project as Officer": self.handle_register_for_project,
            "View My Officer Registrations": self.handle_view_my_registrations,
            "View Handled Projects Details": self.handle_view_handled_projects,
            "View/Reply Enquiries (Handled Projects)": self.handle_view_reply_enquiries_officer,
            "Book Flat for Applicant": self.handle_book_flat,
            "Generate Booking Receipt": self.handle_generate_receipt,
        }
        applicant_actions = {
            k: v for k, v in super().run_menu.__globals__['ApplicantController'].__dict__.items()
            if k.startswith('handle_') and k not in officer_actions
        }
        applicant_actions_manual = {
            "View/Filter Projects": self.handle_view_projects,
            "Apply for Project": self.handle_apply_for_project,
            "View My Application Status": self.handle_view_application_status,
            "Request Application Withdrawal": self.handle_request_withdrawal,
            "Submit Enquiry": self.handle_submit_enquiry,
            "View My Enquiries": self.handle_view_my_enquiries,
            "Edit My Enquiry": self.handle_edit_my_enquiry,
            "Delete My Enquiry": self.handle_delete_my_enquiry,
        }


        actions = {**applicant_actions_manual, **officer_actions, **self._get_common_actions()}
        options = list(actions.keys())
        base_view = self.views['base']

        choice_index = base_view.display_menu("HDB Officer Menu", options)
        if choice_index is None: return None

        selected_action_name = options[choice_index - 1]
        action_method = actions[selected_action_name]

        return action_method()

    def handle_register_for_project(self):
        reg_service = self.services['reg']
        project_service = self.services['project']
        app_service = self.services['app']
        project_view = self.views['project']
        base_view = self.views['base']

        all_projects = project_service.get_all_projects()
        my_regs = {reg.project_name for reg in reg_service.get_registrations_by_officer(self.current_user.nric)}
        my_app = app_service.find_application_by_applicant(self.current_user.nric)
        my_app_project = my_app.project_name if my_app else None

        selectable_projects = [
            p for p in all_projects
            if p.project_name not in my_regs and \
               p.project_name != my_app_project and \
               p.manager_nric != self.current_user.nric
        ]

        project_to_register = project_view.select_project(selectable_projects, action_verb="register for")
        if not project_to_register: return

        reg_service.officer_register_for_project(self.current_user, project_to_register)
        base_view.display_message("Registration submitted successfully. Pending Manager approval.", info=True)

    def handle_view_my_registrations(self):
        reg_service = self.services['reg']
        project_service = self.services['project']
        officer_view = self.views['officer']
        base_view = self.views['base']

        my_registrations = reg_service.get_registrations_by_officer(self.current_user.nric)
        if not my_registrations:
            base_view.display_message("You have no officer registrations.")
            return

        base_view.display_message("Your Officer Registrations:", info=True)
        for reg in my_registrations:
            project = project_service.find_project_by_name(reg.project_name)
            project_name = project.project_name if project else f"Unknown Project ({reg.project_name})"
            officer_view.display_registration(reg, project_name, self.current_user.name)

    def handle_view_handled_projects(self):
        project_service = self.services['project']
        project_view = self.views['project']
        base_view = self.views['base']

        handled_project_names = project_service.get_handled_project_names_for_officer(self.current_user.nric)
        handled_projects = [p for p in project_service.get_all_projects() if p.project_name in handled_project_names]

        if not handled_projects:
            base_view.display_message("You are not currently handling any projects.")
            return

        base_view.display_message("Projects You Handle:", info=True)
        sorted_handled = sorted(handled_projects, key=lambda p: p.project_name)
        is_single = self.current_user.marital_status == "Single"
        for project in sorted_handled:
            project_view.display_project_details(project, user_role="HDB Officer", is_single_applicant=is_single)

    def _get_enquiries_for_handled_projects(self):
        enq_service = self.services['enq']
        project_service = self.services['project']
        auth_service = self.services['auth']

        handled_project_names = project_service.get_handled_project_names_for_officer(self.current_user.nric)
        relevant_enquiries = []
        if not handled_project_names:
            return relevant_enquiries

        for enquiry in enq_service.get_all_enquiries():
            if enquiry.project_name in handled_project_names:
                applicant = auth_service.user_repository.find_user_by_nric(enquiry.applicant_nric)
                applicant_name = applicant.name if applicant else "Unknown Applicant"
                relevant_enquiries.append((enquiry, applicant_name))
        return relevant_enquiries

    def handle_view_reply_enquiries_officer(self):
        enq_service = self.services['enq']
        enq_view = self.views['enq']
        base_view = self.views['base']

        relevant_enquiries_data = self._get_enquiries_for_handled_projects()

        if not relevant_enquiries_data:
            base_view.display_message("No enquiries found for the projects you handle.")
            return

        unreplied_enquiries = [e for e, name in relevant_enquiries_data if not e.is_replied()]

        base_view.display_message("Enquiries for Projects You Handle:", info=True)
        for enquiry, applicant_name in relevant_enquiries_data:
            enq_view.display_enquiry(enquiry, enquiry.project_name, applicant_name)

        if not unreplied_enquiries:
            base_view.display_message("\nNo unreplied enquiries requiring action.")
            return

        if Utils.get_yes_no_input("\nReply to an unreplied enquiry?"):
            enquiry_to_reply = enq_view.select_enquiry(unreplied_enquiries, action_verb="reply to")
            if enquiry_to_reply:
                reply_text = enq_view.prompt_reply_text()
                enq_service.reply_to_enquiry(self.current_user, enquiry_to_reply, reply_text)
                base_view.display_message("Reply submitted successfully.", info=True)

    def handle_book_flat(self):
        app_service = self.services['app']
        auth_service = self.services['auth']
        officer_view = self.views['officer']
        base_view = self.views['base']

        applicant_nric = officer_view.prompt_applicant_nric(purpose="booking flat")
        applicant = auth_service.user_repository.find_user_by_nric(applicant_nric)
        if not applicant:
            raise OperationError(f"Applicant with NRIC {applicant_nric} not found.")

        application = app_service.find_application_by_applicant(applicant_nric)
        if not application:
            raise OperationError(f"No active application found for applicant {applicant_nric}.")

        updated_project = app_service.officer_book_flat(self.current_user, application)

        base_view.display_message("Flat booked successfully and unit count updated.", info=True)

        receipt_data = self._prepare_receipt_data(application, updated_project, applicant)
        officer_view.display_receipt(receipt_data)

    def handle_generate_receipt(self):
        app_service = self.services['app']
        project_service = self.services['project']
        auth_service = self.services['auth']
        officer_view = self.views['officer']
        base_view = self.views['base']

        applicant_nric = officer_view.prompt_applicant_nric(purpose="generating receipt")
        applicant = auth_service.user_repository.find_user_by_nric(applicant_nric)
        if not applicant:
            raise OperationError(f"Applicant with NRIC {applicant_nric} not found.")

        booked_app = None
        for app in app_service.get_all_applications():
            if app.applicant_nric == applicant_nric and app.status == Application.STATUS_BOOKED:
                booked_app = app
                break

        if not booked_app:
            raise OperationError(f"No booked application found for NRIC {applicant_nric}.")

        project = project_service.find_project_by_name(booked_app.project_name)
        if not project:
            raise IntegrityError(f"Project '{booked_app.project_name}' for booked application not found.")

        handled_names = project_service.get_handled_project_names_for_officer(self.current_user.nric)
        if project.project_name not in handled_names:
            raise OperationError("You do not handle the project for this booked application.")

        receipt_data = self._prepare_receipt_data(booked_app, project, applicant)
        officer_view.display_receipt(receipt_data)

class ManagerController(BaseRoleController):
    def run_menu(self):
        actions = {
            "Create Project": self.handle_create_project,
            "Edit Project": self.handle_edit_project,
            "Delete Project": self.handle_delete_project,
            "Toggle Project Visibility": self.handle_toggle_visibility,
            "View All/Filter Projects": self.handle_view_all_projects,
            "View My Managed Projects": self.handle_view_my_projects,
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
            "View/Reply Enquiries (Managed Projects)": self.handle_view_reply_enquiries_manager,
            **self._get_common_actions()
        }
        options = list(actions.keys())
        base_view = self.views['base']

        choice_index = base_view.display_menu("HDB Manager Menu", options)
        if choice_index is None: return None

        selected_action_name = options[choice_index - 1]
        action_method = actions[selected_action_name]

        return action_method()

    def handle_create_project(self):
        project_service = self.services['project']
        project_view = self.views['project']
        base_view = self.views['base']

        details = project_view.prompt_create_project_details()
        project_service.create_project(
            self.current_user, details['name'], details['neighborhood'],
            details['n1'], details['p1'], details['n2'], details['p2'],
            details['od'], details['cd'], details['slot']
        )
        base_view.display_message(f"Project '{details['name']}' created successfully.", info=True)

    def handle_edit_project(self):
        project_service = self.services['project']
        project_view = self.views['project']
        base_view = self.views['base']

        my_projects = project_service.get_projects_by_manager(self.current_user.nric)
        project_to_edit = project_view.select_project(my_projects, action_verb="edit")
        if not project_to_edit: return

        updates = project_view.prompt_edit_project_details(project_to_edit)
        if not updates:
             base_view.display_message("No changes entered.", info=True)
             return

        project_service.edit_project(self.current_user, project_to_edit, updates)
        base_view.display_message(f"Project '{project_to_edit.project_name}' updated successfully.", info=True)

    def handle_delete_project(self):
        project_service = self.services['project']
        project_view = self.views['project']
        base_view = self.views['base']

        my_projects = project_service.get_projects_by_manager(self.current_user.nric)
        project_to_delete = project_view.select_project(my_projects, action_verb="delete")
        if not project_to_delete: return

        warning_msg = (f"WARNING: Deleting '{project_to_delete.project_name}' cannot be undone.\n"
                       f"Related applications, registrations, and enquiries will remain but refer to a non-existent project.\n"
                       f"Proceed with deletion?")
        if Utils.get_yes_no_input(warning_msg):
            project_service.delete_project(self.current_user, project_to_delete)
            base_view.display_message(f"Project '{project_to_delete.project_name}' deleted.", info=True)
        else:
            base_view.display_message("Deletion cancelled.", info=True)

    def handle_toggle_visibility(self):
        project_service = self.services['project']
        project_view = self.views['project']
        base_view = self.views['base']

        my_projects = project_service.get_projects_by_manager(self.current_user.nric)
        project_to_toggle = project_view.select_project(my_projects, action_verb="toggle visibility for")
        if not project_to_toggle: return

        new_status = project_service.toggle_project_visibility(self.current_user, project_to_toggle)
        base_view.display_message(f"Project '{project_to_toggle.project_name}' visibility set to {new_status}.", info=True)

    def handle_view_all_projects(self):
        project_service = self.services['project']
        project_view = self.views['project']
        base_view = self.views['base']

        all_projects = project_service.get_all_projects()

        filtered_projects = project_service.filter_projects(
            all_projects, **self.user_filters
        )

        base_view.display_message(f"Current Filters: {self.user_filters or 'None'}", info=True)
        if not filtered_projects:
            base_view.display_message("No projects match your criteria.")
        else:
            base_view.display_message("Displaying All Projects:", info=True)
            for project in filtered_projects:
                project_view.display_project_details(project, user_role="HDB Manager", is_single_applicant=False)

        if Utils.get_yes_no_input("Update filters?"):
            self.user_filters = project_view.prompt_project_filters(self.user_filters)
            base_view.display_message("Filters updated. View projects again to see changes.", info=True)

    def handle_view_my_projects(self):
        project_service = self.services['project']
        project_view = self.views['project']
        base_view = self.views['base']

        my_projects = project_service.get_projects_by_manager(self.current_user.nric)
        if not my_projects:
            base_view.display_message("You are not managing any projects.")
            return

        base_view.display_message("Projects You Manage:", info=True)
        for project in my_projects:
            project_view.display_project_details(project, user_role="HDB Manager", is_single_applicant=False)

    def _select_project_for_management(self, action_verb="manage"):
        project_service = self.services['project']
        project_view = self.views['project']
        base_view = self.views['base']

        my_projects = project_service.get_projects_by_manager(self.current_user.nric)
        if not my_projects:
            base_view.display_message("You do not manage any projects.")
            return None
        return project_view.select_project(my_projects, action_verb=action_verb)

    def handle_view_officer_registrations(self):
        reg_service = self.services['reg']
        auth_service = self.services['auth']
        officer_view = self.views['officer']
        base_view = self.views['base']

        project_to_view = self._select_project_for_management("view registrations for")
        if not project_to_view: return

        registrations = reg_service.get_registrations_for_project(project_to_view.project_name)
        if not registrations:
            base_view.display_message(f"No officer registrations found for project '{project_to_view.project_name}'.")
            return

        base_view.display_message(f"Officer Registrations for '{project_to_view.project_name}':", info=True)
        officer_view.select_registration(registrations, auth_service, action_verb="view")

    def _select_pending_registration_for_manager(self, action_verb="action"):
        project_service = self.services['project']
        reg_service = self.services['reg']
        auth_service = self.services['auth']
        officer_view = self.views['officer']
        base_view = self.views['base']

        my_projects = project_service.get_projects_by_manager(self.current_user.nric)
        all_pending_regs = []
        for project in my_projects:
            all_pending_regs.extend(
                reg_service.get_registrations_for_project(project.project_name, status_filter=Registration.STATUS_PENDING)
            )

        if not all_pending_regs:
            base_view.display_message("No pending officer registrations found for your projects.")
            return None

        return officer_view.select_registration(all_pending_regs, auth_service, action_verb=action_verb)

    def handle_approve_officer_registration(self):
        reg_service = self.services['reg']
        base_view = self.views['base']

        registration_to_approve = self._select_pending_registration_for_manager(action_verb="approve")
        if not registration_to_approve: return

        reg_service.manager_approve_officer_registration(self.current_user, registration_to_approve)
        base_view.display_message("Officer registration approved.", info=True)

    def handle_reject_officer_registration(self):
        reg_service = self.services['reg']
        base_view = self.views['base']

        registration_to_reject = self._select_pending_registration_for_manager(action_verb="reject")
        if not registration_to_reject: return

        reg_service.manager_reject_officer_registration(self.current_user, registration_to_reject)
        base_view.display_message("Officer registration rejected.", info=True)

    def handle_view_applications(self):
        app_service = self.services['app']
        auth_service = self.services['auth']
        app_view = self.views['app']
        base_view = self.views['base']

        project_to_view = self._select_project_for_management("view applications for")
        if not project_to_view: return

        applications = app_service.get_applications_for_project(project_to_view.project_name)
        if not applications:
            base_view.display_message(f"No applications found for project '{project_to_view.project_name}'.")
            return

        base_view.display_message(f"Applications for '{project_to_view.project_name}':", info=True)
        app_view.select_application(applications, auth_service, action_verb="view")

    def _select_pending_application_for_manager(self, action_verb="action"):
        project_service = self.services['project']
        app_service = self.services['app']
        auth_service = self.services['auth']
        app_view = self.views['app']
        base_view = self.views['base']

        my_projects = project_service.get_projects_by_manager(self.current_user.nric)
        all_pending_apps = []
        for project in my_projects:
            apps = app_service.get_applications_for_project(project.project_name)
            all_pending_apps.extend([app for app in apps if app.status == Application.STATUS_PENDING and not app.request_withdrawal])

        if not all_pending_apps:
            base_view.display_message("No pending applications found for your projects (excluding those with withdrawal requests).")
            return None

        return app_view.select_application(all_pending_apps, auth_service, action_verb=action_verb)

    def handle_approve_application(self):
        app_service = self.services['app']
        base_view = self.views['base']

        application_to_approve = self._select_pending_application_for_manager(action_verb="approve")
        if not application_to_approve: return

        app_service.manager_approve_application(self.current_user, application_to_approve)
        base_view.display_message(f"Application approved successfully (Status: {application_to_approve.status}).", info=True)


    def handle_reject_application(self):
        app_service = self.services['app']
        base_view = self.views['base']

        application_to_reject = self._select_pending_application_for_manager(action_verb="reject")
        if not application_to_reject: return

        app_service.manager_reject_application(self.current_user, application_to_reject)
        base_view.display_message("Application rejected successfully (Status: UNSUCCESSFUL).", info=True)

    def _select_application_with_withdrawal_request_for_manager(self, action_verb="action"):
        project_service = self.services['project']
        app_service = self.services['app']
        auth_service = self.services['auth']
        app_view = self.views['app']
        base_view = self.views['base']

        my_projects = project_service.get_projects_by_manager(self.current_user.nric)
        apps_with_request = []
        for project in my_projects:
            apps = app_service.get_applications_for_project(project.project_name)
            apps_with_request.extend([app for app in apps if app.request_withdrawal])

        if not apps_with_request:
            base_view.display_message("No applications with pending withdrawal requests found for your projects.")
            return None

        return app_view.select_application(apps_with_request, auth_service, action_verb=action_verb)

    def handle_approve_withdrawal(self):
        app_service = self.services['app']
        base_view = self.views['base']

        application_to_action = self._select_application_with_withdrawal_request_for_manager(action_verb="approve withdrawal for")
        if not application_to_action: return

        app_service.manager_approve_withdrawal(self.current_user, application_to_action)
        base_view.display_message("Withdrawal approved. Application status set to UNSUCCESSFUL.", info=True)

    def handle_reject_withdrawal(self):
        app_service = self.services['app']
        base_view = self.views['base']

        application_to_action = self._select_application_with_withdrawal_request_for_manager(action_verb="reject withdrawal for")
        if not application_to_action: return

        app_service.manager_reject_withdrawal(self.current_user, application_to_action)
        base_view.display_message("Withdrawal request rejected. Application status remains unchanged.", info=True)

    def handle_generate_booking_report(self):
        report_service = self.services['report']
        report_view = self.views['report']

        filters = report_view.prompt_report_filters()
        report_data = report_service.generate_booking_report_data(**filters)
        headers = ["NRIC", "Applicant Name", "Age", "Marital Status", "Flat Type", "Project Name", "Neighborhood"]
        report_view.display_report("Booking Report", report_data, headers)

    def _get_enquiries_for_managed_projects(self):
        enq_service = self.services['enq']
        project_service = self.services['project']
        auth_service = self.services['auth']

        managed_project_names = {p.project_name for p in project_service.get_projects_by_manager(self.current_user.nric)}
        relevant_enquiries = []
        if not managed_project_names:
            return relevant_enquiries

        for enquiry in enq_service.get_all_enquiries():
            if enquiry.project_name in managed_project_names:
                applicant = auth_service.user_repository.find_user_by_nric(enquiry.applicant_nric)
                applicant_name = applicant.name if applicant else "Unknown Applicant"
                relevant_enquiries.append((enquiry, applicant_name))
        return relevant_enquiries

    def handle_view_all_enquiries(self):
        enq_service = self.services['enq']
        auth_service = self.services['auth']
        enq_view = self.views['enq']
        base_view = self.views['base']

        all_enquiries_data = []
        for enquiry in enq_service.get_all_enquiries():
            applicant = auth_service.user_repository.find_user_by_nric(enquiry.applicant_nric)
            applicant_name = applicant.name if applicant else "Unknown Applicant"
            all_enquiries_data.append((enquiry, applicant_name))

        if not all_enquiries_data:
            base_view.display_message("There are no enquiries in the system.")
            return

        base_view.display_message("All System Enquiries:", info=True)
        for enquiry, applicant_name in all_enquiries_data:
            enq_view.display_enquiry(enquiry, enquiry.project_name, applicant_name)

    def handle_view_reply_enquiries_manager(self):
        enq_service = self.services['enq']
        enq_view = self.views['enq']
        base_view = self.views['base']

        relevant_enquiries_data = self._get_enquiries_for_managed_projects()

        if not relevant_enquiries_data:
            base_view.display_message("No enquiries found for the projects you manage.")
            return

        unreplied_enquiries = [e for e, name in relevant_enquiries_data if not e.is_replied()]

        base_view.display_message("Enquiries for Projects You Manage:", info=True)
        for enquiry, applicant_name in relevant_enquiries_data:
            enq_view.display_enquiry(enquiry, enquiry.project_name, applicant_name)

        if not unreplied_enquiries:
            base_view.display_message("\nNo unreplied enquiries requiring action.")
            return

        if Utils.get_yes_no_input("\nReply to an unreplied enquiry?"):
            enquiry_to_reply = enq_view.select_enquiry(unreplied_enquiries, action_verb="reply to")
            if enquiry_to_reply:
                reply_text = enq_view.prompt_reply_text()
                enq_service.reply_to_enquiry(self.current_user, enquiry_to_reply, reply_text)
                base_view.display_message("Reply submitted successfully.", info=True)

class ApplicationController:
    def __init__(self):
        try:
            user_repo = UserRepository()
            project_repo = ProjectRepository()
            app_repo = ApplicationRepository()
            reg_repo = RegistrationRepository()
            enq_repo = EnquiryRepository()

            self.services = {}
            self.services['project'] = ProjectService(project_repo, reg_repo)
            self.services['reg'] = RegistrationService(reg_repo, self.services['project'], app_repo)
            self.services['app'] = ApplicationService(app_repo, self.services['project'], self.services['reg'])
            self.services['enq'] = EnquiryService(enq_repo, self.services['project'], user_repo)
            self.services['auth'] = AuthService(user_repo)
            self.services['report'] = ReportService(app_repo, self.services['project'], user_repo)

            self.views = {
                'base': BaseView(),
                'auth': AuthView(),
                'project': ProjectView(),
                'app': ApplicationView(),
                'enq': EnquiryView(),
                'officer': OfficerView(),
                'manager': ManagerView(),
                'report': ReportView()
            }

        except (DataLoadError, DataSaveError) as e:
            BaseView().display_message(f"CRITICAL ERROR during initialization: {e}. Cannot start application.", error=True)
            exit(1)
        except Exception as e:
            BaseView().display_message(f"UNEXPECTED CRITICAL ERROR during initialization: {e}. Cannot start application.", error=True)
            exit(1)

        self.current_user = None
        self.role_controller = None

    def run(self):
        """Main application loop."""
        base_view = self.views['base']
        while True:
            if not self.current_user:
                self.handle_login()
                if not self.current_user:
                    break
            else:
                try:
                    if self.role_controller:
                        signal = self.role_controller.run_menu()
                        if signal == "LOGOUT":
                            self.handle_logout()
                        elif signal == "EXIT":
                            self.shutdown()
                            break
                    else:
                        base_view.display_message("Error: No role controller active.", error=True)
                        self.handle_logout()

                except (OperationError, IntegrityError) as e:
                    base_view.display_message(f"{e}", error=True)
                except (DataLoadError, DataSaveError) as e:
                    base_view.display_message(f"Data Error: {e}. Please check data files.", error=True)
                except KeyboardInterrupt:
                    print("\nOperation cancelled by user.")
                except Exception as e:
                    import traceback
                    print("\n--- UNEXPECTED ERROR ---")
                    traceback.print_exc()
                    print("------------------------")
                    base_view.display_message(f"An unexpected error occurred: {e}", error=True)

    def handle_login(self):
        auth_service = self.services['auth']
        auth_view = self.views['auth']
        base_view = self.views['base']

        base_view.display_message("Welcome to the BTO Management System")
        while not self.current_user:
            try:
                nric, password = auth_view.prompt_login()
                self.current_user = auth_service.login(nric, password)
                role = auth_service.get_user_role(self.current_user)
                base_view.display_message(f"Login successful. Welcome, {self.current_user.name} ({role})!", info=True)

                if role == "HDB Manager":
                    self.role_controller = ManagerController(self.current_user, self.services, self.views)
                elif role == "HDB Officer":
                    self.role_controller = OfficerController(self.current_user, self.services, self.views)
                elif role == "Applicant":
                    self.role_controller = ApplicantController(self.current_user, self.services, self.views)
                else:
                    base_view.display_message("Unknown user role detected. Logging out.", error=True)
                    self.current_user = None
                    self.role_controller = None

            except OperationError as e:
                base_view.display_message(str(e), error=True)
                if not Utils.get_yes_no_input("Login failed. Try again?"):
                    self.shutdown()
                    return
            except KeyboardInterrupt:
                self.shutdown()
                return

    def handle_logout(self):
        base_view = self.views['base']
        if self.current_user:
            base_view.display_message(f"Logging out user {self.current_user.name}.", info=True)
        self.current_user = None
        self.role_controller = None

    def shutdown(self):
        base_view = self.views['base']
        base_view.display_message("Exiting BTO Management System. Goodbye!")

if __name__ == "__main__":
    controller = ApplicationController()
    controller.run()