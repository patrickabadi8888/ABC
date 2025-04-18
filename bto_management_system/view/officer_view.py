from typing import List, Optional, Dict, Any
from .base_view import BaseView
from model.registration import Registration
from repository.interfaces.iuser_repository import IUserRepository # For lookup in select
from utils.input_util import InputUtil

class OfficerView(BaseView):
    """View specific to HDB Officer actions (beyond Applicant actions)."""

    def display_registration_summary(self, registration: Registration, officer_name: str):
         """Displays a brief summary of an officer registration."""
         # Use model's display method
         print(registration.get_display_summary(officer_name))

    def display_registration_details(self, registration: Registration, project_name: str, officer_name: str):
        """Displays details of an officer's registration."""
        details = {
            "Officer": f"{officer_name} ({registration.officer_nric})",
            "Project": project_name, # Use provided name
            "Registration Status": registration.status.value
        }
        self.display_dict("Officer Registration Details", details)

    def select_registration(self, registrations: List[Registration], user_repo: IUserRepository, action_verb: str = "view") -> Optional[Registration]:
        """Displays a list of registrations and prompts for selection."""
        if not registrations:
            self.display_message("No registrations available for selection.", info=True)
            return None

        print(f"\n--- Select Registration to {action_verb} ---")
        reg_map = {} # Map 1-based index to registration object
        for i, reg in enumerate(registrations):
            officer = user_repo.find_user_by_nric(reg.officer_nric)
            officer_name = officer.name if officer else "Unknown Officer"
            print(f"{i + 1}. ", end="")
            self.display_registration_summary(reg, officer_name) # Use summary
            reg_map[i + 1] = reg
        print(" 0. Cancel")
        print("------------------------------------")

        while True:
            choice = InputUtil.get_valid_integer_input("Enter the number of the registration (or 0 to cancel)", min_val=0, max_val=len(registrations))
            if choice == 0: return None
            selected_reg = reg_map.get(choice)
            if selected_reg: return selected_reg
            self.display_message("Invalid selection.", error=True)

    def prompt_applicant_nric(self, purpose: str = "action") -> Optional[str]:
         """Prompts for an applicant's NRIC for a specific purpose."""
         while True:
             try:
                 nric = self.get_input(f"Enter Applicant's NRIC for {purpose} (or type 'cancel')")
                 if nric.lower() == 'cancel': return None
                 if InputUtil.validate_nric(nric):
                     return nric
                 else:
                     self.display_message("Invalid NRIC format. Please try again.", error=True)
             except KeyboardInterrupt:
                  self.display_message("\nInput cancelled.")
                  return None

    def display_receipt(self, receipt_data: Dict[str, Any]):
        """Displays the booking receipt details."""
        self.display_dict("Booking Receipt", receipt_data)