package Repositories;

import java.io.File;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import Enums.FlatType;
import Interfaces.Repositories.IProjectRepository;
import Models.FlatTypeDetails;
import Models.Project;
import Parsers.Dparse;
import Parsers.LSparse;
import Services.CsvRW; // Assuming CsvRW is in Services package
import Utils.DateUtils;

public class CsvProjectRepository implements IProjectRepository {
    private static final String DELIMITER = ",";
    private static final String DATA_DIR = "data";
    private static final String LIST_DELIMITER = ";"; // Used within Officer list column
    private static final String[] PROJECT_HEADER = {
        "Project Name", "Neighborhood", "Type 1", "Number of units for Type 1", "Selling price for Type 1",
        "Type 2", "Number of units for Type 2", "Selling price for Type 2",
        "Application opening date", "Application closing date", "Manager", "Officer Slot", "Officer", "Visibility"
    };
    private static final String PROJECT_FILE = DATA_DIR + File.separator + "ProjectList.csv";

    private List<Project> projectsCache;

    public CsvProjectRepository() {
        this.projectsCache = null; // Load on demand
    }

    @Override
    public List<Project> loadProjects() {
        if (this.projectsCache != null) {
            return new ArrayList<>(this.projectsCache); // Return copy
        }

        List<Project> loadedProjects = new ArrayList<>();
        Set<String> projectNames = new HashSet<>(); // For duplicate name check
        List<String[]> rawData = CsvRW.readCsv(PROJECT_FILE, PROJECT_HEADER.length);

        for (String[] data : rawData) {
            try {
                String projectName = data[0].trim();
                if (projectName.isEmpty() || !projectNames.add(projectName.toLowerCase())) {
                     if (!projectName.isEmpty()) System.err.println("Skipping duplicate project name in CSV: " + projectName);
                    continue;
                }

                String neighborhood = data[1].trim();
                Map<FlatType, FlatTypeDetails> flatTypes = new HashMap<>();

                // Parse Flat Type 1
                if (data[2] != null && !data[2].trim().isEmpty()) {
                    FlatType type1 = FlatType.fromString(data[2].trim());
                    if (type1 != null) {
                        int units1 = Integer.parseInt(data[3].trim());
                        double price1 = Double.parseDouble(data[4].trim());
                        // Available units will be adjusted later by ApplicationService based on booked apps
                        flatTypes.put(type1, new FlatTypeDetails(units1, units1, price1));
                    } else {
                         System.err.println("Warning: Unknown flat type '" + data[2] + "' in project '" + projectName + "'. Skipping type.");
                    }
                }

                // Parse Flat Type 2
                 if (data[5] != null && !data[5].trim().isEmpty()) {
                    FlatType type2 = FlatType.fromString(data[5].trim());
                     if (type2 != null) {
                        int units2 = Integer.parseInt(data[6].trim());
                        double price2 = Double.parseDouble(data[7].trim());
                        // Available units will be adjusted later by ApplicationService based on booked apps
                        flatTypes.put(type2, new FlatTypeDetails(units2, units2, price2));
                     } else {
                          System.err.println("Warning: Unknown flat type '" + data[5] + "' in project '" + projectName + "'. Skipping type.");
                     }
                }

                Date openingDate = Dparse.parseDate(data[8].trim());
                Date closingDate = Dparse.parseDate(data[9].trim());
                String managerNric = data[10].trim();
                int officerSlots = Integer.parseInt(data[11].trim());

                // Parse Officer List using LSparse
                List<String> officers = LSparse.parseListString(data[12]);

                boolean visibility = false;
                if (data.length > 13 && data[13] != null) {
                     String visibilityStr = data[13].trim();
                     if (visibilityStr.equals("1")) {
                         visibility = true;
                     } else if (!visibilityStr.equals("0") && !visibilityStr.isEmpty()) {
                         System.err.println("Warning: Invalid visibility value '" + visibilityStr + "' for project '" + projectName + "'. Assuming false.");
                     }
                }

                // Basic Validation (deeper validation in DataSyncService)
                if (managerNric.isEmpty()) {
                    System.err.println("Warning: Project '" + projectName + "' has missing manager NRIC. Skipping project.");
                    projectNames.remove(projectName.toLowerCase()); // Remove from set if skipped
                    continue;
                }
                 if (openingDate == null || closingDate == null || closingDate.before(openingDate)) {
                     System.err.println("Warning: Project '" + projectName + "' has invalid application dates (Open: " + data[8] + ", Close: " + data[9] + "). Skipping project.");
                     projectNames.remove(projectName.toLowerCase()); // Remove from set if skipped
                     continue;
                 }
                 if (flatTypes.isEmpty()) {
                     System.err.println("Warning: Project '" + projectName + "' has no valid flat types defined. Skipping project.");
                     projectNames.remove(projectName.toLowerCase()); // Remove from set if skipped
                     continue;
                 }

                // Note: Validation of manager/officer NRICs existence and roles happens in DataSyncService
                // Note: Validation of officer count vs slots happens in DataSyncService

                Project project = new Project(projectName, neighborhood, flatTypes, openingDate, closingDate, managerNric, officerSlots, officers, visibility);
                loadedProjects.add(project);

            } catch (NumberFormatException e) {
                System.err.println("Error parsing number in project data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            } catch (IllegalArgumentException e) {
                System.err.println("Error parsing enum/data in project data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            } catch (Exception e) {
                 System.err.println("Unexpected error parsing project data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
                 e.printStackTrace(); // Print stack trace for unexpected errors
            }
        }
        this.projectsCache = loadedProjects;
        System.out.println("Loaded " + this.projectsCache.size() + " projects from CSV.");
        return new ArrayList<>(this.projectsCache); // Return copy
    }

    @Override
    public void saveProjects(List<Project> projectsToSave) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(PROJECT_HEADER);

        projectsToSave.stream()
            .sorted(Comparator.comparing(Project::getProjectName))
            .forEach(project -> {
                String[] data = new String[PROJECT_HEADER.length];
                data[0] = project.getProjectName();
                data[1] = project.getNeighborhood();

                // Handle flat types systematically
                FlatTypeDetails twoRoomDetails = project.getFlatTypeDetails(FlatType.TWO_ROOM);
                FlatTypeDetails threeRoomDetails = project.getFlatTypeDetails(FlatType.THREE_ROOM);

                // Type 1 (Assume 2-Room if present, else 3-Room if present, else empty)
                FlatType type1 = null;
                FlatTypeDetails details1 = null;
                if (twoRoomDetails != null) {
                    type1 = FlatType.TWO_ROOM;
                    details1 = twoRoomDetails;
                } else if (threeRoomDetails != null) {
                    type1 = FlatType.THREE_ROOM;
                    details1 = threeRoomDetails;
                }

                if (details1 != null && type1 != null) {
                    data[2] = type1.getDisplayName(); // Save display name
                    data[3] = String.valueOf(details1.getTotalUnits());
                    data[4] = String.format("%.2f", details1.getSellingPrice()); // Format price
                } else {
                    data[2] = ""; data[3] = "0"; data[4] = "0.00";
                }

                // Type 2 (Assume 3-Room if present AND different from Type 1, else empty)
                 FlatType type2 = null;
                 FlatTypeDetails details2 = null;
                 if (threeRoomDetails != null && type1 != FlatType.THREE_ROOM) {
                     type2 = FlatType.THREE_ROOM;
                     details2 = threeRoomDetails;
                 }

                if (details2 != null && type2 != null) {
                    data[5] = type2.getDisplayName(); // Save display name
                    data[6] = String.valueOf(details2.getTotalUnits());
                    data[7] = String.format("%.2f", details2.getSellingPrice()); // Format price
                } else {
                    data[5] = ""; data[6] = "0"; data[7] = "0.00";
                }


                data[8] = DateUtils.formatDate(project.getApplicationOpeningDate());
                data[9] = DateUtils.formatDate(project.getApplicationClosingDate());
                data[10] = project.getManagerNric();
                data[11] = String.valueOf(project.getMaxOfficerSlots());

                // Join officer list using the correct delimiter
                String officers = project.getApprovedOfficerNrics().stream()
                                        .collect(Collectors.joining(LIST_DELIMITER));
                data[12] = officers;

                data[13] = project.isVisible() ? "1" : "0";

                dataList.add(data);
        });
        CsvRW.writeCsv(PROJECT_FILE, dataList);
        this.projectsCache = new ArrayList<>(projectsToSave); // Update cache
        System.out.println("Saved " + projectsToSave.size() + " projects to CSV.");
    }

     @Override
     public List<Project> getAllProjects() {
         if (this.projectsCache == null) {
             loadProjects();
         }
         // Return a defensive copy
         return new ArrayList<>(this.projectsCache);
     }

     @Override
     public Project findProjectByName(String name) {
         if (name == null || name.trim().isEmpty()) return null;
         String trimmedName = name.trim();
         return getAllProjects().stream() // Use cached data via getAllProjects()
                 .filter(p -> p.getProjectName().equalsIgnoreCase(trimmedName))
                 .findFirst()
                 .orElse(null);
     }
}
