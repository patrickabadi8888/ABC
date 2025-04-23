package Services;

import java.util.List;
import java.util.stream.Collectors;

import Interfaces.Repositories.IEnquiryRepository;
import Interfaces.Services.IEnquiryService;
import Models.Enquiry;
import Models.User;
import Utils.DateUtils;

public class EnquiryService implements IEnquiryService {

    private final IEnquiryRepository enquiryRepository;

    public EnquiryService(IEnquiryRepository enquiryRepository) {
        this.enquiryRepository = enquiryRepository;
    }

    @Override
    public boolean submitEnquiry(User user, String projectName, String text) {
        if (user == null || projectName == null || projectName.trim().isEmpty() || text == null || text.trim().isEmpty()) {
            System.err.println("Invalid parameters for submitting enquiry.");
            return false;
        }
        // Project existence check can be done here or assumed valid based on user input context
        // Let's assume context is valid for now.

        Enquiry newEnquiry = new Enquiry(user.getNric(), projectName.trim(), text.trim(), DateUtils.getCurrentDate());

        List<Enquiry> currentEnquiries = enquiryRepository.getAllEnquiries();
        currentEnquiries.add(newEnquiry);
        enquiryRepository.saveEnquiries(currentEnquiries);

        System.out.println("Enquiry submitted successfully (ID: " + newEnquiry.getEnquiryId() + ").");
        return true;
    }

    @Override
    public boolean replyToEnquiry(Enquiry enquiry, String replyText, User replier) {
        if (enquiry == null || replyText == null || replyText.trim().isEmpty() || replier == null) {
             System.err.println("Invalid parameters for replying to enquiry.");
            return false;
        }

        if (enquiry.setReply(replyText, replier.getNric(), DateUtils.getCurrentDate())) {
            // Persist the change
            List<Enquiry> currentEnquiries = enquiryRepository.getAllEnquiries();
            // Find and update the enquiry in the list (or replace if list is mutable)
            for (int i = 0; i < currentEnquiries.size(); i++) {
                if (currentEnquiries.get(i).getEnquiryId().equals(enquiry.getEnquiryId())) {
                    currentEnquiries.set(i, enquiry);
                    break;
                }
            }
            enquiryRepository.saveEnquiries(currentEnquiries);
            System.out.println("Reply submitted successfully for enquiry ID: " + enquiry.getEnquiryId());
            return true;
        } else {
            // Error message printed within enquiry.setReply()
            return false;
        }
    }

    @Override
    public boolean editEnquiry(Enquiry enquiry, String newText) {
         if (enquiry == null || newText == null || newText.trim().isEmpty()) {
             System.err.println("Invalid parameters for editing enquiry.");
             return false;
         }
         if (enquiry.isReplied()) {
              System.err.println("Cannot edit an enquiry that has already been replied to (ID: " + enquiry.getEnquiryId() + ").");
              return false;
         }

         if (enquiry.setEnquiryText(newText)) {
             // Persist the change
             List<Enquiry> currentEnquiries = enquiryRepository.getAllEnquiries();
             for (int i = 0; i < currentEnquiries.size(); i++) {
                 if (currentEnquiries.get(i).getEnquiryId().equals(enquiry.getEnquiryId())) {
                     currentEnquiries.set(i, enquiry);
                     break;
                 }
             }
             enquiryRepository.saveEnquiries(currentEnquiries);
             System.out.println("Enquiry updated successfully.");
             return true;
         } else {
             // Error message printed within enquiry.setEnquiryText() or above
             return false;
         }
    }

    @Override
    public boolean deleteEnquiry(Enquiry enquiry) {
        if (enquiry == null) return false;

        if (enquiry.isReplied()) {
             System.err.println("Cannot delete an enquiry that has already been replied to (ID: " + enquiry.getEnquiryId() + ").");
             return false;
        }

        List<Enquiry> currentEnquiries = enquiryRepository.getAllEnquiries();
        boolean removed = currentEnquiries.removeIf(e -> e.getEnquiryId().equals(enquiry.getEnquiryId()));

        if (removed) {
            enquiryRepository.saveEnquiries(currentEnquiries);
            System.out.println("Enquiry deleted successfully.");
            return true;
        } else {
            System.err.println("Error: Failed to find enquiry " + enquiry.getEnquiryId() + " for deletion.");
            return false;
        }
    }

    @Override
    public List<Enquiry> getEnquiriesByApplicant(String nric) {
        return enquiryRepository.getAllEnquiries().stream()
                .filter(e -> e.getApplicantNric().equals(nric))
                .sorted(Comparator.comparing(Enquiry::getEnquiryDate).reversed())
                .collect(Collectors.toList());
    }

    @Override
    public List<Enquiry> getEnquiriesByProject(String projectName) {
         return enquiryRepository.getAllEnquiries().stream()
                .filter(e -> e.getProjectName().equalsIgnoreCase(projectName))
                .sorted(Comparator.comparing(Enquiry::getEnquiryDate).reversed())
                .collect(Collectors.toList());
    }

     @Override
     public List<Enquiry> getUnrepliedEnquiriesForProjects(List<String> projectNames) {
         if (projectNames == null || projectNames.isEmpty()) {
             return List.of(); // Return empty list if no projects specified
         }
         return enquiryRepository.getAllEnquiries().stream()
                 .filter(e -> projectNames.contains(e.getProjectName()) && !e.isReplied())
                 .sorted(Comparator.comparing(Enquiry::getProjectName) // Sort by project then date
                           .thenComparing(Enquiry::getEnquiryDate))
                 .collect(Collectors.toList());
     }

     @Override
     public List<Enquiry> getRepliedEnquiriesForProjects(List<String> projectNames) {
          if (projectNames == null || projectNames.isEmpty()) {
             return List.of();
         }
         return enquiryRepository.getAllEnquiries().stream()
                 .filter(e -> projectNames.contains(e.getProjectName()) && e.isReplied())
                 .sorted(Comparator.comparing(Enquiry::getProjectName)
                           .thenComparing(Enquiry::getEnquiryDate).reversed()) // Show newest replied first? Or oldest? Let's do newest.
                 .collect(Collectors.toList());
     }

     @Override
     public List<Enquiry> getAllEnquiries() {
          return enquiryRepository.getAllEnquiries().stream()
                 .sorted(Comparator.comparing(Enquiry::getProjectName)
                           .thenComparing(Enquiry::getEnquiryDate).reversed())
                 .collect(Collectors.toList());
     }

     @Override
     public void removeEnquiriesForProject(String projectName) {
         List<Enquiry> currentEnqs = enquiryRepository.getAllEnquiries();
         boolean changed = currentEnqs.removeIf(enq -> enq.getProjectName().equals(projectName));
         if (changed) {
             enquiryRepository.saveEnquiries(currentEnqs);
             System.out.println("Removed enquiries associated with deleted project: " + projectName);
         }
     }
}
