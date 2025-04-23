package Services;

import java.util.List;
import Models.Enquiry;

public interface IEnquiryService {
    List<Enquiry> loadEnquiries();
    void saveEnquiries(List<Enquiry> enquiries);
    void addEnquiry(Enquiry enquiry);
    boolean removeEnquiry(String enquiryId);
    Enquiry findEnquiryById(String enquiryId);
    List<Enquiry> getEnquiriesByApplicant(String applicantNric);
    List<Enquiry> getEnquiriesByProject(String projectName);
    List<Enquiry> getAllEnquiries(); // To get list for saving/syncing
}
