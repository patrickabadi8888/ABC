from abc import ABC, abstractmethod
from typing import List, Dict, Optional

class IReportService(ABC):
    """Interface for report generation services."""

    @abstractmethod
    def generate_booking_report_data(self, filter_project_name: Optional[str] = None,
                                     filter_flat_type_str: Optional[str] = None,
                                     filter_marital: Optional[str] = None) -> List[Dict]:
        """Generates data for the booking report based on filters."""
        pass