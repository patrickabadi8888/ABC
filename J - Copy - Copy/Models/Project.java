package Models;

import Enums.FlatType;

import java.util.ArrayList;
import java.util.Calendar;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class Project {
    private String projectName;
    private String neighborhood;
    private Map<FlatType, FlatTypeDetails> flatTypes;
    private Date applicationOpeningDate;
    private Date applicationClosingDate;
    private final String managerNric;
    private int maxOfficerSlots;
    private final List<String> approvedOfficerNrics;
    private boolean visibility;

    public Project(String projectName, String neighborhood, Map<FlatType, FlatTypeDetails> flatTypes,
                   Date applicationOpeningDate, Date applicationClosingDate, String managerNric,
                   int maxOfficerSlots, List<String> approvedOfficerNrics, boolean visibility) {
        if (projectName == null || projectName.trim().isEmpty() || neighborhood == null ||
            flatTypes == null || applicationOpeningDate == null || applicationClosingDate == null ||
            managerNric == null || maxOfficerSlots < 0) {
            throw new IllegalArgumentException("Invalid project parameters");
        }
        if (applicationClosingDate.before(applicationOpeningDate)) {
             throw new IllegalArgumentException("Project closing date cannot be before opening date.");
        }
        this.projectName = projectName;
        this.neighborhood = neighborhood;
        this.flatTypes = new HashMap<>(flatTypes);
        this.applicationOpeningDate = applicationOpeningDate;
        this.applicationClosingDate = applicationClosingDate;
        this.managerNric = managerNric;
        this.maxOfficerSlots = maxOfficerSlots;
        this.approvedOfficerNrics = new ArrayList<>(approvedOfficerNrics != null ? approvedOfficerNrics : Collections.emptyList());
        this.visibility = visibility;
    }

    public String getProjectName() { return projectName; }
    public String getNeighborhood() { return neighborhood; }
    public Map<FlatType, FlatTypeDetails> getFlatTypes() { return Collections.unmodifiableMap(flatTypes); }
    public Date getApplicationOpeningDate() { return applicationOpeningDate; }
    public Date getApplicationClosingDate() { return applicationClosingDate; }
    public String getManagerNric() { return managerNric; }
    public int getMaxOfficerSlots() { return maxOfficerSlots; }
    public List<String> getApprovedOfficerNrics() { return Collections.unmodifiableList(approvedOfficerNrics); }
    public boolean isVisible() { return visibility; }
    public int getRemainingOfficerSlots() { return Math.max(0, maxOfficerSlots - approvedOfficerNrics.size()); }

    public void setProjectName(String projectName) {
        if (projectName != null && !projectName.trim().isEmpty()) {
            this.projectName = projectName.trim();
        }
    }
    public void setNeighborhood(String neighborhood) {
         if (neighborhood != null) {
            this.neighborhood = neighborhood;
         }
    }
    public void setFlatTypes(Map<FlatType, FlatTypeDetails> flatTypes) {
        if (flatTypes != null) {
            this.flatTypes = new HashMap<>(flatTypes);
        }
    }
    public void setApplicationOpeningDate(Date applicationOpeningDate) {
        if (applicationOpeningDate != null) {
            this.applicationOpeningDate = applicationOpeningDate;
        }
    }
    public void setApplicationClosingDate(Date applicationClosingDate) {
         if (applicationClosingDate != null && (this.applicationOpeningDate == null || !applicationClosingDate.before(this.applicationOpeningDate))) {
            this.applicationClosingDate = applicationClosingDate;
         } else if (applicationClosingDate != null) {
             System.err.println("Warning: Closing date cannot be before opening date. Not updated.");
         }
    }
    public void setMaxOfficerSlots(int maxOfficerSlots) {
        if (maxOfficerSlots >= this.approvedOfficerNrics.size() && maxOfficerSlots >= 0) {
            this.maxOfficerSlots = maxOfficerSlots;
        } else {
             System.err.println("Warning: Cannot set max officer slots ("+ maxOfficerSlots +") below current approved count (" + this.approvedOfficerNrics.size() + "). Value not changed.");
        }
    }
    public void setVisibility(boolean visibility) { this.visibility = visibility; }

    public boolean addApprovedOfficer(String officerNric) {
        if (officerNric != null && getRemainingOfficerSlots() > 0 && !approvedOfficerNrics.contains(officerNric)) {
            approvedOfficerNrics.add(officerNric);
            return true;
        }
        return false;
    }

    public boolean removeApprovedOfficer(String officerNric) {
        boolean removed = approvedOfficerNrics.remove(officerNric);
        return removed;
    }

    public boolean isApplicationPeriodActive(Date currentDate) {
        if (currentDate == null || applicationOpeningDate == null || applicationClosingDate == null) return false;
        Calendar cal = Calendar.getInstance();
        cal.setTime(applicationClosingDate);
        cal.add(Calendar.DATE, 1);
        Date endOfDayClosing = cal.getTime();

        return !currentDate.before(applicationOpeningDate) && currentDate.before(endOfDayClosing);
    }

    public boolean isActive(Date currentDate) {
        return this.isVisible() && this.isApplicationPeriodActive(currentDate);
    }

    public boolean isApplicationPeriodExpired(Date currentDate) {
         if (currentDate == null || applicationClosingDate == null) return false;
        Calendar cal = Calendar.getInstance();
        cal.setTime(applicationClosingDate);
        cal.add(Calendar.DATE, 1);
        Date endOfDayClosing = cal.getTime();
        return currentDate.after(endOfDayClosing);
    }


    public FlatTypeDetails getFlatTypeDetails(FlatType type) {
        return flatTypes.get(type);
    }

    public FlatTypeDetails getMutableFlatTypeDetails(FlatType type) {
        return flatTypes.get(type);
    }
}
