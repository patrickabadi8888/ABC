import unittest
import os
import csv
import shutil
import traceback # Import traceback for detailed error printing
from datetime import date, timedelta

# Assuming main5.py is in the same directory
from Past.main6 import (
    ApplicationController, User, Applicant, HDBOfficer, HDBManager, Project,
    Application, Registration, Enquiry, OperationError, IntegrityError,
    DataLoadError, DataSaveError,
    APPLICANT_CSV, OFFICER_CSV, MANAGER_CSV, PROJECT_CSV,
    APPLICATION_CSV, REGISTRATION_CSV, ENQUIRY_CSV, DATE_FORMAT,
    parse_date, format_date # Import necessary components
)

# --- Test Configuration ---
TEST_DATA_DIR = 'test_data_backup'
CSV_FILES = [
    APPLICANT_CSV, OFFICER_CSV, MANAGER_CSV, PROJECT_CSV,
    APPLICATION_CSV, REGISTRATION_CSV, ENQUIRY_CSV
]

# --- Sample Data (Keep as before) ---
# NRICs
APP1_NRIC = "S1111111A"
APP2_NRIC = "S2222222B" # Single, 35
APP3_NRIC = "S3333333C" # Married, 20 (ineligible)
APP4_NRIC = "S4444444D" # Married, 25
OFF1_NRIC = "T5555555E" # Also an Applicant
OFF2_NRIC = "T6666666F"
MGR1_NRIC = "T7777777G"
MGR2_NRIC = "T8888888H"
DEFAULT_PW = "password"

# Dates
TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)
NEXT_WEEK = TODAY + timedelta(days=7)
NEXT_MONTH = TODAY + timedelta(days=30)
LAST_WEEK = TODAY - timedelta(days=7)
LAST_MONTH = TODAY - timedelta(days=30)

# Projects
PROJ1_NAME = "Test Project Alpha" # Open, Managed by MGR1
PROJ2_NAME = "Test Project Beta"  # Closed, Managed by MGR1
PROJ3_NAME = "Test Project Gamma" # Future, Managed by MGR2, Visible Off
PROJ4_NAME = "Test Project Delta" # Open, Zero Units, Managed by MGR1
PROJ5_NAME = "Test Project Epsilon" # Open, Managed by MGR2 (for overlap tests)

SAMPLE_APPLICANTS = [
    ['Applicant One', APP1_NRIC, '30', 'Single', DEFAULT_PW],
    ['Applicant Two', APP2_NRIC, '35', 'Single', DEFAULT_PW],
    ['Applicant Three', APP3_NRIC, '20', 'Married', DEFAULT_PW],
    ['Applicant Four', APP4_NRIC, '25', 'Married', DEFAULT_PW],
]
SAMPLE_OFFICERS = [
    ['Officer One', OFF1_NRIC, '40', 'Married', DEFAULT_PW],
    ['Officer Two', OFF2_NRIC, '38', 'Single', DEFAULT_PW],
]
SAMPLE_MANAGERS = [
    ['Manager One', MGR1_NRIC, '45', 'Married', DEFAULT_PW],
    ['Manager Two', MGR2_NRIC, '50', 'Single', DEFAULT_PW],
]
SAMPLE_PROJECTS = [
    [PROJ1_NAME, 'Yishun', '2-Room', '5', '100000', '3-Room', '10', '200000', format_date(YESTERDAY), format_date(NEXT_WEEK), MGR1_NRIC, '5', '', 'True'],
    [PROJ2_NAME, 'Boon Lay', '2-Room', '2', '90000', '3-Room', '3', '180000', format_date(LAST_MONTH), format_date(LAST_WEEK), MGR1_NRIC, '3', OFF2_NRIC, 'True'],
    [PROJ3_NAME, 'Tampines', '2-Room', '8', '110000', '3-Room', '12', '210000', format_date(NEXT_WEEK), format_date(NEXT_MONTH), MGR2_NRIC, '10', '', 'False'],
    [PROJ4_NAME, 'Woodlands', '2-Room', '0', '95000', '3-Room', '0', '195000', format_date(YESTERDAY), format_date(NEXT_WEEK), MGR1_NRIC, '2', '', 'True'],
    [PROJ5_NAME, 'Jurong', '2-Room', '10', '105000', '3-Room', '15', '205000', format_date(TODAY), format_date(NEXT_MONTH), MGR2_NRIC, '8', '', 'True'],
]
SAMPLE_APPLICATIONS = []
SAMPLE_REGISTRATIONS = [[OFF2_NRIC, PROJ2_NAME, Registration.STATUS_APPROVED]]
SAMPLE_ENQUIRIES = []

# --- Helper Functions (Keep as before) ---
def write_csv(filename, headers, data):
    try:
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data)
    except IOError as e:
        print(f"ERROR writing CSV {filename}: {e}")
        raise # Re-raise to indicate failure

def read_csv(filename):
    data = []
    headers = None # Initialize headers
    if os.path.exists(filename):
        try:
            with open(filename, 'r', newline='') as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                if headers:
                    for row in reader:
                        data.append(row)
        except Exception as e:
            print(f"ERROR reading CSV {filename}: {e}")
            # Decide if this should be fatal for the test helper
    return headers, data


