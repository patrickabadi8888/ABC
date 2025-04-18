from typing import List, Optional, Dict, Any
from .base_view import BaseView
from model.project import Project
from common.enums import UserRole, FlatType
from utils.input_util import InputUtil
from utils.date_util import DateUtil

class ProjectView(BaseView):
    """View specific to displaying project information."""

    def display_project_summary(self, project: Project):
         """Displays a brief summary of a project for lists."""
         # Use the model's display method
         print(project.get_display_summary())

    def display_project_details(self, project: Project, requesting_user_role: UserRole, applicant_marital_status: Optional[str] = None):
        """Displays detailed information about a project, tailored by role."""
        details = {
            "Neighborhood": project.neighborhood,
            "Managed by NRIC": project.manager_nric,
            "Application Period": f"{DateUtil.format_date(project.opening_date)} to {DateUtil.format_date(project.closing_date)}",
            "Visibility": "ON" if project.visibility else "OFF",
            "Status": "Active & Visible" if project.is_currently_visible_and_active() else \
                      ("Visible but Inactive/Closed" if project.visibility else "Hidden")
        }

        units2, price2 = project.get_flat_details(FlatType.TWO_ROOM)
        units3, price3 = project.get_flat_details(FlatType.THREE_ROOM)
        details[f"{FlatType.TWO_ROOM.to_string()} Flats"] = f"{units2} units @ ${price2}"

        show_3_room = requesting_user_role in [UserRole.HDB_OFFICER, UserRole.HDB_MANAGER] or \
                      (requesting_user_role == UserRole.APPLICANT and applicant_marital_status == "Married")

        if show_3_room:
            details[f"{FlatType.THREE_ROOM.to_string()} Flats"] = f"{units3} units @ ${price3}"
        else:
             details[f"{FlatType.THREE_ROOM.to_string()} Flats"] = "(Not applicable/visible for single applicants)"

        if requesting_user_role in [UserRole.HDB_OFFICER, UserRole.HDB_MANAGER]:
            assigned = len(project.officer_nrics)
            details["Officer Slots"] = f"{assigned} / {project.officer_slot} (Available: {project.get_available_officer_slots()})"
            details["Assigned Officers (NRIC)"] = ", ".join(project.officer_nrics) if project.officer_nrics else "None"

        self.display_dict(f"Project Details: {project.project_name}", details)

    def prompt_project_filters(self, current_filters: Dict[str, Any]) -> Dict[str, Any]:
        """Prompts user for project filters."""
        self.display_message(f"Current Filters: {current_filters or 'None'}", info=True)
        location = self.get_input("Filter by Neighborhood (leave blank to keep/remove)")
        flat_type = self.get_input("Filter by Flat Type (2 or 3, leave blank to keep/remove)")

        new_filters = current_filters.copy()

        if location is not None:
            if location: new_filters['location'] = location
            elif 'location' in new_filters: del new_filters['location']

        if flat_type is not None:
            if flat_type in ['2', '3']: new_filters['flat_type_str'] = flat_type
            elif flat_type == '' and 'flat_type_str' in new_filters: del new_filters['flat_type_str']
            elif flat_type != '': self.display_message("Invalid flat type filter. Keeping previous.", warning=True)

        return new_filters

    def select_project(self, projects: List[Project], action_verb: str = "view details for") -> Optional[Project]:
        """Displays a list of projects and prompts for selection."""
        if not projects:
            self.display_message("No projects available for selection.", info=True)
            return None

        print(f"\n--- Select Project to {action_verb} ---")
        project_map = {} # Map 1-based index to project object
        for i, p in enumerate(projects):
            print(f"{i + 1}. ", end="")
            self.display_project_summary(p) # Use summary for selection list
            project_map[i + 1] = p
        print(" 0. Cancel")
        print("-------------------------------------")

        while True:
            # Use InputUtil for validated selection
            choice = InputUtil.get_valid_integer_input("Enter the number of the project (or 0 to cancel)", min_val=0, max_val=len(projects))
            if choice == 0: return None
            selected_project = project_map.get(choice)
            if selected_project: return selected_project
            # This else should not be reachable due to InputUtil validation range
            self.display_message("Invalid selection.", error=True)

    def prompt_create_project_details(self) -> Optional[Dict[str, Any]]:
        """Prompts for details needed to create a new project."""
        self.display_message("\n--- Create New Project ---", info=True)
        details = {}
        try:
            details['name'] = InputUtil.get_non_empty_input("Enter Project Name")
            details['neighborhood'] = InputUtil.get_non_empty_input("Enter Neighborhood")
            details['n1'] = InputUtil.get_valid_integer_input("Enter Number of 2-Room units", min_val=0)
            details['p1'] = InputUtil.get_valid_integer_input("Enter Selling Price for 2-Room", min_val=0)
            details['n2'] = InputUtil.get_valid_integer_input("Enter Number of 3-Room units", min_val=0)
            details['p2'] = InputUtil.get_valid_integer_input("Enter Selling Price for 3-Room", min_val=0)
            details['od'] = InputUtil.get_valid_date_input("Enter Application Opening Date")
            details['cd'] = InputUtil.get_valid_date_input("Enter Application Closing Date")
            if details['cd'] < details['od']:
                 self.display_message("Closing date cannot be before opening date.", error=True)
                 return None
            details['slot'] = InputUtil.get_valid_integer_input("Enter Max Officer Slots", min_val=0, max_val=10)
            return details
        except KeyboardInterrupt:
             self.display_message("\nProject creation cancelled.")
             return None

    def prompt_edit_project_details(self, project: Project) -> Optional[Dict[str, Any]]:
        """Prompts for details to edit, showing current values. Returns dict of *changed* values."""
        self.display_message(f"\n--- Editing Project: {project.project_name} ---", info=True)
        print("(Leave input blank to keep the current value)")
        updates = {}
        try:
            # Get potential new values, default to original if blank
            updates['project_name'] = self.get_input(f"New Project Name [{project.project_name}]") or project.project_name
            updates['neighborhood'] = self.get_input(f"New Neighborhood [{project.neighborhood}]") or project.neighborhood

            n1_str = self.get_input(f"New Number of 2-Room units [{project.get_flat_details(FlatType.TWO_ROOM)[0]}]")
            updates['num_units1'] = int(n1_str) if n1_str.isdigit() else project.get_flat_details(FlatType.TWO_ROOM)[0]

            p1_str = self.get_input(f"New Selling Price for 2-Room [{project.get_flat_details(FlatType.TWO_ROOM)[1]}]")
            updates['price1'] = int(p1_str) if p1_str.isdigit() else project.get_flat_details(FlatType.TWO_ROOM)[1]

            n2_str = self.get_input(f"New Number of 3-Room units [{project.get_flat_details(FlatType.THREE_ROOM)[0]}]")
            updates['num_units2'] = int(n2_str) if n2_str.isdigit() else project.get_flat_details(FlatType.THREE_ROOM)[0]

            p2_str = self.get_input(f"New Selling Price for 3-Room [{project.get_flat_details(FlatType.THREE_ROOM)[1]}]")
            updates['price2'] = int(p2_str) if p2_str.isdigit() else project.get_flat_details(FlatType.THREE_ROOM)[1]

            slot_str = self.get_input(f"New Max Officer Slots [{project.officer_slot}]")
            updates['officer_slot'] = int(slot_str) if slot_str.isdigit() else project.officer_slot

            od_str = self.get_input(f"New Opening Date ({DateUtil.DATE_FORMAT}) [{DateUtil.format_date(project.opening_date)}]")
            updates['opening_date'] = DateUtil.parse_date(od_str) if od_str else project.opening_date

            cd_str = self.get_input(f"New Closing Date ({DateUtil.DATE_FORMAT}) [{DateUtil.format_date(project.closing_date)}]")
            updates['closing_date'] = DateUtil.parse_date(cd_str) if cd_str else project.closing_date

            if updates['closing_date'] < updates['opening_date']:
                 self.display_message("Closing date cannot be before opening date.", error=True)
                 return None

            # Compare with original to find actual changes
            changed_updates = {}
            if updates['project_name'] != project.project_name: changed_updates['project_name'] = updates['project_name']
            if updates['neighborhood'] != project.neighborhood: changed_updates['neighborhood'] = updates['neighborhood']
            if updates['num_units1'] != project.get_flat_details(FlatType.TWO_ROOM)[0]: changed_updates['num_units1'] = updates['num_units1']
            if updates['price1'] != project.get_flat_details(FlatType.TWO_ROOM)[1]: changed_updates['price1'] = updates['price1']
            if updates['num_units2'] != project.get_flat_details(FlatType.THREE_ROOM)[0]: changed_updates['num_units2'] = updates['num_units2']
            if updates['price2'] != project.get_flat_details(FlatType.THREE_ROOM)[1]: changed_updates['price2'] = updates['price2']
            if updates['officer_slot'] != project.officer_slot: changed_updates['officer_slot'] = updates['officer_slot']
            if updates['opening_date'] != project.opening_date: changed_updates['opening_date'] = updates['opening_date']
            if updates['closing_date'] != project.closing_date: changed_updates['closing_date'] = updates['closing_date']

            return changed_updates # Return dict of changes, empty if none

        except KeyboardInterrupt:
             self.display_message("\nProject editing cancelled.")
             return None
        except ValueError:
             self.display_message("Invalid numeric input provided.", error=True)
             return None