package Repositories;

import java.io.File;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import Interfaces.Repositories.IEnquiryRepository;
import Models.Enquiry;
import Parsers.Dparse;
import Services.CsvRW; // Assuming CsvRW is in Services package
import Utils.DateUtils;

public class CsvEnquiryRepository implements IEnquiryRepository {
    private static final String DATA_DIR = "data";
    private static final String DELIMITER = ",";
    private static final String ENQUIRY_FILE = DATA_DIR + File.separator + "enquiries.csv";
    private static final String[] ENQUIRY_HEADER = {"EnquiryID", "ApplicantNRIC", "ProjectName", "EnquiryText", "ReplyText", "RepliedByNRIC", "EnquiryDate", "ReplyDate"};

    private List<Enquiry> enquiriesCache;

    public CsvEnquiryRepository() {
        this.enquiriesCache = null; // Load on demand
    }

    @Override
    public List<Enquiry> loadEnquiries() {
        if (this.enquiriesCache != null) {
            return new ArrayList<>(this.enquiriesCache); // Return copy
        }

        List<Enquiry> loadedEnquiries = new ArrayList<>();
        Set<String> enquiryIds = new HashSet<>();
        List<String[]> rawData = CsvRW.readCsv(ENQUIRY_FILE, ENQUIRY_HEADER.length);

        for (String[] data : rawData) {
            try {
                String id = data[0].trim();
                 if (id.isEmpty() || !enquiryIds.add(id)) {
                     if (!id.isEmpty()) System.err.println("Skipping duplicate enquiry ID in CSV: " + id);
                    continue;
                 }
                String applicantNric = data[1].trim();
                String projectName = data[2].trim();
                String text = data[3].trim(); // Keep raw text from CSV
                String reply = data[4].trim(); // Keep raw text from CSV
                String repliedBy = data[5].trim();
                Date enqDate = Dparse.parseDate(data[6].trim());
                Date replyDate = Dparse.parseDate(data[7].trim());

                 if (text.isEmpty() || enqDate == null) {
                     System.err.println("Skipping enquiry with missing text or invalid date: " + id);
                     enquiryIds.remove(id); // Remove from set if skipped
                     continue;
                 }
                 if ((reply != null && !reply.isEmpty()) && (repliedBy == null || repliedBy.isEmpty() || replyDate == null)) {
                     System.err.println("Warning: Enquiry " + id + " seems replied but missing replier NRIC or reply date. Loading reply as is.");
                 }

                // Use the constructor that takes all fields, handles nulls/emptiness internally
                Enquiry enquiry = new Enquiry(id, applicantNric, projectName, text, reply, repliedBy, enqDate, replyDate);
                loadedEnquiries.add(enquiry);
            } catch (IllegalArgumentException e) {
                 System.err.println("Error parsing enum/data in enquiry data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            } catch (Exception e) {
                System.err.println("Error parsing enquiry data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        }
        Enquiry.finalizeNextIdInitialization(); // Ensure nextId is set correctly after loading all
        this.enquiriesCache = loadedEnquiries;
        System.out.println("Loaded " + this.enquiriesCache.size() + " enquiries from CSV.");
        return new ArrayList<>(this.enquiriesCache); // Return copy
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
                    enq.getEnquiryText(), // Save raw text
                    enq.getReplyText() == null ? "" : enq.getReplyText(), // Save raw text or empty
                    enq.getRepliedByNric() == null ? "" : enq.getRepliedByNric(),
                    DateUtils.formatDate(enq.getEnquiryDate()),
                    DateUtils.formatDate(enq.getReplyDate()) // Handles null date formatting
                });
            });
        CsvRW.writeCsv(ENQUIRY_FILE, dataList);
        this.enquiriesCache = new ArrayList<>(enquiriesToSave); // Update cache
        System.out.println("Saved " + enquiriesToSave.size() + " enquiries to CSV.");
    }

     @Override
     public List<Enquiry> getAllEnquiries() {
         if (this.enquiriesCache == null) {
             loadEnquiries();
         }
         // Return a defensive copy
         return new ArrayList<>(this.enquiriesCache);
     }
}
