from typing import List, Optional
from .base_view import BaseView
from model.application import Application
from model.project import Project
from model.user import User # For applicant details
from model.applicant import Applicant # Specifically for type hint
from common.enums import FlatType
from repository.interfaces.iuser_repository import IUserRepository # For lookup in select
from utils.input_util import InputUtil

class ApplicationView(BaseView):
    """View specific to displaying application information."""

    def display_application_summary(self, application: Application, applicant_name: str):
         """Displays a brief summary of an application for lists."""
         # Use model's display method
         print(application.get_display_summary(applicant_name))

    def display_application_details(self, application: Application, project: Project, applicant: User):
        """Displays detailed status of a specific application."""
        details = {
            "Applicant": f"{applicant.name} ({applicant.nric})",
            "Age": applicant.age,
            "Marital Status": applicant.marital_status,
            "Project": f"{project.project_name} ({project.neighborhood})",
            "Flat Type Applied For": application.flat_type.to_string(),
            "Application Status": application.status.value
        }
        if application.request_withdrawal:
            details["Withdrawal Requested"] = "Yes (Pending Manager Action)"

        self.display_dict("BTO Application Status", details)

    def select_application(self, applications: List[Application], user_repo: IUserRepository, action_verb: str = "view") -> Optional[Application]:
        """Displays a list of applications and prompts for selection."""
        if not applications:
            self.display_message("No applications available for selection.", info=True)
            return None

        print(f"\n--- Select Application to {action_verb} ---")
        app_map = {} # Map 1-based index to application object
        for i, app in enumerate(applications):
            applicant = user_repo.find_user_by_nric(app.applicant_nric)
            applicant_name = applicant.name if applicant else "Unknown Applicant"
            print(f"{i + 1}. ", end="")
            self.display_application_summary(app, applicant_name) # Use summary
            app_map[i + 1] = app
        print(" 0. Cancel")
        print("------------------------------------")

        while True:
            choice = InputUtil.get_valid_integer_input("Enter the number of the application (or 0 to cancel)", min_val=0, max_val=len(applications))
            if choice == 0: return None
            selected_app = app_map.get(choice)
            if selected_app: return selected_app
            self.display_message("Invalid selection.", error=True)

    def prompt_flat_type_selection(self, project: Project, applicant: Applicant) -> Optional[FlatType]:
        """Prompts the applicant to select a flat type based on eligibility and availability."""
        available_types = []
        is_single = applicant.marital_status == "Single"
        is_married = applicant.marital_status == "Married"

        units2, _ = project.get_flat_details(FlatType.TWO_ROOM)
        units3, _ = project.get_flat_details(FlatType.THREE_ROOM)

        if units2 > 0 and ((is_single and applicant.age >= 35) or (is_married and applicant.age >= 21)):
            available_types.append(FlatType.TWO_ROOM)
        if units3 > 0 and (is_married and applicant.age >= 21):
            available_types.append(FlatType.THREE_ROOM)

        if not available_types:
            self.display_message("No suitable or available flat types for you in this project.", error=True)
            return None
        elif len(available_types) == 1:
            selected_type = available_types[0]
            self.display_message(f"Automatically selecting {selected_type.to_string()} flat (only option).", info=True)
            return selected_type
        else:
            options_str = ' or '.join(str(ft.value) for ft in available_types)
            while True:
                choice_str = self.get_input(f"Select flat type ({options_str})")
                try:
                    choice_enum = FlatType.from_value(choice_str) # Use enum helper
                    if choice_enum in available_types:
                        return choice_enum
                    else:
                        self.display_message(f"Invalid choice. Please enter one of: {options_str}", error=True)
                except (ValueError, TypeError):
                    self.display_message("Invalid input. Please enter a number (2 or 3).", error=True)