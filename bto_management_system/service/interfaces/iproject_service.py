from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Set
from datetime import date
from model.project import Project
from model.hdb_manager import HDBManager
from model.applicant import Applicant
from model.application import Application # For viewable check

class IProjectService(ABC):
    """Interface for project-related business logic."""

    @abstractmethod
    def find_project_by_name(self, name: str) -> Optional[Project]:
        pass

    @abstractmethod
    def get_all_projects(self) -> List[Project]:
        pass

    @abstractmethod
    def get_projects_by_manager(self, manager_nric: str) -> List[Project]:
        pass

    @abstractmethod
    def get_handled_project_names_for_officer(self, officer_nric: str) -> Set[str]:
        pass

    @abstractmethod
    def get_viewable_projects_for_applicant(self, applicant: Applicant, current_application: Optional[Application] = None) -> List[Project]:
        pass

    @abstractmethod
    def filter_projects(self, projects: List[Project], location: Optional[str] = None, flat_type_str: Optional[str] = None) -> List[Project]:
        pass

    @abstractmethod
    def create_project(self, manager: HDBManager, name: str, neighborhood: str, n1: int, p1: int, n2: int, p2: int, od: date, cd: date, slot: int) -> Project:
        pass

    @abstractmethod
    def edit_project(self, manager: HDBManager, project: Project, updates: Dict):
        pass

    @abstractmethod
    def delete_project(self, manager: HDBManager, project: Project):
        pass

    @abstractmethod
    def toggle_project_visibility(self, manager: HDBManager, project: Project) -> str: # Returns "ON" or "OFF"
        pass

    @abstractmethod
    def add_officer_to_project(self, project: Project, officer_nric: str) -> bool:
        pass

    @abstractmethod
    def remove_officer_from_project(self, project: Project, officer_nric: str) -> bool:
        pass