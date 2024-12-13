from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
from flask import current_app
from werkzeug.datastructures import FileStorage
import logging
import os

from app.models.attachment import Attachment
from app.services.attachment_service import AttachmentService
from app.services.form_submission_service import FormSubmissionService
from app.utils.permission_manager import RoleType

logger = logging.getLogger(__name__)

class AttachmentController:
    @staticmethod
    def validate_and_create_attachment(
        form_submission_id: int,
        file: FileStorage,
        current_user: str,
        is_signature: bool = False,
        user_role: str = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Validate and create new attachment with proper authorization
        """
        try:
            # Validate submission exists and check access rights
            submission = FormSubmissionService.get_submission(form_submission_id)
            if not submission:
                return None, "Form submission not found"

            # Access control
            if user_role != RoleType.ADMIN:
                if user_role in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    if submission.form.creator.environment_id != current_user.environment_id:
                        return None, "Unauthorized access"
                elif submission.submitted_by != current_user:
                    return None, "Can only add attachments to own submissions"

            # Validate file
            is_valid, mime_type_or_error = AttachmentService.validate_file(file, file.filename)
            if not is_valid:
                return None, mime_type_or_error

            # Create attachment
            attachment, error = AttachmentService.create_attachment(
                form_submission_id=form_submission_id,
                file=file,
                filename=file.filename,
                username=current_user,
                upload_path=current_app.config['UPLOAD_FOLDER'],
                file_type=mime_type_or_error,
                is_signature=is_signature
            )

            if error:
                return None, error

            return attachment.to_dict() if attachment else None, None

        except Exception as e:
            logger.error(f"Error in create_attachment controller: {str(e)}")
            return None, str(e)
        
    @staticmethod
    def bulk_create_attachments(
        form_submission_id: int,
        files: List[Dict],
        current_user: str,
        user_role: str = None
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """
        Bulk create attachments with authorization
        
        Args:
            form_submission_id: ID of the form submission
            files: List of file data
            current_user: Username of current user
            user_role: Role of current user
            
        Returns:
            tuple: (List of created attachments or None, Error message or None)
        """
        try:
            # Validate submission exists and check access rights
            submission = FormSubmissionService.get_submission(form_submission_id)
            if not submission:
                return None, "Form submission not found"
                
            # Access control
            if user_role != RoleType.ADMIN:
                if user_role in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    if submission.form.creator.environment_id != current_user.environment_id:
                        return None, "Unauthorized access"
                elif submission.submitted_by != current_user:
                    return None, "Can only add attachments to own submissions"
            
            attachments, error = AttachmentService.bulk_create_attachments(
                form_submission_id=form_submission_id,
                files=files,
                username=current_user,
                upload_path=current_app.config['UPLOAD_FOLDER']
            )
            
            if error:
                return None, error
                
            return [attachment.to_dict() for attachment in attachments], None
            
        except Exception as e:
            logger.error(f"Error in bulk_create_attachments controller: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_attachment(
        attachment_id: int,
        current_user: str = None,
        user_role: str = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get specific attachment with access control
        """
        try:
            attachment = Attachment.query.filter_by(
                id=attachment_id,
                is_deleted=False
            ).first()
            
            if not attachment:
                return None, "Attachment not found"

            # Access control
            if user_role != RoleType.ADMIN:
                if user_role in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    if attachment.form_submission.form.creator.environment_id != current_user.environment_id:
                        return None, "Unauthorized access"
                elif attachment.form_submission.submitted_by != current_user:
                    return None, "Unauthorized access"

            return attachment.to_dict(), None

        except Exception as e:
            logger.error(f"Error getting attachment: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_submission_attachments(
        form_submission_id: int,
        current_user: str = None,
        user_role: str = None
    ) -> Tuple[List[Dict], Optional[str]]:
        """
        Get all attachments for a submission
        """
        try:
            submission = FormSubmissionService.get_submission(form_submission_id)
            if not submission:
                return [], "Form submission not found"

            # Access control
            if user_role != RoleType.ADMIN:
                if user_role in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    if submission.form.creator.environment_id != current_user.environment_id:
                        return [], "Unauthorized access"
                elif submission.submitted_by != current_user:
                    return [], "Unauthorized access"

            attachments = Attachment.query.filter_by(
                form_submission_id=form_submission_id,
                is_deleted=False
            ).all()

            return [att.to_dict() for att in attachments], None

        except Exception as e:
            logger.error(f"Error getting submission attachments: {str(e)}")
            return [], str(e)

    @staticmethod
    def delete_attachment(
        attachment_id: int,
        current_user: str = None,
        user_role: str = None
    ) -> Tuple[bool, str]:
        """
        Delete attachment with authorization check
        """
        try:
            attachment = Attachment.query.filter_by(
                id=attachment_id,
                is_deleted=False
            ).first()
            
            if not attachment:
                return False, "Attachment not found"

            # Access control
            if user_role != RoleType.ADMIN:
                if user_role in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    if attachment.form_submission.form.creator.environment_id != current_user.environment_id:
                        return False, "Unauthorized access"
                elif attachment.form_submission.submitted_by != current_user:
                    return False, "Can only delete own attachments"

                # Check submission age for non-admin users
                submission_age = datetime.utcnow() - attachment.form_submission.submitted_at
                if submission_age.days > 7:
                    return False, "Cannot delete attachments older than 7 days"

            success, error = AttachmentService.delete_attachment(
                attachment_id,
                current_app.config['UPLOAD_FOLDER']
            )

            if not success:
                return False, error or "Failed to delete attachment"

            return True, "Attachment deleted successfully"

        except Exception as e:
            logger.error(f"Error deleting attachment: {str(e)}")
            return False, str(e)