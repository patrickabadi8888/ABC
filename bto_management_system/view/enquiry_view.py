from typing import List, Optional
from .base_view import BaseView
from model.enquiry import Enquiry
from utils.input_util import InputUtil

class EnquiryView(BaseView):
    """View specific to displaying and interacting with enquiries."""

    def display_enquiry_summary(self, enquiry: Enquiry):
         """Displays a brief summary of an enquiry for lists."""
         # Use model's display method
         print(enquiry.get_display_summary())

    def display_enquiry_details(self, enquiry: Enquiry, project_name: str, applicant_name: str):
        """Displays the full details of an enquiry."""
        details = {
            "Enquiry ID": enquiry.enquiry_id,
            "Project": project_name, # Use provided name
            "Submitted by": f"{applicant_name} ({enquiry.applicant_nric})",
            "Enquiry Text": enquiry.text,
            "Reply": enquiry.reply if enquiry.is_replied() else "(No reply yet)"
        }
        self.display_dict(f"Enquiry Details", details)

    def select_enquiry(self, enquiries: List[Enquiry], action_verb: str = "view") -> Optional[Enquiry]:
        """Displays a list of enquiries and prompts for selection by ID."""
        if not enquiries:
            self.display_message("No enquiries available for selection.", info=True)
            return None

        print(f"\n--- Select Enquiry (by ID) to {action_verb} ---")
        enquiry_map = {} # Map ID to enquiry object
        for enq in enquiries:
            self.display_enquiry_summary(enq) # Use summary
            enquiry_map[enq.enquiry_id] = enq
        print("  ID: 0    | Cancel")
        print("--------------------------------------------------")

        while True:
            enquiry_id = InputUtil.get_valid_integer_input("Enter the ID of the enquiry (or 0 to cancel)", min_val=0)
            if enquiry_id == 0: return None
            selected_enq = enquiry_map.get(enquiry_id)
            if selected_enq: return selected_enq
            self.display_message("Invalid enquiry ID.", error=True)

    def prompt_enquiry_text(self, current_text: Optional[str] = None) -> Optional[str]:
        """Prompts for enquiry text (new or edit)."""
        prompt = "Enter enquiry text"
        if current_text:
            preview = (current_text[:30] + '...') if len(current_text) > 33 else current_text
            prompt = f"Enter new enquiry text (current: '{preview}')"
        try:
            # Use InputUtil for non-empty validation
            return InputUtil.get_non_empty_input(prompt)
        except KeyboardInterrupt:
             self.display_message("\nInput cancelled.")
             return None

    def prompt_reply_text(self) -> Optional[str]:
        """Prompts for reply text."""
        try:
            # Use InputUtil for non-empty validation
            return InputUtil.get_non_empty_input("Enter reply text")
        except KeyboardInterrupt:
             self.display_message("\nInput cancelled.")
             return None