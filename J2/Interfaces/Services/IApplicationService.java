package Interfaces.Services;

import java.util.Map;

import Enums.ApplicationStatus;
import Enums.FlatType;
import Models.Applicant;
import Models.BTOApplication;
import Models.Project;
import Models.User;

public interface IApplicationService {
    BTOApplication findApplicationByApplicantAndProject(String nric, String projectName);
    boolean submitApplication(Applicant applicant, Project project, FlatType flatType);
    boolean requestWithdrawal(Applicant applicant);
    boolean approveWithdrawal(BTOApplication application);
    boolean rejectWithdrawal(BTOApplication application);
    boolean approveApplication(BTOApplication application);
    boolean rejectApplication(BTOApplication application);
    boolean bookFlat(BTOApplication application, Applicant applicant, Project project);
    void synchronizeApplicantStatus(Applicant applicant);
    void adjustUnitsOnLoad(); // Called after loading applications
    void removeApplicationsForProject(String projectName); // For project deletion
    Map<String, BTOApplication> getAllApplications();
}
