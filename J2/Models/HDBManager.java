package Models;

import Enums.MaritalStatus;
import Enums.UserRole;

// This class might not need to extend Applicant if Managers cannot perform Applicant actions.
// Let's assume they are distinct for now and extend User directly.
public class HDBManager extends User {

    public HDBManager(String nric, String password, String name, int age, MaritalStatus maritalStatus) {
        super(nric, password, name, age, maritalStatus);
        // No manager-specific fields currently
    }

    @Override
    public UserRole getRole() {
        return UserRole.HDB_MANAGER;
    }

    // Add any manager-specific methods or properties here if needed in the future.
}
