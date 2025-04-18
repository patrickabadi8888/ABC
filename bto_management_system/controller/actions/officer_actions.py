from typing import Dict, Any, Optional, List, Tuple
from controller.interfaces.iaction import IAction
from service.project_service import ProjectService
from service.application_service import ApplicationService
from service.registration_service import RegistrationService
from service.enquiry_service import EnquiryService
from repository.interfaces.iuser_repository import IUserRepository
from view.project_view import ProjectView
from view.officer_view import OfficerView
from view.enquiry_view import EnquiryView
from view.base_view import BaseView
from utils.input_util import InputUtil
from common.enums import UserRole, ApplicationStatus
from common.exceptions import OperationError, IntegrityError
from model.hdb_officer import HDBOfficer
from model.project import Project
from model.registration import Registration
from model.enquiry import Enquiry
from model.application import Application
from model.user import User # For applicant lookup

# Inherit Applicant actions if Officer can do everything Applicant can
from .applicant_actions import (
    ViewProjectsApplicantAction, ApplyForProjectAction, ViewApplicationStatusAction,
    RequestWithdrawalAction, SubmitEnquiryAction, ViewMyEnquiriesAction,
    EditMyEnquiryAction, DeleteMyEnquiryAction
)

# Rename imported Applicant action for clarity if needed, or use as is
ViewProjectsOfficerAction = ViewProjectsApplicantAction

class RegisterForProjectOfficerAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBOfficer] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        reg_service: RegistrationService = services['reg']
        project_service: ProjectService = services['project']
        app_service: ApplicationService = services['app']
        project_view: ProjectView = views['project']
        base_view: BaseView = views['base']

        all_projects = project_service.get_all_projects()
        my_regs = {reg.project_name for reg in reg_service.get_registrations_by_officer(current_user.nric)}
        my_app_projects = {app.project_name for app in app_service.get_all_applications_by_applicant(current_user.nric)}

        selectable = [
            p for p in all_projects
            if p.project_name not in my_regs and \
               p.project_name not in my_app_projects and \
               p.manager_nric != current_user.nric
        ]
        # Rely on service layer for final overlap check

        project_to_register = project_view.select_project(selectable, action_verb="register for as Officer")
        if not project_to_register: return None

        reg_service.officer_register_for_project(current_user, project_to_register)
        base_view.display_message(f"Registration submitted for '{project_to_register.project_name}'. Pending Manager approval.", info=True)
        return None

class ViewMyOfficerRegistrationsAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBOfficer] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        reg_service: RegistrationService = services['reg']
        project_service: ProjectService = services['project']
        officer_view: OfficerView = views['officer']
        base_view: BaseView = views['base']

        my_regs = reg_service.get_registrations_by_officer(current_user.nric)
        if not my_regs:
            base_view.display_message("You have no officer registrations.")
            return None

        base_view.display_message("Your Officer Registrations:", info=True)
        for reg in my_regs:
            project = project_service.find_project_by_name(reg.project_name)
            p_name = project.project_name if project else f"Unknown/Deleted ({reg.project_name})"
            officer_view.display_registration_details(reg, p_name, current_user.name)
        return None

class ViewHandledProjectsOfficerAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBOfficer] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        project_service: ProjectService = services['project']
        project_view: ProjectView = views['project']
        base_view: BaseView = views['base']

        handled_names = project_service.get_handled_project_names_for_officer(current_user.nric)
        handled_projects = [p for p in project_service.get_all_projects() if p.project_name in handled_names]

        if not handled_projects:
            base_view.display_message("You are not currently assigned to handle any projects.")
            return None

        base_view.display_message("Projects You Handle (Assigned):", info=True)
        sorted_handled = sorted(handled_projects, key=lambda p: p.project_name)
        for project in sorted_handled:
             project_view.display_project_details(project, UserRole.HDB_OFFICER, current_user.marital_status)
        return None

