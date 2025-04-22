import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

// ==================
// Enums (Added PENDING_WITHDRAWAL to ApplicationStatus)
// ==================

enum MaritalStatus {
    SINGLE, MARRIED
}

enum FlatType {
    TWO_ROOM("2-Room"), THREE_ROOM("3-Room");

    private final String displayName;

    FlatType(String displayName) {
        this.displayName = displayName;
    }

    public String getDisplayName() {
        return displayName;
    }

    public static FlatType fromDisplayName(String displayName) {
        for (FlatType type : FlatType.values()) {
            if (type.displayName.equalsIgnoreCase(displayName)) {
                return type;
            }
        }
        throw new IllegalArgumentException("Unknown flat type display name: " + displayName);
    }

    // Helper to convert string (name or display name) to enum
    public static FlatType fromString(String text) {
        if (text != null) {
            for (FlatType b : FlatType.values()) {
                // Check both enum constant name and display name, case-insensitive
                if (text.trim().equalsIgnoreCase(b.name()) || text.trim().equalsIgnoreCase(b.displayName)) {
                    return b;
                }
            }
            // Handle specific string representations if needed
            if ("2-Room".equalsIgnoreCase(text.trim())) return TWO_ROOM;
            if ("3-Room".equalsIgnoreCase(text.trim())) return THREE_ROOM;
        }
        // Consider throwing an exception if the text is non-null but doesn't match
        // throw new IllegalArgumentException("Cannot parse FlatType from string: " + text);
        return null; // Or return null if appropriate for the context (e.g., loading optional data)
    }
}

enum ApplicationStatus {
    PENDING,          // Initial state
    SUCCESSFUL,       // Manager approved, applicant can book
    UNSUCCESSFUL,     // Manager rejected, or withdrawal approved after SUCCESSFUL/BOOKED
    BOOKED,           // Officer confirmed booking
    PENDING_WITHDRAWAL, // Applicant requested withdrawal, awaiting Manager action
    WITHDRAWN         // Manager approved withdrawal from PENDING state
}

enum OfficerRegistrationStatus {
    PENDING, APPROVED, REJECTED
}

enum UserRole {
    APPLICANT, HDB_OFFICER, HDB_MANAGER
}

// ==================
// Models (Data Holders - SRP)
// ==================

// --- User Hierarchy ---
abstract class User {
    // Using private fields with public getters enforces encapsulation
    private final String nric; // NRIC is immutable
    private String password;
    private final String name; // Name is immutable
    private final int age; // Age is immutable (at time of creation/load)
    private final MaritalStatus maritalStatus; // Marital status is immutable

    // Constructor validates basic non-nullness
    public User(String nric, String password, String name, int age, MaritalStatus maritalStatus) {
        if (nric == null || password == null || name == null || maritalStatus == null) {
            throw new IllegalArgumentException("User fields cannot be null");
        }
        // Basic validation could go here, but keep it minimal for SRP
        this.nric = nric;
        this.password = password;
        this.name = name;
        this.age = age;
        this.maritalStatus = maritalStatus;
    }

    // Getters provide controlled access
    public String getNric() { return nric; }
    public String getPassword() { return password; }
    public String getName() { return name; }
    public int getAge() { return age; }
    public MaritalStatus getMaritalStatus() { return maritalStatus; }

    // Setter only for mutable fields (password)
    public void setPassword(String password) {
        if (password != null && !password.isEmpty()) {
            this.password = password;
        } else {
            System.err.println("Warning: Attempted to set null or empty password for NRIC: " + nric);
        }
    }

    // Abstract method to enforce role definition in subclasses
    public abstract UserRole getRole();

    // Override equals and hashCode for proper collection handling
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        User user = (User) o;
        return nric.equals(user.nric);
    }

    @Override
    public int hashCode() {
        return Objects.hash(nric);
    }

    @Override
    public String toString() {
        return "User{" +
               "nric='" + nric + '\'' +
               ", name='" + name + '\'' +
               ", age=" + age +
               ", maritalStatus=" + maritalStatus +
               ", role=" + getRole() +
               '}';
    }
}

class Applicant extends User {
    // State specific to an applicant's interaction with BTO applications
    // This state should be considered potentially stale and synced from BTOApplication records on load/access
    private String appliedProjectName; // Track the project applied for
    private ApplicationStatus applicationStatus; // Track status for the applied project
    private FlatType bookedFlatType; // Track booked flat type if status is BOOKED

    public Applicant(String nric, String password, String name, int age, MaritalStatus maritalStatus) {
        super(nric, password, name, age, maritalStatus);
        this.applicationStatus = null; // Initially no application
        this.appliedProjectName = null;
        this.bookedFlatType = null;
    }

    @Override
    public UserRole getRole() { return UserRole.APPLICANT; }

    // Getters and Setters specific to Applicant state (used by sync logic primarily)
    public String getAppliedProjectName() { return appliedProjectName; }
    public void setAppliedProjectName(String appliedProjectName) { this.appliedProjectName = appliedProjectName; }

    public ApplicationStatus getApplicationStatus() { return applicationStatus; }
    public void setApplicationStatus(ApplicationStatus applicationStatus) { this.applicationStatus = applicationStatus; }

    public FlatType getBookedFlatType() { return bookedFlatType; }
    public void setBookedFlatType(FlatType bookedFlatType) { this.bookedFlatType = bookedFlatType; }

    // Convenience methods to check state
    public boolean hasActiveApplication() {
        // An applicant has an "active" application if status is PENDING or SUCCESSFUL
        // PENDING_WITHDRAWAL is NOT considered active for purposes of applying again.
        return this.applicationStatus == ApplicationStatus.PENDING ||
               this.applicationStatus == ApplicationStatus.SUCCESSFUL;
    }

     public boolean hasPendingWithdrawal() {
        return this.applicationStatus == ApplicationStatus.PENDING_WITHDRAWAL;
    }


    public boolean hasBooked() {
        return this.applicationStatus == ApplicationStatus.BOOKED && this.bookedFlatType != null;
    }

    // Reset application state, e.g., after withdrawal or rejection
    public void clearApplicationState() {
        this.appliedProjectName = null;
        this.applicationStatus = null;
        this.bookedFlatType = null;
    }
}

// HDBOfficer IS-A Applicant (can do everything an Applicant can) + Officer duties
class HDBOfficer extends Applicant {
    // Officer registration details are stored separately in OfficerRegistration objects
    // The concept of "handlingProjectName" is derived from APPROVED registrations during sync/runtime checks
    // We don't store it directly on the officer object to avoid sync issues.

    public HDBOfficer(String nric, String password, String name, int age, MaritalStatus maritalStatus) {
        super(nric, password, name, age, maritalStatus);
    }

    @Override
    public UserRole getRole() { return UserRole.HDB_OFFICER; }

    // Method to get the project currently being handled (based on APPROVED registrations)
    // This requires access to the registrations map, so it's better placed in the Controller or DataService sync logic.
    // public String getHandlingProjectName(Map<String, OfficerRegistration> registrations) { ... }
}

// HDBManager IS-A User, but CANNOT be an Applicant
class HDBManager extends User {
    // Manager specific state, if any (e.g., list of projects they manage directly)
    // Currently, managed projects are identified by Project.managerNric

    public HDBManager(String nric, String password, String name, int age, MaritalStatus maritalStatus) {
        super(nric, password, name, age, maritalStatus);
    }

    @Override
    public UserRole getRole() { return UserRole.HDB_MANAGER; }

    // Managers cannot apply for BTOs, so no application-related fields/methods needed here.
}

// --- Project Details ---
class FlatTypeDetails {
    private final int totalUnits; // Total units are fixed once set
    private int availableUnits;
    private double sellingPrice; // Price can potentially be edited by Manager

    public FlatTypeDetails(int totalUnits, int availableUnits, double sellingPrice) {
        if (totalUnits < 0 || availableUnits < 0 || availableUnits > totalUnits || sellingPrice < 0) {
            throw new IllegalArgumentException("Invalid FlatTypeDetails parameters: total=" + totalUnits + ", available=" + availableUnits + ", price=" + sellingPrice);
        }
        this.totalUnits = totalUnits;
        this.availableUnits = availableUnits;
        this.sellingPrice = sellingPrice;
    }

    // Getters
    public int getTotalUnits() { return totalUnits; }
    public int getAvailableUnits() { return availableUnits; }
    public double getSellingPrice() { return sellingPrice; }

    // Setters for mutable fields
    public void setSellingPrice(double sellingPrice) {
        if (sellingPrice >= 0) {
            this.sellingPrice = sellingPrice;
        } else {
             System.err.println("Warning: Attempted to set negative selling price.");
        }
    }

    // Methods to modify available units (ensure constraints are met)
    public boolean decrementAvailableUnits() {
        if (this.availableUnits > 0) {
            this.availableUnits--;
            return true;
        } else {
             System.err.println("Warning: Attempted to decrement zero available units.");
             return false;
        }
    }

    public boolean incrementAvailableUnits() {
        if (this.availableUnits < this.totalUnits) {
            this.availableUnits++;
            return true;
        } else {
             System.err.println("Warning: Attempted to increment available units beyond total units.");
             return false;
        }
    }

     // Used during loading/initialization to set correct available count based on bookings
     protected void setAvailableUnits(int availableUnits) {
        if (availableUnits >= 0 && availableUnits <= this.totalUnits) {
            this.availableUnits = availableUnits;
        } else {
            // Log error but don't throw exception during loading if possible
            System.err.println("Error: Invalid available units (" + availableUnits + ") set for flat type with total " + this.totalUnits + ". Clamping to valid range [0, " + this.totalUnits + "].");
            this.availableUnits = Math.max(0, Math.min(availableUnits, this.totalUnits));
        }
    }
}

class Project {
    private String projectName; // Should be unique
    private String neighborhood;
    private Map<FlatType, FlatTypeDetails> flatTypes; // Use final map, modify contents
    private Date applicationOpeningDate;
    private Date applicationClosingDate;
    private final String managerNric; // Manager is fixed once assigned
    private int maxOfficerSlots;
    private final List<String> approvedOfficerNrics; // Use final list, modify contents
    private boolean visibility; // true = on, false = off

    // Constructor ensures required fields are present
    public Project(String projectName, String neighborhood, Map<FlatType, FlatTypeDetails> flatTypes,
                   Date applicationOpeningDate, Date applicationClosingDate, String managerNric,
                   int maxOfficerSlots, List<String> approvedOfficerNrics, boolean visibility) {
        if (projectName == null || projectName.trim().isEmpty() || neighborhood == null ||
            flatTypes == null || applicationOpeningDate == null || applicationClosingDate == null ||
            managerNric == null || maxOfficerSlots < 0) {
            throw new IllegalArgumentException("Invalid project parameters");
        }
        if (applicationClosingDate.before(applicationOpeningDate)) {
             throw new IllegalArgumentException("Project closing date cannot be before opening date.");
        }
        this.projectName = projectName;
        this.neighborhood = neighborhood;
        // Create a mutable copy for internal use, but expose read-only view if needed
        this.flatTypes = new HashMap<>(flatTypes);
        this.applicationOpeningDate = applicationOpeningDate;
        this.applicationClosingDate = applicationClosingDate;
        this.managerNric = managerNric;
        this.maxOfficerSlots = maxOfficerSlots;
        // Create a mutable copy for internal use
        this.approvedOfficerNrics = new ArrayList<>(approvedOfficerNrics != null ? approvedOfficerNrics : Collections.emptyList());
        this.visibility = visibility;
    }

    // Getters
    public String getProjectName() { return projectName; }
    public String getNeighborhood() { return neighborhood; }
    // Return an unmodifiable view to prevent external modification
    public Map<FlatType, FlatTypeDetails> getFlatTypes() { return Collections.unmodifiableMap(flatTypes); }
    public Date getApplicationOpeningDate() { return applicationOpeningDate; }
    public Date getApplicationClosingDate() { return applicationClosingDate; }
    public String getManagerNric() { return managerNric; }
    public int getMaxOfficerSlots() { return maxOfficerSlots; }
    // Return an unmodifiable view
    public List<String> getApprovedOfficerNrics() { return Collections.unmodifiableList(approvedOfficerNrics); }
    public boolean isVisible() { return visibility; }
    public int getRemainingOfficerSlots() { return Math.max(0, maxOfficerSlots - approvedOfficerNrics.size()); }

    // Setters (primarily for Manager actions) - Validate inputs
    public void setProjectName(String projectName) {
        if (projectName != null && !projectName.trim().isEmpty()) {
            this.projectName = projectName.trim();
        }
    }
    public void setNeighborhood(String neighborhood) {
         if (neighborhood != null) {
            this.neighborhood = neighborhood;
         }
    }
    // Allows replacing the entire map, e.g., during editing
    public void setFlatTypes(Map<FlatType, FlatTypeDetails> flatTypes) {
        if (flatTypes != null) {
            this.flatTypes = new HashMap<>(flatTypes); // Replace with a copy
        }
    }
    public void setApplicationOpeningDate(Date applicationOpeningDate) {
        if (applicationOpeningDate != null) {
            // Optional: Add validation (e.g., not before today if creating new)
            this.applicationOpeningDate = applicationOpeningDate;
        }
    }
    public void setApplicationClosingDate(Date applicationClosingDate) {
         if (applicationClosingDate != null && (this.applicationOpeningDate == null || !applicationClosingDate.before(this.applicationOpeningDate))) {
            this.applicationClosingDate = applicationClosingDate;
         } else if (applicationClosingDate != null) {
             System.err.println("Warning: Closing date cannot be before opening date. Not updated.");
         }
    }
    public void setMaxOfficerSlots(int maxOfficerSlots) {
        // Ensure new max isn't less than current approved count
        if (maxOfficerSlots >= this.approvedOfficerNrics.size() && maxOfficerSlots >= 0) {
            this.maxOfficerSlots = maxOfficerSlots;
        } else {
             System.err.println("Warning: Cannot set max officer slots ("+ maxOfficerSlots +") below current approved count (" + this.approvedOfficerNrics.size() + "). Value not changed.");
        }
    }
    public void setVisibility(boolean visibility) { this.visibility = visibility; }

    // Methods to manage officers (called by ManagerController/Actions) - return boolean for success
    public boolean addApprovedOfficer(String officerNric) {
        if (officerNric != null && getRemainingOfficerSlots() > 0 && !approvedOfficerNrics.contains(officerNric)) {
            approvedOfficerNrics.add(officerNric);
            return true;
        }
        return false;
    }

    public boolean removeApprovedOfficer(String officerNric) {
        boolean removed = approvedOfficerNrics.remove(officerNric);
        // Optional: If removal makes max slots too high, adjust? Or leave as is? Leave as is for now.
        return removed;
    }

    // Helper to check if application period is active (inclusive)
    public boolean isApplicationPeriodActive(Date currentDate) {
        if (currentDate == null || applicationOpeningDate == null || applicationClosingDate == null) return false;
        // Use !before and !after for inclusive range check
        // Adjust closing date check to be inclusive of the closing day
        Calendar cal = Calendar.getInstance();
        cal.setTime(applicationClosingDate);
        cal.add(Calendar.DATE, 1); // Move to the day AFTER closing date
        Date endOfDayClosing = cal.getTime();

        return !currentDate.before(applicationOpeningDate) && currentDate.before(endOfDayClosing);
    }

    // Helper to check if project is currently "active" as defined by FAQ
    // Active: Visibility turned ON + Within application period
    public boolean isActive(Date currentDate) {
        return this.isVisible() && this.isApplicationPeriodActive(currentDate);
    }

    // Helper to check if application period has passed
    public boolean isApplicationPeriodExpired(Date currentDate) {
         if (currentDate == null || applicationClosingDate == null) return false; // Cannot determine if null
         // Expired if current date is strictly after the closing date
         // To match isApplicationPeriodActive, check against the day *after* closing date
        Calendar cal = Calendar.getInstance();
        cal.setTime(applicationClosingDate);
        cal.add(Calendar.DATE, 1); // Move to the day AFTER closing date
        Date endOfDayClosing = cal.getTime();
        return currentDate.after(endOfDayClosing); // Expired if current date is after the closing day ends
    }


    // Helper to get details for a specific flat type (returns null if not found)
    public FlatTypeDetails getFlatTypeDetails(FlatType type) {
        return flatTypes.get(type);
    }

    // Helper to get mutable details (used internally or by trusted controllers)
    protected FlatTypeDetails getMutableFlatTypeDetails(FlatType type) {
        return flatTypes.get(type);
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Project project = (Project) o;
        return projectName.equalsIgnoreCase(project.projectName); // Uniqueness based on name (case-insensitive)
    }

    @Override
    public int hashCode() {
        return Objects.hash(projectName.toLowerCase()); // Use lower case for consistent hashing
    }

    @Override
    public String toString() {
        return "Project{" +
               "projectName='" + projectName + '\'' +
               ", neighborhood='" + neighborhood + '\'' +
               ", managerNric='" + managerNric + '\'' +
               ", visibility=" + visibility +
               '}';
    }
}

// --- Application Tracking ---
class BTOApplication {
    private final String applicationId; // Unique ID (e.g., NRIC + ProjectName)
    private final String applicantNric;
    private final String projectName;
    private FlatType flatTypeApplied; // Can be null initially? No, should be set on creation.
    private ApplicationStatus status;
    private final Date applicationDate; // Track when applied
    private ApplicationStatus statusBeforeWithdrawal; // Store the status before PENDING_WITHDRAWAL

    // Constructor for new application
    public BTOApplication(String applicantNric, String projectName, FlatType flatTypeApplied, Date applicationDate) {
        if (applicantNric == null || projectName == null || flatTypeApplied == null || applicationDate == null) {
            throw new IllegalArgumentException("BTOApplication fields cannot be null");
        }
        this.applicationId = applicantNric + "_" + projectName; // Simple unique ID strategy
        this.applicantNric = applicantNric;
        this.projectName = projectName;
        this.flatTypeApplied = flatTypeApplied;
        this.status = ApplicationStatus.PENDING; // Default status for new applications
        this.applicationDate = applicationDate;
        this.statusBeforeWithdrawal = null; // Initially null
    }

     // Constructor for loading from file (allows setting all fields)
    public BTOApplication(String applicationId, String applicantNric, String projectName, FlatType flatTypeApplied, ApplicationStatus status, Date applicationDate) {
        if (applicationId == null || applicantNric == null || projectName == null || status == null || applicationDate == null) {
             throw new IllegalArgumentException("Required BTOApplication fields cannot be null when loading");
        }
         // flatTypeApplied can be null if status is not BOOKED/SUCCESSFUL/PENDING_WITHDRAWAL? Check CSV format.
         // Assuming flatTypeApplied is stored even for PENDING/UNSUCCESSFUL/WITHDRAWN.
         if (flatTypeApplied == null && (status == ApplicationStatus.BOOKED || status == ApplicationStatus.SUCCESSFUL || status == ApplicationStatus.PENDING_WITHDRAWAL )) {
              System.err.println("Warning: Loading " + status + " application ("+applicationId+") with null flatTypeApplied.");
         }

        this.applicationId = applicationId;
        this.applicantNric = applicantNric;
        this.projectName = projectName;
        this.flatTypeApplied = flatTypeApplied;
        this.status = status;
        this.applicationDate = applicationDate;
        this.statusBeforeWithdrawal = null; // Will be set during runtime if needed
        // If loading PENDING_WITHDRAWAL, we lost the original status - need to handle this gracefully in manager logic
        if (status == ApplicationStatus.PENDING_WITHDRAWAL) {
            System.err.println("Warning: Application " + applicationId + " loaded with PENDING_WITHDRAWAL status. Original status before withdrawal is unknown. Reverting will assume PENDING/SUCCESSFUL based on flat type.");
        }
    }

    // Getters
    public String getApplicationId() { return applicationId; }
    public String getApplicantNric() { return applicantNric; }
    public String getProjectName() { return projectName; }
    public FlatType getFlatTypeApplied() { return flatTypeApplied; }
    public ApplicationStatus getStatus() { return status; }
    public Date getApplicationDate() { return applicationDate; }
    public ApplicationStatus getStatusBeforeWithdrawal() { return statusBeforeWithdrawal; }

    // Setter (primarily for status changes by Manager/Officer/System)
    public void setStatus(ApplicationStatus status) {
        if (status != null) {
             // Store previous status if moving to PENDING_WITHDRAWAL
            if (status == ApplicationStatus.PENDING_WITHDRAWAL && this.status != ApplicationStatus.PENDING_WITHDRAWAL) {
                this.statusBeforeWithdrawal = this.status;
            }
            // Clear the stored status if moving *away* from PENDING_WITHDRAWAL
            if (this.status == ApplicationStatus.PENDING_WITHDRAWAL && status != ApplicationStatus.PENDING_WITHDRAWAL) {
                this.statusBeforeWithdrawal = null;
            }
            this.status = status;
        }
    }
    // Setter for flat type? Should only be set during creation or potentially booking confirmation?
    // Let's assume it's fixed after initial application. If booking allows changing type, add setter.
    // public void setFlatTypeApplied(FlatType flatTypeApplied) { this.flatTypeApplied = flatTypeApplied; }

     @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        BTOApplication that = (BTOApplication) o;
        return applicationId.equals(that.applicationId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(applicationId);
    }
}

// --- Enquiry Tracking ---
class Enquiry {
    private final String enquiryId; // Unique ID
    private final String applicantNric;
    private final String projectName; // Project the enquiry is about
    private String enquiryText; // Mutable if not replied
    private String replyText; // Null until replied
    private String repliedByNric; // NRIC of Officer/Manager who replied
    private final Date enquiryDate;
    private Date replyDate; // Null until replied
    private static long nextId = 1; // Simple static ID generation (Needs careful handling on load)

    // Constructor for new enquiry
    public Enquiry(String applicantNric, String projectName, String enquiryText, Date enquiryDate) {
        if (applicantNric == null || projectName == null || enquiryText == null || enquiryText.trim().isEmpty() || enquiryDate == null) {
            throw new IllegalArgumentException("Invalid Enquiry parameters");
        }
        // Synchronize ID generation if multi-threading is ever considered
        synchronized (Enquiry.class) {
            this.enquiryId = "ENQ" + (nextId++);
        }
        this.applicantNric = applicantNric;
        this.projectName = projectName;
        this.enquiryText = enquiryText;
        this.enquiryDate = enquiryDate;
        this.replyText = null;
        this.repliedByNric = null;
        this.replyDate = null;
    }

