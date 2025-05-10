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
    def export_structured_submission_to_pdf(
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
        Export a form submission to PDF with structured organization of tables and dropdowns
        
        Args:
            submission_id: ID of the form submission
            current_user: Username of current user
            user_role: Role of the current user
            header_image: Optional image file for PDF header
            header_opacity: Opacity for header image (0.0 to 1.0)
            header_size: Optional size percentage (keeping aspect ratio)
            header_width: Optional specific width in pixels (ignores aspect ratio if height also provided)
            header_height: Optional specific height in pixels (ignores aspect ratio if width also provided)
            header_alignment: Alignment of the header image (left, center, right)
            signatures_size: Size percentage for signature images (100 = original size)
            signatures_alignment: Layout for signatures (vertical, horizontal)
            
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
            
            # Call the structured PDF export service
            pdf_buffer, error = ExportSubmissionService.export_structured_submission_to_pdf(
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
                logger.error(f"Error exporting structured submission {submission_id} to PDF: {error}")
                return None, None, error
                    
            # Create metadata for the file
            submission_date = submission.submitted_at.strftime("%Y%m%d")
            form_name = submission.form.title.replace(" ", "_")
            filename = f"{form_name}_submission_{submission_id}_{submission_date}_structured.pdf"
            
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
            logger.error(f"Error in export_structured_submission_to_pdf controller: {str(e)}")
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
        signatures_alignment: str = "vertical",
        structured: bool = False  # New parameter
    ) -> Tuple[Optional[bytes], Optional[Dict], Optional[str]]:
        """
        Export a form submission to PDF with header image and optional table structuring
        """
        try:
            # First check if submission exists
            submission = FormSubmissionService.get_submission(submission_id)
            if not submission:
                return None, None, "Submission not found"
            
            upload_path = current_app.config['UPLOAD_FOLDER']
            
            # Call the appropriate service method based on structured parameter
            if structured:
                # Use the structured version (if you implemented the method above)
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
            else:
                # Use the original unstructured version
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
            return None, None, str(e)