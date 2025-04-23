package Models;

import java.util.Date;

public class Enquiry {
    private final String enquiryId;
    private final String applicantNric;
    private final String projectName;
    private String enquiryText;
    private String replyText;
    private String repliedByNric;
    private final Date enquiryDate;
    private Date replyDate;
    private static long nextId = 1;

    public Enquiry(String applicantNric, String projectName, String enquiryText, Date enquiryDate) {
        if (applicantNric == null || projectName == null || enquiryText == null || enquiryText.trim().isEmpty() || enquiryDate == null) {
            throw new IllegalArgumentException("Invalid Enquiry parameters");
        }
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
        this.replyDate = replyDate;

        updateNextId(enquiryId);
    }

    public static void updateNextId(String loadedEnquiryId) {
         if (loadedEnquiryId != null && loadedEnquiryId.startsWith("ENQ")) {
            try {
                long idNum = Long.parseLong(loadedEnquiryId.substring(3));
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
     public static void finalizeNextIdInitialization() {
         System.out.println("Enquiry nextId initialized to: " + nextId);
     }


    public String getEnquiryId() { return enquiryId; }
    public String getApplicantNric() { return applicantNric; }
    public String getProjectName() { return projectName; }
    public String getEnquiryText() { return enquiryText; }
    public String getReplyText() { return replyText; }
    public String getRepliedByNric() { return repliedByNric; }
    public Date getEnquiryDate() { return enquiryDate; }
    public Date getReplyDate() { return replyDate; }

    public boolean setEnquiryText(String enquiryText) {
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
}

