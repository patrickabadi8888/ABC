package Services;

import java.io.File;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import Models.Enquiry;
import Parsers.Dparse;
import Utils.DateUtils;

public class EnquiryService {
    private static final String DATA_DIR = "data";
    private static final String DELIMITER = ",";
    private static final String ENQUIRY_FILE = DATA_DIR + File.separator + "enquiries.csv";
    private static final String[] ENQUIRY_HEADER = {"EnquiryID", "ApplicantNRIC", "ProjectName", "EnquiryText", "ReplyText", "RepliedByNRIC", "EnquiryDate", "ReplyDate"};
    public static List<Enquiry> loadEnquiries() {
        List<Enquiry> enquiries = new ArrayList<>();
        Set<String> enquiryIds = new HashSet<>();

        CsvRW.readCsv(ENQUIRY_FILE, ENQUIRY_HEADER.length).forEach(data -> {
            try {
                String id = data[0].trim();
                 if (id.isEmpty() || !enquiryIds.add(id)) {
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
                     enquiryIds.remove(id);
                     return;
                 }
                 if ((reply != null && !reply.isEmpty()) && (repliedBy == null || repliedBy.isEmpty() || replyDate == null)) {
                     System.err.println("Warning: Enquiry " + id + " seems replied but missing replier NRIC or reply date. Loading reply as is.");
                 }


                Enquiry enquiry = new Enquiry(id, applicantNric, projectName, text, reply, repliedBy, enqDate, replyDate);
                enquiries.add(enquiry);
            } catch (IllegalArgumentException e) {
                 System.err.println("Error parsing enum/data in enquiry data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            } catch (Exception e) {
                System.err.println("Error parsing enquiry data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });
        Enquiry.finalizeNextIdInitialization();
        System.out.println("Loaded " + enquiries.size() + " enquiries.");
        return enquiries;
    }

    public static void saveEnquiries(List<Enquiry> enquiries) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(ENQUIRY_HEADER);
        enquiries.stream()
            .sorted(Comparator.comparing(enquiry -> enquiry.getEnquiryId()))
            .forEach(enq -> {
                dataList.add(new String[]{
                    enq.getEnquiryId(),
                    enq.getApplicantNric(),
                    enq.getProjectName(),
                    enq.getEnquiryText(),
                    enq.getReplyText() == null ? "" : enq.getReplyText(),
                    enq.getRepliedByNric() == null ? "" : enq.getRepliedByNric(),
                    DateUtils.formatDate(enq.getEnquiryDate()),
                    DateUtils.formatDate(enq.getReplyDate())
                });
            });
        CsvRW.writeCsv(ENQUIRY_FILE, dataList);
        System.out.println("Saved enquiries.");
    }
}
