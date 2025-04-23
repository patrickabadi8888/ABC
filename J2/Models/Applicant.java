package Models;

import Enums.MaritalStatus;
import Enums.UserRole;
import Enums.ApplicationStatus;
import Enums.FlatType;

public class Applicant extends User {
    // These fields represent the *current* state, synchronized from application data
    private String appliedProjectName;
    private ApplicationStatus applicationStatus;
    private FlatType bookedFlatType;

    public Applicant(String nric, String password, String name, int age, MaritalStatus maritalStatus) {
        super(nric, password, name, age, maritalStatus);
        // Initial state is no application
        this.clearApplicationState();
    }

    @Override
    public UserRole getRole() { return UserRole.APPLICANT; }

    // Getters
    public String getAppliedProjectName() { return appliedProjectName; }
    public ApplicationStatus getApplicationStatus() { return applicationStatus; }
    public FlatType getBookedFlatType() { return bookedFlatType; }

    // Setters - Used by synchronization logic
    public void setAppliedProjectName(String appliedProjectName) { this.appliedProjectName = appliedProjectName; }
    public void setApplicationStatus(ApplicationStatus applicationStatus) { this.applicationStatus = applicationStatus; }
    public void setBookedFlatType(FlatType bookedFlatType) { this.bookedFlatType = bookedFlatType; }

    // Convenience methods based on status
    public boolean hasActiveApplication() {
        // Active means pending approval or approved but not yet booked
        return this.applicationStatus == ApplicationStatus.PENDING ||
               this.applicationStatus == ApplicationStatus.SUCCESSFUL;
    }

     public boolean hasPendingWithdrawal() {
        return this.applicationStatus == ApplicationStatus.PENDING_WITHDRAWAL;
    }

    public boolean hasBooked() {
        // Booked status implies a booked flat type should also be set
        return this.applicationStatus == ApplicationStatus.BOOKED;
        // Redundant check: && this.bookedFlatType != null; (should be guaranteed by booking logic)
    }

    // Method to reset state, e.g., if all applications are resolved/deleted
    public void clearApplicationState() {
        this.appliedProjectName = null;
        this.applicationStatus = null; // Or perhaps a 'NO_APPLICATION' status? Null seems fine.
        this.bookedFlatType = null;
    }
}
