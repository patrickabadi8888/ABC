package Views;

import java.util.Scanner;
import Models.User;
import Interfaces.Services.IAuthService;
import Interfaces.Services.IFilterService;
import Utils.InputUtils; // Use InputUtils

public abstract class BaseView {
    protected final Scanner scanner;
    protected final User currentUser;
    // Services needed by base view actions
    protected final IAuthService authService;
    protected final IFilterService filterService;

    public BaseView(Scanner scanner, User currentUser, IAuthService authService, IFilterService filterService) {
        this.scanner = scanner;
        this.currentUser = currentUser;
        this.authService = authService;
        this.filterService = filterService;
    }

    // Abstract method for subclasses to implement their specific menu
    public abstract void displayMenu();

    /**
     * Gets a valid menu choice from the user within the specified range.
     * @param min Minimum valid choice number.
     * @param max Maximum valid choice number.
     * @return The valid integer choice entered by the user.
     */
    protected int getMenuChoice(int min, int max) {
        // Delegate to InputUtils
        return InputUtils.getIntInput(scanner, "Enter your choice: ", min, max);
    }

     /**
      * Handles the process of changing the current user's password.
      * Delegates the actual password change logic to the AuthService.
      * @return true if the password was successfully changed (requires re-login), false otherwise.
      */
     protected boolean changePassword() {
         System.out.println("\n--- Change Password ---");
         System.out.print("Enter current password: ");
         String oldPassword = scanner.nextLine();
         System.out.print("Enter new password: ");
         String newPassword = scanner.nextLine();
         System.out.print("Confirm new password: ");
         String confirmPassword = scanner.nextLine();

         if (!newPassword.equals(confirmPassword)) {
             System.out.println("New passwords do not match. Password not changed.");
             return false;
         }
         // Other checks (empty, same as old) handled by AuthService.changePassword

         // Delegate to auth service
         boolean success = authService.changePassword(currentUser, oldPassword, newPassword);
         // Success/error messages printed within service
         return success; // Return success status (true means logout needed)
     }

     /**
      * Handles applying or clearing project view filters.
      * Delegates the logic to the FilterService.
      */
     protected void applyFilters() {
         // This method now belongs more logically in the specific controllers
         // as it interacts with the FilterService state.
         // Keeping it here requires passing FilterService, which we did.
         System.out.println("\n--- Apply/Clear Filters ---");
         System.out.print("Enter neighborhood to filter by (current: "
                 + (filterService.getLocationFilter() == null ? "Any" : filterService.getLocationFilter()) + ", leave blank to clear): ");
         String loc = scanner.nextLine().trim();
         filterService.setLocationFilter(loc); // Service handles empty string logic

         System.out.print("Enter flat type to filter by (TWO_ROOM, THREE_ROOM, current: "
                 + (filterService.getFlatTypeFilter() == null ? "Any" : filterService.getFlatTypeFilter()) + ", leave blank to clear): ");
         String typeStr = scanner.nextLine().trim();
         if (typeStr.isEmpty()) {
             filterService.setFlatTypeFilter(null);
         } else {
             try {
                 Enums.FlatType parsedType = Enums.FlatType.fromString(typeStr); // Use enum parser
                 if (parsedType != null) {
                     filterService.setFlatTypeFilter(parsedType);
                 } else {
                     System.out.println("Invalid flat type entered. Filter not changed.");
                 }
             } catch (IllegalArgumentException e) {
                 System.out.println("Invalid flat type format. Filter not changed.");
             }
         }
         System.out.println("Filters updated. Current filters: " + filterService.getCurrentFilterStatus());
     }

     /**
      * Pauses execution and waits for the user to press Enter.
      */
     protected void pause() {
          System.out.println("\nPress Enter to continue...");
          scanner.nextLine(); // Consume the Enter key
     }
}
