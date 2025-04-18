from typing import Optional
from .interfaces.iauth_service import IAuthService
from repository.interfaces.iuser_repository import IUserRepository
from model.user import User
from common.enums import UserRole
from common.exceptions import OperationError, DataSaveError
from utils.input_util import InputUtil

class AuthService(IAuthService):
    """Handles authentication and password changes."""
    def __init__(self, user_repository: IUserRepository):
        self._user_repo = user_repository

    def login(self, nric: str, password: str) -> User:
        if not InputUtil.validate_nric(nric):
            raise OperationError("Invalid NRIC format.")

        user = self._user_repo.find_user_by_nric(nric)

        if user and user.check_password(password):
            return user
        elif user:
            raise OperationError("Incorrect password.")
        else:
            raise OperationError("NRIC not found.")

    def change_password(self, user: User, new_password: str):
        try:
            # Validation happens within User model's method
            user.change_password(new_password)
            # Persist change via the facade
            self._user_repo.save_user(user)
        except (ValueError, OperationError) as e: # Catch validation errors
            raise OperationError(f"Password change failed: {e}")
        except DataSaveError as e: # Catch repo/facade save errors
            # Attempting rollback here is complex without transactions.
            # Log the error and inform the user the save failed.
            print(f"ERROR: Failed to save new password for {user.nric}: {e}")
            raise OperationError(f"Failed to save new password. Please try again later.")
        except Exception as e:
            print(f"Unexpected error during password change for {user.nric}: {e}")
            raise OperationError("An unexpected error occurred during password change.")

    def get_user_role(self, user: User) -> UserRole:
        # Delegate to the user object itself
        return user.get_role()