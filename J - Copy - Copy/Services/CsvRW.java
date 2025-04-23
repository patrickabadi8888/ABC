package Services;


import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.text.SimpleDateFormat;
import java.util.List;
import java.util.stream.Collectors;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;

// CsvRW remains a static utility class
public class CsvRW {
    // File paths and headers remain defined here for getHeaderForFile logic
    private static final String DATA_DIR = "data";
    private static final String APPLICANT_LIST_FILE = DATA_DIR + File.separator + "ApplicantList.csv";
    private static final String OFFICER_LIST_FILE = DATA_DIR + File.separator + "OfficerList.csv";
    private static final String MANAGER_LIST_FILE = DATA_DIR + File.separator + "ManagerList.csv";
    private static final String PROJECT_FILE = DATA_DIR + File.separator + "ProjectList.csv";
    private static final String APPLICATION_FILE = DATA_DIR + File.separator + "applications.csv";
    private static final String ENQUIRY_FILE = DATA_DIR + File.separator + "enquiries.csv";
    private static final String OFFICER_REGISTRATION_FILE = DATA_DIR + File.separator + "officer_registrations.csv";

    private static final String DELIMITER = ",";
    private static final String LIST_DELIMITER = ";";
    public static final SimpleDateFormat DATE_FORMAT = new SimpleDateFormat("yyyy-MM-dd");

    // Headers are needed internally for file creation logic
    private static final String[] APPLICANT_HEADER = {"Name", "NRIC", "Age", "Marital Status", "Password"};
    private static final String[] OFFICER_HEADER = {"Name", "NRIC", "Age", "Marital Status", "Password"};
    private static final String[] MANAGER_HEADER = {"Name", "NRIC", "Age", "Marital Status", "Password"};
    private static final String[] PROJECT_HEADER = {
        "Project Name", "Neighborhood", "Type 1", "Number of units for Type 1", "Selling price for Type 1",
        "Type 2", "Number of units for Type 2", "Selling price for Type 2",
        "Application opening date", "Application closing date", "Manager", "Officer Slot", "Officer", "Visibility"
    };
    private static final String[] APPLICATION_HEADER = {"ApplicationID", "ApplicantNRIC", "ProjectName", "FlatTypeApplied", "Status", "ApplicationDate"};
    private static final String[] ENQUIRY_HEADER = {"EnquiryID", "ApplicantNRIC", "ProjectName", "EnquiryText", "ReplyText", "RepliedByNRIC", "EnquiryDate", "ReplyDate"};
    private static final String[] OFFICER_REGISTRATION_HEADER = {"RegistrationID", "OfficerNRIC", "ProjectName", "Status", "RegistrationDate"};


