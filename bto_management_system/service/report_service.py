from typing import List, Dict, Optional
from .interfaces.ireport_service import IReportService
from .interfaces.iproject_service import IProjectService # Use interface
from repository.interfaces.iapplication_repository import IApplicationRepository
from repository.interfaces.iuser_repository import IUserRepository
from common.enums import ApplicationStatus, FlatType

class ReportService(IReportService):
    """Handles generation of reports."""
    def __init__(self, application_repository: IApplicationRepository,
                 project_service: IProjectService,
                 user_repository: IUserRepository):
        self._app_repo = application_repository
        self._project_service = project_service
        self._user_repo = user_repository

    def generate_booking_report_data(self, filter_project_name: Optional[str] = None,
                                     filter_flat_type_str: Optional[str] = None,
                                     filter_marital: Optional[str] = None) -> List[Dict]:
        """Generates data for the booking report based on filters."""
        report_data = []
        booked_apps = [app for app in self._app_repo.get_all() if app.status == ApplicationStatus.BOOKED]

        filter_flat_type: Optional[FlatType] = None
        if filter_flat_type_str:
            try: filter_flat_type = FlatType.from_value(filter_flat_type_str)
            except ValueError: pass # Ignore invalid filter

        filter_marital_lower = filter_marital.lower() if filter_marital else None

        for app in booked_apps:
            project = self._project_service.find_project_by_name(app.project_name)
            applicant = self._user_repo.find_user_by_nric(app.applicant_nric)

            if not project or not applicant:
                print(f"Warning: Skipping report entry for application {app.applicant_nric}-{app.project_name} due to missing project/applicant.")
                continue

            # Apply filters
            if filter_project_name and project.project_name.lower() != filter_project_name.lower(): continue
            if filter_flat_type and app.flat_type != filter_flat_type: continue
            if filter_marital_lower and applicant.marital_status.lower() != filter_marital_lower: continue

            report_data.append({
                "NRIC": app.applicant_nric,
                "Applicant Name": applicant.name,
                "Age": applicant.age,
                "Marital Status": applicant.marital_status,
                "Flat Type": app.flat_type.to_string(),
                "Project Name": project.project_name,
                "Neighborhood": project.neighborhood
            })

        # Sort report data
        report_data.sort(key=lambda x: (x["Project Name"], x["Applicant Name"]))
        return report_data