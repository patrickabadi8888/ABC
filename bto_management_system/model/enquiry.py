from utils.input_util import InputUtil
from common.exceptions import DataLoadError, OperationError

class Enquiry:
    """Represents an enquiry submitted by an applicant."""
    _HEADERS = ['EnquiryID', 'ApplicantNRIC', 'ProjectName', 'Text', 'Reply']

    def __init__(self, enquiry_id: int, applicant_nric: str, project_name: str, text: str, reply: str = ""):
        if not isinstance(enquiry_id, int): raise ValueError("Enquiry ID must be an integer.")
        if not InputUtil.validate_nric(applicant_nric): raise ValueError("Invalid Applicant NRIC")
        if not project_name: raise ValueError("Project Name cannot be empty")
        if not text: raise ValueError("Enquiry text cannot be empty")

        self._enquiry_id = enquiry_id
        self._applicant_nric = applicant_nric
        self._project_name = project_name
        self._text = text
        self._reply = reply if reply is not None else ""

    # --- Getters ---
    @property
    def enquiry_id(self): return self._enquiry_id
    @property
    def applicant_nric(self): return self._applicant_nric
    @property
    def project_name(self): return self._project_name
    @property
    def text(self): return self._text
    @property
    def reply(self): return self._reply

    # --- State Checks ---
    def is_replied(self) -> bool:
        return bool(self._reply)

    # --- State Modifiers ---
    def set_text(self, new_text: str):
        if self.is_replied():
            raise OperationError("Cannot edit an enquiry that has already been replied to.")
        if not new_text:
            raise ValueError("Enquiry text cannot be empty.")
        self._text = new_text

    def set_reply(self, reply_text: str):
        if not reply_text:
             raise ValueError("Reply text cannot be empty.")
        self._reply = reply_text

    def set_id(self, new_id: int):
        """Allows repository to set the ID upon adding."""
        if not isinstance(new_id, int) or new_id <= 0:
             raise ValueError("New Enquiry ID must be a positive integer.")
        if self._enquiry_id != 0 and self._enquiry_id != new_id: # Allow setting if default 0
             print(f"Warning: Changing existing Enquiry ID from {self._enquiry_id} to {new_id}")
        self._enquiry_id = new_id

    def to_csv_dict(self) -> dict:
        return {
            'EnquiryID': self._enquiry_id,
            'ApplicantNRIC': self._applicant_nric,
            'ProjectName': self._project_name,
            'Text': self._text,
            'Reply': self._reply
        }

    @classmethod
    def from_csv_dict(cls, row_dict: dict) -> 'Enquiry':
        try:
            return cls(
                enquiry_id=int(row_dict['EnquiryID']),
                applicant_nric=row_dict['ApplicantNRIC'],
                project_name=row_dict['ProjectName'],
                text=row_dict['Text'],
                reply=row_dict.get('Reply', '')
            )
        except (KeyError, ValueError, TypeError) as e:
            raise DataLoadError(f"Error creating Enquiry from CSV row: {row_dict}. Error: {e}")

    def __eq__(self, other):
        if not isinstance(other, Enquiry): return NotImplemented
        return self._enquiry_id == other._enquiry_id

    def __hash__(self):
        return hash(self._enquiry_id)

    def get_display_summary(self) -> str:
         reply_status = "Replied" if self.is_replied() else "Unreplied"
         text_preview = (self._text[:47] + '...') if len(self._text) > 50 else self._text
         return f"ID: {self._enquiry_id:<4} | Project: {self._project_name:<15} | Status: {reply_status:<9} | Text: {text_preview}"