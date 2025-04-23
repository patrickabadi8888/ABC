/**
 * Utility class for common date-related operations.
 * Provides methods for getting the current date and formatting dates into strings.
 *
 * @author Jordon
 */
package Utils;

import java.text.SimpleDateFormat;
import java.util.Date;

public class DateUtils {
    public static final SimpleDateFormat DATE_FORMAT = new SimpleDateFormat("yyyy-MM-dd");
    
    public static Date getCurrentDate() {
        return new Date();
    }

    public static String formatDate(Date date) {
        if (date == null) {
            return "";
        }
        DATE_FORMAT.setLenient(false);
        return DATE_FORMAT.format(date);
    }
}
