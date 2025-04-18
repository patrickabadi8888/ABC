# repositories/base_repository.py
import os
from abc import ABC, abstractmethod
from utils.exceptions import DataLoadError, DataSaveError, IntegrityError

class BaseRepository(ABC):
    """Abstract base class for repositories using manual CSV handling without external helpers."""

    def __init__(self, csv_filepath: str, model_class, required_headers: list, delimiter: str = ","):
        self.csv_filepath = csv_filepath
        self.model_class = model_class
        self.required_headers = required_headers
        self.delimiter = delimiter
        self.data = {}  # in-memory store keyed by _get_key()
        self._load_data()

    def _ensure_file_exists(self):
        """Ensure the CSV file exists; create with header if missing."""
        if not os.path.exists(self.csv_filepath):
            try:
                os.makedirs(os.path.dirname(self.csv_filepath), exist_ok=True)
                with open(self.csv_filepath, 'w', newline='') as f:
                    f.write(self.delimiter.join(self.required_headers) + '\n')
            except OSError as e:
                raise DataSaveError(f"Could not create file {self.csv_filepath}: {e}")

    def _load_data(self):
        """Load rows from CSV into self.data."""
        self._ensure_file_exists()
        self.data.clear()
        try:
            with open(self.csv_filepath, 'r', newline='') as f:
                header_line = f.readline()
                if not header_line:
                    raise DataLoadError(f"Missing header in {self.csv_filepath}")
                cols = [c.strip() for c in header_line.rstrip('\n').split(self.delimiter)]
                if cols != self.required_headers:
                    raise DataLoadError(
                        f"Header mismatch in {self.csv_filepath}. "
                        f"Expected {self.required_headers}, found {cols}"
                    )
                idx_map = {h: i for i, h in enumerate(cols)}

                count = 0
                for lineno, line in enumerate(f, start=2):
                    line = line.rstrip('\n')
                    if not line:
                        continue
                    parts = line.split(self.delimiter)
                    if len(parts) < len(cols):
                        print(f"Warning: skipping short row {lineno} in {self.csv_filepath}: {line}")
                        continue
                    row = {h: parts[idx_map[h]].strip() for h in self.required_headers}
                    try:
                        inst = self._create_instance(row)
                        key = self._get_key(inst)
                        if key is None:
                            print(f"Warning: null key at row {lineno}, skipping")
                            continue
                        if key in self.data:
                            print(f"Warning: duplicate key '{key}' at row {lineno}, overwriting")
                        self.data[key] = inst
                        count += 1
                    except (ValueError, TypeError) as e:
                        print(f"Warning: error parsing row {lineno} in {self.csv_filepath}: {row}. {e}")
                print(f"Loaded {count} items from {os.path.basename(self.csv_filepath)}.")
        except DataLoadError:
            raise
        except Exception as e:
            raise DataLoadError(f"Error loading {self.csv_filepath}: {e}")

    def save_data(self):
        """Write self.data back to CSV atomically."""
        temp = self.csv_filepath + '.tmp'
        try:
            with open(temp, 'w', newline='') as f:
                # write header
                f.write(self.delimiter.join(self.required_headers) + '\n')
                # write rows in sorted key order
                for key in sorted(self.data):
                    try:
                        row = self._get_row_data(self.data[key])
                        if len(row) != len(self.required_headers):
                            raise ValueError(
                                f"Row length {len(row)} != headers {len(self.required_headers)}"
                            )
                        f.write(self.delimiter.join(str(v) for v in row) + '\n')
                    except Exception as e:
                        print(f"Error serializing key '{key}': {e}")
            os.replace(temp, self.csv_filepath)
        except Exception as e:
            if os.path.exists(temp):
                try:
                    os.remove(temp)
                except OSError:
                    pass
            raise DataSaveError(f"Error saving {self.csv_filepath}: {e}")

    @abstractmethod
    def _get_key(self, item):
        """Return the unique key for the item."""
        pass

    @abstractmethod
    def _create_instance(self, row_dict: dict):
        """Instantiate model from row data."""
        pass

    @abstractmethod
    def _get_row_data(self, item) -> list:
        """Serialize item back into list of column values."""
        pass

    def get_all(self):
        return list(self.data.values())

    def find_by_key(self, key):
        return self.data.get(key)

    def add(self, item):
        key = self._get_key(item)
        if key is None:
            raise ValueError("Null key not allowed")
        if key in self.data:
            raise IntegrityError(f"Duplicate key '{key}' in {self.csv_filepath}")
        self.data[key] = item
        self.save_data()

    def update(self, item):
        key = self._get_key(item)
        if key is None:
            raise ValueError("Null key not allowed")
        if key not in self.data:
            raise IntegrityError(f"Key '{key}' not found in {self.csv_filepath}")
        self.data[key] = item
        self.save_data()

    def delete(self, key):
        if key is None:
            raise ValueError("Null key not allowed")
        if key not in self.data:
            raise IntegrityError(f"Key '{key}' not found in {self.csv_filepath}")
        del self.data[key]
        self.save_data()
