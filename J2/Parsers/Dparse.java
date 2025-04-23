package Parsers;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;

public class Dparse {
    // Make format public for use by DateUtils and Repositories
    public static final SimpleDateFormat DATE_FORMAT = new SimpleDateFormat("yyyy-MM-dd");

    static {
        // Set lenient to false globally for this format instance
        DATE_FORMAT.setLenient(false);
    }

    /**
     * Parses a date string in "yyyy-MM-dd" format.
     * @param dateString The string to parse.
     * @return The parsed Date object, or null if the string is null, empty, "null", or invalid format.
     */
    public static Date parseDate(String dateString) {
        if (dateString == null || dateString.trim().isEmpty() || dateString.trim().equalsIgnoreCase("null")) {
            return null;
        }
        try {
            // Lenient is already set to false
            return DATE_FORMAT.parse(dateString.trim());
        } catch (ParseException e) {
            // Log the error for debugging purposes
            System.err.println("Warning: Invalid date format encountered: '" + dateString + "'. Expected yyyy-MM-dd.");
            return null; // Return null for invalid format
        }
    }
}
