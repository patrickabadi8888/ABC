from enum import Enum

class UserRole(Enum):
    APPLICANT = "Applicant"
    HDB_OFFICER = "HDB Officer"
    HDB_MANAGER = "HDB Manager"

class ApplicationStatus(Enum):
    PENDING = "PENDING"
    SUCCESSFUL = "SUCCESSFUL"
    UNSUCCESSFUL = "UNSUCCESSFUL"
    BOOKED = "BOOKED"

class RegistrationStatus(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class FilePath(Enum):
    # Store relative paths, assuming execution from project root
    # Or configure absolute paths if needed
    APPLICANT = 'data/ApplicantList.csv'
    OFFICER = 'data/OfficerList.csv'
    MANAGER = 'data/ManagerList.csv'
    PROJECT = 'data/ProjectList.csv'
    APPLICATION = 'data/ApplicationData.csv'
    REGISTRATION = 'data/RegistrationData.csv'
    ENQUIRY = 'data/EnquiryData.csv'

class FlatType(Enum):
    TWO_ROOM = 2
    THREE_ROOM = 3

    # Helper to get enum from value, useful for CSV loading
    @classmethod
    def from_value(cls, value):
        try:
            return cls(int(value))
        except (ValueError, TypeError):
            raise ValueError(f"Invalid value for FlatType: {value}")

    # Helper to get descriptive string
    def to_string(self):
        return f"{self.value}-Room"