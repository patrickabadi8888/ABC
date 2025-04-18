from typing import Dict, Any, Optional
from model.user import User
from common.enums import UserRole
from common.exceptions import DataLoadError, DataSaveError, IntegrityError, ConfigurationError, OperationError
from repository.storage.csv_storage_adapter import CsvStorageAdapter
from repository.applicant_repository import ApplicantRepository
from repository.officer_repository import OfficerRepository
from repository.manager_repository import ManagerRepository
from repository.user_repository_facade import UserRepositoryFacade
from repository.project_repository import ProjectRepository
from repository.application_repository import ApplicationRepository
from repository.registration_repository import RegistrationRepository
from repository.enquiry_repository import EnquiryRepository
from repository.persistence_manager import PersistenceManager
# Import Services (adjust path based on final structure)
from service.auth_service import AuthService
from service.project_service import ProjectService
from service.registration_service import RegistrationService
from service.application_service import ApplicationService
from service.enquiry_service import EnquiryService
from service.report_service import ReportService
# Import Views (adjust path)
from view.base_view import BaseView
from view.auth_view import AuthView
from view.project_view import ProjectView
from view.application_view import ApplicationView
from view.enquiry_view import EnquiryView
from view.officer_view import OfficerView
from view.manager_view import ManagerView
from view.report_view import ReportView
# Import Role Controllers
from .base_role_controller import BaseRoleController
from .applicant_controller import ApplicantController
from .officer_controller import OfficerController
from .manager_controller import ManagerController
from utils.input_util import InputUtil # For login retry prompt

