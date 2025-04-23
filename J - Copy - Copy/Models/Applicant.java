package Models;

import Enums.MaritalStatus;
import Enums.UserRole;
import Enums.ApplicationStatus;
import Enums.FlatType;

public class Applicant extends User {
    private String appliedProjectName;
    private ApplicationStatus applicationStatus;
    private FlatType bookedFlatType;

    public Applicant(String nric, String password, String name, int age, MaritalStatus maritalStatus) {
        super(nric, password, name, age, maritalStatus);
        this.applicationStatus = null;
        this.appliedProjectName = null;
        this.bookedFlatType = null;
    }

    @Override
    public UserRole getRole() { return UserRole.APPLICANT; }

    public String getAppliedProjectName() { return appliedProjectName; }
    public void setAppliedProjectName(String appliedProjectName) { this.appliedProjectName = appliedProjectName; }

    public ApplicationStatus getApplicationStatus() { return applicationStatus; }
    public void setApplicationStatus(ApplicationStatus applicationStatus) { this.applicationStatus = applicationStatus; }

    public FlatType getBookedFlatType() { return bookedFlatType; }
    public void setBookedFlatType(FlatType bookedFlatType) { this.bookedFlatType = bookedFlatType; }

    public boolean hasActiveApplication() {
        return this.applicationStatus == ApplicationStatus.PENDING ||
               this.applicationStatus == ApplicationStatus.SUCCESSFUL;
    }

     public boolean hasPendingWithdrawal() {
        return this.applicationStatus == ApplicationStatus.PENDING_WITHDRAWAL;
    }


    public boolean hasBooked() {
        return this.applicationStatus == ApplicationStatus.BOOKED && this.bookedFlatType != null;
    }

    public void clearApplicationState() {
        this.appliedProjectName = null;
        this.applicationStatus = null;
        this.bookedFlatType = null;
    }
}