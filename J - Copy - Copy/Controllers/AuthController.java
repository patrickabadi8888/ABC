package Controllers;

import Models.User;
import Services.DataService; // Still uses static DataService.saveUsers
import Services.IUserService; // Can be injected if DataService.saveUsers is removed
import Utils.NricValidator;

public class AuthController {
    // Can optionally inject IUserService instead of passing map if needed elsewhere
    private final IUserService userService; // Changed to use UserService

    public AuthController(IUserService userService) { // Accept IUserService
        this.userService = userService;
    }

    public User login(String nric, String password) {
        if (!NricValidator.isValidNric(nric)) {
            System.out.println("Invalid NRIC format.");
            return null;
        }
        User user = userService.findUserByNric(nric); // Find user via service
        if (user != null && user.getPassword().equals(password)) {
            return user; // Login success
        } else if (user != null) {
            System.out.println("Incorrect password.");
            return null; // Wrong password
        } else {
            System.out.println("User NRIC not found.");
            return null; // User not found
        }
    }

    // This method modifies User state and triggers a save.
    // It needs access to the *live* user object and a way to save.
    public boolean changePassword(User user, String oldPassword, String newPassword) {
        if (user == null) return false; // Should not happen if called after login

        // Verify old password
        if (user.getPassword().equals(oldPassword)) {
            // Validate new password
            if (newPassword != null && !newPassword.isEmpty()) {
                if (newPassword.equals(oldPassword)) {
                     System.out.println("New password cannot be the same as the old password. Password not changed.");
                     return false;
                }
                // Update password on the User object
                user.setPassword(newPassword);

                // Save the updated user data
                // Ideally, use userService.saveUsers(userService.getAllUsers())
                // But for minimal change, keep using the static DataService method
                DataService.saveUsers(userService.getAllUsers()); // Save ALL users

                System.out.println("Password changed successfully. Please log in again.");
                return true; // Indicate success (caller should handle logout)
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
