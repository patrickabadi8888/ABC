from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Any, Optional

# Generic type variable for the model class
T = TypeVar('T')
# Generic type variable for the key type
K = TypeVar('K')

class IBaseRepository(Generic[T, K], ABC):
    """
    Abstract interface for basic repository operations (CRUD).
    Generic over the Model type (T) and its Key type (K).
    """

    @abstractmethod
    def get_all(self) -> List[T]:
        """Returns a list of all items."""
        pass

    @abstractmethod
    def find_by_key(self, key: K) -> Optional[T]:
        """Finds an item by its primary key."""
        pass

    @abstractmethod
    def add(self, item: T):
        """Adds a new item. Raises IntegrityError if key exists."""
        pass

    @abstractmethod
    def update(self, item: T):
        """Updates an existing item. Raises IntegrityError if key not found."""
        pass

    @abstractmethod
    def delete(self, key: K):
        """Deletes an item by its primary key. Raises IntegrityError if key not found."""
        pass

    @abstractmethod
    def save(self):
        """Persists the current state of the repository's data to storage."""
        pass

    @abstractmethod
    def load(self):
        """Loads data from storage into the repository."""
        pass