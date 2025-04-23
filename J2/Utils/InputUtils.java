package Utils;

import java.util.Date;
import java.util.Scanner;
import Parsers.Dparse; // Assuming Dparse is in Parsers package

public class InputUtils {

    // Make scanner potentially injectable or passed if needed elsewhere,
    // but for simple utility, static methods might be acceptable here.
    // However, passing scanner promotes testability.

    public static int getIntInput(Scanner scanner, String prompt, int min, int max) {
        int value = -1;
        while (true) {
            System.out.print(prompt + " ");
            String input = scanner.nextLine();
            try {
                value = Integer.parseInt(input);
                if (value >= min && value <= max) {
                    break;
                } else {
                    System.out.println("Input must be between " + min + " and " + max + ".");
                }
            } catch (NumberFormatException e) {
                System.out.println("Invalid input. Please enter a whole number.");
            }
        }
        return value;
    }

    public static double getDoubleInput(Scanner scanner, String prompt, double min, double max) {
        double value = -1.0;
        while (true) {
            System.out.print(prompt + " ");
             String input = scanner.nextLine();
            try {
                value = Double.parseDouble(input);
                if (value >= min && value <= max) {
                    break;
                } else {
                    System.out.println("Input must be between " + min + " and " + max + ".");
                }
            } catch (NumberFormatException e) {
                System.out.println("Invalid input. Please enter a number.");
            }
        }
        return value;
    }

    public static Date getDateInput(Scanner scanner, String prompt, boolean allowBlank) {
        Date date = null;
        while (true) {
            System.out.print(prompt + " ");
            String input = scanner.nextLine().trim();
            if (input.isEmpty()) {
                if (allowBlank) {
                    return null; // Return null if blank is allowed
                } else {
                    System.out.println("Input cannot be empty.");
                    continue; // Ask again if blank not allowed
                }
            }
            // Use Dparse for consistent date parsing
            date = Dparse.parseDate(input);
            if (date != null) {
                break; // Valid date parsed
            }
            // Error message is printed by Dparse.parseDate
        }
        return date;
    }

    public static String getStringInput(Scanner scanner, String prompt, boolean allowEmpty) {
         while (true) {
             System.out.print(prompt + " ");
             String input = scanner.nextLine().trim();
             if (!input.isEmpty() || allowEmpty) {
                 return input;
             } else {
                 System.out.println("Input cannot be empty.");
             }
         }
    }

     public static boolean getConfirmation(Scanner scanner, String prompt) {
         while (true) {
             System.out.print(prompt + " (yes/no): ");
             String confirm = scanner.nextLine().trim().toLowerCase();
             if (confirm.equals("yes")) {
                 return true;
             } else if (confirm.equals("no")) {
                 return false;
             } else {
                 System.out.println("Invalid input. Please enter 'yes' or 'no'.");
             }
         }
     }
}
