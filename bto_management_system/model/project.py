from datetime import date
from utils.input_util import InputUtil
from utils.date_util import DateUtil
from common.enums import FlatType
from common.exceptions import DataLoadError, OperationError

class Project:
    """Represents a BTO project."""
    _HEADERS = [ # Define expected headers for CSV consistency
        'Project Name', 'Neighborhood', 'Type 1', 'Number of units for Type 1',
        'Selling price for Type 1', 'Type 2', 'Number of units for Type 2',
        'Selling price for Type 2', 'Application opening date',
        'Application closing date', 'Manager', 'Officer Slot', 'Officer', 'Visibility'
    ]

    def __init__(self, project_name: str, neighborhood: str,
                 num_units1: int, price1: int, num_units2: int, price2: int,
                 opening_date: date, closing_date: date, manager_nric: str,
                 officer_slot: int, officer_nrics: list[str] | None = None, visibility: bool = True):

        if not project_name: raise ValueError("Project Name cannot be empty")
        if not neighborhood: raise ValueError("Neighborhood cannot be empty")
        if not manager_nric or not InputUtil.validate_nric(manager_nric):
             raise ValueError(f"Invalid Manager NRIC: {manager_nric}")
        if not isinstance(opening_date, date) or not isinstance(closing_date, date):
            raise ValueError("Opening and Closing dates must be valid date objects.")
        if closing_date < opening_date:
            raise ValueError("Closing date cannot be before opening date.")
        if not (0 <= int(officer_slot) <= 10):
             raise ValueError("Officer slots must be between 0 and 10.")
        if any(int(v) < 0 for v in [num_units1, price1, num_units2, price2]):
            raise ValueError("Numeric project values (units, price) cannot be negative.")

        self._project_name = project_name
        self._neighborhood = neighborhood
        self._type1 = FlatType.TWO_ROOM
        self._num_units1 = int(num_units1)
        self._price1 = int(price1)
        self._type2 = FlatType.THREE_ROOM
        self._num_units2 = int(num_units2)
        self._price2 = int(price2)
        self._opening_date = opening_date
        self._closing_date = closing_date
        self._manager_nric = manager_nric
        self._officer_slot = int(officer_slot)
        self._officer_nrics = list(officer_nrics) if officer_nrics is not None else []
        self._visibility = bool(visibility)

        if len(self._officer_nrics) > self._officer_slot:
             raise ValueError("Number of assigned officers exceeds available slots.")

    # --- Getters ---
    @property
    def project_name(self): return self._project_name
    @property
    def neighborhood(self): return self._neighborhood
    @property
    def opening_date(self): return self._opening_date
    @property
    def closing_date(self): return self._closing_date
    @property
    def manager_nric(self): return self._manager_nric
    @property
    def officer_slot(self): return self._officer_slot
    @property
    def visibility(self): return self._visibility
    @property
    def officer_nrics(self): return list(self._officer_nrics) # Return copy

    # --- Calculated Properties / State Checks ---
    def is_active_period(self, check_date: date | None = None) -> bool:
        if check_date is None: check_date = date.today()
        return self._opening_date <= check_date <= self._closing_date

    def is_currently_visible_and_active(self) -> bool:
        return self._visibility and self.is_active_period()

    def get_flat_details(self, flat_type: FlatType) -> tuple[int, int]:
        if flat_type == FlatType.TWO_ROOM: return self._num_units1, self._price1
        if flat_type == FlatType.THREE_ROOM: return self._num_units2, self._price2
        raise ValueError(f"Invalid flat type requested: {flat_type}")

    def get_available_officer_slots(self) -> int:
        return self._officer_slot - len(self._officer_nrics)

    def can_add_officer(self) -> bool:
        return self.get_available_officer_slots() > 0

    # --- State Modifiers ---
    def decrease_unit_count(self, flat_type: FlatType) -> bool:
        if flat_type == FlatType.TWO_ROOM and self._num_units1 > 0:
            self._num_units1 -= 1; return True
        if flat_type == FlatType.THREE_ROOM and self._num_units2 > 0:
            self._num_units2 -= 1; return True
        return False # Type invalid or no units left

    def increase_unit_count(self, flat_type: FlatType) -> bool:
        if flat_type == FlatType.TWO_ROOM: self._num_units1 += 1; return True
        if flat_type == FlatType.THREE_ROOM: self._num_units2 += 1; return True
        return False # Invalid type

    def add_officer(self, officer_nric: str) -> bool:
        if not InputUtil.validate_nric(officer_nric):
             raise ValueError("Invalid NRIC format for officer.")
        if officer_nric not in self._officer_nrics:
            if self.can_add_officer():
                self._officer_nrics.append(officer_nric); return True
            else:
                raise OperationError("No available officer slots.")
        return True # Already present is considered success

    def remove_officer(self, officer_nric: str) -> bool:
        if officer_nric in self._officer_nrics:
            self._officer_nrics.remove(officer_nric); return True
        return False # Not found

    def set_visibility(self, is_visible: bool):
        self._visibility = bool(is_visible)

    def update_details(self, updates: dict):
        """Updates project details from a dictionary. Performs validation."""
        # Basic validation before applying changes
        new_name = updates.get('project_name', self._project_name)
        new_hood = updates.get('neighborhood', self._neighborhood)
        n1 = int(updates.get('num_units1', self._num_units1))
        p1 = int(updates.get('price1', self._price1))
        n2 = int(updates.get('num_units2', self._num_units2))
        p2 = int(updates.get('price2', self._price2))
        slot = int(updates.get('officer_slot', self._officer_slot))
        new_od = updates.get('opening_date', self._opening_date)
        new_cd = updates.get('closing_date', self._closing_date)

        if not new_name: raise ValueError("Project Name cannot be empty")
        if not new_hood: raise ValueError("Neighborhood cannot be empty")
        if any(v < 0 for v in [n1, p1, n2, p2, slot]): raise ValueError("Numeric values cannot be negative.")
        if not (0 <= slot <= 10): raise ValueError("Officer slots must be between 0 and 10.")
        if slot < len(self._officer_nrics): raise ValueError(f"Cannot reduce slots below current assigned officers ({len(self._officer_nrics)}).")
        if not isinstance(new_od, date) or not isinstance(new_cd, date): raise ValueError("Dates must be valid date objects.")
        if new_cd < new_od: raise ValueError("Closing date cannot be before opening date.")

        # Apply validated changes
        self._project_name = new_name
        self._neighborhood = new_hood
        self._num_units1 = n1
        self._price1 = p1
        self._num_units2 = n2
        self._price2 = p2
        self._officer_slot = slot
        self._opening_date = new_od
        self._closing_date = new_cd
        # Manager NRIC, visibility, officer list are typically handled by specific methods

    def to_csv_dict(self) -> dict:
        """Converts project data to a dictionary suitable for CSV writing."""
        return {
            'Project Name': self._project_name,
            'Neighborhood': self._neighborhood,
            'Type 1': self._type1.to_string(),
            'Number of units for Type 1': self._num_units1,
            'Selling price for Type 1': self._price1,
            'Type 2': self._type2.to_string(),
            'Number of units for Type 2': self._num_units2,
            'Selling price for Type 2': self._price2,
            'Application opening date': DateUtil.format_date(self._opening_date),
            'Application closing date': DateUtil.format_date(self._closing_date),
            'Manager': self._manager_nric,
            'Officer Slot': self._officer_slot,
            'Officer': ','.join(self._officer_nrics),
            'Visibility': str(self._visibility)
        }

    @classmethod
    def from_csv_dict(cls, row_dict: dict) -> 'Project':
        """Creates a Project instance from a CSV dictionary."""
        try:
            officer_nrics = [nric.strip() for nric in row_dict.get('Officer', '').split(',') if nric.strip()]
            visibility = row_dict.get('Visibility', 'True').lower() == 'true'
            opening_date = DateUtil.parse_date(row_dict['Application opening date'])
            closing_date = DateUtil.parse_date(row_dict['Application closing date'])
            if opening_date is None or closing_date is None:
                 raise ValueError("Invalid date format in CSV row")

            return cls(
                project_name=row_dict['Project Name'],
                neighborhood=row_dict['Neighborhood'],
                num_units1=int(row_dict['Number of units for Type 1']),
                price1=int(row_dict['Selling price for Type 1']),
                num_units2=int(row_dict['Number of units for Type 2']),
                price2=int(row_dict['Selling price for Type 2']),
                opening_date=opening_date,
                closing_date=closing_date,
                manager_nric=row_dict['Manager'],
                officer_slot=int(row_dict['Officer Slot']),
                officer_nrics=officer_nrics,
                visibility=visibility
            )
        except (KeyError, ValueError, TypeError) as e:
            raise DataLoadError(f"Error creating Project from CSV row: {row_dict}. Error: {e}")

    def __eq__(self, other):
        if not isinstance(other, Project): return NotImplemented
        return self._project_name == other._project_name

    def __hash__(self):
        return hash(self._project_name)

    def get_display_summary(self) -> str:
        vis = "Visible" if self._visibility else "Hidden"
        act = "Active" if self.is_currently_visible_and_active() else "Inactive/Closed"
        return f"{self._project_name} ({self._neighborhood}) - Status: {act}, View: {vis}"