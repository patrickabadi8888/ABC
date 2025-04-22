package Services;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.HashSet;
import java.util.Date;
import java.util.Comparator;
import java.io.File;

import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;
import java.io.BufferedReader;
import java.io.BufferedWriter;

import Enums.FlatType;
import Enums.MaritalStatus;
import Enums.OfficerRegistrationStatus;
import Enums.ApplicationStatus;

import Models.Project;
import Models.BTOApplication;
import Models.Enquiry;
import Models.OfficerRegistration;
import Models.User;
import Models.Applicant;
import Models.HDBOfficer;
import Models.HDBManager;
import Models.FlatTypeDetails;

public class DataService {
    private static final String DATA_DIR = "data";
    private static final String APPLICANT_LIST_FILE = DATA_DIR + File.separator + "ApplicantList.csv";
    private static final String OFFICER_LIST_FILE = DATA_DIR + File.separator + "OfficerList.csv";
    private static final String MANAGER_LIST_FILE = DATA_DIR + File.separator + "ManagerList.csv";
    private static final String PROJECT_FILE = DATA_DIR + File.separator + "ProjectList.csv";
    private static final String APPLICATION_FILE = DATA_DIR + File.separator + "applications.csv";
    private static final String ENQUIRY_FILE = DATA_DIR + File.separator + "enquiries.csv";
    private static final String OFFICER_REGISTRATION_FILE = DATA_DIR + File.separator + "officer_registrations.csv";

    private static final String DELIMITER = ",";
    private static final String LIST_DELIMITER = ";";
    public static final SimpleDateFormat DATE_FORMAT = new SimpleDateFormat("yyyy-MM-dd");
    private static final Pattern NRIC_PATTERN = Pattern.compile("^[STFG]\\d{7}[A-Z]$");

    private static final String[] APPLICANT_HEADER = {"Name", "NRIC", "Age", "Marital Status", "Password"};
    private static final String[] OFFICER_HEADER = {"Name", "NRIC", "Age", "Marital Status", "Password"};
    private static final String[] MANAGER_HEADER = {"Name", "NRIC", "Age", "Marital Status", "Password"};
    private static final String[] PROJECT_HEADER = {
        "Project Name", "Neighborhood", "Type 1", "Number of units for Type 1", "Selling price for Type 1",
        "Type 2", "Number of units for Type 2", "Selling price for Type 2",
        "Application opening date", "Application closing date", "Manager", "Officer Slot", "Officer", "Visibility"
    };
    private static final String[] APPLICATION_HEADER = {"ApplicationID", "ApplicantNRIC", "ProjectName", "FlatTypeApplied", "Status", "ApplicationDate"};
    private static final String[] ENQUIRY_HEADER = {"EnquiryID", "ApplicantNRIC", "ProjectName", "EnquiryText", "ReplyText", "RepliedByNRIC", "EnquiryDate", "ReplyDate"};
    private static final String[] OFFICER_REGISTRATION_HEADER = {"RegistrationID", "OfficerNRIC", "ProjectName", "Status", "RegistrationDate"};



