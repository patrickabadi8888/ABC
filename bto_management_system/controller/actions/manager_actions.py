from typing import Dict, Any, Optional, List, Tuple
from controller.interfaces.iaction import IAction
from service.project_service import ProjectService
from service.application_service import ApplicationService
from service.registration_service import RegistrationService
from service.enquiry_service import EnquiryService
from service.report_service import ReportService
from repository.interfaces.iuser_repository import IUserRepository
from view.project_view import ProjectView
from view.application_view import ApplicationView
from view.officer_view import OfficerView
from view.manager_view import ManagerView
from view.enquiry_view import EnquiryView
from view.report_view import ReportView
from view.base_view import BaseView
from utils.input_util import InputUtil
from common.enums import UserRole, RegistrationStatus, ApplicationStatus
from common.exceptions import OperationError, IntegrityError
from model.hdb_manager import HDBManager
from model.project import Project
from model.registration import Registration
from model.application import Application
from model.enquiry import Enquiry
from model.user import User # For lookups

# Helper function within this module
def _select_managed_project(manager: HDBManager, services: Dict[str, Any], views: Dict[str, Any], action_verb="manage") -> Optional[Project]:
    project_service: ProjectService = services['project']
    project_view: ProjectView = views['project']
    base_view: BaseView = views['base']
    my_projects = project_service.get_projects_by_manager(manager.nric)
    if not my_projects:
        base_view.display_message("You do not manage any projects.")
        return None
    return project_view.select_project(my_projects, action_verb=action_verb)

class CreateProjectAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBManager] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        project_service: ProjectService = services['project']
        project_view: ProjectView = views['project']
        base_view: BaseView = views['base']

        details = project_view.prompt_create_project_details()
        if not details: return None

        new_project = project_service.create_project(
            current_user, details['name'], details['neighborhood'],
            details['n1'], details['p1'], details['n2'], details['p2'],
            details['od'], details['cd'], details['slot']
        )
        base_view.display_message(f"Project '{new_project.project_name}' created.", info=True)
        return None

class EditProjectAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBManager] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        project_service: ProjectService = services['project']
        project_view: ProjectView = views['project']
        base_view: BaseView = views['base']

        project_to_edit = _select_managed_project(current_user, services, views, action_verb="edit")
        if not project_to_edit: return None

        updates = project_view.prompt_edit_project_details(project_to_edit)
        if updates is None: # Cancelled or error
             if isinstance(updates, dict) and not updates: # Explicitly check for empty dict (no changes)
                 base_view.display_message("No changes entered.", info=True)
             return None

        project_service.edit_project(current_user, project_to_edit, updates)
        base_view.display_message(f"Project '{project_to_edit.project_name}' updated.", info=True)
        return None

class DeleteProjectAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBManager] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        project_service: ProjectService = services['project']
        base_view: BaseView = views['base']

        project_to_delete = _select_managed_project(current_user, services, views, action_verb="delete")
        if not project_to_delete: return None

        warning = f"Delete project '{project_to_delete.project_name}'? This cannot be undone. Proceed?"
        if InputUtil.get_yes_no_input(warning):
            project_service.delete_project(current_user, project_to_delete)
            base_view.display_message(f"Project '{project_to_delete.project_name}' deleted.", info=True)
        else:
            base_view.display_message("Deletion cancelled.", info=True)
        return None

class ToggleProjectVisibilityAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBManager] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        project_service: ProjectService = services['project']
        base_view: BaseView = views['base']

        project_to_toggle = _select_managed_project(current_user, services, views, action_verb="toggle visibility for")
        if not project_to_toggle: return None

        new_status = project_service.toggle_project_visibility(current_user, project_to_toggle)
        base_view.display_message(f"Project '{project_to_toggle.project_name}' visibility set to {new_status}.", info=True)
        return None

class ViewAllProjectsManagerAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBManager] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        project_service: ProjectService = services['project']
        project_view: ProjectView = views['project']
        base_view: BaseView = views['base']
        user_filters = controller_data.get('filters', {}) if controller_data else {}

        all_projects = project_service.get_all_projects()
        filtered_projects = project_service.filter_projects(all_projects, **user_filters)

        base_view.display_message(f"Current Filters: {user_filters or 'None'}", info=True)
        if not filtered_projects:
            base_view.display_message("No projects match your criteria.")
        else:
            base_view.display_message("Displaying All Projects:", info=True)
            for project in filtered_projects:
                project_view.display_project_details(project, UserRole.HDB_MANAGER)

        if InputUtil.get_yes_no_input("Update filters?"):
            new_filters = project_view.prompt_project_filters(user_filters)
            if controller_data is not None: controller_data['filters'] = new_filters
            base_view.display_message("Filters updated. View projects again.", info=True)
        return None

