# main5.test.py
import unittest
import os
import csv
import tempfile
import shutil
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

# Import everything from the main script
# Assuming main5.py is in the same directory or accessible via PYTHONPATH
from main5 import *

# --- Constants for Test Data ---
TEST_APPLICANT_NRIC = "S1234567A"
TEST_APPLICANT_PWD = "password"
TEST_OFFICER_NRIC = "S7654321B"
TEST_OFFICER_PWD = "password"
TEST_MANAGER_NRIC = "T1111111C"
TEST_MANAGER_PWD = "password"
TEST_MANAGER2_NRIC = "T2222222D" # Another manager for overlap tests
TEST_MANAGER2_PWD = "password"
TEST_OFFICER2_NRIC = "S9876543E" # Another officer
TEST_OFFICER2_PWD = "password"

TEST_PROJECT1_NAME = "Test Project Alpha"
TEST_PROJECT2_NAME = "Test Project Beta"
TEST_PROJECT3_NAME = "Past Project Gamma" # Project with past dates

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)
FUTURE_OPEN = TODAY + timedelta(days=10)
FUTURE_CLOSE = TODAY + timedelta(days=20)
PAST_OPEN = TODAY - timedelta(days=30)
PAST_CLOSE = TODAY - timedelta(days=20)
OVERLAP1_OPEN = TODAY + timedelta(days=5)
OVERLAP1_CLOSE = TODAY + timedelta(days=15)
OVERLAP2_OPEN = TODAY + timedelta(days=12)
OVERLAP2_CLOSE = TODAY + timedelta(days=22)
NON_OVERLAP_OPEN = TODAY + timedelta(days=30)
NON_OVERLAP_CLOSE = TODAY + timedelta(days=40)

# --- Helper Functions for Test Setup ---

