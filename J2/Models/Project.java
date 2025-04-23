package Models;

import Enums.FlatType;
import Utils.DateUtils; // For date comparisons

import java.util.ArrayList;
import java.util.Calendar;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

public class Project {
    private String projectName; // Can be set via setter? No, should be final identifier? Let's make it final.
    private final String projectNameIdentifier; // Use this for equality/hashcode
    private String neighborhood; // Mutable
    private Map<FlatType, FlatTypeDetails> flatTypes; // Mutable map content
    private Date applicationOpeningDate; // Mutable
    private Date applicationClosingDate; // Mutable
    private final String managerNric; // Final
    private int maxOfficerSlots; // Mutable
    private List<String> approvedOfficerNrics; // Mutable list content
    private boolean visibility; // Mutable

    public Project(String projectName, String neighborhood, Map<FlatType, FlatTypeDetails> flatTypes,
                   Date applicationOpeningDate, Date applicationClosingDate, String managerNric,
                   int maxOfficerSlots, List<String> approvedOfficerNrics, boolean visibility) {

        // --- Input Validation ---
        Objects.requireNonNull(projectName, "Project Name cannot be null");
        Objects.requireNonNull(neighborhood, "Neighborhood cannot be null");
        Objects.requireNonNull(flatTypes, "Flat Types map cannot be null");
        Objects.requireNonNull(applicationOpeningDate, "Application Opening Date cannot be null");
        Objects.requireNonNull(applicationClosingDate, "Application Closing Date cannot be null");
        Objects.requireNonNull(managerNric, "Manager NRIC cannot be null");

        if (projectName.trim().isEmpty()) throw new IllegalArgumentException("Project name cannot be empty");
        if (neighborhood.trim().isEmpty()) throw new IllegalArgumentException("Neighborhood cannot be empty");
        if (flatTypes.isEmpty()) throw new IllegalArgumentException("Project must have at least one flat type");
        if (managerNric.trim().isEmpty()) throw new IllegalArgumentException("Manager NRIC cannot be empty");
        if (maxOfficerSlots < 0) throw new IllegalArgumentException("Max officer slots cannot be negative");
        if (applicationClosingDate.before(applicationOpeningDate)) {
             throw new IllegalArgumentException("Project closing date cannot be before opening date.");
        }
        // --- End Validation ---

        this.projectNameIdentifier = projectName.trim();
        this.projectName = projectName.trim(); // Store trimmed version
        this.neighborhood = neighborhood.trim();
        // Create a deep copy of the flat types map to ensure internal state is not modified externally
        this.flatTypes = flatTypes.entrySet().stream()
                .collect(Collectors.toMap(
                        Map.Entry::getKey,
                        e -> new FlatTypeDetails(e.getValue().getTotalUnits(), e.getValue().getAvailableUnits(), e.getValue().getSellingPrice()),
                        (v1, v2) -> v1, // Merge function (shouldn't be needed with distinct FlatType keys)
                        HashMap::new
                ));
        this.applicationOpeningDate = applicationOpeningDate;
        this.applicationClosingDate = applicationClosingDate;
        this.managerNric = managerNric;
        // Ensure approved officers list is not null and doesn't exceed max slots initially
        List<String> initialOfficers = (approvedOfficerNrics != null) ? new ArrayList<>(approvedOfficerNrics) : new ArrayList<>();
        if (initialOfficers.size() > maxOfficerSlots) {
             System.err.println("Warning: Initial approved officers (" + initialOfficers.size() + ") exceed max slots (" + maxOfficerSlots + ") for project " + projectName + ". Truncating list.");
             this.approvedOfficerNrics = initialOfficers.subList(0, maxOfficerSlots);
        } else {
             this.approvedOfficerNrics = initialOfficers;
        }
        this.maxOfficerSlots = maxOfficerSlots; // Set max slots *after* potentially truncating list
        this.visibility = visibility;
    }

