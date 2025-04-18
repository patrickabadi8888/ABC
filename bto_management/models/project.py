# models/project.py
from datetime import date
from utils.helpers import format_date, parse_date, is_valid_int
from .roles import FLAT_TYPE_2_ROOM, FLAT_TYPE_3_ROOM

class Project:
    """Represents a BTO project listing."""
    def __init__(self, project_name: str, neighborhood: str,
                 num_units_2_room: int, price_2_room: int,
                 num_units_3_room: int, price_3_room: int,
                 opening_date: date, closing_date: date,
                 manager_nric: str, officer_slot: int,
                 officer_nrics: list = None, visibility: bool = True):

        # Input validation for critical numeric fields and dates
        if not all(is_valid_int(v) and int(v) >= 0 for v in [
                   num_units_2_room, price_2_room, num_units_3_room, price_3_room, officer_slot]):
            raise ValueError("Unit counts, prices, and officer slots must be non-negative integers.")
        if not (0 <= int(officer_slot) <= 10):
             raise ValueError("Officer slots must be between 0 and 10.")
        if not isinstance(opening_date, date) or not isinstance(closing_date, date):
             # Allow None dates? For now, assume they must be valid date objects on creation.
             # If None is allowed from CSV, handle it here or in the repository's _create_instance.
             raise ValueError("Opening and closing dates must be valid date objects.")
        if closing_date < opening_date:
             raise ValueError("Closing date cannot be before opening date.")

        self.project_name = project_name
        self.neighborhood = neighborhood
        # Store flat details directly
        self.num_units_2_room = int(num_units_2_room)
        self.price_2_room = int(price_2_room)
        self.num_units_3_room = int(num_units_3_room)
        self.price_3_room = int(price_3_room)
        self.opening_date = opening_date
        self.closing_date = closing_date
        self.manager_nric = manager_nric # Foreign key to HDBManager
        self.officer_slot = int(officer_slot)
        # Ensure officer_nrics is a list of strings (NRICs), handle None and filter empty strings
        self.officer_nrics = [str(nric).strip() for nric in officer_nrics if str(nric).strip()] if officer_nrics is not None else []
        # Ensure visibility is a boolean, handle string conversion from CSV robustly
        if isinstance(visibility, str):
            self.visibility = visibility.strip().lower() == 'true'
        else:
            self.visibility = bool(visibility)

    def is_active_period(self, check_date: date = None) -> bool:
        """Checks if the project is within its application period (inclusive)."""
        if check_date is None:
            check_date = date.today()
        # Check if dates are valid before comparison
        if not isinstance(self.opening_date, date) or not isinstance(self.closing_date, date):
            return False # Cannot be active without valid dates
        return self.opening_date <= check_date <= self.closing_date

    def is_currently_active_for_application(self) -> bool:
        """Checks if the project is visible AND within its application period right now."""
        return self.visibility and self.is_active_period()

    def get_flat_details(self, flat_type_room: int) -> tuple[int, int]:
        """Returns (number of units, price) for the given flat type."""
        if flat_type_room == FLAT_TYPE_2_ROOM:
            return self.num_units_2_room, self.price_2_room
        elif flat_type_room == FLAT_TYPE_3_ROOM:
            return self.num_units_3_room, self.price_3_room
        print(f"Warning: Invalid flat type requested: {flat_type_room}")
        return 0, 0 # Return zero tuple for invalid type

    def decrease_unit_count(self, flat_type_room: int) -> bool:
        """Decreases the unit count for the specified flat type if available. Returns True if successful."""
        if flat_type_room == FLAT_TYPE_2_ROOM:
            if self.num_units_2_room > 0:
                self.num_units_2_room -= 1
                return True
        elif flat_type_room == FLAT_TYPE_3_ROOM:
            if self.num_units_3_room > 0:
                self.num_units_3_room -= 1
                return True
        return False # Unit type invalid or count already zero

    def increase_unit_count(self, flat_type_room: int) -> bool:
        """Increases the unit count (e.g., if a booking fails/is withdrawn before finalization). Returns True if successful."""
        # No upper bound check needed usually, assuming it's reverting a decrease
        if flat_type_room == FLAT_TYPE_2_ROOM:
            self.num_units_2_room += 1
            return True
        elif flat_type_room == FLAT_TYPE_3_ROOM:
            self.num_units_3_room += 1
            return True
        return False # Invalid flat type

    def can_add_officer(self) -> bool:
        """Checks if there are available slots for HDB Officers."""
        return len(self.officer_nrics) < self.officer_slot

    # --- Dunder methods for comparison and representation ---
    def __eq__(self, other):
        """Projects are considered equal if their names are the same."""
        if not isinstance(other, Project):
            return NotImplemented
        return self.project_name == other.project_name

    def __hash__(self):
        """Hash based on the unique project name."""
        return hash(self.project_name)

    def __str__(self):
        """User-friendly string representation."""
        vis = "Visible" if self.visibility else "Hidden"
        open_dt = format_date(self.opening_date) if self.opening_date else "N/A"
        close_dt = format_date(self.closing_date) if self.closing_date else "N/A"
        return (f"Project(Name: {self.project_name}, Nhood: {self.neighborhood}, "
                f"2R: {self.num_units_2_room} units, 3R: {self.num_units_3_room} units, "
                f"Period: {open_dt} - {close_dt}, "
                f"Visibility: {vis})")