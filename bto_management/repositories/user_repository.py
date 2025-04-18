# repositories/user_repository.py
from .base_repository import BaseRepository
from models.user import User, Applicant, HDBOfficer, HDBManager
from utils.helpers import APPLICANT_CSV, OFFICER_CSV, MANAGER_CSV, validate_nric
from utils.exceptions import DataSaveError, IntegrityError
import os

class _UserSubRepository(BaseRepository):
    """Internal helper class for specific user type CSV files."""
    def _get_key(self, item: User):
        return item.nric

    def _create_instance(self, row_dict: dict) -> User:
        nric = row_dict.get('NRIC')
        if not validate_nric(nric):
             # Log or handle more gracefully if needed during load
             raise ValueError(f"Invalid NRIC format found in data: {nric}")
        # The specific user type is determined by which file it came from,
        # so the caller (UserRepository) passes the correct model_class.
        return self.model_class(
            name=row_dict.get('Name', ''),
            nric=nric,
            age=int(row_dict.get('Age', 0)), # Default age to 0 if missing/invalid
            marital_status=row_dict.get('Marital Status', ''),
            password=row_dict.get('Password', 'password') # Default password
        )

    def _get_row_data(self, item: User) -> list:
        return [
            item.name,
            item.nric,
            str(item.age),
            item.marital_status,
            item.password
        ]

class UserRepository:
    """Manages persistence for all User types by delegating to sub-repositories."""
    def __init__(self):
        self._applicant_repo = _UserSubRepository(APPLICANT_CSV, Applicant, ['Name', 'NRIC', 'Age', 'Marital Status', 'Password'])
        self._officer_repo = _UserSubRepository(OFFICER_CSV, HDBOfficer, ['Name', 'NRIC', 'Age', 'Marital Status', 'Password'])
        self._manager_repo = _UserSubRepository(MANAGER_CSV, HDBManager, ['Name', 'NRIC', 'Age', 'Marital Status', 'Password'])
        self._all_users = {}
        self._load_all_users()

    def _load_all_users(self):
        """Loads users from all sub-repositories into a single dictionary."""
        self._all_users = {}
        loaded_count = 0
        duplicate_nrics = set()

        for repo in [self._applicant_repo, self._officer_repo, self._manager_repo]:
            repo_name = os.path.basename(repo.csv_filepath)
            for nric, user in repo.data.items():
                if nric in self._all_users:
                    print(f"CRITICAL WARNING: Duplicate NRIC '{nric}' found across user files "
                          f"(already loaded from {self._all_users[nric].__class__.__name__}, "
                          f"now found in {repo_name}). Check data integrity. Using entry from first file encountered.")
                    duplicate_nrics.add(nric)
                    # Decide on handling: skip new one, raise error, etc.
                    # Current implementation skips the duplicate.
                else:
                    self._all_users[nric] = user
                    loaded_count += 1

        print(f"Total unique users loaded: {loaded_count}.")
        if duplicate_nrics:
             print(f"Duplicate NRICs detected and skipped: {', '.join(duplicate_nrics)}")


    def find_user_by_nric(self, nric: str) -> User | None:
        """Finds any user by their NRIC."""
        return self._all_users.get(nric)

    def get_all_users(self) -> list[User]:
        """Returns a list of all loaded users."""
        return list(self._all_users.values())

    def save_user(self, user: User):
        """Saves a user to the appropriate sub-repository."""
        repo_to_use = None
        if isinstance(user, HDBManager):
            repo_to_use = self._manager_repo
        elif isinstance(user, HDBOfficer):
            repo_to_use = self._officer_repo
        elif isinstance(user, Applicant):
            repo_to_use = self._applicant_repo
        else:
            raise TypeError(f"Unknown user type cannot be saved: {type(user)}")

        try:
            # Check if user exists in the specific repo's data before updating
            # This prevents adding a user to the wrong file if only password changed
            if user.nric in repo_to_use.data:
                 repo_to_use.update(user)
            else:
                 # This case should ideally not happen if users don't change roles
                 # Or handle role changes explicitly if allowed
                 # For now, assume update implies existence in the correct file
                 raise IntegrityError(f"User {user.nric} not found in the expected repository for their role {user.get_role()}. Cannot update.")
                 # Alternative: Add if not found? Depends on requirements. repo_to_use.add(user)
            # Update the central dictionary as well
            self._all_users[user.nric] = user
        except IntegrityError as e:
             # Re-raise specific integrity errors
             raise e
        except Exception as e:
            # Catch other potential save errors
            raise DataSaveError(f"Failed to save user {user.nric} to {os.path.basename(repo_to_use.csv_filepath)}: {e}")

    # Add methods for adding or deleting users if needed, ensuring they update
    # both the specific repo and the _all_users dictionary.
    # def add_user(self, user: User): ...
    # def delete_user(self, nric: str): ...