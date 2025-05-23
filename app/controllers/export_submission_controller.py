# app/controllers/export_submission_controller.py

from typing import Dict, Optional, Tuple, Any
from flask import current_app
from app.services.export_submission_service import ExportSubmissionService
from app.services.form_submission_service import FormSubmissionService
from werkzeug.datastructures import FileStorage
import logging

logger = logging.getLogger(__name__)

class ExportSubmissionController:
    @staticmethod
    def generate_pdf_export(
        submission_id: int,
        current_user: Optional[str] = None, # Made Optional for consistency
        user_role: Optional[str] = None,   # Made Optional for consistency
        header_image: Optional[FileStorage] = None,
        header_opacity: float = 1.0,
        header_size: Optional[float] = None,
        header_width: Optional[float] = None,
        header_height: Optional[float] = None,
        header_alignment: str = "center",
        signatures_size: float = 100,
        signatures_alignment: str = "vertical",
        pdf_style_options: Optional[Dict[str, Any]] = None,
        include_signatures: bool = True # Added to allow control if needed, defaults to True
    ) -> Tuple[Optional[bytes], Optional[Dict], Optional[str]]:
        """
        Generate a PDF export for a given submission, handling both default and custom options.
        All PDF exports now use the structured PDF generation service method for consistency.
        """
        try:
            submission = FormSubmissionService.get_submission(submission_id)
            if not submission:
                return None, None, "Submission not found"

            upload_path = current_app.config['UPLOAD_FOLDER']

            logger.debug(f"Controller: Calling ExportSubmissionService.export_structured_submission_to_pdf for sub ID {submission_id}")
            pdf_buffer, error = ExportSubmissionService.export_structured_submission_to_pdf(
                submission_id=submission_id,
                upload_path=upload_path,
                include_signatures=include_signatures,
                header_image=header_image,
                header_opacity=header_opacity,
                header_size=header_size,
                header_width=header_width,
                header_height=header_height,
                header_alignment=header_alignment,
                signatures_size=signatures_size,
                signatures_alignment=signatures_alignment,
                pdf_style_options=pdf_style_options
            )

            if error:
                logger.error(f"Error exporting submission {submission_id} to PDF via structured service: {error}")
                return None, None, error

            submission_date = submission.submitted_at.strftime("%Y%m%d")
            form_name_safe = "".join(c if c.isalnum() else "_" for c in submission.form.title) # Sanitize form name
            
            filename_parts = [form_name_safe, "submission", str(submission_id), submission_date]
            if pdf_style_options or header_image: # Add 'custom' if any customization is applied
                filename_parts.append("custom")
            
            filename = f"{'_'.join(filename_parts)}.pdf"
            
            metadata = {
                "filename": filename,
                "mimetype": "application/pdf",
                "submission_id": submission_id,
                "form_title": submission.form.title,
                "submitted_by": submission.submitted_by,
                "submitted_at": submission.submitted_at.isoformat(),
                "options_applied": {
                    "custom_styles_provided": bool(pdf_style_options),
                    "header_image_provided": bool(header_image),
                    # Add other relevant options if needed for metadata
                }
            }

            return pdf_buffer.getvalue(), metadata, None

        except Exception as e:
            logger.error(f"Error in generate_pdf_export controller for submission {submission_id}: {str(e)}", exc_info=True)
            return None, None, f"An unexpected error occurred during PDF generation: {str(e)}"

    @staticmethod
    def generate_docx_export(
        submission_id: int,
        current_user: Optional[str] = None, # Made Optional
        user_role: Optional[str] = None,   # Made Optional
        header_image: Optional[FileStorage] = None,
        header_size: Optional[float] = None, 
        header_width: Optional[float] = None, 
        header_height: Optional[float] = None, 
        header_alignment: str = "center",
        signatures_size: float = 100, 
        signatures_alignment: str = "vertical",
        style_options: Optional[Dict[str, Any]] = None,
        include_signatures: bool = True # Added to allow control
    ) -> Tuple[Optional[bytes], Optional[Dict], Optional[str]]:
        """
        Generate a DOCX export for a given submission, handling both default and custom options.
        """
        try:
            submission = FormSubmissionService.get_submission(submission_id)
            if not submission:
                return None, None, "Submission not found"

            upload_path = current_app.config['UPLOAD_FOLDER']
            
            logger.debug(f"Controller: Calling ExportSubmissionService.export_submission_to_docx for sub ID {submission_id}")
            docx_buffer, error = ExportSubmissionService.export_submission_to_docx(
                submission_id=submission_id,
                upload_path=upload_path,
                style_options=style_options,
                header_image_file=header_image,
                header_size_percent=header_size,
                header_width_px=header_width,
                header_height_px=header_height,
                header_alignment_str=header_alignment,
                include_signatures=include_signatures,
                signatures_size_percent=signatures_size,
                signatures_alignment_str=signatures_alignment
            )

            if error:
                logger.error(f"Error exporting submission {submission_id} to DOCX from service: {error}")
                return None, None, error

            submission_date = submission.submitted_at.strftime("%Y%m%d")
            form_name_safe = "".join(c if c.isalnum() else "_" for c in submission.form.title)

            filename_parts = [form_name_safe, "submission", str(submission_id), submission_date]
            if style_options or header_image: # Add 'custom' if any customization is applied
                filename_parts.append("custom")

            filename = f"{'_'.join(filename_parts)}.docx"

            metadata = {
                "filename": filename,
                "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "submission_id": submission_id,
                "form_title": submission.form.title,
                "submitted_by": submission.submitted_by,
                "submitted_at": submission.submitted_at.isoformat(),
                "options_applied": {
                    "custom_styles_provided": bool(style_options),
                    "header_image_provided": bool(header_image),
                }
            }

            return docx_buffer.getvalue(), metadata, None

        except Exception as e:
            logger.error(f"Error in generate_docx_export controller for submission {submission_id}: {str(e)}", exc_info=True)
            return None, None, f"An unexpected error occurred during DOCX generation: {str(e)}"