# app/controllers/export_submission_controller.py

from typing import Dict, Optional, Tuple
from flask import current_app
from app.services.export_submission_service import ExportSubmissionService
from app.services.form_submission_service import FormSubmissionService
from app.utils.permission_manager import RoleType
from werkzeug.datastructures import FileStorage
import logging

logger = logging.getLogger(__name__)

class ExportSubmissionController:
    @staticmethod
    def export_submission_to_pdf(
        submission_id: int,
        current_user: str = None,
        user_role: str = None
    ) -> Tuple[Optional[bytes], Optional[Dict], Optional[str]]:
        """
        Export a form submission to PDF with authorization checks
        
        Args:
            submission_id: ID of the form submission
            current_user: Username of current user
            user_role: Role of current user
            
        Returns:
            Tuple containing: 
            - PDF bytes or None
            - Metadata dict (for filename, etc.) or None
            - Error message or None
        """
        try:
            # First check if submission exists
            submission = FormSubmissionService.get_submission(submission_id)
            if not submission:
                return None, None, "Submission not found"
                            
            upload_path = current_app.config['UPLOAD_FOLDER']
            
            # Call the service
            pdf_buffer, error = ExportSubmissionService.export_submission_to_pdf(
                submission_id=submission_id,
                upload_path=upload_path,
                include_signatures=True
            )
            
            if error:
                logger.error(f"Error exporting submission {submission_id} to PDF: {error}")
                return None, None, error
                
            # Create metadata for the file
            submission_date = submission.submitted_at.strftime("%Y%m%d")
            form_name = submission.form.title.replace(" ", "_")
            filename = f"{form_name}_submission_{submission_id}_{submission_date}.pdf"
            
            metadata = {
                "filename": filename,
                "mimetype": "application/pdf",
                "submission_id": submission_id,
                "form_title": submission.form.title,
                "submitted_by": submission.submitted_by,
                "submitted_at": submission.submitted_at.isoformat()
            }
            
            return pdf_buffer.getvalue(), metadata, None
            
        except Exception as e:
            logger.error(f"Error in export_submission_to_pdf controller: {str(e)}")
            return None, None, str(e)
        
    @staticmethod
    def export_submission_to_pdf_with_logo(
        submission_id: int,
        current_user: str = None,
        user_role: str = None,
        header_image: FileStorage = None,
        header_opacity: float = 1.0,
        header_size: float = None,
        header_width: float = None,
        header_height: float = None,
        header_alignment: str = "center",
        signatures_size: float = 100,
        signatures_alignment: str = "vertical"
    ) -> Tuple[Optional[bytes], Optional[Dict], Optional[str]]:
        """
        Export a form submission to PDF with authorization checks and header image
        """
        try:
            # First check if submission exists
            submission = FormSubmissionService.get_submission(submission_id)
            if not submission:
                return None, None, "Submission not found"
            
            upload_path = current_app.config['UPLOAD_FOLDER']
            
            # Validate parameters to avoid passing bad values
            try:
                # Convert to float if string
                header_opacity = float(header_opacity) if header_opacity is not None else 1.0
                header_opacity = max(0.0, min(1.0, header_opacity))  # Ensure within range
                
                if header_size is not None:
                    header_size = float(header_size) 
                    
                if header_width is not None:
                    header_width = float(header_width)
                    
                if header_height is not None:
                    header_height = float(header_height)
                    
                signatures_size = float(signatures_size) if signatures_size is not None else 100.0
                
                # Validate alignment values
                if header_alignment not in ["left", "center", "right"]:
                    header_alignment = "center"  # Default to center
                    
                if signatures_alignment not in ["vertical", "horizontal"]:
                    signatures_alignment = "vertical"  # Default to vertical
            except (ValueError, TypeError) as e:
                logger.warning(f"Parameter validation error: {str(e)}")
                # Use defaults instead of failing
                header_opacity = 1.0
                header_size = None
                header_width = None
                header_height = None
                header_alignment = "center"
                signatures_size = 100.0
                signatures_alignment = "vertical"
            
            # Call the service
            pdf_buffer, error = ExportSubmissionService.export_submission_to_pdf(
                submission_id=submission_id,
                upload_path=upload_path,
                include_signatures=True,
                header_image=header_image,
                header_opacity=header_opacity,
                header_size=header_size,
                header_width=header_width,
                header_height=header_height,
                header_alignment=header_alignment,
                signatures_size=signatures_size,
                signatures_alignment=signatures_alignment
            )
            
            if error:
                logger.error(f"Error exporting submission {submission_id} to PDF: {error}")
                return None, None, error
                    
            # Create metadata for the file
            submission_date = submission.submitted_at.strftime("%Y%m%d")
            form_name = submission.form.title.replace(" ", "_")
            filename = f"{form_name}_submission_{submission_id}_{submission_date}.pdf"
            
            metadata = {
                "filename": filename,
                "mimetype": "application/pdf",
                "submission_id": submission_id,
                "form_title": submission.form.title,
                "submitted_by": submission.submitted_by,
                "submitted_at": submission.submitted_at.isoformat()
            }
            
            return pdf_buffer.getvalue(), metadata, None
            
        except Exception as e:
            logger.error(f"Error in export_submission_to_pdf controller: {str(e)}")
            return None, None, f"Internal server error: {str(e)}"