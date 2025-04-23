/**
 * Interface defining the contract for enquiry data management services.
 * Specifies methods for loading, saving, finding, retrieving, adding, and removing enquiries.
 *
 * @author Kishore Kumar
 */
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

    List<Enquiry> getAllEnquiries();
}
