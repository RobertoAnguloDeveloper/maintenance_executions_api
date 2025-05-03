from typing import Dict, Tuple, Optional, Any
from app.services.report_service import ReportService
from app.models import User
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
                - MIME type, or None on error.
                - Error message, or None on success.
        """
        logger.info(f"Generating report for user {user.username} with params: {report_params}")
        try:
            # Call the service for report generation
            buffer, filename, mime_type, error = ReportService.generate_report(report_params, user)

            # Handle potential errors from the service
            if error:
                logger.error(f"Report generation failed for user {user.username}: {error}")
                # Return None for buffer, filename, mime_type and the error message
                return None, None, None, error

            # Validate return values
            if not buffer or not filename or not mime_type:
                error_msg = "Report service returned incomplete results"
                logger.error(f"{error_msg} for user {user.username}")
                return None, None, None, error_msg

            # Log success and return all results
            logger.info(f"Report '{filename}' generated successfully for user {user.username}")
            return buffer, filename, mime_type, None

        except Exception as e:
            # Catch unexpected errors during controller execution
            logger.exception(f"Unexpected error in ReportController for user {user.username}: {e}")
            # Return None for buffer, filename, mime_type and a generic error message
            return None, None, None, f"An unexpected error occurred while generating the report: {str(e)}"
    
    @staticmethod
    def get_database_schema(user: User) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Retrieves database schema information by calling the ReportService.
        
        Args:
            user (User): The user requesting the schema information.
            
        Returns:
            Tuple[Optional[Dict[str, Any]], Optional[str]]:
                - Dictionary containing schema data, or None on error.
                - Error message, or None on success.
        """
        logger.info(f"Retrieving database schema for user {user.username}")
        try:
            # Call the schema service method from ReportService
            schema_data, error = ReportService.get_database_schema()
            
            if error:
                logger.error(f"Schema retrieval failed: {error}")
                return None, error
                
            if not schema_data:
                error_msg = "Schema service returned empty results"
                logger.error(error_msg)
                return None, error_msg
                
            logger.info(f"Database schema retrieved successfully")
            return schema_data, None
            
        except Exception as e:
            logger.exception(f"Unexpected error retrieving database schema: {e}")
            return None, f"An unexpected error occurred while retrieving database schema: {str(e)}"