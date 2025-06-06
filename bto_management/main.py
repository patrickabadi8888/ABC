# main.py
import sys
import os

# Add project root to Python path to allow imports like 'from controllers import ...'
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import necessary components after setting path
from controllers.app_controller import AppController
from repositories.user_repository import UserRepository
from repositories.project_repository import ProjectRepository
from repositories.application_repository import ApplicationRepository
from repositories.registration_repository import RegistrationRepository
from repositories.enquiry_repository import EnquiryRepository
from services.auth_service import AuthService
from services.project_service import ProjectService
from services.application_service import ApplicationService
from services.registration_service import RegistrationService
from services.enquiry_service import EnquiryService
from services.report_service import ReportService
from views.base_view import BaseView
from views.auth_view import AuthView
from views.project_view import ProjectView
from views.application_view import ApplicationView
from views.enquiry_view import EnquiryView
from views.officer_view import OfficerView
from views.report_view import ReportView
from utils.exceptions import DataLoadError, DataSaveError

def initialize_dependencies():
    """Initializes and wires up repositories, services, and views."""
    try:
        # 1. Initialize Repositories (these load data on init)
        user_repo = UserRepository()
        project_repo = ProjectRepository()
        app_repo = ApplicationRepository()
        reg_repo = RegistrationRepository()
        enq_repo = EnquiryRepository()

        # 2. Initialize Services (inject repositories)
        services = {}
        # Authentication depends only on user repo
        services['auth'] = AuthService(user_repo)
        # Project service needs its own repo (and registration repo eventually)
        services['project'] = ProjectService(project_repo) # Add reg_repo later
        # Application service needs app repo, project service (and reg service eventually)
        services['app'] = ApplicationService(app_repo, services['project']) # Add reg_service later
        # Registration service needs reg repo, project service, app repo
        services['reg'] = RegistrationService(reg_repo, services['project'], app_repo)
        # Enquiry service needs enquiry repo, project service, user repo, app service
        services['enq'] = EnquiryService(enq_repo, services['project'], user_repo, services['app'])
        # Report service needs app service, project service, user repo
        services['report'] = ReportService(services['app'], services['project'], user_repo)

        # Now, inject dependent services into others that need them
        # ProjectService needs RegistrationService (once implemented in ProjectService)
        # services['project'].registration_service = services['reg']
        # ApplicationService needs RegistrationService (once implemented)
        # services['app'].registration_service = services['reg']

        # 3. Initialize Views
        views = {
            'base': BaseView(),
            'auth': AuthView(),
            'project': ProjectView(),
            'app': ApplicationView(),
            'enq': EnquiryView(),
            'officer': OfficerView(),
            'manager': BaseView(), # May remain simple
            'report': ReportView()
        }

        return services, views

    except (DataLoadError, DataSaveError) as e:
        # Handle critical data loading/saving errors during setup
        print(f"\nCRITICAL ERROR DURING INITIALIZATION: {e}")
        print("Application cannot start. Please check data files and permissions.")
        sys.exit(1) # Exit if core data cannot be loaded/saved
    except Exception as e:
        # Catch any other unexpected errors during setup
        import traceback
        print("\n--- UNEXPECTED CRITICAL ERROR DURING INITIALIZATION ---")
        traceback.print_exc()
        print("-------------------------------------------------------")
        print(f"Details: {e}")
        print("Application cannot start.")
        sys.exit(1)


if __name__ == "__main__":
    # Initialize all components
    services, views = initialize_dependencies()

    # Create the main application controller
    app_controller = AppController(services, views)

    # Run the application
    app_controller.run()