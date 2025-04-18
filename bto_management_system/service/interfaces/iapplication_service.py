from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from model.application import Application
from model.applicant import Applicant
from model.hdb_officer import HDBOfficer
from model.hdb_manager import HDBManager
from model.project import Project
from common.enums import FlatType

class IApplicationService(ABC):
    """Interface for application-related business logic."""

    @abstractmethod
    def find_application_by_applicant(self, applicant_nric: str) -> Optional[Application]:
        pass

    @abstractmethod
    def find_booked_application_by_applicant(self, applicant_nric: str) -> Optional[Application]:
        pass

    @abstractmethod
    def get_all_applications_by_applicant(self, applicant_nric: str) -> List[Application]:
        pass

    @abstractmethod
    def get_applications_for_project(self, project_name: str) -> List[Application]:
        pass

    @abstractmethod
    def get_all_applications(self) -> List[Application]:
        pass

    @abstractmethod
    def apply_for_project(self, applicant: Applicant, project: Project, flat_type: FlatType) -> Application:
        pass

    @abstractmethod
    def request_withdrawal(self, application: Application):
        pass

    @abstractmethod
    def manager_approve_application(self, manager: HDBManager, application: Application):
        pass

    @abstractmethod
    def manager_reject_application(self, manager: HDBManager, application: Application):
        pass

    @abstractmethod
    def manager_approve_withdrawal(self, manager: HDBManager, application: Application):
        pass

    @abstractmethod
    def manager_reject_withdrawal(self, manager: HDBManager, application: Application):
        pass

    @abstractmethod
    def officer_book_flat(self, officer: HDBOfficer, application: Application) -> Tuple[Project, Applicant]: # Return updated project and applicant
        pass