package Services;

import java.util.List;
import java.util.Map;
import Models.OfficerRegistration;
import Models.Project; // Needed for validation during load
import Models.User; // Needed for validation during load
import Enums.OfficerRegistrationStatus;

public interface IOfficerRegistrationService {
    Map<String, OfficerRegistration> loadOfficerRegistrations(Map<String, User> users, List<Project> projects); // Pass dependencies for validation
    void saveOfficerRegistrations(Map<String, OfficerRegistration> registrations);
    OfficerRegistration findRegistrationById(String registrationId);
    List<OfficerRegistration> getRegistrationsByOfficer(String officerNric);
    List<OfficerRegistration> getRegistrationsByProject(String projectName);
    List<OfficerRegistration> getRegistrationsByStatus(OfficerRegistrationStatus status);
    OfficerRegistration getApprovedRegistrationForOfficer(String officerNric); // More specific query
    void addRegistration(OfficerRegistration registration);
    boolean removeRegistration(String registrationId);
    Map<String, OfficerRegistration> getAllRegistrations(); // To get map for saving/syncing
}
