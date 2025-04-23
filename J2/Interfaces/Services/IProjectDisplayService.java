package Interfaces.Services;

import java.util.List;
import Models.Project;
import Models.User;
import java.util.Scanner;

public interface IProjectDisplayService {
    void displayProjectList(List<Project> projectList, String prompt, User currentUser);
    Project selectProjectFromList(List<Project> projectList, Scanner scanner); // Scanner passed for interaction
}
