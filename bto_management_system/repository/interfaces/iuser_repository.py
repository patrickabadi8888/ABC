from abc import ABC, abstractmethod
from typing import Optional, List
from model.user import User

class IUserRepository(ABC):
    """Interface for accessing user data across all roles."""

    @abstractmethod
    def find_user_by_nric(self, nric: str) -> Optional[User]:
        """Finds any user (Applicant, Officer, Manager) by NRIC."""
        pass

    @abstractmethod
    def get_all_users(self) -> List[User]:
        """Gets a list of all users from all roles."""
        pass

    @abstractmethod
    def save_user(self, user: User):
        """Saves changes to a specific user in the appropriate underlying repository."""
        pass

    @abstractmethod
    def load_all_users(self):
        """Loads users from all underlying repositories."""
        pass

    @abstractmethod
    def save_all_user_types(self):
        """Saves data for all underlying user repositories."""
        pass