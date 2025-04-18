from .applicant import Applicant # Officers are also Applicants
from common.enums import UserRole

class HDBOfficer(Applicant):
    """Represents an HDB Officer user. Inherits Applicant capabilities."""
    def __init__(self, name: str, nric: str, age: int, marital_status: str, password: str = "password"):
        super().__init__(name, nric, age, marital_status, password)

    def get_role(self) -> UserRole:
        return UserRole.HDB_OFFICER