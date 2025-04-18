import os
from datetime import datetime, date
from abc import ABC, abstractmethod
from enum import Enum

# ==============================================================================
# == UTILS / HELPERS ==
# ==============================================================================

class CsvUtil:
    """
    Handles reading and writing data in CSV format without using the csv library.
    Handles basic quoting for fields containing commas or quotes.
    """
    @staticmethod
    def _parse_csv_line(line):
        """Parses a single CSV line, handling basic quoting."""
        fields = []
        current_field = ''
        in_quotes = False
        i = 0
        while i < len(line):
            char = line[i]

            if char == '"':
                if in_quotes and i + 1 < len(line) and line[i+1] == '"':
                    # Handle escaped quote ("") inside quotes
                    current_field += '"'
                    i += 1
                else:
                    # Toggle quote state
                    in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                # End of a field
                fields.append(current_field)
                current_field = ''
            else:
                # Regular character
                current_field += char
            i += 1

        # Add the last field
        fields.append(current_field)
        return fields

    @staticmethod
    def read_csv(file_path, expected_headers):
        """
        Reads a CSV file, validates headers, and returns a list of dictionaries.
        Raises FileNotFoundError, DataLoadError.
        """
        if not os.path.exists(file_path):
             # If file doesn't exist, create it with headers
            print(f"Warning: Data file not found: {file_path}. Creating empty file with headers.")
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(CsvUtil._format_csv_row(expected_headers) + '\n')
                return [], [] # Return empty data and headers
            except IOError as e:
                raise DataLoadError(f"Error creating data file {file_path}: {e}")

        data = []
        headers = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                header_line = f.readline().strip()
                if not header_line:
                    print(f"Warning: Data file {file_path} is empty. Using expected headers.")
                    # Write expected headers to the empty file
                    with open(file_path, 'w', encoding='utf-8') as fw:
                         fw.write(CsvUtil._format_csv_row(expected_headers) + '\n')
                    return [], list(expected_headers) # Return empty data, expected headers

                headers = CsvUtil._parse_csv_line(header_line)

                # Validate headers
                if not all(h in headers for h in expected_headers):
                    missing = [h for h in expected_headers if h not in headers]
                    extra = [h for h in headers if h not in expected_headers]
                    msg = f"Invalid headers in {file_path}. Expected: {expected_headers}. Found: {headers}."
                    if missing: msg += f" Missing: {missing}."
                    if extra: msg += f" Extra: {extra}."
                    raise DataLoadError(msg)

                header_map = {h: i for i, h in enumerate(headers)}

                for i, line in enumerate(f):
                    line = line.strip()
                    if not line: continue # Skip empty lines

                    row_values = CsvUtil._parse_csv_line(line)

                    if len(row_values) != len(headers):
                         print(f"Warning: Skipping malformed row {i+2} in {file_path}. Expected {len(headers)} fields, got {len(row_values)}: {line}")
                         continue

                    row_dict = {}
                    valid_row = True
                    for req_h in expected_headers:
                        try:
                            idx = header_map[req_h]
                            row_dict[req_h] = row_values[idx]
                        except (IndexError, KeyError):
                            print(f"Warning: Missing expected column '{req_h}' in row {i+2} of {file_path}. Skipping.")
                            valid_row = False
                            break
                    if valid_row:
                        data.append(row_dict)

        except FileNotFoundError:
             # This case is handled by the os.path.exists check now
             raise DataLoadError(f"File not found: {file_path}") # Should not happen if creation logic works
        except IOError as e:
            raise DataLoadError(f"Error reading data file {file_path}: {e}")
        except Exception as e:
            raise DataLoadError(f"Unexpected error reading CSV {file_path}: {e}")

        return data, headers

    @staticmethod
    def _format_csv_field(field_value):
        """Formats a single field for CSV, adding quotes if necessary."""
        str_value = str(field_value)
        if ',' in str_value or '"' in str_value or '\n' in str_value:
            # Escape quotes and wrap in quotes
            return '"' + str_value.replace('"', '""') + '"'
        else:
            return str_value

    @staticmethod
    def _format_csv_row(row_data):
        """Formats a list or dictionary values into a CSV row string."""
        if isinstance(row_data, dict):
            # Ensure consistent order if it's a dict (though input should ideally be ordered list)
            values = [row_data.get(h, '') for h in sorted(row_data.keys())] # Fallback, assumes consistent keys
        elif isinstance(row_data, list):
            values = row_data
        else:
            raise TypeError("Input row_data must be a list or dict")

        return ','.join(CsvUtil._format_csv_field(field) for field in values)

    @staticmethod
    def write_csv(file_path, headers, data_dicts):
        """
        Writes a list of dictionaries to a CSV file using the specified headers.
        Raises DataSaveError.
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write header
                f.write(CsvUtil._format_csv_row(headers) + '\n')
                # Write data rows
                for row_dict in data_dicts:
                    # Ensure row values are in the same order as headers
                    row_values = [row_dict.get(header, '') for header in headers]
                    f.write(CsvUtil._format_csv_row(row_values) + '\n')
        except IOError as e:
            raise DataSaveError(f"Error writing data to {file_path}: {e}")
        except Exception as e:
            raise DataSaveError(f"Unexpected error writing CSV {file_path}: {e}")

class InputUtil:
    """Handles validated user input."""
    DATE_FORMAT = "%Y-%m-%d"

    @staticmethod
    def parse_date(date_str):
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, InputUtil.DATE_FORMAT).date()
        except ValueError:
            return None

    @staticmethod
    def format_date(date_obj):
        if date_obj is None:
            return ""
        return date_obj.strftime(InputUtil.DATE_FORMAT)

    @staticmethod
    def dates_overlap(start1, end1, start2, end2):
        if not all([start1, end1, start2, end2]):
            return False
        # Ensure start <= end for comparison
        start1, end1 = min(start1, end1), max(start1, end1)
        start2, end2 = min(start2, end2), max(start2, end2)
        # Overlap occurs if one period starts before the other ends, and ends after the other starts.
        return start1 <= end2 and start2 <= end1


    @staticmethod
    def validate_nric(nric):
        if not isinstance(nric, str) or len(nric) != 9:
            return False
        first_char = nric[0].upper()
        if first_char not in ('S', 'T'):
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
                value_str = input(f"{prompt}: ").strip()
                value = int(value_str)
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
            date_str = input(f"{prompt} ({InputUtil.DATE_FORMAT}): ").strip()
            parsed = InputUtil.parse_date(date_str)
            if parsed:
                return parsed
            else:
                print(f"ERROR: Invalid date format. Please use {InputUtil.DATE_FORMAT}.")

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
            if choice == 'y':
                return True
            elif choice == 'n':
                return False
            print("ERROR: Please enter 'y' or 'n'.")

# ==============================================================================
# == ENUMS ==
# ==============================================================================

class UserRole(Enum):
    APPLICANT = "Applicant"
    HDB_OFFICER = "HDB Officer"
    HDB_MANAGER = "HDB Manager"

class ApplicationStatus(Enum):
    PENDING = "PENDING"
    SUCCESSFUL = "SUCCESSFUL"
    UNSUCCESSFUL = "UNSUCCESSFUL"
    BOOKED = "BOOKED"

class RegistrationStatus(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class FilePath(Enum):
    APPLICANT = 'ApplicantList.csv'
    OFFICER = 'OfficerList.csv'
    MANAGER = 'ManagerList.csv'
    PROJECT = 'ProjectList.csv'
    APPLICATION = 'ApplicationData.csv'
    REGISTRATION = 'RegistrationData.csv'
    ENQUIRY = 'EnquiryData.csv'

class FlatType(Enum):
    TWO_ROOM = 2
    THREE_ROOM = 3

# ==============================================================================
# == EXCEPTIONS ==
# ==============================================================================

class DataLoadError(Exception):
    """Error during data loading from file."""
    pass

class DataSaveError(Exception):
    """Error during data saving to file."""
    pass

class IntegrityError(Exception):
    """Data integrity violation (e.g., duplicate key, not found)."""
    pass

class OperationError(Exception):
    """Error during a business logic operation (e.g., eligibility fail, invalid state)."""
    pass

# ==============================================================================
# == MODEL ==
# ==============================================================================

class User:
    """Base class for all users."""
    def __init__(self, name, nric, age, marital_status, password="password"):
        if not InputUtil.validate_nric(nric):
            raise ValueError(f"Invalid NRIC format: {nric}")
        try:
            self._age = int(age)
            if self._age < 0: raise ValueError("Age cannot be negative")
        except (ValueError, TypeError):
            raise ValueError(f"Invalid age value: {age}")

        self._name = name
        self._nric = nric
        self._marital_status = marital_status # Assume valid strings like "Single", "Married"
        self._password = password

    # --- Getters (Encapsulation) ---
    @property
    def name(self):
        return self._name

    @property
    def nric(self):
        return self._nric

    @property
    def age(self):
        return self._age

    @property
    def marital_status(self):
        return self._marital_status

    # --- Password Management (Encapsulation) ---
    def check_password(self, password_attempt):
        return self._password == password_attempt

    def change_password(self, new_password):
        if not new_password:
            raise ValueError("Password cannot be empty.")
        self._password = new_password
        # Note: Saving the change is the responsibility of the repository/service layer

    def get_password_for_storage(self):
        """Allows repository to get password for saving."""
        return self._password

    # --- Role (Polymorphism) ---
    def get_role(self) -> UserRole:
        # Base user doesn't have a specific role in this system context
        # Subclasses MUST override this
        raise NotImplementedError("Subclasses must implement get_role()")

    def __eq__(self, other):
        if not isinstance(other, User):
            return NotImplemented
        return self._nric == other._nric

    def __hash__(self):
        return hash(self._nric)

    def __str__(self):
         return f"User(Name: {self._name}, NRIC: {self._nric}, Role: {self.get_role().value})"

class Applicant(User):
    """Represents an applicant user."""
    def __init__(self, name, nric, age, marital_status, password="password"):
        super().__init__(name, nric, age, marital_status, password)

    def get_role(self) -> UserRole:
        return UserRole.APPLICANT

class HDBOfficer(Applicant):
    """Represents an HDB Officer user. Inherits Applicant capabilities."""
    def __init__(self, name, nric, age, marital_status, password="password"):
        super().__init__(name, nric, age, marital_status, password)

    def get_role(self) -> UserRole:
        return UserRole.HDB_OFFICER

class HDBManager(User):
    """Represents an HDB Manager user."""
    def __init__(self, name, nric, age, marital_status, password="password"):
        super().__init__(name, nric, age, marital_status, password)

    def get_role(self) -> UserRole:
        return UserRole.HDB_MANAGER

class Project:
    """Represents a BTO project."""
    # Define expected headers for CSV consistency
    _HEADERS = [
        'Project Name', 'Neighborhood', 'Type 1', 'Number of units for Type 1',
        'Selling price for Type 1', 'Type 2', 'Number of units for Type 2',
        'Selling price for Type 2', 'Application opening date',
        'Application closing date', 'Manager', 'Officer Slot', 'Officer', 'Visibility'
    ]

    def __init__(self, project_name, neighborhood,
                 num_units1, price1, num_units2, price2,
                 opening_date, closing_date, manager_nric,
                 officer_slot, officer_nrics=None, visibility=True):

        if not project_name: raise ValueError("Project Name cannot be empty")
        if not neighborhood: raise ValueError("Neighborhood cannot be empty")
        if not manager_nric or not InputUtil.validate_nric(manager_nric):
             raise ValueError(f"Invalid Manager NRIC: {manager_nric}")

        try:
            self._num_units1 = int(num_units1)
            self._price1 = int(price1)
            self._num_units2 = int(num_units2)
            self._price2 = int(price2)
            self._officer_slot = int(officer_slot)
            if any(v < 0 for v in [self._num_units1, self._price1, self._num_units2, self._price2, self._officer_slot]):
                raise ValueError("Numeric project values (units, price, slots) cannot be negative.")
            if not (0 <= self._officer_slot <= 10):
                 raise ValueError("Officer slots must be between 0 and 10.")
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid numeric value in project data: {e}")

        if not isinstance(opening_date, date) or not isinstance(closing_date, date):
            raise ValueError("Opening and Closing dates must be valid date objects.")
        if closing_date < opening_date:
            raise ValueError("Closing date cannot be before opening date.")

        self._project_name = project_name
        self._neighborhood = neighborhood
        # Flat types are fixed as 2-Room and 3-Room per requirements
        self._type1 = FlatType.TWO_ROOM
        self._type2 = FlatType.THREE_ROOM
        self._opening_date = opening_date
        self._closing_date = closing_date
        self._manager_nric = manager_nric
        self._officer_nrics = list(officer_nrics) if officer_nrics is not None else []
        self._visibility = bool(visibility)

        if len(self._officer_nrics) > self._officer_slot:
             raise ValueError("Number of assigned officers exceeds available slots.")

    # --- Getters ---
    @property
    def project_name(self): return self._project_name
    @property
    def neighborhood(self): return self._neighborhood
    @property
    def opening_date(self): return self._opening_date
    @property
    def closing_date(self): return self._closing_date
    @property
    def manager_nric(self): return self._manager_nric
    @property
    def officer_slot(self): return self._officer_slot
    @property
    def visibility(self): return self._visibility
    @property
    def officer_nrics(self): return list(self._officer_nrics) # Return copy

    # --- Calculated Properties / State Checks ---
    def is_active_period(self, check_date=None):
        """Checks if the project is within its application period."""
        if check_date is None: check_date = date.today()
        return self._opening_date <= check_date <= self._closing_date

    def is_currently_visible_and_active(self):
        """Checks if the project is visible AND within its application period right now."""
        return self._visibility and self.is_active_period()

    def get_flat_details(self, flat_type: FlatType):
        """Returns (num_units, price) for the given flat type."""
        if flat_type == FlatType.TWO_ROOM:
            return self._num_units1, self._price1
        elif flat_type == FlatType.THREE_ROOM:
            return self._num_units2, self._price2
        else:
            raise ValueError(f"Invalid flat type requested: {flat_type}")

    def get_available_officer_slots(self):
        return self._officer_slot - len(self._officer_nrics)

    def can_add_officer(self):
        return self.get_available_officer_slots() > 0

    # --- State Modifiers (Controlled Access) ---
    def decrease_unit_count(self, flat_type: FlatType):
        """Decreases unit count for the specified flat type. Returns True if successful."""
        if flat_type == FlatType.TWO_ROOM:
            if self._num_units1 > 0:
                self._num_units1 -= 1
                return True
        elif flat_type == FlatType.THREE_ROOM:
            if self._num_units2 > 0:
                self._num_units2 -= 1
                return True
        return False # Type invalid or no units left

    def increase_unit_count(self, flat_type: FlatType):
        """Increases unit count (e.g., for withdrawal)."""
        if flat_type == FlatType.TWO_ROOM:
            self._num_units1 += 1
            return True
        elif flat_type == FlatType.THREE_ROOM:
            self._num_units2 += 1
            return True
        return False # Invalid type

    def add_officer(self, officer_nric):
        """Adds an officer if slots available and not already present."""
        if not InputUtil.validate_nric(officer_nric):
             raise ValueError("Invalid NRIC format for officer.")
        if officer_nric not in self._officer_nrics:
            if self.can_add_officer():
                self._officer_nrics.append(officer_nric)
                return True
            else:
                return False # No slots
        return True # Already present

    def remove_officer(self, officer_nric):
        """Removes an officer if present."""
        if officer_nric in self._officer_nrics:
            self._officer_nrics.remove(officer_nric)
            return True
        return False # Not found

    def set_visibility(self, is_visible):
        self._visibility = bool(is_visible)

    def update_details(self, updates: dict):
        """Updates project details from a dictionary. Performs validation."""
        # Keep track of original values for potential rollback if validation fails mid-way
        original_state = self._to_dict()

        try:
            if 'project_name' in updates:
                new_name = updates['project_name']
                if not new_name: raise ValueError("Project Name cannot be empty")
                self._project_name = new_name # Uniqueness check is service layer responsibility
            if 'neighborhood' in updates:
                new_hood = updates['neighborhood']
                if not new_hood: raise ValueError("Neighborhood cannot be empty")
                self._neighborhood = new_hood

            # Validate numeric fields together
            n1 = int(updates.get('num_units1', self._num_units1))
            p1 = int(updates.get('price1', self._price1))
            n2 = int(updates.get('num_units2', self._num_units2))
            p2 = int(updates.get('price2', self._price2))
            slot = int(updates.get('officer_slot', self._officer_slot))

            if any(v < 0 for v in [n1, p1, n2, p2, slot]):
                raise ValueError("Numeric project values cannot be negative.")
            if not (0 <= slot <= 10):
                 raise ValueError("Officer slots must be between 0 and 10.")
            if slot < len(self._officer_nrics):
                raise ValueError(f"Cannot reduce slots below current assigned officers ({len(self._officer_nrics)}).")

            self._num_units1 = n1
            self._price1 = p1
            self._num_units2 = n2
            self._price2 = p2
            self._officer_slot = slot

            # Validate dates
            new_od = updates.get('opening_date', self._opening_date)
            new_cd = updates.get('closing_date', self._closing_date)
            if not isinstance(new_od, date) or not isinstance(new_cd, date):
                 raise ValueError("Opening and Closing dates must be valid date objects.")
            if new_cd < new_od:
                 raise ValueError("Closing date cannot be before opening date.")
            # Overlap check is service layer responsibility

            self._opening_date = new_od
            self._closing_date = new_cd

        except (ValueError, TypeError) as e:
            # Rollback changes on validation error
            self._rollback_from_dict(original_state)
            raise ValueError(f"Invalid update data: {e}")

    def _rollback_from_dict(self, state_dict):
        """Helper to restore state from a dictionary."""
        self._project_name = state_dict['_project_name']
        self._neighborhood = state_dict['_neighborhood']
        self._num_units1 = state_dict['_num_units1']
        self._price1 = state_dict['_price1']
        self._num_units2 = state_dict['_num_units2']
        self._price2 = state_dict['_price2']
        self._opening_date = state_dict['_opening_date']
        self._closing_date = state_dict['_closing_date']
        self._manager_nric = state_dict['_manager_nric']
        self._officer_slot = state_dict['_officer_slot']
        self._officer_nrics = state_dict['_officer_nrics']
        self._visibility = state_dict['_visibility']

    def _to_dict(self):
        """Helper to get current state as a dictionary."""
        return {
            '_project_name': self._project_name,
            '_neighborhood': self._neighborhood,
            '_num_units1': self._num_units1,
            '_price1': self._price1,
            '_num_units2': self._num_units2,
            '_price2': self._price2,
            '_opening_date': self._opening_date,
            '_closing_date': self._closing_date,
            '_manager_nric': self._manager_nric,
            '_officer_slot': self._officer_slot,
            '_officer_nrics': list(self._officer_nrics), # Copy list
            '_visibility': self._visibility
        }

    def to_csv_dict(self):
        """Converts project data to a dictionary suitable for CSV writing."""
        return {
            'Project Name': self._project_name,
            'Neighborhood': self._neighborhood,
            'Type 1': f"{self._type1.value}-Room", # Store descriptive name
            'Number of units for Type 1': self._num_units1,
            'Selling price for Type 1': self._price1,
            'Type 2': f"{self._type2.value}-Room", # Store descriptive name
            'Number of units for Type 2': self._num_units2,
            'Selling price for Type 2': self._price2,
            'Application opening date': InputUtil.format_date(self._opening_date),
            'Application closing date': InputUtil.format_date(self._closing_date),
            'Manager': self._manager_nric,
            'Officer Slot': self._officer_slot,
            'Officer': ','.join(self._officer_nrics), # Comma-separated NRICs
            'Visibility': str(self._visibility) # Store as True/False string
        }

    @classmethod
    def from_csv_dict(cls, row_dict):
        """Creates a Project instance from a CSV dictionary."""
        try:
            # Officer NRICs are stored comma-separated
            officer_nrics = [nric.strip() for nric in row_dict.get('Officer', '').split(',') if nric.strip()]
            # Visibility is stored as 'True'/'False' string
            visibility = row_dict.get('Visibility', 'True').lower() == 'true'

            return cls(
                project_name=row_dict['Project Name'],
                neighborhood=row_dict['Neighborhood'],
                # Type 1/2 names are just descriptive, we use the enum internally
                num_units1=int(row_dict['Number of units for Type 1']),
                price1=int(row_dict['Selling price for Type 1']),
                num_units2=int(row_dict['Number of units for Type 2']),
                price2=int(row_dict['Selling price for Type 2']),
                opening_date=InputUtil.parse_date(row_dict['Application opening date']),
                closing_date=InputUtil.parse_date(row_dict['Application closing date']),
                manager_nric=row_dict['Manager'],
                officer_slot=int(row_dict['Officer Slot']),
                officer_nrics=officer_nrics,
                visibility=visibility
            )
        except (KeyError, ValueError, TypeError) as e:
            raise DataLoadError(f"Error creating Project from CSV row: {row_dict}. Error: {e}")

    def __eq__(self, other):
        if not isinstance(other, Project):
            return NotImplemented
        # Unique identifier is project name
        return self._project_name == other._project_name

    def __hash__(self):
        return hash(self._project_name)

    def __str__(self):
        return f"Project(Name: {self._project_name}, Neighborhood: {self._neighborhood})"


class Application:
    """Represents a BTO application."""
    _HEADERS = ['ApplicantNRIC', 'ProjectName', 'FlatType', 'Status', 'RequestWithdrawal']

    def __init__(self, applicant_nric, project_name, flat_type: FlatType,
                 status: ApplicationStatus = ApplicationStatus.PENDING,
                 request_withdrawal=False):

        if not InputUtil.validate_nric(applicant_nric): raise ValueError("Invalid Applicant NRIC")
        if not project_name: raise ValueError("Project Name cannot be empty")
        if not isinstance(flat_type, FlatType): raise ValueError("Invalid FlatType")
        if not isinstance(status, ApplicationStatus): raise ValueError("Invalid ApplicationStatus")

        self._applicant_nric = applicant_nric
        self._project_name = project_name
        self._flat_type = flat_type
        self._status = status
        self._request_withdrawal = bool(request_withdrawal)

    # --- Getters ---
    @property
    def applicant_nric(self): return self._applicant_nric
    @property
    def project_name(self): return self._project_name
    @property
    def flat_type(self): return self._flat_type
    @property
    def status(self): return self._status
    @property
    def request_withdrawal(self): return self._request_withdrawal

    # --- State Modifiers ---
    def set_status(self, new_status: ApplicationStatus):
        if not isinstance(new_status, ApplicationStatus):
            raise ValueError("Invalid status provided.")
        # Basic state transition validation (can be enhanced in Service layer)
        valid_transitions = {
            ApplicationStatus.PENDING: [ApplicationStatus.SUCCESSFUL, ApplicationStatus.UNSUCCESSFUL],
            ApplicationStatus.SUCCESSFUL: [ApplicationStatus.BOOKED, ApplicationStatus.UNSUCCESSFUL], # Unsuccessful via withdrawal
            ApplicationStatus.BOOKED: [ApplicationStatus.UNSUCCESSFUL], # Unsuccessful via withdrawal
            ApplicationStatus.UNSUCCESSFUL: [] # Terminal state (usually)
        }
        if new_status not in valid_transitions.get(self._status, []):
             # Allow setting to unsuccessful from any state if withdrawal approved
             if not (new_status == ApplicationStatus.UNSUCCESSFUL and self._request_withdrawal):
                  print(f"Warning: Potentially invalid status transition: {self._status.value} -> {new_status.value}") # Log or raise stricter error?

        self._status = new_status

    def set_withdrawal_request(self, requested: bool):
        if requested and self._status not in [ApplicationStatus.PENDING, ApplicationStatus.SUCCESSFUL, ApplicationStatus.BOOKED]:
             raise OperationError(f"Cannot request withdrawal for application with status '{self._status.value}'.")
        self._request_withdrawal = bool(requested)

    def to_csv_dict(self):
        return {
            'ApplicantNRIC': self._applicant_nric,
            'ProjectName': self._project_name,
            'FlatType': self._flat_type.value, # Store numeric value (2 or 3)
            'Status': self._status.value,      # Store enum value string
            'RequestWithdrawal': str(self._request_withdrawal) # Store True/False string
        }

    @classmethod
    def from_csv_dict(cls, row_dict):
        try:
            flat_type_val = int(row_dict['FlatType'])
            flat_type = FlatType(flat_type_val) # Convert int back to Enum

            status_val = row_dict['Status']
            status = ApplicationStatus(status_val) # Convert string back to Enum

            request_withdrawal = row_dict.get('RequestWithdrawal', 'False').lower() == 'true'

            return cls(
                applicant_nric=row_dict['ApplicantNRIC'],
                project_name=row_dict['ProjectName'],
                flat_type=flat_type,
                status=status,
                request_withdrawal=request_withdrawal
            )
        except (KeyError, ValueError, TypeError) as e:
            raise DataLoadError(f"Error creating Application from CSV row: {row_dict}. Error: {e}")

    def __eq__(self, other):
        if not isinstance(other, Application):
            return NotImplemented
        # Unique identifier: applicant NRIC + project name
        return (self._applicant_nric == other._applicant_nric and
                self._project_name == other._project_name)

    def __hash__(self):
        return hash((self._applicant_nric, self._project_name))

class Registration:
    """Represents an HDB Officer's registration for a project."""
    _HEADERS = ['OfficerNRIC', 'ProjectName', 'Status']

    def __init__(self, officer_nric, project_name, status: RegistrationStatus = RegistrationStatus.PENDING):
        if not InputUtil.validate_nric(officer_nric): raise ValueError("Invalid Officer NRIC")
        if not project_name: raise ValueError("Project Name cannot be empty")
        if not isinstance(status, RegistrationStatus): raise ValueError("Invalid RegistrationStatus")

        self._officer_nric = officer_nric
        self._project_name = project_name
        self._status = status

    # --- Getters ---
    @property
    def officer_nric(self): return self._officer_nric
    @property
    def project_name(self): return self._project_name
    @property
    def status(self): return self._status

    # --- State Modifiers ---
    def set_status(self, new_status: RegistrationStatus):
        if not isinstance(new_status, RegistrationStatus):
            raise ValueError("Invalid status provided.")
        # Allow transitions mainly from PENDING
        if self._status != RegistrationStatus.PENDING and new_status != self._status:
             print(f"Warning: Changing registration status from non-pending state: {self._status.value} -> {new_status.value}")
        self._status = new_status

    def to_csv_dict(self):
        return {
            'OfficerNRIC': self._officer_nric,
            'ProjectName': self._project_name,
            'Status': self._status.value # Store enum value string
        }

    @classmethod
    def from_csv_dict(cls, row_dict):
        try:
            status_val = row_dict['Status']
            status = RegistrationStatus(status_val) # Convert string back to Enum

            return cls(
                officer_nric=row_dict['OfficerNRIC'],
                project_name=row_dict['ProjectName'],
                status=status
            )
        except (KeyError, ValueError, TypeError) as e:
            raise DataLoadError(f"Error creating Registration from CSV row: {row_dict}. Error: {e}")

    def __eq__(self, other):
        if not isinstance(other, Registration):
            return NotImplemented
        # Unique identifier: officer NRIC + project name
        return (self._officer_nric == other._officer_nric and
                self._project_name == other._project_name)

    def __hash__(self):
        return hash((self._officer_nric, self._project_name))

