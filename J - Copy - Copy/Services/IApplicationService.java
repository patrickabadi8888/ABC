package Services;

import java.util.List;
import java.util.Map;
import Models.BTOApplication;
import Models.Project; // Needed for adjusting units during load
import Enums.ApplicationStatus;

public interface IApplicationService {
    Map<String, BTOApplication> loadApplications(List<Project> projects); // Pass projects to adjust units
    void saveApplications(Map<String, BTOApplication> applications);
    BTOApplication findApplicationById(String applicationId);
    BTOApplication findApplicationByApplicantAndProject(String nric, String projectName);
    List<BTOApplication> getApplicationsByProject(String projectName);
    List<BTOApplication> getApplicationsByStatus(ApplicationStatus status);
    List<BTOApplication> getApplicationsByApplicant(String nric);
    void addApplication(BTOApplication application);
    boolean removeApplication(String applicationId);
    Map<String, BTOApplication> getAllApplications(); // To get the map for saving/syncing
}
