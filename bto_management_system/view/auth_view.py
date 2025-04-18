from .base_view import BaseView

class AuthView(BaseView):
    """View specific to authentication actions."""

    def prompt_login(self) -> tuple[str, str]:
        """Prompts for NRIC and password."""
        self.display_message("\n--- Login ---", info=True)
        nric = self.get_input("Enter NRIC")
        password = self.get_password()
        return nric, password

    def prompt_change_password(self) -> str | None:
        """Prompts for new password and confirmation. Returns new password if match."""
        self.display_message("\n--- Change Password ---", info=True)
        # Note: Verification of the *current* password should happen in the Action/Controller
        # This view only collects the *new* password details.

        new_pwd = self.get_password("Enter your new password")
        confirm_pwd = self.get_password("Confirm your new password")

        if not new_pwd:
            self.display_message("New password cannot be empty.", error=True)
            return None
        if new_pwd != confirm_pwd:
            self.display_message("New passwords do not match.", error=True)
            return None

        # Return the validated new password
        return new_pwd