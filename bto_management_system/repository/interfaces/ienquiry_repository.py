from abc import abstractmethod
from typing import Optional, List
from .ibase_repository import IBaseRepository
from model.enquiry import Enquiry

# Enquiry key is int (enquiry_id)
class IEnquiryRepository(IBaseRepository[Enquiry, int]):
    """Interface specific to Enquiry data."""

    # find_by_key is inherited as find_by_id implicitly
    @abstractmethod
    def find_by_id(self, enquiry_id: int) -> Optional[Enquiry]:
        """Alias for find_by_key for clarity."""
        pass

    @abstractmethod
    def find_by_applicant(self, applicant_nric: str) -> List[Enquiry]:
        """Finds all enquiries submitted by a specific applicant."""
        pass

    @abstractmethod
    def find_by_project(self, project_name: str) -> List[Enquiry]:
        """Finds all enquiries related to a specific project."""
        pass

    @abstractmethod
    def delete_by_id(self, enquiry_id: int):
        """Alias for delete for clarity."""
        pass

    @abstractmethod
    def get_next_id(self) -> int:
        """Gets the next available ID for a new enquiry."""
        pass