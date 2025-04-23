package Interfaces.Repositories;

import java.util.Map;
import Models.BTOApplication;

public interface IApplicationRepository {
    Map<String, BTOApplication> loadApplications();
    void saveApplications(Map<String, BTOApplication> applications);
    Map<String, BTOApplication> getAllApplications(); // Added for easier access by services
}
