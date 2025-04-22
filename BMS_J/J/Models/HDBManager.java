package Models;

import Enums.MaritalStatus;
import Enums.UserRole;

public class HDBManager extends User {

    public HDBManager(String nric, String password, String name, int age, MaritalStatus maritalStatus) {
        super(nric, password, name, age, maritalStatus);
    }

    @Override
    public UserRole getRole() { return UserRole.HDB_MANAGER; }

}