package Interfaces.Services;

import java.util.List;
import Enums.FlatType;
import Enums.MaritalStatus;
import Models.BTOApplication;

public interface IReportService {
    List<BTOApplication> generateBookedApplicantReport(List<String> projectNames, FlatType filterFlatType,
                                                       MaritalStatus filterMaritalStatus, int minAge, int maxAge);
    void displayApplicantReport(List<BTOApplication> reportData, FlatType filterFlatType,
                                MaritalStatus filterMaritalStatus, int minAge, int maxAge);
}
