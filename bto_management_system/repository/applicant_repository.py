from typing import Dict, Any
from .base_repository import BaseRepository
from .storage.istorage_adapter import IStorageAdapter
from model.applicant import Applicant
from common.enums import FilePath
from common.exceptions import DataLoadError

# Applicant key is string (NRIC)
class ApplicantRepository(BaseRepository[Applicant, str]):
    _HEADERS = ['Name', 'NRIC', 'Age', 'Marital Status', 'Password']

    def __init__(self, storage_adapter: IStorageAdapter):
        super().__init__(
            storage_adapter=storage_adapter,
            model_class=Applicant,
            source_id=FilePath.APPLICANT.value,
            headers=self._HEADERS,
            key_getter=lambda applicant: applicant.nric
        )

    # Override default instance creation/dict conversion to handle User attributes directly
    def _create_instance(self, row_dict: Dict[str, Any]) -> Applicant:
        try:
            return Applicant(
                name=row_dict['Name'],
                nric=row_dict['NRIC'],
                age=int(row_dict['Age']),
                marital_status=row_dict['Marital Status'],
                password=row_dict.get('Password', 'password') # Default if missing
            )
        except (KeyError, ValueError, TypeError) as e:
            raise DataLoadError(f"Error creating Applicant from row: {row_dict}. Error: {e}")

    def _to_storage_dict(self, item: Applicant) -> Dict[str, Any]:
        return {
            'Name': item.name,
            'NRIC': item.nric,
            'Age': item.age,
            'Marital Status': item.marital_status,
            'Password': item.get_password_for_storage()
        }