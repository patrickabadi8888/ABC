/**
 * Interface defining the contract for HDB Officer project registration management services.
 * Specifies methods for loading, saving, finding, retrieving, adding, and removing registrations.
 *
 * @author Kishore Kumar
 */
package Services;

import java.util.List;
import java.util.Map;
import Models.OfficerRegistration;
import Models.Project;
import Models.User;
import Enums.OfficerRegistrationStatus;

public interface IOfficerRegistrationService {

    Map<String, OfficerRegistration> loadOfficerRegistrations(Map<String, User> users, List<Project> projects);

    void saveOfficerRegistrations(Map<String, OfficerRegistration> registrations);

    OfficerRegistration findRegistrationById(String registrationId);

    List<OfficerRegistration> getRegistrationsByOfficer(String officerNric);

    List<OfficerRegistration> getRegistrationsByProject(String projectName);

    List<OfficerRegistration> getRegistrationsByStatus(OfficerRegistrationStatus status);

    OfficerRegistration getApprovedRegistrationForOfficer(String officerNric);

    void addRegistration(OfficerRegistration registration);

    boolean removeRegistration(String registrationId);

    Map<String, OfficerRegistration> getAllRegistrations();
}
