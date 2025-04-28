# app/controllers/report_controller.py

from typing import Dict, Tuple, Optional
from app.services.report_service import ReportService
from app.models import User # Assuming User model is in app.models
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

class ReportController:
    """
    Controller for handling report generation requests.
    """

    @staticmethod
    def generate_custom_report(report_params: dict, user: User) -> Tuple[Optional[BytesIO], Optional[str], Optional[str], Optional[str]]:
        """
        Generates a custom report by calling the ReportService.

        Args:
            report_params (dict): Parameters defining the report.
            user (User): The user requesting the report.

        Returns:
            Tuple[Optional[BytesIO], Optional[str], Optional[str], Optional[str]]:
                - BytesIO buffer with report data, or None on error.
                - Filename, or None on error.
                - MIME type, or None on error. # Added MIME type
                - Error message, or None on success.
        """
        logger.info(f"Generating report for user {user.username} with params: {report_params}")
        try:
            # --- CORRECTED: Unpack all 4 values from the service ---
            buffer, filename, mime_type, error = ReportService.generate_report(report_params, user)

            # Handle potential errors from the service
            if error:
                logger.error(f"Report generation failed for user {user.username}: {error}")
                # Return None for buffer, filename, mime_type and the error message
                return None, None, None, error

            # Log success and return all results
            logger.info(f"Report '{filename}' generated successfully for user {user.username}")
            # --- CORRECTED: Return all 4 values ---
            return buffer, filename, mime_type, None

        except Exception as e:
            # Catch unexpected errors during controller execution
            logger.exception(f"Unexpected error in ReportController for user {user.username}: {e}")
            # Return None for buffer, filename, mime_type and a generic error message
            return None, None, None, "An unexpected error occurred while generating the report."

