package Parsers;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

public class LSparse {
    private static final String LIST_DELIMITER = ";";
    public static List<String> parseListString(String listString) {
        if (listString == null || listString.trim().isEmpty()) {
            return new ArrayList<>();
        }
        String effectiveList = listString.trim();
        if (effectiveList.startsWith("\"") && effectiveList.endsWith("\"")) {
            effectiveList = effectiveList.substring(1, effectiveList.length() - 1).replace("\"\"", "\"");
        }
        return Arrays.stream(effectiveList.split(LIST_DELIMITER))
        .map(str -> str.trim())
        
                     .filter(s -> !s.isEmpty())
                     .collect(Collectors.toList());
    }
}
