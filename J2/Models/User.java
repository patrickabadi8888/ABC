package Models;

import Enums.MaritalStatus;
import Enums.UserRole;
import java.util.Objects;

public abstract class User {
    private final String nric; // Unique identifier, should be final
    private String password; // Mutable
    private final String name; // Should be final? Assume yes for simplicity.
    private final int age; // Should be final? Assume yes.
    private final MaritalStatus maritalStatus; // Should be final? Assume yes.

    public User(String nric, String password, String name, int age, MaritalStatus maritalStatus) {
        // Use Objects.requireNonNull for cleaner null checks
        Objects.requireNonNull(nric, "NRIC cannot be null");
        Objects.requireNonNull(password, "Password cannot be null");
        Objects.requireNonNull(name, "Name cannot be null");
        Objects.requireNonNull(maritalStatus, "Marital Status cannot be null");

        // Basic validation
        if (nric.trim().isEmpty()) throw new IllegalArgumentException("NRIC cannot be empty");
        if (password.isEmpty()) throw new IllegalArgumentException("Password cannot be empty"); // Allow spaces? No.
        if (name.trim().isEmpty()) throw new IllegalArgumentException("Name cannot be empty");
        if (age <= 0) throw new IllegalArgumentException("Age must be positive");

        // Consider NRIC format validation here or rely on external validation (like NricValidator)
        this.nric = nric.trim().toUpperCase(); // Store NRIC consistently
        this.password = password;
        this.name = name.trim();
        this.age = age;
        this.maritalStatus = maritalStatus;
    }

    // --- Getters ---
    public String getNric() { return nric; }
    public String getPassword() { return password; }
    public String getName() { return name; }
    public int getAge() { return age; }
    public MaritalStatus getMaritalStatus() { return maritalStatus; }

    // --- Setters ---
    public void setPassword(String password) {
        Objects.requireNonNull(password, "Password cannot be null");
        if (password.isEmpty()) {
             System.err.println("Warning: Attempted to set empty password for NRIC: " + nric + ". Password not changed.");
             // Or throw new IllegalArgumentException("Password cannot be empty");
             return;
        }
        this.password = password;
    }

    // Abstract method to be implemented by subclasses
    public abstract UserRole getRole();

    // --- Standard overrides ---
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false; // Check class equality for distinct roles
        User user = (User) o;
        return nric.equals(user.nric); // NRIC is the unique identifier
    }

    @Override
    public int hashCode() {
        return Objects.hash(nric);
    }

    @Override
    public String toString() {
        return "User{" +
                "nric='" + nric + '\'' +
                ", name='" + name + '\'' +
                ", age=" + age +
                ", maritalStatus=" + maritalStatus +
                ", role=" + getRole() + // Include role from subclass
                '}';
    }
}
