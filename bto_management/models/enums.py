# models/enums.py
from enum import Enum, auto

class UserRole(Enum):
    APPLICANT = auto()
    HDB_OFFICER = auto()
    HDB_MANAGER = auto()

class ApplicationStatus(Enum):
    PENDING = "PENDING"
    SUCCESSFUL = "SUCCESSFUL"
    UNSUCCESSFUL = "UNSUCCESSFUL"
    BOOKED = "BOOKED"

    @classmethod
    def get_valid_statuses(cls):
        return [status.value for status in cls]

class RegistrationStatus(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

    @classmethod
    def get_valid_statuses(cls):
        return [status.value for status in cls]

class FlatType(Enum):
    TWO_ROOM = 2
    THREE_ROOM = 3

    @classmethod
    def get_valid_types(cls):
        return [flat_type.value for flat_type in cls]