# Helper for enquiry actions
def _get_enquiries_for_officer(officer: HDBOfficer, services: Dict[str, Any]) -> List[Tuple[Enquiry, str]]:
    enq_service: EnquiryService = services['enq']
    project_service: ProjectService = services['project']
    user_repo: IUserRepository = services['user']
    handled_names = project_service.get_handled_project_names_for_officer(officer.nric)
    relevant = []
    if not handled_names: return relevant
    for enq in enq_service.get_all_enquiries():
        if enq.project_name in handled_names:
            applicant = user_repo.find_user_by_nric(enq.applicant_nric)
            applicant_name = applicant.name if applicant else "Unknown"
            relevant.append((enq, applicant_name))
    return relevant

class ViewReplyEnquiriesOfficerAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBOfficer] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        enq_service: EnquiryService = services['enq']
        enq_view: EnquiryView = views['enq']
        base_view: BaseView = views['base']

        relevant_data = _get_enquiries_for_officer(current_user, services)
        if not relevant_data:
            base_view.display_message("No enquiries found for the projects you handle.")
            return None

        unreplied = [e for e, name in relevant_data if not e.is_replied()]
        base_view.display_message("Enquiries for Projects You Handle:", info=True)
        for enquiry, applicant_name in relevant_data:
            enq_view.display_enquiry_details(enquiry, enquiry.project_name, applicant_name)

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

# Helper for booking/receipt actions
def _prepare_receipt_data(application: Application, project: Project, applicant: User) -> dict:
    return {
        "Applicant Name": applicant.name, "NRIC": applicant.nric, "Age": applicant.age,
        "Marital Status": applicant.marital_status,
        "Flat Type Booked": application.flat_type.to_string(),
        "Project Name": project.project_name, "Neighborhood": project.neighborhood,
        "Booking Status": application.status.value
    }

class BookFlatAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBOfficer] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        app_service: ApplicationService = services['app']
        user_repo: IUserRepository = services['user']
        officer_view: OfficerView = views['officer']
        base_view: BaseView = views['base']

        applicant_nric = officer_view.prompt_applicant_nric(purpose="booking flat")
        if not applicant_nric: return None

        applicant = user_repo.find_user_by_nric(applicant_nric)
        if not applicant: raise OperationError(f"Applicant {applicant_nric} not found.")

        application = app_service.find_application_by_applicant(applicant_nric)
        if not application: raise OperationError(f"No active application found for {applicant_nric}.")
        if application.status != ApplicationStatus.SUCCESSFUL:
             raise OperationError(f"Application status is not '{ApplicationStatus.SUCCESSFUL.value}'. Cannot book.")

        prompt = f"Confirm booking {application.flat_type.to_string()} in '{application.project_name}' for {applicant.name} ({applicant.nric})?"
        if not InputUtil.get_yes_no_input(prompt):
             base_view.display_message("Booking cancelled.")
             return None

        updated_project, booked_applicant = app_service.officer_book_flat(current_user, application)
        base_view.display_message("Flat booked successfully! Unit count updated.", info=True)

        receipt_data = _prepare_receipt_data(application, updated_project, booked_applicant)
        officer_view.display_receipt(receipt_data)
        return None

class GenerateReceiptAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[HDBOfficer] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        app_service: ApplicationService = services['app']
        project_service: ProjectService = services['project']
        user_repo: IUserRepository = services['user']
        officer_view: OfficerView = views['officer']
        base_view: BaseView = views['base']

        applicant_nric = officer_view.prompt_applicant_nric(purpose="generating receipt")
        if not applicant_nric: return None

        applicant = user_repo.find_user_by_nric(applicant_nric)
        if not applicant: raise OperationError(f"Applicant {applicant_nric} not found.")

        booked_app = app_service.find_booked_application_by_applicant(applicant_nric) # Need specific method
        if not booked_app: raise OperationError(f"No booked application found for {applicant_nric}.")

        project = project_service.find_project_by_name(booked_app.project_name)
        if not project: raise IntegrityError(f"Project '{booked_app.project_name}' not found.")

        # Permission check (handled by service in book_flat, re-check here for generate)
        handled_names = project_service.get_handled_project_names_for_officer(current_user.nric)
        if project.project_name not in handled_names:
            raise OperationError(f"You do not handle project '{project.project_name}'.")

        receipt_data = _prepare_receipt_data(booked_app, project, applicant)
        officer_view.display_receipt(receipt_data)
        return None