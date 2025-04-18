from abc import ABC
from typing import TypeVar, List, Dict, Any, Optional, Callable, Type
from .interfaces.ibase_repository import IBaseRepository
from .storage.istorage_adapter import IStorageAdapter
from common.exceptions import IntegrityError, DataLoadError, DataSaveError, ConfigurationError

# Re-declare generics for use within this class
T = TypeVar('T')
K = TypeVar('K')

class BaseRepository(IBaseRepository[T, K], ABC):
    """
    Abstract base implementation for repositories using an IStorageAdapter.
    Handles loading, saving, and in-memory storage.
    """
    def __init__(self,
                 storage_adapter: IStorageAdapter,
                 model_class: Type[T],
                 source_id: str,
                 headers: List[str],
                 key_getter: Callable[[T], K]):
        """
        Initializes the repository.
        Args:
            storage_adapter: The adapter for reading/writing data.
            model_class: The class of the model this repository manages (e.g., Project).
            source_id: Identifier for the data source (e.g., file path).
            headers: Expected headers for the data source.
            key_getter: A function that takes a model instance and returns its unique key.
        """
        if not all([storage_adapter, model_class, source_id, headers, key_getter]):
            raise ConfigurationError("All BaseRepository constructor arguments must be provided.")

        self._storage = storage_adapter
        self._model_class = model_class
        self._source_id = source_id
        self._headers = headers
        self._get_key = key_getter
        self._data: Dict[K, T] = {} # In-memory store {key: model_instance}
        self._loaded = False

    def _create_instance(self, row_dict: Dict[str, Any]) -> T:
        """Creates a model instance from a storage row dictionary."""
        # Default implementation assumes Model.from_csv_dict exists
        try:
            # Check if the class method exists before calling
            from_dict_method = getattr(self._model_class, "from_csv_dict", None)
            if callable(from_dict_method):
                return from_dict_method(row_dict)
            else:
                raise NotImplementedError(f"{self._model_class.__name__} must implement from_csv_dict or _create_instance must be overridden.")
        except (DataLoadError, ValueError, TypeError, KeyError) as e:
             # Catch specific errors from model creation
             raise DataLoadError(f"Error creating {self._model_class.__name__} instance: {e}")

    def _to_storage_dict(self, item: T) -> Dict[str, Any]:
        """Converts a model instance to a dictionary suitable for storage."""
        # Default implementation assumes item.to_csv_dict exists
        try:
            # Check if the instance method exists before calling
            to_dict_method = getattr(item, "to_csv_dict", None)
            if callable(to_dict_method):
                return to_dict_method()
            else:
                 raise NotImplementedError(f"{self._model_class.__name__} must implement to_csv_dict or _to_storage_dict must be overridden.")
        except Exception as e:
            # Catch potential errors during conversion
            raise DataSaveError(f"Error converting {self._model_class.__name__} instance to dict: {e}")

    def load(self):
        """Loads data from the storage adapter into the in-memory store."""
        if self._loaded:
            print(f"Data for {self._model_class.__name__} already loaded.")
            return

        self._data = {}
        try:
            storage_data, _ = self._storage.read_data(self._source_id, self._headers)
            for i, row_dict in enumerate(storage_data):
                try:
                    instance = self._create_instance(row_dict)
                    key = self._get_key(instance)
                    if key in self._data:
                        raise IntegrityError(f"Duplicate key '{key}' found for {self._model_class.__name__} in {self._source_id} at source row {i+2}.")
                    self._data[key] = instance
                except (ValueError, TypeError, IntegrityError, DataLoadError) as e:
                    print(f"Warning: Error processing row {i+2} in {self._source_id}: {row_dict}. Error: {e}. Skipping.")
                except Exception as e: # Catch unexpected errors during instance creation/keying
                    print(f"Warning: Unexpected error processing row {i+2} in {self._source_id}: {row_dict}. Error: {e}. Skipping.")

            self._loaded = True
            print(f"Loaded {len(self._data)} {self._model_class.__name__} items from {self._source_id}.")

        except (FileNotFoundError, DataLoadError) as e:
            print(f"Info: Issue loading {self._source_id}: {e}. Starting with empty data.")
            self._data = {} # Ensure data is empty if load fails
            self._loaded = True # Mark as loaded even if empty/failed to avoid reload attempts
        except IntegrityError as e: # Fatal integrity error during load
             raise DataLoadError(f"Fatal integrity error loading {self._source_id}: {e}")

    def save(self):
        """Saves the current in-memory data back to storage via the adapter."""
        if not self._loaded:
            print(f"Warning: Attempting to save {self._model_class.__name__} data before loading. Skipping save.")
            return
        try:
            # Sort keys for consistent output order (optional but good practice)
            # Handle potential non-sortable keys gracefully
            try:
                sorted_keys = sorted(self._data.keys())
            except TypeError:
                sorted_keys = list(self._data.keys()) # Use original order if keys aren't sortable

            data_to_write = [self._to_storage_dict(self._data[key]) for key in sorted_keys]
            self._storage.write_data(self._source_id, self._headers, data_to_write)
            # print(f"Saved {len(data_to_write)} {self._model_class.__name__} items to {self._source_id}.") # Optional success message
        except (DataSaveError, IOError) as e:
            raise DataSaveError(f"Failed to save data for {self._model_class.__name__} to {self._source_id}: {e}")
        except Exception as e:
             raise DataSaveError(f"Unexpected error saving data for {self._model_class.__name__} to {self._source_id}: {e}")

    # --- IBaseRepository Implementation ---
    def get_all(self) -> List[T]:
        if not self._loaded: self.load()
        return list(self._data.values())

    def find_by_key(self, key: K) -> Optional[T]:
        if not self._loaded: self.load()
        return self._data.get(key)

    def add(self, item: T):
        if not self._loaded: self.load()
        if not isinstance(item, self._model_class):
            raise TypeError(f"Item must be of type {self._model_class.__name__}")
        key = self._get_key(item)
        if key in self._data:
            raise IntegrityError(f"{self._model_class.__name__} with key '{key}' already exists.")
        self._data[key] = item
        # Defer saving to explicit save() call or PersistenceManager

    def update(self, item: T):
        if not self._loaded: self.load()
        if not isinstance(item, self._model_class):
            raise TypeError(f"Item must be of type {self._model_class.__name__}")
        key = self._get_key(item)
        if key not in self._data:
            raise IntegrityError(f"{self._model_class.__name__} with key '{key}' not found for update.")
        self._data[key] = item
        # Defer saving

    def delete(self, key: K):
        if not self._loaded: self.load()
        if key not in self._data:
            raise IntegrityError(f"{self._model_class.__name__} with key '{key}' not found for deletion.")
        del self._data[key]
        # Defer saving