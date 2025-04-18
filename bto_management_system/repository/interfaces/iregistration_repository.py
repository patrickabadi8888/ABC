from abc import abstractmethod
from typing import Optional, List
from .ibase_repository import IBaseRepository
from model.registration import Registration
from common.enums import RegistrationStatus

# Registration key is string (composite OfficerNRIC-ProjectName)
class IRegistrationRepository(IBaseRepository[Registration, str]):
    """Interface specific to Registration data."""

    @abstractmethod
    def find_by_officer_and_project(self, officer_nric: str, project_name: str) -> Optional[Registration]:
        """Finds a specific registration by officer and project."""
        pass

    @abstractmethod
    def find_by_officer(self, officer_nric: str) -> List[Registration]:
        """Finds all registrations for a specific officer."""
        pass

    @abstractmethod
    def find_by_project(self, project_name: str, status_filter: Optional[RegistrationStatus] = None) -> List[Registration]:
        """Finds registrations for a project, optionally filtered by status."""
        pass