package Interfaces.Services;

import java.util.List;
import java.util.Map;
import Models.HDBOfficer;
import Models.OfficerRegistration;
import Models.Project;

public interface IOfficerRegistrationService {
    boolean submitRegistration(HDBOfficer officer, Project project);
    boolean approveRegistration(OfficerRegistration registration, Project project);
    boolean rejectRegistration(OfficerRegistration registration);
    List<OfficerRegistration> getRegistrationsByOfficer(String nric);
    List<OfficerRegistration> getRegistrationsByProject(String projectName);
    List<OfficerRegistration> getPendingRegistrationsForProject(String projectName);
    void removeRegistrationsForProject(String projectName); // For project deletion
}
