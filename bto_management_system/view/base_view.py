from typing import List, Dict, Any, Optional
from utils.input_util import InputUtil # Corrected import path

class BaseView:
    """Base class for all views. Handles basic input and output."""

    def display_message(self, message: str, error: bool = False, info: bool = False, warning: bool = False):
        """Displays a formatted message."""
        prefix = ""
        if error: prefix = "ERROR: "
        elif warning: prefix = "WARNING: "
        elif info: prefix = "INFO: "
        print(f"\n{prefix}{message}")

    def get_input(self, prompt: str) -> str:
        """Gets basic string input from the user."""
        # Use InputUtil for potentially more robust input handling if needed later
        return input(f"{prompt}: ").strip()

    def get_password(self, prompt: str = "Enter password") -> str:
        """Gets password input (simple text input for CLI)."""
        # Consider getpass library if masking is strictly required and allowed
        return input(f"{prompt}: ").strip()

    def display_menu(self, title: str, options: List[str]) -> Optional[int]:
        """Displays a numbered menu and gets a valid choice (1-based index)."""
        print(f"\n--- {title} ---")
        if not options:
            print("No options available.")
            return None

        valid_indices = []
        offset = 0
        for i, option in enumerate(options):
            if option.startswith("---"): # Handle separators
                print(f"  {option}")
                offset += 1
            else:
                print(f"{i + 1 - offset}. {option}")
                valid_indices.append(i + 1 - offset) # Store 1-based index of valid options

        print("--------------------")

        if not valid_indices: # Only separators were present
             print("No actionable options available.")
             return None

        # Use InputUtil for validated integer input within the range of valid options
        min_choice = min(valid_indices) if valid_indices else 1
        max_choice = max(valid_indices) if valid_indices else 0 # Will cause validation to fail if no valid options

        if max_choice == 0: return None # No valid options to choose from

        # Loop until a valid *actionable* choice is made
        while True:
            choice = InputUtil.get_valid_integer_input("Enter your choice", min_val=min_choice, max_val=max_choice)
            if choice in valid_indices:
                return choice # Return the 1-based index of the chosen *actionable* item
            else:
                # This case should ideally not be reached if menu display logic is correct
                self.display_message("Please select one of the numbered options.", warning=True)


    def display_list(self, title: str, items: List[Any], empty_message: str = "No items to display."):
        """Displays a numbered list of items using their string representation."""
        print(f"\n--- {title} ---")
        if not items:
            print(empty_message)
        else:
            for i, item in enumerate(items):
                # Attempt to use a specific display method if available, else __str__
                display_str = str(item)
                if hasattr(item, 'get_display_summary') and callable(item.get_display_summary):
                    display_str = item.get_display_summary()
                elif hasattr(item, 'get_display_details') and callable(item.get_display_details):
                     display_str = item.get_display_details() # Fallback if summary not present

                print(f"{i + 1}. {display_str}")
        print("--------------------")

    def display_dict(self, title: str, data_dict: Dict[str, Any]):
        """Displays key-value pairs from a dictionary, aligned."""
        print(f"\n--- {title} ---")
        if not data_dict:
            print("(No details)")
        else:
            max_key_len = 0
            if data_dict:
                 try:
                      max_key_len = max(len(str(k)) for k in data_dict.keys())
                 except ValueError: # Handle empty dict case
                      max_key_len = 0

            for key, value in data_dict.items():
                # Handle multi-line values gracefully
                value_lines = str(value).splitlines()
                print(f"  {str(key):<{max_key_len}} : {value_lines[0]}")
                for line in value_lines[1:]:
                    print(f"  {' ' * (max_key_len + 3)}{line}") # Indent subsequent lines

        print("-" * (len(title) + 6))

    def pause_for_user(self):
        """Pauses execution until the user presses Enter."""
        input("\nPress Enter to continue...")