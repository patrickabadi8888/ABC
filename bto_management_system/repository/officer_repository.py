from typing import Dict, Any
from .base_repository import BaseRepository
from .storage.istorage_adapter import IStorageAdapter
from model.hdb_officer import HDBOfficer
from common.enums import FilePath
from common.exceptions import DataLoadError

# Officer key is string (NRIC)
class OfficerRepository(BaseRepository[HDBOfficer, str]):
    _HEADERS = ['Name', 'NRIC', 'Age', 'Marital Status', 'Password'] # Same as Applicant

    def __init__(self, storage_adapter: IStorageAdapter):
        super().__init__(
            storage_adapter=storage_adapter,
            model_class=HDBOfficer,
            source_id=FilePath.OFFICER.value,
            headers=self._HEADERS,
            key_getter=lambda officer: officer.nric
        )

    def _create_instance(self, row_dict: Dict[str, Any]) -> HDBOfficer:
        try:
            return HDBOfficer(
                name=row_dict['Name'],
                nric=row_dict['NRIC'],
                age=int(row_dict['Age']),
                marital_status=row_dict['Marital Status'],
                password=row_dict.get('Password', 'password')
            )
        except (KeyError, ValueError, TypeError) as e:
            raise DataLoadError(f"Error creating HDBOfficer from row: {row_dict}. Error: {e}")

    def _to_storage_dict(self, item: HDBOfficer) -> Dict[str, Any]:
         return {
            'Name': item.name,
            'NRIC': item.nric,
            'Age': item.age,
            'Marital Status': item.marital_status,
            'Password': item.get_password_for_storage()
        }