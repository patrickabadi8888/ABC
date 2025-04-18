# repositories/application_repository.py
from .base_repository import BaseRepository
from models.application import Application
from models.roles import ApplicationStatus
from utils.helpers import APPLICATION_CSV, is_valid_int

class ApplicationRepository(BaseRepository):
    """Manages persistence for Application data."""
    def __init__(self):
        headers = ['ApplicantNRIC', 'ProjectName', 'FlatType', 'Status', 'RequestWithdrawal']
        super().__init__(APPLICATION_CSV, Application, headers)

    def _get_key(self, item: Application):
        # Define a unique key, e.g., combination of applicant NRIC and project name
        # This assumes one applicant can only have one *active* application per project,
        # or maybe one active application overall. Let's assume one active overall for now.
        # If multiple apps per person allowed (e.g., historical), need different key.
        # Key based on Applicant NRIC seems appropriate based on requirements
        # *Correction*: No, the requirement "cannot apply for multiple projects" means
        # NRIC should be unique among *active* (not unsuccessful/withdrawn) apps.
        # The repo itself stores all, so the KEY should probably allow multiples per NRIC.
        # Let's use ApplicantNRIC-ProjectName as key for uniqueness within the file.
        return f"{item.applicant_nric}-{item.project_name}"


    def _create_instance(self, row_dict: dict) -> Application:
        try:
            flat_type_str = row_dict.get('FlatType', '')
            flat_type = int(flat_type_str) if is_valid_int(flat_type_str) else 0 # Default or raise error

            # Handle boolean conversion for withdrawal request
            withdrawal_str = row_dict.get('RequestWithdrawal', 'False')
            request_withdrawal = withdrawal_str.strip().lower() == 'true'

            return Application(
                applicant_nric=row_dict.get('ApplicantNRIC', ''),
                project_name=row_dict.get('ProjectName', ''),
                flat_type=flat_type,
                status=row_dict.get('Status', ApplicationStatus.PENDING.value), # Default status
                request_withdrawal=request_withdrawal
            )
        except (ValueError, TypeError) as e:
            raise ValueError(f"Error creating Application instance from row: {row_dict}. Details: {e}")

    def _get_row_data(self, item: Application) -> list:
        return [
            item.applicant_nric,
            item.project_name,
            str(item.flat_type),
            item.status,
            str(item.request_withdrawal) # Convert boolean back to string
        ]

    # Add specific query methods if needed
    def find_by_applicant_nric(self, nric: str) -> list[Application]:
        """Finds all applications submitted by a specific applicant."""
        return [app for app in self.get_all() if app.applicant_nric == nric]

    def find_by_project_name(self, project_name: str) -> list[Application]:
        """Finds all applications for a specific project."""
        return [app for app in self.get_all() if app.project_name == project_name]

    # Override add if specific checks are needed before adding to self.data
    # For example, check if applicant already has an active application
    # This logic is better placed in the ApplicationService though.