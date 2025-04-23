/**
 * Interface defining the contract for user data management services.
 * Specifies methods for loading, saving, finding, and retrieving user data.
 *
 * @author Kishore Kumar
 */
package Services;

import java.util.Map;
import Models.User;

public interface IUserService {

    Map<String, User> loadUsers();

    void saveUsers(Map<String, User> users);

    User findUserByNric(String nric);

    Map<String, User> getAllUsers();
}
