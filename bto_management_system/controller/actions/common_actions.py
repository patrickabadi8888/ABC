from typing import Dict, Any, Optional
from controller.interfaces.iaction import IAction
from service.auth_service import AuthService # Assuming interface/concrete class path
from view.auth_view import AuthView
from view.base_view import BaseView
from common.exceptions import OperationError
from model.user import User

class ChangePasswordAction(IAction):
    """Action to handle changing the current user's password."""
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[User] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        if not current_user:
            views['base'].display_message("Cannot change password. No user logged in.", error=True)
            return None

        auth_service: AuthService = services['auth']
        auth_view: AuthView = views['auth']
        base_view: BaseView = views['base']

        # Get current password for verification first
        current_password_attempt = auth_view.get_password("Enter your CURRENT password for verification")
        if not current_user.check_password(current_password_attempt):
             base_view.display_message("Verification failed: Incorrect current password.", error=True)
             return None # Abort change

        # If verification passes, get the new password
        new_password = auth_view.prompt_change_password() # View handles new/confirm match
        if new_password:
            try:
                auth_service.change_password(current_user, new_password)
                base_view.display_message("Password changed successfully.", info=True)
            except OperationError as e:
                 base_view.display_message(str(e), error=True)
            # Let other exceptions propagate up
        return None

class LogoutAction(IAction):
    """Action to signal user logout."""
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[User] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        return "LOGOUT"

class ExitAction(IAction):
    """Action to signal application exit."""
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[User] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        return "EXIT"

class NoOpAction(IAction):
    """Action that does nothing, useful for menu separators."""
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[User] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        return None # Just continue