# views/enquiry_view.py
from .base_view import BaseView
from models.enquiry import Enquiry
from utils import helpers # For non_empty_input

class EnquiryView(BaseView):
    """View specific to Enquiry display and input."""

    def display_enquiry_details(self, enquiry: Enquiry, project_name: str, applicant_name: str):
        """Displays the details of a single enquiry."""
        details = {
            "Project": project_name,
            "Submitted by": f"{applicant_name} ({enquiry.applicant_nric})",
            "Enquiry Text": enquiry.text,
            "Status": "Replied" if enquiry.is_replied() else "Awaiting Reply",
            "Reply": enquiry.reply if enquiry.is_replied() else "(No reply yet)"
        }
        self.display_dict(f"Enquiry Details (ID: {enquiry.enquiry_id})", details)

    def select_enquiry(self, enquiries: list[Enquiry], action_verb: str = "view") -> Enquiry | None:
        """Allows user to select an enquiry from a list by its ID."""
        if not enquiries:
            self.display_message("No enquiries available for selection.", info=True)
            return None

        print(f"\n--- Select Enquiry (by ID) to {action_verb} ---")
        enquiry_map = {} # Map ID to enquiry object
        for enq in enquiries:
            reply_status = "Replied" if enq.is_replied() else "Unreplied"
            # Preview text for easier identification
            text_preview = (enq.text[:47] + '...') if len(enq.text) > 50 else enq.text.replace('\n', ' ')
            print(f"  ID: {enq.enquiry_id:<4} | Project: {enq.project_name:<15} | "
                  f"Status: {reply_status:<9} | Applicant: {enq.applicant_nric:<10} | Text: {text_preview}")
            enquiry_map[enq.enquiry_id] = enq
        print("  ID: 0    | Cancel Selection")
        print("---------------------------------------------------------------------")

        while True:
            id_str = self.get_input("Enter the ID of the enquiry (or 0 to cancel)")
            if id_str == '0':
                return None
            try:
                enquiry_id = int(id_str)
                if enquiry_id in enquiry_map:
                    return enquiry_map[enquiry_id]
                else:
                    self.display_message("Invalid enquiry ID selected.", error=True)
            except ValueError:
                self.display_message("Invalid input. Please enter a number (ID).", error=True)

    def prompt_enquiry_text(self, current_text: str | None = None) -> str | None:
        """Prompts for enquiry text (new or editing)."""
        prompt = "Enter enquiry text"
        if current_text:
             # Show preview if editing
             preview = (current_text[:30] + '...') if len(current_text) > 33 else current_text
             prompt = f"Enter new enquiry text [{preview}]"
        try:
             return helpers.get_non_empty_input(prompt)
        except KeyboardInterrupt:
             print("\nInput cancelled.")
             return None

    def prompt_reply_text(self) -> str | None:
        """Prompts for reply text."""
        try:
            return helpers.get_non_empty_input("Enter reply text")
        except KeyboardInterrupt:
             print("\nInput cancelled.")
             return None