# controllers/applicant_controller.py
from .base_controller import BaseController
from models.user import User, Applicant
from models.roles import UserRole
from services.project_service import ProjectService
from services.application_service import ApplicationService
from services.enquiry_service import EnquiryService
from services.auth_service import AuthService # For user lookup in selections
from views.project_view import ProjectView
from views.application_view import ApplicationView
from views.enquiry_view import EnquiryView
from views.base_view import BaseView
from utils.exceptions import OperationError, AuthorizationError, IntegrityError
from utils import helpers # For yes/no input

class ApplicantController(BaseController):
    """Controller for actions available to Applicants."""
    def __init__(self, current_user: User, services: dict, views: dict):
        # Ensure user is appropriate type (optional but good practice)
        if not isinstance(current_user, Applicant):
             raise TypeError("ApplicantController requires an Applicant user.")
        super().__init__(current_user, services, views)

    def run_menu(self):
        """Displays the Applicant menu and handles actions."""
        actions = {
            "View / Filter Available Projects": self.handle_view_projects,
            "Apply for Project": self.handle_apply_for_project,
            "View My Application Status": self.handle_view_my_application_status,
            "Request Application Withdrawal": self.handle_request_withdrawal,
            "Submit Enquiry": self.handle_submit_enquiry,
            "View My Enquiries": self.handle_view_my_enquiries,
            "Edit My Enquiry": self.handle_edit_my_enquiry,
            "Delete My Enquiry": self.handle_delete_my_enquiry,
            **self._get_common_menu_actions() # Add common actions
        }
        options = list(actions.keys())
        base_view: BaseView = self.views['base']

        choice_index = base_view.display_menu("Applicant Menu", options)
        if choice_index is None: return None # No options available case

        selected_action_name = options[choice_index - 1]
        action_method = actions[selected_action_name]

        try:
             return action_method() # Execute chosen action
        except (OperationError, AuthorizationError, IntegrityError) as e:
             base_view.display_message(f"{e}", error=True)
             return None # Stay in the menu loop after error
        except KeyboardInterrupt:
             print("\nOperation cancelled by user.")
             return None # Stay in the menu loop
        except Exception as e:
             # Log full traceback for unexpected errors
             import traceback
             print("\n--- UNEXPECTED ERROR ---")
             traceback.print_exc()
             print("------------------------")
             base_view.display_message(f"An unexpected error occurred: {e}", error=True)
             return None # Stay in the menu loop

    # --- Action Handlers ---

    def handle_view_projects(self):
        project_service: ProjectService = self.services['project']
        app_service: ApplicationService = self.services['app']
        project_view: ProjectView = self.views['project']
        base_view: BaseView = self.views['base']

        current_app = app_service.find_active_application_by_applicant(self.current_user.nric)
        # Get projects viewable by this specific applicant
        projects = project_service.get_viewable_projects_for_applicant(self.current_user, current_app)

        # Apply user's stored filters
        filtered_projects = project_service.filter_projects(
            projects, **self.user_filters
        )

        base_view.display_message(f"Current Project Filters: {self.user_filters or 'None'}", info=True)
        if not filtered_projects:
            base_view.display_message("No projects match your current filters or eligibility.")
        else:
            base_view.display_message("Displaying projects you are eligible to view/apply for:")
            is_single = self.current_user.marital_status.lower() == "single"
            for project in filtered_projects:
                # Pass user role and single status for appropriate display
                project_view.display_project_details(project, UserRole.APPLICANT, is_single)

        # Option to update filters
        if helpers.get_yes_no_input("\nUpdate filters?"):
            self.user_filters = project_view.prompt_project_filters(self.user_filters)
            base_view.display_message("Filters updated. View projects again to see changes.", info=True)

    def handle_apply_for_project(self):
        app_service: ApplicationService = self.services['app']
        project_service: ProjectService = self.services['project']
        project_view: ProjectView = self.views['project']
        app_view: ApplicationView = self.views['app']
        base_view: BaseView = self.views['base']

        # Check if already applied (re-check inside service, but good pre-check)
        if app_service.find_active_application_by_applicant(self.current_user.nric):
            raise OperationError("You already have an active BTO application.")

        # Get projects eligible for application (visible AND active period)
        potential_projects = project_service.get_viewable_projects_for_applicant(self.current_user)
        # Filter further for those actually open for application right now
        selectable_projects = [p for p in potential_projects if p.is_currently_active_for_application()]

        project_to_apply = project_view.select_project(selectable_projects, action_verb="apply for")
        if not project_to_apply:
             base_view.display_message("Application cancelled.", info=True)
             return

        # Prompt for flat type based on project and applicant eligibility
        flat_type = app_view.prompt_flat_type_selection(project_to_apply, self.current_user)
        if flat_type is None:
             base_view.display_message("Flat type selection cancelled or unavailable. Application aborted.", info=True)
             return

        # Confirm before applying
        if helpers.get_yes_no_input(f"Confirm application for {flat_type}-Room flat in '{project_to_apply.project_name}'?"):
             # Call service to handle application logic and checks
             app_service.apply_for_project(self.current_user, project_to_apply, flat_type)
             base_view.display_message("Application submitted successfully!", info=True)
        else:
             base_view.display_message("Application cancelled.", info=True)


    def handle_view_my_application_status(self):
        app_service: ApplicationService = self.services['app']
        project_service: ProjectService = self.services['project']
        app_view: ApplicationView = self.views['app']
        base_view: BaseView = self.views['base']

        application = app_service.find_active_application_by_applicant(self.current_user.nric)
        if not application:
            base_view.display_message("You do not have an active BTO application.")
            return

        # Need project details to display alongside application status
        project = project_service.find_project_by_name(application.project_name)
        if not project:
            # Data inconsistency - log or raise internal error?
            raise IntegrityError(f"Error: Project '{application.project_name}' associated with your application not found. Please contact support.")

        app_view.display_application_status(application, project, self.current_user)

    def handle_request_withdrawal(self):
        app_service: ApplicationService = self.services['app']
        base_view: BaseView = self.views['base']

        application = app_service.find_active_application_by_applicant(self.current_user.nric)
        if not application:
            raise OperationError("You do not have an active BTO application to withdraw.")

        if application.request_withdrawal:
             base_view.display_message("You have already requested withdrawal for this application.", info=True)
             return

        # Confirm action
        if helpers.get_yes_no_input(f"Request withdrawal for application to '{application.project_name}' (Status: {application.status})?"):
            app_service.request_withdrawal(application)
            base_view.display_message("Withdrawal requested successfully. Pending Manager review.", info=True)
        else:
            base_view.display_message("Withdrawal request cancelled.", info=True)


    def handle_submit_enquiry(self):
        enq_service: EnquiryService = self.services['enq']
        project_service: ProjectService = self.services['project']
        app_service: ApplicationService = self.services['app'] # Needed for viewable check
        project_view: ProjectView = self.views['project']
        enq_view: EnquiryView = self.views['enq']
        base_view: BaseView = self.views['base']

        # Determine which projects the user can enquire about (viewable projects)
        current_app = app_service.find_active_application_by_applicant(self.current_user.nric)
        viewable_projects = project_service.get_viewable_projects_for_applicant(self.current_user, current_app)

        project_to_enquire = project_view.select_project(viewable_projects, action_verb="submit enquiry for")
        if not project_to_enquire:
             base_view.display_message("Enquiry submission cancelled.", info=True)
             return

        text = enq_view.prompt_enquiry_text()
        if text is None: # User cancelled input
             base_view.display_message("Enquiry submission cancelled.", info=True)
             return

        # Submit via service
        enq_service.submit_enquiry(self.current_user, project_to_enquire, text)
        # Success message handled by service now

    def handle_view_my_enquiries(self):
        enq_service: EnquiryService = self.services['enq']
        project_service: ProjectService = self.services['project'] # To get project names
        enq_view: EnquiryView = self.views['enq']
        base_view: BaseView = self.views['base']

        my_enquiries = enq_service.get_enquiries_by_applicant(self.current_user.nric)
        if not my_enquiries:
            base_view.display_message("You have not submitted any enquiries.")
            return

        base_view.display_message("Your Submitted Enquiries:", info=True)
        for enquiry in my_enquiries:
            # Fetch project name for context (handle if project deleted)
            project = project_service.find_project_by_name(enquiry.project_name)
            project_display_name = project.project_name if project else f"{enquiry.project_name} (Deleted)"
            enq_view.display_enquiry_details(enquiry, project_display_name, self.current_user.name)

    def handle_edit_my_enquiry(self):
        enq_service: EnquiryService = self.services['enq']
        enq_view: EnquiryView = self.views['enq']
        base_view: BaseView = self.views['base']

        my_enquiries = enq_service.get_enquiries_by_applicant(self.current_user.nric)
        # Filter for enquiries that can be edited (not replied)
        editable_enquiries = [e for e in my_enquiries if not e.is_replied()]

        if not editable_enquiries:
             base_view.display_message("You have no enquiries that can be edited (either none exist or all have been replied to).")
             return

        enquiry_to_edit = enq_view.select_enquiry(editable_enquiries, action_verb="edit")
        if not enquiry_to_edit:
             base_view.display_message("Enquiry edit cancelled.", info=True)
             return

        new_text = enq_view.prompt_enquiry_text(current_text=enquiry_to_edit.text)
        if new_text is None: # User cancelled input
             base_view.display_message("Enquiry edit cancelled.", info=True)
             return

        # Call service to handle edit logic
        enq_service.edit_enquiry(self.current_user, enquiry_to_edit, new_text)
        # Success message handled by service

    def handle_delete_my_enquiry(self):
        enq_service: EnquiryService = self.services['enq']
        enq_view: EnquiryView = self.views['enq']
        base_view: BaseView = self.views['base']

        my_enquiries = enq_service.get_enquiries_by_applicant(self.current_user.nric)
        # Filter for enquiries that can be deleted (not replied)
        deletable_enquiries = [e for e in my_enquiries if not e.is_replied()]

        if not deletable_enquiries:
             base_view.display_message("You have no enquiries that can be deleted (either none exist or all have been replied to).")
             return

        enquiry_to_delete = enq_view.select_enquiry(deletable_enquiries, action_verb="delete")
        if not enquiry_to_delete:
            base_view.display_message("Enquiry deletion cancelled.", info=True)
            return

        # Confirm deletion
        if helpers.get_yes_no_input(f"Are you sure you want to delete Enquiry ID {enquiry_to_delete.enquiry_id}? This cannot be undone."):
            enq_service.delete_enquiry(self.current_user, enquiry_to_delete)
            # Success message handled by service
        else:
            base_view.display_message("Enquiry deletion cancelled.", info=True)