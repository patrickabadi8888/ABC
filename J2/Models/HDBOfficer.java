package Models;

import Enums.UserRole;
import Enums.MaritalStatus;

// HDBOfficer inherits Applicant capabilities (can view projects, apply - though restricted, manage own enquiries)
public class HDBOfficer extends Applicant {

    public HDBOfficer(String nric, String password, String name, int age, MaritalStatus maritalStatus) {
        super(nric, password, name, age, maritalStatus);
        // No officer-specific fields currently, inherits application state from Applicant
    }

    @Override
    public UserRole getRole() {
        return UserRole.HDB_OFFICER;
    }

    // Add any officer-specific methods or properties here if needed.
    // For example, reference to the project they are currently handling (though this is derived in EligibilityService).
}
