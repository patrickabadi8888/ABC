package Models;

import Enums.OfficerRegistrationStatus;
import java.util.Date;
import java.util.Objects;

public class OfficerRegistration {
    private final String registrationId; // Format: OfficerNRIC_REG_ProjectName
    private final String officerNric;
    private final String projectName;
    private OfficerRegistrationStatus status; // Mutable status
    private final Date registrationDate;

    // Static method to generate consistent IDs
    public static String generateId(String officerNric, String projectName) {
        return officerNric + "_REG_" + projectName;
    }

    // Constructor for new registrations (always start as PENDING)
    public OfficerRegistration(String officerNric, String projectName, Date registrationDate) {
        Objects.requireNonNull(officerNric, "Officer NRIC cannot be null");
        Objects.requireNonNull(projectName, "Project Name cannot be null");
        Objects.requireNonNull(registrationDate, "Registration Date cannot be null");
        if (officerNric.trim().isEmpty() || projectName.trim().isEmpty()) {
             throw new IllegalArgumentException("Officer NRIC and Project Name cannot be empty");
        }

        this.registrationId = generateId(officerNric, projectName);
        this.officerNric = officerNric;
        this.projectName = projectName;
        this.status = OfficerRegistrationStatus.PENDING; // Default status
        this.registrationDate = registrationDate;
    }

    // Constructor for loading from persistence
    public OfficerRegistration(String registrationId, String officerNric, String projectName, OfficerRegistrationStatus status, Date registrationDate) {
        Objects.requireNonNull(registrationId, "Registration ID cannot be null when loading");
        Objects.requireNonNull(officerNric, "Officer NRIC cannot be null when loading");
        Objects.requireNonNull(projectName, "Project Name cannot be null when loading");
        Objects.requireNonNull(status, "Status cannot be null when loading");
        Objects.requireNonNull(registrationDate, "Registration Date cannot be null when loading");

        this.registrationId = registrationId;
        this.officerNric = officerNric;
        this.projectName = projectName;
        this.status = status;
        this.registrationDate = registrationDate;
    }

    // Getters
    public String getRegistrationId() { return registrationId; }
    public String getOfficerNric() { return officerNric; }
    public String getProjectName() { return projectName; }
    public OfficerRegistrationStatus getStatus() { return status; }
    public Date getRegistrationDate() { return registrationDate; }

    // Setter for status
    public void setStatus(OfficerRegistrationStatus status) {
        Objects.requireNonNull(status, "Status cannot be set to null");
        this.status = status;
    }

    // --- Standard overrides ---
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        OfficerRegistration that = (OfficerRegistration) o;
        return registrationId.equals(that.registrationId); // ID is unique identifier
    }

    @Override
    public int hashCode() {
        return Objects.hash(registrationId);
    }

    @Override
    public String toString() {
        return "OfficerRegistration{" +
                "registrationId='" + registrationId + '\'' +
                ", officerNric='" + officerNric + '\'' +
                ", projectName='" + projectName + '\'' +
                ", status=" + status +
                ", registrationDate=" + registrationDate +
                '}';
    }
}
