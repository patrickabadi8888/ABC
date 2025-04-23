package Enums;

import java.util.Comparator;

public enum ApplicationStatus {
    // Define priority for sorting/comparison (higher value = higher priority/later stage)
    PENDING(3),
    SUCCESSFUL(5),
    BOOKED(6),
    PENDING_WITHDRAWAL(4), // Higher than PENDING, lower than SUCCESSFUL/BOOKED
    WITHDRAWN(2),          // Approved withdrawal from PENDING
    UNSUCCESSFUL(1);       // Rejected or withdrawn after SUCCESSFUL/BOOKED

    private final int priority;

    ApplicationStatus(int priority) {
        this.priority = priority;
    }

    public int getPriority() {
        return priority;
    }

    // Optional: Comparator for sorting by priority
    public static Comparator<ApplicationStatus> priorityComparator() {
        return Comparator.comparingInt(ApplicationStatus::getPriority);
    }
}
