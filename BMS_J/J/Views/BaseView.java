package Views;

import java.util.Scanner;

import Models.User;

import Controllers.BaseController;
import Controllers.AuthController;

public abstract class BaseView {
    protected final Scanner scanner;
    protected final User currentUser;
    protected final BaseController controller;
    protected final AuthController authController;

    public BaseView(Scanner scanner, User currentUser, BaseController controller, AuthController authController) {
        this.scanner = scanner;
        this.currentUser = currentUser;
        this.controller = controller;
        this.authController = authController;
    }

    public abstract void displayMenu();

    protected int getMenuChoice(int min, int max) {
        int choice = -1;
        while (true) {
            System.out.print("Enter your choice: ");
            String input = scanner.nextLine();
            try {
                choice = Integer.parseInt(input);
                if (choice >= min && choice <= max) {
                    break;
                } else {
                    System.out.println("Invalid choice. Please enter a number between " + min + " and " + max + ".");
                }
            } catch (NumberFormatException e) {
                System.out.println("Invalid input. Please enter a number.");
            }
        }
        return choice;
    }

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
         if (newPassword.isEmpty()) {
              System.out.println("Password cannot be empty. Password not changed.");
              return false;
         }
         if (newPassword.equals(oldPassword)) {
              System.out.println("New password cannot be the same as the old password. Password not changed.");
              return false;
         }

         boolean success = authController.changePassword(currentUser, oldPassword, newPassword);
         return success;
     }

     protected void applyFilters() {
         if (controller != null) {
             controller.applyFilters();
         } else {
             System.out.println("Error: Controller not available for filtering.");
         }
     }

     protected void pause() {
          System.out.println("\nPress Enter to continue...");
          scanner.nextLine();
     }
}
