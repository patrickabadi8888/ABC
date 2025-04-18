from typing import List, Optional, Tuple
from .interfaces.iapplication_service import IApplicationService
from .interfaces.iproject_service import IProjectService # Use interface
from .interfaces.iregistration_service import IRegistrationService # Use interface
from repository.interfaces.iapplication_repository import IApplicationRepository
from repository.interfaces.iuser_repository import IUserRepository
from model.application import Application
from model.applicant import Applicant
from model.hdb_officer import HDBOfficer
from model.hdb_manager import HDBManager
from model.project import Project
from common.enums import FlatType, ApplicationStatus, UserRole
from common.exceptions import OperationError, IntegrityError, DataSaveError

class ApplicationService(IApplicationService):
    """Handles business logic related to BTO applications."""
    def __init__(self, application_repository: IApplicationRepository,
                 project_service: IProjectService,
                 registration_service: IRegistrationService,
                 user_repository: IUserRepository):
        self._app_repo = application_repository
        self._project_service = project_service
        self._reg_service = registration_service
        self._user_repo = user_repository

    def find_application_by_applicant(self, applicant_nric: str) -> Optional[Application]:
        return self._app_repo.find_by_applicant_nric(applicant_nric)

    def find_booked_application_by_applicant(self, applicant_nric: str) -> Optional[Application]:
        """Finds a specifically BOOKED application for an applicant."""
        apps = self._app_repo.find_all_by_applicant_nric(applicant_nric)
        for app in apps:
            if app.status == ApplicationStatus.BOOKED:
                return app
        return None

    def get_all_applications_by_applicant(self, applicant_nric: str) -> List[Application]:
         return self._app_repo.find_all_by_applicant_nric(applicant_nric)

    def get_applications_for_project(self, project_name: str) -> List[Application]:
        return self._app_repo.find_by_project_name(project_name)

    def get_all_applications(self) -> List[Application]:
        return self._app_repo.get_all()

    def _check_applicant_eligibility(self, applicant: Applicant, project: Project, flat_type: FlatType):
        """Performs eligibility checks. Raises OperationError if ineligible."""
        if not project.is_currently_visible_and_active():
            raise OperationError(f"Project '{project.project_name}' is not open for applications.")
        if self.find_application_by_applicant(applicant.nric):
            raise OperationError("You already have an active BTO application.")
        if applicant.get_role() == UserRole.HDB_MANAGER:
             raise OperationError("HDB Managers cannot apply for BTO projects.")
        if applicant.get_role() == UserRole.HDB_OFFICER:
            if self._reg_service.find_registration(applicant.nric, project.project_name):
                raise OperationError("You cannot apply for a project you have registered for as an officer.")

        is_single = applicant.marital_status == "Single"
        is_married = applicant.marital_status == "Married"
        if is_single and (applicant.age < 35 or flat_type != FlatType.TWO_ROOM):
            raise OperationError("Single applicants must be >= 35 and can only apply for 2-Room.")
        if is_married and applicant.age < 21:
            raise OperationError("Married applicants must be at least 21 years old.")
        if not is_single and not is_married:
            raise OperationError(f"Unknown marital status '{applicant.marital_status}'.")

        units, _ = project.get_flat_details(flat_type)
        if units <= 0:
            raise OperationError(f"No {flat_type.to_string()} units available in '{project.project_name}'.")

    def apply_for_project(self, applicant: Applicant, project: Project, flat_type: FlatType) -> Application:
        self._check_applicant_eligibility(applicant, project, flat_type)
        new_application = Application(applicant.nric, project.project_name, flat_type)
        try:
            self._app_repo.add(new_application)
            # Defer saving
            return new_application
        except IntegrityError as e: raise OperationError(f"Failed to submit application: {e}")

    def request_withdrawal(self, application: Application):
        if application.request_withdrawal:
            raise OperationError("Withdrawal already requested.")
        try:
            application.set_withdrawal_request(True) # Model validates status
            self._app_repo.update(application)
            # Defer saving
        except (OperationError, IntegrityError) as e:
            # Attempt revert in memory? Risky without transaction.
            # application.set_withdrawal_request(False) # Try reverting flag
            raise OperationError(f"Failed to save withdrawal request: {e}")

    def _manager_can_manage_app(self, manager: HDBManager, application: Application) -> bool:
        project = self._project_service.find_project_by_name(application.project_name)
        return project is not None and project.manager_nric == manager.nric

    def manager_approve_application(self, manager: HDBManager, application: Application):
        if not self._manager_can_manage_app(manager, application):
            raise OperationError("You do not manage this project.")
        if application.status != ApplicationStatus.PENDING:
            raise OperationError(f"Application status is not PENDING.")
        if application.request_withdrawal:
            raise OperationError("Cannot approve application with pending withdrawal request.")

        project = self._project_service.find_project_by_name(application.project_name)
        if not project: raise IntegrityError(f"Project '{application.project_name}' not found.")

        units, _ = project.get_flat_details(application.flat_type)
        if units <= 0:
            application.set_status(ApplicationStatus.UNSUCCESSFUL) # Auto-reject
            self._app_repo.update(application)
            # Defer saving
            raise OperationError(f"No {application.flat_type.to_string()} units available. Application rejected.")

        try:
            application.set_status(ApplicationStatus.SUCCESSFUL)
            self._app_repo.update(application)
            # Defer saving
        except IntegrityError as e:
            # application.set_status(ApplicationStatus.PENDING) # Revert attempt
            raise OperationError(f"Failed to save application approval: {e}")

    def manager_reject_application(self, manager: HDBManager, application: Application):
        if not self._manager_can_manage_app(manager, application):
            raise OperationError("You do not manage this project.")
        if application.status != ApplicationStatus.PENDING:
            raise OperationError(f"Application status is not PENDING.")

        try:
            application.set_status(ApplicationStatus.UNSUCCESSFUL)
            self._app_repo.update(application)
            # Defer saving
        except IntegrityError as e:
            # application.set_status(ApplicationStatus.PENDING) # Revert attempt
            raise OperationError(f"Failed to save application rejection: {e}")

    def manager_approve_withdrawal(self, manager: HDBManager, application: Application):
        if not self._manager_can_manage_app(manager, application):
            raise OperationError("You do not manage this project.")
        if not application.request_withdrawal:
            raise OperationError("No withdrawal request is pending.")

        original_status = application.status
        project_updated = False
        try:
            application.set_status(ApplicationStatus.UNSUCCESSFUL)
            application.set_withdrawal_request(False)

            if original_status == ApplicationStatus.BOOKED:
                 project = self._project_service.find_project_by_name(application.project_name)
                 if project:
                     if project.increase_unit_count(application.flat_type):
                         # Update project repo immediately if unit count changed
                         self._project_service._project_repo.update(project)
                         project_updated = True
                     else: print(f"Warning: Could not increase unit count for {application.flat_type.to_string()} in {project.project_name}.")
                 else: print(f"Warning: Project {application.project_name} not found for unit count adjustment.")

            self._app_repo.update(application)
            # Defer saving of app repo and potentially project repo
        except (IntegrityError, OperationError) as e:
            # Rollback attempt (complex)
            # application.set_status(original_status)
            # application.set_withdrawal_request(True)
            # if project_updated and project: project.decrease_unit_count(...) # etc.
            raise OperationError(f"Failed to process withdrawal approval: {e}. State may be inconsistent.")

    def manager_reject_withdrawal(self, manager: HDBManager, application: Application):
        if not self._manager_can_manage_app(manager, application):
            raise OperationError("You do not manage this project.")
        if not application.request_withdrawal:
            raise OperationError("No withdrawal request is pending.")

        try:
            application.set_withdrawal_request(False) # Just clear the flag
            self._app_repo.update(application)
            # Defer saving
        except IntegrityError as e:
            # application.set_withdrawal_request(True) # Revert attempt
            raise OperationError(f"Failed to save withdrawal rejection: {e}")

    def officer_book_flat(self, officer: HDBOfficer, application: Application) -> Tuple[Project, Applicant]:
        project = self._project_service.find_project_by_name(application.project_name)
        if not project: raise OperationError(f"Project '{application.project_name}' not found.")

        handled_names = self._project_service.get_handled_project_names_for_officer(officer.nric)
        if project.project_name not in handled_names:
            raise OperationError(f"You do not handle project '{project.project_name}'.")

        if application.status != ApplicationStatus.SUCCESSFUL:
            raise OperationError(f"Application status must be SUCCESSFUL to book.")

        applicant = self._user_repo.find_user_by_nric(application.applicant_nric)
        if not applicant: raise IntegrityError(f"Applicant {application.applicant_nric} not found.")
        # Ensure applicant is actually an Applicant instance if needed, though User should suffice
        if not isinstance(applicant, Applicant): raise IntegrityError("User found is not an Applicant.")


        # --- Manual Transaction ---
        unit_decreased = False
        try:
            # 1. Decrease unit count in Project model
            if not project.decrease_unit_count(application.flat_type):
                application.set_status(ApplicationStatus.UNSUCCESSFUL)
                self._app_repo.update(application) # Update app status immediately
                # Defer save
                raise OperationError(f"Booking failed: No {application.flat_type.to_string()} units available. Application marked unsuccessful.")
            unit_decreased = True

            # 2. Update Project in repository
            self._project_service._project_repo.update(project)

            # 3. Update Application status in model and repository
            application.set_status(ApplicationStatus.BOOKED)
            self._app_repo.update(application)

            # If all steps successful, return data (saving deferred)
            return project, applicant

        except (OperationError, IntegrityError) as e:
            # --- Rollback attempts (Best Effort) ---
            print(f"ERROR during booking: {e}. Attempting rollback...")
            # Revert application status in memory & repo
            application.set_status(ApplicationStatus.SUCCESSFUL)
            try: self._app_repo.update(application)
            except Exception as rb_e: print(f"CRITICAL: Failed rollback app status: {rb_e}")

            # Revert project unit count in memory & repo if decreased
            if unit_decreased:
                project.increase_unit_count(application.flat_type)
                try: self._project_service._project_repo.update(project)
                except Exception as rb_e: print(f"CRITICAL: Failed rollback project units: {rb_e}")

            raise OperationError(f"Booking failed: {e}. Rollback attempted.") # Re-raise original error