# models/enquiry.py
from utils.helpers import is_valid_int

class Enquiry:
    """Represents an enquiry submitted by an Applicant about a Project."""
    # Note: enquiry_id is typically assigned by the repository/service
    def __init__(self, enquiry_id: int, applicant_nric: str, project_name: str, text: str, reply: str = ""):

        if not is_valid_int(enquiry_id):
             raise ValueError(f"Invalid enquiry ID: {enquiry_id}. Must be an integer.")

        self.enquiry_id = int(enquiry_id)
        self.applicant_nric = applicant_nric # Foreign key to Applicant/Officer
        self.project_name = project_name   # Foreign key to Project
        self.text = text
        self.reply = reply                 # Reply text, potentially prefixed by Officer/Manager info

    def is_replied(self) -> bool:
        """Checks if the enquiry has received a reply."""
        return bool(self.reply and self.reply.strip())

    def __str__(self):
        reply_status = "Replied" if self.is_replied() else "Unreplied"
        return (f"Enquiry(ID: {self.enquiry_id}, Applicant: {self.applicant_nric}, Project: {self.project_name}, "
                f"Status: {reply_status})")

    def __eq__(self, other):
        if not isinstance(other, Enquiry):
            return NotImplemented
        # ID should be unique if assigned correctly
        return self.enquiry_id == other.enquiry_id

    def __hash__(self):
        return hash(self.enquiry_id)