package Interfaces.Services;

import Enums.FlatType;
import Models.HDBOfficer;
import Models.Project;
import Models.User;

public interface IEligibilityService {
     boolean canApplyForFlatType(User user, FlatType type);
     boolean isProjectVisibleToUser(User user, Project project);
     boolean canOfficerRegisterForProject(HDBOfficer officer, Project project);
     boolean isOfficerHandlingOverlappingProject(HDBOfficer officer, Project targetProject);
     Project getOfficerHandlingProject(HDBOfficer officer);
}
