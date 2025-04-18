from abc import abstractmethod
from typing import Optional, List
from .ibase_repository import IBaseRepository
from model.application import Application

# Application key is string (composite ApplicantNRIC-ProjectName)
class IApplicationRepository(IBaseRepository[Application, str]):
    """Interface specific to Application data."""

    @abstractmethod
    def find_by_applicant_nric(self, nric: str) -> Optional[Application]:
        """Finds the current non-unsuccessful application for an applicant."""
        pass

    @abstractmethod
    def find_all_by_applicant_nric(self, nric: str) -> List[Application]:
        """Finds all applications (including unsuccessful) for an applicant."""
        pass

    @abstractmethod
    def find_by_project_name(self, project_name: str) -> List[Application]:
        """Finds all applications associated with a specific project."""
        pass