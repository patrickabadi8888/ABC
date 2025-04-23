package Interfaces.Repositories;

import java.util.List;
import Models.Project;

public interface IProjectRepository {
    List<Project> loadProjects();
    void saveProjects(List<Project> projects);
    List<Project> getAllProjects(); // Added for easier access by services
    Project findProjectByName(String name); // Convenience method
}
