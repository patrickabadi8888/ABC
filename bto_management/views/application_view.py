# views/application_view.py
from .base_view import BaseView
from models.application import Application
from models.project import Project
from models.user import Applicant
from models.roles import FLAT_TYPE_2_ROOM, FLAT_TYPE_3_ROOM
from services.auth_service import AuthService # Type hint for user lookup
from utils import helpers

class ApplicationView(BaseView):
    """View specific to Application display and input."""

    def display_application_status(self, application: Application, project: Project, applicant: Applicant):
        """Displays the status of a specific application."""
        details = {
            "Applicant": f"{applicant.name} ({applicant.nric})",
            "Project": f"{project.project_name} ({project.neighborhood})",
            "Flat Type Applied For": f"{application.flat_type}-Room",
            "Application Status": application.status
        }
        if application.request_withdrawal:
            details["Withdrawal Requested"] = "Yes (Pending Manager Action)"

        self.display_dict("BTO Application Status", details)

    def select_application(self, applications: list[Application], auth_service: AuthService,
                           action_verb: str = "view") -> Application | None:
        """Allows user to select an application from a list."""
        if not applications:
            self.display_message("No applications available for selection.", info=True)
            return None

        print(f"\n--- Select Application to {action_verb} ---")
        app_map = {}
        for i, app in enumerate(applications):
            # Look up applicant name for better display
            applicant = auth_service.user_repository.find_user_by_nric(app.applicant_nric)
            applicant_display = f"{applicant.name} ({app.applicant_nric})" if applicant else app.applicant_nric
            req_status = " (Withdrawal Req.)" if app.request_withdrawal else ""
            print(f"{i + 1}. Project: {app.project_name:<15} | Applicant: {applicant_display:<25} | "
                  f"Type: {app.flat_type}-Room | Status: {app.status}{req_status}")
            app_map[i + 1] = app
        print(" 0. Cancel")
        print("--------------------------------------------------")

        while True:
            choice_str = self.get_input(f"Enter the number of the application (1-{len(applications)}, or 0 to cancel)")
            if choice_str == '0':
                return None
            try:
                index = int(choice_str)
                if 1 <= index <= len(applications):
                    return app_map[index]
                else:
                    self.display_message("Invalid selection number.", error=True)
            except ValueError:
                self.display_message("Invalid input. Please enter a number.", error=True)

    def prompt_flat_type_selection(self, project: Project, applicant: Applicant) -> int | None:
        """Asks the applicant to select a flat type based on availability and eligibility."""
        available_types = []
        units_2r, _ = project.get_flat_details(FLAT_TYPE_2_ROOM)
        units_3r, _ = project.get_flat_details(FLAT_TYPE_3_ROOM)

        is_single = applicant.marital_status.lower() == "single"
        age = applicant.age

        # Determine eligibility and availability
        can_apply_2r = (is_single and age >= 35) or (not is_single and age >= 21)
        can_apply_3r = not is_single and age >= 21

        if units_2r > 0 and can_apply_2r:
            available_types.append(FLAT_TYPE_2_ROOM)
        if units_3r > 0 and can_apply_3r:
            available_types.append(FLAT_TYPE_3_ROOM)

        # Handle selection based on available types
        if not available_types:
            self.display_message(f"No suitable or available flat types for you in project '{project.project_name}'.", error=True)
            return None
        elif len(available_types) == 1:
            selected_type = available_types[0]
            self.display_message(f"Automatically selecting {selected_type}-Room flat (only eligible/available option).", info=True)
            return selected_type
        else:
            # Offer choice if multiple types are available
            options_str = ' or '.join(map(str, available_types))
            while True:
                choice_str = self.get_input(f"Select flat type ({options_str})")
                try:
                    choice = int(choice_str)
                    if choice in available_types:
                        return choice
                    else:
                        self.display_message(f"Invalid choice. Please enter one of: {options_str}", error=True)
                except ValueError:
                    self.display_message("Invalid input. Please enter a number.", error=True)