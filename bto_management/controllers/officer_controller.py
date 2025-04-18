# controllers/officer_controller.py
from .applicant_controller import ApplicantController # Inherit applicant actions
from models.user import User, HDBOfficer
from models.roles import UserRole, ApplicationStatus
from services.project_service import ProjectService
from services.registration_service import RegistrationService
from services.application_service import ApplicationService
from services.enquiry_service import EnquiryService
from services.auth_service import AuthService # Needed for lookups
from views.project_view import ProjectView
from views.officer_view import OfficerView
from views.enquiry_view import EnquiryView
from views.application_view import ApplicationView # For selecting applicant's app
from views.base_view import BaseView
from utils.exceptions import OperationError, AuthorizationError, IntegrityError
from utils import helpers

class OfficerController(ApplicantController): # Inherit from ApplicantController
    """Controller for HDB Officer actions, including inherited Applicant actions."""
    def __init__(self, current_user: User, services: dict, views: dict):
        if not isinstance(current_user, HDBOfficer):
             raise TypeError("OfficerController requires an HDBOfficer user.")
        super().__init__(current_user, services, views) # Initialize Applicant part

    def run_menu(self):
        """Displays the Officer menu (combining Applicant and Officer actions)."""
        # Inherited Applicant actions from ApplicantController's run_menu setup
        applicant_actions = {
            "View / Filter Available Projects": self.handle_view_projects,
            "Apply for Project (as Applicant)": self.handle_apply_for_project,
            "View My Application Status": self.handle_view_my_application_status,
            "Request Application Withdrawal": self.handle_request_withdrawal,
            "Submit Enquiry (as Applicant)": self.handle_submit_enquiry,
            "View My Enquiries": self.handle_view_my_enquiries,
            "Edit My Enquiry": self.handle_edit_my_enquiry,
            "Delete My Enquiry": self.handle_delete_my_enquiry,
        }
        # Officer-specific actions
        officer_actions = {
            "Register for Project (as Officer)": self.handle_register_for_project,
            "View My Officer Registrations": self.handle_view_my_registrations,
            "View Projects I Handle": self.handle_view_handled_projects,
            "View/Reply Enquiries (Handled Projects)": self.handle_view_reply_enquiries_officer,
            "Book Flat for Applicant": self.handle_book_flat_for_applicant,
            "Generate Booking Receipt for Applicant": self.handle_generate_receipt_for_applicant,
        }

        # Combine all actions including common ones from base
        actions = {
            "--- Applicant Actions ---": None, # Separator
            **applicant_actions,
            "--- Officer Actions ---": None, # Separator
            **officer_actions,
            "--- Account ---": None, # Separator
            **self._get_common_menu_actions()
        }

        # Filter out separator lines for display
        options = [k for k in actions.keys() if actions[k] is not None]
        action_map = {k: v for k, v in actions.items() if v is not None}

        base_view: BaseView = self.views['base']
        choice_index = base_view.display_menu("HDB Officer Menu", options)
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

    # --- Officer-Specific Action Handlers ---

    def handle_register_for_project(self):
        reg_service: RegistrationService = self.services['reg']
        project_service: ProjectService = self.services['project']
        project_view: ProjectView = self.views['project']
        base_view: BaseView = self.views['base']

        # Find projects the officer *can* register for
        all_projects = project_service.get_all_projects()
        registrable_projects = []
        for p in all_projects:
             # Use service layer checks to determine eligibility
             try:
                 # Perform a dry-run check without actually creating registration yet
                 reg_service._check_officer_registration_eligibility(self.current_user, p)
                 registrable_projects.append(p)
             except OperationError: # Catches eligibility failures
                 continue # Skip projects they can't register for
             except Exception as e: # Catch unexpected errors during check
                  print(f"Warning: Error checking registration eligibility for project '{p.project_name}': {e}")
                  continue

        project_to_register = project_view.select_project(registrable_projects, action_verb="register for (as Officer)")
        if not project_to_register:
             base_view.display_message("Registration cancelled.", info=True)
             return

        if helpers.get_yes_no_input(f"Confirm registration for project '{project_to_register.project_name}'?"):
            reg_service.officer_register_for_project(self.current_user, project_to_register)
            # Success message handled by service
        else:
             base_view.display_message("Registration cancelled.", info=True)

    def handle_view_my_registrations(self):
        reg_service: RegistrationService = self.services['reg']
        project_service: ProjectService = self.services['project'] # To get project names
        officer_view: OfficerView = self.views['officer']
        base_view: BaseView = self.views['base']

        my_registrations = reg_service.get_registrations_by_officer(self.current_user.nric)
        if not my_registrations:
            base_view.display_message("You have no officer registrations.")
            return

        base_view.display_message("Your Officer Registrations:", info=True)
        for reg in my_registrations:
            project = project_service.find_project_by_name(reg.project_name)
            project_name = project.project_name if project else f"{reg.project_name} (Deleted)"
            officer_view.display_registration_details(reg, project_name, self.current_user.name)

    def handle_view_handled_projects(self):
        project_service: ProjectService = self.services['project']
        project_view: ProjectView = self.views['project']
        base_view: BaseView = self.views['base']

        # Get names/projects officer handles (needs integration with RegistrationService)
        handled_project_names = project_service.get_handled_project_names_for_officer(self.current_user.nric)
        if not handled_project_names:
            base_view.display_message("You are not currently handling any projects (approved registration or directly assigned).")
            return

        handled_projects = [p for p in project_service.get_all_projects() if p.project_name in handled_project_names]
        sorted_handled = sorted(handled_projects, key=lambda p: p.project_name)

        base_view.display_message("Projects You Handle:", info=True)
        is_single = self.current_user.marital_status.lower() == "single" # Get for display consistency
        for project in sorted_handled:
            project_view.display_project_details(project, UserRole.HDB_OFFICER, is_single)

    def handle_view_reply_enquiries_officer(self):
        enq_service: EnquiryService = self.services['enq']
        project_service: ProjectService = self.services['project'] # Needed for handled projects
        auth_service: AuthService = self.services['auth'] # For applicant lookup
        enq_view: EnquiryView = self.views['enq']
        base_view: BaseView = self.views['base']

        # Get enquiries related to projects handled by this officer
        handled_names = project_service.get_handled_project_names_for_officer(self.current_user.nric)
        if not handled_names:
            base_view.display_message("You do not handle any projects, so cannot view/reply to enquiries.")
            return

        relevant_enquiries = []
        for enq in enq_service.get_all_enquiries():
            if enq.project_name in handled_names:
                relevant_enquiries.append(enq)

        if not relevant_enquiries:
            base_view.display_message("No enquiries found for the projects you handle.")
            return

        unreplied_enquiries = [e for e in relevant_enquiries if not e.is_replied()]
        relevant_enquiries.sort(key=lambda e: e.enquiry_id) # Sort by ID

        base_view.display_message("Enquiries for Projects You Handle:", info=True)
        for enquiry in relevant_enquiries:
             applicant = auth_service.user_repository.find_user_by_nric(enquiry.applicant_nric)
             applicant_name = applicant.name if applicant else "Unknown Applicant"
             project = project_service.find_project_by_name(enquiry.project_name)
             project_name = project.project_name if project else f"{enquiry.project_name} (Deleted)"
             enq_view.display_enquiry_details(enquiry, project_name, applicant_name)

        # Option to reply
        if not unreplied_enquiries:
            base_view.display_message("\nNo unreplied enquiries requiring action in your projects.")
            return

        if helpers.get_yes_no_input("\nReply to an unreplied enquiry?"):
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


    def handle_book_flat_for_applicant(self):
        app_service: ApplicationService = self.services['app']
        auth_service: AuthService = self.services['auth'] # To find applicant
        officer_view: OfficerView = self.views['officer']
        base_view: BaseView = self.views['base']

        # Get applicant NRIC from officer
        applicant_nric = officer_view.prompt_applicant_nric(purpose="booking flat")
        if not applicant_nric: return # User cancelled

        # Find the applicant
        applicant = auth_service.user_repository.find_user_by_nric(applicant_nric)
        if not applicant:
            raise OperationError(f"Applicant with NRIC {applicant_nric} not found.")

        # Find the applicant's *successful* application
        apps = app_service.application_repository.find_by_applicant_nric(applicant_nric)
        successful_app = None
        for app in apps:
             if app.status == ApplicationStatus.SUCCESSFUL.value:
                 successful_app = app
                 break

        if not successful_app:
            # Check for other statuses to provide more context
            active_app = app_service.find_active_application_by_applicant(applicant_nric)
            if active_app:
                 status_msg = f"has an application with status '{active_app.status}'"
            else:
                 status_msg = "does not have an active application"
            raise OperationError(f"Applicant {applicant.name} ({applicant_nric}) {status_msg}. "
                                 f"Booking requires status '{ApplicationStatus.SUCCESSFUL.value}'.")

        # Confirm action
        if helpers.get_yes_no_input(f"Confirm booking for Applicant: {applicant.name} ({applicant.nric})\n"
                                    f"Project: {successful_app.project_name}, Flat Type: {successful_app.flat_type}-Room?"):
            # Perform booking via service
            updated_project = app_service.officer_book_flat(self.current_user, successful_app)
            # Success message handled by service

            # Automatically display receipt after successful booking
            receipt_data = self._prepare_receipt_data(successful_app, updated_project, applicant)
            officer_view.display_receipt(receipt_data)
        else:
            base_view.display_message("Booking cancelled.", info=True)

    def handle_generate_receipt_for_applicant(self):
        app_service: ApplicationService = self.services['app']
        project_service: ProjectService = self.services['project'] # To get project details
        auth_service: AuthService = self.services['auth'] # To find applicant
        officer_view: OfficerView = self.views['officer']
        base_view: BaseView = self.views['base']

        # Get applicant NRIC
        applicant_nric = officer_view.prompt_applicant_nric(purpose="generating receipt")
        if not applicant_nric: return # User cancelled

        applicant = auth_service.user_repository.find_user_by_nric(applicant_nric)
        if not applicant:
            raise OperationError(f"Applicant with NRIC {applicant_nric} not found.")

        # Find the applicant's *booked* application
        apps = app_service.application_repository.find_by_applicant_nric(applicant_nric)
        booked_app = None
        for app in apps:
            if app.status == ApplicationStatus.BOOKED.value:
                booked_app = app
                break

        if not booked_app:
            raise OperationError(f"No application with status '{ApplicationStatus.BOOKED.value}' found for applicant {applicant.name} ({applicant_nric}).")

        # Check if the officer handles the project for this booked application
        project = project_service.find_project_by_name(booked_app.project_name)
        if not project:
            raise IntegrityError(f"Project '{booked_app.project_name}' for booked application not found.")

        # TODO: Integrate with RegistrationService for full check
        handled_names = project_service.get_handled_project_names_for_officer(self.current_user.nric)
        if project.project_name not in handled_names:
             raise AuthorizationError(f"You do not handle project '{project.project_name}' and cannot generate the receipt for this booking.")

        # Generate and display receipt
        receipt_data = self._prepare_receipt_data(booked_app, project, applicant)
        officer_view.display_receipt(receipt_data)