package Models;

import Enums.ApplicationStatus;
import Enums.FlatType;

import java.util.Date;
import java.util.Objects;

public class BTOApplication {
    private final String applicationId; // Format: ApplicantNRIC_ProjectName
    private final String applicantNric;
    private final String projectName;
    private FlatType flatTypeApplied; // Can be null initially? No, required on creation.
    private ApplicationStatus status;
    private final Date applicationDate;
    private ApplicationStatus statusBeforeWithdrawal; // To revert if withdrawal is rejected

    // Static method to generate consistent IDs
    public static String generateId(String applicantNric, String projectName) {
         return applicantNric + "_" + projectName;
    }

    // Constructor for new applications
    public BTOApplication(String applicantNric, String projectName, FlatType flatTypeApplied, Date applicationDate) {
        // Basic null checks
        Objects.requireNonNull(applicantNric, "Applicant NRIC cannot be null");
        Objects.requireNonNull(projectName, "Project Name cannot be null");
        Objects.requireNonNull(flatTypeApplied, "Flat Type Applied cannot be null for new application");
        Objects.requireNonNull(applicationDate, "Application Date cannot be null");

        if (applicantNric.trim().isEmpty() || projectName.trim().isEmpty()) {
             throw new IllegalArgumentException("Applicant NRIC and Project Name cannot be empty");
        }

        this.applicationId = generateId(applicantNric, projectName);
        this.applicantNric = applicantNric;
        this.projectName = projectName;
        this.flatTypeApplied = flatTypeApplied;
        this.status = ApplicationStatus.PENDING; // New applications start as PENDING
        this.applicationDate = applicationDate;
        this.statusBeforeWithdrawal = null;
    }

    // Constructor for loading from persistence
    public BTOApplication(String applicationId, String applicantNric, String projectName, FlatType flatTypeApplied, ApplicationStatus status, Date applicationDate) {
        // Basic null checks for required fields during load
        Objects.requireNonNull(applicationId, "Application ID cannot be null when loading");
        Objects.requireNonNull(applicantNric, "Applicant NRIC cannot be null when loading");
        Objects.requireNonNull(projectName, "Project Name cannot be null when loading");
        Objects.requireNonNull(status, "Status cannot be null when loading");
        Objects.requireNonNull(applicationDate, "Application Date cannot be null when loading");

        // Warning if status implies a flat type but it's null
         if (flatTypeApplied == null && (status == ApplicationStatus.BOOKED || status == ApplicationStatus.SUCCESSFUL || status == ApplicationStatus.PENDING_WITHDRAWAL )) {
              System.err.println("Warning: Loading " + status + " application ("+applicationId+") with null flatTypeApplied. Data might be inconsistent.");
         }

        this.applicationId = applicationId;
        this.applicantNric = applicantNric;
        this.projectName = projectName;
        this.flatTypeApplied = flatTypeApplied; // Allow null when loading if CSV was inconsistent
        this.status = status;
        this.applicationDate = applicationDate;
        this.statusBeforeWithdrawal = null; // This should ideally be persisted too if needed across sessions

        // Log if loaded in pending withdrawal state without knowing original
        if (status == ApplicationStatus.PENDING_WITHDRAWAL) {
            // The service layer will handle inferring the original status if needed
            System.out.println("Info: Application " + applicationId + " loaded with PENDING_WITHDRAWAL status.");
        }
    }

    // Getters
    public String getApplicationId() { return applicationId; }
    public String getApplicantNric() { return applicantNric; }
    public String getProjectName() { return projectName; }
    public FlatType getFlatTypeApplied() { return flatTypeApplied; }
    public ApplicationStatus getStatus() { return status; }
    public Date getApplicationDate() { return applicationDate; }
    public ApplicationStatus getStatusBeforeWithdrawal() { return statusBeforeWithdrawal; }

    // Setter for status, handles storing previous status on withdrawal request
    public void setStatus(ApplicationStatus newStatus) {
        Objects.requireNonNull(newStatus, "Application status cannot be set to null");

        // If moving TO pending withdrawal, store the current status
        if (newStatus == ApplicationStatus.PENDING_WITHDRAWAL && this.status != ApplicationStatus.PENDING_WITHDRAWAL) {
            this.statusBeforeWithdrawal = this.status;
        }
        // If moving FROM pending withdrawal (approved/rejected), clear the stored status
        else if (this.status == ApplicationStatus.PENDING_WITHDRAWAL && newStatus != ApplicationStatus.PENDING_WITHDRAWAL) {
            this.statusBeforeWithdrawal = null;
        }
        this.status = newStatus;
    }

    // Optional: Setter for flat type if it can change post-application (unlikely in BTO)
    // public void setFlatTypeApplied(FlatType flatTypeApplied) { this.flatTypeApplied = flatTypeApplied; }

    // --- Standard overrides ---
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        BTOApplication that = (BTOApplication) o;
        return applicationId.equals(that.applicationId); // ID is unique identifier
    }

    @Override
    public int hashCode() {
        return Objects.hash(applicationId);
    }

    @Override
    public String toString() {
        return "BTOApplication{" +
                "applicationId='" + applicationId + '\'' +
                ", applicantNric='" + applicantNric + '\'' +
                ", projectName='" + projectName + '\'' +
                ", flatTypeApplied=" + flatTypeApplied +
                ", status=" + status +
                ", applicationDate=" + applicationDate +
                ", statusBeforeWithdrawal=" + statusBeforeWithdrawal +
                '}';
    }
}
