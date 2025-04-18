from abc import ABC, abstractmethod
from typing import List, Optional
from model.enquiry import Enquiry
from model.applicant import Applicant
from model.user import User # For replier
from model.project import Project

class IEnquiryService(ABC):
    """Interface for enquiry-related business logic."""

    @abstractmethod
    def find_enquiry_by_id(self, enquiry_id: int) -> Optional[Enquiry]:
        pass

    @abstractmethod
    def get_enquiries_by_applicant(self, applicant_nric: str) -> List[Enquiry]:
        pass

    @abstractmethod
    def get_enquiries_for_project(self, project_name: str) -> List[Enquiry]:
        pass

    @abstractmethod
    def get_all_enquiries(self) -> List[Enquiry]:
        pass

    @abstractmethod
    def submit_enquiry(self, applicant: Applicant, project: Project, text: str) -> Enquiry:
        pass

    @abstractmethod
    def edit_enquiry(self, applicant: Applicant, enquiry: Enquiry, new_text: str):
        pass

    @abstractmethod
    def delete_enquiry(self, applicant: Applicant, enquiry: Enquiry):
        pass

    @abstractmethod
    def reply_to_enquiry(self, replier_user: User, enquiry: Enquiry, reply_text: str):
        pass