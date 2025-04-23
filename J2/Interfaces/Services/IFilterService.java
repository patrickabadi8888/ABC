package Interfaces.Services;

import Enums.FlatType;
import Models.Project;
import java.util.List;

public interface IFilterService {
    void setLocationFilter(String location);
    void setFlatTypeFilter(FlatType flatType);
    String getLocationFilter();
    FlatType getFlatTypeFilter();
    void clearFilters();
    List<Project> applyFilters(List<Project> projects); // Applies current filters to a list
    String getCurrentFilterStatus();
}
