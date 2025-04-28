# app/utils/logging_config.py

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
import sys # Import sys for checking stdout/stderr tty

# Regex pattern to detect and remove ANSI escape codes (for colors)
ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class ColorStripFilter(logging.Filter):
    """A logging filter that removes ANSI color codes from log messages."""
    def filter(self, record):
        # Check if the message exists and is a string before attempting to replace
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = ANSI_ESCAPE_PATTERN.sub('', record.msg)
        # Always return True to allow the record to pass through
        return True

# Module-level flag to ensure this setup runs only once per process
_logging_configured = False

def setup_logging():
    """
    Configure logging for the application. Sets up console and rotating file handlers.
    Ensures configuration happens only once per process.

    Returns:
        logging.Logger: The configured logger instance named "app".
    """
    global _logging_configured
    logger_name = "app" # Define a specific name for the application logger

    # If already configured in this specific process, return the existing logger
    if _logging_configured:
        return logging.getLogger(logger_name)

    # --- Basic Setup ---
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True) # Create logs directory if it doesn't exist

    # Define log file naming based on date
    date_format = "%d-%m-%Y"
    current_date = datetime.now().strftime(date_format)
    log_file = log_dir / f'app_{current_date}.log'

    # Define the standard log message format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)

    # --- Configure the Main Application Logger ("app") ---
    app_logger = logging.getLogger(logger_name)
    # Check if handlers have already been added (e.g., by another import)
    if not app_logger.hasHandlers():
         app_logger.setLevel(logging.INFO) # Set the minimum logging level for the app
         # Prevent app logs from propagating to the root logger (avoids duplicate root logs)
         app_logger.propagate = False

         # --- Console Handler (for terminal output) ---
         # Check if running in an interactive terminal before adding console handler
         if sys.stdout.isatty():
             console_handler = logging.StreamHandler(sys.stdout) # Use stdout
             console_handler.setFormatter(formatter)
             # No color stripping for console
             app_logger.addHandler(console_handler)
         else:
             # If not a TTY, maybe skip console logging or log differently
             pass

         # --- Rotating File Handler (for daily log files) ---
         file_handler = TimedRotatingFileHandler(
             filename=log_file,
             when='midnight',  # Rotate logs at midnight
             interval=1,       # Daily rotation
             backupCount=30,   # Keep logs for 30 days
             encoding='utf-8'  # Use UTF-8 encoding
         )
         file_handler.setFormatter(formatter)
         # Use the same date format for rotated file names (e.g., app_27-04-2025.log.2025-04-28)
         file_handler.suffix = "%Y-%m-%d" # Switched to standard ISO format for suffix
         # Add filter to remove color codes before writing to file
         color_filter = ColorStripFilter()
         file_handler.addFilter(color_filter)
         app_logger.addHandler(file_handler)

         # Log initialization message using the app logger itself
         app_logger.info(f"Logging initialized for '{logger_name}' logger. Log file: {log_file}")


    # --- Configure Werkzeug Logger (Flask's internal server) ---
    werkzeug_logger = logging.getLogger('werkzeug')
    if not werkzeug_logger.hasHandlers(): # Configure only if not already done
        werkzeug_logger.setLevel(logging.INFO) # Log standard HTTP requests (INFO level)
        werkzeug_logger.propagate = False # Prevent double logging via root

        # Add app's handlers to Werkzeug logger so requests go to console/file
        # Check if handlers were actually added to app_logger first
        if app_logger.hasHandlers():
            for handler in app_logger.handlers:
                 # Make a copy or create new handlers if necessary to avoid shared state issues
                 # For simplicity here, we reuse, but be mindful in complex scenarios
                 werkzeug_logger.addHandler(handler)
            app_logger.info("Werkzeug logger configured to use app handlers.")


    # --- Configure SQLAlchemy Logger ---
    sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
    if not sqlalchemy_logger.hasHandlers(): # Configure only if not already done
        # Set level (WARNING is common, INFO logs SQL queries)
        sqlalchemy_logger.setLevel(logging.WARNING)
        # Prevent propagation to avoid duplicate logs if root logger is configured
        sqlalchemy_logger.propagate = False
        # Optionally, add app handlers if you want SQL logs in your files/console
        # if app_logger.hasHandlers():
        #     for handler in app_logger.handlers:
        #          sqlalchemy_logger.addHandler(handler)
        app_logger.info("SQLAlchemy logger configured (Level: WARNING).")


    # Mark logging as configured for this process
    _logging_configured = True
    # Return the main application logger instance
    return app_logger

# Optional: Function to get a styled log message (for console logging)
def styled_log(message, style=None):
    """
    Get a styled version of a log message for console output using ANSI codes.
    Styles: 'success', 'error', 'warning', 'info', 'bold'
    """
    styles = {
        'success': '\033[92m',  # Green
        'error': '\033[91m',    # Red
        '422': '\033[91m',    # Red (can use specific codes)
        'warning': '\033[93m',  # Yellow
        'info': '\033[94m',     # Blue
        'bold': '\033[1m',      # Bold
    }
    reset = '\033[0m'          # Reset color to default

    # Apply style only if stdout is a TTY (terminal)
    if style and style in styles and sys.stdout.isatty():
        return f"{styles[style]}{message}{reset}"
    # Return plain message if no style, style not found, or not a TTY
    return message
