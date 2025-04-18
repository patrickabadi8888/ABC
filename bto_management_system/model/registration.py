from utils.input_util import InputUtil
from common.enums import RegistrationStatus
from common.exceptions import DataLoadError

class Registration:
    """Represents an HDB Officer's registration for a project."""
    _HEADERS = ['OfficerNRIC', 'ProjectName', 'Status']

    def __init__(self, officer_nric: str, project_name: str, status: RegistrationStatus = RegistrationStatus.PENDING):
        if not InputUtil.validate_nric(officer_nric): raise ValueError("Invalid Officer NRIC")
        if not project_name: raise ValueError("Project Name cannot be empty")
        if not isinstance(status, RegistrationStatus): raise ValueError("Invalid RegistrationStatus")

        self._officer_nric = officer_nric
        self._project_name = project_name
        self._status = status

    # --- Getters ---
    @property
    def officer_nric(self): return self._officer_nric
    @property
    def project_name(self): return self._project_name
    @property
    def status(self): return self._status

    # --- State Modifiers ---
    def set_status(self, new_status: RegistrationStatus):
        if not isinstance(new_status, RegistrationStatus):
            raise ValueError("Invalid status provided.")
        if self._status != RegistrationStatus.PENDING and new_status != self._status:
             print(f"Warning: Changing registration status from non-pending state: {self._status.value} -> {new_status.value}")
        self._status = new_status

    def to_csv_dict(self) -> dict:
        return {
            'OfficerNRIC': self._officer_nric,
            'ProjectName': self._project_name,
            'Status': self._status.value
        }

    @classmethod
    def from_csv_dict(cls, row_dict: dict) -> 'Registration':
        try:
            status = RegistrationStatus(row_dict['Status'])
            return cls(
                officer_nric=row_dict['OfficerNRIC'],
                project_name=row_dict['ProjectName'],
                status=status
            )
        except (KeyError, ValueError, TypeError) as e:
            raise DataLoadError(f"Error creating Registration from CSV row: {row_dict}. Error: {e}")

    def __eq__(self, other):
        if not isinstance(other, Registration): return NotImplemented
        return (self._officer_nric == other._officer_nric and
                self._project_name == other._project_name)

    def __hash__(self):
        return hash((self._officer_nric, self._project_name))

    def get_display_summary(self, officer_name: str) -> str:
         return f"Project: {self._project_name} | Officer: {officer_name} ({self._officer_nric}) | Status: {self._status.value}"