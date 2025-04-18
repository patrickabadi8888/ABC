from typing import List, Dict, Any
from .base_view import BaseView
from utils.input_util import InputUtil # For filter prompts

class ReportView(BaseView):
    """View specific to displaying reports."""

    def display_report(self, title: str, report_data: List[Dict[str, Any]], headers: List[str]):
        """Displays report data in a formatted table."""
        print(f"\n--- {title} ---")
        if not report_data:
            print("No data found for this report.")
            print("-" * (len(title) + 6))
            return

        # Calculate column widths dynamically
        widths = {header: len(header) for header in headers}
        for row in report_data:
            for header in headers:
                value_str = str(row.get(header, '')) # Ensure value exists and is string
                widths[header] = max(widths[header], len(value_str))

        # Print header row
        header_line = " | ".join(f"{header:<{widths[header]}}" for header in headers)
        print(header_line)
        print("-" * len(header_line))

        # Print data rows
        for row in report_data:
            row_line = " | ".join(f"{str(row.get(header, '')):<{widths[header]}}" for header in headers)
            print(row_line)

        # Print footer
        print("-" * len(header_line))
        print(f"Total Records: {len(report_data)}")
        print("-" * (len(title) + 6))

    def prompt_report_filters(self) -> Dict[str, str]:
        """Prompts for filters specific to the booking report."""
        self.display_message("\n--- Generate Booking Report Filters ---", info=True)
        print("(Leave blank for no filter on that field)")
        filters = {}
        try:
            # Get raw input
            marital_raw = self.get_input("Filter by Marital Status (Single/Married)")
            project_raw = self.get_input("Filter by Project Name")
            flat_type_raw = self.get_input("Filter by Flat Type (2/3)")

            # Clean and validate input before returning
            marital = marital_raw.strip().lower()
            if marital in ['single', 'married']:
                filters['filter_marital'] = marital.capitalize()
            elif marital:
                self.display_message("Invalid marital status filter. Ignoring.", warning=True)

            project_name = project_raw.strip()
            if project_name:
                filters['filter_project_name'] = project_name

            flat_type = flat_type_raw.strip()
            if flat_type in ['2', '3']:
                filters['filter_flat_type_str'] = flat_type
            elif flat_type:
                self.display_message("Invalid flat type filter. Ignoring.", warning=True)

            return filters
        except KeyboardInterrupt:
             self.display_message("\nFilter input cancelled.")
             return {} # Return empty filters