# models/registration.py
from .roles import RegistrationStatus

class Registration:
    """Represents an HDB Officer's registration request for a Project."""
    def __init__(self, officer_nric: str, project_name: str,
                 status: str = RegistrationStatus.PENDING.value):

        if status not in RegistrationStatus.get_valid_statuses():
             raise ValueError(f"Invalid registration status: {status}. Must be one of {RegistrationStatus.get_valid_statuses()}.")

        self.officer_nric = officer_nric # Foreign key to HDBOfficer
        self.project_name = project_name # Foreign key to Project
        self.status = status

    def __str__(self):
        return (f"Registration(Officer: {self.officer_nric}, Project: {self.project_name}, "
                f"Status: {self.status})")