from typing import Optional, List
from .base_repository import BaseRepository
from .interfaces.iapplication_repository import IApplicationRepository
from .storage.istorage_adapter import IStorageAdapter
from model.application import Application
from common.enums import FilePath, ApplicationStatus
from common.exceptions import IntegrityError

class ApplicationRepository(BaseRepository[Application, str], IApplicationRepository):
    def __init__(self, storage_adapter: IStorageAdapter):
        super().__init__(
            storage_adapter=storage_adapter,
            model_class=Application,
            source_id=FilePath.APPLICATION.value,
            headers=Application._HEADERS,
            key_getter=lambda app: f"{app.applicant_nric}-{app.project_name}" # Composite key
        )
        # Default _create_instance and _to_storage_dict using Application methods are sufficient

    def find_by_applicant_nric(self, nric: str) -> Optional[Application]:
        """Finds the current non-unsuccessful application for an applicant."""
        if not self._loaded: self.load()
        for app in self._data.values():
            if app.applicant_nric == nric and app.status != ApplicationStatus.UNSUCCESSFUL:
                return app
        return None

    def find_all_by_applicant_nric(self, nric: str) -> List[Application]:
        """Finds all applications (including unsuccessful) for an applicant."""
        if not self._loaded: self.load()
        return [app for app in self._data.values() if app.applicant_nric == nric]

    def find_by_project_name(self, project_name: str) -> List[Application]:
        if not self._loaded: self.load()
        return [app for app in self._data.values() if app.project_name == project_name]

    # Override add to check for existing active application before adding
    def add(self, item: Application):
        if not self._loaded: self.load()
        # Check for existing *active* application by this applicant
        existing_active = self.find_by_applicant_nric(item.applicant_nric)
        if existing_active:
            raise IntegrityError(f"Applicant {item.applicant_nric} already has an active application for project '{existing_active.project_name}'.")
        # Use base class add logic if check passes
        super().add(item)