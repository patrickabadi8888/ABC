# services/report_service.py
from services.application_service import ApplicationService
from services.project_service import ProjectService
from repositories.user_repository import UserRepository
from models.roles import ApplicationStatus
from utils.exceptions import OperationError

class ReportService:
    """Handles generation of reports."""
    def __init__(self, application_service: ApplicationService,
                 project_service: ProjectService,
                 user_repository: UserRepository):
        self.application_service = application_service
        self.project_service = project_service
        self.user_repository = user_repository

    def generate_booking_report_data(self, filter_project_name: str | None = None,
                                     filter_flat_type_str: str | None = None,
                                     filter_marital: str | None = None) -> list[dict]:
        """Generates data for the booking report based on filters."""
        report_data = []
        # Get only applications with BOOKED status
        all_apps = self.application_service.get_all_applications()
        booked_apps = [app for app in all_apps if app.status == ApplicationStatus.BOOKED.value]

        # Prepare filters
        filter_flat_type = None
        if filter_flat_type_str:
            try:
                filter_flat_type = int(filter_flat_type_str)
                if filter_flat_type not in [2, 3]: filter_flat_type = None # Ignore invalid int
            except ValueError:
                pass # Ignore non-int filter

        filter_marital_lower = filter_marital.strip().lower() if filter_marital else None

        # Process booked applications
        for app in booked_apps:
            # Retrieve related project and applicant data
            project = self.project_service.find_project_by_name(app.project_name)
            if not project:
                print(f"Warning: Project '{app.project_name}' for booked application not found. Skipping record.")
                continue

            applicant = self.user_repository.find_user_by_nric(app.applicant_nric)
            if not applicant:
                print(f"Warning: Applicant '{app.applicant_nric}' for booked application not found. Skipping record.")
                continue

            # Apply filters
            if filter_project_name and project.project_name.lower() != filter_project_name.lower():
                continue
            if filter_flat_type and app.flat_type != filter_flat_type:
                continue
            if filter_marital_lower and applicant.marital_status.lower() != filter_marital_lower:
                continue

            # Add data to report list
            report_data.append({
                "NRIC": app.applicant_nric,
                "Applicant Name": applicant.name,
                "Age": applicant.age,
                "Marital Status": applicant.marital_status,
                "Flat Type": f"{app.flat_type}-Room",
                "Project Name": project.project_name,
                "Neighborhood": project.neighborhood
            })

        # Sort the report data (e.g., by project name, then applicant NRIC)
        report_data.sort(key=lambda x: (x["Project Name"], x["NRIC"]))

        return report_data