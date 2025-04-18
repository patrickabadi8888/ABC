from datetime import datetime, date

class DateUtil:
    """Handles date parsing and formatting."""
    DATE_FORMAT = "%Y-%m-%d"

    @staticmethod
    def parse_date(date_str: str | None) -> date | None:
        """Parses a date string into a date object."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, DateUtil.DATE_FORMAT).date()
        except ValueError:
            return None # Indicate parsing failure

    @staticmethod
    def format_date(date_obj: date | None) -> str:
        """Formats a date object into a string."""
        if date_obj is None:
            return ""
        return date_obj.strftime(DateUtil.DATE_FORMAT)

    @staticmethod
    def dates_overlap(start1: date, end1: date, start2: date, end2: date) -> bool:
        """Checks if two date ranges overlap."""
        if not all([start1, end1, start2, end2]):
            # If any date is missing, assume no overlap for safety
            return False
        # Ensure start <= end for comparison
        s1, e1 = min(start1, end1), max(start1, end1)
        s2, e2 = min(start2, end2), max(start2, end2)
        # Overlap occurs if one period starts before the other ends,
        # and ends after the other starts.
        return s1 <= e2 and s2 <= e1