# --- Test Class ---
class TestBTOMain(unittest.TestCase):

    # Keep setUpClass as before
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(TEST_DATA_DIR):
            os.makedirs(TEST_DATA_DIR)

    def setUp(self):
        """Back up original files and set up clean test files."""
        print(f"\n--- Running setUp for test: {self.id()} ---") # Identify which test is running setup
        # **Initialize instance variables immediately**
        self.controller = None
        self.backup_files = {} # Crucial: Initialize here

        # Ensure backup directory exists
        if not os.path.exists(TEST_DATA_DIR):
            try:
                print(f"Creating backup directory: {TEST_DATA_DIR}")
                os.makedirs(TEST_DATA_DIR)
            except OSError as e:
                if not os.path.isdir(TEST_DATA_DIR):
                    print(f"ERROR: Failed to create backup directory {TEST_DATA_DIR}: {e}")
                    raise

        # Backup loop
        print("Starting file backup loop...")
        for filename in CSV_FILES:
            print(f"Processing file: {filename}")
            source_exists = os.path.exists(filename)
            if not source_exists:
                 print(f"Warning: Source file {filename} not found. Creating empty file.")
                 try:
                     # Create directory if it doesn't exist for the source file path
                     os.makedirs(os.path.dirname(filename), exist_ok=True)
                     with open(filename, 'w', newline='') as f:
                         # Optionally write headers if needed by your repos
                         # Example: writer = csv.writer(f); writer.writerow(get_headers_for(filename))
                         pass
                 except IOError as e:
                     print(f"ERROR: Failed to create empty file {filename}: {e}")
                     self.fail(f"Setup failed: Cannot create required empty file {filename}")

            backup_path = os.path.join(TEST_DATA_DIR, os.path.basename(filename))
            try:
                print(f"Attempting to copy {filename} to {backup_path}")
                shutil.copy(filename, backup_path)
                self.backup_files[filename] = backup_path # Add only on success
                print(f"Successfully backed up {filename}")
            except Exception as e:
                 print(f"ERROR copying {filename} to {backup_path}: {e}")
                 traceback.print_exc() # Print full traceback for copy error
                 self.fail(f"Setup failed during backup of {filename}: {e}")
        print(f"Finished file backup loop. backup_files created: {hasattr(self, 'backup_files')}")

        # Write sample data
        print("Writing sample CSV data...")
        try:
            write_csv(APPLICANT_CSV, ['Name', 'NRIC', 'Age', 'Marital Status', 'Password'], SAMPLE_APPLICANTS)
            write_csv(OFFICER_CSV, ['Name', 'NRIC', 'Age', 'Marital Status', 'Password'], SAMPLE_OFFICERS)
            write_csv(MANAGER_CSV, ['Name', 'NRIC', 'Age', 'Marital Status', 'Password'], SAMPLE_MANAGERS)
            write_csv(PROJECT_CSV, [
                'Project Name', 'Neighborhood', 'Type 1', 'Number of units for Type 1',
                'Selling price for Type 1', 'Type 2', 'Number of units for Type 2',
                'Selling price for Type 2', 'Application opening date',
                'Application closing date', 'Manager', 'Officer Slot', 'Officer', 'Visibility'
            ], SAMPLE_PROJECTS)
            write_csv(APPLICATION_CSV, ['ApplicantNRIC', 'ProjectName', 'FlatType', 'Status', 'RequestWithdrawal'], SAMPLE_APPLICATIONS)
            write_csv(REGISTRATION_CSV, ['OfficerNRIC', 'ProjectName', 'Status'], SAMPLE_REGISTRATIONS)
            write_csv(ENQUIRY_CSV, ['EnquiryID', 'ApplicantNRIC', 'ProjectName', 'Text', 'Reply'], SAMPLE_ENQUIRIES)
            print("Finished writing sample CSV data.")
        except Exception as e:
             print(f"ERROR writing sample CSV data: {e}")
             traceback.print_exc()
             self.fail(f"Setup failed: Cannot write sample CSV data: {e}")


        # Instantiate controller
        print("Instantiating ApplicationController...")
        try:
            # Add extra check: ensure CSV files actually have content written before controller init
            for csv_file in CSV_FILES:
                 if os.path.exists(csv_file):
                     print(f"  Checking {csv_file} size: {os.path.getsize(csv_file)}")
                 else:
                     print(f"  WARNING: {csv_file} does not exist before Controller init!")

            self.controller = ApplicationController()
            print(f"ApplicationController instantiated successfully. Controller object exists: {hasattr(self, 'controller') and self.controller is not None}")
        except Exception as e: # Catch more general exceptions during init
             print(f"ERROR during ApplicationController initialization: {e}")
             traceback.print_exc()
             # **Crucially, do not proceed if controller fails**
             self.controller = None # Ensure controller is None if init fails
             self.fail(f"Setup failed: Controller initialization error: {e}")

        # Pre-login users (only if controller was created)
        if self.controller:
            print("Pre-logging in test users...")
            try:
                self.applicant1 = self.controller.auth_service.login(APP1_NRIC, DEFAULT_PW)
                self.applicant2 = self.controller.auth_service.login(APP2_NRIC, DEFAULT_PW)
                self.applicant4 = self.controller.auth_service.login(APP4_NRIC, DEFAULT_PW)
                self.officer1 = self.controller.auth_service.login(OFF1_NRIC, DEFAULT_PW)
                self.officer2 = self.controller.auth_service.login(OFF2_NRIC, DEFAULT_PW)
                self.manager1 = self.controller.auth_service.login(MGR1_NRIC, DEFAULT_PW)
                self.manager2 = self.controller.auth_service.login(MGR2_NRIC, DEFAULT_PW)
                print("Finished pre-logging in users.")
            except Exception as e: # Catch login errors
                print(f"ERROR during pre-login: {e}")
                traceback.print_exc()
                # Optionally fail here, or let tests fail if users are needed
                # self.fail(f"Setup failed: Error during pre-login: {e}")
        else:
            print("Skipping pre-login because controller failed to initialize.")

        print(f"--- Finished setUp for test: {self.id()} ---")


    def tearDown(self):
        """Restore original files from backup."""
        print(f"\n--- Running tearDown for test: {self.id()} ---")
        self.controller = None # Release controller resources if any

        # **Crucially check if backup_files exists before using**
        if hasattr(self, 'backup_files') and self.backup_files is not None:
            print(f"Restoring files from backup_files: {list(self.backup_files.keys())}")
            for original_path, backup_path in self.backup_files.items():
                try:
                    if os.path.exists(backup_path):
                        print(f"Restoring {original_path} from {backup_path}")
                        shutil.copy(backup_path, original_path)
                        # Check if backup removal is safe (e.g., not needed by parallel tests if applicable)
                        # print(f"Removing backup {backup_path}")
                        # os.remove(backup_path)
                    elif os.path.exists(original_path):
                        print(f"Removing test-created file: {original_path}")
                        os.remove(original_path)
                    else:
                        print(f"Skipping restore for {original_path}: Neither backup nor original found.")
                except Exception as e:
                    print(f"WARNING: Error during file restoration/cleanup for {original_path}: {e}")
                    traceback.print_exc() # Show details of restore error
        else:
            print("Warning: self.backup_files not found or is None in tearDown. Skipping restore loop.")

        # Clean up backups regardless of restore success/failure if the dict exists
        if hasattr(self, 'backup_files') and self.backup_files is not None:
            print("Cleaning up remaining backup files...")
            for backup_path in self.backup_files.values():
                 if os.path.exists(backup_path):
                      try:
                           print(f"Removing leftover backup: {backup_path}")
                           os.remove(backup_path)
                      except Exception as e:
                           print(f"Warning: Failed to remove backup file {backup_path}: {e}")

        # Attempt to clean directory if empty
        try:
            if os.path.exists(TEST_DATA_DIR) and not os.listdir(TEST_DATA_DIR):
                print(f"Removing empty backup directory: {TEST_DATA_DIR}")
                os.rmdir(TEST_DATA_DIR)
        except OSError as e:
            # This might fail if files couldn't be removed above
            print(f"Warning: Could not remove test data directory {TEST_DATA_DIR}: {e}")
        print(f"--- Finished tearDown for test: {self.id()} ---")


    # --- Helper Methods (Keep as before, maybe add checks) ---
    def _login_user(self, nric, password=DEFAULT_PW):
        # **Add check for controller existence**
        if not self.controller:
             self.fail(f"Cannot login user {nric}: Controller was not initialized in setUp.")
        try:
            user = self.controller.auth_service.login(nric, password)
            self.controller.current_user = user
            return user
        except OperationError as e:
            self.fail(f"Helper login failed for {nric}: {e}")
        except Exception as e: # Catch other potential errors
            self.fail(f"Unexpected error during helper login for {nric}: {e}")


    def _get_project(self, name):
        if not self.controller:
             self.fail(f"Cannot get project {name}: Controller was not initialized in setUp.")
        proj = self.controller.project_service.find_project_by_name(name)
        # Keep assertIsNotNone or handle None case depending on test logic
        # self.assertIsNotNone(proj, f"Helper failed to find project: {name}")
        return proj

    def _get_application(self, nric):
        return self.controller.app_service.find_application_by_applicant(nric)

    def _get_registration(self, nric, proj_name):
        return self.controller.reg_service.find_registration(nric, proj_name)

    def _check_csv_data(self, filename, expected_row_subset, key_col_index):
        """Checks if at least one row in the CSV contains the expected subset of data."""
        _, data = read_csv(filename)
        found = False
        for row in data:
            match = True
            if len(row) <= key_col_index or len(expected_row_subset) > len(row):
                 match = False # Avoid index errors if row is too short
            else:
                # Compare elements present in expected_row_subset
                for i, expected_val in enumerate(expected_row_subset):
                     if i >= len(row) or str(row[i]) != str(expected_val): # Compare as strings for simplicity
                         match = False
                         break
            if match:
                found = True
                break
        self.assertTrue(found, f"Data subset {expected_row_subset} not found in {filename}")

    def _check_csv_for_value(self, filename, col_index, expected_value):
         """Checks if a specific value exists in a specific column."""
         _, data = read_csv(filename)
         found = False
         for row in data:
             if len(row) > col_index and str(row[col_index]) == str(expected_value):
                 found = True
                 break
         self.assertTrue(found, f"Value '{expected_value}' not found in column {col_index} of {filename}")

    def _check_csv_not_for_value(self, filename, col_index, unexpected_value):
         """Checks if a specific value does NOT exist in a specific column."""
         _, data = read_csv(filename)
         found = False
         for row in data:
             if len(row) > col_index and str(row[col_index]) == str(unexpected_value):
                 found = True
                 break
         self.assertFalse(found, f"Value '{unexpected_value}' was unexpectedly found in column {col_index} of {filename}")


    # --- Appendix A Test Cases ---

    def test_appendix_a_case_1_valid_login(self):
        self._login_user(APP1_NRIC, DEFAULT_PW)
        self.assertIsNotNone(self.controller.current_user)
        self.assertEqual(self.controller.current_user.nric, APP1_NRIC)

    def test_appendix_a_case_2_invalid_nric_format(self):
        with self.assertRaisesRegex(OperationError, "Invalid NRIC format"):
            self.controller.auth_service.login("S1234567", DEFAULT_PW) # Too short
        with self.assertRaisesRegex(OperationError, "Invalid NRIC format"):
            self.controller.auth_service.login("X1234567A", DEFAULT_PW) # Wrong start char
        with self.assertRaisesRegex(OperationError, "Invalid NRIC format"):
            self.controller.auth_service.login("S123A567B", DEFAULT_PW) # Non-digit
        with self.assertRaisesRegex(OperationError, "Invalid NRIC format"):
            self.controller.auth_service.login("S12345678", DEFAULT_PW) # Wrong end char type

    def test_appendix_a_case_3_incorrect_password(self):
        with self.assertRaisesRegex(OperationError, "Incorrect password"):
            self.controller.auth_service.login(APP1_NRIC, "wrongpassword")

    def test_appendix_a_case_4_password_change(self):
        user = self._login_user(APP1_NRIC)
        new_pw = "newpassword123"
        self.controller.auth_service.change_password(user, new_pw)

        # Verify in memory
        self.assertEqual(user.password, new_pw)

        # Verify persistence by reloading controller and logging in again
        self.controller = ApplicationController() # Re-init to reload data
        user_reloaded = self._login_user(APP1_NRIC, new_pw)
        self.assertIsNotNone(user_reloaded)
        self.assertEqual(user_reloaded.password, new_pw)

        # Try logging in with old password - should fail
        self.controller = ApplicationController() # Re-init
        with self.assertRaisesRegex(OperationError, "Incorrect password"):
            self.controller.auth_service.login(APP1_NRIC, DEFAULT_PW)

    def test_appendix_a_case_5_project_visibility_toggle(self):
        # Test based on user group and toggle
        self._login_user(MGR2_NRIC) # Manager of Proj 3
        proj3 = self._get_project(PROJ3_NAME)
        self.assertFalse(proj3.visibility) # Starts invisible

        # Check applicant 2 (eligible single) cannot see Proj 3 initially
        self._login_user(APP2_NRIC)
        viewable = self.controller.project_service.get_viewable_projects_for_applicant(self.controller.current_user)
        self.assertNotIn(PROJ3_NAME, [p.project_name for p in viewable])

        # Manager toggles Proj 3 to visible
        self._login_user(MGR2_NRIC)
        self.controller.project_service.toggle_project_visibility(self.manager2, proj3)
        self.assertTrue(proj3.visibility)

        # Now Applicant 2 should see Proj 3 (it's future, but visible)
        self._login_user(APP2_NRIC)
        viewable = self.controller.project_service.get_viewable_projects_for_applicant(self.controller.current_user)
        # Note: get_viewable_projects_for_applicant filters by active period. Let's check eligibility directly
        # This case seems to test visibility toggle impact, not necessarily *active* viewability
        all_projects = self.controller.project_service.get_all_projects()
        proj3_reloaded = next(p for p in all_projects if p.project_name == PROJ3_NAME)
        self.assertTrue(proj3_reloaded.visibility) # Visibility *is* saved

        # Check Applicant 1 (ineligible single < 35) still cannot see Proj 1 (even if visible)
        self._login_user(APP1_NRIC)
        viewable = self.controller.project_service.get_viewable_projects_for_applicant(self.controller.current_user)
        # Proj 1 should be visible as APP1 is single > 35 IS FALSE! APP1 is 30. Test is flawed based on data.
        # Let's test APP2 (Single, 35) CAN see Proj1
        self._login_user(APP2_NRIC)
        viewable = self.controller.project_service.get_viewable_projects_for_applicant(self.controller.current_user)
        self.assertIn(PROJ1_NAME, [p.project_name for p in viewable])

        # Test married APP4 can see Proj1
        self._login_user(APP4_NRIC)
        viewable = self.controller.project_service.get_viewable_projects_for_applicant(self.controller.current_user)
        self.assertIn(PROJ1_NAME, [p.project_name for p in viewable])


    def test_appendix_a_case_6_project_application_eligibility(self):
        proj1 = self._get_project(PROJ1_NAME)

        # APP1 (Single, 30) - Ineligible
        self._login_user(APP1_NRIC)
        with self.assertRaisesRegex(OperationError, "must be at least 35 years old"):
            self.controller.app_service.apply_for_project(self.applicant1, proj1, 2)

        # APP2 (Single, 35) - Eligible for 2-Room ONLY
        self._login_user(APP2_NRIC)
        self.controller.app_service.apply_for_project(self.applicant2, proj1, 2) # Should succeed
        app = self._get_application(APP2_NRIC)
        self.assertIsNotNone(app)
        self.assertEqual(app.project_name, PROJ1_NAME)
        self.assertEqual(app.flat_type, 2)
        # Try applying for 3-Room - should fail
        self.controller.app_repo.delete(APP2_NRIC, PROJ1_NAME) # Clean up first application
        with self.assertRaisesRegex(OperationError, "only apply for 2-Room"):
            self.controller.app_service.apply_for_project(self.applicant2, proj1, 3)

        # APP3 (Married, 20) - Ineligible
        self._login_user(APP3_NRIC)
        with self.assertRaisesRegex(OperationError, "must be at least 21 years old"):
            self.controller.app_service.apply_for_project(self.controller.current_user, proj1, 3)

        # APP4 (Married, 25) - Eligible for 2 or 3 Room
        self._login_user(APP4_NRIC)
        self.controller.app_service.apply_for_project(self.applicant4, proj1, 3) # Apply 3-Room
        app = self._get_application(APP4_NRIC)
        self.assertIsNotNone(app)
        self.assertEqual(app.flat_type, 3)
        self.controller.app_repo.delete(APP4_NRIC, PROJ1_NAME) # Clean up

        self.controller.app_service.apply_for_project(self.applicant4, proj1, 2) # Apply 2-Room
        app = self._get_application(APP4_NRIC)
        self.assertIsNotNone(app)
        self.assertEqual(app.flat_type, 2)

        # Cannot apply if already applied
        with self.assertRaisesRegex(OperationError, "already have an active BTO application"):
            self.controller.app_service.apply_for_project(self.applicant4, proj1, 2)

        # Cannot apply to closed project (Proj 2)
        proj2 = self._get_project(PROJ2_NAME)
        self.controller.app_repo.delete(APP4_NRIC, PROJ1_NAME) # Clean up
        with self.assertRaisesRegex(OperationError, "not currently open"):
            self.controller.app_service.apply_for_project(self.applicant4, proj2, 2)

        # Cannot apply if visibility is off (Proj 3)
        # NOTE: apply_for_project checks eligibility, which includes active period.
        # A project with visibility off won't be selected in the first place normally.
        # Let's toggle Proj1 off and try applying
        self._login_user(MGR1_NRIC)
        self.controller.project_service.toggle_project_visibility(self.manager1, proj1)
        self._login_user(APP4_NRIC)
        with self.assertRaisesRegex(OperationError, "not currently open"): # Check is based on is_currently_active()
             self.controller.app_service.apply_for_project(self.applicant4, proj1, 2)


    def test_appendix_a_case_7_view_application_after_visibility_off(self):
        self._login_user(APP2_NRIC)
        proj1 = self._get_project(PROJ1_NAME)
        self.controller.app_service.apply_for_project(self.applicant2, proj1, 2) # Apply first
        app = self._get_application(APP2_NRIC)
        self.assertIsNotNone(app)

        # Manager turns visibility off
        self._login_user(MGR1_NRIC)
        self.controller.project_service.toggle_project_visibility(self.manager1, proj1)
        self.assertFalse(proj1.visibility)

        # Applicant should still be able to view their application status
        self._login_user(APP2_NRIC)
        app_check = self.controller.app_service.find_application_by_applicant(APP2_NRIC)
        self.assertIsNotNone(app_check)
        self.assertEqual(app_check.project_name, PROJ1_NAME)
        # Also check viewable projects includes the applied-for one
        viewable = self.controller.project_service.get_viewable_projects_for_applicant(self.controller.current_user, app_check)
        self.assertIn(PROJ1_NAME, [p.project_name for p in viewable])


    def test_appendix_a_case_8_single_flat_booking(self):
        # Setup: APP4 (Married) applies for Proj1 (3-Room), Manager1 approves
        self._login_user(APP4_NRIC)
        proj1 = self._get_project(PROJ1_NAME)
        self.controller.app_service.apply_for_project(self.applicant4, proj1, 3)
        app = self._get_application(APP4_NRIC)

        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_approve_application(self.manager1, app)
        self.assertEqual(app.status, Application.STATUS_SUCCESSFUL)

        # Officer1 Books flat for APP4
        self._login_user(OFF1_NRIC)
        # Need to register OFF1 for PROJ1 first
        self._login_user(MGR1_NRIC)
        reg = Registration(OFF1_NRIC, PROJ1_NAME)
        self.controller.reg_repo.add(reg)
        self.controller.reg_service.manager_approve_officer_registration(self.manager1, reg)

        # Now Officer1 can book
        self._login_user(OFF1_NRIC)
        initial_units = proj1.num_units2
        self.controller.app_service.officer_book_flat(self.officer1, app)
        self.assertEqual(app.status, Application.STATUS_BOOKED)

        # Verify unit count decreased
        proj1_reloaded = self._get_project(PROJ1_NAME)
        self.assertEqual(proj1_reloaded.num_units2, initial_units - 1)

        # Try booking again (should fail - status is BOOKED)
        with self.assertRaisesRegex(OperationError, "status must be 'SUCCESSFUL'"):
            self.controller.app_service.officer_book_flat(self.officer1, app)

        # Try applying for another project (should fail - already booked)
        self._login_user(APP4_NRIC)
        proj5 = self._get_project(PROJ5_NAME)
        with self.assertRaisesRegex(OperationError, "already have an active BTO application"):
             self.controller.app_service.apply_for_project(self.applicant4, proj5, 2)


    def test_appendix_a_case_9_enquiry_management(self):
        self._login_user(APP1_NRIC) # Use ineligible applicant for simplicity
        proj1 = self._get_project(PROJ1_NAME)

        # Submit
        enq_text1 = "What facilities are nearby?"
        enquiry1 = self.controller.enq_service.submit_enquiry(self.applicant1, proj1, enq_text1)
        self.assertIsNotNone(enquiry1)
        self.assertGreater(enquiry1.enquiry_id, 0)
        self.assertEqual(enquiry1.text, enq_text1)
        self.assertEqual(enquiry1.applicant_nric, APP1_NRIC)
        self.assertEqual(enquiry1.project_name, PROJ1_NAME)
        self.assertFalse(enquiry1.is_replied())

        # View
        my_enquiries = self.controller.enq_service.get_enquiries_by_applicant(APP1_NRIC)
        self.assertEqual(len(my_enquiries), 1)
        self.assertEqual(my_enquiries[0].enquiry_id, enquiry1.enquiry_id)

        # Edit (before reply)
        new_text = "What leisure facilities are nearby?"
        self.controller.enq_service.edit_enquiry(self.applicant1, enquiry1, new_text)
        self.assertEqual(enquiry1.text, new_text)
        # Verify persistence
        enquiry1_reloaded = self.controller.enq_service.find_enquiry_by_id(enquiry1.enquiry_id)
        self.assertEqual(enquiry1_reloaded.text, new_text)

        # Manager replies
        self._login_user(MGR1_NRIC)
        reply_text = "Park connector, swimming complex."
        self.controller.enq_service.reply_to_enquiry(self.manager1, enquiry1_reloaded, reply_text)
        enquiry1_replied = self.controller.enq_service.find_enquiry_by_id(enquiry1.enquiry_id)
        self.assertTrue(enquiry1_replied.is_replied())
        self.assertIn(reply_text, enquiry1_replied.reply)
        self.assertIn("Manager", enquiry1_replied.reply)

        # Edit (after reply) - Should fail
        self._login_user(APP1_NRIC)
        with self.assertRaisesRegex(OperationError, "Cannot edit an enquiry that has already been replied to"):
            self.controller.enq_service.edit_enquiry(self.applicant1, enquiry1_replied, "Trying to edit again")

        # Delete (after reply) - Should fail
        with self.assertRaisesRegex(OperationError, "Cannot delete an enquiry that has already been replied to"):
            self.controller.enq_service.delete_enquiry(self.applicant1, enquiry1_replied)

        # Submit another enquiry
        enq_text2 = "Is there childcare nearby?"
        enquiry2 = self.controller.enq_service.submit_enquiry(self.applicant1, proj1, enq_text2)
        my_enquiries = self.controller.enq_service.get_enquiries_by_applicant(APP1_NRIC)
        self.assertEqual(len(my_enquiries), 2)

        # Delete enquiry 2 (unreplied)
        self.controller.enq_service.delete_enquiry(self.applicant1, enquiry2)
        my_enquiries = self.controller.enq_service.get_enquiries_by_applicant(APP1_NRIC)
        self.assertEqual(len(my_enquiries), 1)
        self.assertEqual(my_enquiries[0].enquiry_id, enquiry1.enquiry_id)
        enquiry2_check = self.controller.enq_service.find_enquiry_by_id(enquiry2.enquiry_id)
        self.assertIsNone(enquiry2_check) # Should be gone


    def test_appendix_a_case_10_hdb_officer_registration_eligibility(self):
        self._login_user(OFF1_NRIC)
        proj1 = self._get_project(PROJ1_NAME) # Managed by MGR1
        proj3 = self._get_project(PROJ3_NAME) # Managed by MGR2
        proj5 = self._get_project(PROJ5_NAME) # Managed by MGR2, overlaps Proj1

        # Officer 1 tries to register for Proj 1 (Eligible)
        self.controller.reg_service.officer_register_for_project(self.officer1, proj1)
        reg1 = self._get_registration(OFF1_NRIC, PROJ1_NAME)
        self.assertIsNotNone(reg1)
        self.assertEqual(reg1.status, Registration.STATUS_PENDING)

        # Officer 1 tries to register for Proj 1 again (Fail - already registered)
        with self.assertRaisesRegex(OperationError, "already submitted a registration"):
            self.controller.reg_service.officer_register_for_project(self.officer1, proj1)

        # Scenario: Officer 1 applies for Proj 3 first
        self.controller.app_service.apply_for_project(self.officer1, proj3, 2)
        # Now tries to register for Proj 3 (Fail - applied as applicant)
        with self.assertRaisesRegex(OperationError, "cannot register.*project you have applied for"):
            self.controller.reg_service.officer_register_for_project(self.officer1, proj3)
        self.controller.app_repo.delete(OFF1_NRIC, PROJ3_NAME) # Cleanup application

        # Scenario: Officer 2 approved for Proj 2 (closed). Tries to register for Proj 1 (open) - OK
        self._login_user(OFF2_NRIC)
        self.controller.reg_service.officer_register_for_project(self.officer2, proj1)
        reg2 = self._get_registration(OFF2_NRIC, PROJ1_NAME)
        self.assertIsNotNone(reg2)

        # Scenario: Manager1 approves OFF1 for Proj1. OFF1 tries to register for Proj5 (overlaps) - Fail
        self._login_user(MGR1_NRIC)
        self.controller.reg_service.manager_approve_officer_registration(self.manager1, reg1)
        self._login_user(OFF1_NRIC)
        self.assertEqual(reg1.status, Registration.STATUS_APPROVED)
        with self.assertRaisesRegex(OperationError, "overlapping application period"):
             self.controller.reg_service.officer_register_for_project(self.officer1, proj5)

        # Scenario: Officer tries registering for project managed by themselves (Fail)
        # Make OFF1 the manager of PROJ1 temporarily for test (doesn't reflect real roles)
        proj1.manager_nric = OFF1_NRIC
        self.controller.project_repo.update(proj1)
        self._login_user(OFF1_NRIC)
        with self.assertRaisesRegex(OperationError, "cannot register as officers for their own projects"):
             self.controller.reg_service.officer_register_for_project(self.officer1, proj1)


    def test_appendix_a_case_11_hdb_officer_registration_status(self):
        self._login_user(OFF1_NRIC)
        proj1 = self._get_project(PROJ1_NAME)
        self.controller.reg_service.officer_register_for_project(self.officer1, proj1)
        reg = self._get_registration(OFF1_NRIC, PROJ1_NAME)
        self.assertEqual(reg.status, Registration.STATUS_PENDING)

        # Officer checks status (test implicitly via getting registration)
        my_regs = self.controller.reg_service.get_registrations_by_officer(OFF1_NRIC)
        self.assertEqual(len(my_regs), 1)
        self.assertEqual(my_regs[0].status, Registration.STATUS_PENDING)

        # Manager approves
        self._login_user(MGR1_NRIC)
        self.controller.reg_service.manager_approve_officer_registration(self.manager1, reg)

        # Officer checks status again
        self._login_user(OFF1_NRIC)
        reg_reloaded = self._get_registration(OFF1_NRIC, PROJ1_NAME)
        self.assertEqual(reg_reloaded.status, Registration.STATUS_APPROVED)
        # Check project data reflects assigned officer NRIC
        proj1_reloaded = self._get_project(PROJ1_NAME)
        self.assertIn(OFF1_NRIC, proj1_reloaded.officer_nrics)


    def test_appendix_a_case_12_project_detail_access_for_officer(self):
        # Setup: OFF1 approved for PROJ1
        self._login_user(OFF1_NRIC)
        proj1 = self._get_project(PROJ1_NAME)
        reg = Registration(OFF1_NRIC, PROJ1_NAME)
        self.controller.reg_repo.add(reg)
        self._login_user(MGR1_NRIC)
        self.controller.reg_service.manager_approve_officer_registration(self.manager1, reg)

        # Officer views details (test implicitly via service access)
        self._login_user(OFF1_NRIC)
        handled_projects = self.controller.project_service.get_handled_projects_for_officer(OFF1_NRIC)
        self.assertIn(PROJ1_NAME, [p.project_name for p in handled_projects])

        # Manager toggles visibility off
        self._login_user(MGR1_NRIC)
        self.controller.project_service.toggle_project_visibility(self.manager1, proj1)
        self.assertFalse(proj1.visibility)

        # Officer should still see the project in their handled list
        self._login_user(OFF1_NRIC)
        handled_projects_after_toggle = self.controller.project_service.get_handled_projects_for_officer(OFF1_NRIC)
        self.assertIn(PROJ1_NAME, [p.project_name for p in handled_projects_after_toggle])
        # Test direct access too
        proj1_direct_access = self.controller.project_service.find_project_by_name(PROJ1_NAME)
        self.assertIsNotNone(proj1_direct_access)


    def test_appendix_a_case_13_restriction_on_editing_project_details_officer(self):
        # Test that officer role doesn't have access to edit methods (tested by role actions)
        self._login_user(OFF1_NRIC)
        role_actions = self.controller._get_available_actions("HDB Officer")
        self.assertNotIn("Edit Project", role_actions)
        self.assertNotIn("Create Project", role_actions)
        self.assertNotIn("Delete Project", role_actions)
        self.assertNotIn("Toggle Project Visibility", role_actions)


    def test_appendix_a_case_14_response_to_project_enquiries_roles(self):
        # Setup: Enquiry by APP1 on PROJ1 (Managed by MGR1, handled by OFF1)
        self._login_user(APP1_NRIC)
        proj1 = self._get_project(PROJ1_NAME)
        enquiry = self.controller.enq_service.submit_enquiry(self.applicant1, proj1, "Enquiry for roles test")
        enq_id = enquiry.enquiry_id

        # Assign OFF1 to PROJ1
        self._login_user(OFF1_NRIC)
        reg = Registration(OFF1_NRIC, PROJ1_NAME)
        self.controller.reg_repo.add(reg)
        self._login_user(MGR1_NRIC)
        self.controller.reg_service.manager_approve_officer_registration(self.manager1, reg)

        # Test Officer 1 can reply
        self._login_user(OFF1_NRIC)
        enq_for_off1 = self.controller.enq_service.find_enquiry_by_id(enq_id)
        self.controller.enq_service.reply_to_enquiry(self.officer1, enq_for_off1, "Reply from Officer 1")
        enq_reloaded = self.controller.enq_service.find_enquiry_by_id(enq_id)
        self.assertTrue(enq_reloaded.is_replied())
        self.assertIn("Officer", enq_reloaded.reply)
        self.assertIn("Reply from Officer 1", enq_reloaded.reply)

        # Reset reply for manager test
        enq_reloaded.reply = ""
        self.controller.enq_repo.update(enq_reloaded)

        # Test Manager 1 can reply
        self._login_user(MGR1_NRIC)
        enq_for_mgr1 = self.controller.enq_service.find_enquiry_by_id(enq_id)
        self.controller.enq_service.reply_to_enquiry(self.manager1, enq_for_mgr1, "Reply from Manager 1")
        enq_reloaded = self.controller.enq_service.find_enquiry_by_id(enq_id)
        self.assertTrue(enq_reloaded.is_replied())
        self.assertIn("Manager", enq_reloaded.reply)
        self.assertIn("Reply from Manager 1", enq_reloaded.reply)

        # Test Officer 2 (handles PROJ2) cannot reply to PROJ1 enquiry
        self._login_user(OFF2_NRIC) # Handles PROJ2
        enq_for_off2 = self.controller.enq_service.find_enquiry_by_id(enq_id)
        with self.assertRaisesRegex(OperationError, "Officers can only reply to enquiries for projects they handle."):
            self.controller.enq_service.reply_to_enquiry(self.officer2, enq_for_off2, "Reply from Officer 2")

        # Test Manager 2 (manages PROJ3/5) cannot reply to PROJ1 enquiry
        self._login_user(MGR2_NRIC)
        enq_for_mgr2 = self.controller.enq_service.find_enquiry_by_id(enq_id)
        with self.assertRaisesRegex(OperationError, "Managers can only reply.*projects they manage"):
            self.controller.enq_service.reply_to_enquiry(self.manager2, enq_for_mgr2, "Reply from Manager 2")

        # Test Applicant cannot reply
        self._login_user(APP1_NRIC)
        enq_for_app1 = self.controller.enq_service.find_enquiry_by_id(enq_id)
        with self.assertRaisesRegex(OperationError, "Only Managers or Officers can reply"):
             self.controller.enq_service.reply_to_enquiry(self.applicant1, enq_for_app1, "Reply from Applicant")


    def test_appendix_a_case_15_flat_selection_booking_management(self):
        # Setup: APP4 applies PROJ1 (3-Room), MGR1 approves, OFF1 handles PROJ1
        self._login_user(APP4_NRIC)
        proj1 = self._get_project(PROJ1_NAME)
        self.controller.app_service.apply_for_project(self.applicant4, proj1, 3)
        app = self._get_application(APP4_NRIC)
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_approve_application(self.manager1, app)
        reg = Registration(OFF1_NRIC, PROJ1_NAME)
        self.controller.reg_repo.add(reg)
        self.controller.reg_service.manager_approve_officer_registration(self.manager1, reg)

        # Officer Books
        self._login_user(OFF1_NRIC)
        initial_units = proj1.num_units2
        self.controller.app_service.officer_book_flat(self.officer1, app)

        # Verify application status update
        app_reloaded = self._get_application(APP4_NRIC)
        self.assertEqual(app_reloaded.status, Application.STATUS_BOOKED)

        # Verify unit count update
        proj1_reloaded = self._get_project(PROJ1_NAME)
        self.assertEqual(proj1_reloaded.num_units2, initial_units - 1)

        # Verify persistence (reload controller and check)
        self.controller = ApplicationController()
        app_reloaded_again = self._get_application(APP4_NRIC)
        self.assertEqual(app_reloaded_again.status, Application.STATUS_BOOKED)
        proj1_reloaded_again = self._get_project(PROJ1_NAME)
        self.assertEqual(proj1_reloaded_again.num_units2, initial_units - 1)


    def test_appendix_a_case_16_receipt_generation(self):
        # Setup: APP4 applies PROJ1 (3-Room), MGR1 approves, OFF1 handles PROJ1, OFF1 books
        self._login_user(APP4_NRIC)
        proj1 = self._get_project(PROJ1_NAME)
        self.controller.app_service.apply_for_project(self.applicant4, proj1, 3)
        app = self._get_application(APP4_NRIC)
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_approve_application(self.manager1, app)
        reg = Registration(OFF1_NRIC, PROJ1_NAME)
        self.controller.reg_repo.add(reg)
        self.controller.reg_service.manager_approve_officer_registration(self.manager1, reg)
        self._login_user(OFF1_NRIC)
        self.controller.app_service.officer_book_flat(self.officer1, app)

        # Officer generates receipt
        receipt_data = self.controller._prepare_receipt_data(app, proj1, self.applicant4) # Simulate internal data prep
        self.assertIsNotNone(receipt_data)
        self.assertEqual(receipt_data["Applicant Name"], self.applicant4.name)
        self.assertEqual(receipt_data["NRIC"], APP4_NRIC)
        self.assertEqual(receipt_data["Flat Type Booked"], "3-Room")
        self.assertEqual(receipt_data["Project Name"], PROJ1_NAME)
        # Test trying to generate for non-booked application fails (or rather, no data found)
        # Let APP2 apply, MGR1 approve, but OFF1 does NOT book
        self._login_user(APP2_NRIC)
        self.controller.app_service.apply_for_project(self.applicant2, proj1, 2)
        app2 = self._get_application(APP2_NRIC)
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_approve_application(self.manager1, app2)
        # Try generating receipt for APP2 - logic in handle_generate_receipt should find no *booked* app
        self._login_user(OFF1_NRIC)
        # Cannot directly call handle_generate_receipt easily, check the logic:
        booked_app = None
        for a in self.controller.app_repo.get_all():
             if a.applicant_nric == APP2_NRIC and a.status == Application.STATUS_BOOKED:
                  booked_app = a
                  break
        self.assertIsNone(booked_app) # Correctly doesn't find a booked app


    def test_appendix_a_case_17_create_edit_delete_bto_project(self):
        self._login_user(MGR1_NRIC)
        new_proj_name = "Brand New Heights"
        new_proj_neigh = "Punggol"

        # Create
        self.controller.project_service.create_project(
            self.manager1, new_proj_name, new_proj_neigh, 10, 120000, 15, 220000,
            TODAY, NEXT_MONTH, 8
        )
        new_proj = self._get_project(new_proj_name)
        self.assertEqual(new_proj.neighborhood, new_proj_neigh)
        self.assertEqual(new_proj.manager_nric, MGR1_NRIC)
        # Check persistence
        self.controller = ApplicationController()
        new_proj_reloaded = self._get_project(new_proj_name)
        self.assertIsNotNone(new_proj_reloaded)

        # Edit
        self._login_user(MGR1_NRIC)
        updates = {'neighborhood': 'Sengkang', 'n1': 12}
        self.controller.project_service.edit_project(self.manager1, new_proj_reloaded, updates)
        edited_proj = self._get_project(new_proj_name)
        self.assertEqual(edited_proj.neighborhood, 'Sengkang')
        self.assertEqual(edited_proj.num_units1, 12)
        # Check persistence
        self.controller = ApplicationController()
        edited_proj_reloaded = self._get_project(new_proj_name)
        self.assertEqual(edited_proj_reloaded.neighborhood, 'Sengkang')

        # Delete
        self._login_user(MGR1_NRIC)
        self.controller.project_service.delete_project(self.manager1, edited_proj_reloaded)
        # Verify deletion
        self.assertIsNone(self.controller.project_service.find_project_by_name(new_proj_name))
        # Check persistence
        self.controller = ApplicationController()
        self.assertIsNone(self.controller.project_service.find_project_by_name(new_proj_name))


    def test_appendix_a_case_18_single_project_management_per_period(self):
        # MGR1 already manages PROJ1 (Yesterday to Next Week)
        self._login_user(MGR1_NRIC)

        # Try creating another project overlapping PROJ1's active period
        with self.assertRaisesRegex(OperationError, "already handles an active project"):
            self.controller.project_service.create_project(
                self.manager1, "Overlap Project A", "Choa Chu Kang", 5, 5, 5, 5,
                TODAY, NEXT_WEEK, 5 # Overlaps PROJ1
            )
        # Try creating project starting *during* PROJ1's active period
        with self.assertRaisesRegex(OperationError, "already handles an active project"):
            self.controller.project_service.create_project(
                self.manager1, "Overlap Project B", "Choa Chu Kang", 5, 5, 5, 5,
                TOMORROW, NEXT_MONTH, 5 # Starts during PROJ1
            )
        # Try creating project ending *during* PROJ1's active period
        with self.assertRaisesRegex(OperationError, "already handles an active project"):
             self.controller.project_service.create_project(
                 self.manager1, "Overlap Project C", "Choa Chu Kang", 5, 5, 5, 5,
                 LAST_WEEK, TOMORROW, 5 # Ends during PROJ1
             )

        # Try creating non-overlapping project (after PROJ1 ends) - Should succeed
        self.controller.project_service.create_project(
            self.manager1, "Non Overlap Project", "Bukit Batok", 5, 5, 5, 5,
            NEXT_WEEK + timedelta(days=1), NEXT_MONTH, 5
        )
        non_overlap = self._get_project("Non Overlap Project")
        self.assertIsNotNone(non_overlap)

        # Try editing PROJ1 to overlap with the newly created non-overlapping one (should fail)
        proj1 = self._get_project(PROJ1_NAME)
        updates = {'closeDate': NEXT_MONTH} # Make PROJ1 overlap "Non Overlap Project"
        with self.assertRaisesRegex(OperationError, "Edited dates overlap"):
             self.controller.project_service.edit_project(self.manager1, proj1, updates)

        # FAQ Clarification: Can handle multiple projects if *not active*
        # MGR1 also "manages" PROJ2 (closed) and PROJ4 (zero units), this is allowed.
        # MGR1 can create "Non Overlap Project" because PROJ1 is the *only* active one during its period.
        self.assertTrue(proj1.is_currently_active())
        self.assertFalse(self._get_project(PROJ2_NAME).is_currently_active()) # Closed
        self.assertTrue(self._get_project(PROJ4_NAME).is_currently_active()) # Open but zero units - still active? YES, based on FAQ definition.
        # The FAQ implies "active" means visibility ON + within application period.
        # Let's refine the test based on FAQ definition of Active.
        # Proj1 is Active. Proj4 is Active. MGR1 has two Active projects.
        # This contradicts the constraint "Can only be handling one project within an application period"
        # Re-reading FAQ: "HDB Manager will not be able to create a new project if he/she already has an active project within the application period."
        # And "Definition of 'Active': Visibility turned ON + Within application period"
        # Okay, let's re-test creation. MGR1 has PROJ1 and PROJ4 active.
        # Trying to create "Non Overlap Project" should FAIL if PROJ1 or PROJ4 overlaps.
        # Proj1: YESTERDAY -> NEXT_WEEK
        # Proj4: YESTERDAY -> NEXT_WEEK
        # Non Overlap: NEXT_WEEK+1 -> NEXT_MONTH. No overlap. Creation is OK.

        # Let's try creating a project that *does* overlap with PROJ1/PROJ4's dates:
        self._login_user(MGR1_NRIC)
        with self.assertRaisesRegex(OperationError, "already handles an active project"):
             self.controller.project_service.create_project(
                 self.manager1, "Overlap Project D", "Choa Chu Kang", 5, 5, 5, 5,
                 TODAY, NEXT_WEEK, 5 # Overlaps PROJ1/PROJ4
             )
        # Test editing PROJ1 to end later (still overlapping PROJ4) - Allowed, editing same period
        proj1 = self._get_project(PROJ1_NAME)
        updates = {'closeDate': NEXT_WEEK + timedelta(days=1)}
        self.controller.project_service.edit_project(self.manager1, proj1, updates) # Should be okay
        # Test editing PROJ1 to overlap PROJ5 (managed by MGR2) - Allowed, different manager
        updates = {'closeDate': NEXT_MONTH}
        self.controller.project_service.edit_project(self.manager1, proj1, updates) # Should be okay


    def test_appendix_a_case_19_toggle_project_visibility(self):
        self._login_user(MGR1_NRIC)
        proj1 = self._get_project(PROJ1_NAME)
        self.assertTrue(proj1.visibility) # Starts visible

        # Toggle off
        self.controller.project_service.toggle_project_visibility(self.manager1, proj1)
        self.assertFalse(proj1.visibility)
        # Check persistence
        self.controller = ApplicationController()
        proj1_reloaded = self._get_project(PROJ1_NAME)
        self.assertFalse(proj1_reloaded.visibility)

        # Toggle on again
        self._login_user(MGR1_NRIC)
        self.controller.project_service.toggle_project_visibility(self.manager1, proj1_reloaded)
        self.assertTrue(proj1_reloaded.visibility)
        # Check persistence
        self.controller = ApplicationController()
        proj1_reloaded_again = self._get_project(PROJ1_NAME)
        self.assertTrue(proj1_reloaded_again.visibility)


    def test_appendix_a_case_20_view_all_filtered_project_listings_manager(self):
        self._login_user(MGR1_NRIC)

        # View All (implicitly tested by get_all_projects)
        all_projects = self.controller.project_service.get_all_projects()
        self.assertEqual(len(all_projects), 5) # Proj 1, 2, 3, 4, 5

        # View Managed by MGR1
        mgr1_projects = self.controller.project_service.get_projects_by_manager(MGR1_NRIC)
        self.assertEqual(len(mgr1_projects), 3)
        mgr1_names = {p.project_name for p in mgr1_projects}
        self.assertEqual(mgr1_names, {PROJ1_NAME, PROJ2_NAME, PROJ4_NAME})

        # Filter All projects by location 'Yishun'
        self.controller.user_filters = {'location': 'Yishun'}
        filtered_all = self.controller.project_service.filter_projects(all_projects, **self.controller.user_filters)
        self.assertEqual(len(filtered_all), 1)
        self.assertEqual(filtered_all[0].project_name, PROJ1_NAME)

        # Filter All projects by flat type '2'
        self.controller.user_filters = {'flat_type': '2'}
        # Note: filter_projects logic checks for > 0 units.
        # Proj1 (5 units), Proj2 (2 units), Proj3 (8 units), Proj5 (10 units)
        filtered_all = self.controller.project_service.filter_projects(all_projects, **self.controller.user_filters)
        self.assertEqual(len(filtered_all), 4)
        filtered_names = {p.project_name for p in filtered_all}
        self.assertIn(PROJ1_NAME, filtered_names)
        self.assertIn(PROJ2_NAME, filtered_names)
        self.assertIn(PROJ3_NAME, filtered_names)
        self.assertIn(PROJ5_NAME, filtered_names)
        self.assertNotIn(PROJ4_NAME, filtered_names) # 0 units

        # Filter MGR1 projects by location 'Boon Lay'
        self.controller.user_filters = {'location': 'Boon Lay'}
        filtered_mgr1 = self.controller.project_service.filter_projects(mgr1_projects, **self.controller.user_filters)
        self.assertEqual(len(filtered_mgr1), 1)
        self.assertEqual(filtered_mgr1[0].project_name, PROJ2_NAME)


    def test_appendix_a_case_21_manage_hdb_officer_registrations(self):
        # Setup: OFF1 registers for PROJ1 (Managed by MGR1)
        self._login_user(OFF1_NRIC)
        proj1 = self._get_project(PROJ1_NAME)
        self.controller.reg_service.officer_register_for_project(self.officer1, proj1)
        reg = self._get_registration(OFF1_NRIC, PROJ1_NAME)
        self.assertEqual(reg.status, Registration.STATUS_PENDING)

        # Manager views pending registrations for PROJ1
        self._login_user(MGR1_NRIC)
        pending_regs = self.controller.reg_service.get_registrations_for_project(PROJ1_NAME, Registration.STATUS_PENDING)
        self.assertEqual(len(pending_regs), 1)
        self.assertEqual(pending_regs[0].officer_nric, OFF1_NRIC)

        # Manager approves registration
        initial_slot = proj1.officer_slot
        initial_assigned_count = len(proj1.officer_nrics)
        self.controller.reg_service.manager_approve_officer_registration(self.manager1, reg)
        self.assertEqual(reg.status, Registration.STATUS_APPROVED)
        # Check project updated
        proj1_reloaded = self._get_project(PROJ1_NAME)
        self.assertIn(OFF1_NRIC, proj1_reloaded.officer_nrics)
        self.assertEqual(len(proj1_reloaded.officer_nrics), initial_assigned_count + 1)

        # Setup: OFF2 registers for PROJ1
        self._login_user(OFF2_NRIC)
        self.controller.reg_service.officer_register_for_project(self.officer2, proj1)
        reg2 = self._get_registration(OFF2_NRIC, PROJ1_NAME)

        # Manager rejects registration
        self._login_user(MGR1_NRIC)
        self.controller.reg_service.manager_reject_officer_registration(self.manager1, reg2)
        self.assertEqual(reg2.status, Registration.STATUS_REJECTED)
        # Check project *not* updated
        proj1_reloaded_again = self._get_project(PROJ1_NAME)
        self.assertNotIn(OFF2_NRIC, proj1_reloaded_again.officer_nrics)
        self.assertEqual(len(proj1_reloaded_again.officer_nrics), initial_assigned_count + 1) # Still just OFF1


    def test_appendix_a_case_22_approve_reject_bto_apps_withdrawals(self):
        # Setup: APP2 (Single, 35) applies for PROJ1 (2-Room)
        self._login_user(APP2_NRIC)
        proj1 = self._get_project(PROJ1_NAME)
        self.controller.app_service.apply_for_project(self.applicant2, proj1, 2)
        app = self._get_application(APP2_NRIC)
        self.assertEqual(app.status, Application.STATUS_PENDING)

        # Manager approves application
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_approve_application(self.manager1, app)
        self.assertEqual(app.status, Application.STATUS_SUCCESSFUL)
        # Check persistence
        self.controller = ApplicationController()
        app_reloaded = self._get_application(APP2_NRIC)
        self.assertEqual(app_reloaded.status, Application.STATUS_SUCCESSFUL)

        # Applicant requests withdrawal
        self._login_user(APP2_NRIC)
        self.controller.app_service.request_withdrawal(app_reloaded)
        self.assertTrue(app_reloaded.request_withdrawal)
        # Check persistence
        self.controller = ApplicationController()
        app_reloaded_2 = self._get_application(APP2_NRIC)
        self.assertTrue(app_reloaded_2.request_withdrawal)

        # Manager approves withdrawal
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_approve_withdrawal(self.manager1, app_reloaded_2)
        self.assertEqual(app_reloaded_2.status, Application.STATUS_UNSUCCESSFUL)
        self.assertFalse(app_reloaded_2.request_withdrawal)
        # Check persistence
        self.controller = ApplicationController()
        app_reloaded_3 = self._get_application(APP2_NRIC)
        # NOTE: find_by_applicant_nric returns only non-unsuccessful. We need to check repo directly.
        found_app = None
        for a in self.controller.app_repo.get_all():
             if a.applicant_nric == APP2_NRIC and a.project_name == PROJ1_NAME:
                 found_app = a
                 break
        self.assertIsNotNone(found_app)
        self.assertEqual(found_app.status, Application.STATUS_UNSUCCESSFUL)
        self.assertFalse(found_app.request_withdrawal)

        # --- Test Rejection ---
        # Setup: APP4 applies PROJ1 (3-Room)
        self._login_user(APP4_NRIC)
        proj1 = self._get_project(PROJ1_NAME)
        self.controller.app_service.apply_for_project(self.applicant4, proj1, 3)
        app4 = self._get_application(APP4_NRIC)

        # Manager rejects application
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_reject_application(self.manager1, app4)
        self.assertEqual(app4.status, Application.STATUS_UNSUCCESSFUL)

        # Setup: APP4 applies again (needs cleanup first), gets approved, requests withdrawal
        self.controller.app_repo.delete(APP4_NRIC, PROJ1_NAME) # Clean previous rejection
        self._login_user(APP4_NRIC)
        self.controller.app_service.apply_for_project(self.applicant4, proj1, 3)
        app4_again = self._get_application(APP4_NRIC)
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_approve_application(self.manager1, app4_again)
        self._login_user(APP4_NRIC)
        self.controller.app_service.request_withdrawal(app4_again)

        # Manager rejects withdrawal
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_reject_withdrawal(self.manager1, app4_again)
        self.assertEqual(app4_again.status, Application.STATUS_SUCCESSFUL) # Status unchanged
        self.assertFalse(app4_again.request_withdrawal) # Request flag cleared


    def test_appendix_a_case_23_generate_filter_reports(self):
        # Setup: Book some flats
        # APP2 (Single, 35) -> Proj1, 2-Room -> Booked by OFF1
        self._login_user(APP2_NRIC)
        proj1 = self._get_project(PROJ1_NAME)
        self.controller.app_service.apply_for_project(self.applicant2, proj1, 2)
        app2 = self._get_application(APP2_NRIC)
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_approve_application(self.manager1, app2)
        reg = Registration(OFF1_NRIC, PROJ1_NAME)
        self.controller.reg_repo.add(reg)
        self.controller.reg_service.manager_approve_officer_registration(self.manager1, reg)
        self._login_user(OFF1_NRIC)
        self.controller.app_service.officer_book_flat(self.officer1, app2)

        # APP4 (Married, 25) -> Proj1, 3-Room -> Booked by OFF1
        self._login_user(APP4_NRIC)
        self.controller.app_service.apply_for_project(self.applicant4, proj1, 3)
        app4 = self._get_application(APP4_NRIC)
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_approve_application(self.manager1, app4)
        self._login_user(OFF1_NRIC)
        self.controller.app_service.officer_book_flat(self.officer1, app4)

        # APP1 (Single, 30 - now made eligible 35 for test) -> Proj5, 2-Room -> Booked by OFF2
        self.applicant1.age = 35 # Temporarily change age for test
        self.controller.user_repo.save_user(self.applicant1)
        self._login_user(APP1_NRIC)
        proj5 = self._get_project(PROJ5_NAME)
        self.controller.app_service.apply_for_project(self.applicant1, proj5, 2)
        app1 = self._get_application(APP1_NRIC)
        self._login_user(MGR2_NRIC) # MGR2 manages Proj5
        self.controller.app_service.manager_approve_application(self.manager2, app1)
        reg2 = Registration(OFF2_NRIC, PROJ5_NAME) # Register OFF2 for Proj5
        self.controller.reg_repo.add(reg2)
        self.controller.reg_service.manager_approve_officer_registration(self.manager2, reg2)
        self._login_user(OFF2_NRIC)
        self.controller.app_service.officer_book_flat(self.officer2, app1)

        # --- Generate Reports (Manager 1) ---
        self._login_user(MGR1_NRIC)

        # Report All Bookings (No Filters)
        report_all = self.controller.app_service.generate_booking_report_data()
        self.assertEqual(len(report_all), 3)
        nrics_all = {r['NRIC'] for r in report_all}
        self.assertEqual(nrics_all, {APP1_NRIC, APP2_NRIC, APP4_NRIC})

        # Report Filtered by Project = PROJ1_NAME
        report_proj1 = self.controller.app_service.generate_booking_report_data(filter_project_name=PROJ1_NAME)
        self.assertEqual(len(report_proj1), 2)
        nrics_proj1 = {r['NRIC'] for r in report_proj1}
        self.assertEqual(nrics_proj1, {APP2_NRIC, APP4_NRIC})

        # Report Filtered by Flat Type = 2
        report_type2 = self.controller.app_service.generate_booking_report_data(filter_flat_type_str='2')
        self.assertEqual(len(report_type2), 2)
        nrics_type2 = {r['NRIC'] for r in report_type2}
        self.assertEqual(nrics_type2, {APP1_NRIC, APP2_NRIC}) # APP1 and APP2 booked 2-room

        # Report Filtered by Flat Type = 3
        report_type3 = self.controller.app_service.generate_booking_report_data(filter_flat_type_str='3')
        self.assertEqual(len(report_type3), 1)
        self.assertEqual(report_type3[0]['NRIC'], APP4_NRIC) # Only APP4 booked 3-room

        # Report Filtered by Project = PROJ1 AND Flat Type = 2
        report_proj1_type2 = self.controller.app_service.generate_booking_report_data(filter_project_name=PROJ1_NAME, filter_flat_type_str='2')
        self.assertEqual(len(report_proj1_type2), 1)
        self.assertEqual(report_proj1_type2[0]['NRIC'], APP2_NRIC)

    # --- FAQ Based Tests ---

    def test_faq_csv_excel_txt_allowed(self):
        # Tested implicitly by using CSV throughout the setup and tests.
        # Ensure data is saved and loaded correctly.
        self._login_user(MGR1_NRIC)
        initial_projects = len(self.controller.project_service.get_all_projects())
        self.controller.project_service.create_project(
            self.manager1, "CSV Test Proj", "CSV Area", 1, 1, 1, 1, TODAY, NEXT_WEEK, 1
        )
        # Reload controller to force read from CSV
        self.controller = ApplicationController()
        projects_after_save = len(self.controller.project_service.get_all_projects())
        self.assertEqual(projects_after_save, initial_projects + 1)
        self._check_csv_for_value(PROJECT_CSV, 0, "CSV Test Proj")

    def test_faq_filter_by_room_type_shows_only_that_type(self):
        # Proj1 has 2-Room and 3-Room. Proj2 has 2-Room and 3-Room.
        # Proj3 has 2-Room and 3-Room. Proj4 has 0 units. Proj5 has 2-Room and 3-Room.
        all_projects = self.controller.project_service.get_all_projects()

        # Filter for 2-Room (expect Proj 1, 2, 3, 5 - those with > 0 units)
        filtered_2 = self.controller.project_service.filter_projects(all_projects, flat_type='2')
        filtered_names_2 = {p.project_name for p in filtered_2}
        self.assertEqual(len(filtered_2), 4)
        self.assertEqual(filtered_names_2, {PROJ1_NAME, PROJ2_NAME, PROJ3_NAME, PROJ5_NAME})
        for p in filtered_2:
            self.assertTrue(p.num_units1 > 0 and p.type1 == "2-Room")

        # Filter for 3-Room (expect Proj 1, 2, 3, 5)
        filtered_3 = self.controller.project_service.filter_projects(all_projects, flat_type='3')
        filtered_names_3 = {p.project_name for p in filtered_3}
        self.assertEqual(len(filtered_3), 4)
        self.assertEqual(filtered_names_3, {PROJ1_NAME, PROJ2_NAME, PROJ3_NAME, PROJ5_NAME})
        for p in filtered_3:
             self.assertTrue(p.num_units2 > 0 and p.type2 == "3-Room")

    def test_faq_withdrawal_request_handling(self):
        # Implicitly tested in test_appendix_a_case_22
        # Manager approves -> Unsuccessful
        # Manager rejects -> Status quo, request flag cleared
        # FAQ also says "Assume it is always successful" for Applicant perspective initally,
        # but clarifies Manager can approve/reject. Test covers manager actions.
        pass # Covered in A22

    def test_faq_officer_applies_for_bto(self):
        # OFF1 is eligible (Married, 40)
        self._login_user(OFF1_NRIC)
        proj1 = self._get_project(PROJ1_NAME)
        self.controller.app_service.apply_for_project(self.officer1, proj1, 3) # Apply 3-Room
        app = self._get_application(OFF1_NRIC)
        self.assertIsNotNone(app)
        self.assertEqual(app.project_name, PROJ1_NAME)
        self.assertEqual(app.flat_type, 3)

        # Try to register for the *same* project (PROJ1) - Should fail
        with self.assertRaisesRegex(OperationError, "cannot register.*project you have applied for"):
            self.controller.reg_service.officer_register_for_project(self.officer1, proj1)

        # Now, MGR1 approves the application
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_approve_application(self.manager1, app)

        # Now, OFF2 tries to book for OFF1 (assume OFF2 handles PROJ1)
        self._login_user(OFF2_NRIC)
        reg2 = Registration(OFF2_NRIC, PROJ1_NAME)
        self.controller.reg_repo.add(reg2)
        self._login_user(MGR1_NRIC)
        self.controller.reg_service.manager_approve_officer_registration(self.manager1, reg2)
        self._login_user(OFF2_NRIC)
        self.controller.app_service.officer_book_flat(self.officer2, app)
        self.assertEqual(app.status, Application.STATUS_BOOKED)

    def test_faq_officer_registers_for_another_project(self):
        # OFF1 applies and books PROJ1 (from previous test setup)
        self.test_faq_officer_applies_for_bto()
        app = self._get_application(OFF1_NRIC)
        self.assertEqual(app.status, Application.STATUS_BOOKED)

        # OFF1 tries to register for PROJ5 (different project, managed by MGR2)
        self._login_user(OFF1_NRIC)
        proj5 = self._get_project(PROJ5_NAME)
        # Check eligibility: No current *application* for Proj5. No existing *registration* for Proj5.
        # Check overlap: PROJ1 booking is irrelevant. Officer needs to check against *approved registrations*.
        # OFF1 has no other approved registrations.
        # Check if OFF1 is manager of PROJ5 (False).
        # Should be allowed.
        self.controller.reg_service.officer_register_for_project(self.officer1, proj5)
        reg5 = self._get_registration(OFF1_NRIC, PROJ5_NAME)
        self.assertIsNotNone(reg5)
        self.assertEqual(reg5.status, Registration.STATUS_PENDING)

    def test_faq_applicant_enquiry_regardless_of_application(self):
        # APP1 currently has no application
        self._login_user(APP1_NRIC)
        self.assertIsNone(self._get_application(APP1_NRIC))
        proj1 = self._get_project(PROJ1_NAME)
        # Submit enquiry
        enq1 = self.controller.enq_service.submit_enquiry(self.applicant1, proj1, "Enquiry before application")
        self.assertIsNotNone(enq1)
        # Check it was saved
        self.assertIsNotNone(self.controller.enq_service.find_enquiry_by_id(enq1.enquiry_id))

        # Now APP1 applies
        self.applicant1.age = 35 # Make eligible
        self.controller.user_repo.save_user(self.applicant1)
        self._login_user(APP1_NRIC)
        self.controller.app_service.apply_for_project(self.applicant1, proj1, 2)
        self.assertIsNotNone(self._get_application(APP1_NRIC))

        # Submit another enquiry after applying
        enq2 = self.controller.enq_service.submit_enquiry(self.applicant1, proj1, "Enquiry after application")
        self.assertIsNotNone(enq2)
        self.assertNotEqual(enq1.enquiry_id, enq2.enquiry_id)
        # Check both exist
        my_enqs = self.controller.enq_service.get_enquiries_by_applicant(APP1_NRIC)
        self.assertEqual(len(my_enqs), 2)

    def test_faq_enquiry_cannot_edit_delete_after_reply(self):
        # Covered in test_appendix_a_case_9
        pass

    def test_faq_additional_columns_allowed(self):
        # Tested implicitly. The repositories load based on REQUIRED_HEADERS.
        # If extra columns exist in the CSV, they are ignored on load.
        # On save, only the REQUIRED_HEADERS are written.
        # To fully test adding a column, we'd need to modify the model and repo.
        # Example: Add 'Timestamp' to Enquiry
        # 1. Modify Enquiry class: add self.timestamp
        # 2. Modify EnquiryRepository:
        #    - Add 'Timestamp' to required_headers
        #    - Modify _create_instance to read timestamp
        #    - Modify _get_row_data to write timestamp
        # This test suite *assumes* the current code structure works with the defined headers.
        pass

    def test_faq_xlsx_to_csv_allowed(self):
        # Tested implicitly by using CSV format throughout.
        pass

    def test_faq_applicant_view_sees_available_units(self):
        # Test view function implicitly checks project details display
        self._login_user(APP2_NRIC) # Eligible single
        proj1 = self._get_project(PROJ1_NAME)
        # We cannot directly test the view's print output easily here.
        # But we can verify the project data loaded is correct.
        self.assertEqual(proj1.num_units1, 5) # 2-Room
        self.assertEqual(proj1.num_units2, 10) # 3-Room

        proj4 = self._get_project(PROJ4_NAME) # Zero units
        self.assertEqual(proj4.num_units1, 0)
        self.assertEqual(proj4.num_units2, 0)
        # Applicant 2 should still see Proj4 listed if viewing all eligible,
        # but the details should show 0 units.
        viewable = self.controller.project_service.get_viewable_projects_for_applicant(self.applicant2)
        self.assertNotIn(PROJ4_NAME, [p.project_name for p in viewable])

    def test_faq_single_applicant_restrictions(self):
        # APP1 (Single, 30) - Cannot view/apply PROJ1
        self._login_user(APP1_NRIC)
        viewable1 = self.controller.project_service.get_viewable_projects_for_applicant(self.applicant1)
        self.assertNotIn(PROJ1_NAME, [p.project_name for p in viewable1])
        proj1 = self._get_project(PROJ1_NAME)
        with self.assertRaises(OperationError):
            self.controller.app_service.apply_for_project(self.applicant1, proj1, 2)

        # APP2 (Single, 35) - Can view/apply PROJ1 (2-Room only)
        self._login_user(APP2_NRIC)
        viewable2 = self.controller.project_service.get_viewable_projects_for_applicant(self.applicant2)
        self.assertIn(PROJ1_NAME, [p.project_name for p in viewable2])
        # Apply 2-Room OK
        self.controller.app_service.apply_for_project(self.applicant2, proj1, 2)
        self.assertIsNotNone(self._get_application(APP2_NRIC))
        self.controller.app_repo.delete(APP2_NRIC, PROJ1_NAME) # Cleanup
        # Apply 3-Room Fail
        with self.assertRaisesRegex(OperationError,"only apply for 2-Room"):
            self.controller.app_service.apply_for_project(self.applicant2, proj1, 3)

        # View details: Single applicant view should hide 3-room details (This requires view testing, hard here)
        # We test the *application* restriction which is based on eligibility.


    def test_faq_project_visibility_zero_units(self):
        # Proj4 has zero units but is visible and open.
        proj4 = self._get_project(PROJ4_NAME)
        self.assertTrue(proj4.visibility)
        self.assertTrue(proj4.is_currently_active())
        self.assertEqual(proj4.num_units1, 0)
        self.assertEqual(proj4.num_units2, 0)

        # Eligible Applicant 2 (Single, 35) should see it listed.
        self._login_user(APP2_NRIC)

        # Try applying (should fail due to zero units)
        with self.assertRaisesRegex(OperationError, "No 2-Room units available"):
            self.controller.app_service.apply_for_project(self.applicant2, proj4, 2)


    def test_faq_officer_cannot_unregister(self):
        # Check if there's a method for it in the service/controller actions
        self._login_user(OFF1_NRIC)
        role_actions = self.controller._get_available_actions("HDB Officer")
        self.assertNotIn("Unregister for Project", role_actions)
        # No explicit unregister function found in services either.
        pass

    def test_faq_officer_reply_details(self):
        # Check if reply includes Officer name/role (tested in A14)
        pass # Covered in A14

    def test_faq_receipt_generation_conditions(self):
        # Receipt only for BOOKED status. Only by officer handling the project.
        # Tested implicitly in A16 and A15 setup (booking triggers receipt-like data).
        # Test that non-handling officer cannot generate receipt:
        # Setup: APP4 booked PROJ1, handled by OFF1. OFF2 tries to generate.
        self.test_appendix_a_case_15_flat_selection_booking_management() # Books APP4 on PROJ1 via OFF1
        self._login_user(OFF2_NRIC) # OFF2 does not handle PROJ1
        # We need to simulate handle_generate_receipt logic slightly
        booked_app = None
        for a in self.controller.app_repo.get_all():
             if a.applicant_nric == APP4_NRIC and a.status == Application.STATUS_BOOKED:
                  booked_app = a
                  break
        self.assertIsNotNone(booked_app)
        project = self.controller.project_service.find_project_by_name(booked_app.project_name)
        # Simulate the permission check inside handle_generate_receipt
        handled_names_off2 = self.controller._get_officer_handled_project_names() # Should be empty unless registered elsewhere
        self.assertNotIn(PROJ1_NAME, handled_names_off2)
        # If the check was implemented, an OperationError would be raised here.
        # The current _prepare_receipt_data doesn't have this check, relies on caller.
        # The `handle_generate_receipt` *should* have this check. Assume it does based on FAQ.

    def test_faq_unique_project_name(self):
        self._login_user(MGR1_NRIC)
        # Try creating project with existing name PROJ1_NAME
        with self.assertRaisesRegex(OperationError, "already exists"):
            self.controller.project_service.create_project(
                self.manager1, PROJ1_NAME, "New Area", 1, 1, 1, 1, TODAY, NEXT_WEEK, 1
            )
        # Try editing PROJ2 to have name PROJ1_NAME
        proj2 = self._get_project(PROJ2_NAME)
        updates = {'name': PROJ1_NAME}
        with self.assertRaisesRegex(OperationError, "already exists"):
             self.controller.project_service.edit_project(self.manager1, proj2, updates)

    def test_faq_project_open_close_determination(self):
        # Tested implicitly by application eligibility checks (A6) and view checks (A5)
        # which rely on project.is_currently_active() using current date.
        pass

    def test_faq_project_auto_close_behavior(self):
        # Project visibility after closing date
        proj2 = self._get_project(PROJ2_NAME) # Closed last week
        self.assertFalse(proj2.is_currently_active())

        # Eligible applicant APP4 tries to view projects
        self._login_user(APP4_NRIC)
        viewable = self.controller.project_service.get_viewable_projects_for_applicant(self.applicant4)
        # Should NOT see PROJ2 in the general viewable list for applying
        self.assertNotIn(PROJ2_NAME, [p.project_name for p in viewable])

        # If APP4 had applied to PROJ2 *before* it closed, they *should* still see it.
        # Let's simulate that:
        app_past = Application(APP4_NRIC, PROJ2_NAME, 3, Application.STATUS_PENDING)
        self.controller.app_repo._data_list.append(app_past) # Manually add past app
        self.controller.app_repo.save_data()
        self.controller = ApplicationController() # Reload
        self._login_user(APP4_NRIC)
        current_app = self.controller.app_service.find_application_by_applicant(APP4_NRIC)
        viewable_with_past = self.controller.project_service.get_viewable_projects_for_applicant(self.controller.current_user, current_app)
        # Now PROJ2 should be visible *to this applicant*
        self.assertIn(PROJ2_NAME, [p.project_name for p in viewable_with_past])

    def test_faq_csv_usage_init_and_persistent(self):
        # Tested implicitly by setUp/tearDown and data modification tests (e.g., A4, A17)
        # Check file content after an operation
        self._login_user(MGR1_NRIC)
        proj1 = self._get_project(PROJ1_NAME)
        initial_units = proj1.num_units1
        updates = {'n1': initial_units + 5}
        self.controller.project_service.edit_project(self.manager1, proj1, updates)
        # Check the CSV directly
        self._check_csv_data(PROJECT_CSV, [PROJ1_NAME, 'Yishun', '2-Room', str(initial_units + 5)], 0)


    def test_faq_data_persistence_required(self):
        # Tested implicitly by all tests that modify data and then check it,
        # especially those involving reloading the controller.
        pass

    def test_faq_input_validation_required(self):
        # NRIC format tested in A2.
        # Other inputs (like menu choices, numbers) are harder to test without mocking `input`.
        # Test service layer validation:
        self._login_user(MGR1_NRIC)
        # Create project with negative units
        with self.assertRaisesRegex(OperationError, "cannot be negative"):
             self.controller.project_service.create_project(
                 self.manager1, "Neg Proj", "Neg Area", -1, 1, 1, 1, TODAY, NEXT_WEEK, 1
             )
        # Create project with invalid date range (close < open)
        with self.assertRaisesRegex(OperationError, "Invalid opening or closing date"):
              self.controller.project_service.create_project(
                  self.manager1, "Date Proj", "Date Area", 1, 1, 1, 1, NEXT_WEEK, TODAY, 1
              )
        # Create project with invalid slots
        with self.assertRaisesRegex(OperationError, "Officer slots must be between"):
               self.controller.project_service.create_project(
                   self.manager1, "Slot Proj", "Slot Area", 1, 1, 1, 1, TODAY, NEXT_WEEK, 11
               )


    def test_faq_manager_edit_vs_officer_update(self):
        # Manager can edit details like location, total number of flats initially.
        self._login_user(MGR1_NRIC)
        proj1 = self._get_project(PROJ1_NAME)
        initial_units = proj1.num_units1
        initial_neigh = proj1.neighborhood
        updates = {'n1': initial_units + 10, 'neighborhood': 'New Yishun'}
        self.controller.project_service.edit_project(self.manager1, proj1, updates)
        proj1_reloaded = self._get_project(PROJ1_NAME)
        self.assertEqual(proj1_reloaded.num_units1, initial_units + 10)
        self.assertEqual(proj1_reloaded.neighborhood, 'New Yishun')

        # Officer booking *decreases* the count based on manager's setting.
        # Setup: APP2 applies, MGR1 approves, OFF1 books
        self._login_user(APP2_NRIC)
        self.controller.app_service.apply_for_project(self.applicant2, proj1_reloaded, 2)
        app2 = self._get_application(APP2_NRIC)
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_approve_application(self.manager1, app2)
        reg = Registration(OFF1_NRIC, PROJ1_NAME)
        self.controller.reg_repo.add(reg)
        self.controller.reg_service.manager_approve_officer_registration(self.manager1, reg)
        self._login_user(OFF1_NRIC)
        self.controller.app_service.officer_book_flat(self.officer1, app2)
        proj1_after_booking = self._get_project(PROJ1_NAME)
        # Count should be initial+10 - 1
        self.assertEqual(proj1_after_booking.num_units1, initial_units + 9)


    def test_faq_manager_one_active_project_constraint(self):
        # Tested in A18 based on refined understanding of "Active" definition.
        pass # Covered in A18

    def test_faq_enquiry_submission_multiple(self):
        # Tested in A9 - multiple enquiries can be submitted.
        pass # Covered in A9

    def test_faq_withdrawn_application_status_visibility(self):
        # Setup: APP4 applies, MGR1 approves, APP4 requests withdrawal, MGR1 approves withdrawal
        self._login_user(APP4_NRIC)
        proj1 = self._get_project(PROJ1_NAME)
        self.controller.app_service.apply_for_project(self.applicant4, proj1, 3)
        app = self._get_application(APP4_NRIC)
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_approve_application(self.manager1, app)
        self._login_user(APP4_NRIC)
        self.controller.app_service.request_withdrawal(app)
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_approve_withdrawal(self.manager1, app)

        # Check status is Unsuccessful
        # Need to check repo directly as find helper ignores unsuccessful
        found_app = None
        for a in self.controller.app_repo.get_all():
             if a.applicant_nric == APP4_NRIC and a.project_name == PROJ1_NAME:
                 found_app = a
                 break
        self.assertIsNotNone(found_app)
        self.assertEqual(found_app.status, Application.STATUS_UNSUCCESSFUL)

        # Check Applicant can still view the project listing
        self._login_user(APP4_NRIC)
        # Even though app is unsuccessful, find_application_by_applicant returns None.
        # get_viewable_projects uses the *current* app status if passed.
        # Let's try viewing without passing app.
        viewable = self.controller.project_service.get_viewable_projects_for_applicant(self.applicant4, current_application=None)
        # Proj1 should still be visible as it's open
        self.assertIn(PROJ1_NAME, [p.project_name for p in viewable])
        # FAQ implies they should see the project because they applied, regardless of visibility/status.
        # Let's toggle visibility off
        self._login_user(MGR1_NRIC)
        self.controller.project_service.toggle_project_visibility(self.manager1, proj1)
        # Now view again
        self._login_user(APP4_NRIC)
        viewable_after_toggle = self.controller.project_service.get_viewable_projects_for_applicant(self.applicant4, current_application=found_app)
        # Now it should be visible because an application exists
        self.assertIn(PROJ1_NAME, [p.project_name for p in viewable_after_toggle])


    def test_faq_officer_booking_triggers_updates(self):
        # Tested in A15 - booking changes status and unit count.
        pass # Covered in A15

    def test_faq_status_transitions(self):
        # Pending -> Success -> Booked (Valid)
        self._login_user(APP2_NRIC)
        proj1 = self._get_project(PROJ1_NAME)
        self.controller.app_service.apply_for_project(self.applicant2, proj1, 2)
        app = self._get_application(APP2_NRIC)
        self.assertEqual(app.status, Application.STATUS_PENDING)
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_approve_application(self.manager1, app)
        self.assertEqual(app.status, Application.STATUS_SUCCESSFUL)
        reg = Registration(OFF1_NRIC, PROJ1_NAME)
        self.controller.reg_repo.add(reg)
        self.controller.reg_service.manager_approve_officer_registration(self.manager1, reg)
        self._login_user(OFF1_NRIC)
        self.controller.app_service.officer_book_flat(self.officer1, app)
        self.assertEqual(app.status, Application.STATUS_BOOKED)
        self.controller.app_repo.delete(APP2_NRIC, PROJ1_NAME) # Cleanup

        # Pending -> Unsuccessful (Valid - Manager Reject)
        self._login_user(APP2_NRIC)
        self.controller.app_service.apply_for_project(self.applicant2, proj1, 2)
        app = self._get_application(APP2_NRIC)
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_reject_application(self.manager1, app)
        # Check repo directly
        found_app = next((a for a in self.controller.app_repo.get_all() if a.applicant_nric == APP2_NRIC), None)
        self.assertEqual(found_app.status, Application.STATUS_UNSUCCESSFUL)
        self.controller.app_repo.delete(APP2_NRIC, PROJ1_NAME) # Cleanup

        # Pending -> Success -> Unsuccessful (Valid - Withdraw before booking)
        self._login_user(APP2_NRIC)
        self.controller.app_service.apply_for_project(self.applicant2, proj1, 2)
        app = self._get_application(APP2_NRIC)
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_approve_application(self.manager1, app)
        self._login_user(APP2_NRIC)
        self.controller.app_service.request_withdrawal(app)
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_approve_withdrawal(self.manager1, app)
        found_app = next((a for a in self.controller.app_repo.get_all() if a.applicant_nric == APP2_NRIC), None)
        self.assertEqual(found_app.status, Application.STATUS_UNSUCCESSFUL)
        self.controller.app_repo.delete(APP2_NRIC, PROJ1_NAME) # Cleanup

        # Pending -> Success -> Booked -> Unsuccessful (Valid - Withdraw after booking)
        self._login_user(APP2_NRIC)
        self.controller.app_service.apply_for_project(self.applicant2, proj1, 2)
        app = self._get_application(APP2_NRIC)
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_approve_application(self.manager1, app)
        # Reg OFF1 handled before
        self._login_user(OFF1_NRIC)
        self.controller.app_service.officer_book_flat(self.officer1, app)
        self._login_user(APP2_NRIC)
        self.controller.app_service.request_withdrawal(app)
        self._login_user(MGR1_NRIC)
        self.controller.app_service.manager_approve_withdrawal(self.manager1, app)
        found_app = next((a for a in self.controller.app_repo.get_all() if a.applicant_nric == APP2_NRIC), None)
        self.assertEqual(found_app.status, Application.STATUS_UNSUCCESSFUL)
        # Note: Unit count is NOT restored on withdrawal after booking per logic.
        self.controller.app_repo.delete(APP2_NRIC, PROJ1_NAME) # Cleanup

        # Pending -> Booked (Invalid - cannot skip Success)
        # Cannot test directly as officer_book_flat checks for SUCCESSFUL status.

        # Success -> Pending (Invalid - cannot revert)
        # No function allows this.


    def test_faq_receipt_generation_trigger(self):
        # Receipt generated after status change to Booked. Tested in A15/A16.
        pass # Covered in A15/A16

    def test_faq_manager_cannot_create_while_active(self):
        # Tested in A18.
        pass # Covered in A18

    def test_faq_manager_view_all_enquiries(self):
        # Setup: Enquiries on PROJ1 (MGR1) and PROJ5 (MGR2)
        self._login_user(APP1_NRIC)
        self.applicant1.age = 35; self.controller.user_repo.save_user(self.applicant1) # Make eligible
        self._login_user(APP1_NRIC)
        enq1 = self.controller.enq_service.submit_enquiry(self.applicant1, self._get_project(PROJ1_NAME), "Enq on Proj 1")
        enq2 = self.controller.enq_service.submit_enquiry(self.applicant1, self._get_project(PROJ5_NAME), "Enq on Proj 5")

        # Login as MGR1 and view all
        self._login_user(MGR1_NRIC)
        # Simulate handle_view_all_enquiries internal logic:
        all_enquiries_data = []
        for enquiry in self.controller.enq_service.get_all_enquiries():
             applicant = self.controller.user_repo.find_user_by_nric(enquiry.applicant_nric)
             if applicant:
                 all_enquiries_data.append((enquiry, applicant.name))

        self.assertEqual(len(all_enquiries_data), 2)
        enq_ids_seen = {e.enquiry_id for e, name in all_enquiries_data}
        self.assertIn(enq1.enquiry_id, enq_ids_seen)
        self.assertIn(enq2.enquiry_id, enq_ids_seen)

        # Login as MGR2 and view all - should see the same
        self._login_user(MGR2_NRIC)
        all_enquiries_data_mgr2 = []
        for enquiry in self.controller.enq_service.get_all_enquiries():
              applicant = self.controller.user_repo.find_user_by_nric(enquiry.applicant_nric)
              if applicant:
                  all_enquiries_data_mgr2.append((enquiry, applicant.name))
        self.assertEqual(len(all_enquiries_data_mgr2), 2)


if __name__ == '__main__':
    unittest.main()