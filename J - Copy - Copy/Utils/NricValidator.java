/**
 * Utility class for validating the format of Singapore NRIC (National Registration Identity Card) numbers.
 * Uses a regular expression to check the pattern.
 *
 * @author Jordon
 */
package Utils;

import java.util.regex.Pattern;

public class NricValidator {
    private static final Pattern NRIC_PATTERN = Pattern.compile("^[STFG]\\d{7}[A-Z]$");

    public static boolean isValidNric(String nric) {
        return nric == null ? false : NRIC_PATTERN.matcher(nric).matches();
    }
}
