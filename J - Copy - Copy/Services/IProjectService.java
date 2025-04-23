package Services;

import java.util.List;
import java.util.Map;
import Models.Project;
import Models.User;

public interface IProjectService {
    List<Project> loadProjects(Map<String, User> users); // Pass users for validation during load
    void saveProjects(List<Project> projects);
    Project findProjectByName(String name);
    List<Project> getAllProjects();
    List<Project> getProjectsManagedBy(String managerNric);
    void addProject(Project project);
    boolean removeProject(Project project);
}
