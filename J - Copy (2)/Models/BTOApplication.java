package Models;

import Enums.ApplicationStatus;
import Enums.FlatType;

import java.util.Date;

public class BTOApplication {
    private final String applicationId;
    private final String applicantNric;
    private final String projectName;
    private FlatType flatTypeApplied;
    private ApplicationStatus status;
    private final Date applicationDate;
    private ApplicationStatus statusBeforeWithdrawal;

    public BTOApplication(String applicantNric, String projectName, FlatType flatTypeApplied, Date applicationDate) {
        if (applicantNric == null || projectName == null || flatTypeApplied == null || applicationDate == null) {
            throw new IllegalArgumentException("BTOApplication fields cannot be null");
        }
        this.applicationId = applicantNric + "_" + projectName;
        this.applicantNric = applicantNric;
        this.projectName = projectName;
        this.flatTypeApplied = flatTypeApplied;
        this.status = ApplicationStatus.PENDING;
        this.applicationDate = applicationDate;
        this.statusBeforeWithdrawal = null;
    }

    public BTOApplication(String applicationId, String applicantNric, String projectName, FlatType flatTypeApplied, ApplicationStatus status, Date applicationDate) {
        if (applicationId == null || applicantNric == null || projectName == null || status == null || applicationDate == null) {
             throw new IllegalArgumentException("Required BTOApplication fields cannot be null when loading");
        }
         if (flatTypeApplied == null && (status == ApplicationStatus.BOOKED || status == ApplicationStatus.SUCCESSFUL || status == ApplicationStatus.PENDING_WITHDRAWAL )) {
              System.err.println("Warning: Loading " + status + " application ("+applicationId+") with null flatTypeApplied.");
         }

        this.applicationId = applicationId;
        this.applicantNric = applicantNric;
        this.projectName = projectName;
        this.flatTypeApplied = flatTypeApplied;
        this.status = status;
        this.applicationDate = applicationDate;
        this.statusBeforeWithdrawal = null;
        if (status == ApplicationStatus.PENDING_WITHDRAWAL) {
            System.err.println("Warning: Application " + applicationId + " loaded with PENDING_WITHDRAWAL status. Original status before withdrawal is unknown. Reverting will assume PENDING/SUCCESSFUL based on flat type.");
        }
    }

    public String getApplicationId() { return applicationId; }
    public String getApplicantNric() { return applicantNric; }
    public String getProjectName() { return projectName; }
    public FlatType getFlatTypeApplied() { return flatTypeApplied; }
    public ApplicationStatus getStatus() { return status; }
    public Date getApplicationDate() { return applicationDate; }
    public ApplicationStatus getStatusBeforeWithdrawal() { return statusBeforeWithdrawal; }

    public void setStatus(ApplicationStatus status) {
        if (status != null) {
            if (status == ApplicationStatus.PENDING_WITHDRAWAL && this.status != ApplicationStatus.PENDING_WITHDRAWAL) {
                this.statusBeforeWithdrawal = this.status;
            }
            if (this.status == ApplicationStatus.PENDING_WITHDRAWAL && status != ApplicationStatus.PENDING_WITHDRAWAL) {
                this.statusBeforeWithdrawal = null;
            }
            this.status = status;
        }
    }

}
