# models/user.py
from .roles import UserRole
from utils.helpers import validate_nric

class User:
    """Base class for all users in the system."""
    def __init__(self, name: str, nric: str, age: int, marital_status: str, password: str):
        if not validate_nric(nric):
            raise ValueError(f"Invalid NRIC format: {nric}")
        self.name = name
        self.nric = nric
        try:
            self.age = int(age)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid age: {age}. Must be an integer.")
        self.marital_status = marital_status # Consider Enum later if fixed values
        self.password = password

    def get_role(self) -> UserRole:
        """Returns the role of the user. Must be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement get_role()")

    def __eq__(self, other):
        if not isinstance(other, User):
            return NotImplemented
        return self.nric == other.nric

    def __hash__(self):
        return hash(self.nric)
    
class Applicant(User):
    """Represents an applicant user."""
    def get_role(self) -> UserRole:
        return UserRole.APPLICANT

class HDBOfficer(Applicant):
    """Represents an HDB Officer user. Inherits Applicant capabilities."""
    def get_role(self) -> UserRole:
        return UserRole.HDB_OFFICER

class HDBManager(User):
    """Represents an HDB Manager user."""
    def get_role(self) -> UserRole:
        return UserRole.HDB_MANAGER