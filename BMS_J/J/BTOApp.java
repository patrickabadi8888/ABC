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
// Enums
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
     public static FlatType fromString(String text) {
        if (text != null) {
            for (FlatType b : FlatType.values()) {
                if (text.equalsIgnoreCase(b.name()) || text.equalsIgnoreCase(b.displayName)) {
                    return b;
                }
            }
        }
        return null; // Or throw exception
    }
}

enum ApplicationStatus {
    PENDING, SUCCESSFUL, UNSUCCESSFUL, BOOKED, WITHDRAWN // Added WITHDRAWN based on requirements
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
    private String nric;
    private String password;
    private String name;
    private int age;
    private MaritalStatus maritalStatus;

    public User(String nric, String password, String name, int age, MaritalStatus maritalStatus) {
        // Basic validation could go here, but keep it minimal for SRP
        this.nric = nric;
        this.password = password;
        this.name = name;
        this.age = age;
        this.maritalStatus = maritalStatus;
    }

    // Getters
    public String getNric() { return nric; }
    public String getPassword() { return password; }
    public String getName() { return name; }
    public int getAge() { return age; }
    public MaritalStatus getMaritalStatus() { return maritalStatus; }

    // Setter for password only as required
    public void setPassword(String password) {
        this.password = password;
    }

    public abstract UserRole getRole();

    // Minimal common methods if any, avoid business logic
}

class Applicant extends User {
    private String appliedProjectName; // Track the project applied for
    private ApplicationStatus applicationStatus; // Track status for the applied project
    private FlatType bookedFlatType; // Track booked flat type if status is BOOKED

    public Applicant(String nric, String password, String name, int age, MaritalStatus maritalStatus) {
        super(nric, password, name, age, maritalStatus);
        this.applicationStatus = null; // Initially no application
    }

    @Override
    public UserRole getRole() { return UserRole.APPLICANT; }

    // Getters and Setters specific to Applicant state
    public String getAppliedProjectName() { return appliedProjectName; }
    public void setAppliedProjectName(String appliedProjectName) { this.appliedProjectName = appliedProjectName; }

    public ApplicationStatus getApplicationStatus() { return applicationStatus; }
    public void setApplicationStatus(ApplicationStatus applicationStatus) { this.applicationStatus = applicationStatus; }

    public FlatType getBookedFlatType() { return bookedFlatType; }
    public void setBookedFlatType(FlatType bookedFlatType) { this.bookedFlatType = bookedFlatType; }

    public boolean hasApplied() {
        return this.appliedProjectName != null;
    }
     public boolean hasBooked() {
        return this.applicationStatus == ApplicationStatus.BOOKED;
    }
}

class HDBOfficer extends Applicant { // Inherits Applicant capabilities
    private String handlingProjectName; // Project they are registered to handle (if approved)
    // Officer registration details are stored separately in OfficerRegistration objects

    public HDBOfficer(String nric, String password, String name, int age, MaritalStatus maritalStatus) {
        super(nric, password, name, age, maritalStatus);
    }

    @Override
    public UserRole getRole() { return UserRole.HDB_OFFICER; }

    // Getters and Setters specific to Officer state
    public String getHandlingProjectName() { return handlingProjectName; }
    public void setHandlingProjectName(String handlingProjectName) { this.handlingProjectName = handlingProjectName; }
}

class HDBManager extends User {
    // Manager specific state, e.g., list of projects they manage directly
    // This might be implicitly handled by checking Project's managerNric

    public HDBManager(String nric, String password, String name, int age, MaritalStatus maritalStatus) {
        super(nric, password, name, age, maritalStatus);
    }

    @Override
    public UserRole getRole() { return UserRole.HDB_MANAGER; }

    // Managers cannot apply for BTOs, so no application-related fields needed here.
}

// --- Project Details ---
class FlatTypeDetails {
    private int totalUnits;
    private int availableUnits;
    private double sellingPrice;

    public FlatTypeDetails(int totalUnits, int availableUnits, double sellingPrice) {
        this.totalUnits = totalUnits;
        this.availableUnits = availableUnits;
        this.sellingPrice = sellingPrice;
    }

    // Getters
    public int getTotalUnits() { return totalUnits; }
    public int getAvailableUnits() { return availableUnits; }
    public double getSellingPrice() { return sellingPrice; }

    // Setters (used by Officer/System during booking)
    public void setAvailableUnits(int availableUnits) {
        if (availableUnits >= 0 && availableUnits <= this.totalUnits) {
            this.availableUnits = availableUnits;
        } else {
            System.err.println("Warning: Attempted to set invalid available units (" + availableUnits + ")");
            // Or throw exception
        }
    }
     public void decrementAvailableUnits() {
        if (this.availableUnits > 0) {
            this.availableUnits--;
        } else {
             System.err.println("Warning: Attempted to decrement zero available units.");
             // Or throw exception
        }
    }
     public void incrementAvailableUnits() {
        if (this.availableUnits < this.totalUnits) {
            this.availableUnits++;
        } else {
             System.err.println("Warning: Attempted to increment beyond total units.");
             // Or throw exception
        }
    }
}

class Project {
    private String projectName; // Should be unique
    private String neighborhood;
    private Map<FlatType, FlatTypeDetails> flatTypes;
    private Date applicationOpeningDate;
    private Date applicationClosingDate;
    private String managerNric; // NRIC of the manager who created/manages it
    private int maxOfficerSlots;
    private List<String> approvedOfficerNrics; // NRICs of approved officers
    private boolean visibility; // true = on, false = off

    // Constructor and Getters/Setters
    public Project(String projectName, String neighborhood, Map<FlatType, FlatTypeDetails> flatTypes,
                   Date applicationOpeningDate, Date applicationClosingDate, String managerNric,
                   int maxOfficerSlots, List<String> approvedOfficerNrics, boolean visibility) {
        this.projectName = projectName;
        this.neighborhood = neighborhood;
        this.flatTypes = flatTypes != null ? new HashMap<>(flatTypes) : new HashMap<>();
        this.applicationOpeningDate = applicationOpeningDate;
        this.applicationClosingDate = applicationClosingDate;
        this.managerNric = managerNric;
        this.maxOfficerSlots = maxOfficerSlots;
        this.approvedOfficerNrics = approvedOfficerNrics != null ? new ArrayList<>(approvedOfficerNrics) : new ArrayList<>();
        this.visibility = visibility;
    }

    // Getters
    public String getProjectName() { return projectName; }
    public String getNeighborhood() { return neighborhood; }
    public Map<FlatType, FlatTypeDetails> getFlatTypes() { return Collections.unmodifiableMap(flatTypes); } // Read-only view
    public Date getApplicationOpeningDate() { return applicationOpeningDate; }
    public Date getApplicationClosingDate() { return applicationClosingDate; }
    public String getManagerNric() { return managerNric; }
    public int getMaxOfficerSlots() { return maxOfficerSlots; }
    public List<String> getApprovedOfficerNrics() { return Collections.unmodifiableList(approvedOfficerNrics); } // Read-only view
    public boolean isVisible() { return visibility; }
    public int getRemainingOfficerSlots() { return maxOfficerSlots - approvedOfficerNrics.size(); }

    // Setters (primarily for Manager actions)
    public void setProjectName(String projectName) { this.projectName = projectName; }
    public void setNeighborhood(String neighborhood) { this.neighborhood = neighborhood; }
    public void setFlatTypes(Map<FlatType, FlatTypeDetails> flatTypes) { this.flatTypes = new HashMap<>(flatTypes); }
    public void setApplicationOpeningDate(Date applicationOpeningDate) { this.applicationOpeningDate = applicationOpeningDate; }
    public void setApplicationClosingDate(Date applicationClosingDate) { this.applicationClosingDate = applicationClosingDate; }
    // Manager NRIC is set on creation, usually not changed.
    public void setMaxOfficerSlots(int maxOfficerSlots) { this.maxOfficerSlots = maxOfficerSlots; }
    public void setVisibility(boolean visibility) { this.visibility = visibility; }

    // Methods to manage officers (called by ManagerController)
    public boolean addApprovedOfficer(String officerNric) {
        if (getRemainingOfficerSlots() > 0 && !approvedOfficerNrics.contains(officerNric)) {
            approvedOfficerNrics.add(officerNric);
            return true;
        }
        return false;
    }

    public boolean removeApprovedOfficer(String officerNric) {
        return approvedOfficerNrics.remove(officerNric);
    }

    // Helper to check if application period is active
    public boolean isApplicationPeriodActive(Date currentDate) {
        return !currentDate.before(applicationOpeningDate) && !currentDate.after(applicationClosingDate);
    }

    // Helper to get details for a specific flat type
    public FlatTypeDetails getFlatTypeDetails(FlatType type) {
        return flatTypes.get(type);
    }
}

// --- Application Tracking ---
class BTOApplication {
    private String applicationId; // Unique ID (e.g., NRIC + ProjectName)
    private String applicantNric;
    private String projectName;
    private FlatType flatTypeApplied; // Specific flat type applied for
    private ApplicationStatus status;
    private Date applicationDate; // Track when applied

    public BTOApplication(String applicantNric, String projectName, FlatType flatTypeApplied, Date applicationDate) {
        this.applicationId = applicantNric + "_" + projectName; // Simple unique ID
        this.applicantNric = applicantNric;
        this.projectName = projectName;
        this.flatTypeApplied = flatTypeApplied;
        this.status = ApplicationStatus.PENDING; // Default status
        this.applicationDate = applicationDate;
    }

     // Constructor for loading from file
    public BTOApplication(String applicationId, String applicantNric, String projectName, FlatType flatTypeApplied, ApplicationStatus status, Date applicationDate) {
        this.applicationId = applicationId;
        this.applicantNric = applicantNric;
        this.projectName = projectName;
        this.flatTypeApplied = flatTypeApplied;
        this.status = status;
        this.applicationDate = applicationDate;
    }


    // Getters
    public String getApplicationId() { return applicationId; }
    public String getApplicantNric() { return applicantNric; }
    public String getProjectName() { return projectName; }
    public FlatType getFlatTypeApplied() { return flatTypeApplied; }
    public ApplicationStatus getStatus() { return status; }
    public Date getApplicationDate() { return applicationDate; }

    // Setter (primarily for status changes by Manager/Officer)
    public void setStatus(ApplicationStatus status) {
        this.status = status;
    }
     public void setFlatTypeApplied(FlatType flatTypeApplied) {
        this.flatTypeApplied = flatTypeApplied;
    }
}

// --- Enquiry Tracking ---
class Enquiry {
    private String enquiryId; // Unique ID
    private String applicantNric;
    private String projectName; // Project the enquiry is about
    private String enquiryText;
    private String replyText;
    private String repliedByNric; // NRIC of Officer/Manager who replied
    private Date enquiryDate;
    private Date replyDate;
    private static long nextId = 1; // Simple ID generation

    // Constructor for new enquiry
    public Enquiry(String applicantNric, String projectName, String enquiryText, Date enquiryDate) {
        this.enquiryId = "ENQ" + (nextId++); // Generate unique ID
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
        this.enquiryId = enquiryId;
        this.applicantNric = applicantNric;
        this.projectName = projectName;
        this.enquiryText = enquiryText;
        this.replyText = replyText;
        this.repliedByNric = repliedByNric;
        this.enquiryDate = enquiryDate;
        this.replyDate = replyDate;
        // Ensure nextId is updated correctly after loading
        try {
            long idNum = Long.parseLong(enquiryId.substring(3));
            if (idNum >= nextId) {
                nextId = idNum + 1;
            }
        } catch (NumberFormatException | StringIndexOutOfBoundsException e) {
            // Ignore if ID format is unexpected during loading
        }
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
    public void setEnquiryText(String enquiryText) {
        // Can only edit if not replied
        if (this.replyText == null) {
            this.enquiryText = enquiryText;
        } else {
             System.err.println("Cannot edit an enquiry that has already been replied to.");
        }
    }

    public void setReply(String replyText, String repliedByNric, Date replyDate) {
        this.replyText = replyText;
        this.repliedByNric = repliedByNric;
        this.replyDate = replyDate;
    }

    public boolean isReplied() {
        return this.replyText != null && !this.replyText.isEmpty();
    }
}

// --- Officer Registration Tracking ---
class OfficerRegistration {
    private String registrationId; // Unique ID (e.g., OfficerNRIC + ProjectName)
    private String officerNric;
    private String projectName;
    private OfficerRegistrationStatus status;
    private Date registrationDate;

    public OfficerRegistration(String officerNric, String projectName, Date registrationDate) {
        this.registrationId = officerNric + "_REG_" + projectName;
        this.officerNric = officerNric;
        this.projectName = projectName;
        this.status = OfficerRegistrationStatus.PENDING;
        this.registrationDate = registrationDate;
    }

     // Constructor for loading from file
    public OfficerRegistration(String registrationId, String officerNric, String projectName, OfficerRegistrationStatus status, Date registrationDate) {
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
        this.status = status;
    }
}


// ==================
// Data Service (Handles CSV Persistence - SRP)
// ==================
class DataService {
    private static final String PROJECT_FILE = "ProjectList.csv";
    private static final String APPLICATION_FILE = "applications.csv";
    private static final String ENQUIRY_FILE = "enquiries.csv";
    private static final String OFFICER_REGISTRATION_FILE = "officer_registrations.csv";
    private static final String DELIMITER = ",";
    private static final String LIST_DELIMITER = ";"; // For lists within a cell (like officers)
    public static final SimpleDateFormat DATE_FORMAT = new SimpleDateFormat("yyyy-MM-dd");
    private static final Pattern NRIC_PATTERN = Pattern.compile("^[ST]\\d{7}[A-Z]$");

    // --- Loading Methods ---