     // Constructor for loading from file
    public Enquiry(String enquiryId, String applicantNric, String projectName, String enquiryText, String replyText, String repliedByNric, Date enquiryDate, Date replyDate) {
         if (enquiryId == null || applicantNric == null || projectName == null || enquiryText == null || enquiryDate == null) {
            throw new IllegalArgumentException("Required Enquiry fields cannot be null when loading");
        }
        this.enquiryId = enquiryId;
        this.applicantNric = applicantNric;
        this.projectName = projectName;
        this.enquiryText = enquiryText;
        this.replyText = (replyText == null || replyText.trim().isEmpty()) ? null : replyText.trim();
        this.repliedByNric = (repliedByNric == null || repliedByNric.trim().isEmpty()) ? null : repliedByNric.trim();
        this.enquiryDate = enquiryDate;
        this.replyDate = replyDate; // Can be null

        // Ensure nextId is updated correctly after loading all enquiries
        updateNextId(enquiryId);
    }

    // Static method to update the nextId based on loaded IDs
    public static void updateNextId(String loadedEnquiryId) {
         if (loadedEnquiryId != null && loadedEnquiryId.startsWith("ENQ")) {
            try {
                long idNum = Long.parseLong(loadedEnquiryId.substring(3));
                // Synchronize access to static variable
                synchronized (Enquiry.class) {
                    if (idNum >= nextId) {
                        nextId = idNum + 1;
                    }
                }
            } catch (NumberFormatException | StringIndexOutOfBoundsException e) {
                System.err.println("Warning: Could not parse enquiry ID for nextId update: " + loadedEnquiryId);
            }
         }
    }
     // Call this after loading all enquiries are complete
     public static void finalizeNextIdInitialization() {
         System.out.println("Enquiry nextId initialized to: " + nextId);
     }


    // Getters
    public String getEnquiryId() { return enquiryId; }
    public String getApplicantNric() { return applicantNric; }
    public String getProjectName() { return projectName; }
    public String getEnquiryText() { return enquiryText; }
    public String getReplyText() { return replyText; }
    public String getRepliedByNric() { return repliedByNric; }
    public Date getEnquiryDate() { return enquiryDate; }
    public Date getReplyDate() { return replyDate; }

    // Setters (for editing enquiry text by applicant, and replying by Officer/Manager)
    public boolean setEnquiryText(String enquiryText) {
        // Can only edit if not replied
        if (!isReplied() && enquiryText != null && !enquiryText.trim().isEmpty()) {
            this.enquiryText = enquiryText.trim();
            return true;
        } else if (isReplied()) {
             System.err.println("Cannot edit an enquiry that has already been replied to (ID: " + enquiryId + ").");
             return false;
        } else {
             System.err.println("Enquiry text cannot be empty.");
             return false;
        }
    }

    public boolean setReply(String replyText, String repliedByNric, Date replyDate) {
        if (replyText != null && !replyText.trim().isEmpty() && repliedByNric != null && replyDate != null) {
            this.replyText = replyText.trim();
            this.repliedByNric = repliedByNric;
            this.replyDate = replyDate;
            return true;
        } else {
            System.err.println("Invalid reply parameters provided for enquiry ID: " + enquiryId);
            return false;
        }
    }

    public boolean isReplied() {
        return this.replyText != null && !this.replyText.isEmpty();
    }

     @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Enquiry enquiry = (Enquiry) o;
        return enquiryId.equals(enquiry.enquiryId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(enquiryId);
    }
}

// --- Officer Registration Tracking ---
class OfficerRegistration {
    private final String registrationId; // Unique ID (e.g., OfficerNRIC + ProjectName)
    private final String officerNric;
    private final String projectName;
    private OfficerRegistrationStatus status;
    private final Date registrationDate;

    public OfficerRegistration(String officerNric, String projectName, Date registrationDate) {
         if (officerNric == null || projectName == null || registrationDate == null) {
            throw new IllegalArgumentException("OfficerRegistration fields cannot be null");
        }
        this.registrationId = officerNric + "_REG_" + projectName; // Simple unique ID
        this.officerNric = officerNric;
        this.projectName = projectName;
        this.status = OfficerRegistrationStatus.PENDING;
        this.registrationDate = registrationDate;
    }

     // Constructor for loading from file
    public OfficerRegistration(String registrationId, String officerNric, String projectName, OfficerRegistrationStatus status, Date registrationDate) {
         if (registrationId == null || officerNric == null || projectName == null || status == null || registrationDate == null) {
            throw new IllegalArgumentException("Required OfficerRegistration fields cannot be null when loading");
        }
        this.registrationId = registrationId;
        this.officerNric = officerNric;
        this.projectName = projectName;
        this.status = status;
        this.registrationDate = registrationDate;
    }

    // Getters
    public String getRegistrationId() { return registrationId; }
    public String getOfficerNric() { return officerNric; }
    public String getProjectName() { return projectName; }
    public OfficerRegistrationStatus getStatus() { return status; }
    public Date getRegistrationDate() { return registrationDate; }

    // Setter (for status change by Manager)
    public void setStatus(OfficerRegistrationStatus status) {
        if (status != null) {
            this.status = status;
        }
    }

     @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        OfficerRegistration that = (OfficerRegistration) o;
        return registrationId.equals(that.registrationId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(registrationId);
    }
}


// ==================
// Data Service (Handles CSV Persistence - SRP)
// ==================
class DataService {
    // File paths
    private static final String DATA_DIR = "data"; // Store CSVs in a subdirectory
    private static final String APPLICANT_LIST_FILE = DATA_DIR + File.separator + "ApplicantList.csv";
    private static final String OFFICER_LIST_FILE = DATA_DIR + File.separator + "OfficerList.csv";
    private static final String MANAGER_LIST_FILE = DATA_DIR + File.separator + "ManagerList.csv";
    private static final String PROJECT_FILE = DATA_DIR + File.separator + "ProjectList.csv";
    private static final String APPLICATION_FILE = DATA_DIR + File.separator + "applications.csv";
    private static final String ENQUIRY_FILE = DATA_DIR + File.separator + "enquiries.csv";
    private static final String OFFICER_REGISTRATION_FILE = DATA_DIR + File.separator + "officer_registrations.csv";

    // CSV constants
    private static final String DELIMITER = ",";
    private static final String LIST_DELIMITER = ";"; // For lists within a cell (like officers)
    public static final SimpleDateFormat DATE_FORMAT = new SimpleDateFormat("yyyy-MM-dd");
    private static final Pattern NRIC_PATTERN = Pattern.compile("^[STFG]\\d{7}[A-Z]$"); // Added F, G

    // Headers (used for writing and verifying reading)
    private static final String[] APPLICANT_HEADER = {"Name", "NRIC", "Age", "Marital Status", "Password"};
    private static final String[] OFFICER_HEADER = {"Name", "NRIC", "Age", "Marital Status", "Password"};
    private static final String[] MANAGER_HEADER = {"Name", "NRIC", "Age", "Marital Status", "Password"};
    private static final String[] PROJECT_HEADER = {
        "Project Name", "Neighborhood", "Type 1", "Number of units for Type 1", "Selling price for Type 1",
        "Type 2", "Number of units for Type 2", "Selling price for Type 2",
        "Application opening date", "Application closing date", "Manager", "Officer Slot", "Officer", "Visibility" // Added Visibility
    };
    // NOTE: Application CSV does not store statusBeforeWithdrawal, it's transient state
    private static final String[] APPLICATION_HEADER = {"ApplicationID", "ApplicantNRIC", "ProjectName", "FlatTypeApplied", "Status", "ApplicationDate"};
    private static final String[] ENQUIRY_HEADER = {"EnquiryID", "ApplicantNRIC", "ProjectName", "EnquiryText", "ReplyText", "RepliedByNRIC", "EnquiryDate", "ReplyDate"};
    private static final String[] OFFICER_REGISTRATION_HEADER = {"RegistrationID", "OfficerNRIC", "ProjectName", "Status", "RegistrationDate"};


    // --- Loading Methods ---

