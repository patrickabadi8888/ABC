from typing import List, Tuple, Optional, Type
from .base_role_controller import BaseRoleController
from .interfaces.iaction import IAction
from .actions.manager_actions import (
    CreateProjectAction, EditProjectAction, DeleteProjectAction, ToggleProjectVisibilityAction,
    ViewAllProjectsManagerAction, ViewMyProjectsManagerAction, ViewOfficerRegistrationsAction,
    ApproveOfficerRegistrationAction, RejectOfficerRegistrationAction, ViewApplicationsAction,
    ApproveApplicationAction, RejectApplicationAction, ApproveWithdrawalAction, RejectWithdrawalAction,
    GenerateBookingReportAction, ViewAllEnquiriesManagerAction, ViewReplyEnquiriesManagerAction
)

class ManagerController(BaseRoleController):
    """Controller for HDB Manager users."""

    def _build_menu(self):
        self._menu_definition: List[Tuple[str, Optional[Type[IAction]]]] = [
            ("--- Project Management ---", None),
            ("Create Project", CreateProjectAction),
            ("Edit Project", EditProjectAction),
            ("Delete Project", DeleteProjectAction),
            ("Toggle Project Visibility", ToggleProjectVisibilityAction),
            ("View All/Filter Projects", ViewAllProjectsManagerAction),
            ("View My Managed Projects", ViewMyProjectsManagerAction),
            ("--- Officer Management ---", None),
            ("View Officer Registrations (Project)", ViewOfficerRegistrationsAction),
            ("Approve Officer Registration", ApproveOfficerRegistrationAction),
            ("Reject Officer Registration", RejectOfficerRegistrationAction),
            ("--- Application Management ---", None),
            ("View Applications (Project)", ViewApplicationsAction),
            ("Approve Application", ApproveApplicationAction),
            ("Reject Application", RejectApplicationAction),
            ("Approve Withdrawal Request", ApproveWithdrawalAction),
            ("Reject Withdrawal Request", RejectWithdrawalAction),
            ("--- Reporting & Enquiries ---", None),
            ("Generate Booking Report", GenerateBookingReportAction),
            ("View All Enquiries", ViewAllEnquiriesManagerAction),
            ("View/Reply Enquiries (Managed Projects)", ViewReplyEnquiriesManagerAction),
            *self._get_common_menu_items()
        ]