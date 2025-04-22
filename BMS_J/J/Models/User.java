package Models;

import Enums.MaritalStatus;
import Enums.UserRole;

public abstract class User {
    private final String nric;
    private String password;
    private final String name;
    private final int age;
    private final MaritalStatus maritalStatus;

    public User(String nric, String password, String name, int age, MaritalStatus maritalStatus) {
        if (nric == null || password == null || name == null || maritalStatus == null) {
            throw new IllegalArgumentException("User fields cannot be null");
        }
        this.nric = nric;
        this.password = password;
        this.name = name;
        this.age = age;
        this.maritalStatus = maritalStatus;
    }

    public String getNric() { return nric; }
    public String getPassword() { return password; }
    public String getName() { return name; }
    public int getAge() { return age; }
    public MaritalStatus getMaritalStatus() { return maritalStatus; }

    public void setPassword(String password) {
        if (password != null && !password.isEmpty()) {
            this.password = password;
        } else {
            System.err.println("Warning: Attempted to set null or empty password for NRIC: " + nric);
        }
    }

    public abstract UserRole getRole();
}