class Enquiry:
    """Represents an enquiry submitted by an applicant."""
    _HEADERS = ['EnquiryID', 'ApplicantNRIC', 'ProjectName', 'Text', 'Reply']

    def __init__(self, enquiry_id, applicant_nric, project_name, text, reply=""):
        try:
            self._enquiry_id = int(enquiry_id)
        except (ValueError, TypeError):
            raise ValueError("Enquiry ID must be an integer.")
        if not InputUtil.validate_nric(applicant_nric): raise ValueError("Invalid Applicant NRIC")
        if not project_name: raise ValueError("Project Name cannot be empty")
        if not text: raise ValueError("Enquiry text cannot be empty")

        self._applicant_nric = applicant_nric
        self._project_name = project_name
        self._text = text
        self._reply = reply if reply is not None else ""

    # --- Getters ---
    @property
    def enquiry_id(self): return self._enquiry_id
    @property
    def applicant_nric(self): return self._applicant_nric
    @property
    def project_name(self): return self._project_name
    @property
    def text(self): return self._text
    @property
    def reply(self): return self._reply

    # --- State Checks ---
    def is_replied(self):
        return bool(self._reply)

    # --- State Modifiers ---
    def set_text(self, new_text):
        if self.is_replied():
            raise OperationError("Cannot edit an enquiry that has already been replied to.")
        if not new_text:
            raise ValueError("Enquiry text cannot be empty.")
        self._text = new_text

    def set_reply(self, reply_text):
        if not reply_text:
            # Allow clearing reply? Or should reply be final? Assume final for now.
            # If clearing is needed, add specific logic/method.
             raise ValueError("Reply text cannot be empty.")
             # Consider adding replier info if needed: self._reply = f"[{role} - {name}]: {reply_text}"
        self._reply = reply_text

    # --- ID Management (Handled by Repository) ---
    def set_id(self, new_id):
        """Allows repository to set the ID upon adding."""
        if self._enquiry_id != 0 and self._enquiry_id != new_id: # Allow setting if default 0
             print(f"Warning: Changing existing Enquiry ID from {self._enquiry_id} to {new_id}")
        self._enquiry_id = int(new_id)


    def to_csv_dict(self):
        return {
            'EnquiryID': self._enquiry_id,
            'ApplicantNRIC': self._applicant_nric,
            'ProjectName': self._project_name,
            'Text': self._text,
            'Reply': self._reply
        }

    @classmethod
    def from_csv_dict(cls, row_dict):
        try:
            return cls(
                enquiry_id=int(row_dict['EnquiryID']),
                applicant_nric=row_dict['ApplicantNRIC'],
                project_name=row_dict['ProjectName'],
                text=row_dict['Text'],
                reply=row_dict.get('Reply', '') # Handle potentially missing Reply column
            )
        except (KeyError, ValueError, TypeError) as e:
            raise DataLoadError(f"Error creating Enquiry from CSV row: {row_dict}. Error: {e}")

    def __eq__(self, other):
        if not isinstance(other, Enquiry):
            return NotImplemented
        # Unique identifier is enquiry ID
        return self._enquiry_id == other._enquiry_id

    def __hash__(self):
        return hash(self._enquiry_id)

# ==============================================================================
# == REPOSITORY (Data Access Layer - Interfaces & Implementations) ==
# ==============================================================================

# --- Interfaces (Abstraction using ABC) ---

class IBaseRepository(ABC):
    """Abstract base class for repositories."""

    @abstractmethod
    def get_all(self):
        """Returns a list of all items."""
        pass

    @abstractmethod
    def find_by_key(self, key):
        """Finds an item by its primary key."""
        pass

    @abstractmethod
    def add(self, item):
        """Adds a new item."""
        pass

    @abstractmethod
    def update(self, item):
        """Updates an existing item."""
        pass

    @abstractmethod
    def delete(self, key):
        """Deletes an item by its primary key."""
        pass

    @abstractmethod
    def save_all(self):
        """Persists all current data to the storage."""
        pass

class IUserRepository(ABC):
    """Interface for accessing user data across all roles."""
    @abstractmethod
    def find_user_by_nric(self, nric) -> User | None:
        pass

    @abstractmethod
    def get_all_users(self) -> list[User]:
        pass

    @abstractmethod
    def save_user(self, user: User):
        """Saves changes to a specific user."""
        pass

class IProjectRepository(IBaseRepository):
    """Interface specific to Project data."""
    @abstractmethod
    def find_by_name(self, name) -> Project | None:
        pass

    @abstractmethod
    def delete_by_name(self, name):
        pass

class IApplicationRepository(IBaseRepository):
    """Interface specific to Application data."""
    @abstractmethod
    def find_by_applicant_nric(self, nric) -> Application | None:
        """Finds the current non-unsuccessful application for an applicant."""
        pass

    @abstractmethod
    def find_all_by_applicant_nric(self, nric) -> list[Application]:
        """Finds all applications (including unsuccessful) for an applicant."""
        pass

    @abstractmethod
    def find_by_project_name(self, project_name) -> list[Application]:
        pass

class IRegistrationRepository(IBaseRepository):
    """Interface specific to Registration data."""
    @abstractmethod
    def find_by_officer_and_project(self, officer_nric, project_name) -> Registration | None:
        pass

    @abstractmethod
    def find_by_officer(self, officer_nric) -> list[Registration]:
        pass

    @abstractmethod
    def find_by_project(self, project_name, status_filter: RegistrationStatus = None) -> list[Registration]:
        pass

class IEnquiryRepository(IBaseRepository):
    """Interface specific to Enquiry data."""
    @abstractmethod
    def find_by_id(self, enquiry_id) -> Enquiry | None:
        pass

    @abstractmethod
    def find_by_applicant(self, applicant_nric) -> list[Enquiry]:
        pass

    @abstractmethod
    def find_by_project(self, project_name) -> list[Enquiry]:
        pass

    @abstractmethod
    def delete_by_id(self, enquiry_id):
        pass

    @abstractmethod
    def get_next_id(self) -> int:
        pass


# --- Concrete Implementations ---

class BaseCsvRepository(IBaseRepository):
    """
    Base implementation for repositories using CSV files via CsvUtil.
    Handles loading, saving, and basic CRUD operations based on a key.
    Subclasses must define _MODEL_CLASS, _FILE_PATH, _HEADERS, _get_key,
    and potentially override _create_instance and _to_csv_dict if needed.
    """
    _MODEL_CLASS = None
    _FILE_PATH = None
    _HEADERS = None

    def __init__(self):
        if not all([self._MODEL_CLASS, self._FILE_PATH, self._HEADERS]):
            raise NotImplementedError("Subclasses must define _MODEL_CLASS, _FILE_PATH, and _HEADERS.")

        self._data = {} # In-memory store {key: model_instance}
        self._load_data()

    @abstractmethod
    def _get_key(self, item):
        """Returns the unique key for the given item instance."""
        pass

    def _create_instance(self, row_dict):
        """Creates a model instance from a CSV row dictionary. Uses Model.from_csv_dict by default."""
        try:
            # Assumes the model class has a from_csv_dict class method
            return self._MODEL_CLASS.from_csv_dict(row_dict)
        except AttributeError:
             raise NotImplementedError(f"{self._MODEL_CLASS.__name__} must implement from_csv_dict or _create_instance must be overridden.")
        except DataLoadError as e:
             raise DataLoadError(f"Error in _create_instance for {self._MODEL_CLASS.__name__}: {e}")


    def _to_csv_dict(self, item):
        """Converts a model instance to a dictionary for CSV writing. Uses item.to_csv_dict by default."""
        try:
             # Assumes the model instance has a to_csv_dict method
            return item.to_csv_dict()
        except AttributeError:
             raise NotImplementedError(f"{self._MODEL_CLASS.__name__} must implement to_csv_dict or _to_csv_dict must be overridden.")

    def _load_data(self):
        """Loads data from the CSV file into the in-memory store."""
        self._data = {}
        try:
            csv_data, _ = CsvUtil.read_csv(self._FILE_PATH.value, self._HEADERS)
            for i, row_dict in enumerate(csv_data):
                try:
                    instance = self._create_instance(row_dict)
                    key = self._get_key(instance)
                    if key in self._data:
                        # Handle duplicates - overwrite might be acceptable for some data,
                        # but raise error for critical data like users/projects by key.
                        # Decision: Raise for all now for stricter integrity.
                        raise IntegrityError(f"Duplicate key '{key}' found for {self._MODEL_CLASS.__name__} in {self._FILE_PATH.value} at row {i+2}. Aborting load.")
                    self._data[key] = instance
                except (ValueError, TypeError, IntegrityError, DataLoadError) as e:
                    print(f"Warning: Error processing row {i+2} in {self._FILE_PATH.value}: {row_dict}. Error: {e}. Skipping.")
                except Exception as e:
                    print(f"Warning: Unexpected error processing row {i+2} in {self._FILE_PATH.value}: {row_dict}. Error: {e}. Skipping.")

        except (FileNotFoundError, DataLoadError) as e:
            # Let DataLoadError propagate up if critical (e.g., bad headers)
            # FileNotFoundError is handled by CsvUtil.read_csv creating the file.
            print(f"Info: Issue loading {self._FILE_PATH.value}: {e}. Starting with empty/default data.")
            self._data = {} # Ensure data is empty if load fails partially
        except IntegrityError as e:
             # Fatal integrity error during load
             raise DataLoadError(f"Fatal integrity error loading {self._FILE_PATH.value}: {e}")

        print(f"Loaded {len(self._data)} {self._MODEL_CLASS.__name__} items from {self._FILE_PATH.value}.")


    def save_all(self):
        """Saves the current in-memory data back to the CSV file."""
        try:
            # Sort keys for consistent output order (optional but good practice)
            sorted_keys = sorted(self._data.keys())
            data_to_write = [self._to_csv_dict(self._data[key]) for key in sorted_keys]
            CsvUtil.write_csv(self._FILE_PATH.value, self._HEADERS, data_to_write)
        except (DataSaveError, IOError) as e:
            # Propagate save errors
            raise DataSaveError(f"Failed to save data for {self._MODEL_CLASS.__name__} to {self._FILE_PATH.value}: {e}")
        except Exception as e:
             raise DataSaveError(f"Unexpected error saving data for {self._MODEL_CLASS.__name__} to {self._FILE_PATH.value}: {e}")


    # --- IBaseRepository Implementation ---
    def get_all(self):
        return list(self._data.values())

    def find_by_key(self, key):
        return self._data.get(key)

    def add(self, item):
        if not isinstance(item, self._MODEL_CLASS):
            raise TypeError(f"Item must be of type {self._MODEL_CLASS.__name__}")
        key = self._get_key(item)
        if key in self._data:
            raise IntegrityError(f"{self._MODEL_CLASS.__name__} with key '{key}' already exists.")
        self._data[key] = item
        # Consider saving immediately or having explicit save calls
        # self.save_all() # Save immediately on add

    def update(self, item):
        if not isinstance(item, self._MODEL_CLASS):
            raise TypeError(f"Item must be of type {self._MODEL_CLASS.__name__}")
        key = self._get_key(item)
        if key not in self._data:
            raise IntegrityError(f"{self._MODEL_CLASS.__name__} with key '{key}' not found for update.")
        # Ensure the object being updated is the same one in memory or replace it
        self._data[key] = item
        # self.save_all() # Save immediately on update

    def delete(self, key):
        if key not in self._data:
            raise IntegrityError(f"{self._MODEL_CLASS.__name__} with key '{key}' not found for deletion.")
        del self._data[key]
        # self.save_all() # Save immediately on delete


# --- Concrete User Repositories ---

class ApplicantRepository(BaseCsvRepository):
    _MODEL_CLASS = Applicant
    _FILE_PATH = FilePath.APPLICANT
    _HEADERS = ['Name', 'NRIC', 'Age', 'Marital Status', 'Password']

    def _get_key(self, item: Applicant):
        return item.nric

    # Override _create_instance and _to_csv_dict to handle User attributes
    def _create_instance(self, row_dict):
        try:
            return Applicant(
                name=row_dict['Name'],
                nric=row_dict['NRIC'],
                age=int(row_dict['Age']),
                marital_status=row_dict['Marital Status'],
                password=row_dict.get('Password', 'password') # Handle missing password column gracefully
            )
        except (KeyError, ValueError, TypeError) as e:
            raise DataLoadError(f"Error creating Applicant from CSV row: {row_dict}. Error: {e}")

    def _to_csv_dict(self, item: Applicant):
        return {
            'Name': item.name,
            'NRIC': item.nric,
            'Age': item.age,
            'Marital Status': item.marital_status,
            'Password': item.get_password_for_storage()
        }

class OfficerRepository(BaseCsvRepository):
    _MODEL_CLASS = HDBOfficer
    _FILE_PATH = FilePath.OFFICER
    _HEADERS = ['Name', 'NRIC', 'Age', 'Marital Status', 'Password'] # Same as Applicant

    def _get_key(self, item: HDBOfficer):
        return item.nric

    def _create_instance(self, row_dict):
        try:
            return HDBOfficer(
                name=row_dict['Name'],
                nric=row_dict['NRIC'],
                age=int(row_dict['Age']),
                marital_status=row_dict['Marital Status'],
                password=row_dict.get('Password', 'password')
            )
        except (KeyError, ValueError, TypeError) as e:
            raise DataLoadError(f"Error creating HDBOfficer from CSV row: {row_dict}. Error: {e}")

    def _to_csv_dict(self, item: HDBOfficer):
         return {
            'Name': item.name,
            'NRIC': item.nric,
            'Age': item.age,
            'Marital Status': item.marital_status,
            'Password': item.get_password_for_storage()
        }

class ManagerRepository(BaseCsvRepository):
    _MODEL_CLASS = HDBManager
    _FILE_PATH = FilePath.MANAGER
    _HEADERS = ['Name', 'NRIC', 'Age', 'Marital Status', 'Password'] # Same as Applicant

    def _get_key(self, item: HDBManager):
        return item.nric

    def _create_instance(self, row_dict):
        try:
            return HDBManager(
                name=row_dict['Name'],
                nric=row_dict['NRIC'],
                age=int(row_dict['Age']),
                marital_status=row_dict['Marital Status'],
                password=row_dict.get('Password', 'password')
            )
        except (KeyError, ValueError, TypeError) as e:
            raise DataLoadError(f"Error creating HDBManager from CSV row: {row_dict}. Error: {e}")

    def _to_csv_dict(self, item: HDBManager):
         return {
            'Name': item.name,
            'NRIC': item.nric,
            'Age': item.age,
            'Marital Status': item.marital_status,
            'Password': item.get_password_for_storage()
        }

