# services/enquiry_service.py
from repositories.enquiry_repository import EnquiryRepository
from repositories.user_repository import UserRepository
from services.project_service import ProjectService
from services.application_service import ApplicationService # To check view rights
from models.user import User, Applicant
from models.project import Project
from models.enquiry import Enquiry
from models.roles import UserRole
from utils.exceptions import OperationError, IntegrityError, AuthorizationError
from datetime import date

class EnquiryService:
    """Handles business logic for enquiries."""
    def __init__(self, enquiry_repository: EnquiryRepository,
                 project_service: ProjectService,
                 user_repository: UserRepository,
                 application_service: ApplicationService):
        self.enquiry_repository = enquiry_repository
        self.project_service = project_service
        self.user_repository = user_repository
        self.application_service = application_service

    def find_enquiry_by_id(self, enquiry_id: int) -> Enquiry | None:
        """Finds an enquiry by its ID."""
        return self.enquiry_repository.find_by_id(enquiry_id)

    def get_enquiries_by_applicant(self, applicant_nric: str) -> list[Enquiry]:
        """Gets all enquiries submitted by a specific applicant, sorted by ID."""
        return sorted(self.enquiry_repository.find_by_applicant_nric(applicant_nric), key=lambda e: e.enquiry_id)

    def get_enquiries_for_project(self, project_name: str) -> list[Enquiry]:
        """Gets all enquiries for a specific project, sorted by ID."""
        return sorted(self.enquiry_repository.find_by_project_name(project_name), key=lambda e: e.enquiry_id)

    def get_all_enquiries(self) -> list[Enquiry]:
        """Gets all enquiries in the system, sorted by ID."""
        return sorted(self.enquiry_repository.get_all(), key=lambda e: e.enquiry_id)

    def submit_enquiry(self, applicant: Applicant, project: Project, text: str) -> Enquiry:
        """Submits a new enquiry."""
        if not text or text.isspace():
            raise OperationError("Enquiry text cannot be empty.")

        # Check if the applicant can actually view this project to enquire about it
        # Reuse the logic from ProjectService, considering current application status
        current_app = self.application_service.find_active_application_by_applicant(applicant.nric)
        viewable_projects = self.project_service.get_viewable_projects_for_applicant(applicant, current_app)

        if project.project_name not in [p.project_name for p in viewable_projects]:
             raise AuthorizationError("You cannot submit an enquiry for a project you are not able to view.")

        # Enquiry ID is assigned by the repository's add method
        new_enquiry = Enquiry(
            enquiry_id=0, # Placeholder, will be set by repo
            applicant_nric=applicant.nric,
            project_name=project.project_name,
            text=text
        )

        try:
            self.enquiry_repository.add(new_enquiry) # This assigns the ID and saves
            print(f"Enquiry (ID: {new_enquiry.enquiry_id}) submitted successfully for project {project.project_name}.")
            return new_enquiry
        except Exception as e:
            raise OperationError(f"Failed to submit enquiry: {e}")

    def edit_enquiry(self, applicant: Applicant, enquiry: Enquiry, new_text: str):
        """Edits an existing enquiry if conditions are met."""
        if enquiry.applicant_nric != applicant.nric:
            raise AuthorizationError("You can only edit your own enquiries.")
        if enquiry.is_replied():
            raise OperationError("Cannot edit an enquiry that has already been replied to.")
        if not new_text or new_text.isspace():
            raise OperationError("New enquiry text cannot be empty.")
        if new_text == enquiry.text:
             print("Info: New text is the same as the old text. No changes made.")
             return # No need to save if text hasn't changed

        enquiry.text = new_text
        try:
            self.enquiry_repository.update(enquiry)
            print(f"Enquiry ID {enquiry.enquiry_id} updated successfully.")
        except Exception as e:
            # Revert text change on failure?
            # enquiry.text = original_text # Need to store original_text
            raise OperationError(f"Failed to update enquiry: {e}")

    def delete_enquiry(self, applicant: Applicant, enquiry: Enquiry):
        """Deletes an enquiry if conditions are met."""
        if enquiry.applicant_nric != applicant.nric:
            raise AuthorizationError("You can only delete your own enquiries.")
        if enquiry.is_replied():
            raise OperationError("Cannot delete an enquiry that has already been replied to.")

        try:
            self.enquiry_repository.delete_by_id(enquiry.enquiry_id)
            print(f"Enquiry ID {enquiry.enquiry_id} deleted successfully.")
        except IntegrityError as e:
             # Should not happen if enquiry object is valid, but handle defensively
             raise OperationError(f"Failed to delete enquiry ID {enquiry.enquiry_id}: {e}")
        except Exception as e:
            raise OperationError(f"An unexpected error occurred while deleting enquiry ID {enquiry.enquiry_id}: {e}")


    def reply_to_enquiry(self, replier_user: User, enquiry: Enquiry, reply_text: str):
        """Adds a reply to an enquiry (Officer or Manager action)."""
        if not reply_text or reply_text.isspace():
            raise OperationError("Reply text cannot be empty.")
        if enquiry.is_replied():
             # Overwrite reply? Or prevent? Let's prevent for now.
             raise OperationError("This enquiry has already been replied to.")

        project = self.project_service.find_project_by_name(enquiry.project_name)
        if not project:
            raise IntegrityError(f"Project '{enquiry.project_name}' associated with enquiry ID {enquiry.enquiry_id} not found.")

        replier_role = replier_user.get_role()
        can_reply = False

        if replier_role == UserRole.HDB_MANAGER:
            if project.manager_nric == replier_user.nric:
                can_reply = True
            else:
                raise AuthorizationError("Managers can only reply to enquiries for projects they manage.")
        elif replier_role == UserRole.HDB_OFFICER:
            # TODO: Integrate with RegistrationService for full check
            handled_names = self.project_service.get_handled_project_names_for_officer(replier_user.nric)
            if project.project_name in handled_names:
                can_reply = True
            else:
                raise AuthorizationError("Officers can only reply to enquiries for projects they handle.")
        else:
            # Applicants cannot reply
            raise AuthorizationError("Only HDB Managers or Officers can reply to enquiries.")

        if not can_reply:
             # This case should be caught above, but defensive check
             raise AuthorizationError("You do not have permission to reply to this enquiry.")

        # Format the reply string
        reply_prefix = f"[{replier_role.name} - {replier_user.name} @ {date.today().strftime('%Y-%m-%d')}]:"
        enquiry.reply = f"{reply_prefix} {reply_text}"

        try:
            self.enquiry_repository.update(enquiry)
            print(f"Reply added to enquiry ID {enquiry.enquiry_id} by {replier_user.name}.")
        except Exception as e:
            enquiry.reply = "" # Revert reply on failure
            raise OperationError(f"Failed to save reply for enquiry ID {enquiry.enquiry_id}: {e}")