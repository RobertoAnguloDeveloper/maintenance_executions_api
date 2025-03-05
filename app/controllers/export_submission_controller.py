# app/controllers/export_submission_controller.py

from typing import Dict, Optional, Tuple
from flask import current_app
from app.services.export_submission_service import ExportSubmissionService
from app.services.form_submission_service import FormSubmissionService
from app.utils.permission_manager import RoleType
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
                
            # Access control
            if user_role != RoleType.ADMIN:
                if user_role in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    if submission.form.creator.environment_id != current_user.environment_id:
                        return None, None, "Unauthorized access"
                elif submission.submitted_by != current_user:
                    return None, None, "Unauthorized access"
            
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