    // --- Getters ---
    public String getProjectName() { return projectName; }
    public String getNeighborhood() { return neighborhood; }
    // Return an unmodifiable view of the map to prevent external modification
    public Map<FlatType, FlatTypeDetails> getFlatTypes() { return Collections.unmodifiableMap(flatTypes); }
    public Date getApplicationOpeningDate() { return applicationOpeningDate; }
    public Date getApplicationClosingDate() { return applicationClosingDate; }
    public String getManagerNric() { return managerNric; }
    public int getMaxOfficerSlots() { return maxOfficerSlots; }
    // Return an unmodifiable view of the list
    public List<String> getApprovedOfficerNrics() { return Collections.unmodifiableList(approvedOfficerNrics); }
    public boolean isVisible() { return visibility; }
    public int getRemainingOfficerSlots() { return Math.max(0, maxOfficerSlots - approvedOfficerNrics.size()); }

    // --- Setters with Validation ---

    // Project Name is identifier, should not be changed after creation.
    // public void setProjectName(String projectName) { ... }

    public void setNeighborhood(String neighborhood) {
         Objects.requireNonNull(neighborhood, "Neighborhood cannot be null");
         if (neighborhood.trim().isEmpty()) throw new IllegalArgumentException("Neighborhood cannot be empty");
         this.neighborhood = neighborhood.trim();
    }

    public void setFlatTypes(Map<FlatType, FlatTypeDetails> newFlatTypes) {
        Objects.requireNonNull(newFlatTypes, "Flat Types map cannot be null");
        if (newFlatTypes.isEmpty()) throw new IllegalArgumentException("Project must have at least one flat type");
        // Create a deep copy again
        this.flatTypes = newFlatTypes.entrySet().stream()
                .collect(Collectors.toMap(
                        Map.Entry::getKey,
                        e -> new FlatTypeDetails(e.getValue().getTotalUnits(), e.getValue().getAvailableUnits(), e.getValue().getSellingPrice()),
                        (v1, v2) -> v1,
                        HashMap::new
                ));
    }

    public void setApplicationOpeningDate(Date applicationOpeningDate) {
        Objects.requireNonNull(applicationOpeningDate, "Application Opening Date cannot be null");
        // Ensure new opening date is not after the current closing date
        if (this.applicationClosingDate != null && applicationOpeningDate.after(this.applicationClosingDate)) {
             System.err.println("Warning: New opening date cannot be after the current closing date. Date not updated.");
             // Or throw new IllegalArgumentException("Opening date cannot be after closing date.");
             return;
        }
        this.applicationOpeningDate = applicationOpeningDate;
    }

    public void setApplicationClosingDate(Date applicationClosingDate) {
         Objects.requireNonNull(applicationClosingDate, "Application Closing Date cannot be null");
         // Ensure new closing date is not before the current opening date
         if (this.applicationOpeningDate != null && applicationClosingDate.before(this.applicationOpeningDate)) {
             System.err.println("Warning: Closing date cannot be before opening date. Date not updated.");
             // Or throw new IllegalArgumentException("Closing date cannot be before opening date.");
             return;
         }
         this.applicationClosingDate = applicationClosingDate;
    }

    /**
     * Sets the maximum number of officer slots. Cannot be set below the current
     * number of approved officers.
     * @param maxOfficerSlots The new maximum number of slots (must be >= 0).
     * @return true if the value was set, false otherwise.
     */
    public boolean setMaxOfficerSlots(int maxOfficerSlots) {
        if (maxOfficerSlots < 0) {
             System.err.println("Warning: Max officer slots cannot be negative. Value not changed.");
             return false;
        }
        if (maxOfficerSlots < this.approvedOfficerNrics.size()) {
            System.err.println("Warning: Cannot set max officer slots ("+ maxOfficerSlots +") below current approved count (" + this.approvedOfficerNrics.size() + "). Value not changed.");
            return false;
        }
        this.maxOfficerSlots = maxOfficerSlots;
        return true;
    }

    public void setVisibility(boolean visibility) { this.visibility = visibility; }

    // --- List Management Methods ---

