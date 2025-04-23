package Services;

import java.io.File;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import Models.Enquiry;
import Parsers.Dparse;
import Utils.DateUtils;

public class EnquiryService implements IEnquiryService {
    private static final String DATA_DIR = "data";
    private static final String DELIMITER = ",";
    private static final String ENQUIRY_FILE = DATA_DIR + File.separator + "enquiries.csv";
    private static final String[] ENQUIRY_HEADER = {"EnquiryID", "ApplicantNRIC", "ProjectName", "EnquiryText", "ReplyText", "RepliedByNRIC", "EnquiryDate", "ReplyDate"};

    private List<Enquiry> enquiries;

    public EnquiryService() {
        this.enquiries = new ArrayList<>();
    }

    @Override
    public List<Enquiry> loadEnquiries() {
        this.enquiries.clear(); // Clear before loading
        Set<String> enquiryIds = new HashSet<>(); // Track IDs during load

        CsvRW.readCsv(ENQUIRY_FILE, ENQUIRY_HEADER.length).forEach(data -> {
            try {
                String id = data[0].trim();
                 if (id.isEmpty() || !enquiryIds.add(id)) { // Use the temporary set for check
                     if (!id.isEmpty()) System.err.println("Skipping duplicate enquiry ID: " + id);
                    return;
                 }
                String applicantNric = data[1].trim();
                String projectName = data[2].trim();
                String text = data[3].trim();
                String reply = data[4].trim();
                String repliedBy = data[5].trim();
                Date enqDate = Dparse.parseDate(data[6].trim());
                Date replyDate = Dparse.parseDate(data[7].trim());

                 if (text.isEmpty() || enqDate == null) {
                     System.err.println("Skipping enquiry with missing text or invalid date: " + id);
                     enquiryIds.remove(id); // Remove invalid ID from tracking set
                     return;
                 }
                 if ((reply != null && !reply.isEmpty()) && (repliedBy == null || repliedBy.isEmpty() || replyDate == null)) {
                     System.err.println("Warning: Enquiry " + id + " seems replied but missing replier NRIC or reply date. Loading reply as is.");
                 }

                // Use the constructor that takes all fields including ID
                Enquiry enquiry = new Enquiry(id, applicantNric, projectName, text, reply, repliedBy, enqDate, replyDate);
                this.enquiries.add(enquiry);
                 // The Enquiry constructor now handles updating the static nextId internally
            } catch (IllegalArgumentException e) {
                 System.err.println("Error parsing enum/data in enquiry data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            } catch (Exception e) {
                System.err.println("Error parsing enquiry data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });
        Enquiry.finalizeNextIdInitialization(); // Call static method after loading all
        System.out.println("Loaded " + this.enquiries.size() + " enquiries.");
        return new ArrayList<>(this.enquiries); // Return copy
    }

    @Override
    public void saveEnquiries(List<Enquiry> enquiriesToSave) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(ENQUIRY_HEADER);
        enquiriesToSave.stream()
            .sorted(Comparator.comparing(Enquiry::getEnquiryId))
            .forEach(enq -> {
                dataList.add(new String[]{
                    enq.getEnquiryId(),
                    enq.getApplicantNric(),
                    enq.getProjectName(),
                    enq.getEnquiryText(),
                    enq.getReplyText() == null ? "" : enq.getReplyText(),
                    enq.getRepliedByNric() == null ? "" : enq.getRepliedByNric(),
                    DateUtils.formatDate(enq.getEnquiryDate()),
                    enq.getReplyDate() == null ? "" : DateUtils.formatDate(enq.getReplyDate()) // Handle null reply date
                });
            });
        CsvRW.writeCsv(ENQUIRY_FILE, dataList);
        System.out.println("Saved enquiries.");
        this.enquiries = new ArrayList<>(enquiriesToSave); // Update internal list
    }

     @Override
     public void addEnquiry(Enquiry enquiry) {
         if (enquiry != null && findEnquiryById(enquiry.getEnquiryId()) == null) {
             this.enquiries.add(enquiry);
         } else if (enquiry != null) {
             System.err.println("Enquiry with ID " + enquiry.getEnquiryId() + " already exists.");
         }
     }

     @Override
     public boolean removeEnquiry(String enquiryId) {
         if (enquiryId != null) {
             return this.enquiries.removeIf(e -> enquiryId.equals(e.getEnquiryId()));
         }
         return false;
     }

     @Override
     public Enquiry findEnquiryById(String enquiryId) {
         if (enquiryId == null) return null;
         return this.enquiries.stream()
             .filter(e -> enquiryId.equals(e.getEnquiryId()))
             .findFirst()
             .orElse(null);
     }

     @Override
     public List<Enquiry> getEnquiriesByApplicant(String applicantNric) {
         if (applicantNric == null) return new ArrayList<>();
         return this.enquiries.stream()
             .filter(e -> applicantNric.equals(e.getApplicantNric()))
             .collect(Collectors.toList());
     }

     @Override
     public List<Enquiry> getEnquiriesByProject(String projectName) {
         if (projectName == null) return new ArrayList<>();
         return this.enquiries.stream()
             .filter(e -> projectName.equals(e.getProjectName()))
             .collect(Collectors.toList());
     }

     @Override
     public List<Enquiry> getAllEnquiries() {
         return new ArrayList<>(this.enquiries); // Return copy
     }
}
