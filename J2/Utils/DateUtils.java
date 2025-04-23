package Utils;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Calendar; // Needed for date manipulation

public class DateUtils {
    // Use the format from Dparse for consistency
    public static final SimpleDateFormat DATE_FORMAT = Parsers.Dparse.DATE_FORMAT;

    public static Date getCurrentDate() {
        // Return a new Date object representing the current moment
        return new Date();
    }

    public static String formatDate(Date date) {
        if (date == null) {
            return ""; // Return empty string for null dates, consistent with CSV saving
        }
        // Ensure lenient is false if needed, though Dparse handles this on parsing
        // DATE_FORMAT.setLenient(false);
        return DATE_FORMAT.format(date);
    }

    // Helper to get the start of the next day, useful for date comparisons
    public static Date getEndOfDay(Date date) {
        if (date == null) return null;
        Calendar cal = Calendar.getInstance();
        cal.setTime(date);
        cal.set(Calendar.HOUR_OF_DAY, 23);
        cal.set(Calendar.MINUTE, 59);
        cal.set(Calendar.SECOND, 59);
        cal.set(Calendar.MILLISECOND, 999);
        // Or more simply for comparison purposes:
        // cal.add(Calendar.DATE, 1);
        // cal.set(Calendar.HOUR_OF_DAY, 0);
        // cal.set(Calendar.MINUTE, 0);
        // cal.set(Calendar.SECOND, 0);
        // cal.set(Calendar.MILLISECOND, 0);
        return cal.getTime();
    }

     // Helper to get the start of the day (00:00:00)
     public static Date getStartOfDay(Date date) {
         if (date == null) return null;
         Calendar cal = Calendar.getInstance();
         cal.setTime(date);
         cal.set(Calendar.HOUR_OF_DAY, 0);
         cal.set(Calendar.MINUTE, 0);
         cal.set(Calendar.SECOND, 0);
         cal.set(Calendar.MILLISECOND, 0);
         return cal.getTime();
     }
}
