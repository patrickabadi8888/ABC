package Utils;

import java.util.regex.Pattern;

public class NricValidator {
    // Singapore NRIC pattern: Starts with S, T, F, or G, followed by 7 digits, ends with an uppercase letter.
    private static final Pattern NRIC_PATTERN = Pattern.compile("^[STFG]\\d{7}[A-Z]$", Pattern.CASE_INSENSITIVE); // Allow lowercase input but match uppercase internally

    /**
     * Validates an NRIC string.
     * @param nric The NRIC string to validate.
     * @return true if the format is valid, false otherwise.
     */
    public static boolean isValidNric(String nric) {
        // Check for null or empty string first
        if (nric == null || nric.trim().isEmpty()) {
            return false;
        }
        // Match against the pattern (case-insensitive due to flag, but usually stored uppercase)
        return NRIC_PATTERN.matcher(nric.trim()).matches();
     }
}
