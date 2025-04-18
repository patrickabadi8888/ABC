# repositories/enquiry_repository.py
from .base_repository import BaseRepository
from models.enquiry import Enquiry
from utils.helpers import ENQUIRY_CSV, is_valid_int
from utils.exceptions import IntegrityError

class EnquiryRepository(BaseRepository):
    """Manages persistence for Enquiry data."""
    def __init__(self):
        headers = ['EnquiryID', 'ApplicantNRIC', 'ProjectName', 'Text', 'Reply']
        # Enquiry ID is the primary key
        super().__init__(ENQUIRY_CSV, Enquiry, headers)
        self.next_id = self._calculate_next_id()

    def _calculate_next_id(self) -> int:
        """Determines the next available ID based on existing data."""
        if not self.data:
            return 1
        max_id = 0
        for key in self.data.keys():
             # Ensure key is treated as int for comparison
             try:
                 current_id = int(key)
                 if current_id > max_id:
                     max_id = current_id
             except ValueError:
                 print(f"Warning: Non-integer key '{key}' found in Enquiry data. Skipping for ID calculation.")
                 continue
        return max_id + 1


    def _get_key(self, item: Enquiry):
        # Use the Enquiry's ID as the key
        return item.enquiry_id

    def _create_instance(self, row_dict: dict) -> Enquiry:
        try:
             enquiry_id_str = row_dict.get('EnquiryID', '')
             enquiry_id = int(enquiry_id_str) if is_valid_int(enquiry_id_str) else 0 # Default or raise error

             return Enquiry(
                 enquiry_id=enquiry_id,
                 applicant_nric=row_dict.get('ApplicantNRIC', ''),
                 project_name=row_dict.get('ProjectName', ''),
                 text=row_dict.get('Text', ''),
                 reply=row_dict.get('Reply', '') # Reply might be empty
             )
        except (ValueError, TypeError) as e:
             raise ValueError(f"Error creating Enquiry instance from row: {row_dict}. Details: {e}")


    def _get_row_data(self, item: Enquiry) -> list:
        return [
            str(item.enquiry_id),
            item.applicant_nric,
            item.project_name,
            item.text,
            item.reply
        ]

    # Override add to assign the next ID
    def add(self, item: Enquiry):
        """Adds a new enquiry, assigning the next available ID."""
        if not isinstance(item, Enquiry):
            raise TypeError("Item to add must be an Enquiry instance.")

        # Assign the next available ID before adding
        item.enquiry_id = self.next_id
        key = self._get_key(item)

        if key in self.data:
             # This should theoretically not happen if next_id logic is correct
             raise IntegrityError(f"Enquiry with auto-assigned ID '{key}' already exists. Check ID generation logic.")

        self.data[key] = item
        self.next_id += 1 # Increment ID for the next add
        self.save_data() # Persist immediately

    def find_by_id(self, enquiry_id: int) -> Enquiry | None:
        """Finds an enquiry by its unique ID."""
        return self.find_by_key(enquiry_id)

    def find_by_applicant_nric(self, applicant_nric: str) -> list[Enquiry]:
        """Finds all enquiries submitted by a specific applicant."""
        return [enq for enq in self.get_all() if enq.applicant_nric == applicant_nric]

    def find_by_project_name(self, project_name: str) -> list[Enquiry]:
        """Finds all enquiries related to a specific project."""
        return [enq for enq in self.get_all() if enq.project_name == project_name]

    def delete_by_id(self, enquiry_id: int):
        """Deletes an enquiry by its ID."""
        self.delete(enquiry_id)