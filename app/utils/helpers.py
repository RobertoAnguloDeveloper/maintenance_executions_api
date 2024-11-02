import re
import uuid

def validate_email(email):
    """Validate an email address."""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def generate_unique_code():
    """
    Generate a unique code (e.g., for verification purposes).
    """
    return str(uuid.uuid4())

def format_date(date_obj, format_str='%Y-%m-%d'):
    """
    Format a date object to a string.
    """
    return date_obj.strftime(format_str)

def parse_date(date_str, format_str='%Y-%m-%d'):
    """
    Parse a date string to a date object.
    """
    from datetime import datetime
    return datetime.strptime(date_str, format_str).date()

def sanitize_input(input_str):
    """
    Sanitize user input to prevent XSS attacks.
    """
    return input_str.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

# Add more utility functions as needed for your application