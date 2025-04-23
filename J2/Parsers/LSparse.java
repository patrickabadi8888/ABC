package Parsers;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

public class LSparse {
    // Delimiter used within a single CSV field to represent a list
    private static final String LIST_DELIMITER = ";";

    /**
     * Parses a string containing a delimited list into a List of strings.
     * Handles quoted strings containing the delimiter.
     * @param listString The string representation of the list (e.g., "item1;item2;\"item3;with;delimiter\"").
     * @return A List of strings, or an empty list if the input is null or empty.
     */
    public static List<String> parseListString(String listString) {
        if (listString == null || listString.trim().isEmpty()) {
            return new ArrayList<>(); // Return empty list for null/empty input
        }

        String effectiveList = listString.trim();

        // Basic handling for CSV quoting (remove surrounding quotes if present)
        // This assumes the *entire* list field might be quoted if it contains delimiters/quotes.
        // More robust CSV parsing would handle quotes around individual items if needed.
        if (effectiveList.startsWith("\"") && effectiveList.endsWith("\"")) {
            // Remove surrounding quotes and unescape double quotes ("") inside
            effectiveList = effectiveList.substring(1, effectiveList.length() - 1).replace("\"\"", "\"");
        }

        // Split by the delimiter, trim each part, and filter out empty strings
        return Arrays.stream(effectiveList.split(LIST_DELIMITER))
                     .map(String::trim) // Trim whitespace from each potential item
                     .filter(s -> !s.isEmpty()) // Remove any empty items resulting from split (e.g., ";;")
                     .collect(Collectors.toList());
    }
}
