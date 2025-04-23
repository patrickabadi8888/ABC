package Utils;

import java.util.regex.Pattern;

public class NricValidator {
    private static final Pattern NRIC_PATTERN = Pattern.compile("^[STFG]\\d{7}[A-Z]$");
    public static boolean isValidNric(String var0) {
        return var0 == null ? false : NRIC_PATTERN.matcher(var0).matches();
     }
}