# --- Facade for User Repositories ---

class UserRepositoryFacade(IUserRepository):
    """Facade to provide a single point of access for finding/saving users across roles."""
    def __init__(self, applicant_repo: ApplicantRepository,
                 officer_repo: OfficerRepository,
                 manager_repo: ManagerRepository):
        self._applicant_repo = applicant_repo
        self._officer_repo = officer_repo
        self._manager_repo = manager_repo
        self._all_users = {} # Combined cache
        self._load_all_users()

    def _load_all_users(self):
        """Loads users from all specific repositories into a combined cache."""
        self._all_users = {}
        users_loaded = 0
        duplicates = 0

        for repo in [self._applicant_repo, self._officer_repo, self._manager_repo]:
            try:
                items = repo.get_all()
                for user in items:
                    if user.nric in self._all_users:
                        print(f"Warning: Duplicate NRIC '{user.nric}' found across user files. Using entry from {repo._FILE_PATH.value}.")
                        duplicates += 1
                    self._all_users[user.nric] = user
                    users_loaded +=1
            except Exception as e:
                 # Log error but continue trying to load other repos
                 print(f"Error loading users from {repo._FILE_PATH.value}: {e}")

        print(f"Total unique users loaded into facade: {len(self._all_users)} (encountered {duplicates} duplicates).")


    def find_user_by_nric(self, nric) -> User | None:
        return self._all_users.get(nric)

    def get_all_users(self) -> list[User]:
        return list(self._all_users.values())

    def save_user(self, user: User):
        """Delegates saving to the appropriate repository based on role."""
        repo = None
        if isinstance(user, HDBManager):
            repo = self._manager_repo
        elif isinstance(user, HDBOfficer):
            repo = self._officer_repo
        elif isinstance(user, Applicant):
            repo = self._applicant_repo
        else:
            raise TypeError(f"Unknown user type cannot be saved: {type(user)}")

        try:
            # Update the specific repository's in-memory data and save it
            repo.update(user) # Assumes update adds if not present, or use add/update logic
            repo.save_all()   # Persist the change in the specific file
            # Update the facade's cache
            self._all_users[user.nric] = user
        except IntegrityError as e:
             # Handle case where user might exist in facade but not specific repo (shouldn't happen with proper loading)
             print(f"Warning: Integrity error saving user {user.nric}: {e}. Attempting to add instead.")
             try:
                 repo.add(user)
                 repo.save_all()
                 self._all_users[user.nric] = user
             except Exception as add_e:
                  raise OperationError(f"Failed to save user {user.nric} after initial integrity error: {add_e}")
        except Exception as e:
             raise DataSaveError(f"Failed to save user {user.nric} to {repo._FILE_PATH.value}: {e}")


# --- Other Concrete Repositories ---

class ProjectRepository(BaseCsvRepository, IProjectRepository):
    _MODEL_CLASS = Project
    _FILE_PATH = FilePath.PROJECT
    # Use headers defined in Project class for consistency
    _HEADERS = Project._HEADERS

    def _get_key(self, item: Project):
        return item.project_name

    # Default _create_instance and _to_csv_dict using Project methods are sufficient

    def find_by_name(self, name) -> Project | None:
        return self.find_by_key(name)

    def delete_by_name(self, name):
        self.delete(name)


class ApplicationRepository(BaseCsvRepository, IApplicationRepository):
    _MODEL_CLASS = Application
    _FILE_PATH = FilePath.APPLICATION
    _HEADERS = Application._HEADERS

    def _get_key(self, item: Application):
        # Composite key: ApplicantNRIC-ProjectName
        return f"{item.applicant_nric}-{item.project_name}"

    # Default _create_instance and _to_csv_dict using Application methods are sufficient

    def find_by_applicant_nric(self, nric) -> Application | None:
        """Finds the current non-unsuccessful application for an applicant."""
        for app in self._data.values():
            if app.applicant_nric == nric and app.status != ApplicationStatus.UNSUCCESSFUL:
                return app
        return None

    def find_all_by_applicant_nric(self, nric) -> list[Application]:
        """Finds all applications (including unsuccessful) for an applicant."""
        return [app for app in self._data.values() if app.applicant_nric == nric]


    def find_by_project_name(self, project_name) -> list[Application]:
        return [app for app in self._data.values() if app.project_name == project_name]

    # Override add to check for existing active application before adding
    def add(self, item: Application):
        if not isinstance(item, self._MODEL_CLASS):
            raise TypeError(f"Item must be of type {self._MODEL_CLASS.__name__}")

        # Check for existing *active* application by this applicant
        existing_active = self.find_by_applicant_nric(item.applicant_nric)
        if existing_active:
            raise IntegrityError(f"Applicant {item.applicant_nric} already has an active application for project '{existing_active.project_name}'.")

        # Use base class add logic if check passes
        super().add(item)


class RegistrationRepository(BaseCsvRepository, IRegistrationRepository):
    _MODEL_CLASS = Registration
    _FILE_PATH = FilePath.REGISTRATION
    _HEADERS = Registration._HEADERS

    def _get_key(self, item: Registration):
        # Composite key: OfficerNRIC-ProjectName
        return f"{item.officer_nric}-{item.project_name}"

    # Default _create_instance and _to_csv_dict using Registration methods are sufficient

    def find_by_officer_and_project(self, officer_nric, project_name) -> Registration | None:
        key = f"{officer_nric}-{project_name}"
        return self.find_by_key(key)

    def find_by_officer(self, officer_nric) -> list[Registration]:
        return [reg for reg in self._data.values() if reg.officer_nric == officer_nric]

    def find_by_project(self, project_name, status_filter: RegistrationStatus = None) -> list[Registration]:
        regs = [reg for reg in self._data.values() if reg.project_name == project_name]
        if status_filter:
            if not isinstance(status_filter, RegistrationStatus):
                 raise ValueError("status_filter must be a RegistrationStatus enum member.")
            regs = [reg for reg in regs if reg.status == status_filter]
        return regs


class EnquiryRepository(BaseCsvRepository, IEnquiryRepository):
    _MODEL_CLASS = Enquiry
    _FILE_PATH = FilePath.ENQUIRY
    _HEADERS = Enquiry._HEADERS

    def __init__(self):
        super().__init__()
        self._next_id = self._calculate_next_id()

    def _calculate_next_id(self):
        if not self._data:
            return 1
        # Keys are integers (EnquiryID)
        return max(int(k) for k in self._data.keys()) + 1

    def _get_key(self, item: Enquiry):
        return item.enquiry_id # Key is the integer ID

    # Default _create_instance and _to_csv_dict using Enquiry methods are sufficient

    # Override add to assign the next ID
    def add(self, item: Enquiry):
        if not isinstance(item, self._MODEL_CLASS):
            raise TypeError(f"Item must be of type {self._MODEL_CLASS.__name__}")

        # Assign the next available ID before adding
        item.set_id(self._next_id)
        key = self._get_key(item) # Get the newly assigned ID as key

        if key in self._data:
            # This should ideally not happen if next_id logic is correct
            raise IntegrityError(f"Enquiry with generated ID '{key}' already exists. ID generation failed?")

        self._data[key] = item
        self._next_id += 1 # Increment for the next add
        # self.save_all() # Optional: save immediately

    def get_next_id(self) -> int:
        return self._next_id

    def find_by_id(self, enquiry_id) -> Enquiry | None:
        try:
            return self.find_by_key(int(enquiry_id))
        except (ValueError, TypeError):
            return None # Invalid ID format

    def find_by_applicant(self, applicant_nric) -> list[Enquiry]:
        return [enq for enq in self._data.values() if enq.applicant_nric == applicant_nric]

    def find_by_project(self, project_name) -> list[Enquiry]:
        return [enq for enq in self._data.values() if enq.project_name == project_name]

    def delete_by_id(self, enquiry_id):
         try:
            key = int(enquiry_id)
            self.delete(key)
         except (ValueError, TypeError):
             raise IntegrityError(f"Invalid Enquiry ID format for deletion: {enquiry_id}")
         # Base delete handles not found error


# ==============================================================================
# == SERVICE (Business Logic Layer) ==
# ==============================================================================

class AuthService:
    """Handles authentication and password changes."""
    def __init__(self, user_repository: IUserRepository):
        self._user_repo = user_repository

    def login(self, nric, password) -> User:
        """Attempts to log in a user."""
        if not InputUtil.validate_nric(nric):
            raise OperationError("Invalid NRIC format.")

        user = self._user_repo.find_user_by_nric(nric)

        if user and user.check_password(password):
            return user
        elif user:
            raise OperationError("Incorrect password.")
        else:
            raise OperationError("NRIC not found.")

    def change_password(self, user: User, new_password):
        """Changes the password for the given user."""
        try:
            user.change_password(new_password) # Validation inside User class
            self._user_repo.save_user(user) # Persist change
        except ValueError as e: # Catch validation errors from User.change_password
            raise OperationError(f"Password change failed: {e}")
        except (DataSaveError, OperationError) as e: # Catch repo/facade errors
            # Attempt to revert password in memory if save failed? Complex.
            # For now, just propagate the error.
            raise OperationError(f"Failed to save new password: {e}")

    def get_user_role(self, user: User) -> UserRole:
        """Gets the role of the user."""
        return user.get_role()


class ProjectService:
    """Handles business logic related to projects."""
    def __init__(self, project_repository: IProjectRepository,
                 registration_repository: IRegistrationRepository): # Needed for overlap checks
        self._project_repo = project_repository
        self._reg_repo = registration_repository # Needed for officer overlap checks

    def find_project_by_name(self, name) -> Project | None:
        return self._project_repo.find_by_name(name)

    def get_all_projects(self) -> list[Project]:
        # Default sort by name
        return sorted(self._project_repo.get_all(), key=lambda p: p.project_name)

    def get_projects_by_manager(self, manager_nric) -> list[Project]:
        if not InputUtil.validate_nric(manager_nric): return []
        return sorted(
            [p for p in self.get_all_projects() if p.manager_nric == manager_nric],
            key=lambda p: p.project_name
        )

    def get_handled_project_names_for_officer(self, officer_nric) -> set[str]:
        """Gets names of projects an officer is assigned to (directly on project)."""
        if not InputUtil.validate_nric(officer_nric): return set()
        handled_project_names = set()
        for p in self.get_all_projects():
            if officer_nric in p.officer_nrics:
                handled_project_names.add(p.project_name)
        return handled_project_names

    def get_approved_registration_project_names_for_officer(self, officer_nric) -> set[str]:
         """Gets names of projects an officer has an APPROVED registration for."""
         if not InputUtil.validate_nric(officer_nric): return set()
         approved_names = set()
         regs = self._reg_repo.find_by_officer(officer_nric)
         for reg in regs:
             if reg.status == RegistrationStatus.APPROVED:
                 approved_names.add(reg.project_name)
         return approved_names

    def get_viewable_projects_for_applicant(self, applicant: Applicant, current_application: Application = None) -> list[Project]:
        """Gets projects viewable by an applicant based on rules."""
        viewable = []
        applicant_applied_project_name = current_application.project_name if current_application else None
        is_single = applicant.marital_status == "Single"
        is_married = applicant.marital_status == "Married"

        for project in self.get_all_projects():
            is_project_applied_for = project.project_name == applicant_applied_project_name

            # Rule: Always show the project they applied for, regardless of visibility/dates
            if is_project_applied_for:
                viewable.append(project)
                continue

            # Rule: Otherwise, only show if visible and active
            if not project.is_currently_visible_and_active():
                continue

            # Rule: Eligibility checks
            units2, _ = project.get_flat_details(FlatType.TWO_ROOM)
            units3, _ = project.get_flat_details(FlatType.THREE_ROOM)

            eligible = False
            if is_single and applicant.age >= 35 and units2 > 0:
                eligible = True
            elif is_married and applicant.age >= 21 and (units2 > 0 or units3 > 0):
                eligible = True

            if eligible:
                viewable.append(project)

        # Return unique projects sorted by name
        # Using dict to ensure uniqueness by project name, then converting back to sorted list
        unique_viewable_dict = {p.project_name: p for p in viewable}
        return sorted(list(unique_viewable_dict.values()), key=lambda p: p.project_name)

    def filter_projects(self, projects: list[Project], location=None, flat_type_str=None) -> list[Project]:
        """Filters a list of projects based on criteria."""
        filtered = list(projects) # Start with a copy
        if location:
            filtered = [p for p in filtered if p.neighborhood.lower() == location.lower()]

        if flat_type_str:
            try:
                flat_type_room = int(flat_type_str)
                target_flat_type = FlatType(flat_type_room) # Convert to Enum
                filtered = [p for p in filtered if p.get_flat_details(target_flat_type)[0] > 0]
            except (ValueError, TypeError):
                print(f"Warning: Invalid flat type filter '{flat_type_str}'. Ignoring filter.")
                pass # Ignore invalid flat type filter
        return filtered

    def _check_manager_project_overlap(self, manager_nric, new_opening_date, new_closing_date, project_to_exclude_name=None):
        """Checks if a manager has another project active during the given period."""
        for existing_project in self.get_projects_by_manager(manager_nric):
            if project_to_exclude_name and existing_project.project_name == project_to_exclude_name:
                continue # Don't compare project against itself when editing

            # Check for overlap only if the existing project has valid dates
            if existing_project.opening_date and existing_project.closing_date:
                 if InputUtil.dates_overlap(new_opening_date, new_closing_date,
                                       existing_project.opening_date, existing_project.closing_date):
                    return existing_project # Found an overlapping project
        return None # No overlap found

    def create_project(self, manager: HDBManager, name, neighborhood, n1, p1, n2, p2, od, cd, slot):
        """Creates a new project after validation."""
        if self.find_project_by_name(name):
            raise OperationError(f"Project name '{name}' already exists.")

        # Basic validation (more happens in Project constructor)
        if not (isinstance(od, date) and isinstance(cd, date) and cd >= od):
            raise OperationError("Invalid opening or closing date.")

        # Check manager overlap
        conflicting_project = self._check_manager_project_overlap(manager.nric, od, cd)
        if conflicting_project:
            raise OperationError(f"Manager already handles project '{conflicting_project.project_name}' during this period ({InputUtil.format_date(conflicting_project.opening_date)} - {InputUtil.format_date(conflicting_project.closing_date)}).")

        try:
            new_project = Project(
                project_name=name, neighborhood=neighborhood,
                num_units1=n1, price1=p1, num_units2=n2, price2=p2,
                opening_date=od, closing_date=cd, manager_nric=manager.nric,
                officer_slot=slot, officer_nrics=[], visibility=True # Default visibility ON
            )
            self._project_repo.add(new_project)
            self._project_repo.save_all() # Persist immediately
            return new_project
        except ValueError as e: # Catch validation errors from Project constructor
             raise OperationError(f"Failed to create project: {e}")
        except (IntegrityError, DataSaveError) as e:
            raise OperationError(f"Failed to save new project: {e}")

    def edit_project(self, manager: HDBManager, project: Project, updates: dict):
        """Edits an existing project after validation."""
        if project.manager_nric != manager.nric:
            raise OperationError("You can only edit projects you manage.")

        original_name = project.project_name
        new_name = updates.get('project_name', original_name)

        # Check for name collision if name is changed
        if new_name != original_name and self.find_project_by_name(new_name):
            raise OperationError(f"Project name '{new_name}' already exists.")

        # Check for date overlap if dates are changed
        new_od = updates.get('opening_date', project.opening_date)
        new_cd = updates.get('closing_date', project.closing_date)
        if new_od != project.opening_date or new_cd != project.closing_date:
             conflicting_project = self._check_manager_project_overlap(manager.nric, new_od, new_cd, project_to_exclude_name=original_name)
             if conflicting_project:
                 raise OperationError(f"Edited dates overlap with project '{conflicting_project.project_name}' ({InputUtil.format_date(conflicting_project.opening_date)} - {InputUtil.format_date(conflicting_project.closing_date)}).")

        try:
            # Apply updates using the Project's own update method for validation
            project.update_details(updates)

            # Handle repository update (delete old key, add new if name changed)
            if project.project_name != original_name:
                self._project_repo.delete(original_name)
                self._project_repo.add(project)
            else:
                self._project_repo.update(project)

            self._project_repo.save_all() # Persist changes
        except ValueError as e: # Catch validation errors from project.update_details
            # State should have been rolled back within project.update_details
            raise OperationError(f"Failed to update project: {e}")
        except (IntegrityError, DataSaveError) as e:
            # Attempt to revert in repo if save fails? Complex. Propagate for now.
            raise OperationError(f"Failed to save project updates: {e}")


    def delete_project(self, manager: HDBManager, project: Project):
        """Deletes a project."""
        if project.manager_nric != manager.nric:
            raise OperationError("You can only delete projects you manage.")
        try:
            self._project_repo.delete_by_name(project.project_name)
            self._project_repo.save_all() # Persist deletion
        except (IntegrityError, DataSaveError) as e:
            raise OperationError(f"Failed to delete project '{project.project_name}': {e}")

    def toggle_project_visibility(self, manager: HDBManager, project: Project):
        """Toggles the visibility of a project."""
        if project.manager_nric != manager.nric:
            raise OperationError("You can only toggle visibility for projects you manage.")
        try:
            project.set_visibility(not project.visibility)
            self._project_repo.update(project)
            self._project_repo.save_all() # Persist change
            return "ON" if project.visibility else "OFF"
        except (IntegrityError, DataSaveError) as e:
            # Attempt to revert in-memory change if save fails
            project.set_visibility(not project.visibility)
            raise OperationError(f"Failed to update project visibility: {e}")

    def add_officer_to_project(self, project: Project, officer_nric):
        """Adds an officer NRIC directly to the project's list (manager action)."""
        try:
            if project.add_officer(officer_nric):
                self._project_repo.update(project)
                # Save is handled by the calling function (e.g., approve registration)
                return True
            else:
                 # Either already present or no slots
                 if officer_nric in project.officer_nrics: return True # Already there is success
                 else: raise OperationError(f"Cannot add officer {officer_nric}, no slots available in {project.project_name}.")
        except ValueError as e: # Catch NRIC validation error
             raise OperationError(f"Cannot add officer: {e}")
        except IntegrityError as e: # Catch repo update error
             raise OperationError(f"Failed to update project after adding officer: {e}")


    def remove_officer_from_project(self, project: Project, officer_nric):
        """Removes an officer NRIC directly from the project's list (manager action)."""
        try:
            if project.remove_officer(officer_nric):
                self._project_repo.update(project)
                # Save is handled by the calling function if needed
                return True
            else:
                return False # Officer not found on project
        except IntegrityError as e:
             raise OperationError(f"Failed to update project after removing officer: {e}")


