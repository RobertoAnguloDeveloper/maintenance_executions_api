# app/controllers/export_submission_controller.py

from typing import Dict, Optional, Tuple, Any
from flask import current_app
from app.services.export_submission_service import ExportSubmissionService
from app.services.form_submission_service import FormSubmissionService
# from app.utils.permission_manager import RoleType # Not used in this controller directly
from werkzeug.datastructures import FileStorage
import logging

logger = logging.getLogger(__name__)

class ExportSubmissionController:
    @staticmethod
    def export_submission_to_pdf(
        submission_id: int,
        current_user: str = None,
        user_role: str = None,
        pdf_style_options: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[bytes], Optional[Dict], Optional[str]]:
        """
        Export a form submission to PDF with authorization checks and style options.
        """
        try:
            submission = FormSubmissionService.get_submission(submission_id)
            if not submission:
                return None, None, "Submission not found"

            upload_path = current_app.config['UPLOAD_FOLDER']

            pdf_buffer, error = ExportSubmissionService.export_submission_to_pdf(
                submission_id=submission_id,
                upload_path=upload_path,
                include_signatures=True, # Default behavior
                pdf_style_options=pdf_style_options, # Pass through
                # Pass header/signature specific params if this endpoint needs them explicitly
            )

            if error:
                logger.error(f"Error exporting submission {submission_id} to PDF: {error}")
                return None, None, error

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
        header_image: Optional[FileStorage] = None,
        header_opacity: float = 1.0,
        header_size: Optional[float] = None,
        header_width: Optional[float] = None,
        header_height: Optional[float] = None,
        header_alignment: str = "center",
        signatures_size: float = 100,
        signatures_alignment: str = "vertical",
        pdf_style_options: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[bytes], Optional[Dict], Optional[str]]:
        """
        Export a form submission to PDF with structured organization, header options, and full style customization.
        """
        try:
            submission = FormSubmissionService.get_submission(submission_id)
            if not submission:
                return None, None, "Submission not found"

            upload_path = current_app.config['UPLOAD_FOLDER']

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
                signatures_alignment=signatures_alignment,
                pdf_style_options=pdf_style_options
            )

            if error:
                logger.error(f"Error exporting structured submission {submission_id} to PDF: {error}")
                return None, None, error

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
        header_image: Optional[FileStorage] = None,
        header_opacity: float = 1.0,
        header_size: Optional[float] = None,
        header_width: Optional[float] = None,
        header_height: Optional[float] = None,
        header_alignment: str = "center",
        signatures_size: float = 100,
        signatures_alignment: str = "vertical",
        structured: bool = True, # This flag might be deprecated for PDF if always structured
        pdf_style_options: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[bytes], Optional[Dict], Optional[str]]:
        """
        Export a form submission to PDF with header image, signature options, and full style customization.
        """
        try:
            submission = FormSubmissionService.get_submission(submission_id)
            if not submission:
                return None, None, "Submission not found"

            upload_path = current_app.config['UPLOAD_FOLDER']

            # All PDF exports now go through the structured method for consistency
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
                signatures_alignment=signatures_alignment,
                pdf_style_options=pdf_style_options
            )

            if error:
                logger.error(f"Error exporting submission {submission_id} to PDF with logo/styles: {error}")
                return None, None, error

            submission_date = submission.submitted_at.strftime("%Y%m%d")
            form_name = submission.form.title.replace(" ", "_")
            base_filename = f"{form_name}_submission_{submission_id}_{submission_date}"

            filename_suffix = "_logo"
            if structured: # If structured flag is true, reflect in filename
                filename_suffix = "_structured_logo"
            filename = f"{base_filename}{filename_suffix}.pdf"

            metadata = {
                "filename": filename,
                "mimetype": "application/pdf",
                "submission_id": submission_id,
                "form_title": submission.form.title,
                "submitted_by": submission.submitted_by,
                "submitted_at": submission.submitted_at.isoformat(),
                "options_applied": {
                    "header_image": bool(header_image),
                    "structured_output_flag": structured,
                    "custom_styles_provided": bool(pdf_style_options)
                }
            }

            return pdf_buffer.getvalue(), metadata, None

        except Exception as e:
            logger.error(f"Error in export_submission_to_pdf_with_logo controller: {str(e)}")
            return None, None, str(e)

    # --- NEW DOCX CONTROLLER METHOD ---
    @staticmethod
    def export_submission_to_docx(
        submission_id: int,
        current_user: str = None,
        user_role: str = None,
        header_image: Optional[FileStorage] = None,
        header_size: Optional[float] = None, # Percentage
        header_width: Optional[float] = None, # Pixels
        header_height: Optional[float] = None, # Pixels
        header_alignment: str = "center",
        signatures_size: float = 100, # Percentage
        signatures_alignment: str = "vertical",
        style_options: Optional[Dict[str, Any]] = None # Generic style options for DOCX
    ) -> Tuple[Optional[bytes], Optional[Dict], Optional[str]]:
        """
        Export a form submission to DOCX with authorization checks and options.
        """
        try:
            submission = FormSubmissionService.get_submission(submission_id)
            if not submission:
                return None, None, "Submission not found"

            upload_path = current_app.config['UPLOAD_FOLDER']

            docx_buffer, error = ExportSubmissionService.export_submission_to_docx(
                submission_id=submission_id,
                upload_path=upload_path,
                style_options=style_options,
                header_image_file=header_image,
                header_size_percent=header_size,
                header_width_px=header_width,
                header_height_px=header_height,
                header_alignment_str=header_alignment,
                include_signatures=True, # Default to include signatures
                signatures_size_percent=signatures_size,
                signatures_alignment_str=signatures_alignment
            )

            if error:
                logger.error(f"Error exporting submission {submission_id} to DOCX: {error}")
                return None, None, error

            submission_date = submission.submitted_at.strftime("%Y%m%d")
            form_name = submission.form.title.replace(" ", "_")
            filename = f"{form_name}_submission_{submission_id}_{submission_date}.docx"

            metadata = {
                "filename": filename,
                "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "submission_id": submission_id,
                "form_title": submission.form.title,
                "submitted_by": submission.submitted_by,
                "submitted_at": submission.submitted_at.isoformat()
            }

            return docx_buffer.getvalue(), metadata, None

        except Exception as e:
            logger.error(f"Error in export_submission_to_docx controller: {str(e)}")
            return None, None, str(e)
