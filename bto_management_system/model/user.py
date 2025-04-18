from abc import ABC, abstractmethod
from utils.input_util import InputUtil
from common.enums import UserRole
from common.exceptions import OperationError

class User(ABC):
    """Abstract base class for all users."""
    def __init__(self, name: str, nric: str, age: int, marital_status: str, password: str = "password"):
        if not name: raise ValueError("Name cannot be empty.")
        if not InputUtil.validate_nric(nric):
            raise ValueError(f"Invalid NRIC format: {nric}")
        if not isinstance(age, int) or age < 0:
            raise ValueError(f"Invalid age value: {age}")
        if not marital_status: raise ValueError("Marital status cannot be empty.")
        if not password: raise ValueError("Password cannot be empty.")

        self._name = name
        self._nric = nric
        self._age = age
        self._marital_status = marital_status
        self._password = password

    @property
    def name(self) -> str:
        return self._name

    @property
    def nric(self) -> str:
        return self._nric

    @property
    def age(self) -> int:
        return self._age

    @property
    def marital_status(self) -> str:
        return self._marital_status

    def check_password(self, password_attempt: str) -> bool:
        """Verifies if the provided password matches."""
        return self._password == password_attempt

    def change_password(self, new_password: str):
        """Updates the user's password after validation."""
        if not new_password:
            raise OperationError("Password cannot be empty.")
        # Add more password complexity rules here if needed
        self._password = new_password

    def get_password_for_storage(self) -> str:
        """Allows repository layer to retrieve the password for saving."""
        return self._password

    @abstractmethod
    def get_role(self) -> UserRole:
        """Returns the specific role of the user."""
        pass

    # Explicit method for display instead of relying solely on __str__
    def get_display_details(self) -> str:
        return f"Name: {self._name}, NRIC: {self._nric}, Role: {self.get_role().value}"

    # Keep __eq__ and __hash__ for identity based on NRIC
    def __eq__(self, other):
        if not isinstance(other, User):
            return NotImplemented
        return self._nric == other._nric

    def __hash__(self):
        return hash(self._nric)