class ApplicationService:
    """Handles business logic related to BTO applications."""
    def __init__(self, application_repository: IApplicationRepository,
                 project_service: ProjectService,
                 registration_service: 'RegistrationService', # Forward reference
                 user_repository: IUserRepository): # Needed for applicant details
        self._app_repo = application_repository
        self._project_service = project_service
        self._reg_service = registration_service
        self._user_repo = user_repository

    def find_application_by_applicant(self, applicant_nric) -> Application | None:
        """Finds the current non-unsuccessful application."""
        return self._app_repo.find_by_applicant_nric(applicant_nric)

    def get_applications_for_project(self, project_name) -> list[Application]:
        return self._app_repo.find_by_project_name(project_name)

    def get_all_applications(self) -> list[Application]:
        return self._app_repo.get_all()

    def _check_applicant_eligibility(self, applicant: Applicant, project: Project, flat_type: FlatType):
        """Performs eligibility checks before application. Raises OperationError if ineligible."""

        # 1. Project Active?
        if not project.is_currently_visible_and_active():
            raise OperationError(f"Project '{project.project_name}' is not currently open for applications.")

        # 2. Existing Active Application?
        if self.find_application_by_applicant(applicant.nric):
            raise OperationError("You already have an active BTO application.")

        # 3. Role Eligibility
        if applicant.get_role() == UserRole.HDB_MANAGER:
             raise OperationError("HDB Managers cannot apply for BTO projects.")
        if applicant.get_role() == UserRole.HDB_OFFICER:
            # Check if officer registered for *this* project
            existing_registration = self._reg_service.find_registration(applicant.nric, project.project_name)
            if existing_registration:
                raise OperationError("You cannot apply for a project you have registered (or been approved) as an officer for.")

        # 4. Age/Marital Status/Flat Type Eligibility
        is_single = applicant.marital_status == "Single"
        is_married = applicant.marital_status == "Married"

        if is_single:
            if applicant.age < 35:
                raise OperationError("Single applicants must be at least 35 years old.")
            if flat_type != FlatType.TWO_ROOM:
                raise OperationError("Single applicants can only apply for 2-Room flats.")
        elif is_married:
            if applicant.age < 21:
                raise OperationError("Married applicants must be at least 21 years old.")
            if flat_type not in [FlatType.TWO_ROOM, FlatType.THREE_ROOM]:
                raise OperationError("Invalid flat type selected for married applicant.")
        else:
            # Should not happen with valid data, but good to check
            raise OperationError(f"Unknown marital status '{applicant.marital_status}'. Cannot determine eligibility.")

        # 5. Unit Availability
        units, _ = project.get_flat_details(flat_type)
        if units <= 0:
            raise OperationError(f"No {flat_type.value}-Room units currently available in '{project.project_name}'.")

    def apply_for_project(self, applicant: Applicant, project: Project, flat_type: FlatType) -> Application:
        """Creates and saves a new application after checking eligibility."""
        # Perform all checks first
        self._check_applicant_eligibility(applicant, project, flat_type)

        # If checks pass, create and save
        new_application = Application(applicant.nric, project.project_name, flat_type)
        try:
            self._app_repo.add(new_application)
            self._app_repo.save_all() # Persist
            return new_application
        except (IntegrityError, DataSaveError) as e:
            # IntegrityError could be from the repo's add check, though our service check should prevent it.
            raise OperationError(f"Failed to submit application: {e}")
        except Exception as e:
            raise OperationError(f"An unexpected error occurred during application submission: {e}")

    def request_withdrawal(self, application: Application):
        """Marks an application for withdrawal request."""
        if application.request_withdrawal:
            raise OperationError("Withdrawal already requested for this application.")
        try:
            application.set_withdrawal_request(True) # Validation inside method
            self._app_repo.update(application)
            self._app_repo.save_all() # Persist
        except (OperationError, IntegrityError, DataSaveError) as e:
            # Attempt to revert in-memory change if save fails
            application.set_withdrawal_request(False)
            raise OperationError(f"Failed to save withdrawal request: {e}")

    def _manager_can_manage_app(self, manager: HDBManager, application: Application) -> bool:
        """Checks if the manager manages the project associated with the application."""
        project = self._project_service.find_project_by_name(application.project_name)
        return project is not None and project.manager_nric == manager.nric

    def manager_approve_application(self, manager: HDBManager, application: Application):
        """Manager approves a pending application."""
        if not self._manager_can_manage_app(manager, application):
            raise OperationError("You can only approve applications for projects you manage.")
        if application.status != ApplicationStatus.PENDING:
            raise OperationError(f"Application status is not {ApplicationStatus.PENDING.value}.")
        if application.request_withdrawal:
            raise OperationError("Cannot approve an application with a pending withdrawal request.")

        project = self._project_service.find_project_by_name(application.project_name)
        if not project:
             # Data integrity issue if project doesn't exist
             raise IntegrityError(f"Project '{application.project_name}' not found for application.")

        # Final check on unit availability at time of approval
        units, _ = project.get_flat_details(application.flat_type)
        if units <= 0:
            # Auto-reject if no units left
            application.set_status(ApplicationStatus.UNSUCCESSFUL)
            self._app_repo.update(application)
            self._app_repo.save_all()
            raise OperationError(f"No {application.flat_type.value}-Room units available. Application automatically rejected.")

        # Approve
        try:
            application.set_status(ApplicationStatus.SUCCESSFUL)
            self._app_repo.update(application)
            self._app_repo.save_all() # Persist
        except (IntegrityError, DataSaveError) as e:
            # Attempt revert
            application.set_status(ApplicationStatus.PENDING)
            raise OperationError(f"Failed to save application approval: {e}")

    def manager_reject_application(self, manager: HDBManager, application: Application):
        """Manager rejects a pending application."""
        if not self._manager_can_manage_app(manager, application):
            raise OperationError("You can only reject applications for projects you manage.")
        if application.status != ApplicationStatus.PENDING:
            raise OperationError(f"Application status is not {ApplicationStatus.PENDING.value}.")
        # Can reject even if withdrawal requested? Assume yes.

        try:
            application.set_status(ApplicationStatus.UNSUCCESSFUL)
            self._app_repo.update(application)
            self._app_repo.save_all() # Persist
        except (IntegrityError, DataSaveError) as e:
            # Attempt revert
            application.set_status(ApplicationStatus.PENDING)
            raise OperationError(f"Failed to save application rejection: {e}")

    def manager_approve_withdrawal(self, manager: HDBManager, application: Application):
        """Manager approves a withdrawal request."""
        if not self._manager_can_manage_app(manager, application):
            raise OperationError("You can only approve withdrawals for projects you manage.")
        if not application.request_withdrawal:
            raise OperationError("No withdrawal request is pending for this application.")

        original_status = application.status
        try:
            # Regardless of original status (PENDING, SUCCESSFUL, BOOKED), withdrawal sets to UNSUCCESSFUL
            application.set_status(ApplicationStatus.UNSUCCESSFUL)
            application.set_withdrawal_request(False) # Clear the request flag

            # If status was BOOKED, need to increment unit count back
            if original_status == ApplicationStatus.BOOKED:
                 project = self._project_service.find_project_by_name(application.project_name)
                 if project:
                     if not project.increase_unit_count(application.flat_type):
                          # This is an issue - log it but proceed with withdrawal approval
                          print(f"Warning: Could not increase unit count for {application.flat_type.value}-Room in project {project.project_name} during withdrawal approval.")
                     # Save project change
                     self._project_service._project_repo.update(project)
                     self._project_service._project_repo.save_all()
                 else:
                      print(f"Warning: Project {application.project_name} not found to increase unit count during withdrawal.")


            self._app_repo.update(application)
            self._app_repo.save_all() # Persist application change
        except (IntegrityError, DataSaveError) as e:
            # Attempt complex revert (status, flag, potentially project units) - difficult
            # For simplicity, just report error. State might be inconsistent.
            # A transaction mechanism would be better here.
            raise OperationError(f"Failed to save withdrawal approval: {e}. System state may be inconsistent.")

    def manager_reject_withdrawal(self, manager: HDBManager, application: Application):
        """Manager rejects a withdrawal request."""
        if not self._manager_can_manage_app(manager, application):
            raise OperationError("You can only reject withdrawals for projects you manage.")
        if not application.request_withdrawal:
            raise OperationError("No withdrawal request is pending for this application.")

        try:
            application.set_withdrawal_request(False) # Just clear the flag
            self._app_repo.update(application)
            self._app_repo.save_all() # Persist
        except (IntegrityError, DataSaveError) as e:
            # Attempt revert
            application.set_withdrawal_request(True)
            raise OperationError(f"Failed to save withdrawal rejection: {e}")

    def officer_book_flat(self, officer: HDBOfficer, application: Application) -> tuple[Project, Applicant]:
        """Officer books a flat for a successful application."""
        project = self._project_service.find_project_by_name(application.project_name)
        if not project:
            raise OperationError(f"Project '{application.project_name}' associated with application not found.")

        # Check if officer handles this project (must be assigned directly)
        handled_project_names = self._project_service.get_handled_project_names_for_officer(officer.nric)
        if project.project_name not in handled_project_names:
            raise OperationError(f"You do not handle project '{project.project_name}' for this application.")

        if application.status != ApplicationStatus.SUCCESSFUL:
            raise OperationError(f"Application status must be '{ApplicationStatus.SUCCESSFUL.value}' to book. Current status: '{application.status.value}'.")

        applicant = self._user_repo.find_user_by_nric(application.applicant_nric)
        if not applicant:
             raise IntegrityError(f"Applicant {application.applicant_nric} not found for booking.")

        # --- Transaction-like block (manual) ---
        original_app_status = application.status
        unit_decreased = False
        project_saved = False
        app_saved = False

        try:
            # 1. Decrease unit count in Project
            if not project.decrease_unit_count(application.flat_type):
                # No units left at the very last moment! Mark unsuccessful.
                application.set_status(ApplicationStatus.UNSUCCESSFUL)
                self._app_repo.update(application)
                self._app_repo.save_all()
                raise OperationError(f"Booking failed: No {application.flat_type.value}-Room units available anymore. Application marked unsuccessful.")
            unit_decreased = True

            # 2. Save Project changes
            self._project_service._project_repo.update(project)
            self._project_service._project_repo.save_all()
            project_saved = True

            # 3. Update Application status
            application.set_status(ApplicationStatus.BOOKED)
            self._app_repo.update(application)
            self._app_repo.save_all()
            app_saved = True

            # If all steps succeeded
            return project, applicant

        except (OperationError, IntegrityError, DataSaveError) as e:
            # --- Rollback attempts ---
            print(f"ERROR during booking process: {e}. Attempting rollback...")
            if app_saved: # App was saved, but maybe project save failed earlier or something else went wrong
                 # This state is tricky. Maybe revert app status?
                 print("Rollback: Reverting application status (best effort).")
                 try:
                     application.set_status(original_app_status)
                     self._app_repo.update(application)
                     self._app_repo.save_all()
                 except Exception as rb_e:
                      print(f"CRITICAL ERROR: Failed to rollback application status: {rb_e}")

            if project_saved and unit_decreased: # Project was saved, but app save failed
                 print("Rollback: Reverting project unit count (best effort).")
                 try:
                     project.increase_unit_count(application.flat_type)
                     self._project_service._project_repo.update(project)
                     self._project_service._project_repo.save_all()
                 except Exception as rb_e:
                      print(f"CRITICAL ERROR: Failed to rollback project unit count: {rb_e}")

            elif unit_decreased: # Unit decreased in memory, but project save failed
                 print("Rollback: Reverting in-memory project unit count.")
                 project.increase_unit_count(application.flat_type) # Revert in-memory change

            # Re-raise the original error after attempting rollback
            raise OperationError(f"Booking failed: {e}. Rollback attempted, state may be inconsistent.")
        except Exception as e:
             # Catch unexpected errors during the process
             # Rollback might be even harder here
             raise OperationError(f"Unexpected error during booking: {e}. State likely inconsistent.")


class RegistrationService:
    """Handles business logic related to HDB Officer registrations."""
    def __init__(self, registration_repository: IRegistrationRepository,
                 project_service: ProjectService,
                 application_repository: IApplicationRepository): # Needed for checks
        self._reg_repo = registration_repository
        self._project_service = project_service
        self._app_repo = application_repository

    def find_registration(self, officer_nric, project_name) -> Registration | None:
        return self._reg_repo.find_by_officer_and_project(officer_nric, project_name)

    def get_registrations_by_officer(self, officer_nric) -> list[Registration]:
        return self._reg_repo.find_by_officer(officer_nric)

    def get_registrations_for_project(self, project_name, status_filter: RegistrationStatus = None) -> list[Registration]:
        return self._reg_repo.find_by_project(project_name, status_filter)

    def _check_officer_registration_eligibility(self, officer: HDBOfficer, project: Project):
        """Checks if an officer can register for a project. Raises OperationError if ineligible."""

        # 1. Already Registered?
        if self.find_registration(officer.nric, project.project_name):
            raise OperationError(f"You have already submitted a registration for project '{project.project_name}'.")

        # 2. Is Manager of Project?
        if project.manager_nric == officer.nric:
            raise OperationError("Managers cannot register as officers for their own projects.")

        # 3. Applied for Project as Applicant?
        application = self._app_repo.find_by_applicant_nric(officer.nric)
        # Check if *any* application exists for this project, even unsuccessful?
        # Requirement: "Cannot apply for the project as an Applicant before and after becoming an HDB Officer"
        # Let's check if *any* application record exists for this project by the officer.
        all_apps_by_officer = self._app_repo.find_all_by_applicant_nric(officer.nric)
        if any(app.project_name == project.project_name for app in all_apps_by_officer):
             raise OperationError("You cannot register as an officer for a project you have previously applied for.")


        # 4. Overlapping Approved Registration?
        target_od = project.opening_date
        target_cd = project.closing_date
        if not target_od or not target_cd:
            # Should not happen with valid project data
            raise OperationError(f"Target project '{project.project_name}' has invalid application dates.")

        approved_regs = self.get_registrations_for_project(project.project_name, status_filter=RegistrationStatus.APPROVED)
        # Check against *all* other approved registrations for this officer
        all_officer_regs = self.get_registrations_by_officer(officer.nric)
        for reg in all_officer_regs:
             if reg.status == RegistrationStatus.APPROVED:
                 other_project = self._project_service.find_project_by_name(reg.project_name)
                 if other_project and other_project.opening_date and other_project.closing_date:
                     # Check if the application periods overlap
                     if InputUtil.dates_overlap(target_od, target_cd, other_project.opening_date, other_project.closing_date):
                         raise OperationError(f"You are already an approved officer for project '{other_project.project_name}' which has an overlapping application period.")


    def officer_register_for_project(self, officer: HDBOfficer, project: Project) -> Registration:
        """Creates and saves a new registration after checking eligibility."""
        self._check_officer_registration_eligibility(officer, project)

        new_registration = Registration(officer.nric, project.project_name)
        try:
            self._reg_repo.add(new_registration)
            self._reg_repo.save_all() # Persist
            return new_registration
        except (IntegrityError, DataSaveError) as e:
            raise OperationError(f"Failed to submit registration: {e}")

    def _manager_can_manage_reg(self, manager: HDBManager, registration: Registration) -> bool:
        """Checks if the manager manages the project for this registration."""
        project = self._project_service.find_project_by_name(registration.project_name)
        return project is not None and project.manager_nric == manager.nric

    def manager_approve_officer_registration(self, manager: HDBManager, registration: Registration):
        """Manager approves a pending officer registration."""
        if not self._manager_can_manage_reg(manager, registration):
            raise OperationError("You can only approve registrations for projects you manage.")
        if registration.status != RegistrationStatus.PENDING:
            raise OperationError(f"Registration status is not {RegistrationStatus.PENDING.value}.")

        project = self._project_service.find_project_by_name(registration.project_name)
        if not project:
            raise OperationError(f"Project '{registration.project_name}' not found.")

        # Check slots again at time of approval
        if not project.can_add_officer():
            raise OperationError(f"No available officer slots in project '{project.project_name}'.")

        # Final check for overlapping approved registrations for the officer
        target_od = project.opening_date
        target_cd = project.closing_date
        if not target_od or not target_cd: raise OperationError("Project has invalid dates.")

        all_officer_regs = self.get_registrations_by_officer(registration.officer_nric)
        for other_reg in all_officer_regs:
            if other_reg != registration and other_reg.status == RegistrationStatus.APPROVED:
                other_project = self._project_service.find_project_by_name(other_reg.project_name)
                if other_project and other_project.opening_date and other_project.closing_date:
                    if InputUtil.dates_overlap(target_od, target_cd, other_project.opening_date, other_project.closing_date):
                        raise OperationError(f"Officer is already approved for project '{other_project.project_name}' with an overlapping period.")

        # --- Transaction-like block ---
        original_reg_status = registration.status
        officer_added_to_project = False
        try:
            # 1. Add officer to project's list
            # This might fail if NRIC invalid (caught in ProjectService) or slots changed
            self._project_service.add_officer_to_project(project, registration.officer_nric)
            officer_added_to_project = True
            # Save project immediately after adding officer
            self._project_service._project_repo.save_all()


            # 2. Update registration status
            registration.set_status(RegistrationStatus.APPROVED)
            self._reg_repo.update(registration)
            self._reg_repo.save_all() # Persist registration change

        except (OperationError, IntegrityError, DataSaveError) as e:
            # --- Rollback attempts ---
            print(f"ERROR during registration approval: {e}. Attempting rollback...")
            # Revert registration status in memory
            registration.set_status(original_reg_status)
            try: # Attempt to save reverted registration status
                 self._reg_repo.update(registration)
                 self._reg_repo.save_all()
            except Exception as rb_e:
                 print(f"Warning: Failed to save reverted registration status during rollback: {rb_e}")

            if officer_added_to_project:
                 # If officer was added to project list, try to remove them
                 print("Rollback: Removing officer from project list (best effort).")
                 try:
                     self._project_service.remove_officer_from_project(project, registration.officer_nric)
                     self._project_service._project_repo.save_all()
                 except Exception as rb_e:
                     print(f"CRITICAL ERROR: Failed to remove officer from project during rollback: {rb_e}")

            raise OperationError(f"Approval failed: {e}. Rollback attempted, state may be inconsistent.")


    def manager_reject_officer_registration(self, manager: HDBManager, registration: Registration):
        """Manager rejects a pending officer registration."""
        if not self._manager_can_manage_reg(manager, registration):
            raise OperationError("You can only reject registrations for projects you manage.")
        if registration.status != RegistrationStatus.PENDING:
            raise OperationError(f"Registration status is not {RegistrationStatus.PENDING.value}.")

        try:
            registration.set_status(RegistrationStatus.REJECTED)
            self._reg_repo.update(registration)
            self._reg_repo.save_all() # Persist
        except (IntegrityError, DataSaveError) as e:
            # Attempt revert
            registration.set_status(RegistrationStatus.PENDING)
            raise OperationError(f"Failed to save registration rejection: {e}")


class EnquiryService:
    """Handles business logic related to enquiries."""
    def __init__(self, enquiry_repository: IEnquiryRepository,
                 project_service: ProjectService,
                 user_repository: IUserRepository,
                 application_repository: IApplicationRepository): # Needed for view checks
        self._enq_repo = enquiry_repository
        self._project_service = project_service
        self._user_repo = user_repository
        self._app_repo = application_repository

    def find_enquiry_by_id(self, enquiry_id) -> Enquiry | None:
        return self._enq_repo.find_by_id(enquiry_id)

    def get_enquiries_by_applicant(self, applicant_nric) -> list[Enquiry]:
        # Sort by ID for consistent display
        return sorted(self._enq_repo.find_by_applicant(applicant_nric), key=lambda e: e.enquiry_id)

    def get_enquiries_for_project(self, project_name) -> list[Enquiry]:
        return sorted(self._enq_repo.find_by_project(project_name), key=lambda e: e.enquiry_id)

    def get_all_enquiries(self) -> list[Enquiry]:
        return sorted(self._enq_repo.get_all(), key=lambda e: e.enquiry_id)

    def submit_enquiry(self, applicant: Applicant, project: Project, text: str) -> Enquiry:
        """Submits a new enquiry after checking view permissions."""
        if not text or text.isspace():
            raise OperationError("Enquiry text cannot be empty.")

        # Check if applicant can view the project they are enquiring about
        current_app = self._app_repo.find_by_applicant_nric(applicant.nric)
        viewable_projects = self._project_service.get_viewable_projects_for_applicant(applicant, current_app)
        if project not in viewable_projects:
             # Check if it's the project they applied for (which should be viewable)
             # This check might be redundant if get_viewable_projects_for_applicant is correct
             is_applied_project = current_app and current_app.project_name == project.project_name
             if not is_applied_project:
                  raise OperationError("You cannot submit an enquiry for a project you cannot view.")

        try:
            # Create enquiry with temporary ID 0, repository will assign correct ID
            new_enquiry = Enquiry(0, applicant.nric, project.project_name, text)
            self._enq_repo.add(new_enquiry) # Add assigns ID
            self._enq_repo.save_all() # Persist
            return new_enquiry # Return enquiry with assigned ID
        except (ValueError, IntegrityError, DataSaveError) as e:
            raise OperationError(f"Failed to submit enquiry: {e}")

    def edit_enquiry(self, applicant: Applicant, enquiry: Enquiry, new_text: str):
        """Allows an applicant to edit their own unreplied enquiry."""
        if enquiry.applicant_nric != applicant.nric:
            raise OperationError("You can only edit your own enquiries.")
        # Validation and state change handled within Enquiry.set_text
        try:
            enquiry.set_text(new_text)
            self._enq_repo.update(enquiry)
            self._enq_repo.save_all() # Persist
        except (OperationError, ValueError, IntegrityError, DataSaveError) as e:
            # Revert in-memory change? Difficult if original text not stored here.
            raise OperationError(f"Failed to update enquiry: {e}")

    def delete_enquiry(self, applicant: Applicant, enquiry: Enquiry):
        """Allows an applicant to delete their own unreplied enquiry."""
        if enquiry.applicant_nric != applicant.nric:
            raise OperationError("You can only delete your own enquiries.")
        if enquiry.is_replied():
            raise OperationError("Cannot delete an enquiry that has already been replied to.")

        try:
            self._enq_repo.delete_by_id(enquiry.enquiry_id)
            self._enq_repo.save_all() # Persist
        except (IntegrityError, DataSaveError) as e:
            raise OperationError(f"Failed to delete enquiry: {e}")

    def reply_to_enquiry(self, replier_user: User, enquiry: Enquiry, reply_text: str):
        """Allows an Officer or Manager to reply to an enquiry for a project they handle."""
        if not reply_text or reply_text.isspace():
            raise OperationError("Reply text cannot be empty.")
        if enquiry.is_replied():
             # Allow editing reply? For now, assume reply is final once set.
             raise OperationError("This enquiry has already been replied to.")

        project = self._project_service.find_project_by_name(enquiry.project_name)
        if not project:
            raise OperationError(f"Project '{enquiry.project_name}' associated with enquiry not found.")

        # Determine permission based on role and project handling
        can_reply = False
        replier_role_str = ""
        user_role = replier_user.get_role()

        if user_role == UserRole.HDB_MANAGER:
            replier_role_str = "Manager"
            if project.manager_nric == replier_user.nric:
                can_reply = True
            else:
                 # FAQ: Managers can view ALL enquiries, but assignment says reply only for handled projects.
                 # Stick to assignment: reply only if managing.
                 raise OperationError("Managers can only reply to enquiries for projects they manage.")
        elif user_role == UserRole.HDB_OFFICER:
            replier_role_str = "Officer"
            handled_names = self._project_service.get_handled_project_names_for_officer(replier_user.nric)
            if project.project_name in handled_names:
                can_reply = True
            else:
                raise OperationError("Officers can only reply to enquiries for projects they handle.")
        else:
            # Applicants cannot reply
            raise OperationError("Only Managers or Officers can reply to enquiries.")

        if not can_reply:
             # This case should be covered by the specific role checks above
             raise OperationError("You do not have permission to reply to this enquiry.")

        # Format reply with role/name prefix
        formatted_reply = f"[{replier_role_str} - {replier_user.name}]: {reply_text}"
        try:
            enquiry.set_reply(formatted_reply)
            self._enq_repo.update(enquiry)
            self._enq_repo.save_all() # Persist
        except (ValueError, IntegrityError, DataSaveError) as e:
            # Revert in-memory change
            enquiry.set_reply("") # Assuming set_reply allows setting back to empty if needed for revert
            raise OperationError(f"Failed to save reply: {e}")


