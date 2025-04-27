# app/utils/logging_config.py

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

# ANSI color codes regex pattern
ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class ColorStripFilter(logging.Filter):
    """Filter to remove ANSI color codes from log records"""
    def filter(self, record):
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = ANSI_ESCAPE_PATTERN.sub('', record.msg)
        return True

def setup_logging():
    """Configure logging for the application with daily log files"""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Format for log filename - just the date part
    date_format = "%d-%m-%Y"
    current_date = datetime.now().strftime(date_format)
    log_file = log_dir / f'app_{current_date}.log'
    
    # Create a formatter for log entries
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Set up the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear any existing handlers to avoid duplication
    if root_logger.handlers:
        root_logger.handlers.clear()
    
    # Console handler - preserve colors
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler - strip colors using our custom filter
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when='midnight',  # Roll over at midnight
        interval=1,       # One day
        backupCount=30,   # Keep 30 days of logs
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%d-%m-%Y"  # Use the same date format for rotated files
    
    # Add color stripping filter to file handler only
    color_filter = ColorStripFilter()
    file_handler.addFilter(color_filter)
    
    root_logger.addHandler(file_handler)
    
    # Set SQLAlchemy logging level
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    # Filter werkzeug logger to strip colors for file logs
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.handlers = []  # Clear default handlers
    
    # Add handlers to werkzeug logger
    werkzeug_console = logging.StreamHandler()
    werkzeug_console.setFormatter(formatter)
    werkzeug_logger.addHandler(werkzeug_console)
    
    werkzeug_file = logging.FileHandler(log_file)
    werkzeug_file.setFormatter(formatter)
    werkzeug_file.addFilter(color_filter)
    werkzeug_logger.addHandler(werkzeug_file)
    
    # Create a named logger for this module
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Current log file: {log_file}")
    
    return logger

# Optional: Function to get a styled log message (for console logging)
def styled_log(message, style=None):
    """
    Get a styled version of a log message for console output.
    Styles: 'success', 'error', 'warning', 'info', 'bold'
    """
    styles = {
        'success': '\033[92m',  # Green
        'error': '\033[91m',    # Red
        'warning': '\033[93m',  # Yellow
        'info': '\033[94m',     # Blue
        'bold': '\033[1m',      # Bold
    }
    reset = '\033[0m'          # Reset to default
    
    if style and style in styles:
        return f"{styles[style]}{message}{reset}"
    return message