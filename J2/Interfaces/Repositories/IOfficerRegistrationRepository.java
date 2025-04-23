package Interfaces.Repositories;

import java.util.List;
import java.util.Map;
import Models.OfficerRegistration;

public interface IOfficerRegistrationRepository {
    Map<String, OfficerRegistration> loadOfficerRegistrations();
    void saveOfficerRegistrations(Map<String, OfficerRegistration> registrations);
    Map<String, OfficerRegistration> getAllRegistrations(); // Added for easier access by services
}
