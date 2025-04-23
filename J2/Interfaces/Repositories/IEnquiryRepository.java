package Interfaces.Repositories;

import java.util.List;
import Models.Enquiry;

public interface IEnquiryRepository {
    List<Enquiry> loadEnquiries();
    void saveEnquiries(List<Enquiry> enquiries);
    List<Enquiry> getAllEnquiries(); // Added for easier access by services
}