class ReportService:
    """Handles generation of reports."""
    def __init__(self, application_repository: IApplicationRepository,
                 project_service: ProjectService,
                 user_repository: IUserRepository):
        self._app_repo = application_repository
        self._project_service = project_service
        self._user_repo = user_repository

    def generate_booking_report_data(self, filter_project_name=None, filter_flat_type_str=None, filter_marital=None) -> list[dict]:
        """Generates data for the booking report based on filters."""
        report_data = []
        all_apps = self._app_repo.get_all()
        booked_apps = [app for app in all_apps if app.status == ApplicationStatus.BOOKED]

        # Prepare filters
        filter_flat_type = None
        if filter_flat_type_str:
            try:
                flat_type_val = int(filter_flat_type_str)
                filter_flat_type = FlatType(flat_type_val)
            except (ValueError, TypeError): pass # Ignore invalid filter

        filter_marital_lower = filter_marital.lower() if filter_marital else None

        # Process booked applications
        for app in booked_apps:
            project = self._project_service.find_project_by_name(app.project_name)
            if not project:
                print(f"Warning: Project '{app.project_name}' for booked application not found. Skipping report entry.")
                continue

            applicant = self._user_repo.find_user_by_nric(app.applicant_nric)
            if not applicant:
                print(f"Warning: Applicant '{app.applicant_nric}' for booked application not found. Skipping report entry.")
                continue

            # Apply filters
            if filter_project_name and project.project_name.lower() != filter_project_name.lower(): continue
            if filter_flat_type and app.flat_type != filter_flat_type: continue
            if filter_marital_lower and applicant.marital_status.lower() != filter_marital_lower: continue

            # Add data to report
            report_data.append({
                "NRIC": app.applicant_nric,
                "Applicant Name": applicant.name,
                "Age": applicant.age,
                "Marital Status": applicant.marital_status,
                "Flat Type": f"{app.flat_type.value}-Room",
                "Project Name": project.project_name,
                "Neighborhood": project.neighborhood
                # Add other project details if needed
            })

        # Sort report data? e.g., by Project Name, then Applicant Name
        report_data.sort(key=lambda x: (x["Project Name"], x["Applicant Name"]))

        return report_data


# ==============================================================================
# == VIEW (Presentation Layer) ==
# ==============================================================================

class BaseView:
    """Base class for all views. Handles basic input and output."""

    def display_message(self, message, error=False, info=False, warning=False):
        """Displays a formatted message."""
        prefix = ""
        if error: prefix = "ERROR: "
        elif warning: prefix = "WARNING: "
        elif info: prefix = "INFO: "
        print(f"\n{prefix}{message}")

    def get_input(self, prompt):
        """Gets basic string input from the user."""
        return input(f"{prompt}: ").strip()

    def get_password(self, prompt="Enter password"):
        """Gets password input (consider using getpass library for masking if allowed/needed)."""
        # Simple input for CLI as per requirement
        return input(f"{prompt}: ").strip()

    def display_menu(self, title, options: list[str]) -> int | None:
        """Displays a numbered menu and gets a valid choice."""
        print(f"\n--- {title} ---")
        if not options:
            print("No options available.")
            return None
        for i, option in enumerate(options):
            print(f"{i + 1}. {option}")
        print("--------------------")

        # Use InputUtil for validated integer input
        choice = InputUtil.get_valid_integer_input("Enter your choice", min_val=1, max_val=len(options))
        return choice # Return the 1-based index

    def display_list(self, title, items: list, empty_message="No items to display."):
        """Displays a numbered list of items."""
        print(f"\n--- {title} ---")
        if not items:
            print(empty_message)
        else:
            for i, item in enumerate(items):
                # Use __str__ representation of the item
                print(f"{i + 1}. {item}")
        print("--------------------")

    def display_dict(self, title, data_dict: dict):
        """Displays key-value pairs from a dictionary."""
        print(f"\n--- {title} ---")
        if not data_dict:
            print("(No details)")
        else:
            # Find max key length for alignment
            max_key_len = 0
            if data_dict: # Check if dict is not empty
                 try:
                      max_key_len = max(len(str(k)) for k in data_dict.keys())
                 except ValueError: # Handle case where dict might be empty after check (race condition?)
                      max_key_len = 0

            for key, value in data_dict.items():
                print(f"  {str(key):<{max_key_len}} : {value}")
        print("-" * (len(title) + 6)) # Adjust separator length

    def pause_for_user(self):
        """Pauses execution until the user presses Enter."""
        input("\nPress Enter to continue...")


class AuthView(BaseView):
    """View specific to authentication actions."""

    def prompt_login(self) -> tuple[str, str]:
        """Prompts for NRIC and password."""
        self.display_message("\n--- Login ---", info=True)
        nric = self.get_input("Enter NRIC")
        password = self.get_password()
        return nric, password

    def prompt_change_password(self, current_password_provided_by_controller) -> str | None:
        """Prompts for current and new password, performs basic checks."""
        self.display_message("\n--- Change Password ---", info=True)
        old_pwd = self.get_password("Enter your current password")

        # Controller should verify old_pwd matches stored password
        # View only checks if it matches the one passed in (if needed for flow)
        # Let's assume controller handles the check against the actual current password.
        # This method just gathers the new password.

        new_pwd = self.get_password("Enter your new password")
        confirm_pwd = self.get_password("Confirm your new password")

        if not new_pwd:
            self.display_message("New password cannot be empty.", error=True)
            return None
        if new_pwd != confirm_pwd:
            self.display_message("New passwords do not match.", error=True)
            return None

        # Return the *new* password for the controller to process
        return new_pwd


class ProjectView(BaseView):
    """View specific to displaying project information."""

    def display_project_summary(self, project: Project):
         """Displays a brief summary of a project for lists."""
         visibility_status = "Visible" if project.visibility else "Hidden"
         active_status = "Active" if project.is_currently_visible_and_active() else "Inactive/Closed"
         print(f"{project.project_name} ({project.neighborhood}) - Status: {active_status}, View: {visibility_status}")


    def display_project_details(self, project: Project, requesting_user_role: UserRole, applicant_marital_status=None):
        """Displays detailed information about a project, tailored by role."""
        details = {
            "Neighborhood": project.neighborhood,
            "Managed by NRIC": project.manager_nric,
            "Application Period": f"{InputUtil.format_date(project.opening_date)} to {InputUtil.format_date(project.closing_date)}",
            "Visibility": "ON" if project.visibility else "OFF",
            "Status": "Active & Visible" if project.is_currently_visible_and_active() else \
                      ("Visible but Inactive/Closed" if project.visibility else "Hidden")
        }

        # Flat details depend on applicant type or if viewer is staff
        units2, price2 = project.get_flat_details(FlatType.TWO_ROOM)
        units3, price3 = project.get_flat_details(FlatType.THREE_ROOM)

        details[f"{FlatType.TWO_ROOM.value}-Room Flats"] = f"{units2} units @ ${price2}"

        # Show 3-Room details to Married Applicants or Staff
        show_3_room = False
        if requesting_user_role in [UserRole.HDB_OFFICER, UserRole.HDB_MANAGER]:
            show_3_room = True
        elif requesting_user_role == UserRole.APPLICANT and applicant_marital_status == "Married":
             show_3_room = True

        if show_3_room:
            details[f"{FlatType.THREE_ROOM.value}-Room Flats"] = f"{units3} units @ ${price3}"
        else:
            # Single applicants don't see 3-room details unless they applied? No, spec says view based on group.
             details[f"{FlatType.THREE_ROOM.value}-Room Flats"] = "(Not applicable/visible for single applicants)"


        # Staff see officer details
        if requesting_user_role in [UserRole.HDB_OFFICER, UserRole.HDB_MANAGER]:
            assigned_count = len(project.officer_nrics)
            details["Officer Slots"] = f"{assigned_count} / {project.officer_slot} (Available: {project.get_available_officer_slots()})"
            if project.officer_nrics:
                details["Assigned Officers (NRIC)"] = ", ".join(project.officer_nrics)
            else:
                 details["Assigned Officers (NRIC)"] = "None"

        self.display_dict(f"Project Details: {project.project_name}", details)

    def prompt_project_filters(self, current_filters: dict) -> dict:
        """Prompts user for project filters."""
        self.display_message(f"Current Filters: {current_filters or 'None'}", info=True)
        location = self.get_input("Filter by Neighborhood (leave blank to keep/remove)")
        flat_type = self.get_input("Filter by Flat Type (2 or 3, leave blank to keep/remove)")

        new_filters = current_filters.copy()

        # Update location filter
        if location is not None: # Check if input was provided
            if location: # Input is not empty string
                new_filters['location'] = location
            else: # Input is empty string, remove filter
                 if 'location' in new_filters: del new_filters['location']

        # Update flat type filter
        if flat_type is not None: # Check if input was provided
            if flat_type in ['2', '3']:
                new_filters['flat_type_str'] = flat_type # Store as string
            elif flat_type == '': # Input is empty string, remove filter
                 if 'flat_type_str' in new_filters: del new_filters['flat_type_str']
            else:
                self.display_message("Invalid flat type filter. Keeping previous.", warning=True)

        return new_filters

    def select_project(self, projects: list[Project], action_verb="view details for") -> Project | None:
        """Displays a list of projects and prompts for selection."""
        if not projects:
            self.display_message("No projects available for selection.", info=True)
            return None

        print(f"\n--- Select Project to {action_verb} ---")
        project_map = {} # Map 1-based index to project object
        for i, p in enumerate(projects):
            # Display summary for selection
            print(f"{i + 1}. ", end="")
            self.display_project_summary(p)
            project_map[i + 1] = p
        print(" 0. Cancel")
        print("-------------------------------------")

        while True:
            choice = InputUtil.get_valid_integer_input("Enter the number of the project (or 0 to cancel)", min_val=0, max_val=len(projects))
            if choice == 0:
                return None
            elif choice in project_map:
                return project_map[choice]
            else:
                # Should not happen with validated input range
                self.display_message("Invalid selection.", error=True)

    def prompt_create_project_details(self) -> dict | None:
        """Prompts for details needed to create a new project."""
        self.display_message("\n--- Create New Project ---", info=True)
        details = {}
        try:
            details['name'] = InputUtil.get_non_empty_input("Enter Project Name")
            details['neighborhood'] = InputUtil.get_non_empty_input("Enter Neighborhood")
            details['n1'] = InputUtil.get_valid_integer_input("Enter Number of 2-Room units", min_val=0)
            details['p1'] = InputUtil.get_valid_integer_input("Enter Selling Price for 2-Room", min_val=0)
            details['n2'] = InputUtil.get_valid_integer_input("Enter Number of 3-Room units", min_val=0)
            details['p2'] = InputUtil.get_valid_integer_input("Enter Selling Price for 3-Room", min_val=0)
            details['od'] = InputUtil.get_valid_date_input("Enter Application Opening Date")
            details['cd'] = InputUtil.get_valid_date_input("Enter Application Closing Date")
            # Validate close date >= open date here for immediate feedback
            if details['cd'] < details['od']:
                 self.display_message("Closing date cannot be before opening date.", error=True)
                 return None # Indicate failure
            details['slot'] = InputUtil.get_valid_integer_input("Enter Max Officer Slots", min_val=0, max_val=10)
            return details
        except KeyboardInterrupt:
             self.display_message("Project creation cancelled.")
             return None
        except Exception as e:
             self.display_message(f"Error during input: {e}", error=True)
             return None


    def prompt_edit_project_details(self, project: Project) -> dict | None:
        """Prompts for details to edit, showing current values."""
        self.display_message(f"\n--- Editing Project: {project.project_name} ---", info=True)
        print("(Leave input blank to keep the current value)")
        updates = {}
        try:
            # Get potential new values, default to original if blank
            updates['project_name'] = self.get_input(f"New Project Name [{project.project_name}]") or project.project_name
            updates['neighborhood'] = self.get_input(f"New Neighborhood [{project.neighborhood}]") or project.neighborhood

            # Numeric values - require explicit number or blank
            n1_str = self.get_input(f"New Number of 2-Room units [{project.get_flat_details(FlatType.TWO_ROOM)[0]}]")
            updates['num_units1'] = int(n1_str) if n1_str.isdigit() else project.get_flat_details(FlatType.TWO_ROOM)[0]

            p1_str = self.get_input(f"New Selling Price for 2-Room [{project.get_flat_details(FlatType.TWO_ROOM)[1]}]")
            updates['price1'] = int(p1_str) if p1_str.isdigit() else project.get_flat_details(FlatType.TWO_ROOM)[1]

            n2_str = self.get_input(f"New Number of 3-Room units [{project.get_flat_details(FlatType.THREE_ROOM)[0]}]")
            updates['num_units2'] = int(n2_str) if n2_str.isdigit() else project.get_flat_details(FlatType.THREE_ROOM)[0]

            p2_str = self.get_input(f"New Selling Price for 3-Room [{project.get_flat_details(FlatType.THREE_ROOM)[1]}]")
            updates['price2'] = int(p2_str) if p2_str.isdigit() else project.get_flat_details(FlatType.THREE_ROOM)[1]

            slot_str = self.get_input(f"New Max Officer Slots [{project.officer_slot}]")
            updates['officer_slot'] = int(slot_str) if slot_str.isdigit() else project.officer_slot

            # Dates - require valid format or blank
            od_str = self.get_input(f"New Opening Date ({InputUtil.DATE_FORMAT}) [{InputUtil.format_date(project.opening_date)}]")
            updates['opening_date'] = InputUtil.parse_date(od_str) if od_str else project.opening_date

            cd_str = self.get_input(f"New Closing Date ({InputUtil.DATE_FORMAT}) [{InputUtil.format_date(project.closing_date)}]")
            updates['closing_date'] = InputUtil.parse_date(cd_str) if cd_str else project.closing_date

            # Validate close date >= open date here
            if updates['closing_date'] < updates['opening_date']:
                 self.display_message("Closing date cannot be before opening date.", error=True)
                 return None

            # Return only the fields that were actually changed from the original project state
            changed_updates = {}
            original_dict = project._to_dict() # Use internal dict for comparison
            if updates['project_name'] != original_dict['_project_name']: changed_updates['project_name'] = updates['project_name']
            if updates['neighborhood'] != original_dict['_neighborhood']: changed_updates['neighborhood'] = updates['neighborhood']
            if updates['num_units1'] != original_dict['_num_units1']: changed_updates['num_units1'] = updates['num_units1']
            if updates['price1'] != original_dict['_price1']: changed_updates['price1'] = updates['price1']
            if updates['num_units2'] != original_dict['_num_units2']: changed_updates['num_units2'] = updates['num_units2']
            if updates['price2'] != original_dict['_price2']: changed_updates['price2'] = updates['price2']
            if updates['officer_slot'] != original_dict['_officer_slot']: changed_updates['officer_slot'] = updates['officer_slot']
            if updates['opening_date'] != original_dict['_opening_date']: changed_updates['opening_date'] = updates['opening_date']
            if updates['closing_date'] != original_dict['_closing_date']: changed_updates['closing_date'] = updates['closing_date']

            return changed_updates if changed_updates else None # Return None if nothing changed

        except KeyboardInterrupt:
             self.display_message("Project editing cancelled.")
             return None
        except Exception as e:
             self.display_message(f"Error during input: {e}", error=True)
             return None


class ApplicationView(BaseView):
    """View specific to displaying application information."""

    def display_application_summary(self, application: Application, applicant_name: str):
         """Displays a brief summary of an application for lists."""
         req_status = " (Withdrawal Requested)" if application.request_withdrawal else ""
         print(f"Project: {application.project_name} | Applicant: {applicant_name} ({application.applicant_nric}) | Type: {application.flat_type.value}-Room | Status: {application.status.value}{req_status}")

    def display_application_details(self, application: Application, project: Project, applicant: Applicant):
        """Displays detailed status of a specific application."""
        details = {
            "Applicant": f"{applicant.name} ({applicant.nric})",
            "Age": applicant.age,
            "Marital Status": applicant.marital_status,
            "Project": f"{project.project_name} ({project.neighborhood})",
            "Flat Type Applied For": f"{application.flat_type.value}-Room",
            "Application Status": application.status.value
        }
        if application.request_withdrawal:
            details["Withdrawal Requested"] = "Yes (Pending Manager Action)"

        self.display_dict("BTO Application Status", details)

    def select_application(self, applications: list[Application], user_repo: IUserRepository, action_verb="view") -> Application | None:
        """Displays a list of applications and prompts for selection."""
        if not applications:
            self.display_message("No applications available for selection.", info=True)
            return None

        print(f"\n--- Select Application to {action_verb} ---")
        app_map = {} # Map 1-based index to application object
        for i, app in enumerate(applications):
            applicant = user_repo.find_user_by_nric(app.applicant_nric)
            applicant_name = applicant.name if applicant else "Unknown Applicant"
            print(f"{i + 1}. ", end="")
            self.display_application_summary(app, applicant_name)
            app_map[i + 1] = app
        print(" 0. Cancel")
        print("------------------------------------")

        while True:
            choice = InputUtil.get_valid_integer_input("Enter the number of the application (or 0 to cancel)", min_val=0, max_val=len(applications))
            if choice == 0:
                return None
            elif choice in app_map:
                return app_map[choice]
            else:
                self.display_message("Invalid selection.", error=True)

    def prompt_flat_type_selection(self, project: Project, applicant: Applicant) -> FlatType | None:
        """Prompts the applicant to select a flat type based on eligibility and availability."""
        available_types = []
        is_single = applicant.marital_status == "Single"
        is_married = applicant.marital_status == "Married"

        units2, _ = project.get_flat_details(FlatType.TWO_ROOM)
        units3, _ = project.get_flat_details(FlatType.THREE_ROOM)

        # Check eligibility and availability for 2-Room
        if units2 > 0:
            if (is_single and applicant.age >= 35) or (is_married and applicant.age >= 21):
                available_types.append(FlatType.TWO_ROOM)

        # Check eligibility and availability for 3-Room
        if units3 > 0:
            if is_married and applicant.age >= 21:
                available_types.append(FlatType.THREE_ROOM)

        # Handle selection
        if not available_types:
            self.display_message("No suitable or available flat types for you in this project.", error=True)
            return None
        elif len(available_types) == 1:
            selected_type = available_types[0]
            self.display_message(f"Automatically selecting {selected_type.value}-Room flat (only option available/eligible).", info=True)
            return selected_type
        else:
            # Present choice
            options_str = ' or '.join(str(ft.value) for ft in available_types)
            while True:
                choice_str = self.get_input(f"Select flat type ({options_str})")
                try:
                    choice_val = int(choice_str)
                    choice_enum = FlatType(choice_val) # Convert to Enum
                    if choice_enum in available_types:
                        return choice_enum
                    else:
                        self.display_message(f"Invalid choice. Please enter one of: {options_str}", error=True)
                except (ValueError, TypeError):
                    self.display_message("Invalid input. Please enter a number (2 or 3).", error=True)


