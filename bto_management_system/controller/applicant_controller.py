from typing import List, Tuple, Optional, Type
from .base_role_controller import BaseRoleController
from .interfaces.iaction import IAction
from .actions.applicant_actions import (
    ViewProjectsApplicantAction, ApplyForProjectAction, ViewApplicationStatusAction,
    RequestWithdrawalAction, SubmitEnquiryAction, ViewMyEnquiriesAction,
    EditMyEnquiryAction, DeleteMyEnquiryAction
)

class ApplicantController(BaseRoleController):
    """Controller for Applicant users."""

    def _build_menu(self):
        self._menu_definition: List[Tuple[str, Optional[Type[IAction]]]] = [
            ("View/Filter Projects", ViewProjectsApplicantAction),
            ("Apply for Project", ApplyForProjectAction),
            ("View My Application Status", ViewApplicationStatusAction),
            ("Request Application Withdrawal", RequestWithdrawalAction),
            ("--- Enquiries ---", None),
            ("Submit Enquiry", SubmitEnquiryAction),
            ("View My Enquiries", ViewMyEnquiriesAction),
            ("Edit My Enquiry", EditMyEnquiryAction),
            ("Delete My Enquiry", DeleteMyEnquiryAction),
            *self._get_common_menu_items() # Add common actions at the end
        ]