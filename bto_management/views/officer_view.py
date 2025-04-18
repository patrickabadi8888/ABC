# views/officer_view.py
from .base_view import BaseView
from models.registration import Registration
from services.auth_service import AuthService # Type hint
from utils import helpers

class OfficerView(BaseView):
    """View specific to HDB Officer actions."""

    def display_registration_details(self, registration: Registration, project_name: str, officer_name: str):
        """Displays details of an officer's registration request."""
        details = {
            "Officer": f"{officer_name} ({registration.officer_nric})",
            "Project": project_name,
            "Registration Status": registration.status
        }
        self.display_dict("Officer Registration Details", details)

    def select_registration(self, registrations: list[Registration], auth_service: AuthService,
                            action_verb: str = "view") -> Registration | None:
        """Allows selection of a registration from a list."""
        if not registrations:
            self.display_message("No registrations available for selection.", info=True)
            return None

        print(f"\n--- Select Registration to {action_verb} ---")
        reg_map = {}
        for i, reg in enumerate(registrations):
            officer = auth_service.user_repository.find_user_by_nric(reg.officer_nric)
            officer_display = f"{officer.name} ({reg.officer_nric})" if officer else reg.officer_nric
            print(f"{i + 1}. Project: {reg.project_name:<15} | Officer: {officer_display:<25} | Status: {reg.status}")
            reg_map[i + 1] = reg
        print(" 0. Cancel")
        print("--------------------------------------------------")

        while True:
            choice_str = self.get_input(f"Enter the number of the registration (1-{len(registrations)}, or 0 to cancel)")
            if choice_str == '0':
                return None
            try:
                index = int(choice_str)
                if 1 <= index <= len(registrations):
                    return reg_map[index]
                else:
                    self.display_message("Invalid selection number.", error=True)
            except ValueError:
                self.display_message("Invalid input. Please enter a number.", error=True)

    def prompt_applicant_nric(self, purpose: str = "action") -> str | None:
         """Prompts for an applicant's NRIC, ensuring valid format."""
         while True:
             try:
                 nric = self.get_input(f"Enter Applicant's NRIC for {purpose} (or type 'cancel')")
                 if nric.lower() == 'cancel':
                      return None
                 if helpers.validate_nric(nric):
                     return nric
                 else:
                     self.display_message("Invalid NRIC format (S/T + 7 digits + Letter). Please try again.", error=True)
             except KeyboardInterrupt:
                  print("\nOperation cancelled.")
                  return None

    def display_receipt(self, receipt_data: dict):
        """Displays the generated booking receipt details."""
        self.display_dict("Booking Receipt", receipt_data)