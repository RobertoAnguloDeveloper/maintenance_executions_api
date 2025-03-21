from datetime import datetime
from typing import Dict, List, Optional, Tuple
from flask import current_app
from app.models.form import Form
from app.models.user import User
from app.models.form_submission import FormSubmission
from app.services.form_submission_service import FormSubmissionService
from app.utils.permission_manager import RoleType
import logging

logger = logging.getLogger(__name__)

class FormSubmissionController:
    @staticmethod
    def create_submission(
        form_id: int,
        username: str,
        answers_data: Optional[List[Dict]] = None
    ) -> Tuple[Optional[FormSubmission], Optional[str]]:
        """
        Create a new form submission with validation and access control
        
        Args:
            form_id: ID of the form
            username: Username of submitter
            answers_data: Optional list of answer data
            
        Returns:
            tuple: (Created FormSubmission or None, Error message or None)
        """
        try:
            # Verify form exists and is accessible
            form = Form.query.filter_by(id=form_id, is_deleted=False).first()
            if not form:
                return None, "Form not found"

            # if not form.is_public and not form.creator.username == username:
            #     return None, "Unauthorized access to form"

            # Get upload path for signatures
            upload_path = current_app.config.get('UPLOAD_FOLDER')

            submission, error = FormSubmissionService.create_submission(
                form_id=form_id,
                username=username,
                answers_data=answers_data,
                upload_path=upload_path
            )
            
            if error:
                return None, error

            return submission, None

        except Exception as e:
            logger.error(f"Error in create_submission controller: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_all_submissions(
        user: User,
        filters: Dict = None
    ) -> List[FormSubmission]:
        """
        Get all submissions with role-based filtering
        
        Args:
            user: Current user object
            filters: Optional filters dictionary
            
        Returns:
            List[FormSubmission]: List of form submissions
        """
        try:
            if not filters:
                filters = {}

            # Apply role-based filtering
            if not user.role.is_super_user:
                if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    filters['environment_id'] = user.environment_id
                else:
                    filters['submitted_by'] = user.username

            return FormSubmissionService.get_all_submissions(user, filters)

        except Exception as e:
            logger.error(f"Error in get_all_submissions controller: {str(e)}")
            return []
        
    @staticmethod
    def get_all_submissions_compact(
        user: User,
        filters: Dict = None
    ) -> List[Dict]:
        """
        Get a compact list of all submissions with minimal information
        
        Args:
            user: Current user object
            filters: Optional filters dictionary
            
        Returns:
            List[Dict]: List of compact form submissions
        """
        try:
            if not filters:
                filters = {}

            # Apply role-based filtering
            if not user.role.is_super_user:
                if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    filters['environment_id'] = user.environment_id
                else:
                    filters['submitted_by'] = user.username

            return FormSubmissionService.get_all_submissions_compact(user, filters)

        except Exception as e:
            logger.error(f"Error in get_all_submissions_compact controller: {str(e)}")
            return []

    @staticmethod
    def get_submission(submission_id: int) -> Optional[FormSubmission]:
        """Get a specific submission with validation"""
        try:
            submission = FormSubmissionService.get_submission(submission_id)
            if not submission:
                return None
                
            return submission
            
        except Exception as e:
            logger.error(f"Error getting submission {submission_id}: {str(e)}")
            return None
        
    @staticmethod
    def get_user_submissions(
        username: str,
        filters: Optional[Dict] = None
    ) -> Tuple[List[FormSubmission], Optional[str]]:
        """
        Get all submissions for a specific user with filtering.
        
        Args:
            username: Username of the submitter
            filters: Optional filters dictionary
            
        Returns:
            tuple: (List of submissions, Error message if any)
        """
        try:
            submissions = FormSubmissionService.get_submissions_by_user(
                username=username,
                filters=filters
            )
            return submissions, None

        except Exception as e:
            error_msg = f"Error getting user submissions: {str(e)}"
            logger.error(error_msg)
            return [], error_msg

    @staticmethod
    def get_submission_answers(
        submission_id: int,
        current_user: str,
        user_role: str
    ) -> Tuple[List[Dict], Optional[str]]:
        """
        Get all answers for a submission with access control
        
        Args:
            submission_id: ID of the submission
            current_user: Username of current user
            user_role: Role of current user
            
        Returns:
            tuple: (List of answer dictionaries, Error message or None)
        """
        try:
            submission = FormSubmissionService.get_submission(submission_id)
            if not submission:
                return [], "Submission not found"

            # Access control
            if user_role != RoleType.ADMIN:
                if user_role in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    if submission.form.creator.environment_id != submission.form.creator.environment_id:
                        return [], "Unauthorized access"
                elif submission.submitted_by != current_user:
                    return [], "Unauthorized access"

            return FormSubmissionService.get_submission_answers(submission_id)

        except Exception as e:
            logger.error(f"Error getting submission answers: {str(e)}")
            return [], str(e)
        
    @staticmethod
    def update_submission(
        submission_id: int,
        current_user: str,
        user_role: str,
        update_data: Dict,
        answers_data: Optional[List[Dict]] = None
    ) -> Tuple[Optional[FormSubmission], Optional[str]]:
        """
        Update an existing form submission with validation and access control
        
        Args:
            submission_id: ID of the submission to update
            current_user: Username of current user
            user_role: Role of current user
            update_data: Dictionary of fields to update
            answers_data: Optional list of updated answer data
            
        Returns:
            tuple: (Updated FormSubmission or None, Error message or None)
        """
        try:
            # Verify submission exists
            submission = FormSubmissionService.get_submission(submission_id)
            if not submission:
                return None, "Submission not found"

            # Access control
            if user_role != RoleType.ADMIN:
                if user_role in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    if submission.form.creator.environment_id != submission.form.creator.environment_id:
                        return None, "Unauthorized access"
                elif submission.submitted_by != current_user:
                    return None, "Can only update own submissions"

                # Check submission age for non-admin users
                submission_age = datetime.utcnow() - submission.submitted_at
                if submission_age.days > 7:  # Configurable timeframe
                    return None, "Cannot update submissions older than 7 days"

            # Get upload path for signatures
            upload_path = current_app.config.get('UPLOAD_FOLDER')

            submission, error = FormSubmissionService.update_submission(
                submission_id=submission_id,
                update_data=update_data,
                answers_data=answers_data,
                upload_path=upload_path
            )
            
            if error:
                return None, error

            return submission, None

        except Exception as e:
            logger.error(f"Error in update_submission controller: {str(e)}")
            return None, str(e)

    @staticmethod
    def delete_submission(
        submission_id: int,
        current_user: str,
        user_role: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Delete a submission with access control
        
        Args:
            submission_id: ID of the submission
            current_user: Username of current user
            user_role: Role of current user
            
        Returns:
            tuple: (Success boolean, Error message or None)
        """
        try:
            submission = FormSubmissionService.get_submission(submission_id)
            if not submission:
                return False, "Submission not found"

            # Access control
            if user_role != RoleType.ADMIN:
                if user_role in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    if submission.form.creator.environment_id != submission.form.creator.environment_id:
                        return False, "Unauthorized access"
                elif submission.submitted_by != current_user:
                    return False, "Can only delete own submissions"

                # Check submission age for non-admin users
                submission_age = datetime.utcnow() - submission.submitted_at
                if submission_age.days > 7:  # Configurable timeframe
                    return False, "Cannot delete submissions older than 7 days"

            return FormSubmissionService.delete_submission(submission_id)

        except Exception as e:
            logger.error(f"Error deleting submission: {str(e)}")
            return False, str(e)