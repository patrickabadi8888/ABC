from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Any

class IStorageAdapter(ABC):
    """Interface for reading and writing data from/to a persistent storage."""

    @abstractmethod
    def read_data(self, source_id: str, expected_headers: List[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Reads data from the specified source.
        Args:
            source_id: Identifier for the data source (e.g., file path).
            expected_headers: List of headers expected in the source.
        Returns:
            A tuple containing:
            - List of dictionaries representing the data rows.
            - The actual headers found in the source.
        Raises:
            DataLoadError: If the source cannot be read or headers are invalid.
            FileNotFoundError: If the source does not exist (implementations may handle creation).
        """
        pass

    @abstractmethod
    def write_data(self, source_id: str, headers: List[str], data_dicts: List[Dict[str, Any]]):
        """
        Writes data to the specified source.
        Args:
            source_id: Identifier for the data source (e.g., file path).
            headers: The list of headers to write.
            data_dicts: A list of dictionaries representing the data rows.
        Raises:
            DataSaveError: If the data cannot be written.
        """
        pass