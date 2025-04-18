from abc import ABC, abstractmethod
from typing import List, Optional
from model.registration import Registration
from model.hdb_officer import HDBOfficer
from model.hdb_manager import HDBManager
from model.project import Project
from common.enums import RegistrationStatus

class IRegistrationService(ABC):
    """Interface for officer registration business logic."""

    @abstractmethod
    def find_registration(self, officer_nric: str, project_name: str) -> Optional[Registration]:
        pass

    @abstractmethod
    def get_registrations_by_officer(self, officer_nric: str) -> List[Registration]:
        pass

    @abstractmethod
    def get_registrations_for_project(self, project_name: str, status_filter: Optional[RegistrationStatus] = None) -> List[Registration]:
        pass

    @abstractmethod
    def officer_register_for_project(self, officer: HDBOfficer, project: Project) -> Registration:
        pass

    @abstractmethod
    def manager_approve_officer_registration(self, manager: HDBManager, registration: Registration):
        pass

    @abstractmethod
    def manager_reject_officer_registration(self, manager: HDBManager, registration: Registration):
        pass