class EnquiryView(BaseView):
    """View specific to displaying and interacting with enquiries."""

    def display_enquiry_summary(self, enquiry: Enquiry):
         """Displays a brief summary of an enquiry for lists."""
         reply_status = "Replied" if enquiry.is_replied() else "Unreplied"
         text_preview = (enquiry.text[:47] + '...') if len(enquiry.text) > 50 else enquiry.text
         print(f"ID: {enquiry.enquiry_id:<4} | Project: {enquiry.project_name:<15} | Status: {reply_status:<9} | Text: {text_preview}")

    def display_enquiry_details(self, enquiry: Enquiry, project_name: str, applicant_name: str):
        """Displays the full details of an enquiry."""
        details = {
            "Enquiry ID": enquiry.enquiry_id,
            "Project": project_name, # Use provided name in case project deleted
            "Submitted by": f"{applicant_name} ({enquiry.applicant_nric})",
            "Enquiry Text": enquiry.text,
            "Reply": enquiry.reply if enquiry.is_replied() else "(No reply yet)"
        }
        self.display_dict(f"Enquiry Details", details)

    def select_enquiry(self, enquiries: list[Enquiry], action_verb="view") -> Enquiry | None:
        """Displays a list of enquiries and prompts for selection by ID."""
        if not enquiries:
            self.display_message("No enquiries available for selection.", info=True)
            return None

        print(f"\n--- Select Enquiry (by ID) to {action_verb} ---")
        enquiry_map = {} # Map ID to enquiry object
        for enq in enquiries:
            self.display_enquiry_summary(enq)
            enquiry_map[enq.enquiry_id] = enq
        print("  ID: 0    | Cancel")
        print("--------------------------------------------------")

        while True:
            # Use get_valid_integer_input for ID selection
            enquiry_id = InputUtil.get_valid_integer_input("Enter the ID of the enquiry (or 0 to cancel)", min_val=0)
            if enquiry_id == 0:
                return None
            elif enquiry_id in enquiry_map:
                return enquiry_map[enquiry_id]
            else:
                self.display_message("Invalid enquiry ID.", error=True)

    def prompt_enquiry_text(self, current_text=None) -> str | None:
        """Prompts for enquiry text (new or edit)."""
        prompt = "Enter enquiry text"
        if current_text:
            prompt = f"Enter new enquiry text (current: '{current_text[:30]}...')"
        try:
            return InputUtil.get_non_empty_input(prompt)
        except KeyboardInterrupt:
             self.display_message("Input cancelled.")
             return None


    def prompt_reply_text(self) -> str | None:
        """Prompts for reply text."""
        try:
            return InputUtil.get_non_empty_input("Enter reply text")
        except KeyboardInterrupt:
             self.display_message("Input cancelled.")
             return None


class OfficerView(BaseView):
    """View specific to HDB Officer actions (beyond Applicant actions)."""

    def display_registration_summary(self, registration: Registration, officer_name: str):
         """Displays a brief summary of an officer registration."""
         print(f"Project: {registration.project_name} | Officer: {officer_name} ({registration.officer_nric}) | Status: {registration.status.value}")

    def display_registration_details(self, registration: Registration, project_name: str, officer_name: str):
        """Displays details of an officer's registration."""
        details = {
            "Officer": f"{officer_name} ({registration.officer_nric})",
            "Project": project_name, # Use provided name
            "Registration Status": registration.status.value
        }
        self.display_dict("Officer Registration Details", details)

    def select_registration(self, registrations: list[Registration], user_repo: IUserRepository, action_verb="view") -> Registration | None:
        """Displays a list of registrations and prompts for selection."""
        if not registrations:
            self.display_message("No registrations available for selection.", info=True)
            return None

        print(f"\n--- Select Registration to {action_verb} ---")
        reg_map = {} # Map 1-based index to registration object
        for i, reg in enumerate(registrations):
            officer = user_repo.find_user_by_nric(reg.officer_nric)
            officer_name = officer.name if officer else "Unknown Officer"
            print(f"{i + 1}. ", end="")
            self.display_registration_summary(reg, officer_name)
            reg_map[i + 1] = reg
        print(" 0. Cancel")
        print("------------------------------------")

        while True:
            choice = InputUtil.get_valid_integer_input("Enter the number of the registration (or 0 to cancel)", min_val=0, max_val=len(registrations))
            if choice == 0:
                return None
            elif choice in reg_map:
                return reg_map[choice]
            else:
                self.display_message("Invalid selection.", error=True)

    def prompt_applicant_nric(self, purpose="action") -> str | None:
         """Prompts for an applicant's NRIC for a specific purpose."""
         while True:
             try:
                 nric = self.get_input(f"Enter Applicant's NRIC for {purpose} (or type 'cancel')")
                 if nric.lower() == 'cancel': return None
                 if InputUtil.validate_nric(nric):
                     return nric
                 else:
                     self.display_message("Invalid NRIC format. Please try again.", error=True)
             except KeyboardInterrupt:
                  self.display_message("Input cancelled.")
                  return None


    def display_receipt(self, receipt_data: dict):
        """Displays the booking receipt details."""
        self.display_dict("Booking Receipt", receipt_data)


class ManagerView(BaseView):
     """View specific to HDB Manager actions."""
     # Currently, Manager actions reuse prompts from other views (Project, Officer, Application, Enquiry)
     # Add specific Manager prompts here if needed, e.g., for report generation filters.
     # Inherits display methods from BaseView.

     def display_officer_registration_for_approval(self, registration: Registration, officer: User, project: Project):
          """Displays registration details specifically in the context of approval/rejection."""
          print("\n--- Officer Registration for Review ---")
          print(f"  Registration for Project: {project.project_name} ({project.neighborhood})")
          print(f"  Officer: {officer.name} ({officer.nric})")
          print(f"  Current Status: {registration.status.value}")
          print(f"  Project Officer Slots: {len(project.officer_nrics)} / {project.officer_slot}")
          print("---------------------------------------")

     def display_application_for_approval(self, application: Application, applicant: User, project: Project):
           """Displays application details specifically in the context of approval/rejection."""
           print("\n--- Application for Review ---")
           print(f"  Applicant: {applicant.name} ({applicant.nric})")
           print(f"  Project: {project.project_name}")
           print(f"  Flat Type: {application.flat_type.value}-Room")
           print(f"  Current Status: {application.status.value}")
           units, _ = project.get_flat_details(application.flat_type)
           print(f"  Units Remaining ({application.flat_type.value}-Room): {units}")
           if application.request_withdrawal:
                print("  ** Withdrawal Requested **")
           print("-----------------------------")

     def display_withdrawal_request_for_approval(self, application: Application, applicant: User, project: Project):
           """Displays withdrawal request details specifically in the context of approval/rejection."""
           print("\n--- Withdrawal Request for Review ---")
           print(f"  Applicant: {applicant.name} ({applicant.nric})")
           print(f"  Project: {project.project_name}")
           print(f"  Flat Type: {application.flat_type.value}-Room")
           print(f"  Current Status: {application.status.value}")
           print(f"  ** Withdrawal Requested: YES **")
           print("------------------------------------")


class ReportView(BaseView):
    """View specific to displaying reports."""

    def display_report(self, title, report_data: list[dict], headers: list[str]):
        """Displays report data in a formatted table."""
        print(f"\n--- {title} ---")
        if not report_data:
            print("No data found for this report.")
            print("-" * (len(title) + 6))
            return

        # Calculate column widths
        widths = {header: len(header) for header in headers}
        for row in report_data:
            for header in headers:
                # Ensure value exists and convert to string before checking length
                value_str = str(row.get(header, ''))
                widths[header] = max(widths[header], len(value_str))

        # Print header
        header_line = " | ".join(f"{header:<{widths[header]}}" for header in headers)
        print(header_line)
        print("-" * len(header_line))

        # Print data rows
        for row in report_data:
            row_line = " | ".join(f"{str(row.get(header, '')):<{widths[header]}}" for header in headers)
            print(row_line)

        # Print footer/summary
        print("-" * len(header_line))
        print(f"Total Records: {len(report_data)}")
        print("-" * (len(title) + 6))


    def prompt_report_filters(self) -> dict:
        """Prompts for filters specific to the booking report."""
        self.display_message("\n--- Generate Booking Report Filters ---", info=True)
        filters = {}
        try:
            filters['filter_marital'] = self.get_input("Filter by Marital Status (Single/Married, leave blank for all)")
            filters['filter_project_name'] = self.get_input("Filter by Project Name (leave blank for all)")
            filters['filter_flat_type_str'] = self.get_input("Filter by Flat Type (2/3, leave blank for all)")

            # Basic validation/cleaning of filters
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
        except KeyboardInterrupt:
             self.display_message("Filter input cancelled.")
             return {} # Return empty filters


# ==============================================================================
# == CONTROLLER (Application Flow Logic) ==
# ==============================================================================

class BaseRoleController(ABC):
    """Abstract base class for role-specific controllers."""
    def __init__(self, current_user: User, services: dict, views: dict):
        self._current_user = current_user
        self._services = services
        self._views = views
        self._user_filters = {} # Store user-specific filter settings

    @abstractmethod
    def run_menu(self):
        """Displays the menu for the role and handles the selected action."""
        pass

    def _get_common_actions(self) -> dict[str, callable]:
        """Returns a dictionary of actions common to all logged-in users."""
        return {
            "Change Password": self._handle_change_password,
            "Logout": self._signal_logout,
            "Exit System": self._signal_exit,
        }

    def _handle_change_password(self):
        """Handles the change password workflow."""
        auth_service: AuthService = self._services['auth']
        auth_view: AuthView = self._views['auth']
        base_view: BaseView = self._views['base']

        # Get the new password from the view
        new_password = auth_view.prompt_change_password(self._current_user.get_password_for_storage())

        if new_password:
            # Verify the *actual* current password before changing
            current_password_attempt = auth_view.get_password("Re-enter current password for verification")
            if not self._current_user.check_password(current_password_attempt):
                 base_view.display_message("Verification failed: Incorrect current password.", error=True)
                 return # Abort change

            # If verification passes, proceed with the change
            try:
                auth_service.change_password(self._current_user, new_password)
                base_view.display_message("Password changed successfully. Please remember your new password.", info=True)
            except OperationError as e:
                 base_view.display_message(str(e), error=True)
            except Exception as e: # Catch unexpected errors
                 base_view.display_message(f"An unexpected error occurred during password change: {e}", error=True)


    def _signal_logout(self):
        """Returns a signal to the main controller to log out."""
        return "LOGOUT"

    def _signal_exit(self):
        """Returns a signal to the main controller to exit."""
        return "EXIT"

    def _prepare_receipt_data(self, application: Application, project: Project, applicant: Applicant) -> dict:
        """Helper to format data consistently for receipt display."""
        return {
            "Applicant Name": applicant.name,
            "NRIC": applicant.nric,
            "Age": applicant.age,
            "Marital Status": applicant.marital_status,
            "Flat Type Booked": f"{application.flat_type.value}-Room",
            "Project Name": project.project_name,
            "Neighborhood": project.neighborhood,
            "Booking Status": application.status.value # Should be BOOKED
            # Add timestamp or other details if needed
        }

    def _handle_view_projects_common(self, role: UserRole):
         """Common logic for viewing projects, used by Applicant and Officer."""
         project_service: ProjectService = self._services['project']
         app_service: ApplicationService = self._services['app']
         project_view: ProjectView = self._views['project']
         base_view: BaseView = self._views['base']

         # Get projects viewable by this user
         current_app = app_service.find_application_by_applicant(self._current_user.nric)
         if role == UserRole.APPLICANT or role == UserRole.HDB_OFFICER:
              # Applicants/Officers see projects based on eligibility rules
              projects = project_service.get_viewable_projects_for_applicant(self._current_user, current_app)
         else: # Should not happen if called correctly, but fallback
              projects = project_service.get_all_projects()


         # Apply user's saved filters
         filtered_projects = project_service.filter_projects(
             projects, **self._user_filters
         )

         base_view.display_message(f"Current Filters: {self._user_filters or 'None'}", info=True)
         if not filtered_projects:
             base_view.display_message("No projects match your criteria or eligibility.")
         else:
             base_view.display_message("Displaying projects you are eligible to view/apply for:")
             for project in filtered_projects:
                 # Pass applicant's marital status for correct display logic in view
                 project_view.display_project_details(project, requesting_user_role=role, applicant_marital_status=self._current_user.marital_status)

         # Option to update filters
         if InputUtil.get_yes_no_input("Update filters?"):
             self._user_filters = project_view.prompt_project_filters(self._user_filters)
             base_view.display_message("Filters updated. View projects again to see changes.", info=True)


class ApplicantController(BaseRoleController):
    """Controller for Applicant users."""

    def run_menu(self):
        """Displays the Applicant menu and handles actions."""
        base_view: BaseView = self._views['base']
        actions = {
            "View/Filter Projects": self._handle_view_projects,
            "Apply for Project": self._handle_apply_for_project,
            "View My Application Status": self._handle_view_application_status,
            "Request Application Withdrawal": self._handle_request_withdrawal,
            "Submit Enquiry": self._handle_submit_enquiry,
            "View My Enquiries": self._handle_view_my_enquiries,
            "Edit My Enquiry": self._handle_edit_my_enquiry,
            "Delete My Enquiry": self._handle_delete_my_enquiry,
            **self._get_common_actions() # Add common actions
        }
        options = list(actions.keys())

        choice_index = base_view.display_menu("Applicant Menu", options)
        if choice_index is None: return None # Should not happen with validated input

        selected_action_name = options[choice_index - 1]
        action_method = actions[selected_action_name]

        # Execute the chosen action
        try:
            return action_method() # Return signal if logout/exit
        except (OperationError, IntegrityError) as e:
            base_view.display_message(str(e), error=True)
        except KeyboardInterrupt:
             base_view.display_message("Operation cancelled.")
        except Exception as e:
             base_view.display_message(f"An unexpected error occurred: {e}", error=True)
             # Consider logging the full traceback here for debugging
             import traceback
             traceback.print_exc()

        base_view.pause_for_user() # Pause after action/error before showing menu again
        return None # Continue showing menu unless logout/exit signal received

    # --- Action Handlers ---

    def _handle_view_projects(self):
        """Handler for viewing projects."""
        self._handle_view_projects_common(UserRole.APPLICANT)


    def _handle_apply_for_project(self):
        """Handler for applying for a project."""
        app_service: ApplicationService = self._services['app']
        project_service: ProjectService = self._services['project']
        project_view: ProjectView = self._views['project']
        app_view: ApplicationView = self._views['app']
        base_view: BaseView = self._views['base']

        # Service layer checks for existing active application and role eligibility
        # Get projects eligible for application (visible, active, meets basic criteria)
        potential_projects = project_service.get_viewable_projects_for_applicant(self._current_user)
        # Filter further for only those currently active for application
        selectable_projects = [p for p in potential_projects if p.is_currently_visible_and_active()]

        # Select project
        project_to_apply = project_view.select_project(selectable_projects, action_verb="apply for")
        if not project_to_apply: return # User cancelled

        # Select flat type (View handles eligibility display based on project/applicant)
        flat_type = app_view.prompt_flat_type_selection(project_to_apply, self._current_user)
        if flat_type is None: return # User cancelled or no eligible types

        # Attempt application via service (handles final eligibility checks)
        app_service.apply_for_project(self._current_user, project_to_apply, flat_type)
        base_view.display_message(f"Application submitted successfully for {flat_type.value}-Room flat in '{project_to_apply.project_name}'.", info=True)


    def _handle_view_application_status(self):
        """Handler for viewing the applicant's application status."""
        app_service: ApplicationService = self._services['app']
        project_service: ProjectService = self._services['project']
        app_view: ApplicationView = self._views['app']
        base_view: BaseView = self._views['base']

        application = app_service.find_application_by_applicant(self._current_user.nric)
        if not application:
            base_view.display_message("You do not have an active BTO application.")
            # Show past unsuccessful applications?
            all_apps = self._services['app']._app_repo.find_all_by_applicant_nric(self._current_user.nric)
            unsuccessful = [app for app in all_apps if app.status == ApplicationStatus.UNSUCCESSFUL]
            if unsuccessful:
                 base_view.display_message("You have past unsuccessful applications:")
                 user_repo: IUserRepository = self._services['user']
                 app_view.select_application(unsuccessful, user_repo, action_verb="view past")
            return

        project = project_service.find_project_by_name(application.project_name)
        if not project:
            # Data integrity issue, but show what we can
            base_view.display_message(f"Error: Project '{application.project_name}' associated with your application not found.", error=True)
            # Display raw application data?
            app_view.display_dict("Application Data (Project Missing)", application.to_csv_dict())
            return

        app_view.display_application_details(application, project, self._current_user)


    def _handle_request_withdrawal(self):
        """Handler for requesting application withdrawal."""
        app_service: ApplicationService = self._services['app']
        base_view: BaseView = self._views['base']

        application = app_service.find_application_by_applicant(self._current_user.nric)
        if not application:
            raise OperationError("You do not have an active BTO application to withdraw.") # Raise error as action is impossible

        # Service layer checks if withdrawal already requested or status invalid
        if InputUtil.get_yes_no_input(f"Confirm request withdrawal for application to '{application.project_name}'? (Status: {application.status.value})"):
            app_service.request_withdrawal(application)
            base_view.display_message("Withdrawal requested. This is pending Manager approval/rejection.", info=True)


    def _handle_submit_enquiry(self):
        """Handler for submitting a new enquiry."""
        enq_service: EnquiryService = self._services['enq']
        project_service: ProjectService = self._services['project']
        app_service: ApplicationService = self._services['app']
        project_view: ProjectView = self._views['project']
        enq_view: EnquiryView = self._views['enq']
        base_view: BaseView = self._views['base']

        # Get projects the applicant can view (including their applied one)
        current_app = app_service.find_application_by_applicant(self._current_user.nric)
        viewable_projects = project_service.get_viewable_projects_for_applicant(self._current_user, current_app)

        project_to_enquire = project_view.select_project(viewable_projects, action_verb="submit enquiry for")
        if not project_to_enquire: return # Cancelled

        text = enq_view.prompt_enquiry_text()
        if not text: return # Cancelled input

        # Service handles check if project is actually viewable by applicant
        enq_service.submit_enquiry(self._current_user, project_to_enquire, text)
        base_view.display_message("Enquiry submitted successfully.", info=True)


    def _handle_view_my_enquiries(self):
        """Handler for viewing the applicant's own enquiries."""
        enq_service: EnquiryService = self._services['enq']
        project_service: ProjectService = self._services['project']
        enq_view: EnquiryView = self._views['enq']
        base_view: BaseView = self._views['base']

        my_enquiries = enq_service.get_enquiries_by_applicant(self._current_user.nric)
        if not my_enquiries:
            base_view.display_message("You have not submitted any enquiries.")
            return

        base_view.display_message("Your Submitted Enquiries:", info=True)
        for enquiry in my_enquiries:
            project = project_service.find_project_by_name(enquiry.project_name)
            project_name = project.project_name if project else f"Unknown/Deleted Project ({enquiry.project_name})"
            # Display full details for each
            enq_view.display_enquiry_details(enquiry, project_name, self._current_user.name)


    def _handle_edit_my_enquiry(self):
        """Handler for editing an applicant's own unreplied enquiry."""
        enq_service: EnquiryService = self._services['enq']
        enq_view: EnquiryView = self._views['enq']
        base_view: BaseView = self._views['base']

        my_enquiries = enq_service.get_enquiries_by_applicant(self._current_user.nric)
        editable_enquiries = [e for e in my_enquiries if not e.is_replied()]

        enquiry_to_edit = enq_view.select_enquiry(editable_enquiries, action_verb="edit")
        if not enquiry_to_edit: return # Cancelled or none editable

        new_text = enq_view.prompt_enquiry_text(current_text=enquiry_to_edit.text)
        if not new_text: return # Cancelled input

        # Service handles permission check (already done by filtering) and reply check
        enq_service.edit_enquiry(self._current_user, enquiry_to_edit, new_text)
        base_view.display_message(f"Enquiry ID {enquiry_to_edit.enquiry_id} updated successfully.", info=True)


    def _handle_delete_my_enquiry(self):
        """Handler for deleting an applicant's own unreplied enquiry."""
        enq_service: EnquiryService = self._services['enq']
        enq_view: EnquiryView = self._views['enq']
        base_view: BaseView = self._views['base']

        my_enquiries = enq_service.get_enquiries_by_applicant(self._current_user.nric)
        deletable_enquiries = [e for e in my_enquiries if not e.is_replied()]

        enquiry_to_delete = enq_view.select_enquiry(deletable_enquiries, action_verb="delete")
        if not enquiry_to_delete: return # Cancelled or none deletable

        if InputUtil.get_yes_no_input(f"Are you sure you want to delete Enquiry ID {enquiry_to_delete.enquiry_id}?"):
            # Service handles permission check (already done by filtering) and reply check
            enq_service.delete_enquiry(self._current_user, enquiry_to_delete)
            base_view.display_message(f"Enquiry ID {enquiry_to_delete.enquiry_id} deleted successfully.", info=True)


