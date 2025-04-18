# services/auth_service.py
from repositories.user_repository import UserRepository
from models.user import User
from utils.exceptions import AuthenticationError, OperationError, DataSaveError
from utils.helpers import validate_nric

class AuthService:
    """Handles user authentication and password management."""
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def login(self, nric: str, password: str) -> User:
        """Authenticates a user based on NRIC and password."""
        if not validate_nric(nric):
            raise AuthenticationError("Invalid NRIC format.")

        user = self.user_repository.find_user_by_nric(nric)

        if user is None:
            raise AuthenticationError(f"NRIC '{nric}' not found.")

        # In a real system, use hashed passwords and verification
        if user.password != password:
            raise AuthenticationError("Incorrect password.")

        print(f"User {user.name} ({user.get_role().name}) logged in successfully.")
        return user

    def change_password(self, user: User, current_password: str, new_password: str):
        """Changes the password for the given user after verifying the current one."""
        if not new_password or new_password.isspace():
            raise OperationError("New password cannot be empty.")

        # Verify current password before changing
        if user.password != current_password:
             raise OperationError("Incorrect current password.")

        # Basic validation (add more rules if needed)
        if len(new_password) < 4: # Example minimum length
             raise OperationError("New password must be at least 4 characters long.")

        if new_password == user.password:
             raise OperationError("New password cannot be the same as the old password.")

        # Update the user object and save
        user.password = new_password
        try:
            self.user_repository.save_user(user)
            print(f"Password changed successfully for user {user.nric}.")
        except DataSaveError as e:
            # Revert the password change on the object if save fails?
            # For simplicity, we'll just report the error.
            # user.password = current_password # Revert if needed
            raise OperationError(f"Failed to save new password due to a data error: {e}")
        except Exception as e:
            # Catch unexpected errors during save
            raise OperationError(f"An unexpected error occurred while saving the new password: {e}")

    def get_user_role(self, user: User):
         """Safely gets the user's role."""
         try:
             return user.get_role()
         except Exception as e:
             print(f"Error getting role for user {user.nric}: {e}")
             return None # Or a default role / raise error