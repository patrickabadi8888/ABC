# controllers/manager_controller.py
from .base_controller import BaseController
from models.user import User, HDBManager
from models.roles import UserRole, ApplicationStatus, RegistrationStatus
from services.project_service import ProjectService
from services.application_service import ApplicationService
from services.registration_service import RegistrationService
from services.enquiry_service import EnquiryService
from services.report_service import ReportService
from services.auth_service import AuthService # For lookups in selections
from views.project_view import ProjectView
from views.application_view import ApplicationView
from views.officer_view import OfficerView # For registration selection
from views.enquiry_view import EnquiryView
from views.report_view import ReportView
from views.base_view import BaseView
from utils.exceptions import OperationError, AuthorizationError, IntegrityError
from utils import helpers

class ManagerController(BaseController):
    """Controller for actions available to HDB Managers."""
    def __init__(self, current_user: User, services: dict, views: dict):
        if not isinstance(current_user, HDBManager):
            raise TypeError("ManagerController requires an HDBManager user.")
        super().__init__(current_user, services, views)

    def run_menu(self):
        """Displays the Manager menu and handles actions."""
        actions = {
            "--- Project Management ---": None,
            "Create New Project": self.handle_create_project,
            "Edit My Managed Project": self.handle_edit_project,
            "Delete My Managed Project": self.handle_delete_project,
            "Toggle Project Visibility": self.handle_toggle_visibility,
            "View All / Filter Projects": self.handle_view_all_projects, # View all, incl. other managers'
            "View My Managed Projects": self.handle_view_my_projects,
            "--- Officer Registration ---": None,
            "View Officer Registrations (My Projects)": self.handle_view_officer_registrations,
            "Approve Officer Registration": self.handle_approve_officer_registration,
            "Reject Officer Registration": self.handle_reject_officer_registration,
            "--- Applicant Application ---": None,
            "View Applications (My Projects)": self.handle_view_applications,
            "Approve Pending Application": self.handle_approve_application,
            "Reject Pending Application": self.handle_reject_application,
            "Approve Withdrawal Request": self.handle_approve_withdrawal,
            "Reject Withdrawal Request": self.handle_reject_withdrawal,
            "--- Reporting & Enquiries ---": None,
            "Generate Booking Report": self.handle_generate_booking_report,
            "View Enquiries (All Projects)": self.handle_view_all_enquiries, # Manager sees all
            "View/Reply Enquiries (My Projects)": self.handle_view_reply_enquiries_manager,
            "--- Account ---": None,
            **self._get_common_menu_actions()
        }

        # Filter out separators for display
        options = [k for k in actions.keys() if actions[k] is not None]
        action_map = {k: v for k, v in actions.items() if v is not None}

        base_view: BaseView = self.views['base']
        choice_index = base_view.display_menu("HDB Manager Menu", options)
        if choice_index is None: return None

        selected_action_name = options[choice_index - 1]
        action_method = action_map[selected_action_name]

        try:
            return action_method() # Execute chosen action
        except (OperationError, AuthorizationError, IntegrityError) as e:
            base_view.display_message(f"{e}", error=True)
            return None # Stay in menu
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            return None # Stay in menu
        except Exception as e:
            import traceback
            print("\n--- UNEXPECTED ERROR ---")
            traceback.print_exc()
            print("------------------------")
            base_view.display_message(f"An unexpected error occurred: {e}", error=True)
            return None # Stay in menu

    # --- Helper to select managed project ---
    def _select_managed_project(self, action_verb: str = "manage"):
        """Helper function to let the manager select one of their projects."""
        project_service: ProjectService = self.services['project']
        project_view: ProjectView = self.views['project']
        base_view: BaseView = self.views['base']

        my_projects = project_service.get_projects_by_manager(self.current_user.nric)
        if not my_projects:
            base_view.display_message("You do not currently manage any projects.")
            return None
        return project_view.select_project(my_projects, action_verb=action_verb)

    # --- Project Management Actions ---
    def handle_create_project(self):
        project_service: ProjectService = self.services['project']
        project_view: ProjectView = self.views['project']
        base_view: BaseView = self.views['base']

        details = project_view.prompt_create_project_details()
        if details is None: return # User cancelled

        project_service.create_project(
            manager=self.current_user, **details # Pass collected details
        )
        # Success message handled by service

    def handle_edit_project(self):
        project_service: ProjectService = self.services['project']
        project_view: ProjectView = self.views['project']
        base_view: BaseView = self.views['base']

        project_to_edit = self._select_managed_project(action_verb="edit")
        if not project_to_edit: return

        updates = project_view.prompt_edit_project_details(project_to_edit)
        if updates is None: # Cancelled or error during input
             base_view.display_message("Project edit cancelled.", info=True)
             return
        if not updates:
             base_view.display_message("No changes entered.", info=True)
             return

        project_service.edit_project(self.current_user, project_to_edit, updates)
        # Success message handled by service

    def handle_delete_project(self):
        project_service: ProjectService = self.services['project']
        base_view: BaseView = self.views['base']

        project_to_delete = self._select_managed_project(action_verb="delete")
        if not project_to_delete: return

        # Confirm deletion
        if helpers.get_yes_no_input(f"WARNING: Are you sure you want to permanently delete project '{project_to_delete.project_name}'? This cannot be undone."):
            project_service.delete_project(self.current_user, project_to_delete)
            # Success message handled by service
        else:
            base_view.display_message("Deletion cancelled.", info=True)

    def handle_toggle_visibility(self):
        project_service: ProjectService = self.services['project']
        base_view: BaseView = self.views['base']

        project_to_toggle = self._select_managed_project(action_verb="toggle visibility for")
        if not project_to_toggle: return

        current_vis = "ON" if project_to_toggle.visibility else "OFF"
        action = "OFF" if project_to_toggle.visibility else "ON"
        if helpers.get_yes_no_input(f"Project '{project_to_toggle.project_name}' visibility is currently {current_vis}. Turn it {action}?"):
            project_service.toggle_project_visibility(self.current_user, project_to_toggle)
            # Success message handled by service
        else:
             base_view.display_message("Visibility toggle cancelled.", info=True)


    def handle_view_all_projects(self):
        project_service: ProjectService = self.services['project']
        project_view: ProjectView = self.views['project']
        base_view: BaseView = self.views['base']

        all_projects = project_service.get_all_projects()
        filtered_projects = project_service.filter_projects(all_projects, **self.user_filters)

        base_view.display_message(f"Current Project Filters: {self.user_filters or 'None'}", info=True)
        if not filtered_projects:
            base_view.display_message("No projects match your current filters.")
        else:
            base_view.display_message("Displaying All Projects in System:", info=True)
            for project in filtered_projects:
                # Display with Manager perspective
                project_view.display_project_details(project, UserRole.HDB_MANAGER, is_single_applicant=False)

        # Option to update filters
        if helpers.get_yes_no_input("\nUpdate filters?"):
            self.user_filters = project_view.prompt_project_filters(self.user_filters)
            base_view.display_message("Filters updated. View projects again to see changes.", info=True)

    def handle_view_my_projects(self):
        project_service: ProjectService = self.services['project']
        project_view: ProjectView = self.views['project']
        base_view: BaseView = self.views['base']

        my_projects = project_service.get_projects_by_manager(self.current_user.nric)
        if not my_projects:
            base_view.display_message("You are not currently managing any projects.")
            return

        base_view.display_message("Projects You Manage:", info=True)
        for project in my_projects:
            project_view.display_project_details(project, UserRole.HDB_MANAGER, is_single_applicant=False)

    # --- Officer Registration Actions ---
    def handle_view_officer_registrations(self):
        reg_service: RegistrationService = self.services['reg']
        auth_service: AuthService = self.services['auth'] # For names
        officer_view: OfficerView = self.views['officer']
        base_view: BaseView = self.views['base']

        project_to_view = self._select_managed_project("view officer registrations for")
        if not project_to_view: return

        registrations = reg_service.get_registrations_for_project(project_to_view.project_name)
        if not registrations:
            base_view.display_message(f"No officer registrations found for project '{project_to_view.project_name}'.")
            return

        base_view.display_message(f"Officer Registrations for '{project_to_view.project_name}':", info=True)
        # Use OfficerView to display list (can reuse selection logic if needed)
        officer_view.select_registration(registrations, auth_service, action_verb="view")
        base_view.display_message("End of registration list.", info=True) # Indicate end


    def _select_pending_registration_for_manager(self, action_verb: str = "action on"):
        """Helper to select a PENDING registration from managed projects."""
        reg_service: RegistrationService = self.services['reg']
        project_service: ProjectService = self.services['project']
        auth_service: AuthService = self.services['auth']
        officer_view: OfficerView = self.views['officer']
        base_view: BaseView = self.views['base']

        my_projects = project_service.get_projects_by_manager(self.current_user.nric)
        all_pending_regs = []
        for project in my_projects:
            all_pending_regs.extend(
                reg_service.get_registrations_for_project(
                    project.project_name, status_filter=RegistrationStatus.PENDING)
            )

        if not all_pending_regs:
            base_view.display_message("No pending officer registrations found across your projects.")
            return None

        return officer_view.select_registration(all_pending_regs, auth_service, action_verb=action_verb)

    def handle_approve_officer_registration(self):
        reg_service: RegistrationService = self.services['reg']
        base_view: BaseView = self.views['base']

        registration_to_approve = self._select_pending_registration_for_manager(action_verb="approve")
        if not registration_to_approve: return

        if helpers.get_yes_no_input(f"Approve registration for Officer {registration_to_approve.officer_nric} "
                                    f"on Project {registration_to_approve.project_name}?"):
             reg_service.manager_approve_officer_registration(self.current_user, registration_to_approve)
             # Success message from service
        else:
             base_view.display_message("Approval cancelled.", info=True)

    def handle_reject_officer_registration(self):
        reg_service: RegistrationService = self.services['reg']
        base_view: BaseView = self.views['base']

        registration_to_reject = self._select_pending_registration_for_manager(action_verb="reject")
        if not registration_to_reject: return

        if helpers.get_yes_no_input(f"Reject registration for Officer {registration_to_reject.officer_nric} "
                                    f"on Project {registration_to_reject.project_name}?"):
             reg_service.manager_reject_officer_registration(self.current_user, registration_to_reject)
             # Success message from service
        else:
             base_view.display_message("Rejection cancelled.", info=True)

    # --- Applicant Application Actions ---
    def handle_view_applications(self):
        app_service: ApplicationService = self.services['app']
        auth_service: AuthService = self.services['auth'] # For names
        app_view: ApplicationView = self.views['app']
        base_view: BaseView = self.views['base']

        project_to_view = self._select_managed_project("view applications for")
        if not project_to_view: return

        applications = app_service.get_applications_for_project(project_to_view.project_name)
        if not applications:
            base_view.display_message(f"No applications found for project '{project_to_view.project_name}'.")
            return

        base_view.display_message(f"Applications for '{project_to_view.project_name}':", info=True)
        # Use ApplicationView to display list
        app_view.select_application(applications, auth_service, action_verb="view")
        base_view.display_message("End of application list.", info=True)

    def _select_pending_application_for_manager(self, action_verb: str = "action on"):
        """Helper to select a PENDING application (without withdrawal request) from managed projects."""
        app_service: ApplicationService = self.services['app']
        project_service: ProjectService = self.services['project']
        auth_service: AuthService = self.services['auth']
        app_view: ApplicationView = self.views['app']
        base_view: BaseView = self.views['base']

        my_projects = project_service.get_projects_by_manager(self.current_user.nric)
        all_pending_apps = []
        for project in my_projects:
            apps = app_service.get_applications_for_project(project.project_name)
            # Filter for PENDING status and NOT requesting withdrawal
            pending = [app for app in apps if app.status == ApplicationStatus.PENDING.value and not app.request_withdrawal]
            all_pending_apps.extend(pending)

        if not all_pending_apps:
            base_view.display_message("No pending applications (without withdrawal requests) found across your projects.")
            return None

        return app_view.select_application(all_pending_apps, auth_service, action_verb=action_verb)

    def handle_approve_application(self):
        app_service: ApplicationService = self.services['app']
        base_view: BaseView = self.views['base']

        application_to_approve = self._select_pending_application_for_manager(action_verb="approve")
        if not application_to_approve: return

        if helpers.get_yes_no_input(f"Approve application for Applicant {application_to_approve.applicant_nric} "
                                    f"on Project {application_to_approve.project_name}?"):
            app_service.manager_approve_application(self.current_user, application_to_approve)
            # Success message/status update from service
        else:
            base_view.display_message("Approval cancelled.", info=True)

    def handle_reject_application(self):
        app_service: ApplicationService = self.services['app']
        base_view: BaseView = self.views['base']

        application_to_reject = self._select_pending_application_for_manager(action_verb="reject")
        if not application_to_reject: return

        if helpers.get_yes_no_input(f"Reject application for Applicant {application_to_reject.applicant_nric} "
                                    f"on Project {application_to_reject.project_name}?"):
            app_service.manager_reject_application(self.current_user, application_to_reject)
            # Success message from service
        else:
            base_view.display_message("Rejection cancelled.", info=True)


    def _select_application_with_withdrawal_request(self, action_verb: str = "action on withdrawal for"):
        """Helper to select an application with a PENDING withdrawal request from managed projects."""
        app_service: ApplicationService = self.services['app']
        project_service: ProjectService = self.services['project']
        auth_service: AuthService = self.services['auth']
        app_view: ApplicationView = self.views['app']
        base_view: BaseView = self.views['base']

        my_projects = project_service.get_projects_by_manager(self.current_user.nric)
        apps_with_request = []
        for project in my_projects:
            apps = app_service.get_applications_for_project(project.project_name)
            apps_with_request.extend([app for app in apps if app.request_withdrawal])

        if not apps_with_request:
            base_view.display_message("No applications with pending withdrawal requests found across your projects.")
            return None

        return app_view.select_application(apps_with_request, auth_service, action_verb=action_verb)


    def handle_approve_withdrawal(self):
        app_service: ApplicationService = self.services['app']
        base_view: BaseView = self.views['base']

        application_to_action = self._select_application_with_withdrawal_request(action_verb="approve withdrawal for")
        if not application_to_action: return

        if helpers.get_yes_no_input(f"Approve withdrawal for Applicant {application_to_action.applicant_nric} "
                                    f"on Project {application_to_action.project_name} (Current Status: {application_to_action.status})?"):
            app_service.manager_approve_withdrawal(self.current_user, application_to_action)
            # Success message from service
        else:
            base_view.display_message("Withdrawal approval cancelled.", info=True)

    def handle_reject_withdrawal(self):
        app_service: ApplicationService = self.services['app']
        base_view: BaseView = self.views['base']

        application_to_action = self._select_application_with_withdrawal_request(action_verb="reject withdrawal for")
        if not application_to_action: return

        if helpers.get_yes_no_input(f"Reject withdrawal for Applicant {application_to_action.applicant_nric} "
                                    f"on Project {application_to_action.project_name} (Current Status: {application_to_action.status})?"):
            app_service.manager_reject_withdrawal(self.current_user, application_to_action)
            # Success message from service
        else:
            base_view.display_message("Withdrawal rejection cancelled.", info=True)

    # --- Reporting & Enquiry Actions ---
    def handle_generate_booking_report(self):
        report_service: ReportService = self.services['report']
        report_view: ReportView = self.views['report']
        base_view: BaseView = self.views['base']

        filters = report_view.prompt_booking_report_filters()
        # Check if filters were cancelled
        if filters is None:
             base_view.display_message("Report generation cancelled.", info=True)
             return

        report_data = report_service.generate_booking_report_data(**filters)
        headers = ["NRIC", "Applicant Name", "Age", "Marital Status", "Flat Type", "Project Name", "Neighborhood"]
        report_view.display_report("Booking Report", report_data, headers)

    def handle_view_all_enquiries(self):
        enq_service: EnquiryService = self.services['enq']
        auth_service: AuthService = self.services['auth'] # For names
        project_service: ProjectService = self.services['project'] # For names
        enq_view: EnquiryView = self.views['enq']
        base_view: BaseView = self.views['base']

        all_enquiries = enq_service.get_all_enquiries()
        if not all_enquiries:
            base_view.display_message("There are no enquiries in the system.")
            return

        base_view.display_message("All System Enquiries:", info=True)
        for enquiry in all_enquiries:
            applicant = auth_service.user_repository.find_user_by_nric(enquiry.applicant_nric)
            applicant_name = applicant.name if applicant else "Unknown Applicant"
            project = project_service.find_project_by_name(enquiry.project_name)
            project_name = project.project_name if project else f"{enquiry.project_name} (Deleted)"
            enq_view.display_enquiry_details(enquiry, project_name, applicant_name)
        base_view.display_message("End of enquiry list.", info=True)


    def handle_view_reply_enquiries_manager(self):
        enq_service: EnquiryService = self.services['enq']
        project_service: ProjectService = self.services['project']
        auth_service: AuthService = self.services['auth']
        enq_view: EnquiryView = self.views['enq']
        base_view: BaseView = self.views['base']

        # Get enquiries only for projects managed by this manager
        my_projects = project_service.get_projects_by_manager(self.current_user.nric)
        my_project_names = {p.project_name for p in my_projects}

        if not my_project_names:
             base_view.display_message("You do not manage any projects, so cannot view/reply to enquiries specific to your projects.")
             return

        relevant_enquiries = []
        for enq in enq_service.get_all_enquiries():
            if enq.project_name in my_project_names:
                relevant_enquiries.append(enq)

        if not relevant_enquiries:
            base_view.display_message("No enquiries found for the projects you manage.")
            return

        unreplied_enquiries = [e for e in relevant_enquiries if not e.is_replied()]
        relevant_enquiries.sort(key=lambda e: e.enquiry_id)

        base_view.display_message("Enquiries for Projects You Manage:", info=True)
        for enquiry in relevant_enquiries:
             applicant = auth_service.user_repository.find_user_by_nric(enquiry.applicant_nric)
             applicant_name = applicant.name if applicant else "Unknown Applicant"
             # Project name is already known to be managed
             enq_view.display_enquiry_details(enquiry, enquiry.project_name, applicant_name)

        # Option to reply
        if not unreplied_enquiries:
            base_view.display_message("\nNo unreplied enquiries requiring action in your projects.")
            return

        if helpers.get_yes_no_input("\nReply to an unreplied enquiry from your projects?"):
            enquiry_to_reply = enq_view.select_enquiry(unreplied_enquiries, action_verb="reply to")
            if enquiry_to_reply:
                reply_text = enq_view.prompt_reply_text()
                if reply_text:
                    enq_service.reply_to_enquiry(self.current_user, enquiry_to_reply, reply_text)
                    # Success message handled by service
                else:
                     base_view.display_message("Reply cancelled.", info=True)
            else:
                 base_view.display_message("Reply cancelled.", info=True)