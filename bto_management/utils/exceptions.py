# utils/exceptions.py
class DataLoadError(Exception):
    """Error loading data from persistence."""
    pass

class DataSaveError(Exception):
    """Error saving data to persistence."""
    pass

class IntegrityError(Exception):
    """Data integrity violation (e.g., duplicate key, foreign key issue)."""
    pass

class OperationError(Exception):
    """Error during a user-initiated operation (e.g., invalid input, insufficient permissions)."""
    pass

class AuthenticationError(OperationError):
    """Specific error for login failures."""
    pass

class AuthorizationError(OperationError):
    """Specific error for permission denied."""
    pass