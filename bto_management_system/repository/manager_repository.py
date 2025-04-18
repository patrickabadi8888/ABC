from typing import Dict, Any
from .base_repository import BaseRepository
from .storage.istorage_adapter import IStorageAdapter
from model.hdb_manager import HDBManager
from common.enums import FilePath
from common.exceptions import DataLoadError

# Manager key is string (NRIC)
class ManagerRepository(BaseRepository[HDBManager, str]):
    _HEADERS = ['Name', 'NRIC', 'Age', 'Marital Status', 'Password'] # Same as Applicant

    def __init__(self, storage_adapter: IStorageAdapter):
        super().__init__(
            storage_adapter=storage_adapter,
            model_class=HDBManager,
            source_id=FilePath.MANAGER.value,
            headers=self._HEADERS,
            key_getter=lambda manager: manager.nric
        )

    def _create_instance(self, row_dict: Dict[str, Any]) -> HDBManager:
        try:
            return HDBManager(
                name=row_dict['Name'],
                nric=row_dict['NRIC'],
                age=int(row_dict['Age']),
                marital_status=row_dict['Marital Status'],
                password=row_dict.get('Password', 'password')
            )
        except (KeyError, ValueError, TypeError) as e:
            raise DataLoadError(f"Error creating HDBManager from row: {row_dict}. Error: {e}")

    def _to_storage_dict(self, item: HDBManager) -> Dict[str, Any]:
         return {
            'Name': item.name,
            'NRIC': item.nric,
            'Age': item.age,
            'Marital Status': item.marital_status,
            'Password': item.get_password_for_storage()
        }