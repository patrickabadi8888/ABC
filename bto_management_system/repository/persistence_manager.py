from typing import List
from .interfaces.ibase_repository import IBaseRepository
from common.exceptions import DataSaveError

class PersistenceManager:
    """Manages loading and saving data across multiple repositories."""

    def __init__(self, repositories: List[IBaseRepository]):
        """
        Initializes the PersistenceManager.
        Args:
            repositories: A list of repository instances to manage.
        """
        self._repositories = repositories

    def load_all(self):
        """Loads data for all managed repositories."""
        print("Loading all data...")
        errors = []
        for repo in self._repositories:
            try:
                repo.load()
            except Exception as e:
                # Log error but continue loading others
                error_msg = f"Failed to load data for {type(repo).__name__}: {e}"
                print(f"ERROR: {error_msg}")
                errors.append(error_msg)
        if errors:
            # Decide if loading errors are fatal or just warnings
            # For now, treat as warnings but report them
            print("\n--- Loading Errors Encountered ---")
            for err in errors:
                print(f"- {err}")
            print("---------------------------------")
        else:
            print("All data loaded successfully.")


    def save_all(self):
        """Saves data for all managed repositories."""
        print("\nSaving all data...")
        errors = []
        for repo in self._repositories:
            try:
                repo.save()
            except Exception as e:
                error_msg = f"Failed to save data for {type(repo).__name__}: {e}"
                print(f"ERROR: {error_msg}")
                errors.append(error_msg)

        if errors:
            # Combine errors into a single exception to signal failure
            raise DataSaveError("Errors occurred during data save:\n" + "\n".join(errors))
        else:
            print("All data saved successfully.")