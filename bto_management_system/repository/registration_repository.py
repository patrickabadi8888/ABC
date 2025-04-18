from typing import Optional, List
from .base_repository import BaseRepository
from .interfaces.iregistration_repository import IRegistrationRepository
from .storage.istorage_adapter import IStorageAdapter
from model.registration import Registration
from common.enums import FilePath, RegistrationStatus

class RegistrationRepository(BaseRepository[Registration, str], IRegistrationRepository):
    def __init__(self, storage_adapter: IStorageAdapter):
        super().__init__(
            storage_adapter=storage_adapter,
            model_class=Registration,
            source_id=FilePath.REGISTRATION.value,
            headers=Registration._HEADERS,
            key_getter=lambda reg: f"{reg.officer_nric}-{reg.project_name}" # Composite key
        )
        # Default _create_instance and _to_storage_dict using Registration methods are sufficient

    def find_by_officer_and_project(self, officer_nric: str, project_name: str) -> Optional[Registration]:
        key = f"{officer_nric}-{project_name}"
        return self.find_by_key(key)

    def find_by_officer(self, officer_nric: str) -> List[Registration]:
        if not self._loaded: self.load()
        return [reg for reg in self._data.values() if reg.officer_nric == officer_nric]

    def find_by_project(self, project_name: str, status_filter: Optional[RegistrationStatus] = None) -> List[Registration]:
        if not self._loaded: self.load()
        regs = [reg for reg in self._data.values() if reg.project_name == project_name]
        if status_filter:
            if not isinstance(status_filter, RegistrationStatus):
                 raise ValueError("status_filter must be a RegistrationStatus enum member.")
            regs = [reg for reg in regs if reg.status == status_filter]
        return regs