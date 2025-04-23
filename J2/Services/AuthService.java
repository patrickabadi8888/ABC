package Services;

import Interfaces.Repositories.IUserRepository;
import Interfaces.Services.IAuthService;
import Models.User;
import Utils.NricValidator;

public class AuthService implements IAuthService {
    private final IUserRepository userRepository;

    public AuthService(IUserRepository userRepository) {
        this.userRepository = userRepository;
    }

    @Override
    public User login(String nric, String password) {
        if (nric == null || password == null) return null;
        String upperNric = nric.trim().toUpperCase();

        if (!NricValidator.isValidNric(upperNric)) {
            System.out.println("Invalid NRIC format.");
            return null;
        }
        User user = userRepository.findUserByNric(upperNric); // Use repository method
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

    @Override
    public boolean changePassword(User user, String oldPassword, String newPassword) {
        if (user == null || oldPassword == null || newPassword == null) return false;

        // Find the user in the repository to ensure we're working with the persisted state if necessary
        // Though the passed 'user' object should be the one to modify
        User persistedUser = userRepository.findUserByNric(user.getNric());
        if (persistedUser == null || !persistedUser.getNric().equals(user.getNric())) {
             System.err.println("Error: User mismatch during password change.");
             return false;
        }


        if (user.getPassword().equals(oldPassword)) {
            if (!newPassword.isEmpty()) {
                if (newPassword.equals(oldPassword)) {
                     System.out.println("New password cannot be the same as the old password.");
                     return false;
                }
                user.setPassword(newPassword); // Update the user object passed in

                // Save the updated user state via the repository
                Map<String, User> allUsers = userRepository.getAllUsers();
                allUsers.put(user.getNric(), user); // Update the map
                userRepository.saveUsers(allUsers); // Persist changes

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
