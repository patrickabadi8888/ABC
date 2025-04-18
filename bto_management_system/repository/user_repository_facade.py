from typing import Optional, List, Dict
from .interfaces.iuser_repository import IUserRepository
from .interfaces.ibase_repository import IBaseRepository # For type hinting internal repos
from model.user import User
from model.applicant import Applicant
from model.hdb_officer import HDBOfficer
from model.hdb_manager import HDBManager
from common.exceptions import OperationError, DataSaveError, IntegrityError

class UserRepositoryFacade(IUserRepository):
    """Facade to provide a single point of access for finding/saving users across roles."""

    def __init__(self, applicant_repo: IBaseRepository[Applicant, str],
                 officer_repo: IBaseRepository[HDBOfficer, str],
                 manager_repo: IBaseRepository[HDBManager, str]):
        self._applicant_repo = applicant_repo
        self._officer_repo = officer_repo
        self._manager_repo = manager_repo
        self._all_users: Dict[str, User] = {} # Combined cache {nric: user_instance}
        self._loaded = False

    def load_all_users(self):
        """Loads users from all specific repositories into the combined cache."""
        if self._loaded: return
        self._all_users = {}
        duplicates = 0

        repos = [self._applicant_repo, self._officer_repo, self._manager_repo]
        for repo in repos:
            try:
                # Ensure underlying repos are loaded first
                repo.load()
                items = repo.get_all()
                for user in items:
                    if user.nric in self._all_users:
                        # Log clearly which file is overwriting which
                        existing_user_type = type(self._all_users[user.nric]).__name__
                        new_user_type = type(user).__name__
                        print(f"Warning: Duplicate NRIC '{user.nric}' found. Overwriting {existing_user_type} entry with {new_user_type} entry.")
                        duplicates += 1
                    self._all_users[user.nric] = user
            except Exception as e:
                 print(f"Error loading users from {type(repo).__name__}: {e}") # Log error but continue

        self._loaded = True
        print(f"Total unique users loaded into facade: {len(self._all_users)} (encountered {duplicates} duplicates).")

    def find_user_by_nric(self, nric: str) -> Optional[User]:
        if not self._loaded: self.load_all_users()
        return self._all_users.get(nric)

    def get_all_users(self) -> List[User]:
        if not self._loaded: self.load_all_users()
        return list(self._all_users.values())

    def save_user(self, user: User):
        """Delegates saving to the appropriate repository based on role."""
        if not self._loaded:
             # Avoid saving if not loaded, could lead to data loss
             raise OperationError("User data not loaded. Cannot save user.")

        repo: Optional[IBaseRepository] = None
        if isinstance(user, HDBManager): repo = self._manager_repo
        elif isinstance(user, HDBOfficer): repo = self._officer_repo
        elif isinstance(user, Applicant): repo = self._applicant_repo
        else: raise TypeError(f"Unknown user type cannot be saved: {type(user)}")

        try:
            # Attempt to update first (common case)
            repo.update(user)
        except IntegrityError: # If update fails (user not found in that repo), try adding
            try:
                repo.add(user)
            except IntegrityError as add_e: # If add also fails (duplicate key)
                 raise OperationError(f"Failed to add user {user.nric} after update failed: {add_e}")
            except Exception as add_e:
                 raise DataSaveError(f"Failed to add user {user.nric}: {add_e}")
        except Exception as update_e: # Catch other update errors
            raise DataSaveError(f"Failed to update user {user.nric}: {update_e}")

        # Update the facade's cache immediately after successful add/update
        self._all_users[user.nric] = user
        # Defer actual file saving to PersistenceManager or explicit repo.save()

    def save_all_user_types(self):
        """Saves data for all underlying user repositories."""
        print("Saving user data...")
        errors = []
        for repo in [self._applicant_repo, self._officer_repo, self._manager_repo]:
            try:
                repo.save()
            except Exception as e:
                errors.append(f"Failed to save {type(repo).__name__}: {e}")
        if errors:
            raise DataSaveError("Errors occurred during user save:\n" + "\n".join(errors))
        print("User data saved.")