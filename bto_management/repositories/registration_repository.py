# repositories/registration_repository.py
from .base_repository import BaseRepository
from models.registration import Registration
from models.roles import RegistrationStatus
from utils.helpers import REGISTRATION_CSV

class RegistrationRepository(BaseRepository):
    """Manages persistence for HDB Officer Registration data."""
    def __init__(self):
        headers = ['OfficerNRIC', 'ProjectName', 'Status']
        super().__init__(REGISTRATION_CSV, Registration, headers)

    def _get_key(self, item: Registration):
        # Unique key: officer NRIC + project name
        return f"{item.officer_nric}-{item.project_name}"

    def _create_instance(self, row_dict: dict) -> Registration:
        try:
            return Registration(
                officer_nric=row_dict.get('OfficerNRIC', ''),
                project_name=row_dict.get('ProjectName', ''),
                status=row_dict.get('Status', RegistrationStatus.PENDING.value) # Default status
            )
        except (ValueError, TypeError) as e:
             raise ValueError(f"Error creating Registration instance from row: {row_dict}. Details: {e}")

    def _get_row_data(self, item: Registration) -> list:
        return [
            item.officer_nric,
            item.project_name,
            item.status
        ]

    # Add specific query methods
    def find_by_officer_nric(self, officer_nric: str) -> list[Registration]:
        """Finds all registrations for a specific officer."""
        return [reg for reg in self.get_all() if reg.officer_nric == officer_nric]

    def find_by_project_name(self, project_name: str) -> list[Registration]:
        """Finds all registrations for a specific project."""
        return [reg for reg in self.get_all() if reg.project_name == project_name]

    def find_by_officer_and_project(self, officer_nric: str, project_name: str) -> Registration | None:
        """Finds a specific registration by officer and project."""
        key = f"{officer_nric}-{project_name}"
        return self.find_by_key(key)