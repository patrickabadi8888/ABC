from .base_view import BaseView
from model.registration import Registration
from model.application import Application
from model.project import Project
from model.user import User # For applicant/officer details
from common.enums import FlatType

class ManagerView(BaseView):
     """View specific to HDB Manager actions."""
     # Inherits display methods from BaseView.
     # Adds specific display formats for approval contexts.

     def display_officer_registration_for_approval(self, registration: Registration, officer: User, project: Project):
          """Displays registration details specifically in the context of approval/rejection."""
          print("\n--- Officer Registration for Review ---")
          details = {
              "Project": f"{project.project_name} ({project.neighborhood})",
              "Officer": f"{officer.name} ({officer.nric})",
              "Current Status": registration.status.value,
              "Project Officer Slots": f"{len(project.officer_nrics)} / {project.officer_slot}"
          }
          self.display_dict("Registration Details", details) # Use standard dict display
          print("---------------------------------------")

     def display_application_for_approval(self, application: Application, applicant: User, project: Project):
           """Displays application details specifically in the context of approval/rejection."""
           print("\n--- Application for Review ---")
           units, _ = project.get_flat_details(application.flat_type)
           details = {
               "Applicant": f"{applicant.name} ({applicant.nric})",
               "Project": project.project_name,
               "Flat Type": application.flat_type.to_string(),
               "Current Status": application.status.value,
               f"Units Remaining ({application.flat_type.to_string()})": units
           }
           if application.request_withdrawal:
                details["** Withdrawal Requested **"] = "Yes"
           self.display_dict("Application Details", details)
           print("-----------------------------")

     def display_withdrawal_request_for_approval(self, application: Application, applicant: User, project: Project):
           """Displays withdrawal request details specifically in the context of approval/rejection."""
           print("\n--- Withdrawal Request for Review ---")
           details = {
               "Applicant": f"{applicant.name} ({applicant.nric})",
               "Project": project.project_name,
               "Flat Type": application.flat_type.to_string(),
               "Current Status": application.status.value,
               "** Withdrawal Requested **": "YES"
           }
           self.display_dict("Withdrawal Request Details", details)
           print("------------------------------------")