from abc import ABC, abstractmethod
from typing import Optional
from model.user import User
from common.enums import UserRole

class IAuthService(ABC):
    """Interface for authentication and user management services."""

    @abstractmethod
    def login(self, nric: str, password: str) -> User:
        """
        Attempts to log in a user.
        Returns the User object on success.
        Raises OperationError on failure (NRIC not found, wrong password, invalid format).
        """
        pass

    @abstractmethod
    def change_password(self, user: User, new_password: str):
        """
        Changes the password for the given user.
        Raises OperationError if validation fails or save fails.
        """
        pass

    @abstractmethod
    def get_user_role(self, user: User) -> UserRole:
        """Gets the role of the user."""
        pass