class ViewMyProjectsManagerAction(IAction):
     def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBManager] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        project_service: ProjectService = services['project']
        project_view: ProjectView = views['project']
        base_view: BaseView = views['base']

        my_projects = project_service.get_projects_by_manager(current_user.nric)
        if not my_projects:
            base_view.display_message("You are not managing any projects.")
            return None

        base_view.display_message("Projects You Manage:", info=True)
        for project in my_projects:
            project_view.display_project_details(project, UserRole.HDB_MANAGER)
        return None

# --- Officer Registration Management ---
class ViewOfficerRegistrationsAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBManager] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        reg_service: RegistrationService = services['reg']
        user_repo: IUserRepository = services['user']
        officer_view: OfficerView = views['officer']
        base_view: BaseView = views['base']

        project_to_view = _select_managed_project(current_user, services, views, "view officer registrations for")
        if not project_to_view: return None

        registrations = reg_service.get_registrations_for_project(project_to_view.project_name)
        if not registrations:
            base_view.display_message(f"No officer registrations for '{project_to_view.project_name}'.")
            return None

        base_view.display_message(f"Officer Registrations for '{project_to_view.project_name}':", info=True)
        officer_view.select_registration(registrations, user_repo, action_verb="view list") # Just display list
        return None

# Helper for selecting pending registrations
def _select_pending_registration(manager: HDBManager, services: Dict[str, Any], views: Dict[str, Any], action_verb="action") -> Optional[Registration]:
    reg_service: RegistrationService = services['reg']
    user_repo: IUserRepository = services['user']
    officer_view: OfficerView = views['officer']
    base_view: BaseView = views['base']
    project_service: ProjectService = services['project']

    my_projects = project_service.get_projects_by_manager(manager.nric)
    pending_regs = []
    for project in my_projects:
        pending_regs.extend(reg_service.get_registrations_for_project(project.project_name, RegistrationStatus.PENDING))

    if not pending_regs:
        base_view.display_message("No pending officer registrations found for your projects.")
        return None
    return officer_view.select_registration(pending_regs, user_repo, action_verb=action_verb)

class ApproveOfficerRegistrationAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBManager] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        reg_service: RegistrationService = services['reg']
        base_view: BaseView = views['base']
        manager_view: ManagerView = views['manager']
        user_repo: IUserRepository = services['user']
        project_service: ProjectService = services['project']

        reg_to_approve = _select_pending_registration(current_user, services, views, action_verb="approve")
        if not reg_to_approve: return None

        officer = user_repo.find_user_by_nric(reg_to_approve.officer_nric)
        project = project_service.find_project_by_name(reg_to_approve.project_name)
        if not officer or not project: raise IntegrityError("Officer or Project not found.")

        manager_view.display_officer_registration_for_approval(reg_to_approve, officer, project)
        if InputUtil.get_yes_no_input(f"Approve {officer.name} for '{project.project_name}'?"):
             reg_service.manager_approve_officer_registration(current_user, reg_to_approve)
             base_view.display_message(f"Registration for {officer.name} approved.", info=True)
        else: base_view.display_message("Approval cancelled.")
        return None

class RejectOfficerRegistrationAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBManager] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        reg_service: RegistrationService = services['reg']
        base_view: BaseView = views['base']
        manager_view: ManagerView = views['manager']
        user_repo: IUserRepository = services['user']
        project_service: ProjectService = services['project']

        reg_to_reject = _select_pending_registration(current_user, services, views, action_verb="reject")
        if not reg_to_reject: return None

        officer = user_repo.find_user_by_nric(reg_to_reject.officer_nric)
        project = project_service.find_project_by_name(reg_to_reject.project_name)
        if not officer or not project: raise IntegrityError("Officer or Project not found.")

        manager_view.display_officer_registration_for_approval(reg_to_reject, officer, project)
        if InputUtil.get_yes_no_input(f"Reject {officer.name} for '{project.project_name}'?"):
             reg_service.manager_reject_officer_registration(current_user, reg_to_reject)
             base_view.display_message(f"Registration for {officer.name} rejected.", info=True)
        else: base_view.display_message("Rejection cancelled.")
        return None

# --- Application Management ---
class ViewApplicationsAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBManager] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        app_service: ApplicationService = services['app']
        user_repo: IUserRepository = services['user']
        app_view: ApplicationView = views['app']
        base_view: BaseView = views['base']

        project_to_view = _select_managed_project(current_user, services, views, "view applications for")
        if not project_to_view: return None

        applications = app_service.get_applications_for_project(project_to_view.project_name)
        if not applications:
            base_view.display_message(f"No applications found for '{project_to_view.project_name}'.")
            return None

        base_view.display_message(f"Applications for '{project_to_view.project_name}':", info=True)
        app_view.select_application(applications, user_repo, action_verb="view list") # Just display list
        return None