    public static List<String[]> readCsv(String filename, int expectedColumns) {
        List<String[]> data = new ArrayList<>();
        Path path = Paths.get(filename);

        if (!Files.exists(path)) {
            System.err.println("Warning: File not found - " + filename + ". Attempting to create.");
            try {
                Path parent = path.getParent();
                if (parent != null) {
                    Files.createDirectories(parent);
                }
                Files.createFile(path);
                String[] header = getHeaderForFile(filename);
                if (header != null) {
                    // Write only the header using the writeCsv method
                    writeCsv(filename, Collections.singletonList(header));
                    System.out.println("Created new file with header: " + filename);
                } else {
                     System.err.println("Could not determine header for new file: " + filename);
                }
            } catch (IOException e) {
                System.err.println("FATAL: Error creating file: " + filename + " - " + e.getMessage() + ". Application might not function correctly.");
            }
            return data; // Return empty list if file was just created or failed to create
        }

        try (BufferedReader br = Files.newBufferedReader(path)) {
            String line;
            boolean isFirstLine = true;
            int lineNumber = 0;
            while ((line = br.readLine()) != null) {
                lineNumber++;
                if (isFirstLine || line.trim().isEmpty()) {
                    isFirstLine = false; // Skip header line
                    continue; // Skip empty lines
                }

                // Regex to handle quoted fields containing delimiters
                String[] values = line.split(DELIMITER + "(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", -1);

                // Trim and unescape quoted values
                for (int i = 0; i < values.length; i++) {
                    values[i] = values[i].trim();
                    // Handle potential quotes properly
                    if (values[i].startsWith("\"") && values[i].endsWith("\"") && values[i].length() >= 2) {
                        values[i] = values[i].substring(1, values[i].length() - 1).replace("\"\"", "\""); // Unescape double quotes
                    }
                }

                // Handle specific case for Project file missing visibility column
                if (values.length < expectedColumns && filename.endsWith(PROJECT_FILE.substring(DATA_DIR.length() + 1)) && values.length == expectedColumns -1) {
                     String[] paddedValues = Arrays.copyOf(values, expectedColumns);
                     paddedValues[expectedColumns - 1] = "0"; // Assume visibility 'Off'
                     values = paddedValues;
                     System.out.println("Info: Line " + lineNumber + " in " + filename + " seems to be missing the 'Visibility' column. Assuming '0' (Off).");
                } else if (values.length != expectedColumns) {
                     System.err.println("Warning: Malformed line " + lineNumber + " in " + filename + ". Expected " + expectedColumns + " columns, found " + values.length + ". Skipping line: " + line);
                     continue; // Skip lines with wrong number of columns
                }

                data.add(values);
            }
        } catch (IOException e) {
            System.err.println("FATAL: Error reading file: " + filename + " - " + e.getMessage());
            // Depending on severity, might want to throw exception or exit
        }
        return data;
    }

    public static void writeCsv(String filename, List<String[]> data) {
        Path path = Paths.get(filename);
        try {
             // Ensure parent directory exists
             Path parent = path.getParent();
             if (parent != null) {
                 Files.createDirectories(parent);
             }

             // Use try-with-resources for BufferedWriter
             // Use TRUNCATE_EXISTING to overwrite the file completely
             try (BufferedWriter bw = Files.newBufferedWriter(path, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING)) {
                for (String[] row : data) {
                    String line = Arrays.stream(row)
                                        .map(CsvRW::escapeCsvField) // Use static method reference
                                        .collect(Collectors.joining(DELIMITER));
                    bw.write(line);
                    bw.newLine(); // Add newline character after each row
                }
            }
        } catch (IOException e) {
            System.err.println("Error writing file: " + filename + " - " + e.getMessage());
             // Depending on severity, might want to throw exception
        }
    }
    // Helper to get header based on filename (relative to DATA_DIR)
    private static String[] getHeaderForFile(String filename) {
        Path p = Paths.get(filename);
        String baseName = p.getFileName().toString();

        // Compare base filenames
        if (baseName.equals(Paths.get(APPLICANT_LIST_FILE).getFileName().toString())) return APPLICANT_HEADER;
        if (baseName.equals(Paths.get(OFFICER_LIST_FILE).getFileName().toString())) return OFFICER_HEADER;
        if (baseName.equals(Paths.get(MANAGER_LIST_FILE).getFileName().toString())) return MANAGER_HEADER;
        if (baseName.equals(Paths.get(PROJECT_FILE).getFileName().toString())) return PROJECT_HEADER;
        if (baseName.equals(Paths.get(APPLICATION_FILE).getFileName().toString())) return APPLICATION_HEADER;
        if (baseName.equals(Paths.get(ENQUIRY_FILE).getFileName().toString())) return ENQUIRY_HEADER;
        if (baseName.equals(Paths.get(OFFICER_REGISTRATION_FILE).getFileName().toString())) return OFFICER_REGISTRATION_HEADER;

        return null; // Unknown file type
    }

    // Helper method to escape fields for CSV writing
    private static String escapeCsvField(String field) {
        if (field == null) return ""; // Represent null as empty string
        // Quote field if it contains delimiter, quote, list delimiter, or newline characters
        if (field.contains(DELIMITER) || field.contains("\"") || field.contains(LIST_DELIMITER) || field.contains("\n") || field.contains("\r")) {
            // Escape existing quotes by doubling them and wrap the whole field in quotes
            return "\"" + field.replace("\"", "\"\"") + "\"";
        }
        // No special characters, return as is
        return field;
    }
}
