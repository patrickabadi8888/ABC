package Interfaces.Services;

import java.util.Date;
import java.util.List;
import java.util.Map;
import Enums.FlatType;
import Models.FlatTypeDetails;
import Models.HDBManager;
import Models.Project;
import Models.User;

public interface IProjectService {
    Project findProjectByName(String name);
    List<Project> getAllProjects();
    List<Project> getVisibleProjects(User currentUser);
    List<Project> getOpenProjects(User currentUser); // Visible, Active, Eligible, Available
    List<Project> getManagedProjects(String managerNric);
    boolean createProject(String projectName, String neighborhood, Map<FlatType, FlatTypeDetails> flatTypes,
                          Date openingDate, Date closingDate, HDBManager manager, int maxOfficers);
    boolean editProjectDetails(Project project, String newNeighborhood, Map<FlatType, FlatTypeDetails> newFlatTypes,
                               Date newOpeningDate, Date newClosingDate, int newMaxSlots);
    boolean deleteProject(Project projectToDelete);
    boolean toggleProjectVisibility(Project project);
    boolean checkDateOverlap(Project p1, Project p2);
}
