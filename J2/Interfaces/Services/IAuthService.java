package Interfaces.Services;

import Models.User;

public interface IAuthService {
    User login(String nric, String password);
    boolean changePassword(User user, String oldPassword, String newPassword);
}
