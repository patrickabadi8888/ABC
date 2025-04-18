from typing import Optional, List
from .base_repository import BaseRepository
from .interfaces.ienquiry_repository import IEnquiryRepository
from .storage.istorage_adapter import IStorageAdapter
from model.enquiry import Enquiry
from common.enums import FilePath
from common.exceptions import IntegrityError

class EnquiryRepository(BaseRepository[Enquiry, int], IEnquiryRepository):
    def __init__(self, storage_adapter: IStorageAdapter):
        super().__init__(
            storage_adapter=storage_adapter,
            model_class=Enquiry,
            source_id=FilePath.ENQUIRY.value,
            headers=Enquiry._HEADERS,
            key_getter=lambda enquiry: enquiry.enquiry_id # Key is integer ID
        )
        self._next_id = 0 # Initialized during load

    def _calculate_next_id(self):
        """Calculates the next ID based on current data."""
        if not self._data:
            return 1
        # Keys are integers (EnquiryID)
        try:
            return max(int(k) for k in self._data.keys()) + 1
        except ValueError: # Handle case where keys might not be ints somehow
             print("Warning: Could not determine max Enquiry ID. Resetting next ID to 1.")
             return 1

    # Override load to calculate next ID after data is loaded
    def load(self):
        super().load() # Load data using base class method
        self._next_id = self._calculate_next_id() # Calculate ID based on loaded data

    # Override add to assign the next ID
    def add(self, item: Enquiry):
        if not self._loaded: self.load()
        if not isinstance(item, self._model_class):
            raise TypeError(f"Item must be of type {self._model_class.__name__}")

        # Assign the next available ID before adding
        item.set_id(self._next_id)
        key = self._get_key(item) # Get the newly assigned ID as key

        if key in self._data:
            # This should ideally not happen if next_id logic is correct
            raise IntegrityError(f"Enquiry with generated ID '{key}' already exists. ID generation failed?")

        self._data[key] = item
        self._next_id += 1 # Increment for the next add
        # Defer saving

    def get_next_id(self) -> int:
        if not self._loaded: self.load()
        return self._next_id

    def find_by_id(self, enquiry_id: int) -> Optional[Enquiry]:
        try:
            key = int(enquiry_id)
            return self.find_by_key(key)
        except (ValueError, TypeError):
            return None # Invalid ID format

    def find_by_applicant(self, applicant_nric: str) -> List[Enquiry]:
        if not self._loaded: self.load()
        return [enq for enq in self._data.values() if enq.applicant_nric == applicant_nric]

    def find_by_project(self, project_name: str) -> List[Enquiry]:
        if not self._loaded: self.load()
        return [enq for enq in self._data.values() if enq.project_name == project_name]

    def delete_by_id(self, enquiry_id: int):
         try:
            key = int(enquiry_id)
            self.delete(key) # Base delete handles not found error
         except (ValueError, TypeError):
             raise IntegrityError(f"Invalid Enquiry ID format for deletion: {enquiry_id}")