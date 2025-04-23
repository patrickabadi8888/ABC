package Services;

import java.util.Map;
import Models.User;

public interface IUserService {
    Map<String, User> loadUsers();
    void saveUsers(Map<String, User> users);
    User findUserByNric(String nric);
    Map<String, User> getAllUsers(); // Added to facilitate saving and synchronization
}
