from .date_util import DateUtil # Use the dedicated DateUtil
from datetime import date

class InputUtil:
    """Handles validated user input."""

    @staticmethod
    def validate_nric(nric: str) -> bool:
        """Validates the format of a Singapore NRIC."""
        if not isinstance(nric, str) or len(nric) != 9:
            return False
        first_char = nric[0].upper()
        if first_char not in ('S', 'T'):
            return False
        if not nric[1:8].isdigit():
            return False
        if not nric[8].isalpha():
            return False
        return True

    @staticmethod
    def get_valid_integer_input(prompt: str, min_val: int | None = None, max_val: int | None = None) -> int:
        """Gets integer input within optional bounds."""
        while True:
            try:
                value_str = input(f"{prompt}: ").strip()
                value = int(value_str)
                if (min_val is not None and value < min_val) or \
                   (max_val is not None and value > max_val):
                    range_msg = ""
                    if min_val is not None and max_val is not None:
                        range_msg = f" between {min_val} and {max_val}"
                    elif min_val is not None:
                        range_msg = f" >= {min_val}"
                    elif max_val is not None:
                        range_msg = f" <= {max_val}"
                    print(f"ERROR: Input must be an integer{range_msg}.")
                else:
                    return value
            except ValueError:
                print("ERROR: Invalid input. Please enter an integer.")
            except KeyboardInterrupt:
                print("\nInput cancelled by user.")
                raise # Re-raise to allow higher levels to catch

    @staticmethod
    def get_valid_date_input(prompt: str) -> date:
        """Gets date input in the standard format."""
        while True:
            date_str = input(f"{prompt} ({DateUtil.DATE_FORMAT}): ").strip()
            parsed_date = DateUtil.parse_date(date_str)
            if parsed_date:
                return parsed_date
            else:
                print(f"ERROR: Invalid date format. Please use {DateUtil.DATE_FORMAT}.")
            # Allow KeyboardInterrupt to propagate

    @staticmethod
    def get_non_empty_input(prompt: str) -> str:
        """Gets input that is not empty or just whitespace."""
        while True:
            value = input(f"{prompt}: ").strip()
            if value:
                return value
            else:
                print("ERROR: Input cannot be empty.")
            # Allow KeyboardInterrupt to propagate

    @staticmethod
    def get_yes_no_input(prompt: str) -> bool:
        """Gets a 'y' or 'n' response."""
        while True:
            choice = input(f"{prompt} (y/n): ").strip().lower()
            if choice == 'y':
                return True
            elif choice == 'n':
                return False
            print("ERROR: Please enter 'y' or 'n'.")
            # Allow KeyboardInterrupt to propagate