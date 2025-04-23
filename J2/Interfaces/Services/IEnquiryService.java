package Interfaces.Services;

import java.util.List;
import Models.Enquiry;
import Models.User;

public interface IEnquiryService {
    boolean submitEnquiry(User user, String projectName, String text);
    boolean replyToEnquiry(Enquiry enquiry, String replyText, User replier);
    boolean editEnquiry(Enquiry enquiry, String newText);
    boolean deleteEnquiry(Enquiry enquiry);
    List<Enquiry> getEnquiriesByApplicant(String nric);
    List<Enquiry> getEnquiriesByProject(String projectName);
    List<Enquiry> getUnrepliedEnquiriesForProjects(List<String> projectNames);
    List<Enquiry> getRepliedEnquiriesForProjects(List<String> projectNames);
    List<Enquiry> getAllEnquiries();
    void removeEnquiriesForProject(String projectName); // For project deletion
}