class OfficerController(ApplicantController): # Inherits Applicant actions
    """Controller for HDB Officer users."""

    def run_menu(self):
        """Displays the Officer menu and handles actions."""
        base_view: BaseView = self._views['base']
        # Combine Applicant actions with Officer-specific actions
        applicant_actions = {
            "View/Filter Projects": self._handle_view_projects, # Uses common handler
            "Apply for Project": self._handle_apply_for_project,
            "View My Application Status": self._handle_view_application_status,
            "Request Application Withdrawal": self._handle_request_withdrawal,
            "Submit Enquiry": self._handle_submit_enquiry,
            "View My Enquiries": self._handle_view_my_enquiries,
            "Edit My Enquiry": self._handle_edit_my_enquiry,
            "Delete My Enquiry": self._handle_delete_my_enquiry,
        }
        officer_actions = {
            "Register for Project as Officer": self._handle_register_for_project,
            "View My Officer Registrations": self._handle_view_my_registrations,
            "View Handled Projects Details": self._handle_view_handled_projects,
            "View/Reply Enquiries (Handled Projects)": self._handle_view_reply_enquiries_officer,
            "Book Flat for Applicant": self._handle_book_flat,
            "Generate Booking Receipt": self._handle_generate_receipt,
        }

        # Order matters for display
        actions = {
             **applicant_actions,
             "--- Officer Actions ---": None, # Separator
             **officer_actions,
             "--- General Actions ---": None, # Separator
             **self._get_common_actions()
        }
        options = [opt for opt in actions.keys() if actions[opt] is not None] # Filter out separators for choice mapping
        display_options = list(actions.keys()) # Keep separators for display

        choice_index = base_view.display_menu("HDB Officer Menu", display_options)
        if choice_index is None: return None

        # Map display index back to action key (handling separators)
        selected_action_name = display_options[choice_index - 1]
        action_method = actions.get(selected_action_name)

        if action_method:
            # Execute the chosen action
            try:
                return action_method() # Return signal if logout/exit
            except (OperationError, IntegrityError) as e:
                base_view.display_message(str(e), error=True)
            except KeyboardInterrupt:
                 base_view.display_message("Operation cancelled.")
            except Exception as e:
                 base_view.display_message(f"An unexpected error occurred: {e}", error=True)
                 import traceback
                 traceback.print_exc()
        elif selected_action_name.startswith("---"):
             pass # Ignore separator selection
        else:
             base_view.display_message("Invalid menu option selected.", error=True)


        base_view.pause_for_user() # Pause after action/error before showing menu again
        return None # Continue showing menu unless logout/exit signal received

    # --- Officer-Specific Action Handlers ---

    def _handle_register_for_project(self):
        """Handler for registering as an officer for a project."""
        reg_service: RegistrationService = self._services['reg']
        project_service: ProjectService = self._services['project']
        app_service: ApplicationService = self._services['app'] # Needed for checks
        project_view: ProjectView = self._views['project']
        base_view: BaseView = self._views['base']

        # Get all projects
        all_projects = project_service.get_all_projects()

        # Filter out projects the officer cannot register for
        my_regs = {reg.project_name for reg in reg_service.get_registrations_by_officer(self._current_user.nric)}
        # Check *all* past/present applications by this officer
        my_apps = self._services['app']._app_repo.find_all_by_applicant_nric(self._current_user.nric)
        my_app_projects = {app.project_name for app in my_apps}

        selectable_projects = [
            p for p in all_projects
            if p.project_name not in my_regs and \
               p.project_name not in my_app_projects and \
               p.manager_nric != self._current_user.nric # Cannot register for own project if somehow manager/officer roles overlap
        ]

        # Further filter based on overlapping approved registrations (Service layer does final check)
        # We can pre-filter here for better UX, but service layer check is crucial
        # This pre-filtering is complex, rely on service layer check for now.

        project_to_register = project_view.select_project(selectable_projects, action_verb="register for as Officer")
        if not project_to_register: return # Cancelled

        # Service handles eligibility checks (including overlap)
        reg_service.officer_register_for_project(self._current_user, project_to_register)
        base_view.display_message(f"Registration submitted successfully for project '{project_to_register.project_name}'. Pending Manager approval.", info=True)


    def _handle_view_my_registrations(self):
        """Handler for viewing the officer's own registrations."""
        reg_service: RegistrationService = self._services['reg']
        project_service: ProjectService = self._services['project']
        officer_view: OfficerView = self._views['officer']
        base_view: BaseView = self._views['base']

        my_registrations = reg_service.get_registrations_by_officer(self._current_user.nric)
        if not my_registrations:
            base_view.display_message("You have no officer registrations.")
            return

        base_view.display_message("Your Officer Registrations:", info=True)
        for reg in my_registrations:
            project = project_service.find_project_by_name(reg.project_name)
            project_name = project.project_name if project else f"Unknown/Deleted Project ({reg.project_name})"
            # Display full details
            officer_view.display_registration_details(reg, project_name, self._current_user.name)


    def _handle_view_handled_projects(self):
        """Handler for viewing details of projects the officer handles."""
        project_service: ProjectService = self._services['project']
        project_view: ProjectView = self._views['project']
        base_view: BaseView = self._views['base']

        # Get projects where officer is directly assigned
        handled_project_names = project_service.get_handled_project_names_for_officer(self._current_user.nric)
        handled_projects = [p for p in project_service.get_all_projects() if p.project_name in handled_project_names]

        if not handled_projects:
            base_view.display_message("You are not currently assigned to handle any projects.")
            return

        base_view.display_message("Projects You Handle (Assigned):", info=True)
        sorted_handled = sorted(handled_projects, key=lambda p: p.project_name)
        for project in sorted_handled:
             # Display details from Officer's perspective
             project_view.display_project_details(project, requesting_user_role=UserRole.HDB_OFFICER, applicant_marital_status=self._current_user.marital_status)


    def _get_enquiries_for_handled_projects(self) -> list[tuple[Enquiry, str]]:
         """Helper to get enquiries for projects the officer handles."""
         enq_service: EnquiryService = self._services['enq']
         project_service: ProjectService = self._services['project']
         user_repo: IUserRepository = self._services['user']

         handled_project_names = project_service.get_handled_project_names_for_officer(self._current_user.nric)
         relevant_enquiries_data = []
         if not handled_project_names:
             return relevant_enquiries_data

         all_enquiries = enq_service.get_all_enquiries()
         for enquiry in all_enquiries:
             if enquiry.project_name in handled_project_names:
                 applicant = user_repo.find_user_by_nric(enquiry.applicant_nric)
                 applicant_name = applicant.name if applicant else "Unknown Applicant"
                 relevant_enquiries_data.append((enquiry, applicant_name))
         return relevant_enquiries_data


    def _handle_view_reply_enquiries_officer(self):
        """Handler for viewing and replying to enquiries for handled projects."""
        enq_service: EnquiryService = self._services['enq']
        enq_view: EnquiryView = self._views['enq']
        base_view: BaseView = self._views['base']

        relevant_enquiries_data = self._get_enquiries_for_handled_projects()

        if not relevant_enquiries_data:
            base_view.display_message("No enquiries found for the projects you handle.")
            return

        unreplied_enquiries = [e for e, name in relevant_enquiries_data if not e.is_replied()]

        base_view.display_message("Enquiries for Projects You Handle:", info=True)
        for enquiry, applicant_name in relevant_enquiries_data:
            # Display full details
            enq_view.display_enquiry_details(enquiry, enquiry.project_name, applicant_name)

        if not unreplied_enquiries:
            base_view.display_message("\nNo unreplied enquiries requiring action.")
            return

        # Option to reply
        if InputUtil.get_yes_no_input("\nReply to an unreplied enquiry?"):
            enquiry_to_reply = enq_view.select_enquiry(unreplied_enquiries, action_verb="reply to")
            if enquiry_to_reply:
                reply_text = enq_view.prompt_reply_text()
                if reply_text:
                    # Service handles permission check and saving
                    enq_service.reply_to_enquiry(self._current_user, enquiry_to_reply, reply_text)
                    base_view.display_message(f"Reply submitted successfully for Enquiry ID {enquiry_to_reply.enquiry_id}.", info=True)


    def _handle_book_flat(self):
        """Handler for booking a flat for an applicant."""
        app_service: ApplicationService = self._services['app']
        user_repo: IUserRepository = self._services['user']
        officer_view: OfficerView = self._views['officer']
        base_view: BaseView = self._views['base']

        # Get applicant NRIC
        applicant_nric = officer_view.prompt_applicant_nric(purpose="booking flat")
        if not applicant_nric: return # Cancelled

        applicant = user_repo.find_user_by_nric(applicant_nric)
        if not applicant:
            raise OperationError(f"Applicant with NRIC {applicant_nric} not found.")

        # Find the application eligible for booking (should be SUCCESSFUL)
        # Use find_application_by_applicant which gets the non-unsuccessful one
        application = app_service.find_application_by_applicant(applicant_nric)
        if not application:
            raise OperationError(f"No active application found for applicant {applicant_nric}.")
        if application.status != ApplicationStatus.SUCCESSFUL:
             raise OperationError(f"Application for {applicant_nric} is not in '{ApplicationStatus.SUCCESSFUL.value}' status (Current: {application.status.value}). Cannot book.")


        # Confirm action
        if not InputUtil.get_yes_no_input(f"Confirm booking {application.flat_type.value}-Room flat in '{application.project_name}' for {applicant.name} ({applicant.nric})?"):
             base_view.display_message("Booking cancelled.")
             return

        # Service handles permission checks, status update, unit count decrease, and saving
        updated_project, booked_applicant = app_service.officer_book_flat(self._current_user, application)

        base_view.display_message("Flat booked successfully! Unit count updated.", info=True)

        # Display receipt immediately
        receipt_data = self._prepare_receipt_data(application, updated_project, booked_applicant)
        officer_view.display_receipt(receipt_data)


    def _handle_generate_receipt(self):
        """Handler for generating a receipt for an already booked flat."""
        app_service: ApplicationService = self._services['app']
        project_service: ProjectService = self._services['project']
        user_repo: IUserRepository = self._services['user']
        officer_view: OfficerView = self._views['officer']
        base_view: BaseView = self._views['base']

        # Get applicant NRIC
        applicant_nric = officer_view.prompt_applicant_nric(purpose="generating receipt")
        if not applicant_nric: return # Cancelled

        applicant = user_repo.find_user_by_nric(applicant_nric)
        if not applicant:
            raise OperationError(f"Applicant with NRIC {applicant_nric} not found.")

        # Find the BOOKED application for this applicant
        booked_app = None
        all_apps = app_service.get_all_applications() # Check all, including past
        for app in all_apps:
            if app.applicant_nric == applicant_nric and app.status == ApplicationStatus.BOOKED:
                booked_app = app
                break

        if not booked_app:
            raise OperationError(f"No booked application found for NRIC {applicant_nric}.")

        # Check if officer handles the project for this booked application
        project = project_service.find_project_by_name(booked_app.project_name)
        if not project:
            raise IntegrityError(f"Project '{booked_app.project_name}' for booked application not found.")

        handled_names = project_service.get_handled_project_names_for_officer(self._current_user.nric)
        if project.project_name not in handled_names:
            raise OperationError(f"You do not handle the project ('{project.project_name}') for this booked application.")

        # Generate and display receipt
        receipt_data = self._prepare_receipt_data(booked_app, project, applicant)
        officer_view.display_receipt(receipt_data)


