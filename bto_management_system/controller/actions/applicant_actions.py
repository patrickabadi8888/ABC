from typing import Dict, Any, Optional, List
from controller.interfaces.iaction import IAction
from service.project_service import ProjectService
from service.application_service import ApplicationService
from service.enquiry_service import EnquiryService
from repository.interfaces.iuser_repository import IUserRepository
from view.project_view import ProjectView
from view.application_view import ApplicationView
from view.enquiry_view import EnquiryView
from view.base_view import BaseView
from utils.input_util import InputUtil
from common.enums import UserRole
from model.applicant import Applicant
from model.project import Project
from common.enums import ApplicationStatus
from common.exceptions import OperationError

# Helper function within this module
def _get_viewable_projects(applicant: Applicant, services: Dict[str, Any]) -> List[Project]:
    project_service: ProjectService = services['project']
    app_service: ApplicationService = services['app']
    current_app = app_service.find_application_by_applicant(applicant.nric)
    return project_service.get_viewable_projects_for_applicant(applicant, current_app)

class ViewProjectsApplicantAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[Applicant] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        project_service: ProjectService = services['project']
        project_view: ProjectView = views['project']
        base_view: BaseView = views['base']
        user_filters = controller_data.get('filters', {}) if controller_data else {}

        projects = _get_viewable_projects(current_user, services)
        filtered_projects = project_service.filter_projects(projects, **user_filters)

        base_view.display_message(f"Current Filters: {user_filters or 'None'}", info=True)
        if not filtered_projects:
            base_view.display_message("No projects match your criteria or eligibility.")
        else:
            base_view.display_message("Displaying projects you are eligible to view/apply for:")
            for project in filtered_projects:
                project_view.display_project_details(project, UserRole.APPLICANT, current_user.marital_status)

        if InputUtil.get_yes_no_input("Update filters?"):
            new_filters = project_view.prompt_project_filters(user_filters)
            if controller_data is not None: controller_data['filters'] = new_filters # Update shared filters
            base_view.display_message("Filters updated. View projects again to see changes.", info=True)
        return None

class ApplyForProjectAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[Applicant] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        app_service: ApplicationService = services['app']
        project_view: ProjectView = views['project']
        app_view: ApplicationView = views['app']
        base_view: BaseView = views['base']

        potential_projects = _get_viewable_projects(current_user, services)
        selectable_projects = [p for p in potential_projects if p.is_currently_visible_and_active()]

        project_to_apply = project_view.select_project(selectable_projects, action_verb="apply for")
        if not project_to_apply: return None

        flat_type = app_view.prompt_flat_type_selection(project_to_apply, current_user)
        if flat_type is None: return None

        app_service.apply_for_project(current_user, project_to_apply, flat_type)
        base_view.display_message(f"Application submitted successfully for {flat_type.to_string()} in '{project_to_apply.project_name}'.", info=True)
        return None

class ViewApplicationStatusAction(IAction):
     def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[Applicant] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        app_service: ApplicationService = services['app']
        project_service: ProjectService = services['project']
        app_view: ApplicationView = views['app']
        base_view: BaseView = views['base']
        user_repo: IUserRepository = services['user'] # Needed for past apps view

        application = app_service.find_application_by_applicant(current_user.nric)
        if not application:
            base_view.display_message("You do not have an active BTO application.")
            all_apps = app_service.get_all_applications_by_applicant(current_user.nric) # Use specific method
            unsuccessful = [app for app in all_apps if app.status == ApplicationStatus.UNSUCCESSFUL]
            if unsuccessful:
                 base_view.display_message("You have past unsuccessful applications:")
                 app_view.select_application(unsuccessful, user_repo, action_verb="view past") # Show list
            return None

        project = project_service.find_project_by_name(application.project_name)
        if not project:
            base_view.display_message(f"Error: Project '{application.project_name}' not found.", error=True)
            app_view.display_dict("Application Data (Project Missing)", application.to_csv_dict())
            return None

        app_view.display_application_details(application, project, current_user)
        return None

class RequestWithdrawalAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[Applicant] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        app_service: ApplicationService = services['app']
        base_view: BaseView = views['base']

        application = app_service.find_application_by_applicant(current_user.nric)
        if not application:
            raise OperationError("You do not have an active BTO application to withdraw.")

        prompt = f"Confirm request withdrawal for application to '{application.project_name}'? (Status: {application.status.value})"
        if InputUtil.get_yes_no_input(prompt):
            app_service.request_withdrawal(application)
            base_view.display_message("Withdrawal requested. Pending Manager action.", info=True)
        return None

class SubmitEnquiryAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[Applicant] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        enq_service: EnquiryService = services['enq']
        project_view: ProjectView = views['project']
        enq_view: EnquiryView = views['enq']
        base_view: BaseView = views['base']

        viewable_projects = _get_viewable_projects(current_user, services)
        project_to_enquire = project_view.select_project(viewable_projects, action_verb="submit enquiry for")
        if not project_to_enquire: return None

        text = enq_view.prompt_enquiry_text()
        if not text: return None

        enq_service.submit_enquiry(current_user, project_to_enquire, text)
        base_view.display_message("Enquiry submitted successfully.", info=True)
        return None

class ViewMyEnquiriesAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[Applicant] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        enq_service: EnquiryService = services['enq']
        project_service: ProjectService = services['project']
        enq_view: EnquiryView = views['enq']
        base_view: BaseView = views['base']

        my_enquiries = enq_service.get_enquiries_by_applicant(current_user.nric)
        if not my_enquiries:
            base_view.display_message("You have not submitted any enquiries.")
            return None

        base_view.display_message("Your Submitted Enquiries:", info=True)
        for enquiry in my_enquiries:
            project = project_service.find_project_by_name(enquiry.project_name)
            p_name = project.project_name if project else f"Unknown/Deleted ({enquiry.project_name})"
            enq_view.display_enquiry_details(enquiry, p_name, current_user.name)
        return None

class EditMyEnquiryAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[Applicant] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        enq_service: EnquiryService = services['enq']
        enq_view: EnquiryView = views['enq']
        base_view: BaseView = views['base']

        my_enquiries = enq_service.get_enquiries_by_applicant(current_user.nric)
        editable = [e for e in my_enquiries if not e.is_replied()]

        enquiry_to_edit = enq_view.select_enquiry(editable, action_verb="edit")
        if not enquiry_to_edit: return None

        new_text = enq_view.prompt_enquiry_text(current_text=enquiry_to_edit.text)
        if not new_text: return None

        enq_service.edit_enquiry(current_user, enquiry_to_edit, new_text)
        base_view.display_message(f"Enquiry ID {enquiry_to_edit.enquiry_id} updated.", info=True)
        return None

class DeleteMyEnquiryAction(IAction):
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[Applicant] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        enq_service: EnquiryService = services['enq']
        enq_view: EnquiryView = views['enq']
        base_view: BaseView = views['base']

        my_enquiries = enq_service.get_enquiries_by_applicant(current_user.nric)
        deletable = [e for e in my_enquiries if not e.is_replied()]

        enquiry_to_delete = enq_view.select_enquiry(deletable, action_verb="delete")
        if not enquiry_to_delete: return None

        if InputUtil.get_yes_no_input(f"Delete Enquiry ID {enquiry_to_delete.enquiry_id}?"):
            enq_service.delete_enquiry(current_user, enquiry_to_delete)
            base_view.display_message(f"Enquiry ID {enquiry_to_delete.enquiry_id} deleted.", info=True)
        return None