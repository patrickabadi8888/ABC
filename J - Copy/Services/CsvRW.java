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

public class CsvRW {
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
                    writeCsv(filename, Collections.singletonList(header));
                    System.out.println("Created new file with header: " + filename);
                } else {
                     System.err.println("Could not determine header for new file: " + filename);
                }
            } catch (IOException e) {
                System.err.println("FATAL: Error creating file: " + filename + " - " + e.getMessage() + ". Application might not function correctly.");
            }
            return data;
        }

        try (BufferedReader br = Files.newBufferedReader(path)) {
            String line;
            boolean isFirstLine = true;
            int lineNumber = 0;
            while ((line = br.readLine()) != null) {
                lineNumber++;
                if (isFirstLine || line.trim().isEmpty()) {
                    isFirstLine = false;
                    continue;
                }

                String[] values = line.split(DELIMITER + "(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", -1);

                for (int i = 0; i < values.length; i++) {
                    values[i] = values[i].trim();
                    if (values[i].startsWith("\"") && values[i].endsWith("\"")) {
                        values[i] = values[i].substring(1, values[i].length() - 1).replace("\"\"", "\"");
                    }
                }

                if (values.length < expectedColumns && filename.equals(PROJECT_FILE) && values.length == expectedColumns -1) {
                     String[] paddedValues = Arrays.copyOf(values, expectedColumns);
                     paddedValues[expectedColumns - 1] = "0";
                     values = paddedValues;
                     System.out.println("Info: Line " + lineNumber + " in " + filename + " seems to be missing the 'Visibility' column. Assuming '0' (Off).");
                } else if (values.length != expectedColumns) {
                     System.err.println("Warning: Malformed line " + lineNumber + " in " + filename + ". Expected " + expectedColumns + " columns, found " + values.length + ". Skipping line: " + line);
                     continue;
                }

                data.add(values);
            }
        } catch (IOException e) {
            System.err.println("FATAL: Error reading file: " + filename + " - " + e.getMessage());
        }
        return data;
    }

    public static void writeCsv(String filename, List<String[]> data) {
        Path path = Paths.get(filename);
        try {
             Path parent = path.getParent();
             if (parent != null) {
                 Files.createDirectories(parent);
             }

             try (BufferedWriter bw = Files.newBufferedWriter(path, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING)) {
                for (String[] row : data) {
                    String line = Arrays.stream(row)
                                        .map(field -> CsvRW.escapeCsvField(field))
                                        .collect(Collectors.joining(DELIMITER));
                    bw.write(line);
                    bw.newLine();
                }
            }
        } catch (IOException e) {
            System.err.println("Error writing file: " + filename + " - " + e.getMessage());
        }
    }
    private static String[] getHeaderForFile(String filename) {
        Path p = Paths.get(filename);
        String baseName = p.getFileName().toString();

        if (baseName.equals(APPLICANT_LIST_FILE)) return APPLICANT_HEADER;
        if (baseName.equals(OFFICER_LIST_FILE)) return OFFICER_HEADER;
        if (baseName.equals(MANAGER_LIST_FILE)) return MANAGER_HEADER;
        if (baseName.equals(PROJECT_FILE)) return PROJECT_HEADER;
        if (baseName.equals(APPLICATION_FILE)) return APPLICATION_HEADER;
        if (baseName.equals(ENQUIRY_FILE)) return ENQUIRY_HEADER;
        if (baseName.equals(OFFICER_REGISTRATION_FILE)) return OFFICER_REGISTRATION_HEADER;
        return null;
    }

    private static String escapeCsvField(String field) {
        if (field == null) return "";
        if (field.contains(DELIMITER) || field.contains("\"") || field.contains(LIST_DELIMITER) || field.contains("\n") || field.contains("\r")) {
            return "\"" + field.replace("\"", "\"\"") + "\"";
        }
        return field;
    }
}
