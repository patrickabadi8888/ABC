# services/project_service.py
from datetime import date
from repositories.project_repository import ProjectRepository
# Need RegistrationRepository later for checks
# from repositories.registration_repository import RegistrationRepository
from models.project import Project
from models.user import HDBManager, Applicant
from models.roles import UserRole, FLAT_TYPE_2_ROOM, FLAT_TYPE_3_ROOM
from utils.exceptions import OperationError, IntegrityError, AuthorizationError
from utils.helpers import dates_overlap

class ProjectService:
    """Handles business logic related to BTO projects."""
    def __init__(self, project_repository: ProjectRepository):
             # registration_repository: RegistrationRepository): # Add later
        self.project_repository = project_repository
        # self.registration_repository = registration_repository # Add later

    def find_project_by_name(self, name: str) -> Project | None:
        """Finds a project by its name."""
        return self.project_repository.find_by_name(name)

    def get_all_projects(self) -> list[Project]:
        """Gets all projects, sorted alphabetically by name."""
        return sorted(self.project_repository.get_all(), key=lambda p: p.project_name)

    def get_projects_by_manager(self, manager_nric: str) -> list[Project]:
        """Gets projects managed by a specific manager, sorted."""
        return sorted(
            [p for p in self.get_all_projects() if p.manager_nric == manager_nric],
            key=lambda p: p.project_name
        )

    def get_handled_project_names_for_officer(self, officer_nric: str) -> set[str]:
        """Gets names of projects an officer is assigned to (directly on project)."""
        # NOTE: This currently only checks the Project.officer_nrics list.
        # The full logic should also consider approved Registrations via RegistrationService.
        handled_project_names = set()
        for p in self.get_all_projects():
            if officer_nric in p.officer_nrics:
                handled_project_names.add(p.project_name)
        # TODO: Integrate with RegistrationService to get approved projects too.
        # approved_regs = self.registration_service.get_approved_registrations_for_officer(officer_nric)
        # handled_project_names.update(reg.project_name for reg in approved_regs)
        return handled_project_names

    def get_viewable_projects_for_applicant(self, applicant: Applicant,
                                            current_application=None) -> list[Project]: # Pass Application object if needed
        """
        Gets projects viewable by an applicant based on role, status, visibility,
        eligibility, and whether they applied already.
        """
        viewable = []
        applicant_applied_project_name = current_application.project_name if current_application else None
        is_single = applicant.marital_status.lower() == "single" # Be explicit

        for project in self.get_all_projects():
            is_project_applied_for = project.project_name == applicant_applied_project_name

            # 1. Always show the project the applicant applied for, regardless of visibility/dates
            if is_project_applied_for:
                viewable.append(project)
                continue # Don't apply other filters to the applied project

            # 2. For other projects, check visibility and application period
            if not project.is_currently_active_for_application():
                continue

            # 3. Check basic flat availability based on marital status (simplified eligibility)
            units_2r, _ = project.get_flat_details(FLAT_TYPE_2_ROOM)
            units_3r, _ = project.get_flat_details(FLAT_TYPE_3_ROOM)

            if is_single:
                # Single can only view if 2-Room is available
                if units_2r <= 0:
                    continue
            else: # Married
                # Married can view if either 2-Room or 3-Room is available
                if units_2r <= 0 and units_3r <= 0:
                    continue

            # If all checks pass, the project is viewable
            viewable.append(project)

        # Return unique projects sorted by name
        # Using dict to remove duplicates if added multiple times (applied vs. general view)
        return sorted(list({p.project_name: p for p in viewable}.values()), key=lambda p: p.project_name)


    def filter_projects(self, projects: list[Project], location: str | None = None,
                        flat_type: str | None = None) -> list[Project]:
        """Filters a list of projects based on criteria."""
        filtered = list(projects) # Start with a copy
        if location:
            filtered = [p for p in filtered if p.neighborhood.lower() == location.lower()]
        if flat_type:
            try:
                flat_type_room = int(flat_type)
                if flat_type_room == FLAT_TYPE_2_ROOM:
                    # Show project if *any* 2-room units are available (doesn't filter out fully booked)
                    filtered = [p for p in filtered if p.num_units_2_room >= 0] # Or > 0 if must have available
                elif flat_type_room == FLAT_TYPE_3_ROOM:
                    filtered = [p for p in filtered if p.num_units_3_room >= 0] # Or > 0
                else:
                     print(f"Warning: Invalid flat type filter '{flat_type}'. Ignoring.")
            except ValueError:
                print(f"Warning: Invalid flat type filter '{flat_type}'. Ignoring.")
                pass # Ignore non-integer flat type filter
        return filtered

    def _check_manager_project_overlap(self, manager_nric: str, new_opening_date: date,
                                       new_closing_date: date, project_to_exclude: Project | None = None):
        """Finds if a manager handles another project overlapping the given dates."""
        for existing_project in self.get_projects_by_manager(manager_nric):
            if project_to_exclude and existing_project.project_name == project_to_exclude.project_name:
                continue # Don't compare a project against itself during edit

            # Check only against projects that are *currently* active or *will be* active
            # during their defined periods. The definition of "active" is within its dates.
            if existing_project.opening_date and existing_project.closing_date:
                 if dates_overlap(new_opening_date, new_closing_date,
                                  existing_project.opening_date, existing_project.closing_date):
                    return existing_project # Found an overlapping project

        return None # No overlap found

    def create_project(self, manager: HDBManager, name: str, neighborhood: str,
                     n2: int, p2: int, n3: int, p3: int, # Use specific names for clarity
                     od: date, cd: date, slot: int) -> Project:
        """Creates a new BTO project."""
        if self.find_project_by_name(name):
            raise OperationError(f"Project name '{name}' already exists.")
        if not (isinstance(od, date) and isinstance(cd, date) and cd >= od):
            raise OperationError("Invalid application dates (must be Date objects, close >= open).")
        if not (0 <= slot <= 10):
            raise OperationError("Officer slots must be between 0 and 10.")
        if any(v < 0 for v in [n2, p2, n3, p3]): # Use specific var names
            raise OperationError("Unit counts and prices cannot be negative.")

        # Check for manager overlap BEFORE creating
        conflicting_project = self._check_manager_project_overlap(manager.nric, od, cd)
        if conflicting_project:
            raise OperationError(f"Manager '{manager.nric}' already handles an active project "
                                 f"('{conflicting_project.project_name}') overlapping with the period "
                                 f"{od.strftime('%Y-%m-%d')} to {cd.strftime('%Y-%m-%d')}.")

        new_project = Project(
            project_name=name, neighborhood=neighborhood,
            num_units_2_room=n2, price_2_room=p2, # Use specific var names
            num_units_3_room=n3, price_3_room=p3,
            opening_date=od, closing_date=cd,
            manager_nric=manager.nric, officer_slot=slot,
            officer_nrics=[], visibility=True # Default visibility to ON
        )
        try:
            self.project_repository.add(new_project)
            print(f"Project '{name}' created successfully.")
            return new_project
        except IntegrityError as e:
             # Should be caught by find_project_by_name, but handle defensively
             raise OperationError(f"Failed to create project '{name}': {e}")
        except Exception as e:
            raise OperationError(f"An unexpected error occurred creating project '{name}': {e}")

    def edit_project(self, manager: HDBManager, project_to_edit: Project, updates: dict):
        """Edits an existing project. Requires manager authorization."""
        if project_to_edit.manager_nric != manager.nric:
            raise AuthorizationError("You can only edit projects you manage.")

        original_name = project_to_edit.project_name
        original_od = project_to_edit.opening_date
        original_cd = project_to_edit.closing_date

        # Apply updates safely
        new_name = updates.get('name', original_name)
        if new_name != original_name and self.find_project_by_name(new_name):
            raise OperationError(f"Cannot rename project: name '{new_name}' already exists.")

        new_od = updates.get('openDate', original_od)
        new_cd = updates.get('closeDate', original_cd)
        if not (isinstance(new_od, date) and isinstance(new_cd, date) and new_cd >= new_od):
            raise OperationError("Invalid application dates in update (must be Date objects, close >= open).")

        # Check for overlap *if dates changed*
        if new_od != original_od or new_cd != original_cd:
             conflicting_project = self._check_manager_project_overlap(manager.nric, new_od, new_cd, project_to_exclude=project_to_edit)
             if conflicting_project:
                 raise OperationError(f"Edited dates overlap with another active project ('{conflicting_project.project_name}') you manage.")

        # Validate numeric values if provided
        n2 = updates.get('n2')
        p2 = updates.get('p2')
        n3 = updates.get('n3')
        p3 = updates.get('p3')
        slot = updates.get('officerSlot')

        if any(v is not None and (not isinstance(v, int) or v < 0) for v in [n2, p2, n3, p3]):
             raise OperationError("Unit counts and prices must be non-negative integers.")
        if slot is not None and (not isinstance(slot, int) or not (0 <= slot <= 10)):
            raise OperationError("Officer slots must be an integer between 0 and 10.")
        if slot is not None and slot < len(project_to_edit.officer_nrics):
            raise OperationError(f"Cannot reduce slots below current number of assigned officers ({len(project_to_edit.officer_nrics)}).")

        # Update the project object
        project_to_edit.project_name = new_name
        project_to_edit.neighborhood = updates.get('neighborhood', project_to_edit.neighborhood)
        project_to_edit.num_units_2_room = n2 if n2 is not None else project_to_edit.num_units_2_room
        project_to_edit.price_2_room = p2 if p2 is not None else project_to_edit.price_2_room
        project_to_edit.num_units_3_room = n3 if n3 is not None else project_to_edit.num_units_3_room
        project_to_edit.price_3_room = p3 if p3 is not None else project_to_edit.price_3_room
        project_to_edit.opening_date = new_od
        project_to_edit.closing_date = new_cd
        project_to_edit.officer_slot = slot if slot is not None else project_to_edit.officer_slot
        # Visibility and manager NRIC are not typically editable here

        try:
            # Handle potential rename by deleting old key and adding new
            if new_name != original_name:
                 self.project_repository.delete(original_name)
                 self.project_repository.add(project_to_edit)
            else:
                 self.project_repository.update(project_to_edit)
            print(f"Project '{new_name}' updated successfully.")
        except IntegrityError as e:
             # Handle potential issues during save (e.g., concurrent modification)
             raise OperationError(f"Failed to save project updates for '{new_name}': {e}")
        except Exception as e:
            raise OperationError(f"An unexpected error occurred saving project updates for '{new_name}': {e}")


    def delete_project(self, manager: HDBManager, project_to_delete: Project):
        """Deletes a project. Requires manager authorization."""
        if project_to_delete.manager_nric != manager.nric:
            raise AuthorizationError("You can only delete projects you manage.")

        # Add warnings about consequences if needed (orphaned applications etc.)
        print(f"WARNING: Deleting project '{project_to_delete.project_name}' is permanent.")

        try:
            self.project_repository.delete_by_name(project_to_delete.project_name)
            print(f"Project '{project_to_delete.project_name}' deleted successfully.")
        except IntegrityError as e:
             # Should not happen if project exists, but handle defensively
             raise OperationError(f"Failed to delete project '{project_to_delete.project_name}': {e}")
        except Exception as e:
            raise OperationError(f"An unexpected error occurred deleting project '{project_to_delete.project_name}': {e}")


    def toggle_project_visibility(self, manager: HDBManager, project_to_toggle: Project) -> bool:
        """Toggles the visibility of a project. Requires manager authorization."""
        if project_to_toggle.manager_nric != manager.nric:
            raise AuthorizationError("You can only toggle visibility for projects you manage.")

        project_to_toggle.visibility = not project_to_toggle.visibility
        try:
            self.project_repository.update(project_to_toggle)
            new_status = "ON" if project_to_toggle.visibility else "OFF"
            print(f"Project '{project_to_toggle.project_name}' visibility set to {new_status}.")
            return project_to_toggle.visibility
        except IntegrityError as e:
             project_to_toggle.visibility = not project_to_toggle.visibility # Revert on failure
             raise OperationError(f"Failed to update project visibility for '{project_to_toggle.project_name}': {e}")
        except Exception as e:
            project_to_toggle.visibility = not project_to_toggle.visibility # Revert on failure
            raise OperationError(f"An unexpected error occurred updating visibility for '{project_to_toggle.project_name}': {e}")

    # --- Methods related to officer assignment (called by RegistrationService usually) ---

    def _add_officer_to_project_list(self, project: Project, officer_nric: str) -> bool:
        """Internal: Adds an officer NRIC directly to the project's list. Assumes checks done."""
        if officer_nric not in project.officer_nrics:
            # No need to check slots again here if called correctly
            project.officer_nrics.append(officer_nric)
            try:
                self.project_repository.update(project)
                return True
            except Exception as e:
                project.officer_nrics.remove(officer_nric) # Attempt revert
                print(f"Error: Failed to save project after adding officer {officer_nric}: {e}")
                raise OperationError(f"Failed to update project with new officer: {e}") # Propagate
        return True # Already there

    def _remove_officer_from_project_list(self, project: Project, officer_nric: str) -> bool:
        """Internal: Removes an officer NRIC directly from the project's list."""
        if officer_nric in project.officer_nrics:
            project.officer_nrics.remove(officer_nric)
            try:
                self.project_repository.update(project)
                return True
            except Exception as e:
                project.officer_nrics.append(officer_nric) # Attempt revert
                print(f"Error: Failed to save project after removing officer {officer_nric}: {e}")
                raise OperationError(f"Failed to update project after removing officer: {e}") # Propagate
        return True # Not there anyway