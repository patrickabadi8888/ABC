# repositories/project_repository.py
from .base_repository import BaseRepository
from models.project import Project
from utils.helpers import PROJECT_CSV, parse_date, format_date, is_valid_int

class ProjectRepository(BaseRepository):
    """Manages persistence for Project data."""
    def __init__(self):
        headers = ['Project Name', 'Neighborhood', 'Type 1', 'Number of units for Type 1', 'Selling price for Type 1', 'Type 2', 'Number of units for Type 2', 'Selling price for Type 2', 'Application opening date', 'Application closing date', 'Manager', 'Officer Slot', 'Officer', 'Visibility']
        super().__init__(PROJECT_CSV, Project, headers)

    def _get_key(self, item: Project):
        return item.project_name

    def _create_instance(self, row_dict: dict) -> Project:
        # Extract and convert data with error checking
        try:
            opening_date = parse_date(row_dict.get('Application opening date'))
            closing_date = parse_date(row_dict.get('Application closing date'))

            # Handle potentially missing or invalid numeric fields gracefully
            num_units_2r = int(row_dict.get('Number of units for 2-Room', 0)) if is_valid_int(row_dict.get('Number of units for 2-Room')) else 0
            price_2r = int(row_dict.get('Selling price for 2-Room', 0)) if is_valid_int(row_dict.get('Selling price for 2-Room')) else 0
            num_units_3r = int(row_dict.get('Number of units for 3-Room', 0)) if is_valid_int(row_dict.get('Number of units for 3-Room')) else 0
            price_3r = int(row_dict.get('Selling price for 3-Room', 0)) if is_valid_int(row_dict.get('Selling price for 3-Room')) else 0
            officer_slot = int(row_dict.get('Officer Slot', 0)) if is_valid_int(row_dict.get('Officer Slot')) else 0

            # Officer NRICs are stored comma-separated in the 'Officer' column
            officer_nrics_str = row_dict.get('Officer', '')
            officer_nrics = [nric.strip() for nric in officer_nrics_str.split(',') if nric.strip()] if officer_nrics_str else []

            visibility_str = row_dict.get('Visibility', 'True') # Default to True if missing
            visibility = visibility_str.strip().lower() == 'true'

            return Project(
                project_name=row_dict.get('Project Name', 'Unnamed Project'),
                neighborhood=row_dict.get('Neighborhood', 'Unknown'),
                num_units_2_room=num_units_2r,
                price_2_room=price_2r,
                num_units_3_room=num_units_3r,
                price_3_room=price_3r,
                opening_date=opening_date,
                closing_date=closing_date,
                manager_nric=row_dict.get('Manager', ''), # Should have a manager NRIC
                officer_slot=officer_slot,
                officer_nrics=officer_nrics,
                visibility=visibility
            )
        except (ValueError, TypeError) as e:
             # Catch errors during instance creation from row data
             raise ValueError(f"Error creating Project instance from row: {row_dict}. Details: {e}")


    def _get_row_data(self, item: Project) -> list:
        # Convert Project object back to list of strings for CSV
        return [
            item.project_name,
            item.neighborhood,
            str(item.num_units_2_room),
            str(item.price_2_room),
            str(item.num_units_3_room),
            str(item.price_3_room),
            format_date(item.opening_date),
            format_date(item.closing_date),
            item.manager_nric,
            str(item.officer_slot),
            ','.join(item.officer_nrics), # Join officer NRICs back into string
            str(item.visibility) # Convert boolean back to string 'True'/'False'
        ]

    def find_by_name(self, name: str) -> Project | None:
        """Finds a project by its unique name."""
        return self.find_by_key(name)

    def delete_by_name(self, name: str):
        """Deletes a project by its name."""
        self.delete(name)