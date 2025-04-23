package Models;

import Enums.UserRole;
import Enums.MaritalStatus;

public class HDBOfficer extends Applicant {

    public HDBOfficer(String nric, String password, String name, int age, MaritalStatus maritalStatus) {
        super(nric, password, name, age, maritalStatus);
    }

    @Override
    public UserRole getRole() { return UserRole.HDB_OFFICER; }

}