# views/auth_view.py
from .base_view import BaseView

class AuthView(BaseView):
    """View specific to authentication actions."""

    def prompt_login(self) -> tuple[str, str]:
        """Prompts for NRIC and password for login."""
        self.display_message("--- Login ---", info=True)
        nric = self.get_input("Enter NRIC")
        password = self.get_password()
        return nric, password

    def prompt_change_password(self) -> tuple[str, str]:
        """Prompts for current and new password."""
        self.display_message("--- Change Password ---", info=True)
        current_pwd = self.get_password("Enter your current password")
        new_pwd = self.get_password("Enter your new password")
        confirm_pwd = self.get_password("Confirm your new password")

        if new_pwd != confirm_pwd:
            self.display_message("New passwords do not match.", error=True)
            return None, None # Indicate failure

        return current_pwd, new_pwd