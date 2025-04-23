package Interfaces.Repositories;

import java.util.Map;
import Models.User;

public interface IUserRepository {
    Map<String, User> loadUsers();
    void saveUsers(Map<String, User> users);
    User findUserByNric(String nric);
    Map<String, User> getAllUsers(); // Added for easier access by services
}
