# controllers/app_controller.py
from models.roles import UserRole
from services.auth_service import AuthService
from views.auth_view import AuthView
from views.base_view import BaseView
from .applicant_controller import ApplicantController
from .officer_controller import OfficerController
from .manager_controller import ManagerController
from utils.exceptions import AuthenticationError, DataLoadError, DataSaveError
from utils import helpers # For get_yes_no_input

class AppController:
    """Main application controller orchestrating the overall flow."""
    def __init__(self, services: dict, views: dict):
        self.services = services
        self.views = views
        self.current_user = None
        self.role_controller = None

    def run(self):
        """Starts and runs the main application loop."""
        base_view: BaseView = self.views['base']
        base_view.display_message("--- Welcome to the BTO Management System ---", info=True)

        while True:
            if not self.current_user:
                # If not logged in, attempt login
                if not self._handle_login():
                    # If login fails and user chooses not to retry, exit
                    break
            else:
                # If logged in, run the role-specific menu
                if self.role_controller:
                    signal = self.role_controller.run_menu()
                    if signal == "LOGOUT":
                        self._handle_logout()
                    elif signal == "EXIT":
                        self._shutdown()
                        break
                    # If signal is None, loop continues (stay in menu)
                else:
                    # Should not happen if login succeeded
                    base_view.display_message("Error: No role controller active despite being logged in. Logging out.", error=True)
                    self._handle_logout()

    def _handle_login(self) -> bool:
        """Handles the login process. Returns True if login successful, False if user wants to exit."""
        auth_service: AuthService = self.services['auth']
        auth_view: AuthView = self.views['auth']
        base_view: BaseView = self.views['base']

        while self.current_user is None:
            try:
                nric, password = auth_view.prompt_login()
                # Attempt login via service
                self.current_user = auth_service.login(nric, password)
                # Determine role and instantiate appropriate controller
                role = auth_service.get_user_role(self.current_user)

                if role == UserRole.HDB_MANAGER:
                    self.role_controller = ManagerController(self.current_user, self.services, self.views)
                elif role == UserRole.HDB_OFFICER:
                    self.role_controller = OfficerController(self.current_user, self.services, self.views)
                elif role == UserRole.APPLICANT:
                    self.role_controller = ApplicantController(self.current_user, self.services, self.views)
                else:
                    # Handle unknown role case
                    base_view.display_message(f"Error: Unknown user role '{role}' detected for user {nric}. Logging out.", error=True)
                    self.current_user = None
                    self.role_controller = None
                    # Decide whether to allow retry or exit
                    if not helpers.get_yes_no_input("Login failed due to role error. Try again?"):
                         self._shutdown()
                         return False # Signal exit

                if self.current_user:
                    base_view.display_message(f"Login successful. Welcome, {self.current_user.name}!", info=True)
                    return True # Login successful

            except AuthenticationError as e:
                base_view.display_message(f"Login failed: {e}", error=True)
                # Ask user if they want to retry login
                if not helpers.get_yes_no_input("Try login again?"):
                    self._shutdown()
                    return False # User chose to exit
            except KeyboardInterrupt:
                 print("\nLogin cancelled by user.")
                 self._shutdown()
                 return False # Exit
            except Exception as e:
                 base_view.display_message(f"An unexpected error occurred during login: {e}", error=True)
                 # Decide recovery strategy - maybe retry?
                 if not helpers.get_yes_no_input("Try login again?"):
                     self._shutdown()
                     return False # Exit

        return True # Should only be reached if login was successful in the loop

    def _handle_logout(self):
        """Handles the logout process."""
        base_view: BaseView = self.views['base']
        if self.current_user:
            base_view.display_message(f"Logging out user {self.current_user.name}.", info=True)
        self.current_user = None
        self.role_controller = None
        # Optionally clear user filters or other session data here

    def _shutdown(self):
        """Performs any cleanup and exits the application."""
        base_view: BaseView = self.views['base']
        # Add any final saving logic if needed (though repositories save on change)
        # e.g., maybe save user session settings if implemented
        base_view.display_message("--- Exiting BTO Management System. Goodbye! ---", info=True)