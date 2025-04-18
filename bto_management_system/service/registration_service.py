from typing import List, Optional
from .interfaces.iregistration_service import IRegistrationService
from .interfaces.iproject_service import IProjectService # Use interface
from repository.interfaces.iregistration_repository import IRegistrationRepository
from repository.interfaces.iapplication_repository import IApplicationRepository
from model.registration import Registration
from model.hdb_officer import HDBOfficer
from model.hdb_manager import HDBManager
from model.project import Project
from common.enums import RegistrationStatus
from common.exceptions import OperationError, IntegrityError
from utils.date_util import DateUtil

class RegistrationService(IRegistrationService):
    """Handles business logic related to HDB Officer registrations."""
    def __init__(self, registration_repository: IRegistrationRepository,
                 project_service: IProjectService,
                 application_repository: IApplicationRepository):
        self._reg_repo = registration_repository
        self._project_service = project_service
        self._app_repo = application_repository

    def find_registration(self, officer_nric: str, project_name: str) -> Optional[Registration]:
        return self._reg_repo.find_by_officer_and_project(officer_nric, project_name)

    def get_registrations_by_officer(self, officer_nric: str) -> List[Registration]:
        return self._reg_repo.find_by_officer(officer_nric)

    def get_registrations_for_project(self, project_name: str, status_filter: Optional[RegistrationStatus] = None) -> List[Registration]:
        return self._reg_repo.find_by_project(project_name, status_filter)

    def _check_officer_registration_eligibility(self, officer: HDBOfficer, project: Project):
        """Checks if an officer can register. Raises OperationError if ineligible."""
        if self.find_registration(officer.nric, project.project_name):
            raise OperationError(f"Already registered for project '{project.project_name}'.")
        if project.manager_nric == officer.nric:
            raise OperationError("Managers cannot register as officers for their own projects.")
        # Check if officer ever applied for this project
        if any(app.project_name == project.project_name for app in self._app_repo.find_all_by_applicant_nric(officer.nric)):
             raise OperationError("Cannot register for a project you have previously applied for.")

        # Check for overlapping approved registrations
        target_od, target_cd = project.opening_date, project.closing_date
        if not target_od or not target_cd: raise OperationError("Target project has invalid dates.")

        for reg in self.get_registrations_by_officer(officer.nric):
             if reg.status == RegistrationStatus.APPROVED:
                 other_project = self._project_service.find_project_by_name(reg.project_name)
                 if other_project and other_project.opening_date and other_project.closing_date:
                     if DateUtil.dates_overlap(target_od, target_cd, other_project.opening_date, other_project.closing_date):
                         raise OperationError(f"Overlaps with approved registration for '{other_project.project_name}'.")

    def officer_register_for_project(self, officer: HDBOfficer, project: Project) -> Registration:
        self._check_officer_registration_eligibility(officer, project)
        new_registration = Registration(officer.nric, project.project_name)
        try:
            self._reg_repo.add(new_registration)
            # Defer saving
            return new_registration
        except IntegrityError as e: raise OperationError(f"Failed to submit registration: {e}")

    def _manager_can_manage_reg(self, manager: HDBManager, registration: Registration) -> bool:
        project = self._project_service.find_project_by_name(registration.project_name)
        return project is not None and project.manager_nric == manager.nric

    def manager_approve_officer_registration(self, manager: HDBManager, registration: Registration):
        if not self._manager_can_manage_reg(manager, registration):
            raise OperationError("You do not manage this project.")
        if registration.status != RegistrationStatus.PENDING:
            raise OperationError(f"Registration status is not PENDING.")

        project = self._project_service.find_project_by_name(registration.project_name)
        if not project: raise OperationError(f"Project '{registration.project_name}' not found.")
        if not project.can_add_officer():
            raise OperationError(f"No available officer slots in project '{project.project_name}'.")

        # Final overlap check at time of approval
        target_od, target_cd = project.opening_date, project.closing_date
        if not target_od or not target_cd: raise OperationError("Project has invalid dates.")
        for other_reg in self.get_registrations_by_officer(registration.officer_nric):
            if other_reg != registration and other_reg.status == RegistrationStatus.APPROVED:
                other_project = self._project_service.find_project_by_name(other_reg.project_name)
                if other_project and other_project.opening_date and other_project.closing_date:
                    if DateUtil.dates_overlap(target_od, target_cd, other_project.opening_date, other_project.closing_date):
                        raise OperationError(f"Officer approved for overlapping project '{other_project.project_name}'.")

        # --- Manual Transaction ---
        officer_added = False
        try:
            # 1. Add officer to project (ProjectService handles repo update)
            self._project_service.add_officer_to_project(project, registration.officer_nric)
            officer_added = True

            # 2. Update registration status
            registration.set_status(RegistrationStatus.APPROVED)
            self._reg_repo.update(registration)
            # Defer saving

        except (OperationError, IntegrityError) as e:
            # --- Rollback attempts ---
            print(f"ERROR during registration approval: {e}. Attempting rollback...")
            registration.set_status(RegistrationStatus.PENDING) # Revert status in memory
            try: self._reg_repo.update(registration) # Attempt to update repo
            except Exception as rb_e: print(f"Warning: Failed rollback reg status: {rb_e}")

            if officer_added: # If officer was added to project, try removing
                 try:
                     self._project_service.remove_officer_from_project(project, registration.officer_nric)
                 except Exception as rb_e: print(f"CRITICAL: Failed rollback officer from project: {rb_e}")

            raise OperationError(f"Approval failed: {e}. Rollback attempted.")

    def manager_reject_officer_registration(self, manager: HDBManager, registration: Registration):
        if not self._manager_can_manage_reg(manager, registration):
            raise OperationError("You do not manage this project.")
        if registration.status != RegistrationStatus.PENDING:
            raise OperationError(f"Registration status is not PENDING.")

        try:
            registration.set_status(RegistrationStatus.REJECTED)
            self._reg_repo.update(registration)
            # Defer saving
        except IntegrityError as e:
            # registration.set_status(RegistrationStatus.PENDING) # Revert attempt
            raise OperationError(f"Failed to save registration rejection: {e}")