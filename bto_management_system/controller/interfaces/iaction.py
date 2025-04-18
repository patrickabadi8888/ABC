from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IAction(ABC):
    """Interface for a command or action triggered by a menu choice."""

    @abstractmethod
    def execute(self, services: Dict[str, Any], views: Dict[str, Any], current_user: Optional[Any] = None, controller_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Executes the action.
        Args:
            services: Dictionary of available service instances.
            views: Dictionary of available view instances.
            current_user: The currently logged-in user object (if any).
            controller_data: Optional dictionary for passing data between controller and action (e.g., filters).
        Returns:
            An optional string signal (e.g., "LOGOUT", "EXIT") or None to continue.
        Raises:
            OperationError, IntegrityError, etc. for business logic failures.
        """
        pass