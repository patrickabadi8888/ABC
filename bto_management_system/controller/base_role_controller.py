from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple, Type
from model.user import User
from view.base_view import BaseView
from common.exceptions import OperationError, IntegrityError
from .interfaces.iaction import IAction
from .actions.common_actions import ChangePasswordAction, LogoutAction, ExitAction, NoOpAction

class BaseRoleController(ABC):
    """Abstract base class for role-specific controllers using the Action pattern."""
    def __init__(self, current_user: User, services: Dict[str, Any], views: Dict[str, Any]):
        self._current_user = current_user
        self._services = services
        self._views = views
        # Store shared data like filters here, passed to actions
        self._controller_data = {'filters': {}}
        # Menu definition: List of (Display String, Action Class or None for separator)
        self._menu_definition: List[Tuple[str, Optional[Type[IAction]]]] = []
        self._action_instances: Dict[Type[IAction], IAction] = {} # Cache action instances

        self._build_menu() # Populate _menu_definition in subclasses

    @abstractmethod
    def _build_menu(self):
        """Subclasses must implement this to define their menu structure."""
        pass

    def _get_action_instance(self, action_class: Type[IAction]) -> IAction:
        """Gets or creates an instance of an action class."""
        if action_class not in self._action_instances:
            self._action_instances[action_class] = action_class() # Instantiate if not cached
        return self._action_instances[action_class]

    def run_menu(self) -> Optional[str]:
        """Displays the menu for the role and handles the selected action."""
        
        base_view: BaseView = self._views['base']

        menu_options = [item[0] for item in self._menu_definition]
        action_map: Dict[int, Optional[IAction]] = {} # Map 1-based index to action instance
        current_index = 1
        for _, action_class in self._menu_definition:
            if action_class:
                action_map[current_index] = self._get_action_instance(action_class)
                current_index += 1
            else:
                # Separators don't increment the choice index mapping
                pass

        # Display menu and get choice
        choice_index = base_view.display_menu(f"{self._current_user.get_role().value} Menu", menu_options)
        if choice_index is None: return None # Should not happen with validated input

        # Find the corresponding action instance from the map
        selected_action = action_map.get(choice_index)

        if selected_action:
            try:
                # Execute the chosen action, passing necessary context
                return selected_action.execute(self._services, self._views, self._current_user, self._controller_data)
            except (OperationError, IntegrityError) as e:
                base_view.display_message(str(e), error=True)
            except KeyboardInterrupt:
                 base_view.display_message("\nOperation cancelled by user.")
            except Exception as e:
                 base_view.display_message(f"An unexpected error occurred: {e}", error=True)
        elif menu_options[choice_index - 1].startswith("---"):
             pass # Ignore separator selection
        else:
             base_view.display_message("Invalid menu option selected.", error=True)

        base_view.pause_for_user()
        return None # Continue showing menu unless logout/exit signal received

    def _get_common_menu_items(self) -> List[Tuple[str, Optional[Type[IAction]]]]:
        """Returns standard menu items common to all logged-in users."""
        return [
            ("--- General Actions ---", None),
            ("Change Password", ChangePasswordAction),
            ("Logout", LogoutAction),
            ("Exit System", ExitAction),
        ]