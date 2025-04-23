package Enums;

public enum ApplicationStatus {
    PENDING,          // Initial state
    SUCCESSFUL,       // Manager approved, applicant can book
    UNSUCCESSFUL,     // Manager rejected, or withdrawal approved after SUCCESSFUL/BOOKED
    BOOKED,           // Officer confirmed booking
    PENDING_WITHDRAWAL, // Applicant requested withdrawal, awaiting Manager action
    WITHDRAWN         // Manager approved withdrawal from PENDING state
}