from typing import List, Optional
from .interfaces.ienquiry_service import IEnquiryService
from .interfaces.iproject_service import IProjectService # Use interface
from repository.interfaces.ienquiry_repository import IEnquiryRepository
from repository.interfaces.iuser_repository import IUserRepository
from repository.interfaces.iapplication_repository import IApplicationRepository
from model.enquiry import Enquiry
from model.applicant import Applicant
from model.user import User
from model.project import Project
from common.enums import UserRole
from common.exceptions import OperationError, IntegrityError

class EnquiryService(IEnquiryService):
    """Handles business logic related to enquiries."""
    def __init__(self, enquiry_repository: IEnquiryRepository,
                 project_service: IProjectService,
                 user_repository: IUserRepository,
                 application_repository: IApplicationRepository):
        self._enq_repo = enquiry_repository
        self._project_service = project_service
        self._user_repo = user_repository
        self._app_repo = application_repository

    def find_enquiry_by_id(self, enquiry_id: int) -> Optional[Enquiry]:
        return self._enq_repo.find_by_id(enquiry_id)

    def get_enquiries_by_applicant(self, applicant_nric: str) -> List[Enquiry]:
        return sorted(self._enq_repo.find_by_applicant(applicant_nric), key=lambda e: e.enquiry_id)

    def get_enquiries_for_project(self, project_name: str) -> List[Enquiry]:
        return sorted(self._enq_repo.find_by_project(project_name), key=lambda e: e.enquiry_id)

    def get_all_enquiries(self) -> List[Enquiry]:
        return sorted(self._enq_repo.get_all(), key=lambda e: e.enquiry_id)

    def submit_enquiry(self, applicant: Applicant, project: Project, text: str) -> Enquiry:
        if not text or text.isspace():
            raise OperationError("Enquiry text cannot be empty.")

        # Check if applicant can view the project
        current_app = self._app_repo.find_by_applicant_nric(applicant.nric)
        viewable_projects = self._project_service.get_viewable_projects_for_applicant(applicant, current_app)
        if project not in viewable_projects:
             # Check if it's the project they applied for (should be viewable)
             is_applied = current_app and current_app.project_name == project.project_name
             if not is_applied:
                  raise OperationError("You cannot submit an enquiry for a project you cannot view.")

        try:
            # Create enquiry with temporary ID 0, repository add assigns correct ID
            new_enquiry = Enquiry(0, applicant.nric, project.project_name, text)
            self._enq_repo.add(new_enquiry) # Add assigns ID
            # Defer saving
            return new_enquiry # Return enquiry with assigned ID
        except (ValueError, IntegrityError) as e:
            raise OperationError(f"Failed to submit enquiry: {e}")

    def edit_enquiry(self, applicant: Applicant, enquiry: Enquiry, new_text: str):
        if enquiry.applicant_nric != applicant.nric:
            raise OperationError("You can only edit your own enquiries.")
        try:
            enquiry.set_text(new_text) # Model validates state (not replied) and text
            self._enq_repo.update(enquiry)
            # Defer saving
        except (OperationError, ValueError, IntegrityError) as e:
            # Reverting in-memory change is difficult without original text stored here.
            raise OperationError(f"Failed to update enquiry: {e}")

    def delete_enquiry(self, applicant: Applicant, enquiry: Enquiry):
        if enquiry.applicant_nric != applicant.nric:
            raise OperationError("You can only delete your own enquiries.")
        if enquiry.is_replied():
            raise OperationError("Cannot delete a replied enquiry.")

        try:
            self._enq_repo.delete_by_id(enquiry.enquiry_id)
            # Defer saving
        except IntegrityError as e:
            raise OperationError(f"Failed to delete enquiry: {e}")

    def reply_to_enquiry(self, replier_user: User, enquiry: Enquiry, reply_text: str):
        if not reply_text or reply_text.isspace():
            raise OperationError("Reply text cannot be empty.")
        if enquiry.is_replied():
             raise OperationError("This enquiry has already been replied to.")

        project = self._project_service.find_project_by_name(enquiry.project_name)
        if not project: raise OperationError(f"Project '{enquiry.project_name}' not found.")

        user_role = replier_user.get_role()
        can_reply = False
        role_str = ""

        if user_role == UserRole.HDB_MANAGER and project.manager_nric == replier_user.nric:
            can_reply = True; role_str = "Manager"
        elif user_role == UserRole.HDB_OFFICER:
            handled = self._project_service.get_handled_project_names_for_officer(replier_user.nric)
            if project.project_name in handled:
                can_reply = True; role_str = "Officer"

        if not can_reply:
             raise OperationError("You do not have permission to reply to this enquiry.")

        formatted_reply = f"[{role_str} - {replier_user.name}]: {reply_text}"
        try:
            enquiry.set_reply(formatted_reply)
            self._enq_repo.update(enquiry)
            # Defer saving
        except (ValueError, IntegrityError) as e:
            # enquiry.set_reply("") # Revert attempt
            raise OperationError(f"Failed to save reply: {e}")