    public static Map<String, User> loadUsers() {
        Map<String, User> users = new HashMap<>();

        // Process Applicants
        readCsv(APPLICANT_LIST_FILE, APPLICANT_HEADER.length).forEach(data -> {
            try {
                String nric = data[1].trim();
                if (!isValidNric(nric) || users.containsKey(nric)) {
                    if(users.containsKey(nric)) System.err.println("Duplicate NRIC found in ApplicantList: " + nric + ". Skipping duplicate.");
                    else System.err.println("Invalid NRIC format in ApplicantList: " + nric + ". Skipping.");
                    return; // Skip invalid or duplicate NRIC
                }
                int age = Integer.parseInt(data[2].trim());
                MaritalStatus status = MaritalStatus.valueOf(data[3].trim().toUpperCase());
                Applicant applicant = new Applicant(nric, data[4].trim(), data[0].trim(), age, status);
                users.put(nric, applicant);
            } catch (Exception e) {
                System.err.println("Error parsing applicant data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });

        // Process Officers (they are also Applicants initially, so create as HDBOfficer)
        readCsv(OFFICER_LIST_FILE, OFFICER_HEADER.length).forEach(data -> {
            try {
                String nric = data[1].trim();
                 if (!isValidNric(nric)) {
                     System.err.println("Invalid NRIC format in OfficerList: " + nric + ". Skipping.");
                     return;
                 }
                int age = Integer.parseInt(data[2].trim());
                MaritalStatus status = MaritalStatus.valueOf(data[3].trim().toUpperCase());
                HDBOfficer officer = new HDBOfficer(nric, data[4].trim(), data[0].trim(), age, status);
                // Overwrite if NRIC was already loaded as Applicant (promoting role)
                if (users.containsKey(nric) && !(users.get(nric) instanceof HDBOfficer)) {
                     System.out.println("Info: User " + nric + " found in both Applicant and Officer lists. Using Officer role.");
                } else if (users.containsKey(nric)) {
                     System.err.println("Duplicate NRIC found in OfficerList: " + nric + ". Skipping duplicate.");
                     return; // Skip duplicate within officer list
                }
                users.put(nric, officer);
            } catch (Exception e) {
                System.err.println("Error parsing officer data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });

        // Process Managers
        readCsv(MANAGER_LIST_FILE, MANAGER_HEADER.length).forEach(data -> {
            try {
                String nric = data[1].trim();
                 if (!isValidNric(nric)) {
                     System.err.println("Invalid NRIC format in ManagerList: " + nric + ". Skipping.");
                     return;
                 }
                int age = Integer.parseInt(data[2].trim());
                MaritalStatus status = MaritalStatus.valueOf(data[3].trim().toUpperCase());
                HDBManager manager = new HDBManager(nric, data[4].trim(), data[0].trim(), age, status);
                 // Overwrite if NRIC was already loaded (promoting role)
                if (users.containsKey(nric) && !(users.get(nric) instanceof HDBManager)) {
                     System.out.println("Info: User " + nric + " found in other lists. Using Manager role.");
                } else if (users.containsKey(nric)) {
                     System.err.println("Duplicate NRIC found in ManagerList: " + nric + ". Skipping duplicate.");
                     return; // Skip duplicate within manager list
                }
                users.put(nric, manager);
            } catch (Exception e) {
                System.err.println("Error parsing manager data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });

        System.out.println("Loaded " + users.size() + " unique users.");
        return users;
    }

    // Load Projects *after* users (for manager validation) and *before* applications (for unit adjustment)
     public static List<Project> loadProjects(Map<String, User> users) {
        List<Project> projects = new ArrayList<>();
        Set<String> projectNames = new HashSet<>(); // To check for duplicate project names

        readCsv(PROJECT_FILE, PROJECT_HEADER.length).forEach(data -> {
            try {
                String projectName = data[0].trim();
                if (projectName.isEmpty() || !projectNames.add(projectName.toLowerCase())) {
                     if (!projectName.isEmpty()) System.err.println("Skipping duplicate project name: " + projectName);
                    return;
                }

                String neighborhood = data[1].trim();
                Map<FlatType, FlatTypeDetails> flatTypes = new HashMap<>();

                // Parse Type 1 (assuming 2-Room based on sample, but use enum parsing)
                if (data[2] != null && !data[2].trim().isEmpty()) {
                    FlatType type1 = FlatType.fromString(data[2].trim());
                    if (type1 != null) {
                        int units1 = Integer.parseInt(data[3].trim());
                        double price1 = Double.parseDouble(data[4].trim());
                        // Available units will be adjusted later based on bookings
                        flatTypes.put(type1, new FlatTypeDetails(units1, units1, price1));
                    } else {
                         System.err.println("Warning: Unknown flat type '" + data[2] + "' in project '" + projectName + "'. Skipping type.");
                    }
                }

                // Parse Type 2 (assuming 3-Room based on sample)
                 if (data[5] != null && !data[5].trim().isEmpty()) {
                    FlatType type2 = FlatType.fromString(data[5].trim());
                     if (type2 != null) {
                        int units2 = Integer.parseInt(data[6].trim());
                        double price2 = Double.parseDouble(data[7].trim());
                        flatTypes.put(type2, new FlatTypeDetails(units2, units2, price2));
                     } else {
                          System.err.println("Warning: Unknown flat type '" + data[5] + "' in project '" + projectName + "'. Skipping type.");
                     }
                }

                Date openingDate = parseDate(data[8].trim());
                Date closingDate = parseDate(data[9].trim());
                String managerNric = data[10].trim();
                int officerSlots = Integer.parseInt(data[11].trim());

                // Parse officer list (semicolon separated, potentially quoted)
                List<String> officers = parseListString(data[12]);

                // Parse Visibility (Column 13, index 13) - Added
                boolean visibility = false; // Default to false if missing or invalid
                if (data.length > 13 && data[13] != null) {
                     String visibilityStr = data[13].trim();
                     if (visibilityStr.equals("1")) {
                         visibility = true;
                     } else if (!visibilityStr.equals("0") && !visibilityStr.isEmpty()) {
                         System.err.println("Warning: Invalid visibility value '" + visibilityStr + "' for project '" + projectName + "'. Assuming false.");
                     }
                }


                // Validate manager NRIC exists and is a Manager
                if (!users.containsKey(managerNric) || !(users.get(managerNric) instanceof HDBManager)) {
                    System.err.println("Warning: Project '" + projectName + "' has invalid or non-manager NRIC: " + managerNric + ". Skipping project.");
                    projectNames.remove(projectName.toLowerCase()); // Allow reprocessing if fixed later
                    return;
                }
                 // Validate dates
                 if (openingDate == null || closingDate == null || closingDate.before(openingDate)) {
                     System.err.println("Warning: Project '" + projectName + "' has invalid application dates (Open: " + data[8] + ", Close: " + data[9] + "). Skipping project.");
                     projectNames.remove(projectName.toLowerCase());
                     return;
                 }
                 // Validate officer NRICs exist and are officers.
                 List<String> validOfficers = new ArrayList<>();
                 List<String> invalidOfficers = new ArrayList<>();
                 for (String nric : officers) {
                     if (users.containsKey(nric) && users.get(nric) instanceof HDBOfficer) {
                         validOfficers.add(nric);
                     } else {
                         invalidOfficers.add(nric);
                     }
                 }
                 if (!invalidOfficers.isEmpty()) {
                     System.err.println("Warning: Project '" + projectName + "' contains invalid or non-officer NRICs in its officer list: " + invalidOfficers + ". Only valid officers retained.");
                 }
                 if (validOfficers.size() > officerSlots) {
                      System.err.println("Warning: Project '" + projectName + "' has more approved officers ("+validOfficers.size()+") than slots ("+officerSlots+"). Check data. Using officer list as is.");
                      // Allow loading even if inconsistent, sync step will handle registrations.
                 }


                Project project = new Project(projectName, neighborhood, flatTypes, openingDate, closingDate, managerNric, officerSlots, validOfficers, visibility);
                projects.add(project);

            } catch (NumberFormatException e) {
                System.err.println("Error parsing number in project data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            } catch (IllegalArgumentException e) {
                System.err.println("Error parsing enum/data in project data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            } catch (Exception e) { // Catch broader exceptions
                 System.err.println("Unexpected error parsing project data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
                 e.printStackTrace(); // Print stack trace for debugging
            }
        });

        System.out.println("Loaded " + projects.size() + " projects.");
        return projects;
    }

    // Load Applications *after* projects
    public static Map<String, BTOApplication> loadApplications(List<Project> projects) {
        Map<String, BTOApplication> applications = new HashMap<>();
        Map<Project, Map<FlatType, Integer>> bookedCounts = new HashMap<>(); // Track booked counts per project/type

        readCsv(APPLICATION_FILE, APPLICATION_HEADER.length).forEach(data -> {
            try {
                String appId = data[0].trim();
                if (appId.isEmpty() || applications.containsKey(appId)) {
                     if (!appId.isEmpty()) System.err.println("Skipping duplicate application ID: " + appId);
                    return;
                }
                String applicantNric = data[1].trim();
                String projectName = data[2].trim();
                FlatType flatType = FlatType.fromString(data[3].trim()); // Handles null/empty/invalid -> null
                ApplicationStatus status = ApplicationStatus.valueOf(data[4].trim().toUpperCase());
                Date appDate = parseDate(data[5].trim());

                if (appDate == null) {
                     System.err.println("Skipping application with invalid date: " + appId);
                     return;
                }
                 // Validate flat type if status requires it
                 if (flatType == null && (status == ApplicationStatus.BOOKED || status == ApplicationStatus.SUCCESSFUL || status == ApplicationStatus.PENDING_WITHDRAWAL)) {
                     System.err.println("Warning: Application " + appId + " is " + status + " but has invalid/missing flat type '" + data[3] + "'. Status might be inconsistent.");
                     // Load as is but warn.
                 }
                 if (status == ApplicationStatus.PENDING_WITHDRAWAL) {
                      System.out.println("Info: Application " + appId + " loaded with PENDING_WITHDRAWAL status.");
                      // Original status before withdrawal is lost on file load.
                 }


                BTOApplication application = new BTOApplication(appId, applicantNric, projectName, flatType, status, appDate);
                applications.put(application.getApplicationId(), application);

                // Track booked counts for adjusting project units later
                if (status == ApplicationStatus.BOOKED && flatType != null) {
                    Project project = projects.stream()
                                            .filter(p -> p.getProjectName().equalsIgnoreCase(projectName))
                                            .findFirst().orElse(null);
                    if (project != null) {
                        bookedCounts.computeIfAbsent(project, _ -> new HashMap<>())
                                    .merge(flatType, 1, Integer::sum);
                    } else {
                         System.err.println("Warning: Booked application " + appId + " refers to non-existent project '" + projectName + "'. Unit count cannot be adjusted.");
                    }
                }

            } catch (IllegalArgumentException e) {
                 System.err.println("Error parsing enum/data in application data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            } catch (Exception e) {
                System.err.println("Error parsing application data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });

        // Adjust available units in projects based on booked counts
        bookedCounts.forEach((project, typeCounts) -> {
            typeCounts.forEach((type, count) -> {
                FlatTypeDetails details = project.getMutableFlatTypeDetails(type);
                if (details != null) {
                    int initialAvailable = details.getTotalUnits();
                    int finalAvailable = Math.max(0, initialAvailable - count);
                    if (finalAvailable != details.getAvailableUnits()) {
                         // System.out.println("Adjusting available units for " + project.getProjectName() + "/" + type.getDisplayName() + " from " + details.getAvailableUnits() + " to " + finalAvailable);
                         details.setAvailableUnits(finalAvailable);
                    }
                     if (count > details.getTotalUnits()) {
                         System.err.println("Error: More flats booked (" + count + ") than total units (" + details.getTotalUnits() + ") for " + project.getProjectName() + "/" + type.getDisplayName() + ". Available units set to 0.");
                     }
                } else {
                     System.err.println("Warning: Trying to adjust units for non-existent flat type " + type.getDisplayName() + " in project " + project.getProjectName());
                }
            });
        });


        System.out.println("Loaded " + applications.size() + " applications.");
        return applications;
    }

    // Load Enquiries *after* users and projects (optional validation)
    public static List<Enquiry> loadEnquiries() {
        List<Enquiry> enquiries = new ArrayList<>();
        Set<String> enquiryIds = new HashSet<>(); // Check duplicates

        readCsv(ENQUIRY_FILE, ENQUIRY_HEADER.length).forEach(data -> {
            try {
                String id = data[0].trim();
                 if (id.isEmpty() || !enquiryIds.add(id)) {
                     if (!id.isEmpty()) System.err.println("Skipping duplicate enquiry ID: " + id);
                    return;
                 }
                String applicantNric = data[1].trim();
                String projectName = data[2].trim();
                String text = data[3].trim(); // Enquiry text should not be empty
                String reply = data[4].trim();
                String repliedBy = data[5].trim();
                Date enqDate = parseDate(data[6].trim());
                Date replyDate = parseDate(data[7].trim()); // Can be null

                 if (text.isEmpty() || enqDate == null) {
                     System.err.println("Skipping enquiry with missing text or invalid date: " + id);
                     enquiryIds.remove(id);
                     return;
                 }
                 // If replied, check if related fields are present
                 if ((reply != null && !reply.isEmpty()) && (repliedBy == null || repliedBy.isEmpty() || replyDate == null)) {
                     System.err.println("Warning: Enquiry " + id + " seems replied but missing replier NRIC or reply date. Loading reply as is.");
                 }


                Enquiry enquiry = new Enquiry(id, applicantNric, projectName, text, reply, repliedBy, enqDate, replyDate);
                enquiries.add(enquiry);
                // Update nextId is handled within the Enquiry constructor now
            } catch (IllegalArgumentException e) {
                 System.err.println("Error parsing enum/data in enquiry data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            } catch (Exception e) {
                System.err.println("Error parsing enquiry data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });
        Enquiry.finalizeNextIdInitialization(); // Set the nextId correctly after all loads
        System.out.println("Loaded " + enquiries.size() + " enquiries.");
        return enquiries;
    }

    // Load Officer Registrations *after* users and projects (for validation)
     public static Map<String, OfficerRegistration> loadOfficerRegistrations(Map<String, User> users, List<Project> projects) {
        Map<String, OfficerRegistration> registrations = new HashMap<>();

        readCsv(OFFICER_REGISTRATION_FILE, OFFICER_REGISTRATION_HEADER.length).forEach(data -> {
            try {
                String regId = data[0].trim();
                 if (regId.isEmpty() || registrations.containsKey(regId)) {
                     if (!regId.isEmpty()) System.err.println("Skipping duplicate registration ID: " + regId);
                    return;
                 }
                String officerNric = data[1].trim();
                String projectName = data[2].trim();
                OfficerRegistrationStatus status = OfficerRegistrationStatus.valueOf(data[3].trim().toUpperCase());
                Date regDate = parseDate(data[4].trim());

                 if (regDate == null) {
                     System.err.println("Skipping registration with invalid date: " + regId);
                     return;
                 }

                 // Validate Officer NRIC
                 if (!users.containsKey(officerNric) || !(users.get(officerNric) instanceof HDBOfficer)) {
                     System.err.println("Warning: Registration " + regId + " refers to invalid or non-officer NRIC: " + officerNric + ". Skipping registration.");
                     return;
                 }
                 // Validate Project Name
                 boolean projectExists = projects.stream().anyMatch(p -> p.getProjectName().equalsIgnoreCase(projectName));
                 if (!projectExists) {
                      System.err.println("Warning: Registration " + regId + " refers to non-existent project: " + projectName + ". Skipping registration.");
                      return;
                 }


                OfficerRegistration registration = new OfficerRegistration(regId, officerNric, projectName, status, regDate);
                registrations.put(registration.getRegistrationId(), registration);
            } catch (IllegalArgumentException e) {
                 System.err.println("Error parsing enum/data in officer registration data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            } catch (Exception e) {
                System.err.println("Error parsing officer registration data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });
        System.out.println("Loaded " + registrations.size() + " officer registrations.");
        return registrations;
    }

    // --- Post-Load Synchronization ---

    // Call this after loading all data to ensure consistency
    public static void synchronizeData(Map<String, User> users, List<Project> projects, Map<String, BTOApplication> applications, Map<String, OfficerRegistration> officerRegistrations) {
        System.out.println("Synchronizing loaded data...");
        boolean registrationsModified = false; // Flag to check if we need to save registrations

        // 1. Sync Applicant state with Applications
        users.values().stream()
             .filter(u -> u instanceof Applicant)
             .map(u -> (Applicant) u)
             .forEach(applicant -> {
                 // Find the *most relevant* application for this user (e.g., not withdrawn/unsuccessful if others exist)
                 BTOApplication relevantApp = applications.values().stream()
                     .filter(app -> app.getApplicantNric().equals(applicant.getNric()))
                     .max(Comparator.comparing(BTOApplication::getStatus, Comparator.comparingInt(s -> {
                         // Define order of relevance: BOOKED > SUCCESSFUL > PENDING_WITHDRAWAL > PENDING > WITHDRAWN > UNSUCCESSFUL
                         switch (s) {
                             case BOOKED: return 6;
                             case SUCCESSFUL: return 5;
                             case PENDING_WITHDRAWAL: return 4; // Higher relevance than PENDING
                             case PENDING: return 3;
                             case WITHDRAWN: return 2;
                             case UNSUCCESSFUL: return 1;
                             default: return 0;
                         }
                     })).thenComparing(BTOApplication::getApplicationDate).reversed()) // Newest first if status same
                     .orElse(null);

                 if (relevantApp != null) {
                     applicant.setAppliedProjectName(relevantApp.getProjectName());
                     applicant.setApplicationStatus(relevantApp.getStatus()); // Set profile status to the most relevant app's status
                     if (relevantApp.getStatus() == ApplicationStatus.BOOKED) {
                         applicant.setBookedFlatType(relevantApp.getFlatTypeApplied());
                     } else {
                         applicant.setBookedFlatType(null); // Clear booked type if not currently BOOKED
                     }
                 } else {
                     // No applications found for this user, ensure state is clear
                     applicant.clearApplicationState();
                 }
             });

        // 2. Sync Officer Registrations with Project Approved Lists
        // Iterate through projects and their approved officer lists
        for (Project project : projects) {
            List<String> approvedNrics = new ArrayList<>(project.getApprovedOfficerNrics()); // Copy to avoid concurrent modification issues if we remove invalid ones

            for (String officerNric : approvedNrics) {
                User user = users.get(officerNric);
                if (!(user instanceof HDBOfficer)) {
                    System.err.println("Data Sync Warning: NRIC " + officerNric + " in project '" + project.getProjectName() + "' approved list is not a valid HDB Officer. Consider removing from project CSV.");
                    // Optionally remove from the project object's list here?
                    // project.removeApprovedOfficer(officerNric); // Be careful with modifying project data here
                    continue;
                }

                // Check if a corresponding APPROVED registration exists
                String expectedRegId = officerNric + "_REG_" + project.getProjectName();
                OfficerRegistration existingReg = officerRegistrations.get(expectedRegId);

                if (existingReg == null || existingReg.getStatus() != OfficerRegistrationStatus.APPROVED) {
                    // Missing or incorrect status registration found for an officer in the project's approved list.
                    System.out.println("Info: Auto-creating/updating APPROVED registration for Officer " + officerNric + " for Project '" + project.getProjectName() + "' based on project list.");

                    // Use project opening date as a placeholder registration date
                    Date placeholderDate = project.getApplicationOpeningDate() != null ? project.getApplicationOpeningDate() : new Date(0); // Use epoch if project date is null

                    OfficerRegistration syncReg = new OfficerRegistration(expectedRegId, officerNric, project.getProjectName(), OfficerRegistrationStatus.APPROVED, placeholderDate);
                    officerRegistrations.put(syncReg.getRegistrationId(), syncReg);
                    registrationsModified = true; // Mark for saving
                }
                // No need to set handlingProjectName on officer object, it's derived at runtime
            }
        }

        // 3. Check for APPROVED registrations where the officer is NOT in the project list (less common issue)
        for (OfficerRegistration reg : officerRegistrations.values()) {
            if (reg.getStatus() == OfficerRegistrationStatus.APPROVED) {
                Project project = projects.stream()
                                        .filter(p -> p.getProjectName().equals(reg.getProjectName()))
                                        .findFirst().orElse(null);
                if (project == null) {
                    System.err.println("Data Sync Warning: Approved registration " + reg.getRegistrationId() + " refers to a non-existent project '" + reg.getProjectName() + "'. Consider removing registration.");
                    // Optionally mark for removal: regsToRemoveOrUpdate.add(reg);
                } else if (!project.getApprovedOfficerNrics().contains(reg.getOfficerNric())) {
                    System.err.println("Data Sync Warning: Approved registration " + reg.getRegistrationId() + " exists, but officer " + reg.getOfficerNric() + " is NOT in project '" + project.getProjectName() + "' approved list. Registration status might be outdated or project list incorrect.");
                    // What to do? Reject the registration? Add officer to project? Let's just warn.
                    // Option: reg.setStatus(OfficerRegistrationStatus.REJECTED); registrationsModified = true;
                }
            }
        }
        // Process removals if decided:
        // regsToRemoveOrUpdate.forEach(reg -> officerRegistrations.remove(reg.getRegistrationId()));
        // if (!regsToRemoveOrUpdate.isEmpty()) registrationsModified = true;


        // 4. Available unit counts are already adjusted during application loading.

        // Save registrations if modified during sync
        if (registrationsModified) {
            System.out.println("Saving updated officer registrations due to synchronization...");
            saveOfficerRegistrations(officerRegistrations);
        }

        System.out.println("Data synchronization complete.");
    }


    // --- Saving Methods ---

    // Save all data - typically called on shutdown or major checkpoints
    public static void saveAllData(Map<String, User> users, List<Project> projects, Map<String, BTOApplication> applications, List<Enquiry> enquiries, Map<String, OfficerRegistration> officerRegistrations) {
        System.out.println("Saving all data...");
        saveUsers(users);
        saveProjects(projects);
        saveApplications(applications);
        saveEnquiries(enquiries);
        saveOfficerRegistrations(officerRegistrations);
        System.out.println("All data saved.");
    }

    // Save only users - called after password change etc.
    public static void saveUsers(Map<String, User> users) {
        List<String[]> applicantData = new ArrayList<>();
        List<String[]> officerData = new ArrayList<>();
        List<String[]> managerData = new ArrayList<>();

        // Add headers
        applicantData.add(APPLICANT_HEADER);
        officerData.add(OFFICER_HEADER);
        managerData.add(MANAGER_HEADER);

        users.values().forEach(user -> {
            String[] userData = {
                user.getName(),
                user.getNric(),
                String.valueOf(user.getAge()),
                user.getMaritalStatus().name(),
                user.getPassword() // Save current password
            };
            switch (user.getRole()) {
                case HDB_MANAGER: managerData.add(userData); break;
                case HDB_OFFICER: officerData.add(userData); break;
                case APPLICANT: applicantData.add(userData); break;
            }
        });

        writeCsv(APPLICANT_LIST_FILE, applicantData);
        writeCsv(OFFICER_LIST_FILE, officerData);
        writeCsv(MANAGER_LIST_FILE, managerData);
        System.out.println("Saved users.");
    }

    // Save only projects - called after create/edit/delete/toggle/booking/officer approval
    public static void saveProjects(List<Project> projects) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(PROJECT_HEADER);

        projects.forEach(project -> {
            String[] data = new String[PROJECT_HEADER.length]; // Use header length
            data[0] = project.getProjectName();
            data[1] = project.getNeighborhood();

            // Get details for known types, handle missing types gracefully
            FlatTypeDetails twoRoomDetails = project.getFlatTypeDetails(FlatType.TWO_ROOM);
            FlatTypeDetails threeRoomDetails = project.getFlatTypeDetails(FlatType.THREE_ROOM);

            // Type 1 (Assuming 2-Room)
            if (twoRoomDetails != null) {
                data[2] = FlatType.TWO_ROOM.getDisplayName();
                data[3] = String.valueOf(twoRoomDetails.getTotalUnits()); // Save total units
                data[4] = String.valueOf(twoRoomDetails.getSellingPrice());
            } else {
                 data[2] = ""; data[3] = "0"; data[4] = "0";
            }

            // Type 2 (Assuming 3-Room)
            if (threeRoomDetails != null) {
                data[5] = FlatType.THREE_ROOM.getDisplayName();
                data[6] = String.valueOf(threeRoomDetails.getTotalUnits()); // Save total units
                data[7] = String.valueOf(threeRoomDetails.getSellingPrice());
            } else {
                 data[5] = ""; data[6] = "0"; data[7] = "0";
            }

            data[8] = formatDate(project.getApplicationOpeningDate());
            data[9] = formatDate(project.getApplicationClosingDate());
            data[10] = project.getManagerNric();
            data[11] = String.valueOf(project.getMaxOfficerSlots());
            // Join approved officers with semicolon, handle empty list
            String officers = String.join(LIST_DELIMITER, project.getApprovedOfficerNrics());
            data[12] = officers; // Let escapeCsvField handle quoting if needed

            // Visibility (Column 13, index 13) - Added
            data[13] = project.isVisible() ? "1" : "0";

            dataList.add(data);
        });
        writeCsv(PROJECT_FILE, dataList);
        System.out.println("Saved projects.");
    }

    // Save only applications - called after apply/withdraw/approve/reject/book
    public static void saveApplications(Map<String, BTOApplication> applications) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(APPLICATION_HEADER);
        applications.values().stream()
            .sorted(Comparator.comparing(BTOApplication::getApplicationId)) // Sort for consistent output
            .forEach(app -> {
                dataList.add(new String[]{
                    app.getApplicationId(),
                    app.getApplicantNric(),
                    app.getProjectName(),
                    // Save enum name for flat type for robustness
                    app.getFlatTypeApplied() == null ? "" : app.getFlatTypeApplied().name(), // Save enum name or ""
                    app.getStatus().name(), // Saves current status (e.g., PENDING_WITHDRAWAL)
                    formatDate(app.getApplicationDate())
                });
            });
        writeCsv(APPLICATION_FILE, dataList);
        System.out.println("Saved applications.");
    }

    // Save only enquiries - called after submit/edit/delete/reply
    public static void saveEnquiries(List<Enquiry> enquiries) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(ENQUIRY_HEADER);
        enquiries.stream()
            .sorted(Comparator.comparing(Enquiry::getEnquiryId)) // Sort for consistent output
            .forEach(enq -> {
                dataList.add(new String[]{
                    enq.getEnquiryId(),
                    enq.getApplicantNric(),
                    enq.getProjectName(),
                    enq.getEnquiryText(),
                    enq.getReplyText() == null ? "" : enq.getReplyText(),
                    enq.getRepliedByNric() == null ? "" : enq.getRepliedByNric(),
                    formatDate(enq.getEnquiryDate()),
                    formatDate(enq.getReplyDate()) // formatDate handles null -> ""
                });
            });
        writeCsv(ENQUIRY_FILE, dataList);
        System.out.println("Saved enquiries.");
    }

    // Save only officer registrations - called after register/approve/reject
     public static void saveOfficerRegistrations(Map<String, OfficerRegistration> registrations) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(OFFICER_REGISTRATION_HEADER);
        registrations.values().stream()
            .sorted(Comparator.comparing(OfficerRegistration::getRegistrationId)) // Sort for consistent output
            .forEach(reg -> {
                dataList.add(new String[]{
                    reg.getRegistrationId(),
                    reg.getOfficerNric(),
                    reg.getProjectName(),
                    reg.getStatus().name(),
                    formatDate(reg.getRegistrationDate())
                });
            });
        writeCsv(OFFICER_REGISTRATION_FILE, dataList);
        System.out.println("Saved officer registrations.");
    }

    // --- Helper Methods ---

    // Reads CSV, skips header, handles basic parsing and potential errors
    private static List<String[]> readCsv(String filename, int expectedColumns) {
        List<String[]> data = new ArrayList<>();
        Path path = Paths.get(filename);

        if (!Files.exists(path)) {
            System.err.println("Warning: File not found - " + filename + ". Attempting to create.");
            try {
                Path parent = path.getParent();
                if (parent != null) {
                    Files.createDirectories(parent); // Ensure directory exists
                }
                Files.createFile(path);
                // Write header to new file based on filename
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
            return data; // Return empty list
        }

        try (BufferedReader br = Files.newBufferedReader(path)) {
            String line;
            boolean isFirstLine = true; // To skip header
            int lineNumber = 0;
            while ((line = br.readLine()) != null) {
                lineNumber++;
                if (isFirstLine || line.trim().isEmpty()) {
                    isFirstLine = false;
                    continue; // Skip header row and empty lines
                }

                // Regex to split CSV, handling quoted fields with commas/quotes inside
                // Ensure it handles empty fields correctly (e.g., ,,)
                String[] values = line.split(DELIMITER + "(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", -1);

                // Trim whitespace and remove surrounding quotes from each value
                for (int i = 0; i < values.length; i++) {
                    values[i] = values[i].trim();
                    if (values[i].startsWith("\"") && values[i].endsWith("\"")) {
                        // Remove quotes and unescape doubled quotes
                        values[i] = values[i].substring(1, values[i].length() - 1).replace("\"\"", "\"");
                    }
                }

                // Check column count consistency (optional but helpful)
                // Allow flexibility if last column (e.g., visibility) might be missing in older files
                if (values.length < expectedColumns && filename.equals(PROJECT_FILE) && values.length == expectedColumns -1) {
                     // If it's the project file and only the visibility column is missing, pad it
                     String[] paddedValues = Arrays.copyOf(values, expectedColumns);
                     paddedValues[expectedColumns - 1] = "0"; // Default visibility to 0 (Off)
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
            // Consider re-throwing or handling more gracefully depending on severity
        }
        return data;
    }

    // Writes data to CSV, overwriting existing content. Handles escaping.
    private static void writeCsv(String filename, List<String[]> data) {
        Path path = Paths.get(filename);
        try {
             // Ensure directory exists before writing
             Path parent = path.getParent();
             if (parent != null) {
                 Files.createDirectories(parent);
             }

             try (BufferedWriter bw = Files.newBufferedWriter(path, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING)) {
                for (String[] row : data) {
                    String line = Arrays.stream(row)
                                        .map(DataService::escapeCsvField) // Escape each field
                                        .collect(Collectors.joining(DELIMITER));
                    bw.write(line);
                    bw.newLine();
                }
            }
        } catch (IOException e) {
            System.err.println("Error writing file: " + filename + " - " + e.getMessage());
        }
    }

    // Helper to get the correct header array based on filename
    private static String[] getHeaderForFile(String filename) {
        Path p = Paths.get(filename);
        String baseName = p.getFileName().toString();

        if (baseName.equals(Paths.get(APPLICANT_LIST_FILE).getFileName().toString())) return APPLICANT_HEADER;
        if (baseName.equals(Paths.get(OFFICER_LIST_FILE).getFileName().toString())) return OFFICER_HEADER;
        if (baseName.equals(Paths.get(MANAGER_LIST_FILE).getFileName().toString())) return MANAGER_HEADER;
        if (baseName.equals(Paths.get(PROJECT_FILE).getFileName().toString())) return PROJECT_HEADER;
        if (baseName.equals(Paths.get(APPLICATION_FILE).getFileName().toString())) return APPLICATION_HEADER;
        if (baseName.equals(Paths.get(ENQUIRY_FILE).getFileName().toString())) return ENQUIRY_HEADER;
        if (baseName.equals(Paths.get(OFFICER_REGISTRATION_FILE).getFileName().toString())) return OFFICER_REGISTRATION_HEADER;
        return null;
    }

    // Escapes fields containing delimiters, quotes, list delimiters, or newlines for CSV compatibility
    private static String escapeCsvField(String field) {
        if (field == null) return ""; // Represent null as empty string
        // Quote the field if it contains delimiter, quote, list delimiter, or newline characters
        if (field.contains(DELIMITER) || field.contains("\"") || field.contains(LIST_DELIMITER) || field.contains("\n") || field.contains("\r")) {
            // Escape internal quotes by doubling them and enclose the whole field in quotes
            return "\"" + field.replace("\"", "\"\"") + "\"";
        }
        return field; // Return as is if no special characters
    }

    // Parses a date string, returns null if invalid format
    protected static Date parseDate(String dateString) {
        if (dateString == null || dateString.trim().isEmpty() || dateString.trim().equalsIgnoreCase("null")) {
            return null;
        }
        try {
            DATE_FORMAT.setLenient(false); // Enforce strict format yyyy-MM-dd
            return DATE_FORMAT.parse(dateString.trim());
        } catch (ParseException e) {
            System.err.println("Warning: Invalid date format encountered: '" + dateString + "'. Expected yyyy-MM-dd.");
            return null;
        }
    }

    // Formats a date object to string, returns empty string if date is null
    protected static String formatDate(Date date) {
        if (date == null) {
            return ""; // Represent null date as empty string in CSV
        }
        DATE_FORMAT.setLenient(false);
        return DATE_FORMAT.format(date);
    }

    // Parses a potentially quoted, semicolon-delimited list string
    private static List<String> parseListString(String listString) {
        if (listString == null || listString.trim().isEmpty()) {
            return new ArrayList<>();
        }
        String effectiveList = listString.trim();
        // Remove surrounding quotes if present (handle escaped quotes inside)
        if (effectiveList.startsWith("\"") && effectiveList.endsWith("\"")) {
            effectiveList = effectiveList.substring(1, effectiveList.length() - 1).replace("\"\"", "\"");
        }
        // Split by delimiter, trim results, remove empty strings
        return Arrays.stream(effectiveList.split(LIST_DELIMITER))
                     .map(String::trim)
                     .filter(s -> !s.isEmpty())
                     .collect(Collectors.toList());
    }


    // Validates NRIC format
    public static boolean isValidNric(String nric) {
        if (nric == null) return false;
        return NRIC_PATTERN.matcher(nric.trim().toUpperCase()).matches();
    }

    // Gets the current date for application/enquiry timestamps etc.
    public static Date getCurrentDate() {
        // Using Date for simplicity as per original code, though java.time is preferred
        // Can be overridden for testing if needed
        // return fixedDateForTesting != null ? fixedDateForTesting : new Date();
        return new Date();
    }
}

// ==================
// Services (Business Logic - Could be part of Controllers or separate)
// ==================

// Using Controllers directly for logic in this structure.
// If complexity grows, extract logic into dedicated Service classes (e.g., ProjectService, ApplicationService).

// ==================
// Controllers (Handle User Input, Interact with Models/DataService)
// ==================

class AuthController {
    private final Map<String, User> users; // Reference to the main user map

    public AuthController(Map<String, User> users) {
        this.users = users;
    }

    public User login(String nric, String password) {
        if (!DataService.isValidNric(nric)) {
            System.out.println("Invalid NRIC format.");
            return null;
        }
        User user = users.get(nric);
        if (user != null && user.getPassword().equals(password)) {
            return user; // Login successful
        } else if (user != null) {
            System.out.println("Incorrect password.");
            return null; // Wrong password
        } else {
            System.out.println("User NRIC not found.");
            return null; // User doesn't exist
        }
    }

    // Password change logic now resides here, called by views/controllers
    public boolean changePassword(User user, String oldPassword, String newPassword) {
        if (user == null) return false; // Should not happen if called after login

        if (user.getPassword().equals(oldPassword)) {
            if (newPassword != null && !newPassword.isEmpty()) {
                user.setPassword(newPassword);
                // Trigger save immediately after successful change
                DataService.saveUsers(users); // Save the updated user map
                System.out.println("Password changed successfully. Please log in again.");
                return true;
            } else {
                 System.out.println("New password cannot be empty.");
                 return false;
            }
        } else {
            System.out.println("Incorrect old password.");
            return false;
        }
    }
}

// --- Base Controller for common functionalities ---
abstract class BaseController {
    // Use protected final for dependencies injected via constructor
    protected final Map<String, User> users;
    protected final List<Project> projects;
    protected final Map<String, BTOApplication> applications;
    protected final List<Enquiry> enquiries;
    protected final Map<String, OfficerRegistration> officerRegistrations;
    protected final User currentUser;
    protected final Scanner scanner;
    protected final AuthController authController; // For password changes

    // Filter settings saved per user session (could be moved to View state if preferred)
    protected String filterLocation = null;
    protected FlatType filterFlatType = null;

    public BaseController(Map<String, User> users, List<Project> projects, Map<String, BTOApplication> applications, List<Enquiry> enquiries, Map<String, OfficerRegistration> officerRegistrations, User currentUser, Scanner scanner, AuthController authController) {
        this.users = users;
        this.projects = projects;
        this.applications = applications;
        this.enquiries = enquiries;
        this.officerRegistrations = officerRegistrations;
        this.currentUser = currentUser;
        this.scanner = scanner;
        this.authController = authController; // Inject AuthController
    }

    // --- Common Utility Methods ---

    protected Project findProjectByName(String name) {
        if (name == null || name.trim().isEmpty()) return null;
        return projects.stream()
                       .filter(p -> p.getProjectName().equalsIgnoreCase(name.trim()))
                       .findFirst()
                       .orElse(null);
    }

     protected BTOApplication findApplicationByApplicantAndProject(String nric, String projectName) {
         if (nric == null || projectName == null) return null;
        // Use the defined ID format for lookup
        String appId = nric + "_" + projectName;
        return applications.get(appId);
    }

    // Helper to get the project an officer is currently handling (if any)
    protected Project getOfficerHandlingProject(HDBOfficer officer) {
        if (officer == null) return null;
        // Find the APPROVED registration for this officer
        Date today = DataService.getCurrentDate();
        return officerRegistrations.values().stream()
            .filter(reg -> reg.getOfficerNric().equals(officer.getNric()) && reg.getStatus() == OfficerRegistrationStatus.APPROVED)
            .map(reg -> findProjectByName(reg.getProjectName())) // Find the corresponding project
            .filter(Objects::nonNull) // Ensure project exists
            .filter(p -> p.isApplicationPeriodActive(today)) // Check if the project is currently active
            .findFirst() // An officer should only handle one at a time due to overlap rules
            .orElse(null);
    }

    // Helper to check if two projects' application periods overlap
    protected boolean checkDateOverlap(Project p1, Project p2) {
        if (p1 == null || p2 == null || p1.getApplicationOpeningDate() == null || p1.getApplicationClosingDate() == null || p2.getApplicationOpeningDate() == null || p2.getApplicationClosingDate() == null) {
            return false; // Cannot determine overlap if dates are missing
        }
        // Overlap exists if p1 starts before p2 ends AND p1 ends after p2 starts
        // Use !after and !before for inclusive start/end date checks
        // Need to compare end of p1 vs start of p2, and start of p1 vs end of p2
        return !p1.getApplicationOpeningDate().after(p2.getApplicationClosingDate()) &&
               !p1.getApplicationClosingDate().before(p2.getApplicationOpeningDate());
    }


    // --- Project Filtering and Display Logic ---

    /**
     * Gets a list of projects based on current filters and context-specific checks.
     *
     * @param checkVisibility If true, filter out projects marked as not visible (unless user is staff/involved).
     * @param checkEligibility If true, filter based on applicant's age/marital status for flat types.
     * @param checkAvailability If true, filter out projects where no eligible flats have units available.
     * @param checkApplicationPeriod If true, filter out projects whose application period is not active.
     * @param checkNotExpired If true, filter out projects whose application period has passed.
     * @return Filtered list of projects.
     */
     protected List<Project> getFilteredProjects(boolean checkVisibility, boolean checkEligibility, boolean checkAvailability, boolean checkApplicationPeriod, boolean checkNotExpired) {
        Date currentDate = DataService.getCurrentDate();
        return projects.stream()
                // 1. Basic Filters (Location, Flat Type Preference)
                .filter(p -> filterLocation == null || p.getNeighborhood().equalsIgnoreCase(filterLocation))
                .filter(p -> filterFlatType == null || p.getFlatTypes().containsKey(filterFlatType)) // Check if preferred type exists

                // 2. Visibility Filter
                .filter(p -> !checkVisibility || isProjectVisibleToCurrentUser(p))

                // 3. Application Period Filter (Active)
                .filter(p -> !checkApplicationPeriod || p.isApplicationPeriodActive(currentDate))

                // 4. Application Period Filter (Not Expired)
                .filter(p -> !checkNotExpired || !p.isApplicationPeriodExpired(currentDate))

                // 5. Eligibility & Availability Filter (more complex)
                .filter(p -> {
                    if (!checkEligibility && !checkAvailability) return true; // Skip if checks not needed

                    // Skip eligibility checks for Manager
                    if (currentUser instanceof HDBManager) return true;

                    // Check if the current user is eligible for *at least one* flat type offered by the project
                    boolean eligibleForAnyType = p.getFlatTypes().keySet().stream()
                                                  .anyMatch(this::canApplyForFlatType); // Check basic eligibility (age/marital)

                    if (checkEligibility && !eligibleForAnyType) {
                         // If checking eligibility and user isn't eligible for *any* type in project
                         return false;
                    }

                    if (!checkAvailability) return true; // Skip availability check if not needed

                    // Check if *at least one* of the flat types the user is eligible for *also* has available units
                    boolean eligibleAndAvailableExists = p.getFlatTypes().entrySet().stream()
                        .anyMatch(entry -> {
                            FlatType type = entry.getKey();
                            FlatTypeDetails details = entry.getValue();
                            // User must be eligible for this type AND it must have units
                            return canApplyForFlatType(type) && details.getAvailableUnits() > 0;
                        });

                    // If checking availability, must have at least one eligible type with units
                    return eligibleAndAvailableExists;
                })
                .sorted(Comparator.comparing(Project::getProjectName)) // Default sort by name
                .collect(Collectors.toList());
    }

    // Helper to determine if a specific project should be visible to the current user
    protected boolean isProjectVisibleToCurrentUser(Project project) {
        if (currentUser instanceof HDBManager) return true; // Managers see all

        // Check if user has applied to this specific project (any non-final or pending withdrawal status)
        boolean appliedToThis = false;
        if (currentUser instanceof Applicant) {
            Applicant appUser = (Applicant) currentUser;
            appliedToThis = project.getProjectName().equals(appUser.getAppliedProjectName()) &&
                            appUser.getApplicationStatus() != null &&
                            appUser.getApplicationStatus() != ApplicationStatus.UNSUCCESSFUL && // Explicitly unsuccessful
                            appUser.getApplicationStatus() != ApplicationStatus.WITHDRAWN;    // Explicitly withdrawn (after PENDING)
            // PENDING_WITHDRAWAL should still allow viewing
        }


        // Check if user is an approved officer for this project
        boolean isHandlingOfficer = false;
        if (currentUser instanceof HDBOfficer) {
            isHandlingOfficer = officerRegistrations.values().stream()
                .anyMatch(reg -> reg.getOfficerNric().equals(currentUser.getNric()) &&
                                 reg.getProjectName().equals(project.getProjectName()) &&
                                 reg.getStatus() == OfficerRegistrationStatus.APPROVED);
        }

        // Project is visible if:
        // 1. Visibility toggle is ON OR
        // 2. Visibility is OFF, BUT the user has an application (not purely unsuccessful/withdrawn) OR is the handling officer
        return project.isVisible() || appliedToThis || isHandlingOfficer;
    }


     // Check if the current user meets basic criteria to apply for a specific flat type
     protected boolean canApplyForFlatType(FlatType type) {
         if (currentUser instanceof HDBManager) return false; // Managers cannot apply

         if (currentUser.getMaritalStatus() == MaritalStatus.SINGLE) {
             // Single: 35+ and can only apply for 2-Room
             return currentUser.getAge() >= 35 && type == FlatType.TWO_ROOM;
         } else if (currentUser.getMaritalStatus() == MaritalStatus.MARRIED) {
             // Married: 21+ and can apply for 2-Room or 3-Room
             return currentUser.getAge() >= 21 && (type == FlatType.TWO_ROOM || type == FlatType.THREE_ROOM);
         }
         return false; // Should not happen
     }

     // --- UI Interaction Helpers ---

     protected void applyFilters() {
         System.out.println("\n--- Apply/Clear Filters ---");
         System.out.print("Enter neighborhood to filter by (current: " + (filterLocation == null ? "Any" : filterLocation) + ", leave blank to clear): ");
         String loc = scanner.nextLine().trim();
         filterLocation = loc.isEmpty() ? null : loc;

         System.out.print("Enter flat type to filter by (TWO_ROOM, THREE_ROOM, current: " + (filterFlatType == null ? "Any" : filterFlatType) + ", leave blank to clear): ");
         String typeStr = scanner.nextLine().trim();
         if (typeStr.isEmpty()) {
             filterFlatType = null;
         } else {
             try {
                 // Use the robust fromString method
                 FlatType parsedType = FlatType.fromString(typeStr);
                 if (parsedType != null) {
                    filterFlatType = parsedType;
                 } else {
                    System.out.println("Invalid flat type entered. Filter not changed.");
                 }
             } catch (IllegalArgumentException e) {
                 System.out.println("Invalid flat type format. Filter not changed.");
             }
         }
         System.out.println("Filters updated. Current filters: Location=" + (filterLocation == null ? "Any" : filterLocation) + ", FlatType=" + (filterFlatType == null ? "Any" : filterFlatType));
     }

     // Displays a list of projects with details relevant to the current user
     protected void viewAndSelectProject(List<Project> projectList, String prompt) {
         if (projectList.isEmpty()) {
             System.out.println("No projects match the current criteria.");
             return;
         }

         System.out.println("\n--- " + prompt + " ---");
         System.out.println("Current Filters: Location=" + (filterLocation == null ? "Any" : filterLocation) + ", FlatType=" + (filterFlatType == null ? "Any" : filterFlatType));
         System.out.println("--------------------------------------------------------------------------------------------------------------------");
         System.out.printf("%-3s %-15s %-12s %-10s %-10s %-8s %-25s\n", "#", "Project Name", "Neighborhood", "Open", "Close", "Visible", "Flat Types (Available/Total, Price, Eligibility)");
         System.out.println("--------------------------------------------------------------------------------------------------------------------");

         for (int i = 0; i < projectList.size(); i++) {
             Project p = projectList.get(i);
             System.out.printf("%-3d %-15s %-12s %-10s %-10s %-8s ",
                     i + 1,
                     p.getProjectName(),
                     p.getNeighborhood(),
                     DataService.formatDate(p.getApplicationOpeningDate()),
                     DataService.formatDate(p.getApplicationClosingDate()),
                     p.isVisible() ? "On" : "Off");

             // Display flat type details concisely
             String flatDetails = p.getFlatTypes().entrySet().stream()
                 .sorted(Map.Entry.comparingByKey()) // Sort by enum order (2-Room then 3-Room)
                 .map(entry -> {
                     FlatType type = entry.getKey();
                     FlatTypeDetails details = entry.getValue();
                     String eligibilityMark = "";
                     // Show eligibility only if user is Applicant or Officer
                     if (currentUser instanceof Applicant) { // Includes Officer
                         if (!canApplyForFlatType(type)) {
                             eligibilityMark = " (Ineligible)";
                         } else if (details.getAvailableUnits() == 0) {
                              eligibilityMark = " (No Units)";
                         }
                     }
                     return String.format("%s: %d/%d ($%.0f)%s", // Show price without decimals for brevity
                             type.getDisplayName(), details.getAvailableUnits(), details.getTotalUnits(), details.getSellingPrice(), eligibilityMark);
                 })
                 .collect(Collectors.joining(", "));
             System.out.println(flatDetails);

             // Optionally show manager/officer info (maybe only for staff?)
             if (currentUser.getRole() != UserRole.APPLICANT) {
                  System.out.printf("%-3s %-15s %-12s %-10s %-10s %-8s %-25s\n", "", "", "", "", "", "",
                    "Mgr: " + p.getManagerNric() + ", Officers: " + p.getApprovedOfficerNrics().size() + "/" + p.getMaxOfficerSlots());
             }
             if (i < projectList.size() - 1) System.out.println("---"); // Separator between projects

         }
         System.out.println("--------------------------------------------------------------------------------------------------------------------");
     }

     // Prompts user to select a project from the displayed list
     protected Project selectProjectFromList(List<Project> projectList) {
         if (projectList == null || projectList.isEmpty()) return null;
         System.out.print("Enter the number of the project (or 0 to cancel): ");
         int choice;
         try {
             choice = Integer.parseInt(scanner.nextLine());
             if (choice == 0) {
                 System.out.println("Operation cancelled.");
                 return null;
             }
             if (choice >= 1 && choice <= projectList.size()) {
                 return projectList.get(choice - 1);
             } else {
                 System.out.println("Invalid choice number.");
                 return null;
             }
         } catch (NumberFormatException e) {
             System.out.println("Invalid input. Please enter a number.");
             return null;
         }
     }

     // Helper for getting integer input within a range
    protected int getIntInput(String prompt, int min, int max) {
        int value = -1;
        while (true) {
            System.out.print(prompt + " ");
            try {
                value = Integer.parseInt(scanner.nextLine());
                if (value >= min && value <= max) {
                    break;
                } else {
                    System.out.println("Input must be between " + min + " and " + max + ".");
                }
            } catch (NumberFormatException e) {
                System.out.println("Invalid input. Please enter a whole number.");
            }
        }
        return value;
    }

    // Helper for getting double input within a range
     protected double getDoubleInput(String prompt, double min, double max) {
        double value = -1.0;
        while (true) {
            System.out.print(prompt + " ");
            try {
                value = Double.parseDouble(scanner.nextLine());
                 if (value >= min && value <= max) {
                    break;
                } else {
                     System.out.println("Input must be between " + min + " and " + max + ".");
                }
            } catch (NumberFormatException e) {
                System.out.println("Invalid input. Please enter a number.");
            }
        }
        return value;
    }

    // Helper for getting date input
     protected Date getDateInput(String prompt, boolean allowBlank) {
        Date date = null;
        while (true) {
            System.out.print(prompt + " ");
            String input = scanner.nextLine().trim();
             if (input.isEmpty() && allowBlank) {
                 return null; // Allow blank input if specified
             }
             date = DataService.parseDate(input); // Use DataService helper
             if (date != null) {
                 break; // Valid date parsed
             }
             // Error message handled by parseDate
        }
        return date;
    }
}


class ApplicantController extends BaseController {

    public ApplicantController(Map<String, User> users, List<Project> projects, Map<String, BTOApplication> applications, List<Enquiry> enquiries, Map<String, OfficerRegistration> officerRegistrations, User currentUser, Scanner scanner, AuthController authController) {
        super(users, projects, applications, enquiries, officerRegistrations, currentUser, scanner, authController);
    }

    // --- Applicant specific actions ---

    // View projects open for application that the user is eligible for
    public void viewOpenProjects() {
        System.out.println("\n--- Viewing Available BTO Projects ---");
        // Filter: Visible, Eligible, Available Units, Active Application Period, Not Expired
        List<Project> availableProjects = getFilteredProjects(true, true, true, true, true);
        viewAndSelectProject(availableProjects, "Available BTO Projects");
        // No selection needed here, just viewing
    }

    public void applyForProject() {
        Applicant applicant = (Applicant) currentUser; // Safe cast within ApplicantController

        // 1. Check Existing Application/Booking Status
        if (applicant.hasBooked()) {
             System.out.println("You have already booked a flat for project '" + applicant.getAppliedProjectName() + "'. You cannot apply again.");
             return;
         }
        if (applicant.hasActiveApplication()) { // Checks for PENDING or SUCCESSFUL status
            System.out.println("You have an active application for project '" + applicant.getAppliedProjectName() + "' with status: " + applicant.getApplicationStatus());
            System.out.println("You must withdraw (and have it approved) or be unsuccessful before applying again.");
            return;
        }
        if (applicant.hasPendingWithdrawal()) { // Check for pending withdrawal
            System.out.println("You have a withdrawal request pending manager approval for project '" + applicant.getAppliedProjectName() + "'.");
            System.out.println("You cannot apply for a new project until the withdrawal is processed.");
            return;
        }


        // 2. Find Eligible Projects Currently Open for Application
        System.out.println("\n--- Apply for BTO Project ---");
        // Filter: Visible, Eligible, Available Units, Active Application Period, Not Expired
        List<Project> eligibleProjects = getFilteredProjects(true, true, true, true, true);

        if (eligibleProjects.isEmpty()) {
            System.out.println("There are currently no open projects you are eligible to apply for based on filters, eligibility, and unit availability.");
            return;
        }

        // 3. Select Project
        viewAndSelectProject(eligibleProjects, "Select Project to Apply For");
        Project selectedProject = selectProjectFromList(eligibleProjects);
        if (selectedProject == null) return; // User cancelled

        // 4. Officer Specific Checks (if current user is an officer)
         if (currentUser instanceof HDBOfficer) {
             HDBOfficer officer = (HDBOfficer) currentUser;
             // Cannot apply for project they are handling (approved)
             Project handlingProject = getOfficerHandlingProject(officer);
             if (handlingProject != null && selectedProject.equals(handlingProject)) {
                 System.out.println("Error: You cannot apply for a project you are currently handling as an Officer.");
                 return;
             }
             // Cannot apply for project they have pending registration for
             boolean hasPendingRegistration = officerRegistrations.values().stream()
                 .anyMatch(reg -> reg.getOfficerNric().equals(officer.getNric()) &&
                                reg.getProjectName().equals(selectedProject.getProjectName()) &&
                                reg.getStatus() == OfficerRegistrationStatus.PENDING);
             if (hasPendingRegistration) {
                  System.out.println("Error: You cannot apply for a project you have a pending registration for.");
                  return;
             }
             // Note: The check for *approved* registration is covered by the handlingProject check above.
         }

        // 5. Select Flat Type
        FlatType selectedFlatType = selectEligibleFlatType(selectedProject);
        if (selectedFlatType == null) return; // No eligible type selected or available

        // 6. Create Application and Update State
        BTOApplication newApplication = new BTOApplication(currentUser.getNric(), selectedProject.getProjectName(), selectedFlatType, DataService.getCurrentDate());
        applications.put(newApplication.getApplicationId(), newApplication);

        // Update applicant's state in the User object immediately for UI feedback
        applicant.setAppliedProjectName(selectedProject.getProjectName());
        applicant.setApplicationStatus(ApplicationStatus.PENDING);
        applicant.setBookedFlatType(null); // Ensure booked type is cleared

        System.out.println("Application submitted successfully for project '" + selectedProject.getProjectName() + "' (" + selectedFlatType.getDisplayName() + "). Status: PENDING.");

        // 7. Save relevant data
        DataService.saveApplications(applications);
        // User state (appliedProjectName, status) is synced from applications on load/access.
        // No need to save users here unless other profile info changed.
    }

    // Helper to select an eligible and available flat type from a project
    private FlatType selectEligibleFlatType(Project project) {
        List<FlatType> eligibleAndAvailableTypes = project.getFlatTypes().entrySet().stream()
            .filter(entry -> canApplyForFlatType(entry.getKey()) && entry.getValue().getAvailableUnits() > 0)
            .map(Map.Entry::getKey)
            .sorted() // Sort by enum order
            .collect(Collectors.toList());

        if (eligibleAndAvailableTypes.isEmpty()) {
             System.out.println("There are no flat types available in this project that you are eligible for.");
             return null;
        }

        if (eligibleAndAvailableTypes.size() == 1) {
            FlatType onlyOption = eligibleAndAvailableTypes.get(0);
            System.out.println("You will be applying for the only eligible and available type: " + onlyOption.getDisplayName() + ".");
            return onlyOption;
        } else {
            System.out.println("Select the flat type you want to apply for:");
            for (int i = 0; i < eligibleAndAvailableTypes.size(); i++) {
                System.out.println((i + 1) + ". " + eligibleAndAvailableTypes.get(i).getDisplayName());
            }
            System.out.print("Enter choice (or 0 to cancel): ");
            try {
                int typeChoice = Integer.parseInt(scanner.nextLine());
                 if (typeChoice == 0) {
                     System.out.println("Application cancelled.");
                     return null;
                 }
                if (typeChoice >= 1 && typeChoice <= eligibleAndAvailableTypes.size()) {
                    return eligibleAndAvailableTypes.get(typeChoice - 1);
                } else {
                    System.out.println("Invalid choice.");
                    return null;
                }
            } catch (NumberFormatException e) {
                System.out.println("Invalid input.");
                return null;
            }
        }
    }


    public void viewMyApplication() {
        Applicant applicant = (Applicant) currentUser;
        // Sync profile status before displaying (best practice)
        DataService.synchronizeData(users, projects, applications, officerRegistrations); // Ensure profile is up-to-date

        // Use the applicant's profile status as the primary source after sync
        String projectName = applicant.getAppliedProjectName();
        ApplicationStatus status = applicant.getApplicationStatus();

        if (projectName == null || status == null) {
            System.out.println("You do not have any current or past BTO application records.");
            return;
        }

        // Find the specific application record for details (like date, flat type)
        BTOApplication application = findApplicationByApplicantAndProject(applicant.getNric(), projectName);
        if (application == null) {
             System.out.println("Error: Your profile indicates an application, but the detailed record could not be found. Please contact support.");
             return;
        }


        Project project = findProjectByName(projectName); // Find project details

        System.out.println("\n--- Your BTO Application ---");
        System.out.println("Project Name: " + projectName);
        if (project != null) {
            System.out.println("Neighborhood: " + project.getNeighborhood());
        } else {
            System.out.println("Neighborhood: (Project details not found)");
        }
        System.out.println("Flat Type Applied For: " + (application.getFlatTypeApplied() != null ? application.getFlatTypeApplied().getDisplayName() : "N/A"));
        System.out.println("Application Status: " + status); // Display status from synced profile
         if (status == ApplicationStatus.BOOKED && applicant.getBookedFlatType() != null) {
             System.out.println("Booked Flat Type: " + applicant.getBookedFlatType().getDisplayName());
         }
         System.out.println("Application Date: " + DataService.formatDate(application.getApplicationDate()));
    }

    public void requestWithdrawal() {
        Applicant applicant = (Applicant) currentUser;
        // Sync profile status first
        DataService.synchronizeData(users, projects, applications, officerRegistrations);

        // Find the application based on the synced profile state
        String currentProject = applicant.getAppliedProjectName();
        ApplicationStatus currentStatus = applicant.getApplicationStatus();

        if (currentProject == null || currentStatus == null) {
             System.out.println("You do not have an application to withdraw.");
             return;
        }

        // Check if eligible for withdrawal request (PENDING, SUCCESSFUL, BOOKED)
        if (currentStatus != ApplicationStatus.PENDING &&
            currentStatus != ApplicationStatus.SUCCESSFUL &&
            currentStatus != ApplicationStatus.BOOKED) {
            System.out.println("Your application status (" + currentStatus + ") is not eligible for withdrawal request.");
            System.out.println("You can only request withdrawal if your status is PENDING, SUCCESSFUL, or BOOKED.");
            return;
        }

        // Find the application object
        BTOApplication application = findApplicationByApplicantAndProject(applicant.getNric(), currentProject);
        if (application == null) {
             System.out.println("Error: Could not find the application record to request withdrawal. Please contact support.");
             return;
        }

        System.out.println("\n--- Request Application Withdrawal ---");
        System.out.println("Project: " + application.getProjectName());
        System.out.println("Current Status: " + currentStatus);
        System.out.print("Are you sure you want to request withdrawal for this application? Manager approval is required. (yes/no): ");
        String confirm = scanner.nextLine().trim().toLowerCase();

        if (confirm.equals("yes")) {
            // Update application status to PENDING_WITHDRAWAL
            // The setStatus method now handles storing the previous status
            application.setStatus(ApplicationStatus.PENDING_WITHDRAWAL);

            // Update applicant's profile status immediately for UI consistency
            applicant.setApplicationStatus(ApplicationStatus.PENDING_WITHDRAWAL);
            // DO NOT clear booked flat type or release unit here - Manager handles on approval

            System.out.println("Withdrawal request submitted successfully.");
            System.out.println("Your application status is now PENDING_WITHDRAWAL and requires Manager approval.");

            // Save application data
            DataService.saveApplications(applications);
            // No need to save projects (unit not released yet)
            // User profile is synced on load/access

        } else {
            System.out.println("Withdrawal request cancelled.");
        }
    }

    // --- Enquiry Management ---

    public void submitEnquiry() {
        System.out.println("\n--- Submit Enquiry ---");
        // List projects user can see (optional, could allow enquiry about any project name)
        // Filter: Visible=true, Eligibility=false, Availability=false, Period=false, NotExpired=false -> Show all potentially visible
        List<Project> viewableProjects = getFilteredProjects(true, false, false, false, false);
        Project selectedProject = null;

        if (!viewableProjects.isEmpty()) {
            viewAndSelectProject(viewableProjects, "Select Project to Enquire About (Optional)");
            selectedProject = selectProjectFromList(viewableProjects); // Returns null if user enters 0 or invalid
        }

        String projectNameInput;
        if (selectedProject != null) {
            projectNameInput = selectedProject.getProjectName();
            System.out.println("Enquiring about: " + projectNameInput);
        } else {
             if (!viewableProjects.isEmpty()) System.out.println("No project selected from list.");
             System.out.print("Enter the exact Project Name you want to enquire about: ");
             projectNameInput = scanner.nextLine().trim();
             // Validate if project exists? Optional, maybe allow enquiry about non-listed/past projects.
             if (findProjectByName(projectNameInput) == null) {
                 System.out.println("Warning: Project '" + projectNameInput + "' not found in current listings, but submitting enquiry anyway.");
             }
             if (projectNameInput.isEmpty()) {
                  System.out.println("Project name cannot be empty. Enquiry cancelled.");
                  return;
             }
        }


        System.out.print("Enter your enquiry text (cannot be empty): ");
        String text = scanner.nextLine().trim();

        if (!text.isEmpty()) {
            Enquiry newEnquiry = new Enquiry(currentUser.getNric(), projectNameInput, text, DataService.getCurrentDate());
            enquiries.add(newEnquiry);
            System.out.println("Enquiry submitted successfully (ID: " + newEnquiry.getEnquiryId() + ").");
            // Save enquiries
            DataService.saveEnquiries(enquiries);
        } else {
            System.out.println("Enquiry text cannot be empty. Enquiry not submitted.");
        }
    }

    public void viewMyEnquiries() {
        System.out.println("\n--- Your Enquiries ---");
        List<Enquiry> myEnquiries = enquiries.stream()
                                            .filter(e -> e.getApplicantNric().equals(currentUser.getNric()))
                                            .sorted(Comparator.comparing(Enquiry::getEnquiryDate).reversed())
                                            .collect(Collectors.toList());

        if (myEnquiries.isEmpty()) {
            System.out.println("You have not submitted any enquiries.");
            return;
        }

        for (int i = 0; i < myEnquiries.size(); i++) {
            Enquiry e = myEnquiries.get(i);
            System.out.printf("%d. ID: %s | Project: %s | Date: %s\n",
                    i + 1, e.getEnquiryId(), e.getProjectName(), DataService.formatDate(e.getEnquiryDate()));
            System.out.println("   Enquiry: " + e.getEnquiryText());
            if (e.isReplied()) {
                System.out.printf("   Reply (by %s on %s): %s\n",
                        e.getRepliedByNric() != null ? e.getRepliedByNric() : "N/A",
                        e.getReplyDate() != null ? DataService.formatDate(e.getReplyDate()) : "N/A",
                        e.getReplyText());
            } else {
                System.out.println("   Reply: (Pending)");
            }
             System.out.println("----------------------------------------");
        }
    }

    public void editMyEnquiry() {
        System.out.println("\n--- Edit Enquiry ---");
        List<Enquiry> editableEnquiries = enquiries.stream()
                                                .filter(e -> e.getApplicantNric().equals(currentUser.getNric()) && !e.isReplied())
                                                .sorted(Comparator.comparing(Enquiry::getEnquiryDate).reversed())
                                                .collect(Collectors.toList());

        if (editableEnquiries.isEmpty()) {
            System.out.println("You have no enquiries that can be edited (must not be replied to yet).");
            return;
        }

        System.out.println("Select enquiry to edit:");
         for (int i = 0; i < editableEnquiries.size(); i++) {
            Enquiry e = editableEnquiries.get(i);
            System.out.printf("%d. ID: %s | Project: %s | Text: %s\n",
                    i + 1, e.getEnquiryId(), e.getProjectName(), e.getEnquiryText());
        }
         System.out.print("Enter choice (or 0 to cancel): ");
         try {
             int choice = Integer.parseInt(scanner.nextLine());
              if (choice == 0) {
                  System.out.println("Operation cancelled.");
                  return;
              }
             if (choice >= 1 && choice <= editableEnquiries.size()) {
                 Enquiry enquiryToEdit = editableEnquiries.get(choice - 1);
                 System.out.print("Enter new enquiry text: ");
                 String newText = scanner.nextLine().trim();
                 if (enquiryToEdit.setEnquiryText(newText)) { // Use setter which includes validation
                     System.out.println("Enquiry updated successfully.");
                     // Save enquiries
                     DataService.saveEnquiries(enquiries);
                 } // Error messages handled by setter
             } else {
                 System.out.println("Invalid choice.");
             }
         } catch (NumberFormatException e) {
             System.out.println("Invalid input.");
         }
    }

    public void deleteMyEnquiry() {
         System.out.println("\n--- Delete Enquiry ---");
        List<Enquiry> deletableEnquiries = enquiries.stream()
                                                .filter(e -> e.getApplicantNric().equals(currentUser.getNric()) && !e.isReplied())
                                                .sorted(Comparator.comparing(Enquiry::getEnquiryDate).reversed())
                                                .collect(Collectors.toList());

        if (deletableEnquiries.isEmpty()) {
            System.out.println("You have no enquiries that can be deleted (must not be replied to yet).");
            return;
        }

        System.out.println("Select enquiry to delete:");
         for (int i = 0; i < deletableEnquiries.size(); i++) {
            Enquiry e = deletableEnquiries.get(i);
            System.out.printf("%d. ID: %s | Project: %s | Text: %s\n",
                    i + 1, e.getEnquiryId(), e.getProjectName(), e.getEnquiryText());
        }
         System.out.print("Enter choice (or 0 to cancel): ");
         try {
             int choice = Integer.parseInt(scanner.nextLine());
              if (choice == 0) {
                  System.out.println("Operation cancelled.");
                  return;
              }
             if (choice >= 1 && choice <= deletableEnquiries.size()) {
                 Enquiry enquiryToDelete = deletableEnquiries.get(choice - 1);
                 System.out.print("Are you sure you want to delete enquiry " + enquiryToDelete.getEnquiryId() + "? (yes/no): ");
                 String confirm = scanner.nextLine().trim().toLowerCase();
                 if (confirm.equals("yes")) {
                     if (enquiries.remove(enquiryToDelete)) {
                         System.out.println("Enquiry deleted successfully.");
                         // Save enquiries
                         DataService.saveEnquiries(enquiries);
                     } else {
                          System.err.println("Error: Failed to remove enquiry from list.");
                     }
                 } else {
                     System.out.println("Deletion cancelled.");
                 }
             } else {
                 System.out.println("Invalid choice.");
             }
         } catch (NumberFormatException e) {
             System.out.println("Invalid input.");
         }
    }
}

class OfficerController extends ApplicantController { // Inherits Applicant actions & state

    public OfficerController(Map<String, User> users, List<Project> projects, Map<String, BTOApplication> applications, List<Enquiry> enquiries, Map<String, OfficerRegistration> officerRegistrations, User currentUser, Scanner scanner, AuthController authController) {
        super(users, projects, applications, enquiries, officerRegistrations, currentUser, scanner, authController);
    }

    // --- Officer specific actions ---

    public void registerForProject() {
        HDBOfficer officer = (HDBOfficer) currentUser; // Safe cast
        Date currentDate = DataService.getCurrentDate();
        // Sync profile before checks
        DataService.synchronizeData(users, projects, applications, officerRegistrations);

        // 1. Check Eligibility: Cannot register if has active BTO application or pending withdrawal
        if (officer.hasActiveApplication()) {
            System.out.println("Error: Cannot register to handle a project while you have an active BTO application (" + officer.getAppliedProjectName() + ", Status: " + officer.getApplicationStatus() + ").");
            return;
        }
        if (officer.hasPendingWithdrawal()) {
            System.out.println("Error: Cannot register to handle a project while you have a pending withdrawal request.");
            return;
        }


        // 2. Find Projects Available for Registration
        System.out.println("\n--- Register to Handle Project ---");

        // Find projects officer is currently handling (approved)
         Project currentlyHandlingProject = getOfficerHandlingProject(officer);

        // Find projects officer has pending registrations for
        List<Project> pendingRegistrationProjects = officerRegistrations.values().stream()
            .filter(reg -> reg.getOfficerNric().equals(officer.getNric()) && reg.getStatus() == OfficerRegistrationStatus.PENDING)
            .map(reg -> findProjectByName(reg.getProjectName()))
            .filter(Objects::nonNull)
            .collect(Collectors.toList());


        List<Project> availableProjects = projects.stream()
                // Basic criteria: Has slots, officer not already registered for *this* project, project not expired
                .filter(p -> p.getRemainingOfficerSlots() > 0)
                .filter(p -> !p.isApplicationPeriodExpired(currentDate)) // Check not expired
                .filter(p -> officerRegistrations.values().stream() // Check not already registered (any status) for this project
                                .noneMatch(reg -> reg.getOfficerNric().equals(officer.getNric()) &&
                                                  reg.getProjectName().equals(p.getProjectName())))
                // Conflict Check 1: Cannot register if already handling a project with overlapping dates
                .filter(p -> currentlyHandlingProject == null || !checkDateOverlap(p, currentlyHandlingProject))
                // Conflict Check 2: Cannot register if pending for another project with overlapping dates
                .filter(p -> pendingRegistrationProjects.stream()
                                .noneMatch(pendingProject -> checkDateOverlap(p, pendingProject)))
                // Conflict Check 3: Cannot register for a project they have *ever* applied for (any status, including PENDING_WITHDRAWAL etc.)
                 .filter(p -> applications.values().stream()
                                .noneMatch(app -> app.getApplicantNric().equals(officer.getNric()) &&
                                                  app.getProjectName().equals(p.getProjectName())))
                .sorted(Comparator.comparing(Project::getProjectName))
                .collect(Collectors.toList());

        if (availableProjects.isEmpty()) {
            System.out.println("No projects currently available for you to register for based on eligibility criteria:");
            System.out.println("- Project must have open officer slots and not be expired.");
            System.out.println("- You must not already have a registration (Pending/Approved/Rejected) for the project.");
            System.out.println("- You cannot have an active BTO application (Pending/Successful) or Pending Withdrawal.");
            System.out.println("- You cannot register if the project's dates overlap with a project you are already handling or have a pending registration for.");
             System.out.println("- You cannot register for a project you have previously applied for.");
            return;
        }

        // 3. Select Project and Submit Registration
        // Show projects regardless of visibility toggle for officers
        viewAndSelectProject(availableProjects, "Select Project to Register For");
        Project selectedProject = selectProjectFromList(availableProjects);

        if (selectedProject != null) {
            // Create registration record
            OfficerRegistration newRegistration = new OfficerRegistration(officer.getNric(), selectedProject.getProjectName(), currentDate);
            officerRegistrations.put(newRegistration.getRegistrationId(), newRegistration);
            System.out.println("Registration request submitted for project '" + selectedProject.getProjectName() + "'. Status: PENDING approval by Manager.");
            // Save registrations
            DataService.saveOfficerRegistrations(officerRegistrations);
        }
    }

    public void viewRegistrationStatus() {
        HDBOfficer officer = (HDBOfficer) currentUser;
        System.out.println("\n--- Your HDB Officer Registration Status ---");

        // Show currently handled project first
        Project handlingProject = getOfficerHandlingProject(officer);
        if (handlingProject != null) {
             System.out.println("You are currently APPROVED and HANDLING project: " + handlingProject.getProjectName());
             System.out.println("----------------------------------------");
        }

        // Show other registrations (Pending, Rejected, or Approved but maybe for past projects)
        List<OfficerRegistration> myRegistrations = officerRegistrations.values().stream()
                .filter(reg -> reg.getOfficerNric().equals(officer.getNric()))
                // Exclude the currently handled one if shown above
                .filter(reg -> handlingProject == null || !reg.getProjectName().equals(handlingProject.getProjectName()))
                .sorted(Comparator.comparing(OfficerRegistration::getRegistrationDate).reversed())
                .collect(Collectors.toList());

        if (myRegistrations.isEmpty() && handlingProject == null) {
            System.out.println("You have no past or pending registration requests.");
        } else if (!myRegistrations.isEmpty()) {
            System.out.println("Other Registration History/Requests:");
            for (OfficerRegistration reg : myRegistrations) {
                System.out.printf("- Project: %-15s | Status: %-10s | Date: %s\n",
                        reg.getProjectName(), reg.getStatus(), DataService.formatDate(reg.getRegistrationDate()));
            }
        }
    }

    public void viewHandlingProjectDetails() {
        HDBOfficer officer = (HDBOfficer) currentUser;
        Project project = getOfficerHandlingProject(officer);

        if (project == null) {
            System.out.println("You are not currently handling any project. Register for one first.");
            return;
        }

        System.out.println("\n--- Details for Handling Project: " + project.getProjectName() + " ---");
        // Use the standard display method, which shows relevant info.
        // Officers see projects they handle regardless of visibility toggle.
        viewAndSelectProject(Collections.singletonList(project), "Project Details");
        // Officers cannot edit details.
    }

    public void viewAndReplyToEnquiries() {
         HDBOfficer officer = (HDBOfficer) currentUser;
         Project handlingProject = getOfficerHandlingProject(officer);

         if (handlingProject == null) {
             System.out.println("You need to be handling a project to view and reply to its enquiries.");
             return;
         }
         String handlingProjectName = handlingProject.getProjectName();

         System.out.println("\n--- Enquiries for Project: " + handlingProjectName + " ---");
         List<Enquiry> projectEnquiries = enquiries.stream()
                 .filter(e -> e.getProjectName().equalsIgnoreCase(handlingProjectName))
                 .sorted(Comparator.comparing(Enquiry::getEnquiryDate).reversed()) // Show newest first
                 .collect(Collectors.toList());

         if (projectEnquiries.isEmpty()) {
             System.out.println("No enquiries found for this project.");
             return;
         }

         // Separate unreplied for selection
         List<Enquiry> unrepliedEnquiries = projectEnquiries.stream()
                                                            .filter(e -> !e.isReplied())
                                                            .collect(Collectors.toList());

         System.out.println("--- Unreplied Enquiries ---");
         if (unrepliedEnquiries.isEmpty()) {
             System.out.println("(None)");
         } else {
             for (int i = 0; i < unrepliedEnquiries.size(); i++) {
                 Enquiry e = unrepliedEnquiries.get(i);
                 System.out.printf("%d. ID: %s | Applicant: %s | Date: %s\n",
                         i + 1, e.getEnquiryId(), e.getApplicantNric(), DataService.formatDate(e.getEnquiryDate()));
                 System.out.println("   Enquiry: " + e.getEnquiryText());
                 System.out.println("---");
             }
             System.out.print("Enter the number of the enquiry to reply to (or 0 to skip): ");
             try {
                 int choice = Integer.parseInt(scanner.nextLine());
                 if (choice >= 1 && choice <= unrepliedEnquiries.size()) {
                     Enquiry enquiryToReply = unrepliedEnquiries.get(choice - 1);
                     System.out.print("Enter your reply: ");
                     String replyText = scanner.nextLine().trim();
                     if (enquiryToReply.setReply(replyText, currentUser.getNric(), DataService.getCurrentDate())) {
                         System.out.println("Reply submitted successfully.");
                         // Save enquiries
                         DataService.saveEnquiries(enquiries);
                     } // Error messages handled by setter
                 } else if (choice != 0) {
                     System.out.println("Invalid choice.");
                 }
             } catch (NumberFormatException e) {
                 System.out.println("Invalid input.");
             }
         }

         // Display replied enquiries for reference
         System.out.println("\n--- Replied Enquiries ---");
         List<Enquiry> repliedEnquiries = projectEnquiries.stream()
                                                          .filter(Enquiry::isReplied)
                                                          .collect(Collectors.toList());
         if (repliedEnquiries.isEmpty()) {
             System.out.println("(None)");
         } else {
             for (Enquiry e : repliedEnquiries) {
                 System.out.printf("ID: %s | Applicant: %s | Enquiry Date: %s\n",
                         e.getEnquiryId(), e.getApplicantNric(), DataService.formatDate(e.getEnquiryDate()));
                 System.out.println("   Enquiry: " + e.getEnquiryText());
                 System.out.printf("   Reply (by %s on %s): %s\n",
                         e.getRepliedByNric(),
                         e.getReplyDate() != null ? DataService.formatDate(e.getReplyDate()) : "N/A",
                         e.getReplyText());
                 System.out.println("--------------------");
             }
         }
    }

    public void manageFlatBooking() {
        HDBOfficer officer = (HDBOfficer) currentUser;
        Project project = getOfficerHandlingProject(officer);

        if (project == null) {
            System.out.println("You need to be handling a project to manage flat bookings.");
            return;
        }
        String handlingProjectName = project.getProjectName();

        System.out.println("\n--- Flat Booking Management for Project: " + handlingProjectName + " ---");

        // Find SUCCESSFUL applications for this project
        List<BTOApplication> successfulApps = applications.values().stream()
            .filter(app -> app.getProjectName().equals(handlingProjectName) && app.getStatus() == ApplicationStatus.SUCCESSFUL)
            .sorted(Comparator.comparing(BTOApplication::getApplicationDate)) // Optional: sort by date
            .collect(Collectors.toList());

        if (successfulApps.isEmpty()) {
            System.out.println("No applicants with status SUCCESSFUL found for this project.");
            return;
        }

        System.out.println("Applicants with SUCCESSFUL status (ready for booking):");
        for (int i = 0; i < successfulApps.size(); i++) {
             BTOApplication app = successfulApps.get(i);
             User applicantUser = users.get(app.getApplicantNric());
             System.out.printf("%d. NRIC: %s | Name: %-15s | Applied Type: %s | App Date: %s\n",
                     i + 1,
                     app.getApplicantNric(),
                     applicantUser != null ? applicantUser.getName() : "N/A",
                     app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A",
                     DataService.formatDate(app.getApplicationDate()));
        }

        System.out.print("Enter the number of the applicant to process booking for (or 0 to cancel): ");
        int choice;
         try {
             choice = Integer.parseInt(scanner.nextLine());
              if (choice == 0) {
                  System.out.println("Operation cancelled.");
                  return;
              }
             if (choice < 1 || choice > successfulApps.size()) {
                  System.out.println("Invalid choice number.");
                  return;
             }
         } catch (NumberFormatException e) {
             System.out.println("Invalid input. Please enter a number.");
             return;
         }

        BTOApplication applicationToBook = successfulApps.get(choice - 1);
        User applicantUser = users.get(applicationToBook.getApplicantNric());

        // Double check applicant exists and is Applicant/Officer type
        if (!(applicantUser instanceof Applicant)) {
            System.out.println("Error: Applicant data not found or invalid for NRIC " + applicationToBook.getApplicantNric());
            return;
        }
        Applicant applicant = (Applicant) applicantUser;

        // Double check status is still SUCCESSFUL (should be, but safeguard)
        if (applicationToBook.getStatus() != ApplicationStatus.SUCCESSFUL) {
            System.out.println("Error: Applicant status is no longer SUCCESSFUL (Current: " + applicationToBook.getStatus() + "). Cannot proceed.");
            return;
        }
        // Check if applicant somehow already booked (shouldn't happen if list is filtered correctly)
         if (applicant.hasBooked()) {
             System.out.println("Error: Applicant " + applicant.getNric() + " has already booked a flat according to their profile.");
             // Potentially sync application status here if profile is out of sync
             // applicationToBook.setStatus(applicant.getApplicationStatus());
             // DataService.saveApplications(applications);
             return;
         }

        FlatType appliedFlatType = applicationToBook.getFlatTypeApplied();
        if (appliedFlatType == null) {
             System.out.println("Error: Application record does not have a valid flat type specified. Cannot book.");
             return;
        }

        FlatTypeDetails details = project.getMutableFlatTypeDetails(appliedFlatType);
        // Check availability AGAIN right before booking
        if (details == null || details.getAvailableUnits() <= 0) {
            System.out.println("Error: No available units for the applied flat type (" + appliedFlatType.getDisplayName() + ") at this moment. Booking cannot proceed.");
            // This might happen if multiple officers try to book concurrently or if data is stale.
            return;
        }

        System.out.println("\n--- Confirm Booking ---");
        System.out.println("Applicant: " + applicant.getName() + " (" + applicant.getNric() + ")");
        System.out.println("Project: " + applicationToBook.getProjectName());
        System.out.println("Flat Type: " + appliedFlatType.getDisplayName());
        System.out.println("Available Units Before Booking: " + details.getAvailableUnits());
        System.out.printf("Selling Price: $%.2f\n", details.getSellingPrice());

        System.out.print("\nConfirm booking for this applicant? (yes/no): ");
        String confirm = scanner.nextLine().trim().toLowerCase();

        if (confirm.equals("yes")) {
            // 1. Decrement project unit count *first* (attempt to reserve)
            if (!details.decrementAvailableUnits()) {
                 System.out.println("Error: Failed to decrement unit count (possibly became zero just now). Booking cancelled.");
                 return; // Failed to reserve unit
            }

            // 2. Update application status
            applicationToBook.setStatus(ApplicationStatus.BOOKED);

            // 3. Update applicant profile (user object) - Sync will handle this, but update for immediate feedback
            applicant.setApplicationStatus(ApplicationStatus.BOOKED);
            applicant.setBookedFlatType(appliedFlatType); // Set the booked type

            System.out.println("Booking confirmed successfully!");
            System.out.println("Applicant status updated to BOOKED.");
            System.out.println("Remaining units for " + appliedFlatType.getDisplayName() + ": " + details.getAvailableUnits());

            // 4. Generate Receipt (display on console)
            generateBookingReceipt(applicant, applicationToBook, project);

            // 5. Save all modified data
            DataService.saveApplications(applications);
            DataService.saveProjects(projects); // Unit count changed
            // User state derived on load, no need to save users unless profile changed

        } else {
            System.out.println("Booking cancelled.");
        }
    }

    // Generates and prints a simple booking receipt to console
    private void generateBookingReceipt(Applicant applicant, BTOApplication application, Project project) {
        System.out.println("\n================ BTO Booking Receipt ================");
        System.out.println(" Receipt Generated: " + DataService.formatDate(DataService.getCurrentDate()) + " by Officer " + currentUser.getNric());
        System.out.println("-----------------------------------------------------");
        System.out.println(" Applicant Details:");
        System.out.println("   Name:          " + applicant.getName());
        System.out.println("   NRIC:          " + applicant.getNric());
        System.out.println("   Age:           " + applicant.getAge());
        System.out.println("   Marital Status:" + applicant.getMaritalStatus());
        System.out.println("-----------------------------------------------------");
        System.out.println(" Booking Details:");
        System.out.println("   Project Name:  " + project.getProjectName());
        System.out.println("   Neighborhood:  " + project.getNeighborhood());
        System.out.println("   Booked Flat:   " + (application.getFlatTypeApplied() != null ? application.getFlatTypeApplied().getDisplayName() : "N/A"));
        FlatTypeDetails details = project.getFlatTypeDetails(application.getFlatTypeApplied());
        if (details != null) {
             System.out.printf("   Selling Price: $%.2f\n", details.getSellingPrice());
        } else {
             System.out.println("   Selling Price: N/A");
        }
        System.out.println("   Booking Status:" + application.getStatus());
        System.out.println("   Application ID:" + application.getApplicationId());
        System.out.println("-----------------------------------------------------");
        System.out.println(" Thank you for choosing HDB!");
        System.out.println("=====================================================");
    }
}

class ManagerController extends BaseController {

    public ManagerController(Map<String, User> users, List<Project> projects, Map<String, BTOApplication> applications, List<Enquiry> enquiries, Map<String, OfficerRegistration> officerRegistrations, User currentUser, Scanner scanner, AuthController authController) {
        super(users, projects, applications, enquiries, officerRegistrations, currentUser, scanner, authController);
    }

    // --- Manager specific actions ---

    public void createProject() {
        HDBManager manager = (HDBManager) currentUser; // Safe cast

        // Requirement 18: "System prevents assigning more than one project to a manager within the same application dates"
        // Clarification: Check against *active* projects (Visible + Within App Period) managed by this manager.

        System.out.println("\n--- Create New BTO Project ---");

        // 1. Get Project Name (Unique)
        String projectName;
        while (true) {
            System.out.print("Enter Project Name: ");
            projectName = scanner.nextLine().trim();
            if (projectName.isEmpty()) {
                System.out.println("Project name cannot be empty.");
            } else if (findProjectByName(projectName) != null) {
                System.out.println("Project name already exists. Please choose a unique name.");
            } else {
                break;
            }
        }

        // 2. Get Other Details
        System.out.print("Enter Neighborhood: ");
        String neighborhood = scanner.nextLine().trim();
        if (neighborhood.isEmpty()) {
             System.out.println("Neighborhood cannot be empty. Creation cancelled.");
             return;
        }

        // 3. Get Flat Type Details
        Map<FlatType, FlatTypeDetails> flatTypes = new HashMap<>();
        System.out.println("--- Flat Type Details ---");
        // 2-Room
        int units2Room = getIntInput("Enter total number of 2-Room units (0 if none): ", 0, 9999);
        if (units2Room > 0) {
            double price2Room = getDoubleInput("Enter selling price for 2-Room units: $", 0, Double.MAX_VALUE);
            flatTypes.put(FlatType.TWO_ROOM, new FlatTypeDetails(units2Room, units2Room, price2Room));
        }
        // 3-Room
        int units3Room = getIntInput("Enter total number of 3-Room units (0 if none): ", 0, 9999);
        if (units3Room > 0) {
            double price3Room = getDoubleInput("Enter selling price for 3-Room units: $", 0, Double.MAX_VALUE);
            flatTypes.put(FlatType.THREE_ROOM, new FlatTypeDetails(units3Room, units3Room, price3Room));
        }

        if (flatTypes.isEmpty()) {
            System.out.println("Error: Project must have at least one type of flat (2-Room or 3-Room). Creation cancelled.");
            return;
        }

        // 4. Get Dates and Validate Overlap (against *active* projects)
        Date openingDate;
        Date closingDate;
        Date currentDate = DataService.getCurrentDate();
        while (true) {
            openingDate = getDateInput("Enter Application Opening Date (yyyy-MM-dd): ", false);
            closingDate = getDateInput("Enter Application Closing Date (yyyy-MM-dd): ", false);

            if (openingDate == null || closingDate == null) {
                 System.out.println("Dates cannot be empty. Please re-enter.");
                 continue;
            }
            if (closingDate.before(openingDate)) {
                System.out.println("Closing date cannot be before opening date. Please re-enter.");
                continue;
            }

            // Create a temporary project object with the proposed dates for overlap check
            Project proposedProjectDates = new Project(
                "__temp__", "__temp__", flatTypes, openingDate, closingDate, manager.getNric(), 0, null, true // Assume visible for check
            );

            // Check for overlap ONLY with existing *active* managed projects (Visible AND within App Period)
            boolean overlapsWithActive = projects.stream()
                .filter(p -> p.getManagerNric().equals(manager.getNric())) // Managed by this manager
                .filter(p -> p.isActive(currentDate)) // Is currently active (Visible + In App Period)
                .anyMatch(existingActiveProject -> checkDateOverlap(proposedProjectDates, existingActiveProject));

            if (overlapsWithActive) {
                 System.out.println("Error: The specified application period overlaps with another *active* project (Visible & Within App Period) you manage. Please enter different dates or manage the visibility/dates of the existing project.");
            } else {
                break; // Dates are valid and non-overlapping with active projects
            }
        }


        // 5. Get Officer Slots
        int maxOfficers = getIntInput("Enter Maximum HDB Officer Slots (1-10): ", 1, 10);

        // 6. Create Project (Visibility defaults to OFF)
        Project newProject = new Project(projectName, neighborhood, flatTypes, openingDate, closingDate,
                                         currentUser.getNric(), maxOfficers, new ArrayList<>(), false);
        projects.add(newProject);

        System.out.println("Project '" + projectName + "' created successfully. Visibility is currently OFF.");
        // Save projects
        DataService.saveProjects(projects);
    }

    public void editProject() {
        System.out.println("\n--- Edit BTO Project ---");
        List<Project> myProjects = getManagedProjects(false); // Get managed projects, ignore filters for selection
        if (myProjects.isEmpty()) {
             System.out.println("You are not managing any projects.");
             return;
        }

        viewAndSelectProject(myProjects, "Select Project to Edit");
        Project projectToEdit = selectProjectFromList(myProjects);
        if (projectToEdit == null) return; // Cancelled

        System.out.println("Editing Project: " + projectToEdit.getProjectName() + " (Leave blank to keep current value)");

        // Edit Neighborhood
        System.out.print("Enter new Neighborhood [" + projectToEdit.getNeighborhood() + "]: ");
        String newNeighborhood = scanner.nextLine().trim();
        if (!newNeighborhood.isEmpty()) projectToEdit.setNeighborhood(newNeighborhood);

        // Edit Flat Types (Only Price for simplicity, Total Units is hard to change after launch)
        Map<FlatType, FlatTypeDetails> currentFlatTypes = projectToEdit.getFlatTypes(); // Get unmodifiable map
        Map<FlatType, FlatTypeDetails> newFlatTypesMap = new HashMap<>(); // Create a mutable copy to modify

         // Copy existing details first
         currentFlatTypes.forEach((type, details) ->
             newFlatTypesMap.put(type, new FlatTypeDetails(details.getTotalUnits(), details.getAvailableUnits(), details.getSellingPrice()))
         );

        for (FlatType type : FlatType.values()) {
             FlatTypeDetails currentDetails = newFlatTypesMap.get(type); // Get from mutable map
             if (currentDetails != null) { // Only edit if type exists in project
                 System.out.println("--- Edit " + type.getDisplayName() + " ---");
                 double currentPrice = currentDetails.getSellingPrice();
                 System.out.print("Enter new selling price [" + String.format("%.2f", currentPrice) + "] (leave blank to keep): $");
                 String priceInput = scanner.nextLine().trim();
                 if (!priceInput.isEmpty()) {
                     try {
                         double newPrice = Double.parseDouble(priceInput);
                         if (newPrice >= 0) {
                             currentDetails.setSellingPrice(newPrice); // Modify the detail in the mutable map
                         } else {
                             System.out.println("Price cannot be negative. Keeping original price.");
                         }
                     } catch (NumberFormatException e) {
                         System.out.println("Invalid price format. Keeping original price.");
                     }
                 }
             }
        }
        projectToEdit.setFlatTypes(newFlatTypesMap); // Set the modified map back


        // Edit Dates (Validate non-overlap with other *active* projects if changed)
        Date originalOpening = projectToEdit.getApplicationOpeningDate();
        Date originalClosing = projectToEdit.getApplicationClosingDate();
        Date newOpeningDate = getDateInput("Enter new Opening Date (yyyy-MM-dd) [" + DataService.formatDate(originalOpening) + "] (leave blank to keep): ", true);
        Date newClosingDate = getDateInput("Enter new Closing Date (yyyy-MM-dd) [" + DataService.formatDate(originalClosing) + "] (leave blank to keep): ", true);

        // Use new dates if provided, otherwise stick to originals
        Date finalOpening = (newOpeningDate != null) ? newOpeningDate : originalOpening;
        Date finalClosing = (newClosingDate != null) ? newClosingDate : originalClosing;
        Date currentDate = DataService.getCurrentDate();

        boolean datesChanged = (newOpeningDate != null || newClosingDate != null);
        boolean datesValid = true;

        if (finalClosing.before(finalOpening)) {
             System.out.println("Error: Closing date cannot be before opening date. Dates not updated.");
             datesValid = false;
        }

        // If dates changed, re-check overlap, excluding the project being edited itself, against other *active* projects
        if (datesChanged && datesValid) {
             // Create a temporary project object with the proposed dates for overlap check
             Project proposedProjectDates = new Project(
                 projectToEdit.getProjectName(), projectToEdit.getNeighborhood(), projectToEdit.getFlatTypes(),
                 finalOpening, finalClosing, projectToEdit.getManagerNric(), projectToEdit.getMaxOfficerSlots(),
                 projectToEdit.getApprovedOfficerNrics(), projectToEdit.isVisible() // Use current visibility
             );

             boolean overlapsWithActive = projects.stream()
                .filter(p -> p.getManagerNric().equals(currentUser.getNric()) && !p.equals(projectToEdit)) // Exclude self
                .filter(p -> p.isActive(currentDate)) // Is currently active
                .anyMatch(existingActiveProject -> checkDateOverlap(proposedProjectDates, existingActiveProject));

             if (overlapsWithActive) {
                 System.out.println("Error: The new application period overlaps with another *active* project you manage. Dates not updated.");
                 datesValid = false;
             }
        }

        // Apply date changes only if valid
        if (datesValid) {
             if (newOpeningDate != null) projectToEdit.setApplicationOpeningDate(newOpeningDate);
             if (newClosingDate != null) projectToEdit.setApplicationClosingDate(newClosingDate);
             if (datesChanged) System.out.println("Application dates updated.");
        }


        // Edit Officer Slots
        int currentMaxSlots = projectToEdit.getMaxOfficerSlots();
        int currentApprovedCount = projectToEdit.getApprovedOfficerNrics().size();
        System.out.print("Enter new Max Officer Slots [" + currentMaxSlots + "] (min " + currentApprovedCount + ", max 10, leave blank to keep): ");
        String slotsInput = scanner.nextLine().trim();
        if (!slotsInput.isEmpty()) {
             try {
                 int newMaxSlots = Integer.parseInt(slotsInput);
                 // setMaxOfficerSlots handles validation (>= approved count)
                 if (newMaxSlots >= 1 && newMaxSlots <= 10) {
                    projectToEdit.setMaxOfficerSlots(newMaxSlots); // Setter will print warning if invalid
                 } else {
                     System.out.println("Max slots must be between 1 and 10. Keeping original value.");
                 }
             } catch (NumberFormatException e) {
                  System.out.println("Invalid number format. Max slots not changed.");
             }
        }

        System.out.println("Project details update attempt complete.");
        // Save projects
        DataService.saveProjects(projects);
    }

    public void deleteProject() {
         System.out.println("\n--- Delete BTO Project ---");
         List<Project> myProjects = getManagedProjects(false); // Ignore filters for selection
         if (myProjects.isEmpty()) {
             System.out.println("You are not managing any projects.");
             return;
         }

        viewAndSelectProject(myProjects, "Select Project to Delete");
        Project projectToDelete = selectProjectFromList(myProjects);
        if (projectToDelete == null) return; // Cancelled

        // Check for active associations before deleting
        boolean hasActiveApplications = applications.values().stream()
            .anyMatch(app -> app.getProjectName().equals(projectToDelete.getProjectName()) &&
                             (app.getStatus() == ApplicationStatus.PENDING ||
                              app.getStatus() == ApplicationStatus.SUCCESSFUL ||
                              app.getStatus() == ApplicationStatus.BOOKED ||
                              app.getStatus() == ApplicationStatus.PENDING_WITHDRAWAL)); // Check active statuses including pending withdrawal

        boolean hasActiveRegistrations = officerRegistrations.values().stream()
            .anyMatch(reg -> reg.getProjectName().equals(projectToDelete.getProjectName()) &&
                             (reg.getStatus() == OfficerRegistrationStatus.PENDING ||
                              reg.getStatus() == OfficerRegistrationStatus.APPROVED)); // Check active statuses

        if (hasActiveApplications || hasActiveRegistrations) {
            System.out.println("Error: Cannot delete project '" + projectToDelete.getProjectName() + "'.");
            if (hasActiveApplications) System.out.println("- It has active BTO applications (Pending/Successful/Booked/PendingWithdrawal).");
            if (hasActiveRegistrations) System.out.println("- It has active Officer registrations (Pending/Approved).");
            System.out.println("Resolve these associations before deleting.");
            return; // Prevent deletion
        }

        // If no active associations, confirm deletion
        System.out.print("Are you sure you want to permanently delete project '" + projectToDelete.getProjectName() + "'? This will also remove associated historical applications/registrations/enquiries. (yes/no): ");
        String confirm = scanner.nextLine().trim().toLowerCase();

        if (confirm.equals("yes")) {
            String deletedProjectName = projectToDelete.getProjectName();
            if (projects.remove(projectToDelete)) {
                System.out.println("Project deleted successfully.");
                // Also remove associated data for cleanliness
                boolean removedApps = applications.values().removeIf(app -> app.getProjectName().equals(deletedProjectName));
                boolean removedRegs = officerRegistrations.values().removeIf(reg -> reg.getProjectName().equals(deletedProjectName));
                boolean removedEnqs = enquiries.removeIf(enq -> enq.getProjectName().equals(deletedProjectName));

                if (removedApps) System.out.println("Removed associated applications.");
                if (removedRegs) System.out.println("Removed associated officer registrations.");
                if (removedEnqs) System.out.println("Removed associated enquiries.");

                // Save all affected data files
                DataService.saveProjects(projects);
                if (removedApps) DataService.saveApplications(applications);
                if (removedRegs) DataService.saveOfficerRegistrations(officerRegistrations);
                if (removedEnqs) DataService.saveEnquiries(enquiries);

            } else {
                 System.err.println("Error: Failed to remove project from list.");
            }
        } else {
            System.out.println("Deletion cancelled.");
        }
    }

    public void toggleProjectVisibility() {
        System.out.println("\n--- Toggle Project Visibility ---");
        List<Project> myProjects = getManagedProjects(false); // Ignore filters for selection
        if (myProjects.isEmpty()) {
             System.out.println("You are not managing any projects.");
             return;
        }

        viewAndSelectProject(myProjects, "Select Project to Toggle Visibility");
        Project projectToToggle = selectProjectFromList(myProjects);

        if (projectToToggle != null) {
            boolean currentVisibility = projectToToggle.isVisible();
            projectToToggle.setVisibility(!currentVisibility);
            System.out.println("Project '" + projectToToggle.getProjectName() + "' visibility toggled to " + (projectToToggle.isVisible() ? "ON" : "OFF") + ".");
            // Save projects
            DataService.saveProjects(projects);
        }
    }

    public void viewAllProjects() {
        System.out.println("\n--- View All Projects (Manager View) ---");
        // Managers see all projects, filters apply, visibility/eligibility checks off, show expired
        List<Project> displayProjects = getFilteredProjects(false, false, false, false, false);
        viewAndSelectProject(displayProjects, "All BTO Projects");
    }

    public void viewMyProjects() {
        System.out.println("\n--- View My Managed Projects ---");
        List<Project> myProjects = getManagedProjects(true); // Uses helper, applies filters
        viewAndSelectProject(myProjects, "Projects Managed By You");
    }

    // Helper to get projects managed by the current manager
    private List<Project> getManagedProjects(boolean applyUserFilters) {
         List<Project> managed = projects.stream()
                                           .filter(p -> p.getManagerNric().equals(currentUser.getNric()))
                                           // Apply user's saved filters only if requested
                                           .filter(p -> !applyUserFilters || filterLocation == null || p.getNeighborhood().equalsIgnoreCase(filterLocation))
                                           .filter(p -> !applyUserFilters || filterFlatType == null || p.getFlatTypes().containsKey(filterFlatType))
                                           .sorted(Comparator.comparing(Project::getProjectName))
                                           .collect(Collectors.toList());
          if (managed.isEmpty() && applyUserFilters) {
            System.out.println("You are not managing any projects" + (filterLocation != null || filterFlatType != null ? " matching the current filters." : "."));
          } else if (managed.isEmpty() && !applyUserFilters) {
              // Don't print message here, let caller handle it if needed
              // System.out.println("You are not managing any projects.");
          }
          return managed;
    }

    public void manageOfficerRegistrations() {
        System.out.println("\n--- Manage HDB Officer Registrations ---");
        List<Project> myProjects = getManagedProjects(false); // Ignore filters for selection
        if (myProjects.isEmpty()) {
             System.out.println("You are not managing any projects.");
             return;
        }

        System.out.println("Select project to manage registrations for:");
        viewAndSelectProject(myProjects, "Select Project"); // Show only managed projects
        Project selectedProject = selectProjectFromList(myProjects);
        if (selectedProject == null) return; // Cancelled

        System.out.println("\n--- Registrations for Project: " + selectedProject.getProjectName() + " ---");
        System.out.println("Officer Slots: " + selectedProject.getApprovedOfficerNrics().size() + " / " + selectedProject.getMaxOfficerSlots() + " (Remaining: " + selectedProject.getRemainingOfficerSlots() + ")");

        // Get registrations specifically for this project
        List<OfficerRegistration> projectRegistrations = officerRegistrations.values().stream()
                .filter(reg -> reg.getProjectName().equals(selectedProject.getProjectName()))
                .sorted(Comparator.comparing(OfficerRegistration::getRegistrationDate))
                .collect(Collectors.toList());

        List<OfficerRegistration> pendingRegistrations = projectRegistrations.stream()
                .filter(reg -> reg.getStatus() == OfficerRegistrationStatus.PENDING)
                .collect(Collectors.toList());

        System.out.println("\n--- Pending Registrations ---");
        if (pendingRegistrations.isEmpty()) {
            System.out.println("(None)");
        } else {
            for (int i = 0; i < pendingRegistrations.size(); i++) {
                OfficerRegistration reg = pendingRegistrations.get(i);
                User officerUser = users.get(reg.getOfficerNric());
                System.out.printf("%d. NRIC: %s | Name: %-15s | Date: %s\n",
                        i + 1, reg.getOfficerNric(),
                        officerUser != null ? officerUser.getName() : "N/A",
                        DataService.formatDate(reg.getRegistrationDate()));
            }
            System.out.print("Enter number to Approve/Reject (or 0 to skip): ");
             try {
                 int choice = Integer.parseInt(scanner.nextLine());
                 if (choice >= 1 && choice <= pendingRegistrations.size()) {
                     OfficerRegistration regToProcess = pendingRegistrations.get(choice - 1);
                     User officerUser = users.get(regToProcess.getOfficerNric());

                     // Ensure the user is still an officer
                     if (!(officerUser instanceof HDBOfficer)) {
                          System.out.println("Error: User " + regToProcess.getOfficerNric() + " is no longer a valid Officer. Rejecting registration.");
                          regToProcess.setStatus(OfficerRegistrationStatus.REJECTED);
                          DataService.saveOfficerRegistrations(officerRegistrations);
                          return;
                     }
                     HDBOfficer officer = (HDBOfficer) officerUser;

                     System.out.print("Approve or Reject? (A/R): ");
                     String action = scanner.nextLine().trim().toUpperCase();

                     if (action.equals("A")) {
                         // Check slots
                         if (selectedProject.getRemainingOfficerSlots() <= 0) {
                             System.out.println("Cannot approve. No remaining officer slots for this project.");
                         }
                         // Check if officer is already handling another overlapping project
                         else if (isOfficerHandlingOverlappingProject(officer, selectedProject)) {
                              System.out.println("Cannot approve. Officer is already handling another project with overlapping dates.");
                         }
                         else {
                             // Proceed with approval
                             approveOfficerRegistration(regToProcess, selectedProject, officer);
                         }
                     } else if (action.equals("R")) {
                         regToProcess.setStatus(OfficerRegistrationStatus.REJECTED);
                         System.out.println("Registration Rejected.");
                         // Save registrations
                         DataService.saveOfficerRegistrations(officerRegistrations);
                     } else {
                         System.out.println("Invalid action.");
                     }
                 } else if (choice != 0) {
                     System.out.println("Invalid choice.");
                 }
             } catch (NumberFormatException e) {
                 System.out.println("Invalid input.");
             }
        }

         // Display other statuses for info
         System.out.println("\n--- Approved Officers for this Project ---");
         if (selectedProject.getApprovedOfficerNrics().isEmpty()) System.out.println("(None)");
         else selectedProject.getApprovedOfficerNrics().forEach(nric -> System.out.println("- NRIC: " + nric + (users.containsKey(nric) ? " (Name: " + users.get(nric).getName() + ")" : " (Name: N/A)")));

         System.out.println("\n--- Rejected Registrations for this Project ---");
         List<OfficerRegistration> rejected = projectRegistrations.stream().filter(r -> r.getStatus() == OfficerRegistrationStatus.REJECTED).collect(Collectors.toList());
          if (rejected.isEmpty()) System.out.println("(None)");
         else rejected.forEach(reg -> System.out.println("- NRIC: " + reg.getOfficerNric() + " | Date: " + DataService.formatDate(reg.getRegistrationDate())));
    }

    // Helper to check if officer handles any *other* project overlapping with the target project
    private boolean isOfficerHandlingOverlappingProject(HDBOfficer officer, Project targetProject) {
        return officerRegistrations.values().stream()
            .filter(reg -> reg.getOfficerNric().equals(officer.getNric()) &&
                           reg.getStatus() == OfficerRegistrationStatus.APPROVED &&
                           !reg.getProjectName().equals(targetProject.getProjectName())) // Exclude the target project itself
            .map(reg -> findProjectByName(reg.getProjectName()))
            .filter(Objects::nonNull)
            .anyMatch(otherProject -> checkDateOverlap(targetProject, otherProject));
    }


    // Helper method for approving officer registration
    private void approveOfficerRegistration(OfficerRegistration registration, Project project, HDBOfficer officer) {
        // Double check slots again before committing
        if (project.getRemainingOfficerSlots() <= 0) {
             System.out.println("Error: No remaining officer slots. Approval aborted.");
             return;
        }
        if (project.addApprovedOfficer(registration.getOfficerNric())) {
             registration.setStatus(OfficerRegistrationStatus.APPROVED);
             // No need to set handlingProjectName on officer object
             System.out.println("Registration Approved. Officer " + registration.getOfficerNric() + " added to project.");
             // Save all relevant data
             DataService.saveOfficerRegistrations(officerRegistrations);
             DataService.saveProjects(projects);
         } else {
             // This should ideally not happen if slot check was done before calling
             System.err.println("Error: Failed to add officer to project's approved list (unexpected). Approval aborted.");
         }
    }


    public void manageApplications() {
        System.out.println("\n--- Manage BTO Applications ---");
        List<Project> myProjects = getManagedProjects(false); // Ignore filters for selection
        if (myProjects.isEmpty()) {
             System.out.println("You are not managing any projects.");
             return;
        }

        System.out.println("Select project to manage applications for:");
        viewAndSelectProject(myProjects, "Select Project");
        Project selectedProject = selectProjectFromList(myProjects);
        if (selectedProject == null) return; // Cancelled

        System.out.println("\n--- Applications for Project: " + selectedProject.getProjectName() + " ---");

        // Get applications for this project
        List<BTOApplication> projectApplications = applications.values().stream()
                .filter(app -> app.getProjectName().equals(selectedProject.getProjectName()))
                .sorted(Comparator.comparing(BTOApplication::getApplicationDate))
                .collect(Collectors.toList());

        if (projectApplications.isEmpty()) {
            System.out.println("No applications found for this project.");
            return;
        }

        // Separate PENDING applications for action
        List<BTOApplication> pendingApps = projectApplications.stream()
                                                                .filter(app -> app.getStatus() == ApplicationStatus.PENDING)
                                                                .collect(Collectors.toList());

        System.out.println("--- Pending Applications ---");
        if (pendingApps.isEmpty()) {
            System.out.println("(None)");
        } else {
             for (int i = 0; i < pendingApps.size(); i++) {
                 BTOApplication app = pendingApps.get(i);
                 User applicant = users.get(app.getApplicantNric());
                 System.out.printf("%d. NRIC: %s | Name: %-15s | Type: %-8s | Date: %s\n",
                         i + 1, app.getApplicantNric(),
                         applicant != null ? applicant.getName() : "N/A",
                         app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A",
                         DataService.formatDate(app.getApplicationDate()));
             }
             System.out.print("Enter number to Approve/Reject (or 0 to skip): ");
             try {
                 int choice = Integer.parseInt(scanner.nextLine());
                 if (choice >= 1 && choice <= pendingApps.size()) {
                     BTOApplication appToProcess = pendingApps.get(choice - 1);
                     User applicantUser = users.get(appToProcess.getApplicantNric());

                     // Ensure applicant exists and is Applicant/Officer
                     if (!(applicantUser instanceof Applicant)) {
                         System.out.println("Error: Applicant data not found or invalid for NRIC " + appToProcess.getApplicantNric() + ". Rejecting application.");
                         appToProcess.setStatus(ApplicationStatus.UNSUCCESSFUL);
                         DataService.saveApplications(applications);
                         return;
                     }
                     Applicant applicant = (Applicant) applicantUser;

                     System.out.print("Approve or Reject? (A/R): ");
                     String action = scanner.nextLine().trim().toUpperCase();

                     if (action.equals("A")) {
                         // Check flat availability for the applied type
                         FlatType appliedType = appToProcess.getFlatTypeApplied();
                         if (appliedType == null) {
                             System.out.println("Error: Application has no specified flat type. Cannot approve.");
                             // Optionally reject: appToProcess.setStatus(ApplicationStatus.UNSUCCESSFUL);
                             return;
                         }
                         FlatTypeDetails details = selectedProject.getFlatTypeDetails(appliedType);

                         // Check 1: Does the flat type exist in the project?
                         if (details == null) {
                              System.out.println("Error: Applied flat type (" + appliedType.getDisplayName() + ") does not exist in this project. Rejecting application.");
                              appToProcess.setStatus(ApplicationStatus.UNSUCCESSFUL);
                              applicant.setApplicationStatus(ApplicationStatus.UNSUCCESSFUL); // Update user state
                              DataService.saveApplications(applications);
                              return;
                         }

                         // Check 2: Are there *any* available units left for booking? (Officer handles actual decrement)
                         // Requirement: "approval is limited to the supply of the flats"
                         // Interpretation: Manager should not approve more applications than total units exist for that type.
                         long alreadySuccessfulOrBookedCount = applications.values().stream()
                             .filter(a -> a.getProjectName().equals(selectedProject.getProjectName()) &&
                                          a.getFlatTypeApplied() == appliedType &&
                                          (a.getStatus() == ApplicationStatus.SUCCESSFUL || a.getStatus() == ApplicationStatus.BOOKED))
                             .count();

                         if (alreadySuccessfulOrBookedCount < details.getTotalUnits()) {
                             // Approve: Change status in application and user object
                             appToProcess.setStatus(ApplicationStatus.SUCCESSFUL);
                             applicant.setApplicationStatus(ApplicationStatus.SUCCESSFUL); // Update user state
                             System.out.println("Application Approved (Status: SUCCESSFUL). Applicant can now book via Officer.");
                             // Save changes
                             DataService.saveApplications(applications);
                             // User state derived on load
                         } else {
                             System.out.println("Cannot approve. The number of successful/booked applications already meets or exceeds the total supply (" + details.getTotalUnits() + ") for " + appliedType.getDisplayName() + ".");
                             // Optionally, auto-reject? Or leave pending? Let's leave pending.
                         }
                     } else if (action.equals("R")) {
                         // Reject: Change status in application and user object
                         appToProcess.setStatus(ApplicationStatus.UNSUCCESSFUL);
                         applicant.setApplicationStatus(ApplicationStatus.UNSUCCESSFUL); // Update user state
                         applicant.setBookedFlatType(null); // Ensure booked type is clear
                         System.out.println("Application Rejected (Status: UNSUCCESSFUL).");
                         // Save changes
                         DataService.saveApplications(applications);
                         // User state derived on load
                     } else {
                         System.out.println("Invalid action.");
                     }
                 } else if (choice != 0) {
                     System.out.println("Invalid choice.");
                 }
             } catch (NumberFormatException e) {
                 System.out.println("Invalid input.");
             }
        }

         // Display other statuses for info
         System.out.println("\n--- Other Application Statuses ---");
         projectApplications.stream()
             .filter(app -> app.getStatus() != ApplicationStatus.PENDING) // Show all non-pending
             .forEach(app -> {
                 User applicant = users.get(app.getApplicantNric());
                 System.out.printf("- NRIC: %s | Name: %-15s | Type: %-8s | Status: %s\n",
                         app.getApplicantNric(),
                         applicant != null ? applicant.getName() : "N/A",
                         app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A",
                         app.getStatus());
             });
    }

     // Method for Manager to approve/reject withdrawal requests
     public void manageWithdrawalRequests() {
        System.out.println("\n--- Manage Withdrawal Requests ---");
        List<Project> myProjects = getManagedProjects(false);
        if (myProjects.isEmpty()) {
             System.out.println("You are not managing any projects.");
             return;
        }
        List<String> myProjectNames = myProjects.stream().map(Project::getProjectName).collect(Collectors.toList());

        // Find applications with PENDING_WITHDRAWAL status for projects managed by this manager
        List<BTOApplication> pendingWithdrawals = applications.values().stream()
            .filter(app -> app.getStatus() == ApplicationStatus.PENDING_WITHDRAWAL)
            .filter(app -> myProjectNames.contains(app.getProjectName())) // Only for managed projects
            .sorted(Comparator.comparing(BTOApplication::getApplicationDate))
            .collect(Collectors.toList());

        if (pendingWithdrawals.isEmpty()) {
            System.out.println("No pending withdrawal requests found for the projects you manage.");
            return;
        }

        System.out.println("--- Pending Withdrawal Requests ---");
        for (int i = 0; i < pendingWithdrawals.size(); i++) {
            BTOApplication app = pendingWithdrawals.get(i);
            User applicantUser = users.get(app.getApplicantNric());

            // Determine status before withdrawal request
            ApplicationStatus statusBefore = app.getStatusBeforeWithdrawal();
            if (statusBefore == null) { // Infer if not stored (e.g., loaded from old file)
                statusBefore = inferStatusBeforeWithdrawal(app, (applicantUser instanceof Applicant) ? (Applicant)applicantUser : null);
                System.out.print(" (Inferred Original: " + statusBefore + ")");
            } else {
                 System.out.print(" (Original: " + statusBefore + ")");
            }

            System.out.printf("\n%d. NRIC: %s | Name: %-15s | Project: %-15s | Type: %-8s | App Date: %s",
                    i + 1,
                    app.getApplicantNric(),
                    applicantUser != null ? applicantUser.getName() : "N/A",
                    app.getProjectName(),
                    app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A",
                    DataService.formatDate(app.getApplicationDate()));
            System.out.println(); // Newline for formatting
        }

        System.out.print("Enter number to Approve/Reject withdrawal (or 0 to skip): ");
        try {
            int choice = Integer.parseInt(scanner.nextLine());
            if (choice >= 1 && choice <= pendingWithdrawals.size()) {
                BTOApplication appToProcess = pendingWithdrawals.get(choice - 1);
                User applicantUser = users.get(appToProcess.getApplicantNric());
                 if (!(applicantUser instanceof Applicant)) {
                    System.out.println("Error: Applicant data not found or invalid for NRIC " + appToProcess.getApplicantNric() + ". Cannot process withdrawal.");
                    return;
                 }
                Applicant applicant = (Applicant) applicantUser;
                Project project = findProjectByName(appToProcess.getProjectName());
                 if (project == null) {
                     System.out.println("Error: Project data not found for application " + appToProcess.getApplicationId() + ". Cannot process withdrawal.");
                     return;
                 }

                // Determine original status more reliably
                ApplicationStatus originalStatus = appToProcess.getStatusBeforeWithdrawal();
                if (originalStatus == null) {
                    originalStatus = inferStatusBeforeWithdrawal(appToProcess, applicant);
                }


                System.out.print("Approve or Reject withdrawal request? (A/R): ");
                String action = scanner.nextLine().trim().toUpperCase();

                if (action.equals("A")) { // APPROVE Withdrawal
                    ApplicationStatus finalStatus;
                    boolean releasedUnit = false;

                    // Determine final status based on original status (as per FAQ Q4/Q2)
                    if (originalStatus == ApplicationStatus.BOOKED) {
                        finalStatus = ApplicationStatus.UNSUCCESSFUL;
                        // Release the booked unit
                        FlatType bookedType = appToProcess.getFlatTypeApplied(); // Use type from application
                        if (bookedType != null) {
                             FlatTypeDetails details = project.getMutableFlatTypeDetails(bookedType);
                             if (details != null) {
                                 if (details.incrementAvailableUnits()) {
                                     releasedUnit = true;
                                     System.out.println("Unit for " + bookedType.getDisplayName() + " released back to project " + project.getProjectName());
                                 } else {
                                      System.err.println("Error: Could not increment available units for " + bookedType + " during withdrawal approval.");
                                 }
                             } else {
                                 System.err.println("Error: Could not find flat details for " + bookedType + " during withdrawal approval.");
                             }
                        } else {
                             System.err.println("Error: Cannot determine booked flat type to release unit during withdrawal approval.");
                        }
                    } else if (originalStatus == ApplicationStatus.SUCCESSFUL) {
                        finalStatus = ApplicationStatus.UNSUCCESSFUL;
                    } else { // Assumed PENDING originally
                        finalStatus = ApplicationStatus.WITHDRAWN;
                    }

                    // Update application and applicant profile
                    appToProcess.setStatus(finalStatus);
                    applicant.setApplicationStatus(finalStatus);
                    applicant.setBookedFlatType(null); // Always clear booked type on withdrawal approval

                    System.out.println("Withdrawal request Approved. Application status set to " + finalStatus + ".");

                    // Save relevant data
                    DataService.saveApplications(applications);
                    if (releasedUnit) {
                        DataService.saveProjects(projects); // Save if unit count changed
                    }
                    // User profile state updated in memory, will be synced on next access/load

                } else if (action.equals("R")) { // REJECT Withdrawal
                    // Revert application status to its state before withdrawal request
                    appToProcess.setStatus(originalStatus);
                    applicant.setApplicationStatus(originalStatus); // Revert profile status too
                    // Note: BookedFlatType remains as it was in the profile.

                    System.out.println("Withdrawal request Rejected. Application status reverted to " + originalStatus + ".");
                    // Save application data
                    DataService.saveApplications(applications);

                } else {
                    System.out.println("Invalid action.");
                }
            } else if (choice != 0) {
                System.out.println("Invalid choice.");
            }
        } catch (NumberFormatException e) {
            System.out.println("Invalid input.");
        }
     }

     // Helper to infer status before withdrawal if not explicitly stored
     private ApplicationStatus inferStatusBeforeWithdrawal(BTOApplication app, Applicant applicant) {
         // This is an estimation, less reliable than storing the actual previous status
         if (applicant != null && applicant.hasBooked() && app.getFlatTypeApplied() != null) {
            return ApplicationStatus.BOOKED;
         } else if (app.getFlatTypeApplied() != null) {
             // If flat type is known, it must have at least reached PENDING or SUCCESSFUL
             // Check if applicant profile *currently* reflects SUCCESSFUL (less likely if PENDING_WITHDRAWAL is shown, but fallback)
             if (applicant != null && applicant.getApplicationStatus() == ApplicationStatus.SUCCESSFUL) {
                 return ApplicationStatus.SUCCESSFUL;
             } else {
                 // Cannot definitively distinguish between PENDING and SUCCESSFUL without more info
                 // Defaulting to SUCCESSFUL if flat type exists, otherwise PENDING
                 return ApplicationStatus.SUCCESSFUL;
             }
         }
         return ApplicationStatus.PENDING; // Default assumption if no other info
     }


    public void generateApplicantReport() {
        System.out.println("\n--- Generate Applicant Report (Booked Flats) ---");

        // 1. Select Project Filter
        System.out.println("Filter by project:");
        System.out.println("1. All Projects Managed By You");
        System.out.println("2. A Specific Project Managed By You");
        System.out.println("0. Cancel");
        int projectFilterChoice = getIntInput("Enter choice: ", 0, 2);

        List<Project> projectsToReportOn = new ArrayList<>();
        if (projectFilterChoice == 0) return; // Cancelled
        if (projectFilterChoice == 1) {
            projectsToReportOn = getManagedProjects(true); // Get all managed projects (applies location/type filters from BaseController state)
            if (projectsToReportOn.isEmpty()) {
                 // Message handled by getManagedProjects
                 return;
            }
             System.out.println("Reporting on all projects you manage" + (filterLocation != null || filterFlatType != null ? " (matching current view filters)." : "."));
        } else { // projectFilterChoice == 2
            List<Project> myProjects = getManagedProjects(false); // Get managed projects (ignore view filters for selection)
            if (myProjects.isEmpty()) {
                 System.out.println("You are not managing any projects.");
                 return;
            }
            viewAndSelectProject(myProjects, "Select Specific Project to Report On");
            Project specificProject = selectProjectFromList(myProjects);
            if (specificProject == null) return; // Cancelled selection
            projectsToReportOn.add(specificProject);
            System.out.println("Reporting specifically for project: " + specificProject.getProjectName());
        }
        final List<String> finalProjectNames = projectsToReportOn.stream().map(Project::getProjectName).collect(Collectors.toList());


        // 2. Filter by Flat Type (Specific to Report)
        System.out.print("Filter report by Flat Type (TWO_ROOM, THREE_ROOM, or leave blank for all): ");
        String typeStr = scanner.nextLine().trim();
        FlatType filterReportFlatType = null; // Use a separate variable for report filter
        if (!typeStr.isEmpty()) {
             try {
                 filterReportFlatType = FlatType.fromString(typeStr);
                 if (filterReportFlatType != null) System.out.println("Filtering report for flat type: " + filterReportFlatType.getDisplayName());
                 else System.out.println("Invalid flat type entered. Reporting for all types.");
             } catch (IllegalArgumentException e) { System.out.println("Invalid flat type format. Reporting for all types."); }
        }

        // 3. Filter by Marital Status (Specific to Report)
        System.out.print("Filter report by Marital Status (SINGLE, MARRIED, or leave blank for all): ");
        String maritalStr = scanner.nextLine().trim().toUpperCase();
        MaritalStatus filterMaritalStatus = null;
        if (!maritalStr.isEmpty()) {
             try {
                 filterMaritalStatus = MaritalStatus.valueOf(maritalStr);
                 System.out.println("Filtering report for marital status: " + filterMaritalStatus);
             } catch (IllegalArgumentException e) { System.out.println("Invalid marital status. Reporting for all statuses."); }
        }

        // 4. Filter by Age Range (Specific to Report)
        int minAge = getIntInput("Filter report by Minimum Age (e.g., 21, or 0 for no minimum): ", 0, 120);
        int maxAge = getIntInput("Filter report by Maximum Age (e.g., 40, or 0 for no maximum): ", 0, 120);
         if (minAge > 0 || maxAge > 0) System.out.println("Filtering report for age range: " + (minAge > 0 ? minAge : "Any") + " to " + (maxAge > 0 ? maxAge : "Any"));


        // 5. Generate Report Data
        final FlatType finalFilterReportFlatType = filterReportFlatType; // Need final for lambda
        final MaritalStatus finalFilterMaritalStatus = filterMaritalStatus;
        final int finalMinAge = minAge;
        final int finalMaxAge = maxAge;

        List<BTOApplication> bookedApplications = applications.values().stream()
            .filter(app -> app.getStatus() == ApplicationStatus.BOOKED) // Only booked
            .filter(app -> finalProjectNames.contains(app.getProjectName())) // Filter by selected project(s)
            .filter(app -> finalFilterReportFlatType == null || app.getFlatTypeApplied() == finalFilterReportFlatType) // Filter by flat type
            .filter(app -> { // Filter by user demographics
                User user = users.get(app.getApplicantNric());
                if (user == null) return false; // Skip if user not found
                if (finalFilterMaritalStatus != null && user.getMaritalStatus() != finalFilterMaritalStatus) return false;
                if (finalMinAge > 0 && user.getAge() < finalMinAge) return false;
                if (finalMaxAge > 0 && user.getAge() > finalMaxAge) return false; // Use > for max age check
                return true;
            })
            .sorted(Comparator.comparing(BTOApplication::getProjectName).thenComparing(BTOApplication::getApplicantNric)) // Sort results
            .collect(Collectors.toList());

        // 6. Display Report
        System.out.println("\n--- Report: Applicants with Flat Bookings ---");
        System.out.println("Filters Applied: Project(s) selected, FlatType=" + (finalFilterReportFlatType == null ? "Any" : finalFilterReportFlatType) + ", MaritalStatus=" + (finalFilterMaritalStatus == null ? "Any" : finalFilterMaritalStatus) + ", Age=" + (finalMinAge > 0 ? finalMinAge : "Any") + "-" + (finalMaxAge > 0 ? finalMaxAge : "Any"));
        System.out.println("---------------------------------------------------------------------------------");
        System.out.printf("%-15s | %-15s | %-5s | %-10s | %-15s | %-8s\n",
                          "Applicant NRIC", "Name", "Age", "Marital", "Project Name", "FlatType");
        System.out.println("---------------------------------------------------------------------------------");

        if (bookedApplications.isEmpty()) {
            System.out.println("No matching booked applications found for the specified filters.");
        } else {
            bookedApplications.forEach(app -> {
                User user = users.get(app.getApplicantNric());
                System.out.printf("%-15s | %-15s | %-5d | %-10s | %-15s | %-8s\n",
                                  app.getApplicantNric(),
                                  user != null ? user.getName() : "N/A",
                                  user != null ? user.getAge() : 0,
                                  user != null ? user.getMaritalStatus() : "N/A",
                                  app.getProjectName(),
                                  app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A");
            });
        }
        System.out.println("---------------------------------------------------------------------------------");
        System.out.println("Total matching booked applicants: " + bookedApplications.size());
        System.out.println("--- End of Report ---");
    }

    // View enquiries for ALL projects (no filtering, manager oversight)
    public void viewAllEnquiries() {
        System.out.println("\n--- View Enquiries (ALL Projects) ---");
         if (enquiries.isEmpty()) {
            System.out.println("No enquiries found in the system.");
            return;
        }

        // Sort by project then date
        enquiries.stream()
                 .sorted(Comparator.comparing(Enquiry::getProjectName).thenComparing(Enquiry::getEnquiryDate).reversed())
                 .forEach(e -> {
                     printEnquiryDetails(e); // Use helper to print
                     System.out.println("----------------------------------------");
                 });
    }

    // View and potentially reply to enquiries for projects managed by this manager
    public void viewAndReplyToManagedEnquiries() {
        System.out.println("\n--- View/Reply Enquiries (Managed Projects) ---");
        List<String> myManagedProjectNames = getManagedProjects(true).stream() // Use helper to get filtered list of projects
                                           .map(Project::getProjectName)
                                           .collect(Collectors.toList());

        if (myManagedProjectNames.isEmpty()) {
            // Message already printed by getManagedProjects if list is empty
            return;
        }

        List<Enquiry> managedEnquiries = enquiries.stream()
                 .filter(e -> myManagedProjectNames.contains(e.getProjectName())) // Filter by managed project names
                 .sorted(Comparator.comparing(Enquiry::getProjectName).thenComparing(Enquiry::getEnquiryDate).reversed())
                 .collect(Collectors.toList());

         if (managedEnquiries.isEmpty()) {
             System.out.println("No enquiries found for the projects you manage" + (filterLocation != null || filterFlatType != null ? " (matching filters)." : "."));
             return;
         }

         // Separate unreplied for selection
         List<Enquiry> unrepliedEnquiries = managedEnquiries.stream()
                                                            .filter(e -> !e.isReplied())
                                                            .collect(Collectors.toList());

         System.out.println("--- Unreplied Enquiries (Managed Projects) ---");
         if (unrepliedEnquiries.isEmpty()) {
             System.out.println("(None)");
         } else {
             for (int i = 0; i < unrepliedEnquiries.size(); i++) {
                 Enquiry e = unrepliedEnquiries.get(i);
                 System.out.printf("%d. ", i + 1);
                 printEnquiryDetails(e); // Use helper
                 System.out.println("---");
             }
             System.out.print("Enter the number of the enquiry to reply to (or 0 to skip): ");
             try {
                 int choice = Integer.parseInt(scanner.nextLine());
                 if (choice >= 1 && choice <= unrepliedEnquiries.size()) {
                     Enquiry enquiryToReply = unrepliedEnquiries.get(choice - 1);
                     System.out.print("Enter your reply: ");
                     String replyText = scanner.nextLine().trim();
                     if (enquiryToReply.setReply(replyText, currentUser.getNric(), DataService.getCurrentDate())) {
                         System.out.println("Reply submitted successfully.");
                         // Save enquiries
                         DataService.saveEnquiries(enquiries);
                     } // Error messages handled by setter
                 } else if (choice != 0) {
                     System.out.println("Invalid choice.");
                 }
             } catch (NumberFormatException e) {
                 System.out.println("Invalid input.");
             }
         }

         // Display replied enquiries for reference
         System.out.println("\n--- Replied Enquiries (Managed Projects) ---");
         List<Enquiry> repliedEnquiries = managedEnquiries.stream()
                                                          .filter(Enquiry::isReplied)
                                                          .collect(Collectors.toList());
         if (repliedEnquiries.isEmpty()) {
             System.out.println("(None)");
         } else {
             for (Enquiry e : repliedEnquiries) {
                 printEnquiryDetails(e);
                 System.out.println("----------------------------------------");
             }
         }
    }

    // Helper to print enquiry details consistently
    private void printEnquiryDetails(Enquiry e) {
         System.out.printf("ID: %s | Project: %s | Applicant: %s | Date: %s\n",
                 e.getEnquiryId(), e.getProjectName(), e.getApplicantNric(), DataService.formatDate(e.getEnquiryDate()));
         System.out.println("   Enquiry: " + e.getEnquiryText());
         if (e.isReplied()) {
             System.out.printf("   Reply (by %s on %s): %s\n",
                     e.getRepliedByNric() != null ? e.getRepliedByNric() : "N/A",
                     e.getReplyDate() != null ? DataService.formatDate(e.getReplyDate()) : "N/A",
                     e.getReplyText());
         } else {
             System.out.println("   Reply: (Pending)");
         }
    }
}


// ==================
// Views (Handle CLI Display and Input Gathering)
// ==================

// --- Base View ---
abstract class BaseView {
    protected final Scanner scanner; // Input mechanism
    protected final User currentUser; // Current logged-in user
    protected final BaseController controller; // Associated controller for actions
    protected final AuthController authController; // For changing password

    public BaseView(Scanner scanner, User currentUser, BaseController controller, AuthController authController) {
        this.scanner = scanner;
        this.currentUser = currentUser;
        this.controller = controller;
        this.authController = authController; // Inject AuthController
    }

    // Abstract method to display the specific menu for the role
    public abstract void displayMenu();

    // Gets menu choice, handles invalid input
    protected int getMenuChoice(int min, int max) {
        int choice = -1;
        while (true) {
            System.out.print("Enter your choice: ");
            String input = scanner.nextLine();
            try {
                choice = Integer.parseInt(input);
                if (choice >= min && choice <= max) {
                    break; // Valid choice
                } else {
                    System.out.println("Invalid choice. Please enter a number between " + min + " and " + max + ".");
                }
            } catch (NumberFormatException e) {
                System.out.println("Invalid input. Please enter a number.");
            }
        }
        return choice;
    }

    // Handles the change password interaction
     protected boolean changePassword() { // Return true if password changed (forces logout)
         System.out.println("\n--- Change Password ---");
         System.out.print("Enter current password: ");
         String oldPassword = scanner.nextLine();
         System.out.print("Enter new password: ");
         String newPassword = scanner.nextLine();
         System.out.print("Confirm new password: ");
         String confirmPassword = scanner.nextLine();

         if (!newPassword.equals(confirmPassword)) {
             System.out.println("New passwords do not match. Password not changed.");
             return false;
         }
         if (newPassword.isEmpty()) {
              System.out.println("Password cannot be empty. Password not changed.");
              return false;
         }
         if (newPassword.equals(oldPassword)) {
              System.out.println("New password cannot be the same as the old password. Password not changed.");
              return false;
         }

         // Use AuthController to handle the change and saving
         boolean success = authController.changePassword(currentUser, oldPassword, newPassword);
         return success; // Return true if successful to trigger logout in menu loop
     }

     // Calls the controller's filter method
     protected void applyFilters() {
         if (controller != null) {
             controller.applyFilters();
         } else {
             // This should not happen if view is constructed correctly
             System.out.println("Error: Controller not available for filtering.");
         }
     }

     // Pauses execution until user presses Enter
     protected void pause() {
          System.out.println("\nPress Enter to continue...");
          scanner.nextLine();
     }
}

// --- Specific Role Views ---

class ApplicantView extends BaseView {
    // Cast controller once in constructor for convenience
    private final ApplicantController applicantController;

    public ApplicantView(Scanner scanner, User currentUser, ApplicantController controller, AuthController authController) {
        super(scanner, currentUser, controller, authController);
        this.applicantController = controller;
    }

    @Override
    public void displayMenu() {
        boolean logout = false;
        while (!logout) {
            System.out.println("\n=========== Applicant Menu ===========");
            System.out.println("Welcome, " + currentUser.getName() + "!");
            System.out.println("1. View Available BTO Projects");
            System.out.println("2. Apply for BTO Project");
            System.out.println("3. View My Application Status");
            System.out.println("4. Request Application Withdrawal"); // Changed wording
            System.out.println("5. Submit Enquiry");
            System.out.println("6. View My Enquiries");
            System.out.println("7. Edit My Enquiry");
            System.out.println("8. Delete My Enquiry");
            System.out.println("9. Apply/Clear Project Filters");
            System.out.println("10. Change Password");
            System.out.println("0. Logout");
            System.out.println("======================================");

            int choice = getMenuChoice(0, 10);

            switch (choice) {
                case 1: applicantController.viewOpenProjects(); break;
                case 2: applicantController.applyForProject(); break;
                case 3: applicantController.viewMyApplication(); break;
                case 4: applicantController.requestWithdrawal(); break; // Now requests, doesn't directly withdraw
                case 5: applicantController.submitEnquiry(); break;
                case 6: applicantController.viewMyEnquiries(); break;
                case 7: applicantController.editMyEnquiry(); break;
                case 8: applicantController.deleteMyEnquiry(); break;
                case 9: applyFilters(); break;
                case 10:
                    if (changePassword()) { // changePassword returns true on success
                        logout = true; // Set flag to exit loop after successful password change
                    }
                    break;
                case 0:
                    logout = true; // Set flag to exit loop
                    System.out.println("Logging out...");
                    break;
                default: System.out.println("Invalid choice."); break; // Should not happen
            }
             if (!logout && choice != 0) { // Don't pause if logging out or just changed password
                 pause(); // Pause after action (unless logging out)
             }
        }
    }
}

class OfficerView extends BaseView {
    private final OfficerController officerController;

    public OfficerView(Scanner scanner, User currentUser, OfficerController controller, AuthController authController) {
        super(scanner, currentUser, controller, authController);
        this.officerController = controller;
    }

    @Override
    public void displayMenu() {
        boolean logout = false;
        while (!logout) {
            System.out.println("\n=========== HDB Officer Menu ===========");
            System.out.println("Welcome, Officer " + currentUser.getName() + "!");
            // Get handling project dynamically
            Project handlingProject = officerController.getOfficerHandlingProject((HDBOfficer)currentUser);
            if (handlingProject != null) {
                 System.out.println("--> Currently Handling Project: " + handlingProject.getProjectName() + " <--");
            } else {
                 System.out.println("--> Not currently handling any project <--");
            }
            System.out.println("--- Officer Actions ---");
            System.out.println(" 1. Register to Handle Project");
            System.out.println(" 2. View My Registration Status");
            System.out.println(" 3. View Handling Project Details");
            System.out.println(" 4. View/Reply Enquiries (Handling Project)");
            System.out.println(" 5. Manage Flat Booking (Process Successful Applicants)");
            System.out.println("--- Applicant Actions (Inherited) ---");
            System.out.println(" 6. View Available BTO Projects");
            System.out.println(" 7. Apply for BTO Project");
            System.out.println(" 8. View My Application Status");
            System.out.println(" 9. Request Application Withdrawal"); // Changed wording
            System.out.println("10. Submit Enquiry");
            System.out.println("11. View My Enquiries");
            System.out.println("12. Edit My Enquiry");
            System.out.println("13. Delete My Enquiry");
            System.out.println("--- Common Actions ---");
            System.out.println("14. Apply/Clear Project Filters");
            System.out.println("15. Change Password");
            System.out.println(" 0. Logout");
            System.out.println("========================================");

            int choice = getMenuChoice(0, 15);

            switch (choice) {
                // Officer Actions
                case 1: officerController.registerForProject(); break;
                case 2: officerController.viewRegistrationStatus(); break;
                case 3: officerController.viewHandlingProjectDetails(); break;
                case 4: officerController.viewAndReplyToEnquiries(); break;
                case 5: officerController.manageFlatBooking(); break;
                // Applicant Actions
                case 6: officerController.viewOpenProjects(); break;
                case 7: officerController.applyForProject(); break;
                case 8: officerController.viewMyApplication(); break;
                case 9: officerController.requestWithdrawal(); break; // Now requests
                case 10: officerController.submitEnquiry(); break;
                case 11: officerController.viewMyEnquiries(); break;
                case 12: officerController.editMyEnquiry(); break;
                case 13: officerController.deleteMyEnquiry(); break;
                // Common Actions
                case 14: applyFilters(); break;
                case 15:
                    if (changePassword()) {
                        logout = true;
                    }
                    break;
                case 0:
                    logout = true;
                    System.out.println("Logging out...");
                    break;
                default: System.out.println("Invalid choice."); break;
            }
             if (!logout && choice != 0) {
                 pause();
             }
        }
    }
}

class ManagerView extends BaseView {
    private final ManagerController managerController;

    public ManagerView(Scanner scanner, User currentUser, ManagerController controller, AuthController authController) {
        super(scanner, currentUser, controller, authController);
        this.managerController = controller; // Cast controller
    }

    @Override
    public void displayMenu() {
        boolean logout = false;
        while (!logout) {
            System.out.println("\n=========== HDB Manager Menu ===========");
            System.out.println("Welcome, Manager " + currentUser.getName() + "!");
            System.out.println("--- Project Management ---");
            System.out.println(" 1. Create New BTO Project");
            System.out.println(" 2. Edit My Project Details");
            System.out.println(" 3. Delete My Project");
            System.out.println(" 4. Toggle Project Visibility");
            System.out.println(" 5. View All Projects (Manager Oversight)");
            System.out.println(" 6. View My Managed Projects");
            System.out.println("--- Staff & Application Management ---");
            System.out.println(" 7. Manage Officer Registrations (Approve/Reject)");
            System.out.println(" 8. Manage BTO Applications (Approve/Reject)");
            System.out.println(" 9. Manage Withdrawal Requests (Approve/Reject)"); // Added
            System.out.println("--- Reporting & Enquiries ---");
            System.out.println("10. Generate Applicant Report (Booked Flats)");
            System.out.println("11. View Enquiries (ALL Projects)");
            System.out.println("12. View/Reply Enquiries (My Managed Projects)");
            System.out.println("--- Common Actions ---");
            System.out.println("13. Apply/Clear Project Filters (Affects Views 5, 6, 10, 12)"); // Updated range
            System.out.println("14. Change Password");
            System.out.println(" 0. Logout");
            System.out.println("========================================");

            int choice = getMenuChoice(0, 14); // Updated max choice

            switch (choice) {
                // Project Management
                case 1: managerController.createProject(); break;
                case 2: managerController.editProject(); break;
                case 3: managerController.deleteProject(); break;
                case 4: managerController.toggleProjectVisibility(); break;
                case 5: managerController.viewAllProjects(); break;
                case 6: managerController.viewMyProjects(); break;
                // Staff & Application Management
                case 7: managerController.manageOfficerRegistrations(); break;
                case 8: managerController.manageApplications(); break;
                case 9: managerController.manageWithdrawalRequests(); break; // Added call
                // Reporting & Enquiries
                case 10: managerController.generateApplicantReport(); break;
                case 11: managerController.viewAllEnquiries(); break;
                case 12: managerController.viewAndReplyToManagedEnquiries(); break;
                // Common Actions
                case 13: applyFilters(); break;
                case 14:
                    if (changePassword()) {
                        logout = true;
                    }
                    break;
                case 0:
                    logout = true;
                    System.out.println("Logging out...");
                    break;
                default: System.out.println("Invalid choice."); break;
            }
             if (!logout && choice != 0) {
                 pause();
             }
        }
    }
}


// ==================
// Main Application Class
// ==================
public class BTOApp {

    // In-memory data stores
    private Map<String, User> users;
    private List<Project> projects;
    private Map<String, BTOApplication> applications;
    private List<Enquiry> enquiries;
    private Map<String, OfficerRegistration> officerRegistrations;

    // Core components
    private AuthController authController;
    private Scanner scanner;

    public BTOApp() {
        // Initialize scanner here
        scanner = new Scanner(System.in);
    }

    // Load data from files
    public void initialize() {
        System.out.println("Initializing BTO Management System...");
        // Load data - order matters for dependencies
        users = DataService.loadUsers();
        projects = DataService.loadProjects(users); // Pass users for validation
        applications = DataService.loadApplications(projects); // Pass projects for unit adjustment
        enquiries = DataService.loadEnquiries();
        officerRegistrations = DataService.loadOfficerRegistrations(users, projects); // Pass users/projects for validation

        // Post-load synchronization to ensure consistency between data structures
        DataService.synchronizeData(users, projects, applications, officerRegistrations);

        // Initialize controllers that need data access
        authController = new AuthController(users);
        System.out.println("Initialization complete. System ready.");
    }

    // Main application loop
    public void run() {
        User currentUser = null;
        while (true) { // Keep running until explicitly shutdown
            // Run sync before login screen to ensure applicant profiles are up-to-date
             if (this.users != null && this.projects != null && this.applications != null && this.officerRegistrations != null) {
                DataService.synchronizeData(users, projects, applications, officerRegistrations);
             } else {
                  System.err.println("Warning: Data not fully loaded, skipping pre-login sync.");
             }

            currentUser = loginScreen(); // Attempt login
            if (currentUser != null) {
                showRoleMenu(currentUser); // Show menu for logged-in user
                currentUser = null; // Reset currentUser after logout
                System.out.println("\nReturning to Login Screen...");
            } else {
                // Login failed, offer to retry or exit?
                System.out.print("Login failed. Try again? (yes/no): ");
                String retry = scanner.nextLine().trim().toLowerCase();
                if (!retry.equals("yes")) {
                    break; // Exit the main loop if user doesn't want to retry
                }
            }
        }
        System.out.println("Exiting application.");
    }

    // Handles the login process
    private User loginScreen() {
        System.out.println("\n--- BTO Management System Login ---");
        System.out.print("Enter NRIC: ");
        String nric = scanner.nextLine().trim().toUpperCase();
        System.out.print("Enter Password: ");
        String password = scanner.nextLine(); // Read password

        User user = authController.login(nric, password);
        if (user != null) {
            System.out.println("Login successful! Welcome, " + user.getName() + " (" + user.getRole() + ")");
        }
        // Error messages (invalid NRIC, wrong password, user not found) handled within AuthController.login
        return user;
    }

    // Creates and displays the appropriate menu based on user role
    private void showRoleMenu(User user) {
        BaseView view;
        BaseController controller; // Declare controller variable

        // Instantiate the correct controller and view based on the user's role
        switch (user.getRole()) {
            case APPLICANT:
                ApplicantController appController = new ApplicantController(users, projects, applications, enquiries, officerRegistrations, user, scanner, authController);
                controller = appController; // Assign to base type
                view = new ApplicantView(scanner, user, appController, authController);
                break;
            case HDB_OFFICER:
                 OfficerController offController = new OfficerController(users, projects, applications, enquiries, officerRegistrations, user, scanner, authController);
                 controller = offController; // Assign to base type
                 view = new OfficerView(scanner, user, offController, authController);
                break;
            case HDB_MANAGER:
                 ManagerController manController = new ManagerController(users, projects, applications, enquiries, officerRegistrations, user, scanner, authController);
                 controller = manController; // Assign to base type
                 view = new ManagerView(scanner, user, manController, authController);
                break;
            default:
                System.err.println("FATAL Error: Unknown user role encountered: " + user.getRole());
                return; // Cannot proceed if role is unknown
        }
        // Enter the role-specific menu loop
        view.displayMenu();
    }

    // Saves all data and closes resources
    public void shutdown() {
        System.out.println("\nShutting down BTO Management System...");
        // Save all data using the DataService method
        // Ensure data is not null before saving (might happen if init failed badly)
        if (this.users != null && this.projects != null && this.applications != null && this.enquiries != null && this.officerRegistrations != null) {
            DataService.saveAllData(users, projects, applications, enquiries, officerRegistrations);
        } else {
             System.err.println("Shutdown: Data not fully initialized, cannot save.");
        }
        // Close the scanner
        if (scanner != null) {
            try {
                scanner.close();
                 System.out.println("Scanner closed.");
            } catch (IllegalStateException e) {
                // Ignore if already closed
            }
        }
        System.out.println("System shutdown complete.");
    }


    public static void main(String[] args) {
        BTOApp app = new BTOApp();
        try {
            // Add shutdown hook *before* initialization, so it's always registered
            // This hook runs in a separate thread.
            Runtime.getRuntime().addShutdownHook(new Thread(app::shutdown, "Shutdown-Thread")); // Use method reference


            app.initialize();

            // Start the main application loop
            app.run();

        } catch (Exception e) {
             System.err.println("An unexpected critical error occurred in the main application thread: " + e.getMessage());
             e.printStackTrace();
             // Shutdown hook will attempt to save data and close resources.
             // Explicit System.exit might be needed if the main thread error prevents normal exit
             // System.exit(1); // Uncomment if needed to ensure shutdown hook runs
        }
        // Normal exit after run() loop finishes (e.g., user chooses not to retry login)
        // Shutdown hook will still run here. If run() finished normally, exit code is 0.
         System.exit(0); // Ensure JVM terminates and runs shutdown hook
    }
}