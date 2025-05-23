# app/services/report/report_formatter.py
from typing import Dict, Any, List, Optional, BinaryIO
from abc import ABC, abstractmethod
from io import BytesIO
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ReportFormatter(ABC):
    """Base abstract class for all report formatters"""
    
    def __init__(self, processed_data: Dict[str, Dict[str, Any]], global_params: Dict[str, Any]):
        """
        Initialize formatter with data and parameters
        
        Args:
            processed_data: Dictionary of processed data for each report type
            global_params: Global report parameters
        """
        self.processed_data = processed_data
        self.global_params = global_params
        self.buffer = BytesIO()
        self.report_title = global_params.get("report_title", "Data Analysis Report")
        self.generation_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    @abstractmethod
    def generate(self) -> BytesIO:
        """
        Generate the formatted report
        
        Returns:
            BytesIO buffer with the formatted report
        """
        pass
    
    def handle_error(self, report_type: str, error_message: str) -> None:
        """
        Add error message to the report for the specified report type
        
        Args:
            report_type: Type of report with error
            error_message: Error message to display
        """
        pass  # Implement in subclasses as needed
        
    def get_first_valid_report(self) -> Optional[Dict[str, Any]]:
        """
        Find the first valid report type and result
        
        Returns:
            Dictionary of report data or None if no valid report found
        """
        primary_report_type = None
        primary_result = None
        
        for rt, res in self.processed_data.items():
            if not res.get('error'):
                primary_report_type = rt
                primary_result = res
                logger.info(f"Using {primary_report_type} as primary entity")
                return {
                    'type': primary_report_type,
                    'result': primary_result
                }
                
        logger.warning("No valid report data found")
        return None
    
    def get_all_errors(self) -> str:
        """
        Get a string of all errors from the processed data
        
        Returns:
            String of all errors
        """
        errors = [f"{rt}: {res['error']}" for rt, res in self.processed_data.items() if res.get('error')]
        return "; ".join(errors) if errors else "No specific error details available."