# utils/helpers.py
import os
from datetime import datetime
from utils.exceptions import DataLoadError, DataSaveError

DATE_FORMAT = "%Y-%m-%d"
DATA_DIR = "data" # Define the data directory relative to the project root

# --- File Paths ---
APPLICANT_CSV = os.path.join(DATA_DIR, 'ApplicantList.csv')
OFFICER_CSV = os.path.join(DATA_DIR, 'OfficerList.csv')
MANAGER_CSV = os.path.join(DATA_DIR, 'ManagerList.csv')
PROJECT_CSV = os.path.join(DATA_DIR, 'ProjectList.csv')
APPLICATION_CSV = os.path.join(DATA_DIR, 'ApplicationData.csv')
REGISTRATION_CSV = os.path.join(DATA_DIR, 'RegistrationData.csv')
ENQUIRY_CSV = os.path.join(DATA_DIR, 'EnquiryData.csv')

# --- Date Handling ---
def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, DATE_FORMAT).date()
    except ValueError:
        print(f"Warning: Invalid date format encountered: {date_str}. Expected {DATE_FORMAT}.")
        return None # Or raise specific error if needed

def format_date(date_obj):
    if date_obj is None:
        return ""
    try:
        return date_obj.strftime(DATE_FORMAT)
    except AttributeError:
        print(f"Warning: Invalid object passed to format_date: {date_obj}")
        return ""

def dates_overlap(start1, end1, start2, end2):
    """Checks if two date ranges overlap (inclusive)."""
    if not all([start1, end1, start2, end2]):
        return False
    # Ensure start <= end for both ranges
    start1, end1 = min(start1, end1), max(start1, end1)
    start2, end2 = min(start2, end2), max(start2, end2)
    # Check for non-overlap condition
    return not (end1 < start2 or start1 > end2)

# --- Validation ---
def validate_nric(nric):
    """Validates the NRIC format (S/T + 7 digits + Letter)."""
    if not isinstance(nric, str) or len(nric) != 9:
        return False
    if nric[0].upper() not in ('S', 'T'):
        return False
    if not nric[1:8].isdigit():
        return False
    if not nric[8].isalpha():
        return False
    return True

def is_valid_int(value):
    """Checks if a value can be safely converted to an integer."""
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False

# --- Input Helpers ---
def get_valid_integer_input(prompt, min_val=None, max_val=None):
    """Gets integer input within optional bounds."""
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

def get_valid_date_input(prompt):
    """Gets date input in the correct format."""
    while True:
        date_str = input(f"{prompt} ({DATE_FORMAT}): ").strip()
        parsed_date = parse_date(date_str)
        if parsed_date:
            return parsed_date
        else:
            print(f"ERROR: Invalid date format. Please use {DATE_FORMAT}.")

def get_non_empty_input(prompt):
    """Gets input that is not empty or just whitespace."""
    while True:
        value = input(f"{prompt}: ").strip()
        if value:
            return value
        else:
            print("ERROR: Input cannot be empty.")

def get_yes_no_input(prompt):
    """Gets a 'y' or 'n' input, returning True for 'y'."""
    while True:
        choice = input(f"{prompt} (y/n): ").strip().lower()
        if choice == 'y':
            return True
        elif choice == 'n':
            return False
        print("ERROR: Please enter 'y' or 'n'.")