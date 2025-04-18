# views/project_view.py
from .base_view import BaseView
from models.project import Project
from models.roles import UserRole, FLAT_TYPE_2_ROOM, FLAT_TYPE_3_ROOM
from utils import helpers

class ProjectView(BaseView):
    """View specific to Project display and input."""

    def display_project_details(self, project: Project, user_role: UserRole, is_single_applicant: bool = False):
        """Displays detailed information about a project."""
        details = {
            "Neighborhood": project.neighborhood,
            "Manager NRIC": project.manager_nric,
            "Application Period": f"{helpers.format_date(project.opening_date)} to {helpers.format_date(project.closing_date)}",
            "Visibility": "ON" if project.visibility else "OFF",
            "Status": "Active for Applications" if project.is_currently_active_for_application() else "Inactive / Closed",
        }

        # Flat details
        units_2r, price_2r = project.get_flat_details(FLAT_TYPE_2_ROOM)
        units_3r, price_3r = project.get_flat_details(FLAT_TYPE_3_ROOM)
        details["2-Room Flats"] = f"{units_2r} units @ ${price_2r}"
        if not is_single_applicant:
             details["3-Room Flats"] = f"{units_3r} units @ ${price_3r}"
        else:
             # Singles can only apply for 2-Room, make 3-Room info less prominent or indicate ineligibility
             details["3-Room Flats"] = f"{units_3r} units @ ${price_3r} (Eligibility restrictions apply)"

        # Officer details (visible to staff)
        if user_role in [UserRole.HDB_OFFICER, UserRole.HDB_MANAGER]:
            details["Officer Slots"] = f"{len(project.officer_nrics)} / {project.officer_slot}"
            if project.officer_nrics:
                details["Assigned Officers (NRIC)"] = ", ".join(project.officer_nrics)
            else:
                 details["Assigned Officers (NRIC)"] = "None"

        self.display_dict(f"Project Details: {project.project_name}", details)

    def prompt_project_filters(self, current_filters: dict) -> dict:
        """Prompts user for project filtering criteria."""
        self.display_message(f"Current Filters: {current_filters or 'None'}", info=True)
        location = self.get_input("Filter by Neighborhood (leave blank to keep/remove)")
        flat_type = self.get_input("Filter by Flat Type (2 or 3, leave blank to keep/remove)")

        new_filters = current_filters.copy()

        # Update location filter
        if location is not None: # User provided input (even if empty)
            new_filters['location'] = location if location else None

        # Update flat type filter
        if flat_type is not None:
            if flat_type in ['2', '3']:
                new_filters['flat_type'] = flat_type
            elif flat_type == '': # Explicitly remove filter
                new_filters['flat_type'] = None
            else:
                self.display_message("Invalid flat type filter. Must be '2', '3', or blank. Keeping previous.", warning=True)

        # Remove keys with None values for cleaner filter dict
        return {k: v for k, v in new_filters.items() if v is not None}

    def select_project(self, projects: list[Project], action_verb: str = "view details for") -> Project | None:
        """Allows user to select a project from a list."""
        if not projects:
            self.display_message("No projects available for selection.", info=True)
            return None

        print(f"\n--- Select Project to {action_verb} ---")
        project_map = {} # Use dict for easy lookup by choice number
        for i, p in enumerate(projects):
            vis_status = "Visible" if p.visibility else "Hidden"
            app_status = "Active" if p.is_currently_active_for_application() else "Inactive/Closed"
            # Display minimal info for selection
            print(f"{i + 1}. {p.project_name} ({p.neighborhood}) - Status: {app_status}, View: {vis_status}")
            project_map[i + 1] = p
        print(" 0. Cancel")
        print("-------------------------------------")

        while True:
            choice_str = self.get_input(f"Enter the number of the project (1-{len(projects)}, or 0 to cancel)")
            if choice_str == '0':
                return None
            try:
                index = int(choice_str)
                if 1 <= index <= len(projects):
                     return project_map[index] # Return the selected Project object
                else:
                    self.display_message("Invalid selection number.", error=True)
            except ValueError:
                self.display_message("Invalid input. Please enter a number.", error=True)

    def prompt_create_project_details(self) -> dict | None:
        """Gathers details for creating a new project."""
        self.display_message("--- Create New Project ---", info=True)
        details = {}
        try:
            details['name'] = helpers.get_non_empty_input("Enter Project Name")
            details['neighborhood'] = helpers.get_non_empty_input("Enter Neighborhood")
            details['n2'] = helpers.get_valid_integer_input("Enter Number of 2-Room units", min_val=0)
            details['p2'] = helpers.get_valid_integer_input("Enter Selling Price for 2-Room", min_val=0)
            details['n3'] = helpers.get_valid_integer_input("Enter Number of 3-Room units", min_val=0)
            details['p3'] = helpers.get_valid_integer_input("Enter Selling Price for 3-Room", min_val=0)
            details['od'] = helpers.get_valid_date_input("Enter Application Opening Date")
            details['cd'] = helpers.get_valid_date_input("Enter Application Closing Date")
            # Ensure closing date is not before opening date
            if details['cd'] < details['od']:
                 self.display_message("Closing date cannot be before opening date.", error=True)
                 return None
            details['slot'] = helpers.get_valid_integer_input("Enter Max Officer Slots", min_val=0, max_val=10)
            return details
        except KeyboardInterrupt:
             print("\nProject creation cancelled.")
             return None
        except Exception as e:
             self.display_message(f"Error during input: {e}", error=True)
             return None

    def prompt_edit_project_details(self, project: Project) -> dict | None:
        """Gathers details for editing an existing project. Returns None if cancelled."""
        self.display_message(f"--- Editing Project: {project.project_name} ---", info=True)
        print("(Leave input blank to keep the current value)")
        updates = {}
        try:
            # String fields: allow empty input to keep original
            updates['name'] = self.get_input(f"New Project Name [{project.project_name}]") or project.project_name
            updates['neighborhood'] = self.get_input(f"New Neighborhood [{project.neighborhood}]") or project.neighborhood

            # Numeric fields: parse only if input is provided
            n2_str = self.get_input(f"New Number of 2-Room units [{project.num_units_2_room}]")
            updates['n2'] = int(n2_str) if n2_str.isdigit() else None
            p2_str = self.get_input(f"New Selling Price for 2-Room [{project.price_2_room}]")
            updates['p2'] = int(p2_str) if p2_str.isdigit() else None
            n3_str = self.get_input(f"New Number of 3-Room units [{project.num_units_3_room}]")
            updates['n3'] = int(n3_str) if n3_str.isdigit() else None
            p3_str = self.get_input(f"New Selling Price for 3-Room [{project.price_3_room}]")
            updates['p3'] = int(p3_str) if p3_str.isdigit() else None
            slot_str = self.get_input(f"New Max Officer Slots [{project.officer_slot}]")
            updates['officerSlot'] = int(slot_str) if slot_str.isdigit() else None

            # Date fields: parse only if input is provided
            od_str = self.get_input(f"New Opening Date ({helpers.DATE_FORMAT}) [{helpers.format_date(project.opening_date)}]")
            updates['openDate'] = helpers.parse_date(od_str) if od_str else None # Keep original if blank
            cd_str = self.get_input(f"New Closing Date ({helpers.DATE_FORMAT}) [{helpers.format_date(project.closing_date)}]")
            updates['closeDate'] = helpers.parse_date(cd_str) if cd_str else None

            # Clean up the updates dict: remove None values, keep explicitly set ones
            final_updates = {}
            if updates['name'] != project.project_name: final_updates['name'] = updates['name']
            if updates['neighborhood'] != project.neighborhood: final_updates['neighborhood'] = updates['neighborhood']
            if updates['n2'] is not None: final_updates['n2'] = updates['n2']
            if updates['p2'] is not None: final_updates['p2'] = updates['p2']
            if updates['n3'] is not None: final_updates['n3'] = updates['n3']
            if updates['p3'] is not None: final_updates['p3'] = updates['p3']
            if updates['officerSlot'] is not None: final_updates['officerSlot'] = updates['officerSlot']
            if updates['openDate'] is not None: final_updates['openDate'] = updates['openDate']
            if updates['closeDate'] is not None: final_updates['closeDate'] = updates['closeDate']

            # Basic validation: Ensure closing date is not before opening date if both are updated
            check_od = final_updates.get('openDate', project.opening_date)
            check_cd = final_updates.get('closeDate', project.closing_date)
            if check_od and check_cd and check_cd < check_od:
                 self.display_message("Closing date cannot be before opening date.", error=True)
                 return None # Abort edit

            return final_updates

        except KeyboardInterrupt:
             print("\nProject editing cancelled.")
             return None
        except Exception as e:
             self.display_message(f"Error during input: {e}", error=True)
             return None