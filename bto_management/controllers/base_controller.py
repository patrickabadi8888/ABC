# controllers/base_controller.py
from abc import ABC, abstractmethod
from models.user import User
from services.auth_service import AuthService
from views.auth_view import AuthView
from views.base_view import BaseView
from utils.exceptions import OperationError, AuthorizationError, DataSaveError

class BaseController(ABC):
    """Base class for role-specific controllers."""
    def __init__(self, current_user: User, services: dict, views: dict):
        self.current_user = current_user
        self.services = services
        self.views = views
        self.user_filters = {} # Store user-specific filters (e.g., for project view)

    @abstractmethod
    def run_menu(self):
        """Displays the role-specific menu and handles user choice. Returns signal ('LOGOUT', 'EXIT', None)."""
        pass

    def _get_common_menu_actions(self) -> dict:
        """Returns a dictionary of common actions available to all logged-in users."""
        return {
            "Change Password": self.handle_change_password,
            "Logout": self._signal_logout,
            "Exit System": self._signal_exit,
        }

    def handle_change_password(self):
        """Handles the workflow for changing the current user's password."""
        auth_service: AuthService = self.services['auth']
        auth_view: AuthView = self.views['auth']
        base_view: BaseView = self.views['base']

        current_pwd, new_password = auth_view.prompt_change_password()

        if current_pwd is None: # Indicates mismatch during prompt
             return # Message already displayed by view

        try:
            auth_service.change_password(self.current_user, current_pwd, new_password)
            base_view.display_message("Password changed successfully.", info=True)
        except (OperationError, DataSaveError) as e:
             base_view.display_message(f"Password change failed: {e}", error=True)
        except Exception as e:
             base_view.display_message(f"An unexpected error occurred during password change: {e}", error=True)


    def _signal_logout(self):
        """Action method that signals logout."""
        return "LOGOUT"

    def _signal_exit(self):
        """Action method that signals system exit."""
        return "EXIT"

    # Helper for preparing receipt data (could be in a utility or service too)
    def _prepare_receipt_data(self, application, project, applicant) -> dict:
        """Helper to format data consistently for receipt display."""
        if not all([application, project, applicant]):
            return {"Error": "Missing data for receipt generation."}
        try:
            return {
                "Applicant Name": applicant.name,
                "NRIC": applicant.nric,
                "Age": applicant.age,
                "Marital Status": applicant.marital_status,
                "Flat Type Booked": f"{application.flat_type}-Room",
                "Project Name": project.project_name,
                "Neighborhood": project.neighborhood
                # Add booking date/time if tracked
            }
        except AttributeError as e:
             return {"Error": f"Missing expected attribute for receipt: {e}"}