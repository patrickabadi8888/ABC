# services/registration_service.py
from repositories.registration_repository import RegistrationRepository
from repositories.application_repository import ApplicationRepository
from services.project_service import ProjectService
from models.user import HDBOfficer, HDBManager
from models.project import Project
from models.registration import Registration
from models.roles import RegistrationStatus, UserRole
from utils.exceptions import OperationError, IntegrityError, AuthorizationError
from utils.helpers import dates_overlap

class RegistrationService:
    """Handles business logic for HDB Officer project registrations."""
    def __init__(self, registration_repository: RegistrationRepository,
                 project_service: ProjectService,
                 application_repository: ApplicationRepository):
        self.registration_repository = registration_repository
        self.project_service = project_service
        self.application_repository = application_repository # Needed for eligibility checks

    def find_registration(self, officer_nric: str, project_name: str) -> Registration | None:
        """Finds a specific registration."""
        return self.registration_repository.find_by_officer_and_project(officer_nric, project_name)

    def get_registrations_by_officer(self, officer_nric: str) -> list[Registration]:
        """Gets all registrations for a specific officer."""
        return self.registration_repository.find_by_officer_nric(officer_nric)

    def get_registrations_for_project(self, project_name: str,
                                      status_filter: RegistrationStatus | None = None) -> list[Registration]:
        """Gets registrations for a project, optionally filtering by status."""
        regs = self.registration_repository.find_by_project_name(project_name)
        if status_filter:
             return [reg for reg in regs if reg.status == status_filter.value]
        return regs

    def is_approved_officer_for_project(self, officer_nric: str, project_name: str) -> bool:
        """Checks if an officer has an approved registration for a project."""
        reg = self.find_registration(officer_nric, project_name)
        return reg and reg.status == RegistrationStatus.APPROVED.value

    def is_registered_for_project(self, officer_nric: str, project_name: str) -> bool:
         """Checks if an officer has *any* registration (pending, approved, rejected) for a project."""
         return self.find_registration(officer_nric, project_name) is not None

    def _check_officer_registration_eligibility(self, officer: HDBOfficer, project: Project):
        """Performs eligibility checks before allowing officer registration."""
        # 1. Already registered for this project?
        if self.is_registered_for_project(officer.nric, project.project_name):
            raise OperationError("You have already submitted a registration for this project.")

        # 2. Is the manager trying to register for own project?
        if project.manager_nric == officer.nric:
            # This check might be redundant if only Officers can call this, but good defense
            raise OperationError("Managers cannot register as officers for their own projects.")

        # 3. Applied for this project as applicant?
        # Need ApplicationRepository instance passed to __init__
        applicant_apps = self.application_repository.find_by_applicant_nric(officer.nric)
        if any(app.project_name == project.project_name for app in applicant_apps):
             # Check if any application (even unsuccessful) exists for this project
             # Requirement: "No intention to apply... before and after becoming an HDB Officer"
             # Implies cannot register if *any* application exists for that project.
             raise OperationError("You cannot register as an officer for a project you have ever applied for.")

        # 4. Overlap Check: Already approved for another project in overlapping period?
        target_od = project.opening_date
        target_cd = project.closing_date
        if not target_od or not target_cd:
             # Should not happen for valid projects, but check defensively
             raise OperationError(f"Target project '{project.project_name}' has invalid application dates.")

        approved_regs = [reg for reg in self.get_registrations_by_officer(officer.nric)
                         if reg.status == RegistrationStatus.APPROVED.value]

        for reg in approved_regs:
            other_project = self.project_service.find_project_by_name(reg.project_name)
            if other_project and other_project.opening_date and other_project.closing_date:
                if dates_overlap(target_od, target_cd, other_project.opening_date, other_project.closing_date):
                    raise OperationError(f"You are already an approved officer for project "
                                         f"'{other_project.project_name}' which has an application period "
                                         f"overlapping with '{project.project_name}'.")


    def officer_register_for_project(self, officer: HDBOfficer, project: Project) -> Registration:
        """Creates and saves a new officer registration request."""
        if officer.get_role() != UserRole.HDB_OFFICER:
             # Defensive check
             raise AuthorizationError("Only HDB Officers can register for projects.")

        # Perform eligibility checks
        self._check_officer_registration_eligibility(officer, project)

        # Create registration object
        new_registration = Registration(
            officer_nric=officer.nric,
            project_name=project.project_name,
            status=RegistrationStatus.PENDING.value # Initial status
        )

        try:
            self.registration_repository.add(new_registration)
            print(f"Officer {officer.nric} registered for project {project.project_name}. Pending approval.")
            return new_registration
        except IntegrityError as e:
            # Should be caught by eligibility check, but handle defensively
            raise OperationError(f"Failed to submit registration: A registration might already exist. {e}")
        except Exception as e:
            raise OperationError(f"An unexpected error occurred during registration submission: {e}")

    # --- Manager Actions ---
    def _ensure_manager_can_manage(self, manager: HDBManager, registration: Registration):
        """Checks if the manager manages the project of the registration."""
        project = self.project_service.find_project_by_name(registration.project_name)
        if not project:
             raise IntegrityError(f"Project '{registration.project_name}' associated with registration not found.")
        if project.manager_nric != manager.nric:
             raise AuthorizationError(f"You do not manage project '{project.project_name}' and cannot modify this registration.")
        return project # Return project for convenience

    def manager_approve_officer_registration(self, manager: HDBManager, registration: Registration):
        """Approves a pending officer registration (Manager action)."""
        project = self._ensure_manager_can_manage(manager, registration)

        if registration.status != RegistrationStatus.PENDING.value:
            raise OperationError(f"Registration status is '{registration.status}', not PENDING. Cannot approve.")

        # Check project slots
        if not project.can_add_officer():
            raise OperationError(f"No available officer slots in project '{project.project_name}'. Cannot approve.")

        # Final overlap check at time of approval (important!)
        officer_nric = registration.officer_nric
        target_od = project.opening_date
        target_cd = project.closing_date
        if not target_od or not target_cd:
             raise OperationError(f"Target project '{project.project_name}' has invalid application dates.")

        approved_regs = [reg for reg in self.get_registrations_by_officer(officer_nric)
                         if reg.status == RegistrationStatus.APPROVED.value and reg != registration] # Exclude self

        for reg in approved_regs:
             other_project = self.project_service.find_project_by_name(reg.project_name)
             if other_project and other_project.opening_date and other_project.closing_date:
                 if dates_overlap(target_od, target_cd, other_project.opening_date, other_project.closing_date):
                     raise OperationError(f"Cannot approve: Officer '{officer_nric}' is already approved for project "
                                          f"'{other_project.project_name}' with an overlapping period.")


        # If checks pass, proceed with approval
        original_reg_status = registration.status
        registration.status = RegistrationStatus.APPROVED.value

        try:
            # Add officer to project's internal list first
            self.project_service._add_officer_to_project_list(project, officer_nric) # Use internal method
            try:
                # Then update the registration status
                self.registration_repository.update(registration)
                print(f"Registration for officer {officer_nric} approved for project {project.project_name}.")
            except Exception as reg_save_e:
                # Critical: Project updated, but Reg failed. Revert project.
                print(f"ERROR: Failed to save registration status after approval: {reg_save_e}. Attempting project revert.")
                registration.status = original_reg_status # Revert reg status obj
                try:
                     self.project_service._remove_officer_from_project_list(project, officer_nric)
                     print("Project officer list successfully reverted.")
                except Exception as proj_revert_e:
                     print(f"CRITICAL ERROR: Failed to revert project officer list after registration save failure: {proj_revert_e}. Manual intervention needed.")
                raise OperationError(f"Approval partially failed: Officer added to project, but registration save failed. Project reverted. Error: {reg_save_e}")

        except Exception as proj_save_e:
            # If adding officer to project fails, revert reg status and raise
            registration.status = original_reg_status
            print(f"ERROR: Failed to add officer to project list during approval: {proj_save_e}. Reverting registration status.")
            raise OperationError(f"Approval failed: Could not update project's officer list. Error: {proj_save_e}")


    def manager_reject_officer_registration(self, manager: HDBManager, registration: Registration):
        """Rejects a pending officer registration (Manager action)."""
        self._ensure_manager_can_manage(manager, registration)

        if registration.status != RegistrationStatus.PENDING.value:
            raise OperationError(f"Registration status is '{registration.status}', not PENDING. Cannot reject.")

        registration.status = RegistrationStatus.REJECTED.value
        try:
            self.registration_repository.update(registration)
            print(f"Registration for officer {registration.officer_nric} rejected for project {registration.project_name}.")
        except Exception as e:
            # Revert status on failure?
            registration.status = RegistrationStatus.PENDING.value
            raise OperationError(f"Failed to save registration rejection status: {e}")