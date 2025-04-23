package Services;

import java.util.List;
import java.util.stream.Collectors;

import Enums.FlatType;
import Interfaces.Services.IFilterService;
import Models.Project;

public class FilterService implements IFilterService {

    private String filterLocation = null;
    private FlatType filterFlatType = null;

    @Override
    public void setLocationFilter(String location) {
        this.filterLocation = (location == null || location.trim().isEmpty()) ? null : location.trim();
    }

    @Override
    public void setFlatTypeFilter(FlatType flatType) {
        this.filterFlatType = flatType; // Allow null to clear
    }

    @Override
    public String getLocationFilter() {
        return filterLocation;
    }

    @Override
    public FlatType getFlatTypeFilter() {
        return filterFlatType;
    }

    @Override
    public void clearFilters() {
        this.filterLocation = null;
        this.filterFlatType = null;
        System.out.println("Filters cleared.");
    }

    @Override
    public List<Project> applyFilters(List<Project> projects) {
        if (projects == null) return List.of();

        return projects.stream()
                .filter(p -> filterLocation == null || p.getNeighborhood().equalsIgnoreCase(filterLocation))
                .filter(p -> filterFlatType == null || p.getFlatTypes().containsKey(filterFlatType))
                // Sorting is usually done *after* filtering, where the list is used
                .collect(Collectors.toList());
    }

    @Override
    public String getCurrentFilterStatus() {
         return "Location=" + (filterLocation == null ? "Any" : filterLocation)
                        + ", FlatType=" + (filterFlatType == null ? "Any" : filterFlatType);
    }
}