def create_csv(filepath, headers, data_rows):
    """Creates a CSV file with given headers and data."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data_rows)

def setup_initial_csvs(temp_dir):
    """Creates initial empty or minimal CSV files in the temp directory."""
    paths = {
        'APPLICANT_CSV': os.path.join(temp_dir, 'ApplicantList.csv'),
        'OFFICER_CSV': os.path.join(temp_dir, 'OfficerList.csv'),
        'MANAGER_CSV': os.path.join(temp_dir, 'ManagerList.csv'),
        'PROJECT_CSV': os.path.join(temp_dir, 'ProjectList.csv'),
        'APPLICATION_CSV': os.path.join(temp_dir, 'ApplicationData.csv'),
        'REGISTRATION_CSV': os.path.join(temp_dir, 'RegistrationData.csv'),
        'ENQUIRY_CSV': os.path.join(temp_dir, 'EnquiryData.csv'),
    }

    # Applicant Data
    create_csv(paths['APPLICANT_CSV'],
               ['Name', 'NRIC', 'Age', 'Marital Status', 'Password'],
               [
                   ['Test Applicant', TEST_APPLICANT_NRIC, '36', 'Single', TEST_APPLICANT_PWD],
                   ['Young Applicant', 'S2345678F', '25', 'Single', 'password'],
                   ['Married Applicant', 'S3456789G', '22', 'Married', 'password'],
                   ['Old Married', 'S1122334H', '40', 'Married', 'password'],
               ])

    # Officer Data
    create_csv(paths['OFFICER_CSV'],
               ['Name', 'NRIC', 'Age', 'Marital Status', 'Password'],
               [
                   ['Test Officer', TEST_OFFICER_NRIC, '30', 'Married', TEST_OFFICER_PWD],
                   ['Test Officer 2', TEST_OFFICER2_NRIC, '32', 'Single', TEST_OFFICER2_PWD],
               ])

    # Manager Data
    create_csv(paths['MANAGER_CSV'],
               ['Name', 'NRIC', 'Age', 'Marital Status', 'Password'],
               [
                   ['Test Manager', TEST_MANAGER_NRIC, '45', 'Married', TEST_MANAGER_PWD],
                   ['Test Manager 2', TEST_MANAGER2_NRIC, '46', 'Married', TEST_MANAGER2_PWD],
                ])

    # Project Data (Start with one active, one inactive, one past)
    create_csv(paths['PROJECT_CSV'],
               [ 'Project Name', 'Neighborhood', 'Type 1', 'Number of units for Type 1',
                 'Selling price for Type 1', 'Type 2', 'Number of units for Type 2',
                 'Selling price for Type 2', 'Application opening date',
                 'Application closing date', 'Manager', 'Officer Slot', 'Officer', 'Visibility'],
                [
                    [TEST_PROJECT1_NAME, 'Yishun', '2-Room', '10', '100000', '3-Room', '5', '200000',
                     format_date(TODAY), format_date(FUTURE_CLOSE), TEST_MANAGER_NRIC, '2', '', 'True'],
                    [TEST_PROJECT2_NAME, 'Boon Lay', '2-Room', '8', '90000', '3-Room', '12', '180000',
                     format_date(FUTURE_OPEN), format_date(FUTURE_CLOSE + timedelta(days=10)), TEST_MANAGER_NRIC, '3', '', 'False'], # Future & Invisible
                    [TEST_PROJECT3_NAME, 'Tampines', '2-Room', '0', '80000', '3-Room', '0', '170000',
                     format_date(PAST_OPEN), format_date(PAST_CLOSE), TEST_MANAGER2_NRIC, '1', '', 'True'], # Past
                ])

    # Application Data (Start empty)
    create_csv(paths['APPLICATION_CSV'],
               ['ApplicantNRIC', 'ProjectName', 'FlatType', 'Status', 'RequestWithdrawal'],
               [])

    # Registration Data (Start empty)
    create_csv(paths['REGISTRATION_CSV'],
               ['OfficerNRIC', 'ProjectName', 'Status'],
               [])

    # Enquiry Data (Start empty)
    create_csv(paths['ENQUIRY_CSV'],
                ['EnquiryID', 'ApplicantNRIC', 'ProjectName', 'Text', 'Reply'],
                [])

    return paths

# --- Base Test Class for Setup/Teardown ---

class BaseBTOIntegrationTest(unittest.TestCase):
    temp_dir = None
    original_paths = {}
    patched_paths = {}

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        print(f"Created temp dir: {cls.temp_dir}")

        # Store original paths
        cls.original_paths = {
            'APPLICANT_CSV': APPLICANT_CSV, 'OFFICER_CSV': OFFICER_CSV, 'MANAGER_CSV': MANAGER_CSV,
            'PROJECT_CSV': PROJECT_CSV, 'APPLICATION_CSV': APPLICATION_CSV,
            'REGISTRATION_CSV': REGISTRATION_CSV, 'ENQUIRY_CSV': ENQUIRY_CSV
        }

        # Create and get paths for temp CSVs
        cls.patched_paths = setup_initial_csvs(cls.temp_dir)

        # Patch the global constants IN THE CONTEXT OF THE IMPORTED MODULE (main5)
        cls.patchers = []
        for key, temp_path in cls.patched_paths.items():
            patcher = patch(f'main5.{key}', temp_path)
            cls.patchers.append(patcher)
            patcher.start()

        # Initialize services AFTER patching paths
        cls.user_repo = UserRepository()
        cls.project_repo = ProjectRepository()
        cls.app_repo = ApplicationRepository()
        cls.reg_repo = RegistrationRepository()
        cls.enq_repo = EnquiryRepository() # Re-init to get correct next_id

        cls.project_service = ProjectService(cls.project_repo, cls.reg_repo)
        cls.reg_service = RegistrationService(cls.reg_repo, cls.project_service, cls.app_repo)
        cls.app_service = ApplicationService(cls.app_repo, cls.project_service, cls.reg_service)
        cls.enq_service = EnquiryService(cls.enq_repo, cls.project_service, cls.reg_service, cls.user_repo)
        cls.auth_service = AuthService(cls.user_repo)


    @classmethod
    def tearDownClass(cls):
        # Stop patchers
        for patcher in cls.patchers:
            patcher.stop()

        # Remove temporary directory
        if cls.temp_dir and os.path.exists(cls.temp_dir):
            print(f"Removing temp dir: {cls.temp_dir}")
            shutil.rmtree(cls.temp_dir)
        cls.temp_dir = None

    def setUp(self):
        """ Reset data between tests by reloading from initial files """
        # It might be faster to just re-initialize repositories if load is quick
        # Or, re-copy initial files if tests modify them heavily
        # For simplicity here, we'll re-initialize the repositories
        # This assumes BaseRepository._load_data() correctly re-reads the patched files
        try:
            # print(f"Setting up test: {self.id()}") # Uncomment for debugging test order/setup
            self.user_repo = UserRepository()
            self.project_repo = ProjectRepository(csv_file=self.patched_paths['PROJECT_CSV'])
            self.app_repo = ApplicationRepository(csv_file=self.patched_paths['APPLICATION_CSV'])
            self.reg_repo = RegistrationRepository(csv_file=self.patched_paths['REGISTRATION_CSV'])
            # Re-init EnquiryRepo to reset next_id based on current file state
            self.enq_repo = EnquiryRepository(csv_file=self.patched_paths['ENQUIRY_CSV'])

            self.project_service = ProjectService(self.project_repo, self.reg_repo)
            self.reg_service = RegistrationService(self.reg_repo, self.project_service, self.app_repo)
            self.app_service = ApplicationService(self.app_repo, self.project_service, self.reg_service)
            self.enq_service = EnquiryService(self.enq_repo, self.project_service, self.reg_service, self.user_repo)
            self.auth_service = AuthService(self.user_repo)

            # Find users for convenience in tests
            self.applicant = self.user_repo.find_user_by_nric(TEST_APPLICANT_NRIC)
            self.officer = self.user_repo.find_user_by_nric(TEST_OFFICER_NRIC)
            self.officer2 = self.user_repo.find_user_by_nric(TEST_OFFICER2_NRIC)
            self.manager = self.user_repo.find_user_by_nric(TEST_MANAGER_NRIC)
            self.manager2 = self.user_repo.find_user_by_nric(TEST_MANAGER2_NRIC)
            self.young_applicant = self.user_repo.find_user_by_nric("S2345678F")
            self.married_applicant = self.user_repo.find_user_by_nric("S3456789G")
            self.old_married_applicant = self.user_repo.find_user_by_nric("S1122334H")

            # Find projects for convenience
            self.project1 = self.project_service.find_project_by_name(TEST_PROJECT1_NAME)
            self.project2 = self.project_service.find_project_by_name(TEST_PROJECT2_NAME)
            self.project3 = self.project_service.find_project_by_name(TEST_PROJECT3_NAME)
        except Exception as e:
             # If setup fails, make sure the test fails clearly
             self.fail(f"Test setUp failed: {e}")

    # --- Test Cases ---

    # --- Authentication Tests ---
    def test_login_success(self):
        user = self.auth_service.login(TEST_APPLICANT_NRIC, TEST_APPLICANT_PWD)
        self.assertIsInstance(user, Applicant)
        self.assertEqual(user.nric, TEST_APPLICANT_NRIC)

        user = self.auth_service.login(TEST_OFFICER_NRIC, TEST_OFFICER_PWD)
        self.assertIsInstance(user, HDBOfficer)
        self.assertEqual(user.nric, TEST_OFFICER_NRIC)

        user = self.auth_service.login(TEST_MANAGER_NRIC, TEST_MANAGER_PWD)
        self.assertIsInstance(user, HDBManager)
        self.assertEqual(user.nric, TEST_MANAGER_NRIC)

    def test_login_fail_wrong_password(self):
        with self.assertRaisesRegex(OperationError, "Incorrect password"):
            self.auth_service.login(TEST_APPLICANT_NRIC, "wrongpassword")

    def test_login_fail_wrong_nric(self):
        with self.assertRaisesRegex(OperationError, "NRIC not found"):
            self.auth_service.login("S0000000Z", TEST_APPLICANT_PWD)

    def test_login_fail_invalid_nric_format(self):
        with self.assertRaisesRegex(OperationError, "Invalid NRIC format"):
            self.auth_service.login("InvalidNRIC", TEST_APPLICANT_PWD)

    def test_change_password_success(self):
        new_password = "newpassword123"
        self.auth_service.change_password(self.applicant, new_password)
        # Verify by trying to log in with the new password
        user = self.auth_service.login(TEST_APPLICANT_NRIC, new_password)
        self.assertEqual(user.nric, TEST_APPLICANT_NRIC)
        # Verify old password fails
        with self.assertRaisesRegex(OperationError, "Incorrect password"):
            self.auth_service.login(TEST_APPLICANT_NRIC, TEST_APPLICANT_PWD)

    def test_change_password_fail_empty(self):
         with self.assertRaisesRegex(OperationError, "Password cannot be empty"):
             self.auth_service.change_password(self.applicant, "")

    # --- Project Tests ---
    def test_project_currently_active(self):
        self.assertTrue(self.project1.is_currently_active()) # Visible, date range includes today
        self.assertFalse(self.project2.is_currently_active()) # Invisible
        self.project2.visibility = True # Make visible
        self.assertFalse(self.project2.is_currently_active()) # Still false, future date
        self.project2.visibility = False # Reset
        self.assertFalse(self.project3.is_currently_active()) # Past date

    def test_get_flat_details(self):
        units, price = self.project1.get_flat_details(2)
        self.assertEqual(units, 10)
        self.assertEqual(price, 100000)
        units, price = self.project1.get_flat_details(3)
        self.assertEqual(units, 5)
        self.assertEqual(price, 200000)
        units, price = self.project1.get_flat_details(4) # Invalid type
        self.assertEqual(units, 0)
        self.assertEqual(price, 0)

    def test_decrease_unit_count(self):
        self.assertTrue(self.project1.decrease_unit_count(2))
        self.assertEqual(self.project1.num_units1, 9)
        self.assertTrue(self.project1.decrease_unit_count(3))
        self.assertEqual(self.project1.num_units2, 4)
        # Decrease till zero
        for _ in range(4): self.assertTrue(self.project1.decrease_unit_count(3))
        self.assertEqual(self.project1.num_units2, 0)
        self.assertFalse(self.project1.decrease_unit_count(3)) # Cannot decrease further

    def test_can_add_officer(self):
        self.assertTrue(self.project1.can_add_officer()) # Slot 2, 0 assigned
        self.project1.officer_nrics.append("S111")
        self.assertTrue(self.project1.can_add_officer()) # Slot 2, 1 assigned
        self.project1.officer_nrics.append("S222")
        self.assertFalse(self.project1.can_add_officer()) # Slot 2, 2 assigned

    # --- Applicant Flow Tests ---
    def test_applicant_view_projects_eligibility(self):
        # Young single (<35) - cannot view any project based on age/marital alone
        # But project1 is active, they meet the age/marital status for 2-room, so should see project1
        # Note: Original requirement implies view filtering first, then flat eligibility inside apply
        # Revised interpretation: Viewable if *potentially* eligible for *any* flat type in an active project
        # Simplified eligibility for viewing: Just check if project is active and visible
        # More strict interpretation (based on FAQ Q2 for Single): Hide 3-room details
        # The current `get_viewable_projects_for_applicant` implements a mix. Let's test that logic.

        # Test Applicant (Single, 36) - Can view active/visible Project 1
        viewable = self.project_service.get_viewable_projects_for_applicant(self.applicant)
        self.assertIn(self.project1, viewable)
        self.assertNotIn(self.project2, viewable) # Invisible / Future
        self.assertNotIn(self.project3, viewable) # Past

        # Young Applicant (Single, 25) - Cannot apply, but can they view?
        # Based on code logic: No, because age < 35 for single
        viewable_young = self.project_service.get_viewable_projects_for_applicant(self.young_applicant)
        self.assertEqual(len(viewable_young), 0) # Cannot view any project

        # Married Applicant (Married, 22) - Eligible for 2 or 3 room in active projects
        viewable_married = self.project_service.get_viewable_projects_for_applicant(self.married_applicant)
        self.assertIn(self.project1, viewable_married)
        self.assertNotIn(self.project2, viewable_married)
        self.assertNotIn(self.project3, viewable_married)

    def test_applicant_apply_success_single(self):
        # Applicant (Single, 36) applies for 2-Room in Project 1
        application = self.app_service.apply_for_project(self.applicant, self.project1, 2)
        self.assertIsInstance(application, Application)
        self.assertEqual(application.applicant_nric, self.applicant.nric)
        self.assertEqual(application.project_name, self.project1.project_name)
        self.assertEqual(application.flat_type, 2)
        self.assertEqual(application.status, Application.STATUS_PENDING)
        # Verify application exists
        self.assertIsNotNone(self.app_service.find_application_by_applicant(self.applicant.nric))

    def test_applicant_apply_success_married_3_room(self):
        # Married Applicant (Married, 22) applies for 3-Room in Project 1
        application = self.app_service.apply_for_project(self.married_applicant, self.project1, 3)
        self.assertIsInstance(application, Application)
        self.assertEqual(application.flat_type, 3)
        self.assertEqual(application.status, Application.STATUS_PENDING)

    def test_applicant_apply_fail_single_3_room(self):
        # Applicant (Single, 36) tries to apply for 3-Room
        with self.assertRaisesRegex(OperationError, "Single applicants can only apply for 2-Room flats"):
            self.app_service.apply_for_project(self.applicant, self.project1, 3)

    def test_applicant_apply_fail_married_underage(self):
        # Make married applicant underage temporarily
        original_age = self.married_applicant.age
        self.married_applicant.age = 20
        with self.assertRaisesRegex(OperationError, "Married applicants must be at least 21 years old"):
            self.app_service.apply_for_project(self.married_applicant, self.project1, 2)
        self.married_applicant.age = original_age # Restore age

    def test_applicant_apply_fail_single_underage(self):
        # Young Applicant (Single, 25) tries to apply
        with self.assertRaisesRegex(OperationError, "Single applicants must be at least 35 years old"):
            self.app_service.apply_for_project(self.young_applicant, self.project1, 2)

    def test_applicant_apply_fail_already_applied(self):
        self.app_service.apply_for_project(self.applicant, self.project1, 2) # First application
        with self.assertRaisesRegex(OperationError, "You already have an active BTO application"):
            # Try applying again (even to a different project, if one existed)
            self.app_service.apply_for_project(self.applicant, self.project1, 2)

    def test_applicant_apply_fail_project_inactive(self):
        with self.assertRaisesRegex(OperationError, "Project is not currently open for applications"):
            self.app_service.apply_for_project(self.applicant, self.project3, 2) # Apply for past project

    def test_applicant_apply_fail_no_units(self):
        self.project1.num_units1 = 0 # No 2-room units
        self.project_repo.update(self.project1) # Save change
        self.project1 = self.project_service.find_project_by_name(TEST_PROJECT1_NAME) # Re-fetch

        with self.assertRaisesRegex(OperationError, "No 2-Room units available"):
           self.app_service.apply_for_project(self.applicant, self.project1, 2)

    def test_applicant_apply_fail_manager_cannot_apply(self):
        # FAQ: Cannot apply for any BTO project as an Applicant.
        with self.assertRaisesRegex(OperationError, "HDB Managers cannot apply for BTO projects"):
            self.app_service.apply_for_project(self.manager, self.project1, 2)

    def test_applicant_view_own_application(self):
        # No application initially
        self.assertIsNone(self.app_service.find_application_by_applicant(self.applicant.nric))
        # Apply
        app = self.app_service.apply_for_project(self.applicant, self.project1, 2)
        # View
        found_app = self.app_service.find_application_by_applicant(self.applicant.nric)
        self.assertEqual(app.applicant_nric, found_app.applicant_nric)
        self.assertEqual(app.project_name, found_app.project_name)

    def test_applicant_request_withdrawal_pending(self):
        app = self.app_service.apply_for_project(self.applicant, self.project1, 2)
        self.assertFalse(app.request_withdrawal)
        self.app_service.request_withdrawal(app)
        # Re-fetch application to check updated state
        updated_app = self.app_service.find_application_by_applicant(self.applicant.nric)
        self.assertTrue(updated_app.request_withdrawal)

    def test_applicant_request_withdrawal_fail_unsuccessful(self):
        app = self.app_service.apply_for_project(self.applicant, self.project1, 2)
        app.status = Application.STATUS_UNSUCCESSFUL
        self.app_repo.update(app)
        updated_app = self.app_service.find_application_by_applicant(self.applicant.nric)
        with self.assertRaisesRegex(OperationError, "Cannot request withdrawal.*status 'UNSUCCESSFUL'"):
            self.app_service.request_withdrawal(updated_app)

    def test_applicant_request_withdrawal_fail_already_requested(self):
        app = self.app_service.apply_for_project(self.applicant, self.project1, 2)
        self.app_service.request_withdrawal(app)
        updated_app = self.app_service.find_application_by_applicant(self.applicant.nric)
        with self.assertRaisesRegex(OperationError, "Withdrawal already requested"):
            self.app_service.request_withdrawal(updated_app)

    def test_applicant_submit_view_edit_delete_enquiry(self):
        # Submit
        enq = self.enq_service.submit_enquiry(self.applicant, self.project1, "Test enquiry text?")
        self.assertIsNotNone(enq)
        self.assertGreater(enq.enquiry_id, 0)
        self.assertEqual(enq.applicant_nric, self.applicant.nric)
        self.assertEqual(enq.project_name, self.project1.project_name)
        self.assertEqual(enq.text, "Test enquiry text?")
        self.assertEqual(enq.reply, "")

        # View
        my_enquiries = self.enq_service.get_enquiries_by_applicant(self.applicant.nric)
        self.assertEqual(len(my_enquiries), 1)
        self.assertEqual(my_enquiries[0].enquiry_id, enq.enquiry_id)

        # Edit
        self.enq_service.edit_enquiry(self.applicant, enq, "Updated enquiry text.")
        edited_enq = self.enq_service.find_enquiry_by_id(enq.enquiry_id)
        self.assertEqual(edited_enq.text, "Updated enquiry text.")

        # Delete
        self.enq_service.delete_enquiry(self.applicant, edited_enq)
        deleted_enq = self.enq_service.find_enquiry_by_id(enq.enquiry_id)
        self.assertIsNone(deleted_enq)

    def test_applicant_enquiry_fail_edit_delete_replied(self):
        enq = self.enq_service.submit_enquiry(self.applicant, self.project1, "Enquiry to be replied")
        # Manager replies
        self.enq_service.reply_to_enquiry(self.manager, enq, "Manager reply.")
        replied_enq = self.enq_service.find_enquiry_by_id(enq.enquiry_id)

        # Cannot edit replied
        with self.assertRaisesRegex(OperationError, "Cannot edit an enquiry that has already been replied to"):
            self.enq_service.edit_enquiry(self.applicant, replied_enq, "Trying to edit replied.")

        # Cannot delete replied
        with self.assertRaisesRegex(OperationError, "Cannot delete an enquiry that has already been replied to"):
            self.enq_service.delete_enquiry(self.applicant, replied_enq)

    # --- Officer Flow Tests ---
    def test_officer_register_project_success(self):
        # Officer registers for Project 3 (managed by Manager 2)
        reg = self.reg_service.officer_register_for_project(self.officer, self.project3)
        self.assertIsInstance(reg, Registration)
        self.assertEqual(reg.officer_nric, self.officer.nric)
        self.assertEqual(reg.project_name, self.project3.project_name)
        self.assertEqual(reg.status, Registration.STATUS_PENDING)
        # Verify registration exists
        found_reg = self.reg_service.find_registration(self.officer.nric, self.project3.project_name)
        self.assertIsNotNone(found_reg)

    def test_officer_register_fail_already_registered(self):
        self.reg_service.officer_register_for_project(self.officer, self.project3)
        with self.assertRaisesRegex(OperationError, "already submitted a registration"):
            self.reg_service.officer_register_for_project(self.officer, self.project3)

    def test_officer_register_fail_is_applicant_for_project(self):
        # Officer applies for project 1 first
        self.app_service.apply_for_project(self.officer, self.project1, 2)
        # Then tries to register as officer for the same project
        with self.assertRaisesRegex(OperationError, "cannot register as an officer for a project you have applied for"):
            self.reg_service.officer_register_for_project(self.officer, self.project1)

    def test_officer_register_fail_is_manager_for_project(self):
        # Manager tries to register as officer for their own project
        with self.assertRaisesRegex(OperationError, "Managers cannot register as officers for their own projects"):
             self.reg_service.officer_register_for_project(self.manager, self.project1) # manager is technically an officer type user in code

    def test_officer_register_fail_overlap_approved(self):
        # 1. Create two overlapping projects managed by different managers
        proj_overlap1 = self.project_service.create_project(self.manager, "Overlap A", "Area A", 5, 1, 5, 1, OVERLAP1_OPEN, OVERLAP1_CLOSE, 2)
        proj_overlap2 = self.project_service.create_project(self.manager2, "Overlap B", "Area B", 5, 1, 5, 1, OVERLAP2_OPEN, OVERLAP2_CLOSE, 2)

        # 2. Officer registers for first project
        reg1 = self.reg_service.officer_register_for_project(self.officer, proj_overlap1)
        # 3. Manager approves registration
        self.reg_service.manager_approve_officer_registration(self.manager, reg1)

        # 4. Officer tries to register for second (overlapping) project
        with self.assertRaisesRegex(OperationError, "already an approved officer for another project.*overlapping application period"):
            self.reg_service.officer_register_for_project(self.officer, proj_overlap2)

    def test_officer_apply_fail_is_approved_officer_for_project(self):
        # 1. Officer registers for Project 3
        reg = self.reg_service.officer_register_for_project(self.officer, self.project3)
        # 2. Manager 2 approves
        self.reg_service.manager_approve_officer_registration(self.manager2, reg)
        # 3. Officer tries to apply for Project 3 (which they now handle)
        with self.assertRaisesRegex(OperationError, "cannot apply for a project you are an approved officer for"):
            self.app_service.apply_for_project(self.officer, self.project3, 2) # Officer is married, >21, eligible otherwise

    def test_officer_apply_for_other_project_success(self):
        # Officer can apply for project 1 (managed by manager 1, officer not registered for it)
        app = self.app_service.apply_for_project(self.officer, self.project1, 2)
        self.assertIsNotNone(app)
        self.assertEqual(app.applicant_nric, self.officer.nric)

    def test_officer_view_handled_projects(self):
        # Initially, officer handles no projects
        handled = self.project_service.get_handled_projects_for_officer(self.officer.nric)
        self.assertEqual(len(handled), 0)

        # Register and approve for project 3
        reg = self.reg_service.officer_register_for_project(self.officer, self.project3)
        self.reg_service.manager_approve_officer_registration(self.manager2, reg)

        # Now should handle project 3
        handled = self.project_service.get_handled_projects_for_officer(self.officer.nric)
        self.assertEqual(len(handled), 1)
        self.assertEqual(handled[0].project_name, self.project3.project_name)

        # Also check direct assignment (although approval adds automatically now)
        self.project1.officer_nrics.append(self.officer.nric)
        self.project_repo.update(self.project1)
        handled = self.project_service.get_handled_projects_for_officer(self.officer.nric)
        self.assertEqual(len(handled), 2)
        self.assertIn(self.project1.project_name, [p.project_name for p in handled])
        self.assertIn(self.project3.project_name, [p.project_name for p in handled])


    def test_officer_reply_enquiry_handled_project(self):
        # Setup: Make officer handle project 1
        reg = self.reg_service.officer_register_for_project(self.officer, self.project1)
        self.reg_service.manager_approve_officer_registration(self.manager, reg)
        # Applicant submits enquiry for project 1
        enq = self.enq_service.submit_enquiry(self.applicant, self.project1, "Question for officer?")
        # Officer replies
        self.enq_service.reply_to_enquiry(self.officer, enq, "Officer reply.")
        replied_enq = self.enq_service.find_enquiry_by_id(enq.enquiry_id)
        self.assertIn("[Officer - Test Officer]: Officer reply.", replied_enq.reply)

    def test_officer_reply_enquiry_fail_not_handled(self):
        # Applicant submits enquiry for project 1
        enq = self.enq_service.submit_enquiry(self.applicant, self.project1, "Question?")
        # Officer (who doesn't handle project 1 yet) tries to reply
        with self.assertRaisesRegex(OperationError, "Officers can only reply to enquiries for projects they handle"):
            self.enq_service.reply_to_enquiry(self.officer, enq, "Unauthorized reply.")

    def test_officer_book_flat_success(self):
        # Setup:
        # 1. Applicant applies for project 1
        app = self.app_service.apply_for_project(self.applicant, self.project1, 2)
        # 2. Manager approves application
        self.app_service.manager_approve_application(self.manager, app)
        # 3. Officer registers and gets approved for project 1
        reg = self.reg_service.officer_register_for_project(self.officer, self.project1)
        self.reg_service.manager_approve_officer_registration(self.manager, reg)

        # Get updated application (status should be SUCCESSFUL)
        app_successful = self.app_service.find_application_by_applicant(self.applicant.nric)
        self.assertEqual(app_successful.status, Application.STATUS_SUCCESSFUL)
        initial_units = self.project1.num_units1

        # Action: Officer books flat
        updated_project = self.app_service.officer_book_flat(self.officer, app_successful)

        # Verify:
        # 1. Application status is BOOKED
        app_booked = self.app_service.find_application_by_applicant(self.applicant.nric)
        self.assertEqual(app_booked.status, Application.STATUS_BOOKED)
        # 2. Project unit count decreased
        self.assertEqual(updated_project.num_units1, initial_units - 1)
        # 3. Project state saved
        reloaded_project = self.project_service.find_project_by_name(self.project1.project_name)
        self.assertEqual(reloaded_project.num_units1, initial_units - 1)

    def test_officer_book_flat_fail_not_handled(self):
        app = self.app_service.apply_for_project(self.applicant, self.project1, 2)
        self.app_service.manager_approve_application(self.manager, app)
        app_successful = self.app_service.find_application_by_applicant(self.applicant.nric)
        # Officer does NOT handle project 1
        with self.assertRaisesRegex(OperationError, "You do not handle the project for this application"):
             self.app_service.officer_book_flat(self.officer, app_successful)

    def test_officer_book_flat_fail_app_not_successful(self):
        app = self.app_service.apply_for_project(self.applicant, self.project1, 2) # Status is PENDING
        reg = self.reg_service.officer_register_for_project(self.officer, self.project1)
        self.reg_service.manager_approve_officer_registration(self.manager, reg)
        with self.assertRaisesRegex(OperationError, "Application status must be 'SUCCESSFUL'"):
            self.app_service.officer_book_flat(self.officer, app)

    def test_officer_book_flat_fail_no_units_at_booking(self):
        app = self.app_service.apply_for_project(self.applicant, self.project1, 2)
        self.app_service.manager_approve_application(self.manager, app)
        reg = self.reg_service.officer_register_for_project(self.officer, self.project1)
        self.reg_service.manager_approve_officer_registration(self.manager, reg)
        app_successful = self.app_service.find_application_by_applicant(self.applicant.nric)

        # Make units zero just before booking
        self.project1.num_units1 = 0
        self.project_repo.update(self.project1)
        self.project1 = self.project_service.find_project_by_name(TEST_PROJECT1_NAME) # Re-fetch

        with self.assertRaisesRegex(OperationError, "Booking failed: No 2-Room units available anymore"):
            self.app_service.officer_book_flat(self.officer, app_successful)

        # Verify app status changed to UNSUCCESSFUL
        app_updated = self.app_service.find_application_by_applicant(self.applicant.nric)
        self.assertEqual(app_updated.status, Application.STATUS_UNSUCCESSFUL)


    def test_officer_generate_receipt_success(self):
        # Full flow: apply, approve, book
        app = self.app_service.apply_for_project(self.applicant, self.project1, 2)
        self.app_service.manager_approve_application(self.manager, app)
        reg = self.reg_service.officer_register_for_project(self.officer, self.project1)
        self.reg_service.manager_approve_officer_registration(self.manager, reg)
        app_successful = self.app_service.find_application_by_applicant(self.applicant.nric)
        self.app_service.officer_book_flat(self.officer, app_successful)

        # Generate receipt requires re-fetching the app and project inside the controller usually
        # Here we simulate the data preparation
        app_booked = self.app_service.find_application_by_applicant(self.applicant.nric)
        project = self.project_service.find_project_by_name(app_booked.project_name)
        receipt_data = self.controller._prepare_receipt_data(app_booked, project, self.applicant) # Using hypothetical controller method structure

        self.assertEqual(receipt_data["NRIC"], self.applicant.nric)
        self.assertEqual(receipt_data["Project Name"], self.project1.project_name)
        self.assertEqual(receipt_data["Flat Type Booked"], "2-Room")


    def test_officer_generate_receipt_fail_app_not_booked(self):
        # Setup: Apply and approve, but don't book
        app = self.app_service.apply_for_project(self.applicant, self.project1, 2)
        self.app_service.manager_approve_application(self.manager, app)
        reg = self.reg_service.officer_register_for_project(self.officer, self.project1)
        self.reg_service.manager_approve_officer_registration(self.manager, reg)

        # Attempt to generate receipt (simulate controller finding no booked app)
        booked_app = None
        for a in self.app_repo.get_all():
            if a.applicant_nric == self.applicant.nric and a.status == Application.STATUS_BOOKED:
                booked_app = a
                break
        self.assertIsNone(booked_app)
        # In real controller, would raise OperationError("No booked application found...")

    # --- Manager Flow Tests ---
    def test_manager_create_project_success(self):
        name = "New Manager Project"
        proj = self.project_service.create_project(
            self.manager, name, "Jurong", 10, 110000, 20, 210000,
            FUTURE_OPEN, FUTURE_CLOSE, 5
        )
        self.assertIsNotNone(proj)
        found_proj = self.project_service.find_project_by_name(name)
        self.assertIsNotNone(found_proj)
        self.assertEqual(found_proj.manager_nric, self.manager.nric)

    def test_manager_create_project_fail_name_exists(self):
        with self.assertRaisesRegex(OperationError, "Project name.*already exists"):
            self.project_service.create_project(
                self.manager, TEST_PROJECT1_NAME, "Jurong", 10, 1, 20, 1,
                FUTURE_OPEN, FUTURE_CLOSE, 5
            )

    def test_manager_create_project_fail_invalid_dates(self):
        with self.assertRaisesRegex(OperationError, "Invalid opening or closing date"):
            self.project_service.create_project(
                self.manager, "DateFail", "Area", 1, 1, 1, 1,
                FUTURE_CLOSE, FUTURE_OPEN, 1 # Close date before open date
            )
        with self.assertRaisesRegex(OperationError, "Closing date cannot be in the past"):
            self.project_service.create_project(
                self.manager, "DateFailPast", "Area", 1, 1, 1, 1,
                PAST_OPEN, PAST_CLOSE, 1 # Closing date is past
            )

    def test_manager_create_project_fail_overlap(self):
        # Project 1 (FUTURE_CLOSE) is active for manager 1
        # Try creating another project overlapping with project 1's dates
        with self.assertRaisesRegex(OperationError, "Manager already handles an active project.*during this period"):
            self.project_service.create_project(
                self.manager, "Overlap Fail", "Area", 1, 1, 1, 1,
                OVERLAP1_OPEN, OVERLAP1_CLOSE, 1 # Overlaps with project 1's period
            )
        # Try creating non-overlapping project - should succeed
        proj_ok = self.project_service.create_project(
                self.manager, "NonOverlap OK", "Area", 1, 1, 1, 1,
                NON_OVERLAP_OPEN, NON_OVERLAP_CLOSE, 1 # Does not overlap
            )
        self.assertIsNotNone(proj_ok)


    def test_manager_edit_project_success(self):
        updates = {'neighborhood': 'New Yishun', 'p1': 105000}
        self.project_service.edit_project(self.manager, self.project1, updates)
        edited_proj = self.project_service.find_project_by_name(TEST_PROJECT1_NAME)
        self.assertEqual(edited_proj.neighborhood, 'New Yishun')
        self.assertEqual(edited_proj.price1, 105000)
        self.assertEqual(edited_proj.num_units1, 10) # Unchanged

    def test_manager_edit_project_fail_not_owner(self):
        with self.assertRaisesRegex(OperationError, "You can only edit projects you manage"):
            self.project_service.edit_project(self.manager2, self.project1, {'n1': 5})

    def test_manager_edit_project_fail_reduce_slots_below_assigned(self):
        # Assign officer first
        self.project1.officer_nrics.append(TEST_OFFICER_NRIC)
        self.project_repo.update(self.project1)
        self.project1 = self.project_service.find_project_by_name(TEST_PROJECT1_NAME) # Re-fetch
        # Try reducing slots to 0
        with self.assertRaisesRegex(OperationError, "Cannot reduce slots below current number of assigned officers"):
             self.project_service.edit_project(self.manager, self.project1, {'officerSlot': 0})

    def test_manager_edit_project_fail_date_overlap(self):
        # Create another project for manager 1
        proj_non_overlap = self.project_service.create_project(
            self.manager, "NonOverlap", "Area", 1, 1, 1, 1, NON_OVERLAP_OPEN, NON_OVERLAP_CLOSE, 1
            )
        # Try editing project 1's dates to overlap with proj_non_overlap
        with self.assertRaisesRegex(OperationError, "Edited dates overlap with another active project"):
            self.project_service.edit_project(
                self.manager, self.project1, {'openDate': NON_OVERLAP_OPEN, 'closeDate': NON_OVERLAP_CLOSE}
            )

    def test_manager_delete_project_success(self):
        proj_name = self.project1.project_name
        self.project_service.delete_project(self.manager, self.project1)
        self.assertIsNone(self.project_service.find_project_by_name(proj_name))

    def test_manager_delete_project_fail_not_owner(self):
        with self.assertRaisesRegex(OperationError, "You can only delete projects you manage"):
             self.project_service.delete_project(self.manager2, self.project1)

    def test_manager_toggle_visibility(self):
        self.assertTrue(self.project1.visibility)
        status = self.project_service.toggle_project_visibility(self.manager, self.project1)
        self.assertEqual(status, "OFF")
        toggled_proj = self.project_service.find_project_by_name(self.project1.project_name)
        self.assertFalse(toggled_proj.visibility)
        status = self.project_service.toggle_project_visibility(self.manager, toggled_proj)
        self.assertEqual(status, "ON")
        toggled_proj2 = self.project_service.find_project_by_name(self.project1.project_name)
        self.assertTrue(toggled_proj2.visibility)

    def test_manager_approve_reject_officer_registration(self):
        # Officer registers for project 1
        reg = self.reg_service.officer_register_for_project(self.officer, self.project1)
        self.assertEqual(reg.status, Registration.STATUS_PENDING)
        initial_slots = self.project1.officer_slot
        initial_assigned = len(self.project1.officer_nrics)

        # Manager approves
        self.reg_service.manager_approve_officer_registration(self.manager, reg)
        approved_reg = self.reg_service.find_registration(self.officer.nric, self.project1.project_name)
        self.assertEqual(approved_reg.status, Registration.STATUS_APPROVED)
        updated_proj = self.project_service.find_project_by_name(self.project1.project_name)
        self.assertEqual(len(updated_proj.officer_nrics), initial_assigned + 1)
        self.assertIn(self.officer.nric, updated_proj.officer_nrics)

        # --- Test Rejection ---
        # Officer 2 registers for project 1
        reg2 = self.reg_service.officer_register_for_project(self.officer2, self.project1)
        initial_assigned_before_reject = len(updated_proj.officer_nrics)
        # Manager rejects
        self.reg_service.manager_reject_officer_registration(self.manager, reg2)
        rejected_reg = self.reg_service.find_registration(self.officer2.nric, self.project1.project_name)
        self.assertEqual(rejected_reg.status, Registration.STATUS_REJECTED)
        proj_after_reject = self.project_service.find_project_by_name(self.project1.project_name)
        self.assertEqual(len(proj_after_reject.officer_nrics), initial_assigned_before_reject) # No change
        self.assertNotIn(self.officer2.nric, proj_after_reject.officer_nrics)

    def test_manager_approve_registration_fail_no_slots(self):
        # Set project 1 slots to 0
        self.project1.officer_slot = 0
        self.project_repo.update(self.project1)
        self.project1 = self.project_service.find_project_by_name(TEST_PROJECT1_NAME) # Re-fetch

        reg = self.reg_service.officer_register_for_project(self.officer, self.project1)
        with self.assertRaisesRegex(OperationError, "No available officer slots"):
            self.reg_service.manager_approve_officer_registration(self.manager, reg)

    def test_manager_approve_reject_application(self):
        # Applicant applies
        app = self.app_service.apply_for_project(self.applicant, self.project1, 2)
        self.assertEqual(app.status, Application.STATUS_PENDING)
        initial_units = self.project1.num_units1

        # Manager approves
        self.app_service.manager_approve_application(self.manager, app)
        approved_app = self.app_service.find_application_by_applicant(self.applicant.nric)
        self.assertEqual(approved_app.status, Application.STATUS_SUCCESSFUL)
        # Unit count should NOT decrease on manager approval
        proj_after_approve = self.project_service.find_project_by_name(self.project1.project_name)
        self.assertEqual(proj_after_approve.num_units1, initial_units)

        # --- Test Rejection ---
        # Married applicant applies
        app2 = self.app_service.apply_for_project(self.married_applicant, self.project1, 3)
        # Manager rejects
        self.app_service.manager_reject_application(self.manager, app2)
        rejected_app = self.app_service.find_application_by_applicant(self.married_applicant.nric)
        self.assertEqual(rejected_app.status, Application.STATUS_UNSUCCESSFUL)

    def test_manager_approve_application_fail_no_units_auto_reject(self):
        # Set units to 0
        self.project1.num_units1 = 0
        self.project_repo.update(self.project1)
        self.project1 = self.project_service.find_project_by_name(TEST_PROJECT1_NAME) # Re-fetch

        app = self.app_service.apply_for_project(self.applicant, self.project1, 2)
        # Manager tries to approve
        with self.assertRaisesRegex(OperationError, "No 2-Room units available. Application automatically rejected."):
             self.app_service.manager_approve_application(self.manager, app)
        # Check status is UNSUCCESSFUL
        rejected_app = self.app_service.find_application_by_applicant(self.applicant.nric)
        self.assertEqual(rejected_app.status, Application.STATUS_UNSUCCESSFUL)


    def test_manager_approve_reject_withdrawal(self):
        # Apply and request withdrawal
        app = self.app_service.apply_for_project(self.applicant, self.project1, 2)
        self.app_service.request_withdrawal(app)
        app_with_req = self.app_service.find_application_by_applicant(self.applicant.nric)
        self.assertTrue(app_with_req.request_withdrawal)

        # Manager approves withdrawal
        self.app_service.manager_approve_withdrawal(self.manager, app_with_req)
        app_withdrawn = self.app_service.find_application_by_applicant(self.applicant.nric)
        self.assertEqual(app_withdrawn.status, Application.STATUS_UNSUCCESSFUL)
        self.assertFalse(app_withdrawn.request_withdrawal) # Request flag cleared

        # --- Test Reject Withdrawal ---
        # Married applies and requests withdrawal
        app2 = self.app_service.apply_for_project(self.married_applicant, self.project1, 3)
        self.app_service.request_withdrawal(app2)
        app2_with_req = self.app_service.find_application_by_applicant(self.married_applicant.nric)
        original_status_app2 = app2_with_req.status # Should be PENDING

        # Manager rejects withdrawal
        self.app_service.manager_reject_withdrawal(self.manager, app2_with_req)
        app2_rejected_withdrawal = self.app_service.find_application_by_applicant(self.married_applicant.nric)
        self.assertFalse(app2_rejected_withdrawal.request_withdrawal) # Flag cleared
        self.assertEqual(app2_rejected_withdrawal.status, original_status_app2) # Status unchanged

    def test_manager_view_all_enquiries(self):
        # Applicant submits enquiry for project 1 (managed by manager 1)
        enq1 = self.enq_service.submit_enquiry(self.applicant, self.project1, "Q1")
        # Married applicant submits enquiry for project 3 (managed by manager 2)
        enq2 = self.enq_service.submit_enquiry(self.married_applicant, self.project3, "Q2")

        # Manager 1 views all - should see both
        all_enquiries = self.enq_service.get_all_enquiries()
        self.assertEqual(len(all_enquiries), 2)
        enq_ids = {e.enquiry_id for e in all_enquiries}
        self.assertIn(enq1.enquiry_id, enq_ids)
        self.assertIn(enq2.enquiry_id, enq_ids)

    def test_manager_reply_enquiry_managed_project(self):
        enq = self.enq_service.submit_enquiry(self.applicant, self.project1, "Question for Manager?")
        # Manager 1 replies to enquiry on project 1 (they manage it)
        self.enq_service.reply_to_enquiry(self.manager, enq, "Manager 1 reply.")
        replied_enq = self.enq_service.find_enquiry_by_id(enq.enquiry_id)
        self.assertIn("[Manager - Test Manager]: Manager 1 reply.", replied_enq.reply)

    def test_manager_reply_enquiry_fail_not_managed(self):
        enq = self.enq_service.submit_enquiry(self.applicant, self.project1, "Question?")
        # Manager 2 tries to reply to enquiry on project 1 (managed by Manager 1)
        with self.assertRaisesRegex(OperationError, "Managers can only reply to enquiries for projects they manage"):
            self.enq_service.reply_to_enquiry(self.manager2, enq, "Manager 2 unauthorized reply.")

    # --- Reporting Tests ---
    def test_generate_booking_report(self):
        # Setup: Two booked applications
        # App 1: Applicant (Single, 36) -> Project 1 (Yishun), 2-Room
        app1 = self.app_service.apply_for_project(self.applicant, self.project1, 2)
        self.app_service.manager_approve_application(self.manager, app1)
        reg1 = self.reg_service.officer_register_for_project(self.officer, self.project1)
        self.reg_service.manager_approve_officer_registration(self.manager, reg1)
        app1_s = self.app_service.find_application_by_applicant(self.applicant.nric)
        self.app_service.officer_book_flat(self.officer, app1_s)

        # App 2: Old Married (Married, 40) -> Project 1 (Yishun), 3-Room
        app2 = self.app_service.apply_for_project(self.old_married_applicant, self.project1, 3)
        self.app_service.manager_approve_application(self.manager, app2)
        app2_s = self.app_service.find_application_by_applicant(self.old_married_applicant.nric)
        self.app_service.officer_book_flat(self.officer, app2_s) # Same officer handles

        # Generate report - no filters
        report_data = self.app_service.generate_booking_report_data()
        self.assertEqual(len(report_data), 2)
        nrics_in_report = {row['NRIC'] for row in report_data}
        self.assertIn(self.applicant.nric, nrics_in_report)
        self.assertIn(self.old_married_applicant.nric, nrics_in_report)

        # Generate report - filter by flat type 2
        report_data_2r = self.app_service.generate_booking_report_data(filter_flat_type_str='2')
        self.assertEqual(len(report_data_2r), 1)
        self.assertEqual(report_data_2r[0]['NRIC'], self.applicant.nric)
        self.assertEqual(report_data_2r[0]['Flat Type'], '2-Room')

        # Generate report - filter by project name
        report_data_p1 = self.app_service.generate_booking_report_data(filter_project_name=TEST_PROJECT1_NAME)
        self.assertEqual(len(report_data_p1), 2)

        report_data_p3 = self.app_service.generate_booking_report_data(filter_project_name=TEST_PROJECT3_NAME)
        self.assertEqual(len(report_data_p3), 0)

    # --- Repository/Data Handling Tests ---
    def test_repository_add_find_delete(self):
        # Use Project Repo as example
        repo = self.project_repo
        name = "Repo Test Project"
        new_proj = Project(name, "Repo Town", "2-Room", 1, 1, "3-Room", 1, 1, TODAY, TOMORROW, self.manager.nric, 1)

        # Add
        repo.add(new_proj)
        found = repo.find_by_key(name)
        self.assertIsNotNone(found)
        self.assertEqual(found.project_name, name)

        # Add duplicate fails
        with self.assertRaises(IntegrityError):
            repo.add(new_proj)

        # Delete
        repo.delete(name)
        not_found = repo.find_by_key(name)
        self.assertIsNone(not_found)

        # Delete non-existent fails
        with self.assertRaises(IntegrityError):
            repo.delete("NonExistentProject")

    def test_enquiry_repo_next_id(self):
        initial_next_id = self.enq_repo.next_id
        # Add one enquiry
        enq1 = Enquiry(0, self.applicant.nric, self.project1.project_name, "Text 1")
        self.enq_repo.add(enq1)
        self.assertEqual(enq1.enquiry_id, initial_next_id)
        self.assertEqual(self.enq_repo.next_id, initial_next_id + 1)
        # Add another
        enq2 = Enquiry(0, self.applicant.nric, self.project1.project_name, "Text 2")
        self.enq_repo.add(enq2)
        self.assertEqual(enq2.enquiry_id, initial_next_id + 1)
        self.assertEqual(self.enq_repo.next_id, initial_next_id + 2)

    # --- Utility Tests ---
    def test_validate_nric(self):
        self.assertTrue(validate_nric("S1234567A"))
        self.assertTrue(validate_nric("T9876543Z"))
        self.assertFalse(validate_nric("S123456A")) # Too short
        self.assertFalse(validate_nric("S12345678A")) # Too long digit part
        self.assertFalse(validate_nric("F1234567A")) # Invalid start letter
        self.assertFalse(validate_nric("S123A567A")) # Non-digit in middle
        self.assertFalse(validate_nric("S12345678")) # Missing end letter
        self.assertFalse(validate_nric("S12345671")) # Digit end letter

    def test_dates_overlap(self):
        d1 = date(2024, 1, 1)
        d2 = date(2024, 1, 10)
        d3 = date(2024, 1, 5)
        d4 = date(2024, 1, 15)
        d5 = date(2024, 1, 11)
        d6 = date(2024, 1, 20)
        d7 = date(2024, 1, 10) # Edge case - touching end/start

        self.assertTrue(dates_overlap(d1, d2, d3, d4)) # Partial overlap
        self.assertTrue(dates_overlap(d3, d4, d1, d2)) # Partial overlap reversed
        self.assertTrue(dates_overlap(d1, d4, d3, d2)) # Inner contains outer
        self.assertFalse(dates_overlap(d1, d2, d5, d6)) # No overlap
        self.assertFalse(dates_overlap(d5, d6, d1, d2)) # No overlap reversed
        self.assertFalse(dates_overlap(d1, d7, d5, d6)) # Touching but no overlap (d7 < d5)
        self.assertTrue(dates_overlap(d1, d7, d3, d7)) # Touching end included


    # --- Add More Tests as Needed ---
    # Consider edge cases for filtering, more complex overlap scenarios, etc.

# --- Run Tests ---
if __name__ == '__main__':
     # Need to setup the controller instance for tests that might use it indirectly
     # We won't test the full CLI flow, but can test helper methods if needed
     # For now, we focus on service layer testing which covers most logic
     controller = ApplicationController() # Initialize controller AFTER patching
     BaseBTOIntegrationTest.controller = controller # Make it accessible if needed in tests

     unittest.main(verbosity=2)