    /**
     * Adds an officer NRIC to the list of approved officers if slots are available
     * and the officer is not already approved.
     * @param officerNric The NRIC of the officer to add.
     * @return true if the officer was successfully added, false otherwise.
     */
    public boolean addApprovedOfficer(String officerNric) {
        Objects.requireNonNull(officerNric, "Officer NRIC cannot be null");
        if (officerNric.trim().isEmpty()) return false; // Cannot add empty NRIC

        if (getRemainingOfficerSlots() > 0 && !approvedOfficerNrics.contains(officerNric.trim())) {
            approvedOfficerNrics.add(officerNric.trim());
            return true;
        } else if (approvedOfficerNrics.contains(officerNric.trim())) {
             System.err.println("Info: Officer " + officerNric + " is already approved for project " + this.projectName);
             return false; // Or return true if already present is considered success? Let's say false.
        } else { // No remaining slots
             System.err.println("Warning: No remaining officer slots to add " + officerNric + " to project " + this.projectName);
             return false;
        }
    }

    /**
     * Removes an officer NRIC from the list of approved officers.
     * @param officerNric The NRIC of the officer to remove.
     * @return true if the officer was found and removed, false otherwise.
     */
    public boolean removeApprovedOfficer(String officerNric) {
        if (officerNric == null) return false;
        return approvedOfficerNrics.remove(officerNric.trim());
    }

    // Internal method for synchronization service to bypass unmodifiable list
    // Use with caution!
    puvlix void internal_setApprovedOfficers(List<String> officers) {
         this.approvedOfficerNrics = new ArrayList<>(officers);
    }


    // --- State Check Methods ---

    /**
     * Checks if the project's application period is currently active based on the provided date.
     * The period includes the opening date and the closing date.
     * @param currentDate The date to check against.
     * @return true if the application period is active, false otherwise.
     */
    public boolean isApplicationPeriodActive(Date currentDate) {
        if (currentDate == null || applicationOpeningDate == null || applicationClosingDate == null) return false;

        // Normalize dates to avoid time-of-day issues if necessary, or compare directly.
        // Let's compare directly: Active if currentDate >= openingDate AND currentDate <= closingDate (inclusive)
        // To make closingDate inclusive, we check if currentDate is *not after* the end of the closing day.
        Date startOfDayOpening = DateUtils.getStartOfDay(applicationOpeningDate);
        Date endOfDayClosing = DateUtils.getEndOfDay(applicationClosingDate); // Get 23:59:59... of closing day

        return !currentDate.before(startOfDayOpening) && !currentDate.after(endOfDayClosing);
    }

    /**
     * Checks if the project's application period has expired based on the provided date.
     * @param currentDate The date to check against.
     * @return true if the application period has expired, false otherwise.
     */
    public boolean isApplicationPeriodExpired(Date currentDate) {
         if (currentDate == null || applicationClosingDate == null) return false; // Cannot be expired if no closing date or current date
         Date endOfDayClosing = DateUtils.getEndOfDay(applicationClosingDate);
         return currentDate.after(endOfDayClosing);
    }

    // --- Flat Type Details Access ---

    /**
     * Gets the details for a specific flat type.
     * @param type The FlatType enum.
     * @return The FlatTypeDetails object, or null if the type doesn't exist in this project.
     */
    public FlatTypeDetails getFlatTypeDetails(FlatType type) {
        // Returns the actual object, but since the map is internal, it's okay.
        // If we returned the unmodifiable map's value, it would still be the same object.
        return flatTypes.get(type);
    }

    /**
     * Gets a *mutable* reference to the FlatTypeDetails for a specific type.
     * Use with caution, intended for services that need to modify unit counts (e.g., ApplicationService).
     * @param type The FlatType enum.
     * @return The mutable FlatTypeDetails object, or null if the type doesn't exist.
     */
    public FlatTypeDetails getMutableFlatTypeDetails(FlatType type) {
        return flatTypes.get(type);
    }

    // --- Standard overrides ---
     @Override
     public boolean equals(Object o) {
         if (this == o) return true;
         if (o == null || getClass() != o.getClass()) return false;
         Project project = (Project) o;
         // Equality based on the unique project name identifier
         return projectNameIdentifier.equals(project.projectNameIdentifier);
     }

     @Override
     public int hashCode() {
         return Objects.hash(projectNameIdentifier);
     }

     @Override
     public String toString() {
         return "Project{" +
                 "projectName='" + projectName + '\'' +
                 ", neighborhood='" + neighborhood + '\'' +
                 ", openingDate=" + DateUtils.formatDate(applicationOpeningDate) +
                 ", closingDate=" + DateUtils.formatDate(applicationClosingDate) +
                 ", visibility=" + visibility +
                 '}';
     }
}
