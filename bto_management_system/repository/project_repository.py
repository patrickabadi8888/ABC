from typing import Optional, List
from .base_repository import BaseRepository
from .interfaces.iproject_repository import IProjectRepository
from .storage.istorage_adapter import IStorageAdapter
from model.project import Project
from common.enums import FilePath

class ProjectRepository(BaseRepository[Project, str], IProjectRepository):
    def __init__(self, storage_adapter: IStorageAdapter):
        super().__init__(
            storage_adapter=storage_adapter,
            model_class=Project,
            source_id=FilePath.PROJECT.value,
            headers=Project._HEADERS, # Use headers defined in Project model
            key_getter=lambda project: project.project_name
        )
        # Default _create_instance and _to_storage_dict using Project methods are sufficient

    def find_by_name(self, name: str) -> Optional[Project]:
        return self.find_by_key(name)

    def delete_by_name(self, name: str):
        self.delete(name) # Base class handles key not found

    def find_by_manager_nric(self, manager_nric: str) -> List[Project]:
        # Assuming your projects are stored in a dictionary like self._items
        # or a list like self._data from a base class
        # Adapt this line based on how you store the loaded projects internally
        return [project for project in self.get_all() if project.manager_nric == manager_nric]