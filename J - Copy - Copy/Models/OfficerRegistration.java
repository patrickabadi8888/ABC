package Models;

import Enums.OfficerRegistrationStatus;
import java.util.Date;

public class OfficerRegistration {
    private final String registrationId;
    private final String officerNric;
    private final String projectName;
    private OfficerRegistrationStatus status;
    private final Date registrationDate;

    public OfficerRegistration(String officerNric, String projectName, Date registrationDate) {
         if (officerNric == null || projectName == null || registrationDate == null) {
            throw new IllegalArgumentException("OfficerRegistration fields cannot be null");
        }
        this.registrationId = officerNric + "_REG_" + projectName;
        this.officerNric = officerNric;
        this.projectName = projectName;
        this.status = OfficerRegistrationStatus.PENDING;
        this.registrationDate = registrationDate;
    }

    public OfficerRegistration(String registrationId, String officerNric, String projectName, OfficerRegistrationStatus status, Date registrationDate) {
         if (registrationId == null || officerNric == null || projectName == null || status == null || registrationDate == null) {
            throw new IllegalArgumentException("Required OfficerRegistration fields cannot be null when loading");
        }
        this.registrationId = registrationId;
        this.officerNric = officerNric;
        this.projectName = projectName;
        this.status = status;
        this.registrationDate = registrationDate;
    }

    public String getRegistrationId() { return registrationId; }
    public String getOfficerNric() { return officerNric; }
    public String getProjectName() { return projectName; }
    public OfficerRegistrationStatus getStatus() { return status; }
    public Date getRegistrationDate() { return registrationDate; }

    public void setStatus(OfficerRegistrationStatus status) {
        if (status != null) {
            this.status = status;
        }
    }
}
