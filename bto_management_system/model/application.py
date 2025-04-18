from utils.input_util import InputUtil
from common.enums import FlatType, ApplicationStatus
from common.exceptions import DataLoadError, OperationError

class Application:
    """Represents a BTO application."""
    _HEADERS = ['ApplicantNRIC', 'ProjectName', 'FlatType', 'Status', 'RequestWithdrawal']

    def __init__(self, applicant_nric: str, project_name: str, flat_type: FlatType,
                 status: ApplicationStatus = ApplicationStatus.PENDING,
                 request_withdrawal: bool = False):

        if not InputUtil.validate_nric(applicant_nric): raise ValueError("Invalid Applicant NRIC")
        if not project_name: raise ValueError("Project Name cannot be empty")
        if not isinstance(flat_type, FlatType): raise ValueError("Invalid FlatType")
        if not isinstance(status, ApplicationStatus): raise ValueError("Invalid ApplicationStatus")

        self._applicant_nric = applicant_nric
        self._project_name = project_name
        self._flat_type = flat_type
        self._status = status
        self._request_withdrawal = bool(request_withdrawal)

    # --- Getters ---
    @property
    def applicant_nric(self): return self._applicant_nric
    @property
    def project_name(self): return self._project_name
    @property
    def flat_type(self): return self._flat_type
    @property
    def status(self): return self._status
    @property
    def request_withdrawal(self): return self._request_withdrawal

    # --- State Modifiers ---
    def set_status(self, new_status: ApplicationStatus):
        if not isinstance(new_status, ApplicationStatus):
            raise ValueError("Invalid status provided.")
        # Basic state transition validation (can be enhanced in Service layer)
        # Allow setting to unsuccessful from any state if withdrawal approved
        # Allow setting to current state
        allowed = {
            ApplicationStatus.PENDING: [ApplicationStatus.SUCCESSFUL, ApplicationStatus.UNSUCCESSFUL, ApplicationStatus.PENDING],
            ApplicationStatus.SUCCESSFUL: [ApplicationStatus.BOOKED, ApplicationStatus.UNSUCCESSFUL, ApplicationStatus.SUCCESSFUL],
            ApplicationStatus.BOOKED: [ApplicationStatus.UNSUCCESSFUL, ApplicationStatus.BOOKED],
            ApplicationStatus.UNSUCCESSFUL: [ApplicationStatus.UNSUCCESSFUL] # Terminal state
        }
        if new_status not in allowed.get(self._status, []):
             if not (new_status == ApplicationStatus.UNSUCCESSFUL and self._request_withdrawal):
                  print(f"Warning: Potentially invalid status transition: {self._status.value} -> {new_status.value}")

        self._status = new_status

    def set_withdrawal_request(self, requested: bool):
        if requested and self._status not in [ApplicationStatus.PENDING, ApplicationStatus.SUCCESSFUL, ApplicationStatus.BOOKED]:
             raise OperationError(f"Cannot request withdrawal for application with status '{self._status.value}'.")
        self._request_withdrawal = bool(requested)

    def to_csv_dict(self) -> dict:
        return {
            'ApplicantNRIC': self._applicant_nric,
            'ProjectName': self._project_name,
            'FlatType': self._flat_type.value,
            'Status': self._status.value,
            'RequestWithdrawal': str(self._request_withdrawal)
        }

    @classmethod
    def from_csv_dict(cls, row_dict: dict) -> 'Application':
        try:
            flat_type = FlatType.from_value(row_dict['FlatType'])
            status = ApplicationStatus(row_dict['Status'])
            request_withdrawal = row_dict.get('RequestWithdrawal', 'False').lower() == 'true'

            return cls(
                applicant_nric=row_dict['ApplicantNRIC'],
                project_name=row_dict['ProjectName'],
                flat_type=flat_type,
                status=status,
                request_withdrawal=request_withdrawal
            )
        except (KeyError, ValueError, TypeError) as e:
            raise DataLoadError(f"Error creating Application from CSV row: {row_dict}. Error: {e}")

    def __eq__(self, other):
        if not isinstance(other, Application): return NotImplemented
        return (self._applicant_nric == other._applicant_nric and
                self._project_name == other._project_name)

    def __hash__(self):
        return hash((self._applicant_nric, self._project_name))

    def get_display_summary(self, applicant_name: str) -> str:
         req_status = " (Withdrawal Requested)" if self._request_withdrawal else ""
         return (f"Project: {self._project_name} | Applicant: {applicant_name} ({self._applicant_nric}) | "
                 f"Type: {self._flat_type.to_string()} | Status: {self._status.value}{req_status}")