    public static Map<String, User> loadUsers() {
        Map<String, User> users = new HashMap<>();

        readCsv(APPLICANT_LIST_FILE, APPLICANT_HEADER.length).forEach(data -> {
            try {
                String nric = data[1].trim();
                if (!isValidNric(nric) || users.containsKey(nric)) {
                    if(users.containsKey(nric)) System.err.println("Duplicate NRIC found in ApplicantList: " + nric + ". Skipping duplicate.");
                    else System.err.println("Invalid NRIC format in ApplicantList: " + nric + ". Skipping.");
                    return;
                }
                int age = Integer.parseInt(data[2].trim());
                MaritalStatus status = MaritalStatus.valueOf(data[3].trim().toUpperCase());
                Applicant applicant = new Applicant(nric, data[4].trim(), data[0].trim(), age, status);
                users.put(nric, applicant);
            } catch (Exception e) {
                System.err.println("Error parsing applicant data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });

        readCsv(OFFICER_LIST_FILE, OFFICER_HEADER.length).forEach(data -> {
            try {
                String nric = data[1].trim();
                 if (!isValidNric(nric)) {
                     System.err.println("Invalid NRIC format in OfficerList: " + nric + ". Skipping.");
                     return;
                 }
                int age = Integer.parseInt(data[2].trim());
                MaritalStatus status = MaritalStatus.valueOf(data[3].trim().toUpperCase());
                HDBOfficer officer = new HDBOfficer(nric, data[4].trim(), data[0].trim(), age, status);
                if (users.containsKey(nric) && !(users.get(nric) instanceof HDBOfficer)) {
                     System.out.println("Info: User " + nric + " found in both Applicant and Officer lists. Using Officer role.");
                } else if (users.containsKey(nric)) {
                     System.err.println("Duplicate NRIC found in OfficerList: " + nric + ". Skipping duplicate.");
                     return;
                }
                users.put(nric, officer);
            } catch (Exception e) {
                System.err.println("Error parsing officer data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });

        readCsv(MANAGER_LIST_FILE, MANAGER_HEADER.length).forEach(data -> {
            try {
                String nric = data[1].trim();
                 if (!isValidNric(nric)) {
                     System.err.println("Invalid NRIC format in ManagerList: " + nric + ". Skipping.");
                     return;
                 }
                int age = Integer.parseInt(data[2].trim());
                MaritalStatus status = MaritalStatus.valueOf(data[3].trim().toUpperCase());
                HDBManager manager = new HDBManager(nric, data[4].trim(), data[0].trim(), age, status);
                if (users.containsKey(nric) && !(users.get(nric) instanceof HDBManager)) {
                     System.out.println("Info: User " + nric + " found in other lists. Using Manager role.");
                } else if (users.containsKey(nric)) {
                     System.err.println("Duplicate NRIC found in ManagerList: " + nric + ". Skipping duplicate.");
                     return;
                }
                users.put(nric, manager);
            } catch (Exception e) {
                System.err.println("Error parsing manager data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });

        System.out.println("Loaded " + users.size() + " unique users.");
        return users;
    }

     public static List<Project> loadProjects(Map<String, User> users) {
        List<Project> projects = new ArrayList<>();
        Set<String> projectNames = new HashSet<>();

        readCsv(PROJECT_FILE, PROJECT_HEADER.length).forEach(data -> {
            try {
                String projectName = data[0].trim();
                if (projectName.isEmpty() || !projectNames.add(projectName.toLowerCase())) {
                     if (!projectName.isEmpty()) System.err.println("Skipping duplicate project name: " + projectName);
                    return;
                }

                String neighborhood = data[1].trim();
                Map<FlatType, FlatTypeDetails> flatTypes = new HashMap<>();

                if (data[2] != null && !data[2].trim().isEmpty()) {
                    FlatType type1 = FlatType.fromString(data[2].trim());
                    if (type1 != null) {
                        int units1 = Integer.parseInt(data[3].trim());
                        double price1 = Double.parseDouble(data[4].trim());
                        flatTypes.put(type1, new FlatTypeDetails(units1, units1, price1));
                    } else {
                         System.err.println("Warning: Unknown flat type '" + data[2] + "' in project '" + projectName + "'. Skipping type.");
                    }
                }

                 if (data[5] != null && !data[5].trim().isEmpty()) {
                    FlatType type2 = FlatType.fromString(data[5].trim());
                     if (type2 != null) {
                        int units2 = Integer.parseInt(data[6].trim());
                        double price2 = Double.parseDouble(data[7].trim());
                        flatTypes.put(type2, new FlatTypeDetails(units2, units2, price2));
                     } else {
                          System.err.println("Warning: Unknown flat type '" + data[5] + "' in project '" + projectName + "'. Skipping type.");
                     }
                }

                Date openingDate = parseDate(data[8].trim());
                Date closingDate = parseDate(data[9].trim());
                String managerNric = data[10].trim();
                int officerSlots = Integer.parseInt(data[11].trim());

                List<String> officers = parseListString(data[12]);

                boolean visibility = false;
                if (data.length > 13 && data[13] != null) {
                     String visibilityStr = data[13].trim();
                     if (visibilityStr.equals("1")) {
                         visibility = true;
                     } else if (!visibilityStr.equals("0") && !visibilityStr.isEmpty()) {
                         System.err.println("Warning: Invalid visibility value '" + visibilityStr + "' for project '" + projectName + "'. Assuming false.");
                     }
                }


                if (!users.containsKey(managerNric) || !(users.get(managerNric) instanceof HDBManager)) {
                    System.err.println("Warning: Project '" + projectName + "' has invalid or non-manager NRIC: " + managerNric + ". Skipping project.");
                    projectNames.remove(projectName.toLowerCase());
                    return;
                }
                 if (openingDate == null || closingDate == null || closingDate.before(openingDate)) {
                     System.err.println("Warning: Project '" + projectName + "' has invalid application dates (Open: " + data[8] + ", Close: " + data[9] + "). Skipping project.");
                     projectNames.remove(projectName.toLowerCase());
                     return;
                 }
                 List<String> validOfficers = new ArrayList<>();
                 List<String> invalidOfficers = new ArrayList<>();
                 for (String nric : officers) {
                     if (users.containsKey(nric) && users.get(nric) instanceof HDBOfficer) {
                         validOfficers.add(nric);
                     } else {
                         invalidOfficers.add(nric);
                     }
                 }
                 if (!invalidOfficers.isEmpty()) {
                     System.err.println("Warning: Project '" + projectName + "' contains invalid or non-officer NRICs in its officer list: " + invalidOfficers + ". Only valid officers retained.");
                 }
                 if (validOfficers.size() > officerSlots) {
                      System.err.println("Warning: Project '" + projectName + "' has more approved officers ("+validOfficers.size()+") than slots ("+officerSlots+"). Check data. Using officer list as is.");
                 }


                Project project = new Project(projectName, neighborhood, flatTypes, openingDate, closingDate, managerNric, officerSlots, validOfficers, visibility);
                projects.add(project);

            } catch (NumberFormatException e) {
                System.err.println("Error parsing number in project data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            } catch (IllegalArgumentException e) {
                System.err.println("Error parsing enum/data in project data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            } catch (Exception e) {
                 System.err.println("Unexpected error parsing project data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
                 e.printStackTrace();
            }
        });

        System.out.println("Loaded " + projects.size() + " projects.");
        return projects;
    }

    public static Map<String, BTOApplication> loadApplications(List<Project> projects) {
        Map<String, BTOApplication> applications = new HashMap<>();
        Map<Project, Map<FlatType, Integer>> bookedCounts = new HashMap<>();

        readCsv(APPLICATION_FILE, APPLICATION_HEADER.length).forEach(data -> {
            try {
                String appId = data[0].trim();
                if (appId.isEmpty() || applications.containsKey(appId)) {
                     if (!appId.isEmpty()) System.err.println("Skipping duplicate application ID: " + appId);
                    return;
                }
                String applicantNric = data[1].trim();
                String projectName = data[2].trim();
                FlatType flatType = FlatType.fromString(data[3].trim());
                ApplicationStatus status = ApplicationStatus.valueOf(data[4].trim().toUpperCase());
                Date appDate = parseDate(data[5].trim());

                if (appDate == null) {
                     System.err.println("Skipping application with invalid date: " + appId);
                     return;
                }
                 if (flatType == null && (status == ApplicationStatus.BOOKED || status == ApplicationStatus.SUCCESSFUL || status == ApplicationStatus.PENDING_WITHDRAWAL)) {
                     System.err.println("Warning: Application " + appId + " is " + status + " but has invalid/missing flat type '" + data[3] + "'. Status might be inconsistent.");
                 }
                 if (status == ApplicationStatus.PENDING_WITHDRAWAL) {
                      System.out.println("Info: Application " + appId + " loaded with PENDING_WITHDRAWAL status.");
                 }


                BTOApplication application = new BTOApplication(appId, applicantNric, projectName, flatType, status, appDate);
                applications.put(application.getApplicationId(), application);

                if (status == ApplicationStatus.BOOKED && flatType != null) {
                    Project project = projects.stream()
                                            .filter(p -> p.getProjectName().equalsIgnoreCase(projectName))
                                            .findFirst().orElse(null);
                    if (project != null) {
                        bookedCounts.computeIfAbsent(project, _ -> new HashMap<>())
                                    .merge(flatType, 1, Integer::sum);
                    } else {
                         System.err.println("Warning: Booked application " + appId + " refers to non-existent project '" + projectName + "'. Unit count cannot be adjusted.");
                    }
                }

            } catch (IllegalArgumentException e) {
                 System.err.println("Error parsing enum/data in application data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            } catch (Exception e) {
                System.err.println("Error parsing application data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });

        bookedCounts.forEach((project, typeCounts) -> {
            typeCounts.forEach((type, count) -> {
                FlatTypeDetails details = project.getMutableFlatTypeDetails(type);
                if (details != null) {
                    int initialAvailable = details.getTotalUnits();
                    int finalAvailable = Math.max(0, initialAvailable - count);
                    if (finalAvailable != details.getAvailableUnits()) {
                         details.setAvailableUnits(finalAvailable);
                    }
                     if (count > details.getTotalUnits()) {
                         System.err.println("Error: More flats booked (" + count + ") than total units (" + details.getTotalUnits() + ") for " + project.getProjectName() + "/" + type.getDisplayName() + ". Available units set to 0.");
                     }
                } else {
                     System.err.println("Warning: Trying to adjust units for non-existent flat type " + type.getDisplayName() + " in project " + project.getProjectName());
                }
            });
        });


        System.out.println("Loaded " + applications.size() + " applications.");
        return applications;
    }

    public static List<Enquiry> loadEnquiries() {
        List<Enquiry> enquiries = new ArrayList<>();
        Set<String> enquiryIds = new HashSet<>();

        readCsv(ENQUIRY_FILE, ENQUIRY_HEADER.length).forEach(data -> {
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
                Date enqDate = parseDate(data[6].trim());
                Date replyDate = parseDate(data[7].trim());

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

     public static Map<String, OfficerRegistration> loadOfficerRegistrations(Map<String, User> users, List<Project> projects) {
        Map<String, OfficerRegistration> registrations = new HashMap<>();

        readCsv(OFFICER_REGISTRATION_FILE, OFFICER_REGISTRATION_HEADER.length).forEach(data -> {
            try {
                String regId = data[0].trim();
                 if (regId.isEmpty() || registrations.containsKey(regId)) {
                     if (!regId.isEmpty()) System.err.println("Skipping duplicate registration ID: " + regId);
                    return;
                 }
                String officerNric = data[1].trim();
                String projectName = data[2].trim();
                OfficerRegistrationStatus status = OfficerRegistrationStatus.valueOf(data[3].trim().toUpperCase());
                Date regDate = parseDate(data[4].trim());

                 if (regDate == null) {
                     System.err.println("Skipping registration with invalid date: " + regId);
                     return;
                 }

                 if (!users.containsKey(officerNric) || !(users.get(officerNric) instanceof HDBOfficer)) {
                     System.err.println("Warning: Registration " + regId + " refers to invalid or non-officer NRIC: " + officerNric + ". Skipping registration.");
                     return;
                 }
                 boolean projectExists = projects.stream().anyMatch(p -> p.getProjectName().equalsIgnoreCase(projectName));
                 if (!projectExists) {
                      System.err.println("Warning: Registration " + regId + " refers to non-existent project: " + projectName + ". Skipping registration.");
                      return;
                 }


                OfficerRegistration registration = new OfficerRegistration(regId, officerNric, projectName, status, regDate);
                registrations.put(registration.getRegistrationId(), registration);
            } catch (IllegalArgumentException e) {
                 System.err.println("Error parsing enum/data in officer registration data: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            } catch (Exception e) {
                System.err.println("Error parsing officer registration data line: " + String.join(DELIMITER, data) + " - " + e.getMessage());
            }
        });
        System.out.println("Loaded " + registrations.size() + " officer registrations.");
        return registrations;
    }


    public static void synchronizeData(Map<String, User> users, List<Project> projects, Map<String, BTOApplication> applications, Map<String, OfficerRegistration> officerRegistrations) {
        System.out.println("Synchronizing loaded data...");
        boolean registrationsModified = false;

        users.values().stream()
             .filter(u -> u instanceof Applicant)
             .map(u -> (Applicant) u)
             .forEach(applicant -> {
                 BTOApplication relevantApp = applications.values().stream()
                     .filter(app -> app.getApplicantNric().equals(applicant.getNric()))
                     .max(Comparator.comparing(BTOApplication::getStatus, Comparator.comparingInt(s -> {
                         switch (s) {
                             case BOOKED: return 6;
                             case SUCCESSFUL: return 5;
                             case PENDING_WITHDRAWAL: return 4;
                             case PENDING: return 3;
                             case WITHDRAWN: return 2;
                             case UNSUCCESSFUL: return 1;
                             default: return 0;
                         }
                     })).thenComparing(BTOApplication::getApplicationDate).reversed())
                     .orElse(null);

                 if (relevantApp != null) {
                     applicant.setAppliedProjectName(relevantApp.getProjectName());
                     applicant.setApplicationStatus(relevantApp.getStatus());
                     if (relevantApp.getStatus() == ApplicationStatus.BOOKED) {
                         applicant.setBookedFlatType(relevantApp.getFlatTypeApplied());
                     } else {
                         applicant.setBookedFlatType(null);
                     }
                 } else {
                     applicant.clearApplicationState();
                 }
             });

        for (Project project : projects) {
            List<String> approvedNrics = new ArrayList<>(project.getApprovedOfficerNrics());

            for (String officerNric : approvedNrics) {
                User user = users.get(officerNric);
                if (!(user instanceof HDBOfficer)) {
                    System.err.println("Data Sync Warning: NRIC " + officerNric + " in project '" + project.getProjectName() + "' approved list is not a valid HDB Officer. Consider removing from project CSV.");
                    continue;
                }

                String expectedRegId = officerNric + "_REG_" + project.getProjectName();
                OfficerRegistration existingReg = officerRegistrations.get(expectedRegId);

                if (existingReg == null || existingReg.getStatus() != OfficerRegistrationStatus.APPROVED) {
                    System.out.println("Info: Auto-creating/updating APPROVED registration for Officer " + officerNric + " for Project '" + project.getProjectName() + "' based on project list.");

                    Date placeholderDate = project.getApplicationOpeningDate() != null ? project.getApplicationOpeningDate() : new Date(0);

                    OfficerRegistration syncReg = new OfficerRegistration(expectedRegId, officerNric, project.getProjectName(), OfficerRegistrationStatus.APPROVED, placeholderDate);
                    officerRegistrations.put(syncReg.getRegistrationId(), syncReg);
                    registrationsModified = true;
                }
            }
        }

        for (OfficerRegistration reg : officerRegistrations.values()) {
            if (reg.getStatus() == OfficerRegistrationStatus.APPROVED) {
                Project project = projects.stream()
                                        .filter(p -> p.getProjectName().equals(reg.getProjectName()))
                                        .findFirst().orElse(null);
                if (project == null) {
                    System.err.println("Data Sync Warning: Approved registration " + reg.getRegistrationId() + " refers to a non-existent project '" + reg.getProjectName() + "'. Consider removing registration.");
                } else if (!project.getApprovedOfficerNrics().contains(reg.getOfficerNric())) {
                    System.err.println("Data Sync Warning: Approved registration " + reg.getRegistrationId() + " exists, but officer " + reg.getOfficerNric() + " is NOT in project '" + project.getProjectName() + "' approved list. Registration status might be outdated or project list incorrect.");
                }
            }
        }



        if (registrationsModified) {
            System.out.println("Saving updated officer registrations due to synchronization...");
            saveOfficerRegistrations(officerRegistrations);
        }

        System.out.println("Data synchronization complete.");
    }



    public static void saveAllData(Map<String, User> users, List<Project> projects, Map<String, BTOApplication> applications, List<Enquiry> enquiries, Map<String, OfficerRegistration> officerRegistrations) {
        System.out.println("Saving all data...");
        saveUsers(users);
        saveProjects(projects);
        saveApplications(applications);
        saveEnquiries(enquiries);
        saveOfficerRegistrations(officerRegistrations);
        System.out.println("All data saved.");
    }

    public static void saveUsers(Map<String, User> users) {
        List<String[]> applicantData = new ArrayList<>();
        List<String[]> officerData = new ArrayList<>();
        List<String[]> managerData = new ArrayList<>();

        applicantData.add(APPLICANT_HEADER);
        officerData.add(OFFICER_HEADER);
        managerData.add(MANAGER_HEADER);

        users.values().forEach(user -> {
            String[] userData = {
                user.getName(),
                user.getNric(),
                String.valueOf(user.getAge()),
                user.getMaritalStatus().name(),
                user.getPassword()
            };
            switch (user.getRole()) {
                case HDB_MANAGER: managerData.add(userData); break;
                case HDB_OFFICER: officerData.add(userData); break;
                case APPLICANT: applicantData.add(userData); break;
            }
        });

        writeCsv(APPLICANT_LIST_FILE, applicantData);
        writeCsv(OFFICER_LIST_FILE, officerData);
        writeCsv(MANAGER_LIST_FILE, managerData);
        System.out.println("Saved users.");
    }

    public static void saveProjects(List<Project> projects) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(PROJECT_HEADER);

        projects.forEach(project -> {
            String[] data = new String[PROJECT_HEADER.length];
            data[0] = project.getProjectName();
            data[1] = project.getNeighborhood();

            FlatTypeDetails twoRoomDetails = project.getFlatTypeDetails(FlatType.TWO_ROOM);
            FlatTypeDetails threeRoomDetails = project.getFlatTypeDetails(FlatType.THREE_ROOM);

            if (twoRoomDetails != null) {
                data[2] = FlatType.TWO_ROOM.getDisplayName();
                data[3] = String.valueOf(twoRoomDetails.getTotalUnits());
                data[4] = String.valueOf(twoRoomDetails.getSellingPrice());
            } else {
                 data[2] = ""; data[3] = "0"; data[4] = "0";
            }

            if (threeRoomDetails != null) {
                data[5] = FlatType.THREE_ROOM.getDisplayName();
                data[6] = String.valueOf(threeRoomDetails.getTotalUnits());
                data[7] = String.valueOf(threeRoomDetails.getSellingPrice());
            } else {
                 data[5] = ""; data[6] = "0"; data[7] = "0";
            }

            data[8] = formatDate(project.getApplicationOpeningDate());
            data[9] = formatDate(project.getApplicationClosingDate());
            data[10] = project.getManagerNric();
            data[11] = String.valueOf(project.getMaxOfficerSlots());
            String officers = String.join(LIST_DELIMITER, project.getApprovedOfficerNrics());
            data[12] = officers;

            data[13] = project.isVisible() ? "1" : "0";

            dataList.add(data);
        });
        writeCsv(PROJECT_FILE, dataList);
        System.out.println("Saved projects.");
    }

    public static void saveApplications(Map<String, BTOApplication> applications) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(APPLICATION_HEADER);
        applications.values().stream()
            .sorted(Comparator.comparing(BTOApplication::getApplicationId))
            .forEach(app -> {
                dataList.add(new String[]{
                    app.getApplicationId(),
                    app.getApplicantNric(),
                    app.getProjectName(),
                    app.getFlatTypeApplied() == null ? "" : app.getFlatTypeApplied().name(),
                    app.getStatus().name(),
                    formatDate(app.getApplicationDate())
                });
            });
        writeCsv(APPLICATION_FILE, dataList);
        System.out.println("Saved applications.");
    }

    public static void saveEnquiries(List<Enquiry> enquiries) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(ENQUIRY_HEADER);
        enquiries.stream()
            .sorted(Comparator.comparing(Enquiry::getEnquiryId))
            .forEach(enq -> {
                dataList.add(new String[]{
                    enq.getEnquiryId(),
                    enq.getApplicantNric(),
                    enq.getProjectName(),
                    enq.getEnquiryText(),
                    enq.getReplyText() == null ? "" : enq.getReplyText(),
                    enq.getRepliedByNric() == null ? "" : enq.getRepliedByNric(),
                    formatDate(enq.getEnquiryDate()),
                    formatDate(enq.getReplyDate())
                });
            });
        writeCsv(ENQUIRY_FILE, dataList);
        System.out.println("Saved enquiries.");
    }

     public static void saveOfficerRegistrations(Map<String, OfficerRegistration> registrations) {
        List<String[]> dataList = new ArrayList<>();
        dataList.add(OFFICER_REGISTRATION_HEADER);
        registrations.values().stream()
            .sorted(Comparator.comparing(OfficerRegistration::getRegistrationId))
            .forEach(reg -> {
                dataList.add(new String[]{
                    reg.getRegistrationId(),
                    reg.getOfficerNric(),
                    reg.getProjectName(),
                    reg.getStatus().name(),
                    formatDate(reg.getRegistrationDate())
                });
            });
        writeCsv(OFFICER_REGISTRATION_FILE, dataList);
        System.out.println("Saved officer registrations.");
    }


    private static List<String[]> readCsv(String filename, int expectedColumns) {
        List<String[]> data = new ArrayList<>();
        Path path = Paths.get(filename);

        if (!Files.exists(path)) {
            System.err.println("Warning: File not found - " + filename + ". Attempting to create.");
            try {
                Path parent = path.getParent();
                if (parent != null) {
                    Files.createDirectories(parent);
                }
                Files.createFile(path);
                String[] header = getHeaderForFile(filename);
                if (header != null) {
                    writeCsv(filename, Collections.singletonList(header));
                    System.out.println("Created new file with header: " + filename);
                } else {
                     System.err.println("Could not determine header for new file: " + filename);
                }
            } catch (IOException e) {
                System.err.println("FATAL: Error creating file: " + filename + " - " + e.getMessage() + ". Application might not function correctly.");
            }
            return data;
        }

        try (BufferedReader br = Files.newBufferedReader(path)) {
            String line;
            boolean isFirstLine = true;
            int lineNumber = 0;
            while ((line = br.readLine()) != null) {
                lineNumber++;
                if (isFirstLine || line.trim().isEmpty()) {
                    isFirstLine = false;
                    continue;
                }

                String[] values = line.split(DELIMITER + "(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", -1);

                for (int i = 0; i < values.length; i++) {
                    values[i] = values[i].trim();
                    if (values[i].startsWith("\"") && values[i].endsWith("\"")) {
                        values[i] = values[i].substring(1, values[i].length() - 1).replace("\"\"", "\"");
                    }
                }

                if (values.length < expectedColumns && filename.equals(PROJECT_FILE) && values.length == expectedColumns -1) {
                     String[] paddedValues = Arrays.copyOf(values, expectedColumns);
                     paddedValues[expectedColumns - 1] = "0";
                     values = paddedValues;
                     System.out.println("Info: Line " + lineNumber + " in " + filename + " seems to be missing the 'Visibility' column. Assuming '0' (Off).");
                } else if (values.length != expectedColumns) {
                     System.err.println("Warning: Malformed line " + lineNumber + " in " + filename + ". Expected " + expectedColumns + " columns, found " + values.length + ". Skipping line: " + line);
                     continue;
                }

                data.add(values);
            }
        } catch (IOException e) {
            System.err.println("FATAL: Error reading file: " + filename + " - " + e.getMessage());
        }
        return data;
    }

    private static void writeCsv(String filename, List<String[]> data) {
        Path path = Paths.get(filename);
        try {
             Path parent = path.getParent();
             if (parent != null) {
                 Files.createDirectories(parent);
             }

             try (BufferedWriter bw = Files.newBufferedWriter(path, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING)) {
                for (String[] row : data) {
                    String line = Arrays.stream(row)
                                        .map(DataService::escapeCsvField)
                                        .collect(Collectors.joining(DELIMITER));
                    bw.write(line);
                    bw.newLine();
                }
            }
        } catch (IOException e) {
            System.err.println("Error writing file: " + filename + " - " + e.getMessage());
        }
    }

    private static String[] getHeaderForFile(String filename) {
        Path p = Paths.get(filename);
        String baseName = p.getFileName().toString();

        if (baseName.equals(APPLICANT_LIST_FILE)) return APPLICANT_HEADER;
        if (baseName.equals(OFFICER_LIST_FILE)) return OFFICER_HEADER;
        if (baseName.equals(MANAGER_LIST_FILE)) return MANAGER_HEADER;
        if (baseName.equals(PROJECT_FILE)) return PROJECT_HEADER;
        if (baseName.equals(APPLICATION_FILE)) return APPLICATION_HEADER;
        if (baseName.equals(ENQUIRY_FILE)) return ENQUIRY_HEADER;
        if (baseName.equals(OFFICER_REGISTRATION_FILE)) return OFFICER_REGISTRATION_HEADER;
        return null;
    }

    private static String escapeCsvField(String field) {
        if (field == null) return "";
        if (field.contains(DELIMITER) || field.contains("\"") || field.contains(LIST_DELIMITER) || field.contains("\n") || field.contains("\r")) {
            return "\"" + field.replace("\"", "\"\"") + "\"";
        }
        return field;
    }

    public static Date parseDate(String dateString) {
        if (dateString == null || dateString.trim().isEmpty() || dateString.trim().equalsIgnoreCase("null")) {
            return null;
        }
        try {
            DATE_FORMAT.setLenient(false);
            return DATE_FORMAT.parse(dateString.trim());
        } catch (ParseException e) {
            System.err.println("Warning: Invalid date format encountered: '" + dateString + "'. Expected yyyy-MM-dd.");
            return null;
        }
    }

    public static String formatDate(Date date) {
        if (date == null) {
            return "";
        }
        DATE_FORMAT.setLenient(false);
        return DATE_FORMAT.format(date);
    }

    private static List<String> parseListString(String listString) {
        if (listString == null || listString.trim().isEmpty()) {
            return new ArrayList<>();
        }
        String effectiveList = listString.trim();
        if (effectiveList.startsWith("\"") && effectiveList.endsWith("\"")) {
            effectiveList = effectiveList.substring(1, effectiveList.length() - 1).replace("\"\"", "\"");
        }
        return Arrays.stream(effectiveList.split(LIST_DELIMITER))
                     .map(String::trim)
                     .filter(s -> !s.isEmpty())
                     .collect(Collectors.toList());
    }


    public static boolean isValidNric(String nric) {
        if (nric == null) return false;
        return NRIC_PATTERN.matcher(nric.trim().toUpperCase()).matches();
    }

    public static Date getCurrentDate() {
        return new Date();
    }
}
