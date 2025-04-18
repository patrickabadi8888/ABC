# models/roles.py
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

# Flat Type constants
FLAT_TYPE_2_ROOM = 2
FLAT_TYPE_3_ROOM = 3
VALID_FLAT_TYPES = [FLAT_TYPE_2_ROOM, FLAT_TYPE_3_ROOM]