    public static Map<String, User> loadUsers() {
        Map<String, User> users = new HashMap<>();
        List<String[]> applicantData = readCsv("ApplicantList.csv");
        List<String[]> officerData = readCsv("OfficerList.csv");
        List<String[]> managerData = readCsv("ManagerList.csv");

        // Process Applicants
        for (String[] data : applicantData) {
            if (data.length >= 5) {
                try {
                    String nric = data[1].trim();
                    if (!isValidNric(nric)) continue; // Skip invalid NRIC
                    int age = Integer.parseInt(data[2].trim());
                    MaritalStatus status = MaritalStatus.valueOf(data[3].trim().toUpperCase());
                    Applicant applicant = new Applicant(nric, data[4].trim(), data[0].trim(), age, status);
                    users.put(nric, applicant);
                } catch (Exception e) {
                    System.err.println("Error parsing applicant data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
                }
            }
        }

        // Process Officers (they are also Applicants initially)
        for (String[] data : officerData) {
             if (data.length >= 5) {
                try {
                    String nric = data[1].trim();
                     if (!isValidNric(nric)) continue;
                    int age = Integer.parseInt(data[2].trim());
                    MaritalStatus status = MaritalStatus.valueOf(data[3].trim().toUpperCase());
                    // Create as HDBOfficer, inheriting Applicant properties
                    HDBOfficer officer = new HDBOfficer(nric, data[4].trim(), data[0].trim(), age, status);
                    users.put(nric, officer); // Overwrites if NRIC was already in applicant list
                } catch (Exception e) {
                    System.err.println("Error parsing officer data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
                }
            }
        }

        // Process Managers
        for (String[] data : managerData) {
             if (data.length >= 5) {
                try {
                    String nric = data[1].trim();
                     if (!isValidNric(nric)) continue;
                    int age = Integer.parseInt(data[2].trim());
                    MaritalStatus status = MaritalStatus.valueOf(data[3].trim().toUpperCase());
                    HDBManager manager = new HDBManager(nric, data[4].trim(), data[0].trim(), age, status);
                    users.put(nric, manager); // Overwrites if NRIC was already in other lists
                } catch (Exception e) {
                    System.err.println("Error parsing manager data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
                }
            }
        }

        // Load additional user state from other files if necessary (like applied project)
        // This might be better handled after loading applications
        Map<String, BTOApplication> applications = loadApplications();
        for (BTOApplication app : applications.values()) {
            User user = users.get(app.getApplicantNric());
            if (user instanceof Applicant) { // Includes HDBOfficer
                Applicant applicant = (Applicant) user;
                applicant.setAppliedProjectName(app.getProjectName());
                applicant.setApplicationStatus(app.getStatus());
                if (app.getStatus() == ApplicationStatus.BOOKED) {
                    applicant.setBookedFlatType(app.getFlatTypeApplied());
                }
            }
        }

        // Load handling project for officers
         List<Project> projects = loadProjects(users); // Need users to validate manager NRIC
        for (Project project : projects) {
            for (String officerNric : project.getApprovedOfficerNrics()) {
                 User user = users.get(officerNric);
                 if (user instanceof HDBOfficer) {
                     ((HDBOfficer) user).setHandlingProjectName(project.getProjectName());
                 }
            }
        }


        System.out.println("Loaded " + users.size() + " users.");
        return users;
    }

     public static List<Project> loadProjects(Map<String, User> users) { // Pass users to validate manager
        List<Project> projects = new ArrayList<>();
        List<String[]> dataList = readCsv(PROJECT_FILE);
        for (String[] data : dataList) {
            if (data.length >= 13) { // Expecting 13 columns based on sample
                try {
                    String projectName = data[0].trim();
                    String neighborhood = data[1].trim();
                    Map<FlatType, FlatTypeDetails> flatTypes = new HashMap<>();

                    // Type 1
                    FlatType type1 = FlatType.fromDisplayName(data[2].trim());
                    int units1 = Integer.parseInt(data[3].trim());
                    double price1 = Double.parseDouble(data[4].trim());
                    // Assume available units = total units initially if not stored separately
                    flatTypes.put(type1, new FlatTypeDetails(units1, units1, price1));

                    // Type 2
                    FlatType type2 = FlatType.fromDisplayName(data[5].trim());
                    int units2 = Integer.parseInt(data[6].trim());
                    double price2 = Double.parseDouble(data[7].trim());
                    flatTypes.put(type2, new FlatTypeDetails(units2, units2, price2));

                    Date openingDate = DATE_FORMAT.parse(data[8].trim());
                    Date closingDate = DATE_FORMAT.parse(data[9].trim());
                    String managerNric = data[10].trim();
                    int officerSlots = Integer.parseInt(data[11].trim());

                    // Parse officer list (assuming semicolon separated)
                    List<String> officers = new ArrayList<>();
                    if (data[12] != null && !data[12].trim().isEmpty() && !data[12].trim().equals("\"\"")) {
                         // Handle potential quotes around the list
                        String officerListStr = data[12].trim();
                        if (officerListStr.startsWith("\"") && officerListStr.endsWith("\"")) {
                            officerListStr = officerListStr.substring(1, officerListStr.length() - 1);
                        }
                        officers.addAll(Arrays.asList(officerListStr.split(LIST_DELIMITER)));
                        officers.replaceAll(String::trim); // Trim whitespace from each NRIC
                        officers.removeIf(String::isEmpty); // Remove empty entries if any
                    }


                    // Validate manager NRIC exists and is a Manager
                    if (!users.containsKey(managerNric) || !(users.get(managerNric) instanceof HDBManager)) {
                        System.err.println("Warning: Project '" + projectName + "' has invalid or non-manager NRIC: " + managerNric + ". Skipping project.");
                        continue;
                    }

                    // Visibility not in sample CSV, assume true initially or add a column
                    boolean visibility = true; // Default assumption

                    Project project = new Project(projectName, neighborhood, flatTypes, openingDate, closingDate, managerNric, officerSlots, officers, visibility);
                    projects.add(project);

                } catch (ParseException e) {
                    System.err.println("Error parsing date in project data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
                } catch (NumberFormatException e) {
                    System.err.println("Error parsing number in project data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
                } catch (IllegalArgumentException e) {
                    System.err.println("Error parsing enum/data in project data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
                } catch (Exception e) { // Catch broader exceptions
                     System.err.println("Unexpected error parsing project data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
                     e.printStackTrace(); // Print stack trace for debugging
                }
            } else {
                 System.err.println("Skipping malformed project data line (expected 13 columns): " + String.join(DELIMITER, data));
            }
        }
         // Adjust available units based on booked applications after loading projects and applications
        Map<String, BTOApplication> applications = loadApplications();
        for (BTOApplication app : applications.values()) {
            if (app.getStatus() == ApplicationStatus.BOOKED) {
                Project project = projects.stream()
                                        .filter(p -> p.getProjectName().equals(app.getProjectName()))
                                        .findFirst()
                                        .orElse(null);
                if (project != null && app.getFlatTypeApplied() != null) {
                    FlatTypeDetails details = project.getFlatTypeDetails(app.getFlatTypeApplied());
                    if (details != null) {
                        details.decrementAvailableUnits(); // Decrement for booked flats
                    }
                }
            }
        }

        System.out.println("Loaded " + projects.size() + " projects.");
        return projects;
    }

    public static Map<String, BTOApplication> loadApplications() {
        Map<String, BTOApplication> applications = new HashMap<>();
        List<String[]> dataList = readCsv(APPLICATION_FILE);
        for (String[] data : dataList) {
            if (data.length >= 6) {
                try {
                    String appId = data[0].trim();
                    String applicantNric = data[1].trim();
                    String projectName = data[2].trim();
                    // Handle potentially null/empty flat type before booking
                    FlatType flatType = null;
                    if (data[3] != null && !data[3].trim().isEmpty() && !data[3].trim().equalsIgnoreCase("null")) {
                         flatType = FlatType.fromString(data[3].trim());
                    }
                    ApplicationStatus status = ApplicationStatus.valueOf(data[4].trim().toUpperCase());
                    Date appDate = DATE_FORMAT.parse(data[5].trim());

                    BTOApplication application = new BTOApplication(appId, applicantNric, projectName, flatType, status, appDate);
                    applications.put(application.getApplicationId(), application);
                } catch (Exception e) {
                    System.err.println("Error parsing application data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
                }
            }
        }
        System.out.println("Loaded " + applications.size() + " applications.");
        return applications;
    }

    public static List<Enquiry> loadEnquiries() {
        List<Enquiry> enquiries = new ArrayList<>();
        List<String[]> dataList = readCsv(ENQUIRY_FILE);
        for (String[] data : dataList) {
             if (data.length >= 8) { // ID, Applicant, Project, Text, Reply, RepliedBy, EnqDate, ReplyDate
                try {
                    String id = data[0].trim();
                    String applicantNric = data[1].trim();
                    String projectName = data[2].trim();
                    String text = data[3].trim();
                    String reply = data[4].trim().isEmpty() ? null : data[4].trim();
                    String repliedBy = data[5].trim().isEmpty() ? null : data[5].trim();
                    Date enqDate = DATE_FORMAT.parse(data[6].trim());
                    Date replyDate = (data[7] == null || data[7].trim().isEmpty() || data[7].trim().equalsIgnoreCase("null")) ? null : DATE_FORMAT.parse(data[7].trim());

                    Enquiry enquiry = new Enquiry(id, applicantNric, projectName, text, reply, repliedBy, enqDate, replyDate);
                    enquiries.add(enquiry);
                } catch (Exception e) {
                    System.err.println("Error parsing enquiry data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
                }
            }
        }
        System.out.println("Loaded " + enquiries.size() + " enquiries.");
        return enquiries;
    }

     public static Map<String, OfficerRegistration> loadOfficerRegistrations() {
        Map<String, OfficerRegistration> registrations = new HashMap<>();
        List<String[]> dataList = readCsv(OFFICER_REGISTRATION_FILE);
        for (String[] data : dataList) {
            if (data.length >= 5) {
                try {
                    String regId = data[0].trim();
                    String officerNric = data[1].trim();
                    String projectName = data[2].trim();
                    OfficerRegistrationStatus status = OfficerRegistrationStatus.valueOf(data[3].trim().toUpperCase());
                    Date regDate = DATE_FORMAT.parse(data[4].trim());

                    OfficerRegistration registration = new OfficerRegistration(regId, officerNric, projectName, status, regDate);
                    registrations.put(registration.getRegistrationId(), registration);
                } catch (Exception e) {
                    System.err.println("Error parsing officer registration data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
                }
            }
        }
        System.out.println("Loaded " + registrations.size() + " officer registrations.");
        return registrations;
    }


    // --- Saving Methods ---

    public static void saveUsers(Map<String, User> users) {
        // Separate users by role for saving back to original files (or a combined one if preferred)
        List<String[]> applicantData = new ArrayList<>();
        List<String[]> officerData = new ArrayList<>();
        List<String[]> managerData = new ArrayList<>();

        // Add headers
        applicantData.add(new String[]{"Name", "NRIC", "Age", "Marital Status", "Password"});
        officerData.add(new String[]{"Name", "NRIC", "Age", "Marital Status", "Password"});
        managerData.add(new String[]{"Name", "NRIC", "Age", "Marital Status", "Password"});

        for (User user : users.values()) {
            String[] userData = {
                user.getName(),
                user.getNric(),
                String.valueOf(user.getAge()),
                user.getMaritalStatus().name(),
                user.getPassword() // Save current password
            };
            if (user instanceof HDBManager) {
                managerData.add(userData);
            } else if (user instanceof HDBOfficer) {
                officerData.add(userData);
            } else if (user instanceof Applicant) {
                applicantData.add(userData);
            }
        }

        writeCsv("ApplicantList.csv", applicantData);
        writeCsv("OfficerList.csv", officerData);
        writeCsv("ManagerList.csv", managerData);
        System.out.println("Saved users.");
    }

    public static void saveProjects(List<Project> projects) {
        List<String[]> dataList = new ArrayList<>();
        // Add header matching the load format
        dataList.add(new String[]{
            "Project Name", "Neighborhood", "Type 1", "Number of units for Type 1", "Selling price for Type 1",
            "Type 2", "Number of units for Type 2", "Selling price for Type 2",
            "Application opening date", "Application closing date", "Manager", "Officer Slot", "Officer"
        });

        for (Project project : projects) {
            String[] data = new String[13];
            data[0] = project.getProjectName();
            data[1] = project.getNeighborhood();

            // Assuming exactly TWO_ROOM and THREE_ROOM exist
            FlatTypeDetails twoRoomDetails = project.getFlatTypeDetails(FlatType.TWO_ROOM);
            FlatTypeDetails threeRoomDetails = project.getFlatTypeDetails(FlatType.THREE_ROOM);

            if (twoRoomDetails != null) {
                data[2] = FlatType.TWO_ROOM.getDisplayName();
                data[3] = String.valueOf(twoRoomDetails.getTotalUnits()); // Save total units
                data[4] = String.valueOf(twoRoomDetails.getSellingPrice());
            } else {
                 data[2] = ""; data[3] = "0"; data[4] = "0"; // Or handle differently
            }

            if (threeRoomDetails != null) {
                data[5] = FlatType.THREE_ROOM.getDisplayName();
                data[6] = String.valueOf(threeRoomDetails.getTotalUnits()); // Save total units
                data[7] = String.valueOf(threeRoomDetails.getSellingPrice());
            } else {
                 data[5] = ""; data[6] = "0"; data[7] = "0";
            }

            data[8] = DATE_FORMAT.format(project.getApplicationOpeningDate());
            data[9] = DATE_FORMAT.format(project.getApplicationClosingDate());
            data[10] = project.getManagerNric();
            data[11] = String.valueOf(project.getMaxOfficerSlots());
            // Join approved officers with semicolon, handle empty list
            String officers = project.getApprovedOfficerNrics().isEmpty() ? "" : String.join(LIST_DELIMITER, project.getApprovedOfficerNrics());
             // Add quotes if it contains the delimiter or needs escaping, though simple join might suffice
            data[12] = "\"" + officers + "\""; // Enclose in quotes like sample

            // Add visibility if column exists/needed
            // data[13] = String.valueOf(project.isVisible());

            dataList.add(data);
        }
        writeCsv(PROJECT_FILE, dataList);
        System.out.println("Saved projects.");
    }

    public static void saveApplications(Map<String, BTOApplication> applications) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(new String[]{"ApplicationID", "ApplicantNRIC", "ProjectName", "FlatTypeApplied", "Status", "ApplicationDate"});
        for (BTOApplication app : applications.values()) {
            dataList.add(new String[]{
                app.getApplicationId(),
                app.getApplicantNric(),
                app.getProjectName(),
                app.getFlatTypeApplied() == null ? "null" : app.getFlatTypeApplied().name(), // Save enum name or "null"
                app.getStatus().name(),
                DATE_FORMAT.format(app.getApplicationDate())
            });
        }
        writeCsv(APPLICATION_FILE, dataList);
        System.out.println("Saved applications.");
    }

    public static void saveEnquiries(List<Enquiry> enquiries) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(new String[]{"EnquiryID", "ApplicantNRIC", "ProjectName", "EnquiryText", "ReplyText", "RepliedByNRIC", "EnquiryDate", "ReplyDate"});
        for (Enquiry enq : enquiries) {
            dataList.add(new String[]{
                enq.getEnquiryId(),
                enq.getApplicantNric(),
                enq.getProjectName(),
                enq.getEnquiryText(),
                enq.getReplyText() == null ? "" : enq.getReplyText(),
                enq.getRepliedByNric() == null ? "" : enq.getRepliedByNric(),
                DATE_FORMAT.format(enq.getEnquiryDate()),
                enq.getReplyDate() == null ? "null" : DATE_FORMAT.format(enq.getReplyDate())
            });
        }
        writeCsv(ENQUIRY_FILE, dataList);
        System.out.println("Saved enquiries.");
    }

     public static void saveOfficerRegistrations(Map<String, OfficerRegistration> registrations) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(new String[]{"RegistrationID", "OfficerNRIC", "ProjectName", "Status", "RegistrationDate"});
        for (OfficerRegistration reg : registrations.values()) {
            dataList.add(new String[]{
                reg.getRegistrationId(),
                reg.getOfficerNric(),
                reg.getProjectName(),
                reg.getStatus().name(),
                DATE_FORMAT.format(reg.getRegistrationDate())
            });
        }
        writeCsv(OFFICER_REGISTRATION_FILE, dataList);
        System.out.println("Saved officer registrations.");
    }

    // --- Helper Methods ---

    private static List<String[]> readCsv(String filename) {
        List<String[]> data = new ArrayList<>();
        Path path = Paths.get(filename);
        if (!Files.exists(path)) {
            System.err.println("Warning: File not found - " + filename);
            // Create empty file?
             try {
                 Files.createFile(path);
                 // Write header if needed for new files
                 if (filename.equals(APPLICATION_FILE)) {
                    writeCsv(filename,
                             Collections.singletonList(new String[]{
                               "ApplicationID",
                               "ApplicantNRIC",
                               "ProjectName",
                               "FlatTypeApplied",
                               "Status",
                               "ApplicationDate"
                             }));
                }
                if (filename.equals(ENQUIRY_FILE)) {
                    writeCsv(filename,
                             Collections.singletonList(new String[]{
                               "EnquiryID",
                               "ApplicantNRIC",
                               "ProjectName",
                               "EnquiryText",
                               "ReplyText",
                               "RepliedByNRIC",
                               "EnquiryDate",
                               "ReplyDate"
                             }));
                }
                if (filename.equals(OFFICER_REGISTRATION_FILE)) {
                    writeCsv(filename,
                             Collections.singletonList(new String[]{
                               "RegistrationID",
                               "OfficerNRIC",
                               "ProjectName",
                               "Status",
                               "RegistrationDate"
                             }));
                }

             } catch (IOException e) {
                 System.err.println("Error creating file: " + filename + " - " + e.getMessage());
             }
            return data; // Return empty list
        }

        try (BufferedReader br = Files.newBufferedReader(path)) {
            String line;
            boolean isFirstLine = true; // To skip header
            while ((line = br.readLine()) != null) {
                if (isFirstLine || line.trim().isEmpty()) {
                    isFirstLine = false;
                    continue; // Skip header row and empty lines
                }
                // Basic CSV split, may need improvement for quoted fields containing commas
                String[] values = line.split(DELIMITER + "(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", -1);
                 // Trim whitespace and remove quotes from each value
                for (int i = 0; i < values.length; i++) {
                    values[i] = values[i].trim();
                    if (values[i].startsWith("\"") && values[i].endsWith("\"")) {
                        values[i] = values[i].substring(1, values[i].length() - 1);
                    }
                }
                data.add(values);
            }
        } catch (IOException e) {
            System.err.println("Error reading file: " + filename + " - " + e.getMessage());
        }
        return data;
    }

    private static void writeCsv(String filename, List<String[]> data) {
        Path path = Paths.get(filename);
        try (BufferedWriter bw = Files.newBufferedWriter(path, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING)) {
            for (String[] row : data) {
                String line = Arrays.stream(row)
                                    .map(DataService::escapeCsvField)
                                    .collect(Collectors.joining(DELIMITER));
                bw.write(line);
                bw.newLine();
            }
        } catch (IOException e) {
            System.err.println("Error writing file: " + filename + " - " + e.getMessage());
        }
    }

     // Simple CSV field escaping (add quotes if it contains delimiter, quote, or newline)
    private static String escapeCsvField(String field) {
        if (field == null) return "";
        if (field.contains(DELIMITER) || field.contains("\"") || field.contains("\n") || field.contains("\r")) {
            return "\"" + field.replace("\"", "\"\"") + "\""; // Escape quotes by doubling them
        }
        return field;
    }


    public static boolean isValidNric(String nric) {
        if (nric == null) return false;
        return NRIC_PATTERN.matcher(nric).matches();
    }

    public static Date getCurrentDate() {
        // In a real system, use LocalDate/LocalDateTime. For simplicity here:
        // return new Date();
        // For testing specific date-related logic (like application periods),
        // allow setting a fixed date.
        try {
             // Set a fixed date for consistent testing if needed
             // return DATE_FORMAT.parse("2025-03-01");
             return new Date(); // Use current system date
        } catch (/*ParseException*/ Exception e) {
             return new Date(); // Fallback
        }
    }
}

// ==================
// Services (Business Logic - Could be part of Controllers or separate)
// ==================

// Using Controllers directly for logic in this simpler structure.
// If complexity grows, extract logic into dedicated Service classes.

// ==================
// Controllers (Handle User Input, Interact with Models/DataService)
// ==================

class AuthController {
    private final Map<String, User> users;

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
            return user;
        } else if (user != null) {
            System.out.println("Incorrect password.");
            return null;
        } else {
            System.out.println("User NRIC not found.");
            return null;
        }
    }

    public boolean changePassword(User user, String oldPassword, String newPassword) {
        if (user.getPassword().equals(oldPassword)) {
            user.setPassword(newPassword);
            // No need to save immediately here, save happens globally on exit
            System.out.println("Password changed successfully. Please log in again.");
            return true;
        } else {
            System.out.println("Incorrect old password.");
            return false;
        }
    }
}

// --- Base Controller for common functionalities ---
abstract class BaseController {
    protected final Map<String, User> users;
    protected final List<Project> projects;
    protected final Map<String, BTOApplication> applications;
    protected final List<Enquiry> enquiries;
    protected final Map<String, OfficerRegistration> officerRegistrations;
    protected final User currentUser;
    protected final Scanner scanner;

    // Filter settings saved per user session
    protected String filterLocation = null;
    protected FlatType filterFlatType = null;
    // Add more filters as needed (e.g., price range, date range)

    public BaseController(Map<String, User> users, List<Project> projects, Map<String, BTOApplication> applications, List<Enquiry> enquiries, Map<String, OfficerRegistration> officerRegistrations, User currentUser, Scanner scanner) {
        this.users = users;
        this.projects = projects;
        this.applications = applications;
        this.enquiries = enquiries;
        this.officerRegistrations = officerRegistrations;
        this.currentUser = currentUser;
        this.scanner = scanner;
    }

    // Common utility methods
    protected Project findProjectByName(String name) {
        return projects.stream()
                       .filter(p -> p.getProjectName().equalsIgnoreCase(name))
                       .findFirst()
                       .orElse(null);
    }

     protected BTOApplication findApplicationByApplicantAndProject(String nric, String projectName) {
        String appId = nric + "_" + projectName;
        return applications.get(appId);
    }

     protected List<Project> getFilteredProjects(boolean checkVisibility, boolean checkEligibility) {
        Date currentDate = DataService.getCurrentDate();
        return projects.stream()
                .filter(p -> filterLocation == null || p.getNeighborhood().equalsIgnoreCase(filterLocation))
                .filter(p -> {
                    if (filterFlatType == null) return true;
                    FlatTypeDetails details = p.getFlatTypeDetails(filterFlatType);
                    return details != null && details.getAvailableUnits() > 0; // Check availability for filtered type
                })
                .filter(p -> !checkVisibility || p.isVisible() || (currentUser instanceof HDBOfficer && p.getProjectName().equals(((HDBOfficer)currentUser).getHandlingProjectName())) || (currentUser instanceof HDBManager) ) // Visibility check
                .filter(p -> !checkEligibility || isEligibleToView(p, currentDate)) // Eligibility check for applicants
                .sorted(Comparator.comparing(Project::getProjectName)) // Default sort
                .collect(Collectors.toList());
    }

     // Check if the current user (assumed Applicant/Officer) is eligible to view/apply
     protected boolean isEligibleToView(Project project, Date currentDate) {
         if (currentUser instanceof HDBManager) return true; // Managers see all

         // Check if application period is closed (but allow viewing if already applied)
         boolean appliedToThis = (currentUser instanceof Applicant) && project.getProjectName().equals(((Applicant)currentUser).getAppliedProjectName());
         if (!project.isApplicationPeriodActive(currentDate) && !appliedToThis) {
             // If period is closed AND user hasn't applied, they shouldn't see it for *new* applications
             // But the requirement says they can view applied projects even after visibility off.
             // Let's refine: Visibility toggle controls general view, eligibility controls application.
             // If visibility is OFF, only applied users or staff see it.
             // If visibility is ON, check eligibility based on role/status.
             if (!project.isVisible() && !appliedToThis && !(currentUser instanceof HDBOfficer && project.getProjectName().equals(((HDBOfficer)currentUser).getHandlingProjectName()))) {
                 return false; // Hidden and not involved
             }
             // If visible or involved, proceed to check role eligibility
         }


         if (currentUser.getMaritalStatus() == MaritalStatus.SINGLE) {
             // Single: 35+ and project must have 2-Room flats
             return currentUser.getAge() >= 35 && project.getFlatTypes().containsKey(FlatType.TWO_ROOM);
         } else if (currentUser.getMaritalStatus() == MaritalStatus.MARRIED) {
             // Married: 21+ and project must have *any* flat type
             return currentUser.getAge() >= 21 && !project.getFlatTypes().isEmpty();
         }
         return false; // Should not happen
     }

     protected boolean canApplyForFlatType(FlatType type) {
         if (currentUser.getMaritalStatus() == MaritalStatus.SINGLE) {
             return currentUser.getAge() >= 35 && type == FlatType.TWO_ROOM;
         } else if (currentUser.getMaritalStatus() == MaritalStatus.MARRIED) {
             return currentUser.getAge() >= 21 && (type == FlatType.TWO_ROOM || type == FlatType.THREE_ROOM);
         }
         return false;
     }

     protected void applyFilters() {
         System.out.println("\n--- Apply Filters ---");
         System.out.print("Enter neighborhood to filter by (or leave blank to clear): ");
         String loc = scanner.nextLine().trim();
         filterLocation = loc.isEmpty() ? null : loc;

         System.out.print("Enter flat type to filter by (TWO_ROOM, THREE_ROOM, or leave blank to clear): ");
         String typeStr = scanner.nextLine().trim().toUpperCase();
         try {
             filterFlatType = typeStr.isEmpty() ? null : FlatType.valueOf(typeStr);
         } catch (IllegalArgumentException e) {
             System.out.println("Invalid flat type. Filter not applied.");
             filterFlatType = null; // Keep previous or clear? Let's clear on invalid input.
         }
         System.out.println("Filters updated. Current filters: Location=" + (filterLocation == null ? "Any" : filterLocation) + ", FlatType=" + (filterFlatType == null ? "Any" : filterFlatType));
     }

     protected void viewAndSelectProject(List<Project> projectList, String prompt) {
         if (projectList.isEmpty()) {
             System.out.println("No projects match the current filters or eligibility criteria.");
             return;
         }

         System.out.println("\n--- " + prompt + " ---");
         System.out.println("Current Filters: Location=" + (filterLocation == null ? "Any" : filterLocation) + ", FlatType=" + (filterFlatType == null ? "Any" : filterFlatType));
         for (int i = 0; i < projectList.size(); i++) {
             Project p = projectList.get(i);
             System.out.printf("%d. %s (%s) - Open: %s, Close: %s [Vis: %s]\n",
                     i + 1, p.getProjectName(), p.getNeighborhood(),
                     DataService.DATE_FORMAT.format(p.getApplicationOpeningDate()),
                     DataService.DATE_FORMAT.format(p.getApplicationClosingDate()),
                     p.isVisible() ? "On" : "Off");
             p.getFlatTypes().forEach((type, details) ->
                     System.out.printf("   - %s: %d / %d units available, Price: $%.2f\n",
                             type.getDisplayName(), details.getAvailableUnits(), details.getTotalUnits(), details.getSellingPrice()));
              System.out.printf("   - Manager: %s, Officers: %d/%d\n", p.getManagerNric(), p.getApprovedOfficerNrics().size(), p.getMaxOfficerSlots());
         }
         System.out.println("--------------------");
     }

     protected Project selectProjectFromList(List<Project> projectList) {
         if (projectList.isEmpty()) return null;
         System.out.print("Enter the number of the project: ");
         int choice;
         try {
             choice = Integer.parseInt(scanner.nextLine());
             if (choice >= 1 && choice <= projectList.size()) {
                 return projectList.get(choice - 1);
             } else {
                 System.out.println("Invalid choice.");
                 return null;
             }
         } catch (NumberFormatException e) {
             System.out.println("Invalid input. Please enter a number.");
             return null;
         }
     }
}


class ApplicantController extends BaseController {

    public ApplicantController(Map<String, User> users, List<Project> projects, Map<String, BTOApplication> applications, List<Enquiry> enquiries, Map<String, OfficerRegistration> officerRegistrations, User currentUser, Scanner scanner) {
        super(users, projects, applications, enquiries, officerRegistrations, currentUser, scanner);
    }

    // Applicant specific actions
    public void viewOpenProjects() {
        List<Project> visibleProjects = getFilteredProjects(true, true); // Check visibility and eligibility
        viewAndSelectProject(visibleProjects, "Available BTO Projects");
        // No selection needed here, just viewing
    }

    public void applyForProject() {
        Applicant applicant = (Applicant) currentUser; // Cast is safe here

        if (applicant.hasApplied() && applicant.getApplicationStatus() != ApplicationStatus.UNSUCCESSFUL && applicant.getApplicationStatus() != ApplicationStatus.WITHDRAWN) {
            System.out.println("You have already applied for project '" + applicant.getAppliedProjectName() + "' with status: " + applicant.getApplicationStatus());
            System.out.println("You must withdraw or be unsuccessful before applying again.");
            return;
        }
         if (applicant.hasBooked()) {
             System.out.println("You have already booked a flat. You cannot apply for another project.");
             return;
         }

        List<Project> eligibleProjects = getFilteredProjects(true, true) // Check visibility & eligibility
                                        .stream()
                                        .filter(p -> p.isApplicationPeriodActive(DataService.getCurrentDate())) // Only show projects currently open for application
                                        .collect(Collectors.toList());

        if (eligibleProjects.isEmpty()) {
            System.out.println("There are currently no open projects you are eligible to apply for.");
            return;
        }

        viewAndSelectProject(eligibleProjects, "Select Project to Apply For");
        Project selectedProject = selectProjectFromList(eligibleProjects);

        if (selectedProject != null) {
            FlatType selectedFlatType = null;
            boolean canApply = false;

            // Determine eligible flat type(s)
            List<FlatType> availableTypesInProject = new ArrayList<>(selectedProject.getFlatTypes().keySet());
            List<FlatType> eligibleTypesForUser = new ArrayList<>();

            for(FlatType ft : availableTypesInProject) {
                if (canApplyForFlatType(ft)) {
                     FlatTypeDetails details = selectedProject.getFlatTypeDetails(ft);
                     if (details != null && details.getAvailableUnits() > 0) { // Check availability
                         eligibleTypesForUser.add(ft);
                     } else {
                         System.out.println("Note: " + ft.getDisplayName() + " is available in this project but has no units left.");
                     }
                }
            }

            if (eligibleTypesForUser.isEmpty()) {
                 System.out.println("You are not eligible for any available flat types in this project, or there are no units left for eligible types.");
                 return;
            }

            if (currentUser.getMaritalStatus() == MaritalStatus.SINGLE) {
                // Singles can ONLY apply for 2-Room, if available and eligible
                if (eligibleTypesForUser.contains(FlatType.TWO_ROOM)) {
                    selectedFlatType = FlatType.TWO_ROOM;
                    canApply = true;
                    System.out.println("As a single applicant, you will be applying for a " + selectedFlatType.getDisplayName() + ".");
                } else {
                     System.out.println("You are only eligible for 2-Room flats, which are not available or have no units left in this project.");
                     return; // Exit if the only eligible type isn't available
                }
            } else { // Married
                // Married can apply for any available type they are eligible for
                if (eligibleTypesForUser.size() == 1) {
                    selectedFlatType = eligibleTypesForUser.get(0);
                    canApply = true;
                     System.out.println("You will be applying for the only available eligible type: " + selectedFlatType.getDisplayName() + ".");
                } else {
                    System.out.println("Select the flat type you want to apply for:");
                    for (int i = 0; i < eligibleTypesForUser.size(); i++) {
                        System.out.println((i + 1) + ". " + eligibleTypesForUser.get(i).getDisplayName());
                    }
                    System.out.print("Enter choice: ");
                    try {
                        int typeChoice = Integer.parseInt(scanner.nextLine());
                        if (typeChoice >= 1 && typeChoice <= eligibleTypesForUser.size()) {
                            selectedFlatType = eligibleTypesForUser.get(typeChoice - 1);
                            canApply = true;
                        } else {
                            System.out.println("Invalid choice.");
                        }
                    } catch (NumberFormatException e) {
                        System.out.println("Invalid input.");
                    }
                }
            }

            if (canApply && selectedFlatType != null) {
                 // Check if officer is trying to apply for a project they handle/registered for
                 if (currentUser instanceof HDBOfficer) {
                     HDBOfficer officer = (HDBOfficer) currentUser;
                     if (selectedProject.getProjectName().equals(officer.getHandlingProjectName())) {
                         System.out.println("Error: You cannot apply for a project you are handling as an Officer.");
                         return;
                     }
                     // Check pending registrations too
                     OfficerRegistration pendingReg = officerRegistrations.values().stream()
                         .filter(reg -> reg.getOfficerNric().equals(officer.getNric()) &&
                                        reg.getProjectName().equals(selectedProject.getProjectName()) &&
                                        reg.getStatus() == OfficerRegistrationStatus.PENDING)
                         .findFirst().orElse(null);
                     if (pendingReg != null) {
                          System.out.println("Error: You cannot apply for a project you have a pending registration for.");
                          return;
                     }
                 }


                // Create application
                BTOApplication newApplication = new BTOApplication(currentUser.getNric(), selectedProject.getProjectName(), selectedFlatType, DataService.getCurrentDate());
                applications.put(newApplication.getApplicationId(), newApplication);

                // Update applicant's state
                applicant.setAppliedProjectName(selectedProject.getProjectName());
                applicant.setApplicationStatus(ApplicationStatus.PENDING);
                applicant.setBookedFlatType(null); // Reset booked type

                System.out.println("Application submitted successfully for project '" + selectedProject.getProjectName() + "' (" + selectedFlatType.getDisplayName() + "). Status: PENDING.");
                // DataService.saveApplications(applications); // Save immediately or on exit? Let's save on exit.
            }
        }
    }

    public void viewMyApplication() {
        Applicant applicant = (Applicant) currentUser;
        if (!applicant.hasApplied()) {
            System.out.println("You have not applied for any BTO project yet.");
            return;
        }

        String projectName = applicant.getAppliedProjectName();
        ApplicationStatus status = applicant.getApplicationStatus();
        Project project = findProjectByName(projectName);

        System.out.println("\n--- Your BTO Application ---");
        System.out.println("Project Name: " + projectName);
        if (project != null) {
            System.out.println("Neighborhood: " + project.getNeighborhood());
            // Show applied flat type from application record
            BTOApplication app = findApplicationByApplicantAndProject(applicant.getNric(), projectName);
            if (app != null && app.getFlatTypeApplied() != null) {
                 System.out.println("Flat Type Applied For: " + app.getFlatTypeApplied().getDisplayName());
            }
        } else {
            System.out.println("Project details not found (possibly deleted).");
        }
        System.out.println("Application Status: " + status);
         if (status == ApplicationStatus.BOOKED && applicant.getBookedFlatType() != null) {
             System.out.println("Booked Flat Type: " + applicant.getBookedFlatType().getDisplayName());
         }
    }

    public void requestWithdrawal() {
        Applicant applicant = (Applicant) currentUser;
        if (!applicant.hasApplied() || applicant.getApplicationStatus() == ApplicationStatus.WITHDRAWN || applicant.getApplicationStatus() == ApplicationStatus.UNSUCCESSFUL) {
            System.out.println("You do not have an active application to withdraw.");
            return;
        }

        BTOApplication application = findApplicationByApplicantAndProject(applicant.getNric(), applicant.getAppliedProjectName());
        if (application == null) {
             System.out.println("Error: Could not find your application record.");
             return;
        }

        System.out.println("Current application status: " + application.getStatus());
        System.out.print("Are you sure you want to request withdrawal for project '" + applicant.getAppliedProjectName() + "'? (yes/no): ");
        String confirm = scanner.nextLine().trim().toLowerCase();

        if (confirm.equals("yes")) {
            // In this simplified model, withdrawal is auto-approved as per FAQ clarification
            // Manager approval step is skipped for simplicity here, but spec says Manager approves/rejects.
            // Let's follow the spec: Mark for withdrawal, Manager approves later.
            // For now, let's make it auto-approved for simplicity as per FAQ hint.

            System.out.println("Withdrawal request submitted. Assuming auto-approval for now.");

            // If application was successful/booked, need to revert unit count
            if (application.getStatus() == ApplicationStatus.BOOKED) {
                 Project project = findProjectByName(application.getProjectName());
                 if (project != null && application.getFlatTypeApplied() != null) {
                     FlatTypeDetails details = project.getFlatTypeDetails(application.getFlatTypeApplied());
                     if (details != null) {
                         details.incrementAvailableUnits(); // Put unit back
                         System.out.println("Unit count for " + application.getFlatTypeApplied().getDisplayName() + " in project " + project.getProjectName() + " incremented.");
                     }
                 }
                 applicant.setBookedFlatType(null); // Clear booked flat type
            }

            application.setStatus(ApplicationStatus.WITHDRAWN); // Or set to UNSUCCESSFUL as per FAQ Q2
            applicant.setApplicationStatus(ApplicationStatus.WITHDRAWN); // Update user state
            // applicant.setAppliedProjectName(null); // Allow applying again

            System.out.println("Application withdrawn successfully.");
            // DataService.saveApplications(applications);
            // DataService.saveProjects(projects); // If unit count changed
            // DataService.saveUsers(users); // If user state changed significantly (less likely here)

        } else {
            System.out.println("Withdrawal cancelled.");
        }
    }

    public void submitEnquiry() {
        System.out.println("\n--- Submit Enquiry ---");
        // List projects the user can view (optional, could allow enquiry about any project name)
        List<Project> viewableProjects = getFilteredProjects(true, false); // Show all potentially viewable
        viewAndSelectProject(viewableProjects, "Select Project to Enquire About");
        Project selectedProject = selectProjectFromList(viewableProjects);

        if (selectedProject == null) {
            System.out.print("Or enter the exact Project Name to enquire about: ");
            String projectNameInput = scanner.nextLine().trim();
            selectedProject = findProjectByName(projectNameInput);
            if (selectedProject == null) {
                System.out.println("Project not found.");
                return;
            }
        }

        System.out.print("Enter your enquiry text: ");
        String text = scanner.nextLine().trim();

        if (!text.isEmpty()) {
            Enquiry newEnquiry = new Enquiry(currentUser.getNric(), selectedProject.getProjectName(), text, DataService.getCurrentDate());
            enquiries.add(newEnquiry);
            System.out.println("Enquiry submitted successfully (ID: " + newEnquiry.getEnquiryId() + ").");
            // DataService.saveEnquiries(enquiries);
        } else {
            System.out.println("Enquiry text cannot be empty.");
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
                    i + 1, e.getEnquiryId(), e.getProjectName(), DataService.DATE_FORMAT.format(e.getEnquiryDate()));
            System.out.println("   Enquiry: " + e.getEnquiryText());
            if (e.isReplied()) {
                System.out.printf("   Reply (by %s on %s): %s\n",
                        e.getRepliedByNric(),
                        e.getReplyDate() != null ? DataService.DATE_FORMAT.format(e.getReplyDate()) : "N/A",
                        e.getReplyText());
            } else {
                System.out.println("   Reply: (Pending)");
            }
            System.out.println("--------------------");
        }
    }

    public void editMyEnquiry() {
        System.out.println("\n--- Edit Enquiry ---");
        List<Enquiry> editableEnquiries = enquiries.stream()
                                                .filter(e -> e.getApplicantNric().equals(currentUser.getNric()) && !e.isReplied())
                                                .sorted(Comparator.comparing(Enquiry::getEnquiryDate).reversed())
                                                .collect(Collectors.toList());

        if (editableEnquiries.isEmpty()) {
            System.out.println("You have no enquiries that can be edited (must not be replied to).");
            return;
        }

        System.out.println("Select enquiry to edit:");
         for (int i = 0; i < editableEnquiries.size(); i++) {
            Enquiry e = editableEnquiries.get(i);
            System.out.printf("%d. ID: %s | Project: %s | Text: %s\n",
                    i + 1, e.getEnquiryId(), e.getProjectName(), e.getEnquiryText());
        }
         System.out.print("Enter choice: ");
         try {
             int choice = Integer.parseInt(scanner.nextLine());
             if (choice >= 1 && choice <= editableEnquiries.size()) {
                 Enquiry enquiryToEdit = editableEnquiries.get(choice - 1);
                 System.out.print("Enter new enquiry text: ");
                 String newText = scanner.nextLine().trim();
                 if (!newText.isEmpty()) {
                     enquiryToEdit.setEnquiryText(newText);
                     System.out.println("Enquiry updated successfully.");
                     // DataService.saveEnquiries(enquiries);
                 } else {
                     System.out.println("Enquiry text cannot be empty.");
                 }
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
            System.out.println("You have no enquiries that can be deleted (must not be replied to).");
            return;
        }

        System.out.println("Select enquiry to delete:");
         for (int i = 0; i < deletableEnquiries.size(); i++) {
            Enquiry e = deletableEnquiries.get(i);
            System.out.printf("%d. ID: %s | Project: %s | Text: %s\n",
                    i + 1, e.getEnquiryId(), e.getProjectName(), e.getEnquiryText());
        }
         System.out.print("Enter choice: ");
         try {
             int choice = Integer.parseInt(scanner.nextLine());
             if (choice >= 1 && choice <= deletableEnquiries.size()) {
                 Enquiry enquiryToDelete = deletableEnquiries.get(choice - 1);
                 System.out.print("Are you sure you want to delete enquiry " + enquiryToDelete.getEnquiryId() + "? (yes/no): ");
                 String confirm = scanner.nextLine().trim().toLowerCase();
                 if (confirm.equals("yes")) {
                     enquiries.remove(enquiryToDelete);
                     System.out.println("Enquiry deleted successfully.");
                     // DataService.saveEnquiries(enquiries);
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

class OfficerController extends ApplicantController { // Inherits Applicant actions

    public OfficerController(Map<String, User> users, List<Project> projects, Map<String, BTOApplication> applications, List<Enquiry> enquiries, Map<String, OfficerRegistration> officerRegistrations, User currentUser, Scanner scanner) {
        super(users, projects, applications, enquiries, officerRegistrations, currentUser, scanner);
    }

    // Officer specific actions
    public void registerForProject() {
        HDBOfficer officer = (HDBOfficer) currentUser;
        Date currentDate = DataService.getCurrentDate();

        // 1. Check if already applied for any project as Applicant
        if (officer.hasApplied() && officer.getApplicationStatus() != ApplicationStatus.UNSUCCESSFUL && officer.getApplicationStatus() != ApplicationStatus.WITHDRAWN) {
            System.out.println("Error: Cannot register to handle a project while you have an active BTO application (" + officer.getAppliedProjectName() + ").");
            return;
        }

        // 2. Check if already an approved officer for another project *within the same application period*
        // Find projects the officer is currently approved for
         List<Project> currentlyHandling = projects.stream()
            .filter(p -> p.getApprovedOfficerNrics().contains(officer.getNric()))
            .collect(Collectors.toList());

        // Find projects with pending/approved registrations for this officer
        List<OfficerRegistration> currentRegistrations = officerRegistrations.values().stream()
            .filter(reg -> reg.getOfficerNric().equals(officer.getNric()) &&
                           (reg.getStatus() == OfficerRegistrationStatus.PENDING || reg.getStatus() == OfficerRegistrationStatus.APPROVED))
            .collect(Collectors.toList());


        // List projects available for registration
        System.out.println("\n--- Register to Handle Project ---");
        List<Project> availableProjects = projects.stream()
                .filter(p -> p.getRemainingOfficerSlots() > 0) // Must have slots
                .filter(p -> !p.getApprovedOfficerNrics().contains(officer.getNric())) // Not already approved for this one
                .filter(p -> officerRegistrations.values().stream() // Not already pending for this one
                                .noneMatch(reg -> reg.getOfficerNric().equals(officer.getNric()) &&
                                                reg.getProjectName().equals(p.getProjectName()) &&
                                                reg.getStatus() == OfficerRegistrationStatus.PENDING))
                .filter(p -> { // Check for overlapping application periods with existing commitments
                    Date p_start = p.getApplicationOpeningDate();
                    Date p_end = p.getApplicationClosingDate();

                    // Check against currently handled projects
                    boolean handlingOverlap = currentlyHandling.stream().anyMatch(handled -> {
                        Date h_start = handled.getApplicationOpeningDate();
                        Date h_end = handled.getApplicationClosingDate();
                        // Overlap if p starts before h ends AND p ends after h starts
                        return p_start.before(h_end) && p_end.after(h_start);
                    });

                     // Check against other pending/approved registrations
                    boolean registrationOverlap = currentRegistrations.stream()
                        .filter(reg -> !reg.getProjectName().equals(p.getProjectName())) // Exclude self if checking pending
                        .map(OfficerRegistration::getProjectName) // <-- Get project name string first
                        .map(this::findProjectByName)
                        .filter(Objects::nonNull)
                        .anyMatch(registeredProject -> {
                             Date r_start = registeredProject.getApplicationOpeningDate();
                             Date r_end = registeredProject.getApplicationClosingDate();
                             return p_start.before(r_end) && p_end.after(r_start);
                        });


                    return !handlingOverlap && !registrationOverlap;
                })
                .sorted(Comparator.comparing(Project::getProjectName))
                .collect(Collectors.toList());

        if (availableProjects.isEmpty()) {
            System.out.println("No projects currently available for registration based on eligibility criteria (slots, existing applications/registrations, period overlaps).");
            return;
        }

        viewAndSelectProject(availableProjects, "Select Project to Register For");
        Project selectedProject = selectProjectFromList(availableProjects);

        if (selectedProject != null) {
             // Double check: Cannot register for a project they have ever applied for (even if unsuccessful/withdrawn)
             // This check seems missing in the requirements but is logical. Let's assume the requirement means *active* application.
             // Re-checking requirement: "Cannot apply for the project as an Applicant before and after becoming an HDB Officer of the project"
             // And "Once applied for a BTO project, he/she cannot register to handle the same project"
             // This implies ANY past application disqualifies registration for that specific project.

             boolean everAppliedToSelected = applications.values().stream()
                 .anyMatch(app -> app.getApplicantNric().equals(officer.getNric()) &&
                                  app.getProjectName().equals(selectedProject.getProjectName()));

             if (everAppliedToSelected) {
                 System.out.println("Error: You cannot register for project '" + selectedProject.getProjectName() + "' because you have previously applied for it.");
                 return;
             }


            // Create registration record
            OfficerRegistration newRegistration = new OfficerRegistration(officer.getNric(), selectedProject.getProjectName(), currentDate);
            officerRegistrations.put(newRegistration.getRegistrationId(), newRegistration);
            System.out.println("Registration request submitted for project '" + selectedProject.getProjectName() + "'. Status: PENDING approval by Manager.");
            // DataService.saveOfficerRegistrations(officerRegistrations);
        }
    }

    public void viewRegistrationStatus() {
        HDBOfficer officer = (HDBOfficer) currentUser;
        System.out.println("\n--- Your HDB Officer Registration Status ---");

        List<OfficerRegistration> myRegistrations = officerRegistrations.values().stream()
                .filter(reg -> reg.getOfficerNric().equals(officer.getNric()))
                .sorted(Comparator.comparing(OfficerRegistration::getRegistrationDate).reversed())
                .collect(Collectors.toList());

        if (myRegistrations.isEmpty()) {
            System.out.println("You have no registration requests.");
        } else {
            for (OfficerRegistration reg : myRegistrations) {
                System.out.printf("Project: %s | Status: %s | Date: %s\n",
                        reg.getProjectName(), reg.getStatus(), DataService.DATE_FORMAT.format(reg.getRegistrationDate()));
            }
        }

        // Also show currently handled project if approved
        if (officer.getHandlingProjectName() != null) {
             System.out.println("\nYou are currently the approved HDB Officer for project: " + officer.getHandlingProjectName());
        }
    }

    public void viewHandlingProjectDetails() {
        HDBOfficer officer = (HDBOfficer) currentUser;
        String handlingProjectName = officer.getHandlingProjectName();

        if (handlingProjectName == null) {
            System.out.println("You are not currently handling any project.");
            // Maybe show pending/rejected registrations here? viewRegistrationStatus covers that.
            return;
        }

        Project project = findProjectByName(handlingProjectName);
        if (project == null) {
            System.out.println("Error: Details for your handling project '" + handlingProjectName + "' could not be found.");
            return;
        }

        System.out.println("\n--- Details for Project You Are Handling ---");
        System.out.println("Project Name: " + project.getProjectName());
        System.out.println("Neighborhood: " + project.getNeighborhood());
        System.out.println("Application Period: " + DataService.DATE_FORMAT.format(project.getApplicationOpeningDate()) + " to " + DataService.DATE_FORMAT.format(project.getApplicationClosingDate()));
        System.out.println("Visibility: " + (project.isVisible() ? "On" : "Off"));
        System.out.println("Manager: " + project.getManagerNric());
        System.out.println("Officer Slots: " + project.getApprovedOfficerNrics().size() + " / " + project.getMaxOfficerSlots());
        System.out.println("Approved Officers: " + String.join(", ", project.getApprovedOfficerNrics()));
        System.out.println("Flat Types:");
        project.getFlatTypes().forEach((type, details) ->
                System.out.printf("   - %s: %d / %d units available, Price: $%.2f\n",
                        type.getDisplayName(), details.getAvailableUnits(), details.getTotalUnits(), details.getSellingPrice()));
        System.out.println("------------------------------------------");

        // Officers cannot edit details.
    }

    public void viewAndReplyToEnquiries() {
         HDBOfficer officer = (HDBOfficer) currentUser;
         String handlingProjectName = officer.getHandlingProjectName();

         if (handlingProjectName == null) {
             System.out.println("You need to be handling a project to view and reply to enquiries.");
             return;
         }

         System.out.println("\n--- Enquiries for Project: " + handlingProjectName + " ---");
         List<Enquiry> projectEnquiries = enquiries.stream()
                 .filter(e -> e.getProjectName().equalsIgnoreCase(handlingProjectName))
                 .sorted(Comparator.comparing(Enquiry::getEnquiryDate)) // Show oldest first? Or newest? Let's do newest.
                 .sorted(Comparator.comparing(Enquiry::getEnquiryDate).reversed())
                 .collect(Collectors.toList());

         if (projectEnquiries.isEmpty()) {
             System.out.println("No enquiries found for this project.");
             return;
         }

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
                         i + 1, e.getEnquiryId(), e.getApplicantNric(), DataService.DATE_FORMAT.format(e.getEnquiryDate()));
                 System.out.println("   Enquiry: " + e.getEnquiryText());
             }
             System.out.print("Enter the number of the enquiry to reply to (or 0 to skip): ");
             try {
                 int choice = Integer.parseInt(scanner.nextLine());
                 if (choice >= 1 && choice <= unrepliedEnquiries.size()) {
                     Enquiry enquiryToReply = unrepliedEnquiries.get(choice - 1);
                     System.out.print("Enter your reply: ");
                     String replyText = scanner.nextLine().trim();
                     if (!replyText.isEmpty()) {
                         enquiryToReply.setReply(replyText, currentUser.getNric(), DataService.getCurrentDate());
                         System.out.println("Reply submitted successfully.");
                         // DataService.saveEnquiries(enquiries);
                     } else {
                         System.out.println("Reply cannot be empty.");
                     }
                 } else if (choice != 0) {
                     System.out.println("Invalid choice.");
                 }
             } catch (NumberFormatException e) {
                 System.out.println("Invalid input.");
             }
         }

         System.out.println("\n--- Replied Enquiries ---");
         List<Enquiry> repliedEnquiries = projectEnquiries.stream()
                                                          .filter(Enquiry::isReplied)
                                                          .collect(Collectors.toList());
         if (repliedEnquiries.isEmpty()) {
             System.out.println("(None)");
         } else {
             for (Enquiry e : repliedEnquiries) {
                 System.out.printf("ID: %s | Applicant: %s | Enquiry Date: %s\n",
                         e.getEnquiryId(), e.getApplicantNric(), DataService.DATE_FORMAT.format(e.getEnquiryDate()));
                 System.out.println("   Enquiry: " + e.getEnquiryText());
                 System.out.printf("   Reply (by %s on %s): %s\n",
                         e.getRepliedByNric(),
                         e.getReplyDate() != null ? DataService.DATE_FORMAT.format(e.getReplyDate()) : "N/A",
                         e.getReplyText());
                 System.out.println("--------------------");
             }
         }
    }

    public void manageFlatBooking() {
        HDBOfficer officer = (HDBOfficer) currentUser;
        String handlingProjectName = officer.getHandlingProjectName();

        if (handlingProjectName == null) {
            System.out.println("You need to be handling a project to manage flat bookings.");
            return;
        }

        System.out.println("\n--- Flat Booking Management for Project: " + handlingProjectName + " ---");
        System.out.print("Enter Applicant's NRIC to manage booking: ");
        String applicantNric = scanner.nextLine().trim().toUpperCase();

        if (!DataService.isValidNric(applicantNric)) {
             System.out.println("Invalid NRIC format.");
             return;
        }

        // Retrieve application
        BTOApplication application = findApplicationByApplicantAndProject(applicantNric, handlingProjectName);
        User applicantUser = users.get(applicantNric);

        if (application == null || !(applicantUser instanceof Applicant)) {
            System.out.println("No application found for NRIC " + applicantNric + " in project " + handlingProjectName);
            return;
        }

        Applicant applicant = (Applicant) applicantUser;

        // Check status - must be SUCCESSFUL to proceed to BOOKED
        if (application.getStatus() != ApplicationStatus.SUCCESSFUL) {
            System.out.println("Applicant " + applicantNric + " does not have a SUCCESSFUL application status for this project (Current: " + application.getStatus() + "). Cannot proceed with booking.");
            return;
        }

        // Check if already booked (shouldn't happen if check above works, but good safeguard)
         if (applicant.hasBooked()) {
             System.out.println("Applicant " + applicantNric + " has already booked a flat.");
             return;
         }


        Project project = findProjectByName(handlingProjectName);
        if (project == null) {
             System.out.println("Error: Project details not found.");
             return;
        }

        FlatType appliedFlatType = application.getFlatTypeApplied();
        if (appliedFlatType == null) {
             System.out.println("Error: Application record does not have a flat type specified.");
             // This might happen if Manager approved without specifying? Design flaw?
             // Let's assume Manager approval implies the applied type is confirmed.
             // Or maybe the officer confirms the type here?
             // Requirement: "Update applicant’s profile with the type of flat (2-Room or 3-Room) chosen under a project"
             // This implies the type might not be fixed until booking. Let's re-read application logic.
             // Application logic *does* select a type. So it should be there. Let's treat null as error.
             return;
        }

        FlatTypeDetails details = project.getFlatTypeDetails(appliedFlatType);
        if (details == null || details.getAvailableUnits() <= 0) {
            System.out.println("Error: No available units for the applied flat type (" + appliedFlatType.getDisplayName() + ") in project " + handlingProjectName + ".");
            // This suggests an issue with Manager approval logic or unit tracking.
            return;
        }

        System.out.println("\nApplicant Details:");
        System.out.println("Name: " + applicant.getName());
        System.out.println("NRIC: " + applicant.getNric());
        System.out.println("Age: " + applicant.getAge());
        System.out.println("Marital Status: " + applicant.getMaritalStatus());
        System.out.println("Project: " + application.getProjectName());
        System.out.println("Applied Flat Type: " + appliedFlatType.getDisplayName());
        System.out.println("Current Status: " + application.getStatus());
        System.out.println("Available Units for " + appliedFlatType.getDisplayName() + ": " + details.getAvailableUnits());

        System.out.print("\nConfirm booking for this applicant? (yes/no): ");
        String confirm = scanner.nextLine().trim().toLowerCase();

        if (confirm.equals("yes")) {
            // 1. Update application status
            application.setStatus(ApplicationStatus.BOOKED);

            // 2. Update applicant profile (user object)
            applicant.setApplicationStatus(ApplicationStatus.BOOKED);
            applicant.setBookedFlatType(appliedFlatType); // Set the booked type

            // 3. Update project unit count
            details.decrementAvailableUnits();

            System.out.println("Booking confirmed successfully!");
            System.out.println("Applicant status updated to BOOKED.");
            System.out.println("Remaining units for " + appliedFlatType.getDisplayName() + ": " + details.getAvailableUnits());

            // 4. Generate Receipt (display on console)
            generateBookingReceipt(applicant, application, project);

            // Save changes
            // DataService.saveApplications(applications);
            // DataService.saveProjects(projects);
            // DataService.saveUsers(users); // Applicant profile updated

        } else {
            System.out.println("Booking cancelled.");
        }
    }

    public void generateBookingReceipt(Applicant applicant, BTOApplication application, Project project) {
        System.out.println("\n--- BTO Booking Receipt ---");
        System.out.println("------------------------------------------");
        System.out.println("Applicant Details:");
        System.out.println("  Name:          " + applicant.getName());
        System.out.println("  NRIC:          " + applicant.getNric());
        System.out.println("  Age:           " + applicant.getAge());
        System.out.println("  Marital Status:" + applicant.getMaritalStatus());
        System.out.println("\nBooking Details:");
        System.out.println("  Project Name:  " + project.getProjectName());
        System.out.println("  Neighborhood:  " + project.getNeighborhood());
        System.out.println("  Booked Flat:   " + application.getFlatTypeApplied().getDisplayName());
        FlatTypeDetails details = project.getFlatTypeDetails(application.getFlatTypeApplied());
        if (details != null) {
             System.out.printf("  Selling Price: $%.2f\n", details.getSellingPrice());
        }
        System.out.println("  Booking Status:" + application.getStatus());
        System.out.println("  Booking Date:  " + DataService.DATE_FORMAT.format(DataService.getCurrentDate())); // Use current date as booking date
        System.out.println("------------------------------------------");
        System.out.println("Generated by HDB Officer: " + currentUser.getNric());
        System.out.println("------------------------------------------");
    }

     // Overriding applyForProject to add officer-specific checks if needed
     @Override
     public void applyForProject() {
         HDBOfficer officer = (HDBOfficer) currentUser;

         // Check if trying to apply for the project they are handling
         if (officer.getHandlingProjectName() != null) {
             // Find the project they might select
             // This check is better placed *after* project selection in the superclass method
             // Let's modify the superclass method to include this check. Done.
         }

         // Check if trying to apply for a project they have a pending registration for
          boolean hasPendingReg = officerRegistrations.values().stream()
             .anyMatch(reg -> reg.getOfficerNric().equals(officer.getNric()) &&
                              reg.getStatus() == OfficerRegistrationStatus.PENDING);
          if (hasPendingReg) {
               // Also better checked after project selection. Done in superclass method.
          }


         // Call the original applicant logic
         super.applyForProject();
     }
}

class ManagerController extends BaseController { // Managers don't inherit Applicant/Officer actions

    public ManagerController(Map<String, User> users, List<Project> projects, Map<String, BTOApplication> applications, List<Enquiry> enquiries, Map<String, OfficerRegistration> officerRegistrations, User currentUser, Scanner scanner) {
        super(users, projects, applications, enquiries, officerRegistrations, currentUser, scanner);
    }

    // Manager specific actions

    public void createProject() {
        HDBManager manager = (HDBManager) currentUser;
        Date currentDate = DataService.getCurrentDate();

        // Check if manager is already handling an active project
        boolean handlingActiveProject = projects.stream()
                .filter(p -> p.getManagerNric().equals(manager.getNric()))
                .anyMatch(p -> p.isApplicationPeriodActive(currentDate) && p.isVisible()); // Definition of Active

        if (handlingActiveProject) {
            System.out.println("Error: You are already managing an active project during its application period. You cannot create a new one until the current one's period ends or visibility is turned off.");
            return;
        }


        System.out.println("\n--- Create New BTO Project ---");
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

        System.out.print("Enter Neighborhood: ");
        String neighborhood = scanner.nextLine().trim();

        Map<FlatType, FlatTypeDetails> flatTypes = new HashMap<>();
        // Get details for 2-Room
        System.out.println("--- 2-Room Flat Details ---");
        int units2Room = getIntInput("Enter total number of 2-Room units: ", 0, Integer.MAX_VALUE);
        double price2Room = getDoubleInput("Enter selling price for 2-Room units: ", 0, Double.MAX_VALUE);
        if (units2Room > 0) {
            flatTypes.put(FlatType.TWO_ROOM, new FlatTypeDetails(units2Room, units2Room, price2Room));
        }

        // Get details for 3-Room
        System.out.println("--- 3-Room Flat Details ---");
        int units3Room = getIntInput("Enter total number of 3-Room units: ", 0, Integer.MAX_VALUE);
        double price3Room = getDoubleInput("Enter selling price for 3-Room units: ", 0, Double.MAX_VALUE);
        if (units3Room > 0) {
            flatTypes.put(FlatType.THREE_ROOM, new FlatTypeDetails(units3Room, units3Room, price3Room));
        }

        if (flatTypes.isEmpty()) {
            System.out.println("Error: Project must have at least one type of flat.");
            return;
        }

        Date openingDate = getDateInput("Enter Application Opening Date (yyyy-MM-dd): ");
        Date closingDate = getDateInput("Enter Application Closing Date (yyyy-MM-dd): ");

        if (openingDate == null || closingDate == null || closingDate.before(openingDate)) {
            System.out.println("Invalid date range.");
            return;
        }

        int maxOfficers = getIntInput("Enter Maximum HDB Officer Slots (1-10): ", 1, 10);

        // Create project
        Project newProject = new Project(projectName, neighborhood, flatTypes, openingDate, closingDate,
                                         currentUser.getNric(), maxOfficers, new ArrayList<>(), false); // Default visibility off
        projects.add(newProject);

        System.out.println("Project '" + projectName + "' created successfully. Visibility is currently OFF.");
        // DataService.saveProjects(projects);
    }

    public void editProject() {
        System.out.println("\n--- Edit BTO Project ---");
        List<Project> myProjects = projects.stream()
                                           .filter(p -> p.getManagerNric().equals(currentUser.getNric()))
                                           .sorted(Comparator.comparing(Project::getProjectName))
                                           .collect(Collectors.toList());

        if (myProjects.isEmpty()) {
            System.out.println("You are not managing any projects.");
            return;
        }

        viewAndSelectProject(myProjects, "Select Project to Edit");
        Project projectToEdit = selectProjectFromList(myProjects);

        if (projectToEdit != null) {
            System.out.println("Editing Project: " + projectToEdit.getProjectName());
            System.out.println("Leave blank to keep current value.");

            System.out.print("Enter new Neighborhood [" + projectToEdit.getNeighborhood() + "]: ");
            String newNeighborhood = scanner.nextLine().trim();
            if (!newNeighborhood.isEmpty()) projectToEdit.setNeighborhood(newNeighborhood);

            // Editing flat types (complex - allow changing units/price? add/remove types?)
            // Simple approach: Edit existing unit counts and prices.
            Map<FlatType, FlatTypeDetails> currentFlatTypes = projectToEdit.getFlatTypes();
            Map<FlatType, FlatTypeDetails> newFlatTypes = new HashMap<>(currentFlatTypes); // Edit a copy

            for (FlatType type : FlatType.values()) {
                 FlatTypeDetails currentDetails = newFlatTypes.get(type);
                 System.out.println("--- Edit " + type.getDisplayName() + " ---");
                 // Editing total units after launch is tricky due to available units. Disallow for now?
                 // Let's allow editing price only for simplicity.
                 // int newTotal = getIntInput("Enter new total units [" + currentTotal + "] (cannot be less than booked): ", 0, Integer.MAX_VALUE);
                 double currentPrice = (currentDetails != null) ? currentDetails.getSellingPrice() : 0.0;
                 double newPrice = getDoubleInput("Enter new selling price [" + currentPrice + "]: ", 0, Double.MAX_VALUE);

                 if (currentDetails != null) { // Only edit price if type exists
                     if (newPrice != currentPrice && newPrice >= 0) { // Check if price actually changed
                         // Create new details object to avoid modifying original if edit is cancelled
                         newFlatTypes.put(type, new FlatTypeDetails(currentDetails.getTotalUnits(), currentDetails.getAvailableUnits(), newPrice));
                     }
                 } else {
                     // Add new flat type? Too complex for basic edit.
                 }
            }
             projectToEdit.setFlatTypes(newFlatTypes); // Update with potentially modified prices


            // Edit dates (careful if application period active/passed)
            System.out.println("Current Opening Date: " + DataService.DATE_FORMAT.format(projectToEdit.getApplicationOpeningDate()));
            Date newOpeningDate = getDateInput("Enter new Opening Date (yyyy-MM-dd) or leave blank: ");
            if (newOpeningDate != null) projectToEdit.setApplicationOpeningDate(newOpeningDate);

            System.out.println("Current Closing Date: " + DataService.DATE_FORMAT.format(projectToEdit.getApplicationClosingDate()));
            Date newClosingDate = getDateInput("Enter new Closing Date (yyyy-MM-dd) or leave blank: ");
             if (newClosingDate != null && (projectToEdit.getApplicationOpeningDate() == null || !newClosingDate.before(projectToEdit.getApplicationOpeningDate()))) {
                 projectToEdit.setApplicationClosingDate(newClosingDate);
             } else if (newClosingDate != null) {
                 System.out.println("Closing date cannot be before opening date. Not updated.");
             }


            // Edit officer slots (careful not to go below current approved count)
            int currentMaxSlots = projectToEdit.getMaxOfficerSlots();
            int currentApprovedCount = projectToEdit.getApprovedOfficerNrics().size();
            int newMaxSlots = getIntInput("Enter new Max Officer Slots (current: " + currentMaxSlots + ", min: " + currentApprovedCount + ", max: 10): ", currentApprovedCount, 10);
            if (newMaxSlots != currentMaxSlots) {
                 projectToEdit.setMaxOfficerSlots(newMaxSlots);
            }


            System.out.println("Project details updated successfully.");
            // DataService.saveProjects(projects);
        }
    }

    public void deleteProject() {
         System.out.println("\n--- Delete BTO Project ---");
        List<Project> myProjects = projects.stream()
                                           .filter(p -> p.getManagerNric().equals(currentUser.getNric()))
                                           .sorted(Comparator.comparing(Project::getProjectName))
                                           .collect(Collectors.toList());

        if (myProjects.isEmpty()) {
            System.out.println("You are not managing any projects.");
            return;
        }

        viewAndSelectProject(myProjects, "Select Project to Delete");
        Project projectToDelete = selectProjectFromList(myProjects);

        if (projectToDelete != null) {
            // Add checks: Cannot delete if there are pending/successful/booked applications? Or active officers?
            // For simplicity, let's allow deletion but warn.
            boolean hasApplications = applications.values().stream().anyMatch(app -> app.getProjectName().equals(projectToDelete.getProjectName()));
            boolean hasOfficers = !projectToDelete.getApprovedOfficerNrics().isEmpty();
            boolean hasRegistrations = officerRegistrations.values().stream().anyMatch(reg -> reg.getProjectName().equals(projectToDelete.getProjectName()));

            if (hasApplications || hasOfficers || hasRegistrations) {
                System.out.println("Warning: This project has associated applications, officers, or registrations.");
            }
            System.out.print("Are you sure you want to permanently delete project '" + projectToDelete.getProjectName() + "'? (yes/no): ");
            String confirm = scanner.nextLine().trim().toLowerCase();

            if (confirm.equals("yes")) {
                projects.remove(projectToDelete);
                // Optionally: Clean up related applications, registrations, enquiries? Or leave them orphaned?
                // Let's leave them for now.
                System.out.println("Project deleted successfully.");
                // DataService.saveProjects(projects);
            } else {
                System.out.println("Deletion cancelled.");
            }
        }
    }

    public void toggleProjectVisibility() {
        System.out.println("\n--- Toggle Project Visibility ---");
        List<Project> myProjects = projects.stream()
                                           .filter(p -> p.getManagerNric().equals(currentUser.getNric()))
                                           .sorted(Comparator.comparing(Project::getProjectName))
                                           .collect(Collectors.toList());

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
            // DataService.saveProjects(projects);
        }
    }

    public void viewAllProjects() {
        System.out.println("\n--- View All Projects ---");
        // Managers see all projects, regardless of visibility or filters (filters apply optionally)
        List<Project> displayProjects = getFilteredProjects(false, false); // Ignore visibility, ignore eligibility
        viewAndSelectProject(displayProjects, "All BTO Projects");
    }

    public void viewMyProjects() {
        System.out.println("\n--- View My Projects ---");
        List<Project> myProjects = projects.stream()
                                           .filter(p -> p.getManagerNric().equals(currentUser.getNric()))
                                           // Apply user's saved filters
                                           .filter(p -> filterLocation == null || p.getNeighborhood().equalsIgnoreCase(filterLocation))
                                           .filter(p -> filterFlatType == null || p.getFlatTypes().containsKey(filterFlatType))
                                           .sorted(Comparator.comparing(Project::getProjectName))
                                           .collect(Collectors.toList());
        viewAndSelectProject(myProjects, "Projects Managed By You");
    }

    public void manageOfficerRegistrations() {
        System.out.println("\n--- Manage HDB Officer Registrations ---");
        List<Project> myProjects = projects.stream()
                                           .filter(p -> p.getManagerNric().equals(currentUser.getNric()))
                                           .sorted(Comparator.comparing(Project::getProjectName))
                                           .collect(Collectors.toList());

        if (myProjects.isEmpty()) {
            System.out.println("You are not managing any projects.");
            return;
        }

        System.out.println("Select project to manage registrations for:");
        viewAndSelectProject(myProjects, "Select Project");
        Project selectedProject = selectProjectFromList(myProjects);

        if (selectedProject != null) {
            System.out.println("\n--- Registrations for Project: " + selectedProject.getProjectName() + " ---");
            List<OfficerRegistration> pendingRegistrations = officerRegistrations.values().stream()
                    .filter(reg -> reg.getProjectName().equals(selectedProject.getProjectName()) && reg.getStatus() == OfficerRegistrationStatus.PENDING)
                    .collect(Collectors.toList());

            List<OfficerRegistration> approvedRegistrations = officerRegistrations.values().stream()
                    .filter(reg -> reg.getProjectName().equals(selectedProject.getProjectName()) && reg.getStatus() == OfficerRegistrationStatus.APPROVED)
                    .collect(Collectors.toList());

             List<OfficerRegistration> rejectedRegistrations = officerRegistrations.values().stream()
                    .filter(reg -> reg.getProjectName().equals(selectedProject.getProjectName()) && reg.getStatus() == OfficerRegistrationStatus.REJECTED)
                    .collect(Collectors.toList());


            System.out.println("--- Pending Registrations ---");
            if (pendingRegistrations.isEmpty()) {
                System.out.println("(None)");
            } else {
                for (int i = 0; i < pendingRegistrations.size(); i++) {
                    OfficerRegistration reg = pendingRegistrations.get(i);
                    User officerUser = users.get(reg.getOfficerNric());
                    System.out.printf("%d. NRIC: %s | Name: %s | Date: %s\n",
                            i + 1, reg.getOfficerNric(), officerUser != null ? officerUser.getName() : "N/A", DataService.DATE_FORMAT.format(reg.getRegistrationDate()));
                }
                System.out.print("Enter number to Approve/Reject (or 0 to skip): ");
                 try {
                     int choice = Integer.parseInt(scanner.nextLine());
                     if (choice >= 1 && choice <= pendingRegistrations.size()) {
                         OfficerRegistration regToProcess = pendingRegistrations.get(choice - 1);
                         System.out.print("Approve or Reject? (A/R): ");
                         String action = scanner.nextLine().trim().toUpperCase();

                         if (action.equals("A")) {
                             // Check slots
                             if (selectedProject.getRemainingOfficerSlots() > 0) {
                                 regToProcess.setStatus(OfficerRegistrationStatus.APPROVED);
                                 selectedProject.addApprovedOfficer(regToProcess.getOfficerNric());
                                 // Update officer's handling project
                                 User officerUser = users.get(regToProcess.getOfficerNric());
                                 if (officerUser instanceof HDBOfficer) {
                                     ((HDBOfficer) officerUser).setHandlingProjectName(selectedProject.getProjectName());
                                 }
                                 System.out.println("Registration Approved. Officer added to project.");
                                 // DataService.saveOfficerRegistrations(officerRegistrations);
                                 // DataService.saveProjects(projects);
                                 // DataService.saveUsers(users);
                             } else {
                                 System.out.println("Cannot approve. No remaining officer slots for this project.");
                             }
                         } else if (action.equals("R")) {
                             regToProcess.setStatus(OfficerRegistrationStatus.REJECTED);
                             System.out.println("Registration Rejected.");
                             // DataService.saveOfficerRegistrations(officerRegistrations);
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

             System.out.println("\n--- Approved Registrations ---");
             if (approvedRegistrations.isEmpty()) System.out.println("(None)");
             else approvedRegistrations.forEach(reg -> System.out.println("- NRIC: " + reg.getOfficerNric() + " | Date: " + DataService.DATE_FORMAT.format(reg.getRegistrationDate())));

             System.out.println("\n--- Rejected Registrations ---");
              if (rejectedRegistrations.isEmpty()) System.out.println("(None)");
             else rejectedRegistrations.forEach(reg -> System.out.println("- NRIC: " + reg.getOfficerNric() + " | Date: " + DataService.DATE_FORMAT.format(reg.getRegistrationDate())));
        }
    }

    public void manageApplications() {
        System.out.println("\n--- Manage BTO Applications ---");
        // List projects managed by this manager
         List<Project> myProjects = projects.stream()
                                           .filter(p -> p.getManagerNric().equals(currentUser.getNric()))
                                           .sorted(Comparator.comparing(Project::getProjectName))
                                           .collect(Collectors.toList());

        if (myProjects.isEmpty()) {
            System.out.println("You are not managing any projects.");
            return;
        }

        System.out.println("Select project to manage applications for:");
        viewAndSelectProject(myProjects, "Select Project");
        Project selectedProject = selectProjectFromList(myProjects);

        if (selectedProject != null) {
            System.out.println("\n--- Applications for Project: " + selectedProject.getProjectName() + " ---");
            List<BTOApplication> projectApplications = applications.values().stream()
                    .filter(app -> app.getProjectName().equals(selectedProject.getProjectName()))
                    .sorted(Comparator.comparing(BTOApplication::getApplicationDate))
                    .collect(Collectors.toList());

            if (projectApplications.isEmpty()) {
                System.out.println("No applications found for this project.");
                return;
            }

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
                     System.out.printf("%d. NRIC: %s | Name: %s | Type: %s | Date: %s\n",
                             i + 1, app.getApplicantNric(),
                             applicant != null ? applicant.getName() : "N/A",
                             app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A",
                             DataService.DATE_FORMAT.format(app.getApplicationDate()));
                 }
                 System.out.print("Enter number to Approve/Reject (or 0 to skip): ");
                 try {
                     int choice = Integer.parseInt(scanner.nextLine());
                     if (choice >= 1 && choice <= pendingApps.size()) {
                         BTOApplication appToProcess = pendingApps.get(choice - 1);
                         User applicantUser = users.get(appToProcess.getApplicantNric());
                         Applicant applicant = (applicantUser instanceof Applicant) ? (Applicant) applicantUser : null;

                         if (applicant == null) {
                             System.out.println("Error: Applicant data not found.");
                             return;
                         }

                         System.out.print("Approve or Reject? (A/R): ");
                         String action = scanner.nextLine().trim().toUpperCase();

                         if (action.equals("A")) {
                             // Check flat availability for the applied type
                             FlatType appliedType = appToProcess.getFlatTypeApplied();
                             if (appliedType == null) {
                                 System.out.println("Error: Application has no specified flat type. Cannot approve.");
                                 return; // Should not happen if application logic is correct
                             }
                             FlatTypeDetails details = selectedProject.getFlatTypeDetails(appliedType);
                             // Approval doesn't decrement count here, booking does. Manager just checks if *theoretically* possible.
                             // The spec says "approval is limited to the supply of the flats".
                             // This implies the manager *should* consider the current available count vs other successful apps.
                             // Let's count successful (but not booked) apps for this type.
                             long successfulCount = applications.values().stream()
                                 .filter(a -> a.getProjectName().equals(selectedProject.getProjectName()) &&
                                              a.getFlatTypeApplied() == appliedType &&
                                              a.getStatus() == ApplicationStatus.SUCCESSFUL)
                                 .count();

                             if (details != null && details.getAvailableUnits() > 0 && successfulCount < details.getTotalUnits()) {
                                 // We check availableUnits > 0 for immediate check, and successfulCount < totalUnits as the theoretical limit check
                                 appToProcess.setStatus(ApplicationStatus.SUCCESSFUL);
                                 applicant.setApplicationStatus(ApplicationStatus.SUCCESSFUL); // Update user state
                                 System.out.println("Application Approved (Status: SUCCESSFUL).");
                                 // DataService.saveApplications(applications);
                                 // DataService.saveUsers(users);
                             } else {
                                 System.out.println("Cannot approve. No available units or supply limit reached for " + appliedType.getDisplayName() + ".");
                                 // Optionally, auto-reject? Or leave pending? Let's leave pending.
                             }
                         } else if (action.equals("R")) {
                             appToProcess.setStatus(ApplicationStatus.UNSUCCESSFUL);
                             applicant.setApplicationStatus(ApplicationStatus.UNSUCCESSFUL); // Update user state
                             // applicant.setAppliedProjectName(null); // Allow applying again
                             System.out.println("Application Rejected (Status: UNSUCCESSFUL).");
                             // DataService.saveApplications(applications);
                             // DataService.saveUsers(users);
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
                 .filter(app -> app.getStatus() != ApplicationStatus.PENDING)
                 .forEach(app -> {
                     User applicant = users.get(app.getApplicantNric());
                     System.out.printf("- NRIC: %s | Name: %s | Type: %s | Status: %s\n",
                             app.getApplicantNric(),
                             applicant != null ? applicant.getName() : "N/A",
                             app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A",
                             app.getStatus());
                 });
        }
    }

     public void manageWithdrawals() {
         // As per FAQ, withdrawal is often auto-approved.
         // If strict manager approval is needed:
         // 1. Applicant requests withdrawal -> Status changes to PENDING_WITHDRAWAL (new status?) or stays same but flags internally.
         // 2. Manager views pending withdrawals for their projects.
         // 3. Manager approves/rejects.
         // 4. If approved: Status -> WITHDRAWN/UNSUCCESSFUL. If booked, increment unit count. Update user state.
         // 5. If rejected: Status reverts to previous state.
         // Let's stick to the simplified auto-approval based on FAQ for now. This method might not be needed.
         System.out.println("Withdrawal management: Currently handled automatically upon applicant request (as per simplified interpretation).");
     }


    public void generateApplicantReport() {
        System.out.println("\n--- Generate Applicant Report ---");
        // Filters: Project, Flat Type, Marital Status, Age Range?

        // 1. Select Project (optional, can report across all managed projects or all projects)
        System.out.print("Filter by specific project? (Enter project name or leave blank for all managed): ");
        String filterProjectName = scanner.nextLine().trim();
        Project filterProject = null;
        List<Project> projectsToReport = new ArrayList<>();
        if (!filterProjectName.isEmpty()) {
            filterProject = findProjectByName(filterProjectName);
            if (filterProject != null && filterProject.getManagerNric().equals(currentUser.getNric())) {
                projectsToReport.add(filterProject);
                 System.out.println("Filtering report for project: " + filterProjectName);
            } else if (filterProject != null) {
                 System.out.println("You do not manage project '" + filterProjectName + "'. Reporting on all your projects.");
                 filterProject = null; // Reset filter
                 projectsToReport = projects.stream()
                                           .filter(p -> p.getManagerNric().equals(currentUser.getNric()))
                                           .collect(Collectors.toList());
            } else {
                 System.out.println("Project '" + filterProjectName + "' not found. Reporting on all your projects.");
                 projectsToReport = projects.stream()
                                           .filter(p -> p.getManagerNric().equals(currentUser.getNric()))
                                           .collect(Collectors.toList());
            }
        } else {
             System.out.println("Reporting across all projects you manage.");
             projectsToReport = projects.stream()
                                       .filter(p -> p.getManagerNric().equals(currentUser.getNric()))
                                       .collect(Collectors.toList());
        }
         final List<String> projectNamesToInclude = projectsToReport.stream().map(Project::getProjectName).collect(Collectors.toList());


        // 2. Filter by Flat Type
        System.out.print("Filter by Flat Type (TWO_ROOM, THREE_ROOM, or leave blank for all): ");
        String typeStr = scanner.nextLine().trim().toUpperCase();
        FlatType filterReportFlatType = null;
        try {
            filterReportFlatType = typeStr.isEmpty() ? null : FlatType.valueOf(typeStr);
             if(filterReportFlatType != null) System.out.println("Filtering report for flat type: " + filterReportFlatType);
        } catch (IllegalArgumentException e) {
            System.out.println("Invalid flat type. Reporting for all types.");
        }

        // 3. Filter by Marital Status
        System.out.print("Filter by Marital Status (SINGLE, MARRIED, or leave blank for all): ");
        String maritalStr = scanner.nextLine().trim().toUpperCase();
        MaritalStatus filterMaritalStatus = null;
        try {
            filterMaritalStatus = maritalStr.isEmpty() ? null : MaritalStatus.valueOf(maritalStr);
             if(filterMaritalStatus != null) System.out.println("Filtering report for marital status: " + filterMaritalStatus);
        } catch (IllegalArgumentException e) {
            System.out.println("Invalid marital status. Reporting for all statuses.");
        }

        // 4. Filter by Age Range
        int minAge = getIntInput("Filter by Minimum Age (or 0 for no minimum): ", 0, 120);
        int maxAge = getIntInput("Filter by Maximum Age (or 0 for no maximum): ", 0, 120);
         if (minAge > 0 || maxAge > 0) System.out.println("Filtering report for age range: " + (minAge > 0 ? minAge : "Any") + " to " + (maxAge > 0 ? maxAge : "Any"));


        // Generate Report (focus on BOOKED status as per requirement)
        System.out.println("\n--- Report: Applicants with Flat Bookings ---");
        System.out.printf("%-15s | %-10s | %-8s | %-12s | %-20s | %-10s\n",
                          "Applicant NRIC", "Name", "Age", "Marital", "Project Name", "Flat Type");
        System.out.println(String.join("", Collections.nCopies(80, "-"))); // Separator line

        final FlatType finalFilterReportFlatType = filterReportFlatType; // Need final for lambda
        final MaritalStatus finalFilterMaritalStatus = filterMaritalStatus;
        final int finalMinAge = minAge;
        final int finalMaxAge = maxAge;

        long count = applications.values().stream()
            .filter(app -> app.getStatus() == ApplicationStatus.BOOKED)
            .filter(app -> projectNamesToInclude.contains(app.getProjectName())) // Filter by selected project(s)
            .filter(app -> finalFilterReportFlatType == null || app.getFlatTypeApplied() == finalFilterReportFlatType) // Filter by flat type
            .map(app -> users.get(app.getApplicantNric())) // Get the User object
            .filter(Objects::nonNull) // Ensure user exists
            .filter(user -> finalFilterMaritalStatus == null || user.getMaritalStatus() == finalFilterMaritalStatus) // Filter by marital status
            .filter(user -> finalMinAge <= 0 || user.getAge() >= finalMinAge) // Filter by min age
            .filter(user -> finalMaxAge <= 0 || user.getAge() <= finalMaxAge) // Filter by max age
            .peek(user -> { // Use peek to perform action (print) without terminating stream
                BTOApplication app = applications.values().stream() // Find the corresponding application again
                                    .filter(a -> a.getApplicantNric().equals(user.getNric()) && a.getStatus() == ApplicationStatus.BOOKED)
                                    .findFirst().orElse(null);
                if (app != null) {
                    System.out.printf("%-15s | %-10s | %-8d | %-12s | %-20s | %-10s\n",
                                      user.getNric(), user.getName(), user.getAge(), user.getMaritalStatus(),
                                      app.getProjectName(), app.getFlatTypeApplied() != null ? app.getFlatTypeApplied().getDisplayName() : "N/A");
                }
            })
            .count(); // Count the matching records

        System.out.println(String.join("", Collections.nCopies(80, "-")));
        System.out.println("Total matching booked applicants: " + count);
        System.out.println("--- End of Report ---");
    }

    public void viewAllEnquiries() {
        System.out.println("\n--- View Enquiries for ALL Projects ---");
         if (enquiries.isEmpty()) {
            System.out.println("No enquiries found in the system.");
            return;
        }

        // Sort by project then date?
        enquiries.stream()
                 .sorted(Comparator.comparing(Enquiry::getProjectName).thenComparing(Enquiry::getEnquiryDate).reversed())
                 .forEach(e -> {
                     System.out.printf("ID: %s | Project: %s | Applicant: %s | Date: %s\n",
                             e.getEnquiryId(), e.getProjectName(), e.getApplicantNric(), DataService.DATE_FORMAT.format(e.getEnquiryDate()));
                     System.out.println("   Enquiry: " + e.getEnquiryText());
                     if (e.isReplied()) {
                         System.out.printf("   Reply (by %s on %s): %s\n",
                                 e.getRepliedByNric(),
                                 e.getReplyDate() != null ? DataService.DATE_FORMAT.format(e.getReplyDate()) : "N/A",
                                 e.getReplyText());
                     } else {
                         System.out.println("   Reply: (Pending)");
                     }
                     System.out.println("--------------------");
                 });
    }

    public void viewAndReplyToManagedEnquiries() {
        System.out.println("\n--- View/Reply Enquiries for Your Projects ---");
        List<String> myManagedProjectNames = projects.stream() // New declaration (List<String>) and name
                                           .filter(p -> p.getManagerNric().equals(currentUser.getNric()))
                                           .map(Project::getProjectName)
                                           .collect(Collectors.toList());

        if (myManagedProjectNames.isEmpty()) {
            System.out.println("You are not managing any projects.");
            return;
        }

        List<Enquiry> managedEnquiries = enquiries.stream()
                 .filter(e -> myManagedProjectNames.contains(e.getProjectName()))
                 .sorted(Comparator.comparing(Enquiry::getProjectName).thenComparing(Enquiry::getEnquiryDate).reversed())
                 .collect(Collectors.toList());

         if (managedEnquiries.isEmpty()) {
             System.out.println("No enquiries found for the projects you manage.");
             return;
         }

         List<Enquiry> unrepliedEnquiries = managedEnquiries.stream()
                                                            .filter(e -> !e.isReplied())
                                                            .collect(Collectors.toList());

         System.out.println("--- Unreplied Enquiries (Managed Projects) ---");
         if (unrepliedEnquiries.isEmpty()) {
             System.out.println("(None)");
         } else {
             for (int i = 0; i < unrepliedEnquiries.size(); i++) {
                 Enquiry e = unrepliedEnquiries.get(i);
                 System.out.printf("%d. ID: %s | Project: %s | Applicant: %s | Date: %s\n",
                         i + 1, e.getEnquiryId(), e.getProjectName(), e.getApplicantNric(), DataService.DATE_FORMAT.format(e.getEnquiryDate()));
                 System.out.println("   Enquiry: " + e.getEnquiryText());
             }
             System.out.print("Enter the number of the enquiry to reply to (or 0 to skip): ");
             try {
                 int choice = Integer.parseInt(scanner.nextLine());
                 if (choice >= 1 && choice <= unrepliedEnquiries.size()) {
                     Enquiry enquiryToReply = unrepliedEnquiries.get(choice - 1);
                     System.out.print("Enter your reply: ");
                     String replyText = scanner.nextLine().trim();
                     if (!replyText.isEmpty()) {
                         enquiryToReply.setReply(replyText, currentUser.getNric(), DataService.getCurrentDate());
                         System.out.println("Reply submitted successfully.");
                         // DataService.saveEnquiries(enquiries);
                     } else {
                         System.out.println("Reply cannot be empty.");
                     }
                 } else if (choice != 0) {
                     System.out.println("Invalid choice.");
                 }
             } catch (NumberFormatException e) {
                 System.out.println("Invalid input.");
             }
         }

         System.out.println("\n--- Replied Enquiries (Managed Projects) ---");
         List<Enquiry> repliedEnquiries = managedEnquiries.stream()
                                                          .filter(Enquiry::isReplied)
                                                          .collect(Collectors.toList());
         if (repliedEnquiries.isEmpty()) {
             System.out.println("(None)");
         } else {
             for (Enquiry e : repliedEnquiries) {
                  System.out.printf("ID: %s | Project: %s | Applicant: %s | Date: %s\n",
                         e.getEnquiryId(), e.getProjectName(), e.getApplicantNric(), DataService.DATE_FORMAT.format(e.getEnquiryDate()));
                 System.out.println("   Enquiry: " + e.getEnquiryText());
                 System.out.printf("   Reply (by %s on %s): %s\n",
                         e.getRepliedByNric(),
                         e.getReplyDate() != null ? DataService.DATE_FORMAT.format(e.getReplyDate()) : "N/A",
                         e.getReplyText());
                 System.out.println("--------------------");
             }
         }
    }


    // --- Helper methods for input ---
    private int getIntInput(String prompt, int min, int max) {
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
                System.out.println("Invalid input. Please enter a number.");
            }
        }
        return value;
    }

     private double getDoubleInput(String prompt, double min, double max) {
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

     private Date getDateInput(String prompt) {
        Date date = null;
        while (true) {
            System.out.print(prompt + " ");
            String input = scanner.nextLine().trim();
             if (input.isEmpty() && prompt.contains("or leave blank")) { // Allow blank input for optional dates
                 return null;
             }
            try {
                // Set lenient to false to enforce strict date format
                DataService.DATE_FORMAT.setLenient(false);
                date = DataService.DATE_FORMAT.parse(input);
                break; // Valid date parsed
            } catch (ParseException e) {
                System.out.println("Invalid date format. Please use yyyy-MM-dd.");
            }
        }
        return date;
    }
}


// ==================
// Views (Handle CLI Display and Input Gathering)
// ==================

// --- Base View ---
abstract class BaseView {
    protected Scanner scanner;
    protected User currentUser;
    protected BaseController controller; // Reference to the controller for actions

    public BaseView(Scanner scanner, User currentUser, BaseController controller) {
        this.scanner = scanner;
        this.currentUser = currentUser;
        this.controller = controller;
    }

    public abstract void displayMenu();

    protected int getMenuChoice(int min, int max) {
        int choice = -1;
        while (true) {
            System.out.print("Enter your choice: ");
            try {
                choice = Integer.parseInt(scanner.nextLine());
                if (choice >= min && choice <= max) {
                    break;
                } else {
                    System.out.println("Invalid choice. Please enter a number between " + min + " and " + max + ".");
                }
            } catch (NumberFormatException e) {
                System.out.println("Invalid input. Please enter a number.");
            }
        }
        return choice;
    }

     protected void changePassword() {
         System.out.println("\n--- Change Password ---");
         System.out.print("Enter current password: ");
         String oldPassword = scanner.nextLine();
         System.out.print("Enter new password: ");
         String newPassword = scanner.nextLine();
         System.out.print("Confirm new password: ");
         String confirmPassword = scanner.nextLine();

         if (!newPassword.equals(confirmPassword)) {
             System.out.println("New passwords do not match.");
             return;
         }
         if (newPassword.isEmpty()) {
              System.out.println("Password cannot be empty.");
              return;
         }

         // Assuming AuthController is accessible or password change logic is here/in BaseController
         // Let's assume BaseController has access to AuthController or the users map
         if (currentUser.getPassword().equals(oldPassword)) {
             currentUser.setPassword(newPassword);
             System.out.println("Password changed successfully. You will need to log in again.");
             // Force logout by returning a specific value or setting a flag
         } else {
             System.out.println("Incorrect current password.");
         }
     }

     protected void applyFilters() {
         if (controller != null) {
             controller.applyFilters();
         } else {
             System.out.println("Error: Controller not available for filtering.");
         }
     }
}

// --- Specific Role Views ---

class ApplicantView extends BaseView {
    private ApplicantController applicantController;

    public ApplicantView(Scanner scanner, User currentUser, ApplicantController controller) {
        super(scanner, currentUser, controller);
        this.applicantController = controller;
    }

    @Override
    public void displayMenu() {
        int choice;
        do {
            System.out.println("\n=========== Applicant Menu ===========");
            System.out.println("Welcome, " + currentUser.getName() + "!");
            System.out.println("1. View Available BTO Projects");
            System.out.println("2. Apply for BTO Project");
            System.out.println("3. View My Application Status");
            System.out.println("4. Withdraw Application");
            System.out.println("5. Submit Enquiry");
            System.out.println("6. View My Enquiries");
            System.out.println("7. Edit My Enquiry");
            System.out.println("8. Delete My Enquiry");
            System.out.println("9. Apply/Clear Project Filters");
            System.out.println("10. Change Password");
            System.out.println("0. Logout");
            System.out.println("======================================");

            choice = getMenuChoice(0, 10);

            switch (choice) {
                case 1: applicantController.viewOpenProjects(); break;
                case 2: applicantController.applyForProject(); break;
                case 3: applicantController.viewMyApplication(); break;
                case 4: applicantController.requestWithdrawal(); break;
                case 5: applicantController.submitEnquiry(); break;
                case 6: applicantController.viewMyEnquiries(); break;
                case 7: applicantController.editMyEnquiry(); break;
                case 8: applicantController.deleteMyEnquiry(); break;
                case 9: applyFilters(); break;
                case 10: changePassword(); if (!currentUser.getPassword().equals("password")) choice = 0; break; // Force logout after pwd change
                case 0: System.out.println("Logging out..."); break;
                default: System.out.println("Invalid choice."); break; // Should not happen
            }
             if (choice != 0) {
                 System.out.println("\nPress Enter to continue...");
                 scanner.nextLine(); // Pause
             }

        } while (choice != 0);
    }
}

class OfficerView extends BaseView {
    private OfficerController officerController;

    public OfficerView(Scanner scanner, User currentUser, OfficerController controller) {
        super(scanner, currentUser, controller);
        this.officerController = controller;
    }

    @Override
    public void displayMenu() {
        int choice;
        do {
            System.out.println("\n=========== HDB Officer Menu ===========");
            System.out.println("Welcome, Officer " + currentUser.getName() + "!");
            if (((HDBOfficer)currentUser).getHandlingProjectName() != null) {
                 System.out.println("Handling Project: " + ((HDBOfficer)currentUser).getHandlingProjectName());
            }
            System.out.println("--- Officer Actions ---");
            System.out.println("1. Register to Handle Project");
            System.out.println("2. View My Registration Status");
            System.out.println("3. View Handling Project Details");
            System.out.println("4. View/Reply Enquiries (Handling Project)");
            System.out.println("5. Manage Flat Booking (Process Successful Applicants)");
            // Receipt generation is part of manageFlatBooking
            System.out.println("--- Applicant Actions (Inherited) ---");
            System.out.println("6. View Available BTO Projects");
            System.out.println("7. Apply for BTO Project");
            System.out.println("8. View My Application Status");
            System.out.println("9. Withdraw Application");
            System.out.println("10. Submit Enquiry");
            System.out.println("11. View My Enquiries");
            System.out.println("12. Edit My Enquiry");
            System.out.println("13. Delete My Enquiry");
            System.out.println("--- Common Actions ---");
            System.out.println("14. Apply/Clear Project Filters");
            System.out.println("15. Change Password");
            System.out.println("0. Logout");
            System.out.println("========================================");

            choice = getMenuChoice(0, 15);

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
                case 9: officerController.requestWithdrawal(); break;
                case 10: officerController.submitEnquiry(); break;
                case 11: officerController.viewMyEnquiries(); break;
                case 12: officerController.editMyEnquiry(); break;
                case 13: officerController.deleteMyEnquiry(); break;
                // Common Actions
                case 14: applyFilters(); break;
                case 15: changePassword(); if (!currentUser.getPassword().equals("password")) choice = 0; break; // Force logout
                case 0: System.out.println("Logging out..."); break;
                default: System.out.println("Invalid choice."); break;
            }
             if (choice != 0) {
                 System.out.println("\nPress Enter to continue...");
                 scanner.nextLine(); // Pause
             }
        } while (choice != 0);
    }
}

class ManagerView extends BaseView {

    public ManagerView(Scanner scanner, User currentUser, ManagerController controller) {
        super(scanner, currentUser, controller);
    }

    @Override
    public void displayMenu() {
        int choice;
        do {
            System.out.println("\n=========== HDB Manager Menu ===========");
            System.out.println("Welcome, Manager " + currentUser.getName() + "!");
            System.out.println("--- Project Management ---");
            System.out.println("1. Create New BTO Project");
            System.out.println("2. Edit My Project Details");
            System.out.println("3. Delete My Project");
            System.out.println("4. Toggle Project Visibility");
            System.out.println("5. View All Projects");
            System.out.println("6. View My Projects");
            System.out.println("--- Staff & Application Management ---");
            System.out.println("7. Manage Officer Registrations (Approve/Reject)");
            System.out.println("8. Manage BTO Applications (Approve/Reject)");
            // System.out.println("9. Manage Application Withdrawals"); // Simplified/Auto-approved
            System.out.println("--- Reporting & Enquiries ---");
            System.out.println("10. Generate Applicant Report (Booked Flats)");
            System.out.println("11. View Enquiries (ALL Projects)");
            System.out.println("12. View/Reply Enquiries (My Projects)");
            System.out.println("--- Common Actions ---");
            System.out.println("13. Apply/Clear Project Filters (for View All/My)");
            System.out.println("14. Change Password");
            System.out.println("0. Logout");
            System.out.println("========================================");

            choice = getMenuChoice(0, 14);

            switch (choice) {
                // Project Management
                case 1: ((ManagerController) controller).createProject(); break;
                case 2: ((ManagerController) controller).editProject(); break;
                case 3: ((ManagerController) controller).deleteProject(); break;
                case 4: ((ManagerController) controller).toggleProjectVisibility(); break;
                case 5: ((ManagerController) controller).viewAllProjects(); break;
                case 6: ((ManagerController) controller).viewMyProjects(); break;
                // Staff & Application Management
                case 7: ((ManagerController) controller).manageOfficerRegistrations(); break;
                case 8: ((ManagerController) controller).manageApplications(); break;
                // case 9: managerController.manageWithdrawals(); break; // Skipped
                // Reporting & Enquiries
                case 10: ((ManagerController) controller).generateApplicantReport(); break;
                case 11: ((ManagerController) controller).viewAllEnquiries(); break;
                case 12: ((ManagerController) controller).viewAndReplyToManagedEnquiries(); break;
                // Common Actions
                case 13: applyFilters(); break;
                case 14: changePassword(); if (!currentUser.getPassword().equals("password")) choice = 0; break; // Force logout
                case 0: System.out.println("Logging out..."); break;
                default: System.out.println("Invalid choice."); break;
            }
             if (choice != 0) {
                 System.out.println("\nPress Enter to continue...");
                 scanner.nextLine(); // Pause
             }
        } while (choice != 0);
    }
}


// ==================
// Main Application Class
// ==================
public class BTOApp {

    private Map<String, User> users;
    private List<Project> projects;
    private Map<String, BTOApplication> applications;
    private List<Enquiry> enquiries;
    private Map<String, OfficerRegistration> officerRegistrations;

    private AuthController authController;
    private Scanner scanner;

    public BTOApp() {
        scanner = new Scanner(System.in);
    }

    public void initialize() {
        System.out.println("Initializing BTO Management System...");
        // Load data - order matters for dependencies (users first, then projects, then others)
        users = DataService.loadUsers();
        projects = DataService.loadProjects(users); // Pass users for validation
        applications = DataService.loadApplications();
        enquiries = DataService.loadEnquiries();
        officerRegistrations = DataService.loadOfficerRegistrations();

        // Post-load adjustments (ensure consistency)
        // - Update user application status based on loaded applications
        // - Update officer handling project based on approved registrations/projects
        // - Adjust project available units based on booked applications
        // (These adjustments are now integrated into the loading methods)

        authController = new AuthController(users);
        System.out.println("Initialization complete.");
    }

    public void run() {
        User currentUser = null;
        do {
            currentUser = loginScreen();
            if (currentUser != null) {
                showRoleMenu(currentUser);
                currentUser = null; // Reset after logout
            }
        } while (true); // Loop indefinitely until explicitly exited (e.g., via System.exit or breaking loop)
                       // For now, login loop continues after logout.
    }

    private User loginScreen() {
        System.out.println("\n--- Welcome to BTO Management System ---");
        System.out.println("--- Login ---");
        System.out.print("Enter NRIC: ");
        String nric = scanner.nextLine().trim().toUpperCase();
        System.out.print("Enter Password: ");
        String password = scanner.nextLine(); // Read password

        User user = authController.login(nric, password);
        if (user != null) {
            System.out.println("Login successful! Role: " + user.getRole());
        }
        // Error messages handled within AuthController
        return user;
    }

    private void showRoleMenu(User user) {
        BaseView view;

        switch (user.getRole()) {
            case APPLICANT:
                ApplicantController appController = new ApplicantController(users, projects, applications, enquiries, officerRegistrations, user, scanner);
                view = new ApplicantView(scanner, user, appController);
                break;
            case HDB_OFFICER:
                 OfficerController offController = new OfficerController(users, projects, applications, enquiries, officerRegistrations, user, scanner);
                 view = new OfficerView(scanner, user, offController);
                break;
            case HDB_MANAGER:
                 ManagerController manController = new ManagerController(users, projects, applications, enquiries, officerRegistrations, user, scanner);
                 view = new ManagerView(scanner, user, manController);
                break;
            default:
                System.out.println("Error: Unknown user role.");
                return;
        }
        view.displayMenu(); // Enters the role-specific menu loop
    }

    public void shutdown() {
        System.out.println("\nShutting down BTO Management System...");
        // Save all data
        DataService.saveUsers(users);
        DataService.saveProjects(projects);
        DataService.saveApplications(applications);
        DataService.saveEnquiries(enquiries);
        DataService.saveOfficerRegistrations(officerRegistrations);
        System.out.println("Data saved.");
        scanner.close();
        System.out.println("System shutdown complete.");
    }


    public static void main(String[] args) {
        BTOApp app = new BTOApp();
        app.initialize();

        // Add shutdown hook to save data on exit (Ctrl+C or normal exit)
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            app.shutdown();
        }));

        try {
            app.run();
        } catch (Exception e) {
             System.err.println("An unexpected error occurred: " + e.getMessage());
             e.printStackTrace();
             // Attempt to save data even if an error occurred
             app.shutdown();
        }
    }
}