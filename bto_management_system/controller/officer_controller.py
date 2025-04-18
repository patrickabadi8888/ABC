from typing import List, Tuple, Optional, Type
from .base_role_controller import BaseRoleController
from .interfaces.iaction import IAction
# Import both Applicant and Officer specific actions
from .actions.applicant_actions import (
    ViewProjectsApplicantAction, ApplyForProjectAction, ViewApplicationStatusAction,
    RequestWithdrawalAction, SubmitEnquiryAction, ViewMyEnquiriesAction,
    EditMyEnquiryAction, DeleteMyEnquiryAction
)
from .actions.officer_actions import (
    RegisterForProjectOfficerAction, ViewMyOfficerRegistrationsAction,
    ViewHandledProjectsOfficerAction, ViewReplyEnquiriesOfficerAction,
    BookFlatAction, GenerateReceiptAction
)

class OfficerController(BaseRoleController): # Can inherit from ApplicantController if structure allows, or BaseRoleController
    """Controller for HDB Officer users."""

    def _build_menu(self):
        # Officers have Applicant actions + their own
        self._menu_definition: List[Tuple[str, Optional[Type[IAction]]]] = [
            # Applicant Actions (reuse or alias)
            ("View/Filter Projects", ViewProjectsApplicantAction), # Officer uses same view logic as Applicant
            ("Apply for Project", ApplyForProjectAction),
            ("View My Application Status", ViewApplicationStatusAction),
            ("Request Application Withdrawal", RequestWithdrawalAction),
            ("--- Enquiries (Personal) ---", None),
            ("Submit Enquiry", SubmitEnquiryAction),
            ("View My Enquiries", ViewMyEnquiriesAction),
            ("Edit My Enquiry", EditMyEnquiryAction),
            ("Delete My Enquiry", DeleteMyEnquiryAction),
            # Officer Specific Actions
            ("--- Officer Actions ---", None),
            ("Register for Project as Officer", RegisterForProjectOfficerAction),
            ("View My Officer Registrations", ViewMyOfficerRegistrationsAction),
            ("View Handled Projects Details", ViewHandledProjectsOfficerAction),
            ("View/Reply Enquiries (Handled Projects)", ViewReplyEnquiriesOfficerAction),
            ("Book Flat for Applicant", BookFlatAction),
            ("Generate Booking Receipt", GenerateReceiptAction),
            # Common Actions
            *self._get_common_menu_items()
        ]