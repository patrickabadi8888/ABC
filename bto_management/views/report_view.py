# views/report_view.py
from .base_view import BaseView
from utils import helpers # For input validation if needed

class ReportView(BaseView):
    """View specific to displaying reports."""

    def display_report(self, title: str, report_data: list[dict], headers: list[str]):
        """
        Displays report data in a formatted table.

        Args:
            title: The title of the report.
            report_data: A list of dictionaries, where each dictionary represents a row
                         and keys correspond to headers.
            headers: A list of strings representing the column headers in the desired order.
        """
        print(f"\n--- {title} ---")
        if not report_data:
            print("(No data found for this report)")
            # Print a bottom separator even if empty
            print("-" * (len(title) + 6))
            return

        # --- Calculate Column Widths ---
        # Initialize widths with header lengths
        widths = {header: len(header) for header in headers}
        # Update widths based on data content
        for row in report_data:
            for header in headers:
                # Get value safely, convert to string, handle potential None
                value_str = str(row.get(header, '')) # Use empty string for missing keys/None
                widths[header] = max(widths[header], len(value_str))

        # --- Print Header ---
        header_line = " | ".join(f"{header:<{widths[header]}}" for header in headers)
        separator_line = "-" * len(header_line)
        print(header_line)
        print(separator_line)

        # --- Print Data Rows ---
        for row in report_data:
            row_values = []
            for header in headers:
                 # Get value safely, convert to string
                 value_str = str(row.get(header, ''))
                 # Format each cell left-aligned within its calculated width
                 row_values.append(f"{value_str:<{widths[header]}}")
            print(" | ".join(row_values))

        # --- Print Footer ---
        print(separator_line)
        print(f"Total Records: {len(report_data)}")
        # Print a bottom separator matching the title width
        print("-" * (len(title) + 6))


    def prompt_booking_report_filters(self) -> dict | None:
        """
        Gathers filter criteria specifically for the booking report.
        Returns a dictionary of filters or None if cancelled.
        """
        self.display_message("--- Generate Booking Report Filters ---", info=True)
        print("(Leave blank for no filter on a criterion)")
        filters = {}
        try:
            # Use simple get_input, validation happens in the service/controller
            filters['filter_marital'] = self.get_input("Filter by Marital Status (e.g., Single, Married)")
            filters['filter_project_name'] = self.get_input("Filter by Project Name (exact match)")
            filters['filter_flat_type_str'] = self.get_input("Filter by Flat Type (2 or 3)")

            # --- Basic Cleaning/Normalization (Optional here, Service should validate) ---
            clean_filters = {}
            marital_input = filters['filter_marital'].strip()
            if marital_input:
                # Capitalize standard inputs, pass others as-is for service validation
                if marital_input.lower() in ['single', 'married']:
                    clean_filters['filter_marital'] = marital_input.capitalize()
                else:
                    # Pass potentially invalid input for service layer to handle/reject
                    clean_filters['filter_marital'] = marital_input

            project_name_input = filters['filter_project_name'].strip()
            if project_name_input:
                 clean_filters['filter_project_name'] = project_name_input

            flat_type_input = filters['filter_flat_type_str'].strip()
            if flat_type_input:
                 # Pass potentially invalid input for service layer validation
                 clean_filters['filter_flat_type_str'] = flat_type_input

            return clean_filters # Return the dictionary of gathered filters

        except KeyboardInterrupt:
            print("\nFilter input cancelled.")
            return None # Indicate cancellation