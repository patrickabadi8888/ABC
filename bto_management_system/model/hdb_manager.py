from .user import User
from common.enums import UserRole

class HDBManager(User):
    """Represents an HDB Manager user."""
    def __init__(self, name: str, nric: str, age: int, marital_status: str, password: str = "password"):
        super().__init__(name, nric, age, marital_status, password)

    def get_role(self) -> UserRole:
        return UserRole.HDB_MANAGER