class ManagerController(BaseRoleController):
    """Controller for HDB Manager users."""

    def run_menu(self):
        """Displays the Manager menu and handles actions."""
        base_view: BaseView = self._views['base']
        actions = {
            "Create Project": self._handle_create_project,
            "Edit Project": self._handle_edit_project,
            "Delete Project": self._handle_delete_project,
            "Toggle Project Visibility": self._handle_toggle_visibility,
            "View All/Filter Projects": self._handle_view_all_projects,
            "View My Managed Projects": self._handle_view_my_projects,
            "--- Officer Management ---": None,
            "View Officer Registrations (Project)": self._handle_view_officer_registrations,
            "Approve Officer Registration": self._handle_approve_officer_registration,
            "Reject Officer Registration": self._handle_reject_officer_registration,
            "--- Application Management ---": None,
            "View Applications (Project)": self._handle_view_applications,
            "Approve Application": self._handle_approve_application,
            "Reject Application": self._handle_reject_application,
            "Approve Withdrawal Request": self._handle_approve_withdrawal,
            "Reject Withdrawal Request": self._handle_reject_withdrawal,
            "--- Reporting & Enquiries ---": None,
            "Generate Booking Report": self._handle_generate_booking_report,
            "View All Enquiries": self._handle_view_all_enquiries,
            "View/Reply Enquiries (Managed Projects)": self._handle_view_reply_enquiries_manager,
             "--- General Actions ---": None, # Separator
            **self._get_common_actions() # Add common actions
        }
        options = [opt for opt in actions.keys() if actions[opt] is not None] # Filter out separators for choice mapping
        display_options = list(actions.keys()) # Keep separators for display

        choice_index = base_view.display_menu("HDB Manager Menu", display_options)
        if choice_index is None: return None

        # Map display index back to action key (handling separators)
        selected_action_name = display_options[choice_index - 1]
        action_method = actions.get(selected_action_name)

        if action_method:
            # Execute the chosen action
            try:
                return action_method() # Return signal if logout/exit
            except (OperationError, IntegrityError) as e:
                base_view.display_message(str(e), error=True)
            except KeyboardInterrupt:
                 base_view.display_message("Operation cancelled.")
            except Exception as e:
                 base_view.display_message(f"An unexpected error occurred: {e}", error=True)
                 import traceback
                 traceback.print_exc()
        elif selected_action_name.startswith("---"):
             pass # Ignore separator selection
        else:
             base_view.display_message("Invalid menu option selected.", error=True)

        base_view.pause_for_user() # Pause after action/error before showing menu again
        return None # Continue showing menu unless logout/exit signal received

    # --- Helper for selecting managed project ---
    def _select_managed_project(self, action_verb="manage") -> Project | None:
         project_service: ProjectService = self._services['project']
         project_view: ProjectView = self._views['project']
         base_view: BaseView = self._views['base']

         my_projects = project_service.get_projects_by_manager(self._current_user.nric)
         if not my_projects:
             base_view.display_message("You do not manage any projects.")
             return None
         return project_view.select_project(my_projects, action_verb=action_verb)

    # --- Project Management Handlers ---

    def _handle_create_project(self):
        """Handler for creating a new project."""
        project_service: ProjectService = self._services['project']
        project_view: ProjectView = self._views['project']
        base_view: BaseView = self._views['base']

        details = project_view.prompt_create_project_details()
        if not details: return # Cancelled or error during input

        # Service handles validation (name unique, dates valid, overlap check) and saving
        new_project = project_service.create_project(
            self._current_user, details['name'], details['neighborhood'],
            details['n1'], details['p1'], details['n2'], details['p2'],
            details['od'], details['cd'], details['slot']
        )
        base_view.display_message(f"Project '{new_project.project_name}' created successfully.", info=True)


    def _handle_edit_project(self):
        """Handler for editing a managed project."""
        project_service: ProjectService = self._services['project']
        project_view: ProjectView = self._views['project']
        base_view: BaseView = self._views['base']

        project_to_edit = self._select_managed_project(action_verb="edit")
        if not project_to_edit: return # None managed or cancelled

        updates = project_view.prompt_edit_project_details(project_to_edit)
        if updates is None: # Indicates cancellation or error during input
             if updates == {}: base_view.display_message("No changes entered.", info=True)
             return

        # Service handles validation (name unique, dates valid, overlap check) and saving
        project_service.edit_project(self._current_user, project_to_edit, updates)
        base_view.display_message(f"Project '{project_to_edit.project_name}' updated successfully.", info=True)


    def _handle_delete_project(self):
        """Handler for deleting a managed project."""
        project_service: ProjectService = self._services['project']
        # project_view: ProjectView = self._views['project'] # Used via _select_managed_project
        base_view: BaseView = self._views['base']

        project_to_delete = self._select_managed_project(action_verb="delete")
        if not project_to_delete: return # None managed or cancelled

        warning_msg = (f"WARNING: Deleting project '{project_to_delete.project_name}' cannot be undone.\n"
                       f"Related applications, registrations, and enquiries will remain but may refer to a deleted project.\n"
                       f"Proceed with deletion?")
        if InputUtil.get_yes_no_input(warning_msg):
            project_service.delete_project(self._current_user, project_to_delete)
            base_view.display_message(f"Project '{project_to_delete.project_name}' deleted.", info=True)
        else:
            base_view.display_message("Deletion cancelled.", info=True)


    def _handle_toggle_visibility(self):
        """Handler for toggling project visibility."""
        project_service: ProjectService = self._services['project']
        # project_view: ProjectView = self._views['project'] # Used via _select_managed_project
        base_view: BaseView = self._views['base']

        project_to_toggle = self._select_managed_project(action_verb="toggle visibility for")
        if not project_to_toggle: return # None managed or cancelled

        # Service handles update and saving
        new_status = project_service.toggle_project_visibility(self._current_user, project_to_toggle)
        base_view.display_message(f"Project '{project_to_toggle.project_name}' visibility set to {new_status}.", info=True)


    def _handle_view_all_projects(self):
        """Handler for viewing all projects (with filters)."""
        project_service: ProjectService = self._services['project']
        project_view: ProjectView = self._views['project']
        base_view: BaseView = self._views['base']

        all_projects = project_service.get_all_projects()

        # Apply user's saved filters
        filtered_projects = project_service.filter_projects(
            all_projects, **self._user_filters
        )

        base_view.display_message(f"Current Filters: {self._user_filters or 'None'}", info=True)
        if not filtered_projects:
            base_view.display_message("No projects match your criteria.")
        else:
            base_view.display_message("Displaying All Projects:", info=True)
            for project in filtered_projects:
                # Display details from Manager's perspective
                project_view.display_project_details(project, requesting_user_role=UserRole.HDB_MANAGER)

        # Option to update filters
        if InputUtil.get_yes_no_input("Update filters?"):
            self._user_filters = project_view.prompt_project_filters(self._user_filters)
            base_view.display_message("Filters updated. View projects again to see changes.", info=True)


    def _handle_view_my_projects(self):
        """Handler for viewing only projects managed by the current manager."""
        project_service: ProjectService = self._services['project']
        project_view: ProjectView = self._views['project']
        base_view: BaseView = self._views['base']

        my_projects = project_service.get_projects_by_manager(self._current_user.nric)
        if not my_projects:
            base_view.display_message("You are not managing any projects.")
            return

        base_view.display_message("Projects You Manage:", info=True)
        for project in my_projects:
            # Display details from Manager's perspective
            project_view.display_project_details(project, requesting_user_role=UserRole.HDB_MANAGER)


    # --- Officer Registration Management Handlers ---

    def _handle_view_officer_registrations(self):
        """Handler to view registrations for a specific managed project."""
        reg_service: RegistrationService = self._services['reg']
        user_repo: IUserRepository = self._services['user']
        officer_view: OfficerView = self._views['officer']
        base_view: BaseView = self._views['base']

        project_to_view = self._select_managed_project("view officer registrations for")
        if not project_to_view: return

        registrations = reg_service.get_registrations_for_project(project_to_view.project_name)
        if not registrations:
            base_view.display_message(f"No officer registrations found for project '{project_to_view.project_name}'.")
            return

        base_view.display_message(f"Officer Registrations for '{project_to_view.project_name}':", info=True)
        # Use the select_registration view to list them (user can cancel without selecting)
        officer_view.select_registration(registrations, user_repo, action_verb="view list")


    def _select_pending_registration_for_action(self, action_verb="action") -> Registration | None:
         """Helper to select a PENDING registration from managed projects."""
         reg_service: RegistrationService = self._services['reg']
         user_repo: IUserRepository = self._services['user']
         officer_view: OfficerView = self._views['officer']
         base_view: BaseView = self._views['base']
         project_service: ProjectService = self._services['project'] # Needed for project info

         my_projects = project_service.get_projects_by_manager(self._current_user.nric)
         all_pending_regs = []
         for project in my_projects:
             pending_for_proj = reg_service.get_registrations_for_project(project.project_name, status_filter=RegistrationStatus.PENDING)
             all_pending_regs.extend(pending_for_proj)

         if not all_pending_regs:
             base_view.display_message("No pending officer registrations found for your projects.")
             return None

         # Display pending registrations and let manager select one
         return officer_view.select_registration(all_pending_regs, user_repo, action_verb=action_verb)


    def _handle_approve_officer_registration(self):
        """Handler to approve a pending officer registration."""
        reg_service: RegistrationService = self._services['reg']
        base_view: BaseView = self._views['base']
        manager_view: ManagerView = self._views['manager']
        user_repo: IUserRepository = self._services['user']
        project_service: ProjectService = self._services['project']

        registration_to_approve = self._select_pending_registration_for_action(action_verb="approve")
        if not registration_to_approve: return # None pending or cancelled

        # Show details before final confirmation
        officer = user_repo.find_user_by_nric(registration_to_approve.officer_nric)
        project = project_service.find_project_by_name(registration_to_approve.project_name)
        if not officer or not project:
             raise IntegrityError("Officer or Project not found for the selected registration.")

        manager_view.display_officer_registration_for_approval(registration_to_approve, officer, project)

        if InputUtil.get_yes_no_input(f"Confirm APPROVAL for {officer.name} for project '{project.project_name}'?"):
             # Service handles validation (slots, overlap) and saving
             reg_service.manager_approve_officer_registration(self._current_user, registration_to_approve)
             base_view.display_message(f"Officer registration for {officer.name} approved.", info=True)
        else:
             base_view.display_message("Approval cancelled.")


    def _handle_reject_officer_registration(self):
        """Handler to reject a pending officer registration."""
        reg_service: RegistrationService = self._services['reg']
        base_view: BaseView = self._views['base']
        manager_view: ManagerView = self._views['manager']
        user_repo: IUserRepository = self._services['user']
        project_service: ProjectService = self._services['project']


        registration_to_reject = self._select_pending_registration_for_action(action_verb="reject")
        if not registration_to_reject: return # None pending or cancelled

        # Show details before final confirmation
        officer = user_repo.find_user_by_nric(registration_to_reject.officer_nric)
        project = project_service.find_project_by_name(registration_to_reject.project_name)
        if not officer or not project:
             raise IntegrityError("Officer or Project not found for the selected registration.")

        manager_view.display_officer_registration_for_approval(registration_to_reject, officer, project)


        if InputUtil.get_yes_no_input(f"Confirm REJECTION for {officer.name} for project '{project.project_name}'?"):
             # Service handles update and saving
             reg_service.manager_reject_officer_registration(self._current_user, registration_to_reject)
             base_view.display_message(f"Officer registration for {officer.name} rejected.", info=True)
        else:
             base_view.display_message("Rejection cancelled.")


    # --- Application Management Handlers ---

    def _handle_view_applications(self):
        """Handler to view applications for a specific managed project."""
        app_service: ApplicationService = self._services['app']
        user_repo: IUserRepository = self._services['user']
        app_view: ApplicationView = self._views['app']
        base_view: BaseView = self._views['base']

        project_to_view = self._select_managed_project("view applications for")
        if not project_to_view: return

        applications = app_service.get_applications_for_project(project_to_view.project_name)
        if not applications:
            base_view.display_message(f"No applications found for project '{project_to_view.project_name}'.")
            return

        base_view.display_message(f"Applications for '{project_to_view.project_name}':", info=True)
        # Use the select_application view to list them
        app_view.select_application(applications, user_repo, action_verb="view list")


    def _select_pending_application_for_action(self, action_verb="action") -> Application | None:
         """Helper to select a PENDING application (without withdrawal request) from managed projects."""
         app_service: ApplicationService = self._services['app']
         user_repo: IUserRepository = self._services['user']
         app_view: ApplicationView = self._views['app']
         base_view: BaseView = self._views['base']
         project_service: ProjectService = self._services['project']

         my_projects = project_service.get_projects_by_manager(self._current_user.nric)
         all_pending_apps = []
         for project in my_projects:
             apps = app_service.get_applications_for_project(project.project_name)
             # Filter for PENDING status AND no withdrawal request
             all_pending_apps.extend([app for app in apps if app.status == ApplicationStatus.PENDING and not app.request_withdrawal])

         if not all_pending_apps:
             base_view.display_message("No pending applications (without withdrawal requests) found for your projects.")
             return None

         # Display pending applications and let manager select one
         return app_view.select_application(all_pending_apps, user_repo, action_verb=action_verb)


    def _handle_approve_application(self):
        """Handler to approve a pending application."""
        app_service: ApplicationService = self._services['app']
        base_view: BaseView = self._views['base']
        manager_view: ManagerView = self._views['manager']
        user_repo: IUserRepository = self._services['user']
        project_service: ProjectService = self._services['project']

        application_to_approve = self._select_pending_application_for_action(action_verb="approve")
        if not application_to_approve: return # None pending or cancelled

        # Show details before final confirmation
        applicant = user_repo.find_user_by_nric(application_to_approve.applicant_nric)
        project = project_service.find_project_by_name(application_to_approve.project_name)
        if not applicant or not project:
             raise IntegrityError("Applicant or Project not found for the selected application.")

        manager_view.display_application_for_approval(application_to_approve, applicant, project)

        if InputUtil.get_yes_no_input(f"Confirm APPROVAL for {applicant.name}'s application for project '{project.project_name}'?"):
             # Service handles validation (units available) and saving
             app_service.manager_approve_application(self._current_user, application_to_approve)
             # Service might auto-reject if no units, message will come from exception
             base_view.display_message(f"Application for {applicant.name} approved (Status: {application_to_approve.status.value}).", info=True)
        else:
             base_view.display_message("Approval cancelled.")


    def _handle_reject_application(self):
        """Handler to reject a pending application."""
        app_service: ApplicationService = self._services['app']
        base_view: BaseView = self._views['base']
        manager_view: ManagerView = self._views['manager']
        user_repo: IUserRepository = self._services['user']
        project_service: ProjectService = self._services['project']

        application_to_reject = self._select_pending_application_for_action(action_verb="reject")
        if not application_to_reject: return # None pending or cancelled

        # Show details before final confirmation
        applicant = user_repo.find_user_by_nric(application_to_reject.applicant_nric)
        project = project_service.find_project_by_name(application_to_reject.project_name)
        if not applicant or not project:
             raise IntegrityError("Applicant or Project not found for the selected application.")

        manager_view.display_application_for_approval(application_to_reject, applicant, project)

        if InputUtil.get_yes_no_input(f"Confirm REJECTION for {applicant.name}'s application for project '{project.project_name}'?"):
             # Service handles update and saving
             app_service.manager_reject_application(self._current_user, application_to_reject)
             base_view.display_message(f"Application for {applicant.name} rejected (Status: UNSUCCESSFUL).", info=True)
        else:
             base_view.display_message("Rejection cancelled.")


    def _select_application_with_withdrawal_request(self, action_verb="action") -> Application | None:
         """Helper to select an application with a pending withdrawal request from managed projects."""
         app_service: ApplicationService = self._services['app']
         user_repo: IUserRepository = self._services['user']
         app_view: ApplicationView = self._views['app']
         base_view: BaseView = self._views['base']
         project_service: ProjectService = self._services['project']

         my_projects = project_service.get_projects_by_manager(self._current_user.nric)
         apps_with_request = []
         for project in my_projects:
             apps = app_service.get_applications_for_project(project.project_name)
             apps_with_request.extend([app for app in apps if app.request_withdrawal])

         if not apps_with_request:
             base_view.display_message("No applications with pending withdrawal requests found for your projects.")
             return None

         # Display these applications and let manager select one
         return app_view.select_application(apps_with_request, user_repo, action_verb=action_verb)


    def _handle_approve_withdrawal(self):
        """Handler to approve a pending withdrawal request."""
        app_service: ApplicationService = self._services['app']
        base_view: BaseView = self._views['base']
        manager_view: ManagerView = self._views['manager']
        user_repo: IUserRepository = self._services['user']
        project_service: ProjectService = self._services['project']

        application_to_action = self._select_application_with_withdrawal_request(action_verb="approve withdrawal for")
        if not application_to_action: return # None pending or cancelled

        # Show details before final confirmation
        applicant = user_repo.find_user_by_nric(application_to_action.applicant_nric)
        project = project_service.find_project_by_name(application_to_action.project_name)
        if not applicant or not project:
             raise IntegrityError("Applicant or Project not found for the selected application.")

        manager_view.display_withdrawal_request_for_approval(application_to_action, applicant, project)

        if InputUtil.get_yes_no_input(f"Confirm APPROVAL of withdrawal request for {applicant.name} (Project: {project.project_name})?"):
             # Service handles status update, flag clearing, unit count adjustment, and saving
             app_service.manager_approve_withdrawal(self._current_user, application_to_action)
             base_view.display_message(f"Withdrawal request for {applicant.name} approved. Application status set to UNSUCCESSFUL.", info=True)
        else:
             base_view.display_message("Withdrawal approval cancelled.")


    def _handle_reject_withdrawal(self):
        """Handler to reject a pending withdrawal request."""
        app_service: ApplicationService = self._services['app']
        base_view: BaseView = self._views['base']
        manager_view: ManagerView = self._views['manager']
        user_repo: IUserRepository = self._services['user']
        project_service: ProjectService = self._services['project']

        application_to_action = self._select_application_with_withdrawal_request(action_verb="reject withdrawal for")
        if not application_to_action: return # None pending or cancelled

        # Show details before final confirmation
        applicant = user_repo.find_user_by_nric(application_to_action.applicant_nric)
        project = project_service.find_project_by_name(application_to_action.project_name)
        if not applicant or not project:
             raise IntegrityError("Applicant or Project not found for the selected application.")

        manager_view.display_withdrawal_request_for_approval(application_to_action, applicant, project)

        if InputUtil.get_yes_no_input(f"Confirm REJECTION of withdrawal request for {applicant.name} (Project: {project.project_name})?"):
             # Service handles flag clearing and saving
             app_service.manager_reject_withdrawal(self._current_user, application_to_action)
             base_view.display_message(f"Withdrawal request for {applicant.name} rejected. Application status remains '{application_to_action.status.value}'.", info=True)
        else:
             base_view.display_message("Withdrawal rejection cancelled.")


    # --- Reporting & Enquiry Handlers ---

    def _handle_generate_booking_report(self):
        """Handler to generate the booking report with filters."""
        report_service: ReportService = self._services['report']
        report_view: ReportView = self._views['report']

        filters = report_view.prompt_report_filters()
        report_data = report_service.generate_booking_report_data(**filters)
        headers = ["NRIC", "Applicant Name", "Age", "Marital Status", "Flat Type", "Project Name", "Neighborhood"]
        report_view.display_report("Booking Report", report_data, headers)


    def _handle_view_all_enquiries(self):
        """Handler for viewing all enquiries in the system."""
        enq_service: EnquiryService = self._services['enq']
        user_repo: IUserRepository = self._services['user']
        project_service: ProjectService = self._services['project'] # To get project names
        enq_view: EnquiryView = self._views['enq']
        base_view: BaseView = self._views['base']

        all_enquiries = enq_service.get_all_enquiries()

        if not all_enquiries:
            base_view.display_message("There are no enquiries in the system.")
            return

        base_view.display_message("All System Enquiries:", info=True)
        for enquiry in all_enquiries:
            applicant = user_repo.find_user_by_nric(enquiry.applicant_nric)
            applicant_name = applicant.name if applicant else "Unknown Applicant"
            project = project_service.find_project_by_name(enquiry.project_name)
            project_name = project.project_name if project else f"Unknown/Deleted Project ({enquiry.project_name})"
            # Display full details
            enq_view.display_enquiry_details(enquiry, project_name, applicant_name)


    def _get_enquiries_for_managed_projects(self) -> list[tuple[Enquiry, str]]:
         """Helper to get enquiries for projects the manager handles."""
         enq_service: EnquiryService = self._services['enq']
         project_service: ProjectService = self._services['project']
         user_repo: IUserRepository = self._services['user']

         managed_project_names = {p.project_name for p in project_service.get_projects_by_manager(self._current_user.nric)}
         relevant_enquiries_data = []
         if not managed_project_names:
             return relevant_enquiries_data

         all_enquiries = enq_service.get_all_enquiries()
         for enquiry in all_enquiries:
             if enquiry.project_name in managed_project_names:
                 applicant = user_repo.find_user_by_nric(enquiry.applicant_nric)
                 applicant_name = applicant.name if applicant else "Unknown Applicant"
                 relevant_enquiries_data.append((enquiry, applicant_name))
         return relevant_enquiries_data


    def _handle_view_reply_enquiries_manager(self):
        """Handler for viewing and replying to enquiries for managed projects."""
        enq_service: EnquiryService = self._services['enq']
        enq_view: EnquiryView = self._views['enq']
        base_view: BaseView = self._views['base']
        project_service: ProjectService = self._services['project'] # Needed for project name

        relevant_enquiries_data = self._get_enquiries_for_managed_projects()

        if not relevant_enquiries_data:
            base_view.display_message("No enquiries found for the projects you manage.")
            return

        unreplied_enquiries = [e for e, name in relevant_enquiries_data if not e.is_replied()]

        base_view.display_message("Enquiries for Projects You Manage:", info=True)
        for enquiry, applicant_name in relevant_enquiries_data:
             project = project_service.find_project_by_name(enquiry.project_name)
             project_name = project.project_name if project else f"Unknown/Deleted Project ({enquiry.project_name})"
             enq_view.display_enquiry_details(enquiry, project_name, applicant_name)


        if not unreplied_enquiries:
            base_view.display_message("\nNo unreplied enquiries requiring action.")
            return

        # Option to reply
        if InputUtil.get_yes_no_input("\nReply to an unreplied enquiry?"):
            enquiry_to_reply = enq_view.select_enquiry(unreplied_enquiries, action_verb="reply to")
            if enquiry_to_reply:
                reply_text = enq_view.prompt_reply_text()
                if reply_text:
                    # Service handles permission check and saving
                    enq_service.reply_to_enquiry(self._current_user, enquiry_to_reply, reply_text)
                    base_view.display_message(f"Reply submitted successfully for Enquiry ID {enquiry_to_reply.enquiry_id}.", info=True)


# ==============================================================================
# == MAIN APPLICATION CONTROLLER ==
# ==============================================================================

class ApplicationController:
    """Main controller orchestrating the application lifecycle."""
    def __init__(self):
        self._services = {}
        self._views = {}
        self._current_user: User | None = None
        self._role_controller: BaseRoleController | None = None

        try:
            self._initialize_dependencies()
        except (DataLoadError, DataSaveError, IntegrityError) as e:
            # Use BaseView directly for initialization errors as views dict might not be ready
            BaseView().display_message(f"CRITICAL ERROR during initialization: {e}. Cannot start application.", error=True)
            exit(1)
        except Exception as e:
            BaseView().display_message(f"UNEXPECTED CRITICAL ERROR during initialization: {e}. Cannot start application.", error=True)
            import traceback
            traceback.print_exc()
            exit(1)

    def _initialize_dependencies(self):
        """Sets up repositories, services, and views."""
        # Repositories (using specific classes and facade)
        applicant_repo = ApplicantRepository()
        officer_repo = OfficerRepository()
        manager_repo = ManagerRepository()
        user_repo_facade = UserRepositoryFacade(applicant_repo, officer_repo, manager_repo)
        project_repo = ProjectRepository()
        app_repo = ApplicationRepository()
        reg_repo = RegistrationRepository()
        enq_repo = EnquiryRepository()

        # Services (inject repository dependencies)
        self._services['auth'] = AuthService(user_repo_facade)
        # ProjectService needs reg_repo for overlap checks
        self._services['project'] = ProjectService(project_repo, reg_repo)
        # RegistrationService needs project_service and app_repo for checks
        self._services['reg'] = RegistrationService(reg_repo, self._services['project'], app_repo)
        # ApplicationService needs project_service, reg_service, user_repo
        self._services['app'] = ApplicationService(app_repo, self._services['project'], self._services['reg'], user_repo_facade)
        # EnquiryService needs project_service, user_repo, app_repo
        self._services['enq'] = EnquiryService(enq_repo, self._services['project'], user_repo_facade, app_repo)
        # ReportService needs app_repo, project_service, user_repo
        self._services['report'] = ReportService(app_repo, self._services['project'], user_repo_facade)

        # Add repositories to services dict if controllers need direct access (try to avoid)
        self._services['user'] = user_repo_facade # Needed by views/controllers sometimes
        self._services['project_repo'] = project_repo # If needed directly
        # ... add others if absolutely necessary

        # Views
        self._views['base'] = BaseView()
        self._views['auth'] = AuthView()
        self._views['project'] = ProjectView()
        self._views['app'] = ApplicationView()
        self._views['enq'] = EnquiryView()
        self._views['officer'] = OfficerView()
        self._views['manager'] = ManagerView() # Use the specific ManagerView
        self._views['report'] = ReportView()

    def run(self):
        """Main application loop."""
        base_view = self._views['base']
        while True:
            if not self._current_user:
                if not self._handle_login(): # Login prompts until success or user quits
                    break # Exit if login fails and user doesn't retry
            else:
                if self._role_controller:
                    signal = self._role_controller.run_menu() # Run the role-specific menu
                    if signal == "LOGOUT":
                        self._handle_logout()
                    elif signal == "EXIT":
                        self._shutdown()
                        break # Exit main loop
                else:
                    # Should not happen if login sets controller correctly
                    base_view.display_message("Error: No role controller active. Logging out.", error=True)
                    self._handle_logout()

    def _handle_login(self) -> bool:
        """Handles the login process. Returns True if login successful, False if user quits."""
        auth_service: AuthService = self._services['auth']
        auth_view: AuthView = self._views['auth']
        base_view: BaseView = self._views['base']

        base_view.display_message("Welcome to the BTO Management System")
        while True: # Loop until successful login or quit
            try:
                nric, password = auth_view.prompt_login()
                self._current_user = auth_service.login(nric, password)
                role = auth_service.get_user_role(self._current_user)
                base_view.display_message(f"Login successful. Welcome, {self._current_user.name} ({role.value})!", info=True)

                # Instantiate the correct controller based on role
                if role == UserRole.HDB_MANAGER:
                    self._role_controller = ManagerController(self._current_user, self._services, self._views)
                elif role == UserRole.HDB_OFFICER:
                    self._role_controller = OfficerController(self._current_user, self._services, self._views)
                elif role == UserRole.APPLICANT:
                    self._role_controller = ApplicantController(self._current_user, self._services, self._views)
                else:
                    # Should not happen with defined roles
                    base_view.display_message(f"Error: Unknown user role '{role}'. Logging out.", error=True)
                    self._current_user = None
                    self._role_controller = None
                    return False # Indicate login failure

                return True # Login successful

            except OperationError as e:
                base_view.display_message(str(e), error=True)
                if not InputUtil.get_yes_no_input("Login failed. Try again?"):
                    self._shutdown()
                    return False # User chose to quit
            except KeyboardInterrupt:
                 self._shutdown()
                 return False # User quit via Ctrl+C

    def _handle_logout(self):
        """Handles the logout process."""
        base_view = self._views['base']
        if self._current_user:
            base_view.display_message(f"Logging out user {self._current_user.name}.", info=True)
        self._current_user = None
        self._role_controller = None
        # Clear filters on logout? Optional.
        # if self._role_controller: self._role_controller._user_filters = {}


    def _save_all_data(self):
        """Attempts to save data from all repositories."""
        print("\nAttempting to save all data...")
        saved_count = 0
        error_count = 0
        # Iterate through known repository instances (could be improved with registration)
        repos_to_save = [
             self._services['user']._applicant_repo, # Access via facade's internal refs
             self._services['user']._officer_repo,
             self._services['user']._manager_repo,
             self._services['project_repo'], # Assumes project repo is in services
             self._services['app']._app_repo, # Access via service's internal refs
             self._services['reg']._reg_repo,
             self._services['enq']._enq_repo
        ]
        for repo in repos_to_save:
             if isinstance(repo, IBaseRepository):
                 try:
                     repo.save_all()
                     print(f" - Saved data for {repo._MODEL_CLASS.__name__} to {repo._FILE_PATH.value}")
                     saved_count += 1
                 except (DataSaveError, Exception) as e:
                     print(f"ERROR: Failed to save data for {repo._MODEL_CLASS.__name__}: {e}")
                     error_count += 1
             else:
                  print(f"Warning: Cannot save data for object of type {type(repo)}, not a known repository.")
                  error_count += 1

        if error_count == 0:
             print("All data saved successfully.")
        else:
             print(f"Data saving completed with {error_count} error(s).")


    def _shutdown(self):
        """Handles application shutdown, including saving data."""
        base_view = self._views['base']
        base_view.display_message("Exiting BTO Management System...")
        try:
            self._save_all_data()
        except Exception as e:
             base_view.display_message(f"An error occurred during final data save: {e}", error=True)
        base_view.display_message("Goodbye!")

# ==============================================================================
# == APPLICATION ENTRY POINT ==
# ==============================================================================

if __name__ == "__main__":
    app = ApplicationController()
    app.run()