class ApplicationController:
    """Main controller orchestrating the application lifecycle."""
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._views: Dict[str, Any] = {}
        self._repositories: Dict[str, Any] = {} # Store repositories if needed elsewhere
        self._persistence_manager: Optional[PersistenceManager] = None
        self._current_user: Optional[User] = None
        self._role_controller: Optional[BaseRoleController] = None

        try:
            self._initialize_dependencies()
            self._load_initial_data()
        except (DataLoadError, DataSaveError, IntegrityError, ConfigurationError) as e:
            # Use BaseView directly for initialization errors
            BaseView().display_message(f"CRITICAL ERROR during initialization: {e}. Cannot start.", error=True)
            exit(1)
        except Exception as e:
            BaseView().display_message(f"UNEXPECTED CRITICAL ERROR during initialization: {e}. Cannot start.", error=True)
            exit(1)

    def _initialize_dependencies(self):
        """Sets up repositories, services, views, and persistence manager."""
        # Storage Adapter
        storage_adapter = CsvStorageAdapter()

        # Repositories
        applicant_repo = ApplicantRepository(storage_adapter)
        officer_repo = OfficerRepository(storage_adapter)
        manager_repo = ManagerRepository(storage_adapter)
        user_repo_facade = UserRepositoryFacade(applicant_repo, officer_repo, manager_repo)
        project_repo = ProjectRepository(storage_adapter)
        app_repo = ApplicationRepository(storage_adapter)
        reg_repo = RegistrationRepository(storage_adapter)
        enq_repo = EnquiryRepository(storage_adapter)

        # Store repositories if needed by other layers (e.g., views needing user repo)
        self._repositories['applicant'] = applicant_repo
        self._repositories['officer'] = officer_repo
        self._repositories['manager'] = manager_repo
        self._repositories['user'] = user_repo_facade # Facade for general user access
        self._repositories['project'] = project_repo
        self._repositories['application'] = app_repo
        self._repositories['registration'] = reg_repo
        self._repositories['enquiry'] = enq_repo

        # Persistence Manager (collect all base repositories)
        all_repos = [applicant_repo, officer_repo, manager_repo, project_repo, app_repo, reg_repo, enq_repo]
        self._persistence_manager = PersistenceManager(all_repos)

        # Services (inject repository dependencies)
        self._services['auth'] = AuthService(user_repo_facade)
        self._services['project'] = ProjectService(project_repo, reg_repo) # Pass needed repos
        self._services['reg'] = RegistrationService(reg_repo, self._services['project'], app_repo)
        self._services['app'] = ApplicationService(app_repo, self._services['project'], self._services['reg'], user_repo_facade)
        self._services['enq'] = EnquiryService(enq_repo, self._services['project'], user_repo_facade, app_repo)
        self._services['report'] = ReportService(app_repo, self._services['project'], user_repo_facade)
        # Add user repo to services if actions need it directly (try to avoid)
        self._services['user'] = user_repo_facade

        # Views
        self._views['base'] = BaseView()
        self._views['auth'] = AuthView()
        self._views['project'] = ProjectView()
        self._views['app'] = ApplicationView()
        self._views['enq'] = EnquiryView()
        self._views['officer'] = OfficerView()
        self._views['manager'] = ManagerView()
        self._views['report'] = ReportView()

    def _load_initial_data(self):
        """Loads data using the PersistenceManager."""
        if self._persistence_manager:
            self._persistence_manager.load_all()
        else:
            raise ConfigurationError("Persistence Manager not initialized.")

    def run(self):
        """Main application loop."""
        base_view = self._views['base']
        while True:
            if not self._current_user:
                if not self._handle_login():
                    break # Exit if login fails and user quits
            else:
                if self._role_controller:
                    signal = self._role_controller.run_menu()
                    if signal == "LOGOUT": self._handle_logout()
                    elif signal == "EXIT": self._shutdown(); break

                    if self._persistence_manager:
                        try:
                            self._persistence_manager.save_all()
                        except DataSaveError as e:
                            base_view.display_message(f"ERROR during final data save:\n{e}", error=True)
                        except Exception as e:
                            base_view.display_message(f"Unexpected error during final data save: {e}", error=True)
                    else:
                        base_view.display_message("Warning: Persistence Manager not available for final save.", warning=True)
                    
                else:
                    base_view.display_message("Error: No role controller active. Logging out.", error=True)
                    self._handle_logout()

    def _handle_login(self) -> bool:
        """Handles the login process."""
        auth_service: AuthService = self._services['auth']
        auth_view: AuthView = self._views['auth']
        base_view: BaseView = self._views['base']

        base_view.display_message("Welcome to the BTO Management System")
        while True:
            try:
                nric, password = auth_view.prompt_login()
                user = auth_service.login(nric, password) # Service returns User object
                self._current_user = user
                role = user.get_role()
                base_view.display_message(f"Login successful. Welcome, {user.name} ({role.value})!", info=True)

                # Instantiate the correct controller
                if role == UserRole.HDB_MANAGER: self._role_controller = ManagerController(user, self._services, self._views)
                elif role == UserRole.HDB_OFFICER: self._role_controller = OfficerController(user, self._services, self._views)
                elif role == UserRole.APPLICANT: self._role_controller = ApplicantController(user, self._services, self._views)
                else: raise ConfigurationError(f"Unknown user role '{role}' encountered.")

                return True # Login successful

            except (OperationError, ConfigurationError) as e:
                base_view.display_message(str(e), error=True)
                if not InputUtil.get_yes_no_input("Login failed. Try again?"):
                    self._shutdown()
                    return False # User chose to quit
            except KeyboardInterrupt:
                 base_view.display_message("\nLogin cancelled by user.")
                 self._shutdown()
                 return False

    def _handle_logout(self):
        """Handles the logout process."""
        base_view = self._views['base']
        if self._current_user:
            base_view.display_message(f"Logging out user {self._current_user.name}.", info=True)
        self._current_user = None
        self._role_controller = None

    def _shutdown(self):
        """Handles application shutdown, including saving data."""
        base_view = self._views['base']
        base_view.display_message("Exiting BTO Management System...")

        base_view.display_message("Goodbye!")