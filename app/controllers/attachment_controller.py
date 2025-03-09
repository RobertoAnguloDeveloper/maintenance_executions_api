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
        user_role: str = None,
        answer_submitted_id: int = None,
        signature_position: str = None,
        signature_author: str = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Validate and create new attachment with proper authorization
        """
        try:
            # Validate submission exists and check access rights
            submission = FormSubmissionService.get_submission(form_submission_id)
            if not submission:
                return None, "Form submission not found"

            # Validate file
            is_valid, mime_type_or_error = AttachmentService.validate_file(file, file.filename)
            if not is_valid:
                return None, mime_type_or_error

            # Create attachment with enhanced signature handling
            attachment, error = AttachmentService.create_attachment(
                form_submission_id=form_submission_id,
                file=file,
                filename=file.filename,
                username=current_user,
                upload_path=current_app.config['UPLOAD_FOLDER'],
                file_type=mime_type_or_error,
                is_signature=is_signature,
                answer_submitted_id=answer_submitted_id,  # Pass answer_submitted_id for signatures
                signature_position=signature_position,    # Pass new signature position
                signature_author=signature_author         # Pass new signature author
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
        Bulk create attachments with improved validation
        """
        try:
            # Validate submission exists and check access rights
            submission = FormSubmissionService.get_submission(form_submission_id)
            if not submission:
                return None, "Form submission not found"
            
            # Validate all files first
            for file_data in files:
                file = file_data.get('file')
                if not file:
                    return None, "File object is required for each attachment"
                    
                # Initial validation
                is_valid, error_or_mime = AttachmentService.validate_file(
                    file,
                    file.filename,
                    max_size=Attachment.MAX_FILE_SIZE
                )
                
                if not is_valid:
                    return None, f"Invalid file {file.filename}: {error_or_mime}"
            
            # If all validations pass, create attachments
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
    def get_all_attachments(
        current_user: str = None,
        user_role: str = None,
        filters: Dict = None
    ) -> Tuple[List[Dict], Optional[str]]:
        """
        Get all attachments with role-based access control
        
        Args:
            current_user: Username of current user
            user_role: Role of current user
            filters: Optional filters
            
        Returns:
            tuple: (List of attachments, Error message or None)
        """
        try:
            # Initialize filters if None
            filters = filters or {}
            
            # Apply role-based filtering
            if user_role != RoleType.ADMIN:
                if user_role in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    # Filter by environment
                    filters['environment_id'] = current_user.environment_id
                else:
                    # Regular users can only see their own submissions
                    filters['submitted_by'] = current_user

            attachments = AttachmentService.get_all_attachments(filters)
            
            # Convert attachments to dict representation
            return [attachment.to_dict() for attachment in attachments], None

        except Exception as e:
            logger.error(f"Error getting attachments in controller: {str(e)}")
            return [], str(e)

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
    def get_attachment_with_file(
        attachment_id: int,
        current_user: str = None,
        user_role: str = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get attachment with file data and authorization check
        """
        try:
            logger.info(f"Fetching attachment {attachment_id} from upload folder: {current_app.config['UPLOAD_FOLDER']}")
            
            attachment_data, error = AttachmentService.get_attachment_with_file(
                attachment_id=attachment_id,
                base_path=current_app.config['UPLOAD_FOLDER']
            )
            
            if error:
                logger.error(f"Error retrieving attachment {attachment_id}: {error}")
                return None, error
                    
            # Access control
            if user_role != RoleType.ADMIN:
                if user_role in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    attachment_data['record'].form_submission.submitted_by != current_user
                    return None, "Unauthorized access"
                        
            return attachment_data, None
                
        except Exception as e:
            logger.error(f"Error in get_attachment controller: {str(e)}")
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
    def update_attachment(
        attachment_id: int,
        signature_position: str = None,
        signature_author: str = None,
        is_signature: bool = None,
        current_user: str = None,
        user_role: str = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Update attachment signature metadata with authorization check
        
        Args:
            attachment_id: ID of the attachment to update
            signature_position: New signature position
            signature_author: New signature author
            is_signature: Update is_signature flag
            current_user: Username of current user
            user_role: Role of current user
            
        Returns:
            tuple: (Updated attachment dict or None, Error message or None)
        """
        try:
            # Get attachment for access control
            attachment = AttachmentService.get_attachment(attachment_id)
            if not attachment:
                return None, "Attachment not found"

            # Update attachment
            updated_attachment, error = AttachmentService.update_attachment(
                attachment_id=attachment_id,
                signature_position=signature_position,
                signature_author=signature_author,
                is_signature=is_signature
            )
            
            if error:
                return None, error
                
            return updated_attachment.to_dict(), None
            
        except Exception as e:
            logger.error(f"Error updating attachment {attachment_id}: {str(e)}")
            return None, str(e)

    @staticmethod
    def delete_attachment(
        attachment_id: int,
        current_user: str = None,
        user_role: str = None
    ) -> Tuple[bool, str]:
        """
        Delete an attachment
        """
        try:
            # Get attachment for access control
            attachment = AttachmentService.get_attachment(attachment_id)
            if not attachment:
                return False, "Attachment not found"

            # Check ownership/permissions
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

            success, result = AttachmentService.delete_attachment(
                attachment_id,
                current_app.config['UPLOAD_FOLDER']
            )

            if not success:
                return False, result

            return True, "Attachment deleted successfully"

        except Exception as e:
            logger.error(f"Error in delete_attachment controller: {str(e)}")
            return False, str(e)