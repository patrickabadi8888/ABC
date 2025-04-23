package Services;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.List;
import java.util.stream.Collectors;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;

public class CsvRW {
    private static final String DATA_DIR = "data"; // Keep consistent
    private static final String DELIMITER = ",";
    // LIST_DELIMITER is handled by LSparse now
    // Headers are now defined in the respective Repositories

    /**
     * Reads a CSV file, skipping the header row.
     * Handles basic CSV quoting for fields containing the delimiter.
     * @param filename The path to the CSV file.
     * @param expectedColumns The number of columns expected per row (used for validation).
     * @return A List of String arrays, where each array represents a row (excluding header).
     */
    public static List<String[]> readCsv(String filename, int expectedColumns) {
        List<String[]> data = new ArrayList<>();
        Path path = Paths.get(filename);

        // Check if file exists, create if not (with appropriate header if possible)
        if (!Files.exists(path)) {
            System.err.println("Warning: File not found - " + filename + ". Attempting to create.");
            try {
                Path parent = path.getParent();
                if (parent != null) {
                    Files.createDirectories(parent); // Ensure data directory exists
                }
                Files.createFile(path);
                // Cannot reliably get header here anymore, Repositories handle headers on save
                System.out.println("Created empty file: " + filename);
                // Write header? No, let the first save operation write the header.
            } catch (IOException e) {
                System.err.println("FATAL: Error creating file: " + filename + " - " + e.getMessage() + ". Application might not function correctly.");
                // Return empty list, subsequent operations might fail
            }
            return data; // Return empty list if file was just created or creation failed
        }

        // Read existing file
        try (BufferedReader br = Files.newBufferedReader(path)) {
            String line;
            boolean isFirstLine = true; // To skip header
            int lineNumber = 0;
            while ((line = br.readLine()) != null) {
                lineNumber++;
                // Skip header row and any blank lines
                if (isFirstLine || line.trim().isEmpty()) {
                    isFirstLine = false;
                    continue;
                }

                // Basic CSV split respecting quotes (may not handle all edge cases)
                String[] values = line.split(DELIMITER + "(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", -1);

                // Trim and unquote values
                for (int i = 0; i < values.length; i++) {
                    values[i] = values[i].trim();
                    // Remove surrounding quotes and unescape double quotes ("")
                    if (values[i].startsWith("\"") && values[i].endsWith("\"")) {
                        values[i] = values[i].substring(1, values[i].length() - 1).replace("\"\"", "\"");
                    }
                }

                // --- Column Count Validation ---
                // Specific handling for ProjectList potentially missing 'Visibility' (column 14, index 13)
                boolean isProjectFile = filename.endsWith("ProjectList.csv"); // Simple check
                if (isProjectFile && values.length == expectedColumns - 1) {
                     // Pad with default visibility "0" (Off) if missing
                     String[] paddedValues = Arrays.copyOf(values, expectedColumns);
                     paddedValues[expectedColumns - 1] = "0"; // Default visibility
                     values = paddedValues;
                     System.out.println("Info: Line " + lineNumber + " in " + filename + " missing 'Visibility'. Assuming '0' (Off).");
                } else if (values.length != expectedColumns) {
                     // General mismatch warning
                     System.err.println("Warning: Malformed line " + lineNumber + " in " + filename + ". Expected " + expectedColumns + " columns, found " + values.length + ". Skipping line: " + line);
                     continue; // Skip this malformed row
                }
                // --- End Validation ---

                data.add(values);
            }
        } catch (IOException e) {
            // Log fatal error if reading fails
            System.err.println("FATAL: Error reading file: " + filename + " - " + e.getMessage());
        }
        return data;
    }

    /**
     * Writes data to a CSV file, overwriting existing content.
     * Automatically quotes fields containing delimiters, quotes, or newlines.
     * @param filename The path to the CSV file.
     * @param data A List of String arrays, where each array represents a row (including header).
     */
    public static void writeCsv(String filename, List<String[]> data) {
        Path path = Paths.get(filename);
        try {
             // Ensure parent directory exists
             Path parent = path.getParent();
             if (parent != null) {
                 Files.createDirectories(parent);
             }

             // Write using try-with-resources for automatic closing
             try (BufferedWriter bw = Files.newBufferedWriter(path, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING)) {
                for (String[] row : data) {
                    // Escape each field and join with delimiter
                    String line = Arrays.stream(row)
                                        .map(CsvRW::escapeCsvField) // Use helper method
                                        .collect(Collectors.joining(DELIMITER));
                    bw.write(line);
                    bw.newLine(); // Add newline character after each row
                }
            }
        } catch (IOException e) {
            // Log error if writing fails
            System.err.println("Error writing file: " + filename + " - " + e.getMessage());
        }
    }

    /**
     * Escapes a string field for CSV output if necessary.
     * Adds surrounding quotes if the field contains the delimiter, double quotes, or newline characters.
     * Escapes existing double quotes within the field by doubling them ("").
     * @param field The string field to escape.
     * @return The escaped string, ready for CSV output.
     */
    private static String escapeCsvField(String field) {
        if (field == null) {
            return ""; // Represent null as empty string in CSV
        }
        // Check if escaping is needed
        if (field.contains(DELIMITER) || field.contains("\"") || field.contains("\n") || field.contains("\r")) {
            // Escape double quotes within the field and add surrounding quotes
            return "\"" + field.replace("\"", "\"\"") + "\"";
        }
        // No escaping needed, return original field
        return field;
    }

    // getHeaderForFile method is removed as headers are now managed by Repositories
}
