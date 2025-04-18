# models/application.py
from .roles import ApplicationStatus, VALID_FLAT_TYPES
from utils.helpers import is_valid_int

class Application:
    """Represents a BTO application submitted by an Applicant."""
    def __init__(self, applicant_nric: str, project_name: str, flat_type: int,
                 status: str = ApplicationStatus.PENDING.value, request_withdrawal: bool = False):

        if not is_valid_int(flat_type) or int(flat_type) not in VALID_FLAT_TYPES:
            raise ValueError(f"Invalid flat type: {flat_type}. Must be one of {VALID_FLAT_TYPES}.")
        if status not in ApplicationStatus.get_valid_statuses():
             raise ValueError(f"Invalid application status: {status}. Must be one of {ApplicationStatus.get_valid_statuses()}.")

        self.applicant_nric = applicant_nric # Foreign key to Applicant/Officer
        self.project_name = project_name   # Foreign key to Project
        self.flat_type = int(flat_type)
        self.status = status
        # Ensure request_withdrawal is boolean
        if isinstance(request_withdrawal, str):
            self.request_withdrawal = request_withdrawal.strip().lower() == 'true'
        else:
            self.request_withdrawal = bool(request_withdrawal)

    def __str__(self):
        withdrawal_str = " (Withdrawal Requested)" if self.request_withdrawal else ""
        return (f"Application(Applicant: {self.applicant_nric}, Project: {self.project_name}, "
                f"Type: {self.flat_type}-Room, Status: {self.status}{withdrawal_str})")