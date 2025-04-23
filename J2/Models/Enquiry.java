package Models;

import java.util.Date;
import java.util.Objects;
import java.util.concurrent.atomic.AtomicLong; // Use AtomicLong for thread safety

public class Enquiry {
    private final String enquiryId;
    private final String applicantNric;
    private final String projectName;
    private String enquiryText; // Mutable if not replied
    private String replyText; // Null until replied
    private String repliedByNric; // Null until replied
    private final Date enquiryDate;
    private Date replyDate; // Null until replied

    // Thread-safe static counter for generating unique IDs
    private static final AtomicLong nextId = new AtomicLong(1);

    // Constructor for new enquiries
    public Enquiry(String applicantNric, String projectName, String enquiryText, Date enquiryDate) {
        // Use Objects.requireNonNull for cleaner null checks
        Objects.requireNonNull(applicantNric, "Applicant NRIC cannot be null");
        Objects.requireNonNull(projectName, "Project Name cannot be null");
        Objects.requireNonNull(enquiryText, "Enquiry Text cannot be null");
        Objects.requireNonNull(enquiryDate, "Enquiry Date cannot be null");

        if (applicantNric.trim().isEmpty() || projectName.trim().isEmpty() || enquiryText.trim().isEmpty()) {
            throw new IllegalArgumentException("Enquiry fields (NRIC, Project, Text) cannot be empty");
        }

        // Generate unique ID atomically
        this.enquiryId = "ENQ" + nextId.getAndIncrement();
        this.applicantNric = applicantNric;
        this.projectName = projectName;
        this.enquiryText = enquiryText.trim(); // Trim input text
        this.enquiryDate = enquiryDate;
        // Initialize reply fields to null
        this.replyText = null;
        this.repliedByNric = null;
        this.replyDate = null;
    }

    // Constructor for loading from persistence
    public Enquiry(String enquiryId, String applicantNric, String projectName, String enquiryText, String replyText, String repliedByNric, Date enquiryDate, Date replyDate) {
        // Null checks for essential fields during load
        Objects.requireNonNull(enquiryId, "Enquiry ID cannot be null when loading");
        Objects.requireNonNull(applicantNric, "Applicant NRIC cannot be null when loading");
        Objects.requireNonNull(projectName, "Project Name cannot be null when loading");
        Objects.requireNonNull(enquiryText, "Enquiry Text cannot be null when loading");
        Objects.requireNonNull(enquiryDate, "Enquiry Date cannot be null when loading");

        this.enquiryId = enquiryId;
        this.applicantNric = applicantNric;
        this.projectName = projectName;
        this.enquiryText = enquiryText; // Assume already trimmed from source
        // Handle potentially empty/null reply fields from CSV
        this.replyText = (replyText == null || replyText.trim().isEmpty()) ? null : replyText.trim();
        this.repliedByNric = (repliedByNric == null || repliedByNric.trim().isEmpty()) ? null : repliedByNric.trim();
        this.enquiryDate = enquiryDate;
        this.replyDate = replyDate; // Can be null if not replied

        // Update the static counter based on loaded IDs
        updateNextId(enquiryId);
    }

    // Method to update the static ID counter based on loaded IDs
    // Should be called by the repository after loading all enquiries
    public static void updateNextId(String loadedEnquiryId) {
         if (loadedEnquiryId != null && loadedEnquiryId.startsWith("ENQ")) {
            try {
                // Extract number part after "ENQ"
                long idNum = Long.parseLong(loadedEnquiryId.substring(3));
                // Atomically set nextId if the loaded ID is greater or equal
                nextId.accumulateAndGet(idNum + 1, Math::max);
            } catch (NumberFormatException | StringIndexOutOfBoundsException e) {
                // Log warning if parsing fails, but don't stop loading
                System.err.println("Warning: Could not parse enquiry ID for nextId update: " + loadedEnquiryId);
            }
         }
    }

    // Method to call after all loading is done (e.g., in Repository or DataService)
     public static void finalizeNextIdInitialization() {
         System.out.println("Enquiry nextId initialized to: " + nextId.get());
     }

    // --- Getters ---
    public String getEnquiryId() { return enquiryId; }
    public String getApplicantNric() { return applicantNric; }
    public String getProjectName() { return projectName; }
    public String getEnquiryText() { return enquiryText; }
    public String getReplyText() { return replyText; }
    public String getRepliedByNric() { return repliedByNric; }
    public Date getEnquiryDate() { return enquiryDate; }
    public Date getReplyDate() { return replyDate; }

    // --- Setters ---

    /**
     * Sets the enquiry text. Can only be done if the enquiry has not been replied to.
     * @param enquiryText The new enquiry text (cannot be null or empty).
     * @return true if the text was set successfully, false otherwise.
     */
    public boolean setEnquiryText(String enquiryText) {
        if (isReplied()) {
             System.err.println("Cannot edit an enquiry that has already been replied to (ID: " + enquiryId + ").");
             return false;
        }
        if (enquiryText == null || enquiryText.trim().isEmpty()) {
             System.err.println("Enquiry text cannot be empty.");
             return false;
        }
        this.enquiryText = enquiryText.trim();
        return true;
    }

    /**
     * Sets the reply details for the enquiry.
     * @param replyText The reply text (cannot be null or empty).
     * @param repliedByNric The NRIC of the user who replied (cannot be null or empty).
     * @param replyDate The date of the reply (cannot be null).
     * @return true if the reply was set successfully, false otherwise.
     */
    public boolean setReply(String replyText, String repliedByNric, Date replyDate) {
        // Prevent setting reply if already replied? Or allow overwriting? Let's prevent.
        if (isReplied()) {
             System.err.println("Enquiry " + enquiryId + " has already been replied to. Cannot set reply again.");
             return false;
        }
        if (replyText == null || replyText.trim().isEmpty() ||
            repliedByNric == null || repliedByNric.trim().isEmpty() ||
            replyDate == null)
        {
            System.err.println("Invalid reply parameters provided for enquiry ID: " + enquiryId + ". All fields (text, replier NRIC, date) are required.");
            return false;
        }
        this.replyText = replyText.trim();
        this.repliedByNric = repliedByNric.trim();
        this.replyDate = replyDate;
        return true;
    }

    // --- State Check ---
    public boolean isReplied() {
        // Considered replied if replyText is not null and not empty
        return this.replyText != null && !this.replyText.isEmpty();
    }

    // --- Standard overrides ---
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Enquiry enquiry = (Enquiry) o;
        return enquiryId.equals(enquiry.enquiryId); // ID is unique identifier
    }

    @Override
    public int hashCode() {
        return Objects.hash(enquiryId);
    }

    @Override
    public String toString() {
        return "Enquiry{" +
                "enquiryId='" + enquiryId + '\'' +
                ", applicantNric='" + applicantNric + '\'' +
                ", projectName='" + projectName + '\'' +
                ", enquiryDate=" + enquiryDate +
                ", replied=" + isReplied() +
                '}';
    }
}