# Helper for selecting pending applications
def _select_pending_application(manager: HDBManager, services: Dict[str, Any], views: Dict[str, Any], action_verb="action") -> Optional[Application]:
    app_service: ApplicationService = services['app']
    user_repo: IUserRepository = services['user']
    app_view: ApplicationView = views['app']
    base_view: BaseView = views['base']
    project_service: ProjectService = services['project']

    my_projects = project_service.get_projects_by_manager(manager.nric)
    pending_apps = []
    for project in my_projects:
        apps = app_service.get_applications_for_project(project.project_name)
        pending_apps.extend([app for app in apps if app.status == ApplicationStatus.PENDING and not app.request_withdrawal])

    if not pending_apps:
        base_view.display_message("No pending applications (without withdrawal requests) found.")
        return None
    return app_view.select_application(pending_apps, user_repo, action_verb=action_verb)

class ApproveApplicationAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBManager] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        app_service: ApplicationService = services['app']
        base_view: BaseView = views['base']
        manager_view: ManagerView = views['manager']
        user_repo: IUserRepository = services['user']
        project_service: ProjectService = services['project']

        app_to_approve = _select_pending_application(current_user, services, views, action_verb="approve")
        if not app_to_approve: return None

        applicant = user_repo.find_user_by_nric(app_to_approve.applicant_nric)
        project = project_service.find_project_by_name(app_to_approve.project_name)
        if not applicant or not project: raise IntegrityError("Applicant or Project not found.")

        manager_view.display_application_for_approval(app_to_approve, applicant, project)
        if InputUtil.get_yes_no_input(f"Approve {applicant.name}'s application for '{project.project_name}'?"):
             app_service.manager_approve_application(current_user, app_to_approve)
             base_view.display_message(f"Application for {applicant.name} approved (Status: {app_to_approve.status.value}).", info=True)
        else: base_view.display_message("Approval cancelled.")
        return None

class RejectApplicationAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBManager] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        app_service: ApplicationService = services['app']
        base_view: BaseView = views['base']
        manager_view: ManagerView = views['manager']
        user_repo: IUserRepository = services['user']
        project_service: ProjectService = services['project']

        app_to_reject = _select_pending_application(current_user, services, views, action_verb="reject")
        if not app_to_reject: return None

        applicant = user_repo.find_user_by_nric(app_to_reject.applicant_nric)
        project = project_service.find_project_by_name(app_to_reject.project_name)
        if not applicant or not project: raise IntegrityError("Applicant or Project not found.")

        manager_view.display_application_for_approval(app_to_reject, applicant, project)
        if InputUtil.get_yes_no_input(f"Reject {applicant.name}'s application for '{project.project_name}'?"):
             app_service.manager_reject_application(current_user, app_to_reject)
             base_view.display_message(f"Application for {applicant.name} rejected.", info=True)
        else: base_view.display_message("Rejection cancelled.")
        return None

# Helper for selecting applications with withdrawal requests
def _select_withdrawal_request(manager: HDBManager, services: Dict[str, Any], views: Dict[str, Any], action_verb="action") -> Optional[Application]:
    app_service: ApplicationService = services['app']
    user_repo: IUserRepository = services['user']
    app_view: ApplicationView = views['app']
    base_view: BaseView = views['base']
    project_service: ProjectService = services['project']

    my_projects = project_service.get_projects_by_manager(manager.nric)
    apps_with_request = []
    for project in my_projects:
        apps = app_service.get_applications_for_project(project.project_name)
        apps_with_request.extend([app for app in apps if app.request_withdrawal])

    if not apps_with_request:
        base_view.display_message("No pending withdrawal requests found.")
        return None
    return app_view.select_application(apps_with_request, user_repo, action_verb=action_verb)

class ApproveWithdrawalAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBManager] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        app_service: ApplicationService = services['app']
        base_view: BaseView = views['base']
        manager_view: ManagerView = views['manager']
        user_repo: IUserRepository = services['user']
        project_service: ProjectService = services['project']

        app_to_action = _select_withdrawal_request(current_user, services, views, action_verb="approve withdrawal for")
        if not app_to_action: return None

        applicant = user_repo.find_user_by_nric(app_to_action.applicant_nric)
        project = project_service.find_project_by_name(app_to_action.project_name)
        if not applicant or not project: raise IntegrityError("Applicant or Project not found.")

        manager_view.display_withdrawal_request_for_approval(app_to_action, applicant, project)
        if InputUtil.get_yes_no_input(f"Approve withdrawal for {applicant.name} (Project: {project.project_name})?"):
             app_service.manager_approve_withdrawal(current_user, app_to_action)
             base_view.display_message(f"Withdrawal for {applicant.name} approved. Status set to UNSUCCESSFUL.", info=True)
        else: base_view.display_message("Approval cancelled.")
        return None

class RejectWithdrawalAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBManager] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        app_service: ApplicationService = services['app']
        base_view: BaseView = views['base']
        manager_view: ManagerView = views['manager']
        user_repo: IUserRepository = services['user']
        project_service: ProjectService = services['project']

        app_to_action = _select_withdrawal_request(current_user, services, views, action_verb="reject withdrawal for")
        if not app_to_action: return None

        applicant = user_repo.find_user_by_nric(app_to_action.applicant_nric)
        project = project_service.find_project_by_name(app_to_action.project_name)
        if not applicant or not project: raise IntegrityError("Applicant or Project not found.")

        manager_view.display_withdrawal_request_for_approval(app_to_action, applicant, project)
        if InputUtil.get_yes_no_input(f"Reject withdrawal for {applicant.name} (Project: {project.project_name})?"):
             app_service.manager_reject_withdrawal(current_user, app_to_action)
             base_view.display_message(f"Withdrawal request for {applicant.name} rejected.", info=True)
        else: base_view.display_message("Rejection cancelled.")
        return None

# --- Reporting & Enquiries ---
class GenerateBookingReportAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBManager] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        report_service: ReportService = services['report']
        report_view: ReportView = views['report']

        filters = report_view.prompt_report_filters()
        report_data = report_service.generate_booking_report_data(**filters)
        headers = ["NRIC", "Applicant Name", "Age", "Marital Status", "Flat Type", "Project Name", "Neighborhood"]
        report_view.display_report("Booking Report", report_data, headers)
        return None

class ViewAllEnquiriesManagerAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBManager] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        enq_service: EnquiryService = services['enq']
        user_repo: IUserRepository = services['user']
        project_service: ProjectService = services['project']
        enq_view: EnquiryView = views['enq']
        base_view: BaseView = views['base']

        all_enquiries = enq_service.get_all_enquiries()
        if not all_enquiries:
            base_view.display_message("There are no enquiries in the system.")
            return None

        base_view.display_message("All System Enquiries:", info=True)
        for enquiry in all_enquiries:
            applicant = user_repo.find_user_by_nric(enquiry.applicant_nric)
            applicant_name = applicant.name if applicant else "Unknown"
            project = project_service.find_project_by_name(enquiry.project_name)
            p_name = project.project_name if project else f"Unknown/Deleted ({enquiry.project_name})"
            enq_view.display_enquiry_details(enquiry, p_name, applicant_name)
        return None

# Helper for manager enquiry actions
def _get_enquiries_for_manager(manager: HDBManager, services: Dict[str, Any]) -> List[Tuple[Enquiry, str]]:
    enq_service: EnquiryService = services['enq']
    project_service: ProjectService = services['project']
    user_repo: IUserRepository = services['user']
    managed_names = {p.project_name for p in project_service.get_projects_by_manager(manager.nric)}
    relevant = []
    if not managed_names: return relevant
    for enq in enq_service.get_all_enquiries():
        if enq.project_name in managed_names:
            applicant = user_repo.find_user_by_nric(enq.applicant_nric)
            applicant_name = applicant.name if applicant else "Unknown"
            relevant.append((enq, applicant_name))
    return relevant

class ViewReplyEnquiriesManagerAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBManager] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        enq_service: EnquiryService = services['enq']
        enq_view: EnquiryView = views['enq']
        base_view: BaseView = views['base']
        project_service: ProjectService = services['project']

        relevant_data = _get_enquiries_for_manager(current_user, services)
        if not relevant_data:
            base_view.display_message("No enquiries found for the projects you manage.")
            return None

        unreplied = [e for e, name in relevant_data if not e.is_replied()]
        base_view.display_message("Enquiries for Projects You Manage:", info=True)
        for enquiry, applicant_name in relevant_data:
             project = project_service.find_project_by_name(enquiry.project_name)
             p_name = project.project_name if project else f"Unknown/Deleted ({enquiry.project_name})"
             enq_view.display_enquiry_details(enquiry, p_name, applicant_name)

        if not unreplied:
            base_view.display_message("\nNo unreplied enquiries requiring action.")
            return None

        if InputUtil.get_yes_no_input("\nReply to an unreplied enquiry?"):
            enquiry_to_reply = enq_view.select_enquiry(unreplied, action_verb="reply to")
            if enquiry_to_reply:
                reply_text = enq_view.prompt_reply_text()
                if reply_text:
                    enq_service.reply_to_enquiry(current_user, enquiry_to_reply, reply_text)
                    base_view.display_message(f"Reply submitted for Enquiry ID {enquiry_to_reply.enquiry_id}.", info=True)
        return None