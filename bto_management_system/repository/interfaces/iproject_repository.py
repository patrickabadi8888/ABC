from abc import abstractmethod
from typing import Optional, List
from .ibase_repository import IBaseRepository
from model.project import Project

class IProjectRepository(IBaseRepository[Project, str]):
    """Interface specific to Project data."""

    @abstractmethod
    def find_by_name(self, name: str) -> Optional[Project]:
        """Finds a project by its unique name."""
        pass

    @abstractmethod
    def find_by_manager_nric(self, manager_nric: str) -> List[Project]:
        """Finds all projects managed by a specific manager."""
        pass
