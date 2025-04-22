package Controllers;

import java.util.Map;
import Models.User;
import Services.DataService;

public class AuthController {
    private final Map<String, User> users;

    public AuthController(Map<String, User> users) {
        this.users = users;
    }

    public User login(String nric, String password) {
        if (!DataService.isValidNric(nric)) {
            System.out.println("Invalid NRIC format.");
            return null;
        }
        User user = users.get(nric);
        if (user != null && user.getPassword().equals(password)) {
            return user;
        } else if (user != null) {
            System.out.println("Incorrect password.");
            return null;
        } else {
            System.out.println("User NRIC not found.");
            return null;
        }
    }

    public boolean changePassword(User user, String oldPassword, String newPassword) {
        if (user == null) return false;

        if (user.getPassword().equals(oldPassword)) {
            if (newPassword != null && !newPassword.isEmpty()) {
                user.setPassword(newPassword);
                DataService.saveUsers(users);
                System.out.println("Password changed successfully. Please log in again.");
                return true;
            } else {
                 System.out.println("New password cannot be empty.");
                 return false;
            }
        } else {
            System.out.println("Incorrect old password.");
            return false;
        }
    }
}

