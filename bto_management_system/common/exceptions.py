class DataLoadError(Exception):
    """Error during data loading from storage."""
    pass

class DataSaveError(Exception):
    """Error during data saving to storage."""
    pass

class IntegrityError(Exception):
    """Data integrity violation (e.g., duplicate key, not found)."""
    pass

class OperationError(Exception):
    """Error during a business logic operation (e.g., eligibility fail, invalid state)."""
    pass

class ConfigurationError(Exception):
    """Error related to application configuration or setup."""
    pass