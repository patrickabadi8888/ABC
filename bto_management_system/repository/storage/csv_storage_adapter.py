import os
from typing import List, Dict, Tuple, Any
from .istorage_adapter import IStorageAdapter
from common.exceptions import DataLoadError, DataSaveError

class CsvStorageAdapter(IStorageAdapter):
    """Implements storage adapter using simple CSV file handling."""

    @staticmethod
    def _parse_csv_line(line: str) -> List[str]:
        """Parses a single CSV line, handling basic quoting."""
        fields = []
        current_field = ''
        in_quotes = False
        i = 0
        while i < len(line):
            char = line[i]
            if char == '"':
                if in_quotes and i + 1 < len(line) and line[i+1] == '"':
                    current_field += '"' # Handle escaped quote ("")
                    i += 1
                else:
                    in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                fields.append(current_field)
                current_field = ''
            else:
                current_field += char
            i += 1
        fields.append(current_field) # Add the last field
        return fields

    @staticmethod
    def _format_csv_field(field_value: Any) -> str:
        """Formats a single field for CSV, adding quotes if necessary."""
        str_value = str(field_value)
        if ',' in str_value or '"' in str_value or '\n' in str_value:
            return '"' + str_value.replace('"', '""') + '"'
        return str_value

    @staticmethod
    def _format_csv_row(row_values: List[Any]) -> str:
        """Formats a list of values into a CSV row string."""
        return ','.join(CsvStorageAdapter._format_csv_field(field) for field in row_values)

    def read_data(self, source_id: str, expected_headers: List[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Reads data from a CSV file."""
        file_path = source_id
        if not os.path.exists(file_path):
            print(f"Warning: Data file not found: {file_path}. Creating empty file with headers.")
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True) # Ensure directory exists
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self._format_csv_row(expected_headers) + '\n')
                return [], list(expected_headers) # Return empty data and expected headers
            except IOError as e:
                raise DataLoadError(f"Error creating data file {file_path}: {e}")

        data = []
        headers = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                header_line = f.readline().strip()
                if not header_line:
                    print(f"Warning: Data file {file_path} is empty. Using expected headers.")
                    with open(file_path, 'w', encoding='utf-8') as fw:
                         fw.write(self._format_csv_row(expected_headers) + '\n')
                    return [], list(expected_headers)

                headers = self._parse_csv_line(header_line)
                if not all(h in headers for h in expected_headers):
                    missing = [h for h in expected_headers if h not in headers]
                    extra = [h for h in headers if h not in expected_headers]
                    msg = f"Invalid headers in {file_path}. Expected: {expected_headers}. Found: {headers}."
                    if missing: msg += f" Missing: {missing}."
                    if extra: msg += f" Extra: {extra}."
                    raise DataLoadError(msg)

                header_map = {h: i for i, h in enumerate(headers)}
                for i, line in enumerate(f):
                    line = line.strip()
                    if not line: continue
                    row_values = self._parse_csv_line(line)
                    if len(row_values) != len(headers):
                         print(f"Warning: Skipping malformed row {i+2} in {file_path}. Fields: {len(row_values)}, Headers: {len(headers)}. Line: '{line}'")
                         continue

                    row_dict = {}
                    valid_row = True
                    # Use actual headers found for creating dict, but ensure expected ones exist
                    for req_h in expected_headers:
                        if req_h not in header_map:
                             print(f"Warning: Missing expected column '{req_h}' in header map for row {i+2} of {file_path}. Skipping row.")
                             valid_row = False
                             break
                        try:
                            idx = header_map[req_h]
                            row_dict[req_h] = row_values[idx]
                        except IndexError:
                            print(f"Warning: Index error accessing column '{req_h}' (index {idx}) in row {i+2} of {file_path}. Skipping row.")
                            valid_row = False
                            break
                    if valid_row:
                        data.append(row_dict)

        except FileNotFoundError: # Should be handled by os.path.exists now
             raise DataLoadError(f"File not found: {file_path}")
        except IOError as e:
            raise DataLoadError(f"Error reading data file {file_path}: {e}")
        except Exception as e:
            raise DataLoadError(f"Unexpected error reading CSV {file_path}: {e}")

        return data, headers # Return actual headers read

    def write_data(self, source_id: str, headers: List[str], data_dicts: List[Dict[str, Any]]):
        """Writes data to a CSV file."""
        file_path = source_id
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True) # Ensure directory exists
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self._format_csv_row(headers) + '\n')
                for row_dict in data_dicts:
                    row_values = [row_dict.get(header, '') for header in headers]
                    f.write(self._format_csv_row(row_values) + '\n')
        except IOError as e:
            raise DataSaveError(f"Error writing data to {file_path}: {e}")
        except Exception as e:
            raise DataSaveError(f"Unexpected error writing CSV {file_path}: {e}")