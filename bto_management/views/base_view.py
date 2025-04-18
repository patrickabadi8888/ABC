# views/base_view.py
from utils import helpers

class BaseView:
    """Provides common methods for displaying information and getting input."""

    def display_message(self, message: str, error: bool = False, info: bool = False, warning: bool = False):
        """Displays a formatted message."""
        prefix = ""
        if error:
            prefix = "ERROR: "
        elif info:
            prefix = "INFO: "
        elif warning:
            prefix = "WARNING: "
        print(f"\n{prefix}{message}")

    def get_input(self, prompt: str) -> str:
        """Gets simple string input from the user."""
        return input(f"{prompt}: ").strip()

    def get_password(self, prompt: str = "Enter password") -> str:
        """Gets password input (consider using getpass library for masking in real app)."""
        # Note: getpass might not work well in all IDEs/terminals
        # import getpass
        # return getpass.getpass(f"{prompt}: ")
        return input(f"{prompt}: ").strip() # Simple input for CLI compatibility

    def display_menu(self, title: str, options: list[str]) -> int | None:
        """Displays a numbered menu and gets a valid choice."""
        print(f"\n--- {title} ---")
        if not options:
            print("No options available.")
            return None
        for i, option in enumerate(options):
            print(f"{i + 1}. {option}")
        print("--------------------")

        # Use helper for validated integer input
        choice = helpers.get_valid_integer_input("Enter your choice", min_val=1, max_val=len(options))
        return choice # Returns the 1-based index

    def display_list(self, title: str, items: list, empty_message: str = "No items to display."):
        """Displays a simple numbered list."""
        print(f"\n--- {title} ---")
        if not items:
            print(empty_message)
        else:
            for i, item in enumerate(items):
                # Attempt to call str() on item, handle potential errors
                try:
                     item_str = str(item)
                except Exception as e:
                     item_str = f"[Error displaying item: {e}]"
                print(f"{i + 1}. {item_str}")
        print("--------------------")

    def display_dict(self, title: str, data_dict: dict):
        """Displays data from a dictionary in a key-value format."""
        print(f"\n--- {title} ---")
        if not data_dict:
            print("(No details)")
        else:
            # Find max key length for alignment (optional, but nice)
            max_key_len = 0
            if data_dict:
                try:
                    max_key_len = max(len(str(k)) for k in data_dict.keys())
                except ValueError: # Handles case where dict might be empty after check
                    pass

            for key, value in data_dict.items():
                try:
                     key_str = str(key)
                     value_str = str(value)
                except Exception as e:
                     key_str = "[Error Key]"
                     value_str = f"[Error Value: {e}]"

                print(f"  {key_str:<{max_key_len}} : {value_str}")
        print("-" * (len(title) + 6)) # Simple separator