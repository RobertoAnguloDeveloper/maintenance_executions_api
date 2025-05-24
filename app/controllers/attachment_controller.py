from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
from flask import current_app
from werkzeug.datastructures import FileStorage
import logging
import os

from app.models.attachment import Attachment
from app.services.attachment_service import AttachmentService
from app.services.auth_service import AuthService
from app.services.form_submission_service import FormSubmissionService
from app.utils.permission_manager import RoleType

logger = logging.getLogger(__name__)

class AttachmentController:
    @staticmethod
    def validate_and_create_attachment(
        form_submission_id: int,
        file: FileStorage,
        current_user: str, # This is the username string
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
            # --- FIX STARTS HERE ---
            # 1. Resolve user string to User object
            user_obj = AuthService.get_current_user(current_user)
            if not user_obj:
                logger.warning(f"User '{current_user}' not found for creating attachment.")
                return None, "User not found for authorization."

            # 2. Validate submission exists and check access rights using User object
            submission = FormSubmissionService.get_submission(
                submission_id=form_submission_id,
                current_user=user_obj # Pass User object
            )
            # --- FIX ENDS HERE ---

            if not submission:
                return None, "Form submission not found or access denied"

            # Validate file
            is_valid, mime_type_or_error = AttachmentService.validate_file(file, file.filename)
            if not is_valid:
                return None, mime_type_or_error

            # Create attachment with enhanced signature handling
            attachment, error = AttachmentService.create_attachment(
                form_submission_id=form_submission_id,
                file=file,
                filename=file.filename,
                username=current_user, # Service uses username for path
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
        current_user: str, # This is the username string
        user_role: str = None
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """
        Bulk create attachments with improved validation
        """
        try:
            # --- FIX STARTS HERE ---
            # 1. Resolve user string to User object
            user_obj = AuthService.get_current_user(current_user)
            if not user_obj:
                logger.warning(f"User '{current_user}' not found for bulk creating attachments.")
                return None, "User not found for authorization."

            # 2. Validate submission exists and check access rights using User object
            submission = FormSubmissionService.get_submission(
                submission_id=form_submission_id,
                current_user=user_obj # Pass User object
            )
            # --- FIX ENDS HERE ---

            if not submission:
                return None, "Form submission not found or access denied"

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
            current_user: Username of current user (string)
            user_role: Role of current user
            filters: Optional filters
            
        Returns:
            tuple: (List of attachments, Error message or None)
        """
        try:
            # Initialize filters if None
            filters = filters or {}
            
            # Apply role-based filterin
            if user_role != RoleType.ADMIN:
                if user_role in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    # Get user object first - current_user is a username string, not a User object
                    user_obj = AuthService.get_current_user(current_user)
                    if not user_obj:
                        return [], "User not found"
                    
                    # Filter by environment using the user object
                    filters['environment_id'] = user_obj.environment_id
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
    def get_batch(page=1, per_page=50, **filters):
        """
        Get batch of attachments with pagination
        
        Args:
            page: Page number (starts from 1)
            per_page: Number of items per page
            **filters: Optional filters
            
        Returns:
            tuple: (total_count, attachments)
        """
        return AttachmentService.get_batch(page, per_page, **filters)

    @staticmethod
    def get_attachment(
        attachment_id: int,
        current_user: str = None, # username string
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

            # --- FIX ACCESS CONTROL LOGIC ---
            # 1. Resolve user string to User object
            user_obj = AuthService.get_current_user(current_user)
            if not user_obj:
                return None, "User not found for authorization."

            # 2. Check access via FormSubmissionService.get_submission
            submission = FormSubmissionService.get_submission(
                submission_id=attachment.form_submission_id,
                current_user=user_obj
            )
            if not submission:
                return None, "Unauthorized access to this attachment's submission."
            # --- END FIX ---

            return attachment.to_dict(), None

        except Exception as e:
            logger.error(f"Error getting attachment: {str(e)}")
            return None, str(e)
        
    @staticmethod
    def get_attachment_with_file(
        attachment_id: int,
        current_user: str = None, # username string
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

            # --- ADD ACCESS CONTROL ---
            attachment_record = attachment_data['record']
            user_obj = AuthService.get_current_user(current_user)
            if not user_obj:
                return None, "User not found for authorization."

            submission = FormSubmissionService.get_submission(
                submission_id=attachment_record.form_submission_id,
                current_user=user_obj
            )
            if not submission:
                return None, "Unauthorized access to download this attachment."
            # --- END ACCESS CONTROL ---

            return attachment_data, None

        except Exception as e:
            logger.error(f"Error in get_attachment controller: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_submission_attachments(
        form_submission_id: int,
        current_user: str = None, # This is the username string
        user_role: str = None
    ) -> Tuple[List[Dict], Optional[str]]:
        """
        Get all attachments for a submission
        """
        try:
            # --- FIX STARTS HERE ---
            # 1. Resolve the current_user (username string) to a User object
            user_obj = AuthService.get_current_user(current_user)
            if not user_obj:
                logger.warning(f"User '{current_user}' not found for getting submission attachments.")
                return [], "User not found for authorization."

            # 2. Call FormSubmissionService.get_submission with the User object
            submission = FormSubmissionService.get_submission(
                submission_id=form_submission_id,
                current_user=user_obj
            )
            # --- FIX ENDS HERE ---

            if not submission:
                # Updated message for clarity
                return [], "Form submission not found or access denied"

            attachments = Attachment.query.filter_by(
                form_submission_id=form_submission_id,
                is_deleted=False
            ).all()

            return [att.to_dict() for att in attachments], None

        except Exception as e:
            # Added form_submission_id to log for better context
            logger.error(f"Error getting submission attachments for ID {form_submission_id}: {str(e)}")
            return [], str(e)
            
    @staticmethod
    def update_attachment(
        attachment_id: int,
        signature_position: str = None,
        signature_author: str = None,
        is_signature: bool = None,
        current_user: str = None, # username string
        user_role: str = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Update attachment signature metadata with authorization check
        """
        try:
            # --- ADD ACCESS CONTROL ---
            attachment_to_update = AttachmentService.get_attachment(attachment_id)
            if not attachment_to_update:
                return None, "Attachment not found"

            user_obj = AuthService.get_current_user(current_user)
            if not user_obj:
                return None, "User not found for authorization."

            submission = FormSubmissionService.get_submission(
                submission_id=attachment_to_update.form_submission_id,
                current_user=user_obj
            )
            if not submission:
                return None, "Unauthorized access to update this attachment."
            # You might add more granular checks here (e.g., role-based, time limits)
            # --- END ACCESS CONTROL ---

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
        current_user: str = None, # username string
        user_role: str = None
    ) -> Tuple[bool, str]:
        """
        Delete an attachment
        """
        try:
            # Get attachment
            attachment = AttachmentService.get_attachment(attachment_id)
            if not attachment:
                return False, "Attachment not found"

            # --- FIX ACCESS CONTROL ---
            user_obj = AuthService.get_current_user(current_user)
            if not user_obj:
                return False, "User not found for authorization."

            submission = FormSubmissionService.get_submission(
                submission_id=attachment.form_submission_id,
                current_user=user_obj
            )
            if not submission:
                return False, "Unauthorized access to delete this attachment."

            # Check role and time limits if necessary (using user_obj and user_role)
            if user_role != RoleType.ADMIN.name: # Use .name if comparing with string
                if user_role in [RoleType.SITE_MANAGER.name, RoleType.SUPERVISOR.name]:
                    # Check environment (Requires user_obj and submitter's env ID)
                    submitter = AuthService.get_current_user(submission.submitted_by)
                    if not submitter or submitter.environment_id != user_obj.environment_id:
                         return False, "Unauthorized access (Environment mismatch)."
                elif submission.submitted_by != current_user:
                     return False, "Can only delete own attachments (or need higher privileges)."

                # Check submission age
                submission_age = datetime.utcnow() - attachment.form_submission.submitted_at
                if submission_age.days > 7:
                    return False, "Cannot delete attachments older than 7 days"
            # --- END FIX ---

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