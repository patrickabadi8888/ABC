# services/application_service.py
from repositories.application_repository import ApplicationRepository
# Need ProjectService and RegistrationService later
from services.project_service import ProjectService
# from services.registration_service import RegistrationService
from models.user import Applicant, HDBOfficer, HDBManager
from models.application import Application
from models.project import Project
from models.roles import ApplicationStatus, UserRole, FLAT_TYPE_2_ROOM, FLAT_TYPE_3_ROOM
from utils.exceptions import OperationError, IntegrityError, AuthorizationError

class ApplicationService:
    """Handles business logic for BTO applications."""
    def __init__(self, application_repository: ApplicationRepository,
                 project_service: ProjectService):
                 # registration_service: RegistrationService): # Add later
        self.application_repository = application_repository
        self.project_service = project_service
        # self.registration_service = registration_service # Add later

    def find_active_application_by_applicant(self, applicant_nric: str) -> Application | None:
        """Finds the currently active (not unsuccessful) application for an applicant."""
        apps = self.application_repository.find_by_applicant_nric(applicant_nric)
        for app in apps:
             # Define "active": Pending, Successful, Booked (potentially withdrawable)
             if app.status != ApplicationStatus.UNSUCCESSFUL.value:
                 return app
        return None

    def get_applications_for_project(self, project_name: str) -> list[Application]:
        """Gets all applications associated with a specific project."""
        return self.application_repository.find_by_project_name(project_name)

    def get_all_applications(self) -> list[Application]:
        """Gets all applications from the repository."""
        return self.application_repository.get_all()

    def _check_applicant_eligibility(self, applicant: Applicant, project: Project, flat_type: int):
        """Performs eligibility checks before allowing an application."""
        # 1. Project Open?
        if not project.is_currently_active_for_application():
            raise OperationError(f"Project '{project.project_name}' is not currently open for applications.")

        # 2. Already has active application?
        if self.find_active_application_by_applicant(applicant.nric):
            raise OperationError("You already have an active BTO application.")

        # 3. Role-based restrictions
        if applicant.get_role() == UserRole.HDB_MANAGER:
             raise AuthorizationError("HDB Managers cannot apply for BTO projects.")

        # 4. Age/Marital Status Eligibility
        is_single = applicant.marital_status.lower() == "single"
        age = applicant.age

        if is_single:
            if age < 35:
                raise OperationError("Single applicants must be at least 35 years old.")
            if flat_type != FLAT_TYPE_2_ROOM:
                raise OperationError("Single applicants can only apply for 2-Room flats.")
        else: # Assume Married (add checks for other statuses if needed)
            if age < 21:
                raise OperationError("Married applicants must be at least 21 years old.")
            if flat_type not in [FLAT_TYPE_2_ROOM, FLAT_TYPE_3_ROOM]:
                raise OperationError("Invalid flat type selected for married applicant.")

        # 5. Unit Availability
        units, _ = project.get_flat_details(flat_type)
        if units <= 0:
            raise OperationError(f"No {flat_type}-Room units are currently available in project '{project.project_name}'.")

        # 6. Officer Conflict Check (Requires RegistrationService)
        if applicant.get_role() == UserRole.HDB_OFFICER:
            pass
            # TODO: Integrate with RegistrationService
            # is_registered = self.registration_service.is_registered_for_project(applicant.nric, project.project_name)
            # if is_registered:
            #     raise OperationError("You cannot apply for a project you have registered for as an officer.")

    def apply_for_project(self, applicant: Applicant, project: Project, flat_type: int) -> Application:
        """Creates and saves a new application after eligibility checks."""
        # Perform checks first
        self._check_applicant_eligibility(applicant, project, flat_type)

        # Create application object
        new_application = Application(
            applicant_nric=applicant.nric,
            project_name=project.project_name,
            flat_type=flat_type,
            status=ApplicationStatus.PENDING.value # Initial status
        )

        try:
            # Add to repository (which handles saving)
            # The repository key logic prevents duplicates for same user-project combo
            self.application_repository.add(new_application)
            print(f"Application by {applicant.nric} for {project.project_name} submitted successfully.")
            return new_application
        except IntegrityError as e:
            # This might occur if the repo key logic detects a true duplicate not caught by active check
            raise OperationError(f"Failed to submit application: An application for this project might already exist. {e}")
        except Exception as e:
            raise OperationError(f"An unexpected error occurred during application submission: {e}")

    def request_withdrawal(self, application: Application):
        """Marks an application for withdrawal request."""
        # Check if withdrawal is allowed based on status
        allowed_statuses = [
             ApplicationStatus.PENDING.value,
             ApplicationStatus.SUCCESSFUL.value,
             ApplicationStatus.BOOKED.value # Allowed as per FAQ
        ]
        if application.status not in allowed_statuses:
            raise OperationError(f"Cannot request withdrawal for an application with status '{application.status}'.")

        if application.request_withdrawal:
            raise OperationError("Withdrawal already requested for this application.")

        application.request_withdrawal = True
        try:
            self.application_repository.update(application)
            print(f"Withdrawal requested for application (Applicant: {application.applicant_nric}, Project: {application.project_name}).")
        except Exception as e:
            application.request_withdrawal = False # Revert on failure
            raise OperationError(f"Failed to save withdrawal request: {e}")

    # --- Manager Actions ---
    def _ensure_manager_can_manage(self, manager: HDBManager, application: Application):
        """Checks if the manager manages the project associated with the application."""
        project = self.project_service.find_project_by_name(application.project_name)
        if not project:
             # This indicates data inconsistency
             raise IntegrityError(f"Project '{application.project_name}' associated with application not found.")
        if project.manager_nric != manager.nric:
             raise AuthorizationError(f"You do not manage project '{project.project_name}' and cannot modify this application.")
        return project # Return the project for convenience

    def manager_approve_application(self, manager: HDBManager, application: Application):
        """Approves a pending application (Manager action)."""
        project = self._ensure_manager_can_manage(manager, application)

        if application.status != ApplicationStatus.PENDING.value:
            raise OperationError(f"Application status is '{application.status}', not PENDING. Cannot approve.")
        if application.request_withdrawal:
            raise OperationError("Cannot approve an application with a pending withdrawal request.")

        # Check unit availability AT THE TIME OF APPROVAL
        units, _ = project.get_flat_details(application.flat_type)
        if units <= 0:
            # Auto-reject if no units left
            print(f"No {application.flat_type}-Room units left in '{project.project_name}'. Auto-rejecting application.")
            application.status = ApplicationStatus.UNSUCCESSFUL.value
        else:
            application.status = ApplicationStatus.SUCCESSFUL.value

        try:
            self.application_repository.update(application)
            print(f"Application by {application.applicant_nric} for {project.project_name} status updated to: {application.status}.")
        except Exception as e:
            # Revert status change on failure? Depends on desired atomicity.
            # For simplicity, report error.
            raise OperationError(f"Failed to save application approval status: {e}")

    def manager_reject_application(self, manager: HDBManager, application: Application):
        """Rejects a pending application (Manager action)."""
        self._ensure_manager_can_manage(manager, application)

        if application.status != ApplicationStatus.PENDING.value:
            raise OperationError(f"Application status is '{application.status}', not PENDING. Cannot reject.")
        # Allow rejecting even if withdrawal requested? Yes, seems logical.

        application.status = ApplicationStatus.UNSUCCESSFUL.value
        try:
            self.application_repository.update(application)
            print(f"Application by {application.applicant_nric} for {application.project_name} rejected.")
        except Exception as e:
            raise OperationError(f"Failed to save application rejection status: {e}")

    def manager_approve_withdrawal(self, manager: HDBManager, application: Application):
        """Approves a withdrawal request (Manager action)."""
        self._ensure_manager_can_manage(manager, application)

        if not application.request_withdrawal:
            raise OperationError("No withdrawal request is pending for this application.")

        # FAQ: If withdrawal approved, status becomes Unsuccessful.
        original_status = application.status
        application.status = ApplicationStatus.UNSUCCESSFUL.value
        application.request_withdrawal = False # Clear the request flag

        # If the application was already BOOKED, need to increase unit count
        unit_to_return = None
        if original_status == ApplicationStatus.BOOKED.value:
             unit_to_return = application.flat_type

        try:
            self.application_repository.update(application)
            print(f"Withdrawal approved for application (Applicant: {application.applicant_nric}). Status set to UNSUCCESSFUL.")

            # If unit needs returning, do it after app status saved
            if unit_to_return:
                project = self.project_service.find_project_by_name(application.project_name)
                if project:
                    project.increase_unit_count(unit_to_return)
                    try:
                        self.project_service.project_repository.update(project)
                        print(f"Unit count for {unit_to_return}-Room in '{project.project_name}' incremented due to withdrawal.")
                    except Exception as proj_e:
                        # Log this critical error - app withdrawn but unit not returned
                        print(f"CRITICAL ERROR: Failed to return unit to project '{project.project_name}' after withdrawal approval: {proj_e}")
                else:
                    print(f"CRITICAL ERROR: Project '{application.project_name}' not found to return unit after withdrawal approval.")

        except Exception as e:
            # Revert application status and flag if save fails
            application.status = original_status
            application.request_withdrawal = True
            raise OperationError(f"Failed to save withdrawal approval: {e}")

    def manager_reject_withdrawal(self, manager: HDBManager, application: Application):
        """Rejects a withdrawal request (Manager action)."""
        self._ensure_manager_can_manage(manager, application)

        if not application.request_withdrawal:
            raise OperationError("No withdrawal request is pending for this application.")

        application.request_withdrawal = False # Just clear the flag
        try:
            self.application_repository.update(application)
            print(f"Withdrawal request rejected for application (Applicant: {application.applicant_nric}). Status remains '{application.status}'.")
        except Exception as e:
            application.request_withdrawal = True # Revert on failure
            raise OperationError(f"Failed to save withdrawal rejection: {e}")


    # --- Officer Actions ---
    def _ensure_officer_can_manage(self, officer: HDBOfficer, application: Application):
        """Checks if the officer handles the project for the application."""
        project = self.project_service.find_project_by_name(application.project_name)
        if not project:
            raise IntegrityError(f"Project '{application.project_name}' associated with application not found.")

        # TODO: Integrate with RegistrationService for full check
        handled_project_names = self.project_service.get_handled_project_names_for_officer(officer.nric)
        if project.project_name not in handled_project_names:
             raise AuthorizationError(f"You do not handle project '{project.project_name}' and cannot modify this application.")
        return project

    def officer_book_flat(self, officer: HDBOfficer, application: Application) -> Project:
        """Books a flat for a successful application (Officer action)."""
        project = self._ensure_officer_can_manage(officer, application)

        # Validate status transition: Must be SUCCESSFUL -> BOOKED
        if application.status != ApplicationStatus.SUCCESSFUL.value:
            raise OperationError(f"Application status must be '{ApplicationStatus.SUCCESSFUL.value}' to book. Current status: '{application.status}'.")

        # Attempt to decrease unit count first (atomic-like operation)
        unit_decreased = project.decrease_unit_count(application.flat_type)

        if not unit_decreased:
            # If no units left when trying to book, mark as unsuccessful
            print(f"Booking failed: No {application.flat_type}-Room units available in '{project.project_name}' at time of booking.")
            application.status = ApplicationStatus.UNSUCCESSFUL.value
            try:
                self.application_repository.update(application)
            except Exception as app_fail_e:
                # Log critical error: unit check failed, AND status update failed
                print(f"CRITICAL ERROR: Failed to mark application unsuccessful after booking failure for unit availability: {app_fail_e}")
            raise OperationError(f"Booking failed: No units available. Application marked unsuccessful.")

        # If unit count decreased successfully, update application status
        original_app_status = application.status
        application.status = ApplicationStatus.BOOKED.value

        try:
            # Save project change (unit count) FIRST
            self.project_service.project_repository.update(project)
            try:
                # Then save application status change
                self.application_repository.update(application)
                print(f"Flat booked successfully by {officer.nric} for applicant {application.applicant_nric} in project {project.project_name}.")
                return project # Return updated project for receipt generation
            except Exception as app_save_e:
                # Critical: Project saved, but App failed. Attempt to revert project.
                print(f"ERROR: Failed to save application status update after booking: {app_save_e}. Attempting project revert.")
                project.increase_unit_count(application.flat_type)
                application.status = original_app_status # Revert app status too
                try:
                    self.project_service.project_repository.update(project)
                    print("Project unit count successfully reverted.")
                except Exception as proj_revert_e:
                    # Very critical state - data inconsistent
                    print(f"CRITICAL ERROR: Failed to revert project unit count after application save failure: {proj_revert_e}. Manual intervention likely needed.")
                raise OperationError(f"Booking partially failed: Unit count updated, but application status save failed. Project reverted. Error: {app_save_e}")

        except Exception as proj_save_e:
            # If project save fails, revert the unit count decrease and app status
            project.increase_unit_count(application.flat_type)
            application.status = original_app_status
            print(f"ERROR: Failed to save project unit count update during booking: {proj_save_e}. Reverting.")
            raise OperationError(f"Booking failed: Could not update project unit count. Error: {proj_save_e}")