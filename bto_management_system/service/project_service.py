from typing import List, Optional, Dict, Set
from datetime import date
from .interfaces.iproject_service import IProjectService
from repository.interfaces.iproject_repository import IProjectRepository
from repository.interfaces.iregistration_repository import IRegistrationRepository
from model.project import Project
from model.hdb_manager import HDBManager
from model.applicant import Applicant
from model.application import Application
from common.enums import UserRole, FlatType, RegistrationStatus
from common.exceptions import OperationError, IntegrityError, DataSaveError
from utils.input_util import InputUtil
from utils.date_util import DateUtil

class ProjectService(IProjectService):
    """Handles business logic related to projects."""
    def __init__(self, project_repository: IProjectRepository,
                 registration_repository: IRegistrationRepository):
        self._project_repo = project_repository
        self._reg_repo = registration_repository # Needed for officer overlap checks

    def find_project_by_name(self, name: str) -> Optional[Project]:
        return self._project_repo.find_by_name(name)

    def get_all_projects(self) -> List[Project]:
        return sorted(self._project_repo.get_all(), key=lambda p: p.project_name)

    def get_projects_by_manager(self, manager_nric: str) -> List[Project]:
        if not InputUtil.validate_nric(manager_nric): return []
        return sorted(
            [p for p in self.get_all_projects() if p.manager_nric == manager_nric],
            key=lambda p: p.project_name
        )

    def get_handled_project_names_for_officer(self, officer_nric: str) -> Set[str]:
        """Gets names of projects an officer is directly assigned to."""
        if not InputUtil.validate_nric(officer_nric): return set()
        return {p.project_name for p in self.get_all_projects() if officer_nric in p.officer_nrics}

    def get_viewable_projects_for_applicant(self, applicant: Applicant, current_application: Optional[Application] = None) -> List[Project]:
        """Gets projects viewable by an applicant based on rules."""
        viewable = []
        app_proj_name = current_application.project_name if current_application else None
        is_single = applicant.marital_status == "Single"
        is_married = applicant.marital_status == "Married"

        for project in self.get_all_projects():
            if project.project_name == app_proj_name: # Always show applied project
                viewable.append(project); continue
            if not project.is_currently_visible_and_active(): continue # Must be visible & active

            units2, _ = project.get_flat_details(FlatType.TWO_ROOM)
            units3, _ = project.get_flat_details(FlatType.THREE_ROOM)
            eligible = False
            if is_single and applicant.age >= 35 and units2 > 0: eligible = True
            elif is_married and applicant.age >= 21 and (units2 > 0 or units3 > 0): eligible = True

            if eligible: viewable.append(project)

        # Ensure uniqueness and sort
        unique_viewable = {p.project_name: p for p in viewable}
        return sorted(list(unique_viewable.values()), key=lambda p: p.project_name)

    def filter_projects(self, projects: List[Project], location: Optional[str] = None, flat_type_str: Optional[str] = None) -> List[Project]:
        """Filters a list of projects based on criteria."""
        filtered = list(projects)
        if location:
            filtered = [p for p in filtered if p.neighborhood.lower() == location.lower()]
        if flat_type_str:
            try:
                target_flat_type = FlatType.from_value(flat_type_str)
                filtered = [p for p in filtered if p.get_flat_details(target_flat_type)[0] > 0]
            except ValueError:
                print(f"Warning: Invalid flat type filter '{flat_type_str}'. Ignoring.")
        return filtered

    def _check_manager_project_overlap(self, manager_nric: str, od: date, cd: date, exclude_name: Optional[str] = None):
        """Checks if a manager has another project active during the given period."""
        for p in self.get_projects_by_manager(manager_nric):
            if exclude_name and p.project_name == exclude_name: continue
            if p.opening_date and p.closing_date:
                 if DateUtil.dates_overlap(od, cd, p.opening_date, p.closing_date):
                    raise OperationError(f"Manager handles overlapping project '{p.project_name}' ({DateUtil.format_date(p.opening_date)} - {DateUtil.format_date(p.closing_date)}).")

    def create_project(self, manager: HDBManager, name: str, neighborhood: str, n1: int, p1: int, n2: int, p2: int, od: date, cd: date, slot: int) -> Project:
        if self.find_project_by_name(name):
            raise OperationError(f"Project name '{name}' already exists.")
        self._check_manager_project_overlap(manager.nric, od, cd) # Check overlap

        try:
            new_project = Project(
                project_name=name, neighborhood=neighborhood, num_units1=n1, price1=p1,
                num_units2=n2, price2=p2, opening_date=od, closing_date=cd,
                manager_nric=manager.nric, officer_slot=slot, visibility=True
            )
            self._project_repo.add(new_project)
            # Defer saving to PersistenceManager or explicit call
            return new_project
        except ValueError as e: raise OperationError(f"Failed to create project: {e}")
        except IntegrityError as e: raise OperationError(f"Failed to add project: {e}")

    def edit_project(self, manager: HDBManager, project: Project, updates: Dict):
        if project.manager_nric != manager.nric:
            raise OperationError("You can only edit projects you manage.")

        original_name = project.project_name
        new_name = updates.get('project_name', original_name)
        if new_name != original_name and self.find_project_by_name(new_name):
            raise OperationError(f"Project name '{new_name}' already exists.")

        new_od = updates.get('opening_date', project.opening_date)
        new_cd = updates.get('closing_date', project.closing_date)
        if new_od != project.opening_date or new_cd != project.closing_date:
             self._check_manager_project_overlap(manager.nric, new_od, new_cd, exclude_name=original_name)

        try:
            # Apply updates using Project's method (includes validation)
            project.update_details(updates)

            # Handle repository update (delete old key, add new if name changed)
            if project.project_name != original_name:
                self._project_repo.delete(original_name) # Must delete before adding new key
                self._project_repo.add(project)
            else:
                self._project_repo.update(project)
            # Defer saving
        except ValueError as e: raise OperationError(f"Failed to update project: {e}")
        except IntegrityError as e: raise OperationError(f"Failed to update project in repository: {e}")

    def delete_project(self, manager: HDBManager, project: Project):
        if project.manager_nric != manager.nric:
            raise OperationError("You can only delete projects you manage.")
        try:
            self._project_repo.delete_by_name(project.project_name)
            # Defer saving
        except IntegrityError as e: raise OperationError(f"Failed to delete project: {e}")

    def toggle_project_visibility(self, manager: HDBManager, project: Project) -> str:
        if project.manager_nric != manager.nric:
            raise OperationError("You can only toggle visibility for projects you manage.")
        try:
            project.set_visibility(not project.visibility)
            self._project_repo.update(project)
            # Defer saving
            return "ON" if project.visibility else "OFF"
        except IntegrityError as e:
            project.set_visibility(not project.visibility) # Revert in-memory change
            raise OperationError(f"Failed to update project visibility: {e}")

    def add_officer_to_project(self, project: Project, officer_nric: str) -> bool:
        """Adds officer NRIC to project list. Assumes caller handles permissions."""
        try:
            # Project model handles validation (NRIC format, slots, uniqueness)
            if project.add_officer(officer_nric):
                self._project_repo.update(project) # Update repo state
                # Defer saving
                return True
            return False # Should not happen if add_officer raises OperationError on failure
        except (ValueError, OperationError) as e:
             raise OperationError(f"Cannot add officer: {e}")
        except IntegrityError as e:
             raise OperationError(f"Failed to update project after adding officer: {e}")

    def remove_officer_from_project(self, project: Project, officer_nric: str) -> bool:
        """Removes officer NRIC from project list. Assumes caller handles permissions."""
        try:
            if project.remove_officer(officer_nric):
                self._project_repo.update(project)
                # Defer saving
                return True
            return False # Officer not found on project
        except IntegrityError as e:
             raise OperationError(f"Failed to update project after removing officer: {e}")