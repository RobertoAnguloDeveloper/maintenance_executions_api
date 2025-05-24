from typing import Dict, List, Optional, Tuple
from flask import current_app
# Ensure User model is imported if not already via app.models
from app.models.user import User as UserModel # Renamed to avoid conflict if 'user' var is used
from app.models.answer_submitted import AnswerSubmitted
from app.services.answer_submitted_service import AnswerSubmittedService
from app.services.form_submission_service import FormSubmissionService
from app.services.auth_service import AuthService # Import AuthService
from app.services.form_service import FormService
from app.utils.permission_manager import RoleType
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AnswerSubmittedController:
    @staticmethod
    def create_answer_submitted(
        form_submission_id: int,
        question_text: str,
        question_type_text: str,
        answer_text: str,
        question_order: Optional[int] = None, # Added question_order to match service
        current_user: str = None, # username string
        column: Optional[int] = None,
        row: Optional[int] = None,
        cell_content: Optional[str] = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        try:
            # Resolve current_user (username string) to a User model instance for service call
            user_obj_for_service_call = None
            if current_user:
                user_obj_for_service_call = AuthService.get_current_user(current_user)
                if not user_obj_for_service_call:
                    return None, f"User '{current_user}' not found for authorization check."

            submission = FormSubmissionService.get_submission(
                submission_id=form_submission_id,
                current_user=user_obj_for_service_call # Pass User object
            )
            if not submission:
                return None, "Form submission not found or access denied"

            # Original ownership check (using username string 'current_user')
            if current_user and submission.submitted_by != current_user:
                return None, "Unauthorized: Can only add answers to own submissions"

            # Validate table-type data
            if question_type_text == 'table':
                if column is None or row is None:
                    return None, "Column and row are required for table-type questions"

            answer_submitted_obj, error = AnswerSubmittedService.create_answer_submitted( # Renamed to avoid confusion
                form_submission_id=form_submission_id,
                question_text=question_text,
                question_type_text=question_type_text,
                answer_text=answer_text,
                question_order=question_order, # Pass question_order
                # is_signature, signature_file, upload_path are handled by AnswerSubmittedService if needed
                column=column,
                row=row,
                cell_content=cell_content
            )
            
            if error:
                return None, error

            return answer_submitted_obj.to_dict() if answer_submitted_obj else None, None # Use .to_dict() if it's an object

        except Exception as e:
            logger.error(f"Error in create_answer_submitted controller: {str(e)}")
            return None, str(e)
        
    @staticmethod
    def bulk_create_answers_submitted(
        form_submission_id: int,
        submissions_data: List[Dict],
        current_user: str = None # This is the username string from JWT
    ) -> Tuple[Optional[List[AnswerSubmitted]], Optional[str]]:
        """
        Bulk create answer submissions with validation
        
        Args:
            form_submission_id: ID of the form submission
            submissions_data: List of submission data dictionaries
            current_user: Username of current user (string)
            
        Returns:
            tuple: (List of created AnswerSubmitted objects or None, Error message or None)
        """
        try:
            # Resolve current_user (username string) to a User model instance
            user_obj_for_service_call = None
            if current_user:
                user_obj_for_service_call = AuthService.get_current_user(current_user) # Use AuthService
                if not user_obj_for_service_call:
                    # This implies the JWT identity is valid, but no corresponding user in DB.
                    # This should ideally be caught by @jwt_required or initial user loading in the view.
                    return None, f"User '{current_user}' not found for authorization."

            # Call FormSubmissionService.get_submission with the User object
            submission = FormSubmissionService.get_submission(
                submission_id=form_submission_id,
                current_user=user_obj_for_service_call # Pass the User object here
            )
            
            if not submission:
                # FormSubmissionService.get_submission now handles "not found" or "access denied"
                return None, "Form submission not found or access denied."
                    
            # Original ownership check: Only submission owner (identified by username string) can add answers.
            # This is an additional business rule on top of being able to view/access the submission.
            if current_user and submission.submitted_by != current_user: # current_user is the username string
                return None, "Unauthorized: Can only add answers to own submissions."

            # Validate table-type data for each submission (this part of your original logic is fine)
            for data in submissions_data:
                if data.get('question_type_text') == 'table':
                    if 'column' not in data or 'row' not in data:
                        return None, "Column and row are required for table-type questions"

            created_submissions, error = AnswerSubmittedService.bulk_create_answers_submitted(
                form_submission_id=form_submission_id,
                answers_data=submissions_data
            )
            
            if error:
                return None, error
                    
            return created_submissions, None

        except Exception as e:
            logger.error(f"Error in bulk_create_answers_submitted controller: {str(e)}") # Log the exception for more details
            return None, str(e)

    @staticmethod
    def get_all_answers_submitted(
        user: UserModel, # Expecting User Model instance here
        filters: Dict = None
    ) -> List[Dict]:
        """
        Get all answers submitted with role-based access control
        
        Args:
            user: Current user object (UserModel instance) for role-based access
            filters: Optional filters (form_id, environment_id, date range)
            
        Returns:
            list: List of answer submitted dictionaries
        """
        try:
            # Initialize filters if None
            filters = filters or {}
            
            # Apply role-based filtering (user is already a UserModel instance)
            if not user.role.is_super_user:
                if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    # Can only see answers from users in their environment
                    filters['environment_id'] = user.environment_id
                else:
                    # Regular users can only see their own submissions' answers
                    filters['submitted_by'] = user.username # Filter by the username

            answers = AnswerSubmittedService.get_all_answers_submitted(filters)
            return [answer.to_dict() for answer in answers if answer]

        except Exception as e:
            logger.error(f"Error getting answers submitted in controller: {str(e)}")
            return []
        
    @staticmethod
    def get_batch(page=1, per_page=50, **filters):
        """
        Get batch of submitted answers with pagination
        
        Args:
            page: Page number (starts from 1)
            per_page: Number of items per page
            **filters: Optional filters, current_user (username string) should be resolved to User object if needed by service
            
        Returns:
            tuple: (total_count, answers_submitted)
        """
        # Resolve current_user string to User object if service expects it
        if 'current_user' in filters and isinstance(filters['current_user'], str):
            username_str = filters.pop('current_user') # Remove string version
            user_obj = AuthService.get_current_user(username_str)
            if not user_obj:
                 # Handle case where user string doesn't resolve to a user object
                 logger.warning(f"User '{username_str}' not found for get_batch call.")
                 return 0, [] # Or handle error appropriately
            filters['current_user'] = user_obj # Add User object version

        return AnswerSubmittedService.get_batch(page, per_page, **filters)

        
    @staticmethod
    def get_answer_submitted(
        answer_submitted_id: int,
        current_user: str = None, # username string
        user_role: str = None # role name string
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get a specific submitted answer with authorization checks.
        
        Args:
            answer_submitted_id: ID of the answer submission
            current_user: Username of current user (string)
            user_role: Role of current user (string)
            
        Returns:
            tuple: (Answer submitted dictionary or None, Error message or None)
        """
        try:
            # Get the answer submission (AnswerSubmittedService.get_answer_submitted does not require user object)
            answer = AnswerSubmittedService.get_answer_submitted(answer_submitted_id)
            if not answer:
                return None, "Answer submission not found"

            # Access control (uses username string and role string as before)
            if current_user and user_role != RoleType.ADMIN.value: # Ensure comparing with RoleType enum value if needed
                # Get the submitter to check environment_id
                # This requires joining through form_submission to user
                submitter = UserModel.query.filter_by(username=answer.form_submission.submitted_by).first()
                # Get the current user object (UserModel instance) for environment comparison
                user_obj_for_check = AuthService.get_current_user(current_user)
                if not user_obj_for_check:
                    return None, f"User '{current_user}' not found for permission check."

                if user_role in [RoleType.SITE_MANAGER.value, RoleType.SUPERVISOR.value]:
                    # Check if submitter is in the same environment
                    if not submitter or submitter.environment_id != user_obj_for_check.environment_id:
                        return None, "Unauthorized access"
                elif answer.form_submission.submitted_by != current_user: # Compare username strings
                    # Regular users can only see their own submissions
                    return None, "Unauthorized access"

            return answer.to_dict(), None

        except Exception as e:
            logger.error(f"Error getting answer submitted {answer_submitted_id}: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_answers_by_submission(
        submission_id: int,
        current_user: str = None, # username string
        user_role: str = None # role name string
    ) -> Tuple[List[Dict], Optional[str]]:
        """Get all submitted answers for a form submission"""
        try:
            # Resolve current_user (username string) to a User model instance for service call
            user_obj_for_service_call = None
            if current_user:
                user_obj_for_service_call = AuthService.get_current_user(current_user)
                if not user_obj_for_service_call:
                    return [], f"User '{current_user}' not found for authorization."
            
            # Get submission for access control (this now takes User object)
            submission = FormSubmissionService.get_submission(submission_id, user_obj_for_service_call)
            if not submission:
                return [], "Form submission not found or access denied"

            # If submission access is granted, proceed to get answers.
            # The original access control logic here was based on the resolved `submission` and string `current_user`/`user_role`.
            # This is largely handled by get_submission now. If additional checks are needed, they can be placed here.
            # For instance, if `get_answers_by_submission` itself had stricter rules than `get_submission`.

            answers_list, error = AnswerSubmittedService.get_answers_by_submission(submission_id) # Assuming this doesn't need user
            if error:
                return [], error

            return [answer.to_dict() for answer in answers_list], None # Use .to_dict() for each AnswerSubmitted object

        except Exception as e:
            logger.error(f"Error getting answers by submission in controller: {str(e)}")
            return [], str(e)

    @staticmethod
    def update_answer_submitted(
        answer_submitted_id: int,
        answer_text: Optional[str] = None,
        question_order: Optional[int] = None, # Added to match service
        column: Optional[int] = None,
        row: Optional[int] = None,
        cell_content: Optional[str] = None,
        current_user: str = None, # username string
        user_role: str = None # role name string
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """Update a submitted answer with table support"""
        try:
            answer = AnswerSubmittedService.get_answer_submitted(answer_submitted_id)
            if not answer:
                return None, "Answer submission not found"

            # Access control logic (uses username string and role string as before)
            if current_user and user_role != RoleType.ADMIN.value:
                user_obj_for_check = AuthService.get_current_user(current_user) # For environment ID
                if not user_obj_for_check:
                     return None, f"User '{current_user}' not found for permission check."

                # Assuming answer.form_submission.form.creator provides access to the form creator User object
                # to check their environment_id. This requires the relationships to be loaded.
                form_creator_env_id = None
                if answer.form_submission and answer.form_submission.form and answer.form_submission.form.creator:
                    form_creator_env_id = answer.form_submission.form.creator.environment_id
                else: # Need to explicitly load creator if not available
                    form_id = answer.form_submission.form_id
                    form_obj = FormService.get_form(form_id) # Assuming FormService.get_form returns Form with creator loaded
                    if form_obj and form_obj.creator:
                        form_creator_env_id = form_obj.creator.environment_id

                if user_role in [RoleType.SITE_MANAGER.value, RoleType.SUPERVISOR.value]:
                    if form_creator_env_id is None or form_creator_env_id != user_obj_for_check.environment_id:
                        return None, "Unauthorized access: Environment mismatch."
                elif answer.form_submission.submitted_by != current_user: # Compare username strings
                    return None, "Unauthorized access: Not the submitter."

            # Check submission age for non-admin users
            if user_role != RoleType.ADMIN.value: # Compare with RoleType enum value
                submission_age = datetime.utcnow() - answer.form_submission.submitted_at
                if submission_age.days > 7:  # Configurable timeframe
                    return None, "Cannot update answers older than 7 days"

            # Validate table-type data
            if answer.question_type == 'table' and (column is not None or row is not None):
                if (column is not None and row is None) or (column is None and row is not None):
                    return None, "Both column and row must be provided when updating table positions"

            updated_answer_obj, error = AnswerSubmittedService.update_answer_submitted( # Renamed
                answer_submitted_id,
                answer_text,
                question_order, # Pass question_order
                column,
                row,
                cell_content
            )
            
            if error:
                return None, error

            return updated_answer_obj.to_dict() if updated_answer_obj else None, None # Use .to_dict() if it's an object

        except Exception as e:
            logger.error(f"Error updating answer submitted in controller: {str(e)}")
            return None, str(e)

    @staticmethod
    def delete_answer_submitted(
        answer_submitted_id: int,
        current_user: str = None, # username string
        user_role: str = None # role name string
    ) -> Tuple[bool, str]:
        """Delete a submitted answer"""
        try:
            answer = AnswerSubmittedService.get_answer_submitted(answer_submitted_id)
            if not answer:
                return False, "Answer submission not found"

            # Access control (uses username string and role string as before)
            if current_user and user_role != RoleType.ADMIN.value: # Compare with RoleType enum value
                user_obj_for_check = AuthService.get_current_user(current_user) # For environment ID
                if not user_obj_for_check:
                     return False, f"User '{current_user}' not found for permission check."
                
                form_creator_env_id = None
                if answer.form_submission and answer.form_submission.form and answer.form_submission.form.creator:
                    form_creator_env_id = answer.form_submission.form.creator.environment_id
                else: # Need to explicitly load
                    form_id = answer.form_submission.form_id
                    form_obj = FormService.get_form(form_id)
                    if form_obj and form_obj.creator:
                        form_creator_env_id = form_obj.creator.environment_id

                if user_role in [RoleType.SITE_MANAGER.value, RoleType.SUPERVISOR.value]:
                    if form_creator_env_id is None or form_creator_env_id != user_obj_for_check.environment_id:
                        return False, "Unauthorized access: Environment mismatch."
                elif answer.form_submission.submitted_by != current_user: # Compare username strings
                    return False, "Unauthorized access: Not the submitter."

            # Check submission age for non-admin users
            if user_role != RoleType.ADMIN.value: # Compare with RoleType enum value
                submission_age = datetime.utcnow() - answer.form_submission.submitted_at
                if submission_age.days > 7:
                    return False, "Cannot delete answers from submissions older than 7 days"

            success, error_msg_or_success_msg = AnswerSubmittedService.delete_answer_submitted(answer_submitted_id) # Renamed for clarity
            if not success:
                return False, error_msg_or_success_msg or "Failed to delete answer submission"

            return True, error_msg_or_success_msg # This should be success message from service

        except Exception as e:
            logger.error(f"Error deleting answer submitted in controller: {str(e)}")
            return False, str(e)
            
    @staticmethod
    def get_table_structure(
        submission_id: int,
        question_text: str,
        current_user: str = None, # username string
        user_role: str = None # role name string
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get the structure of a table-type question response
        
        Args:
            submission_id: ID of the form submission
            question_text: Text of the table question
            current_user: Username of current user (string)
            user_role: Role of current user (string)
            
        Returns:
            tuple: (Dictionary with table structure or None, Error message or None)
        """
        try:
            # Resolve current_user (username string) to a User model instance for service call
            user_obj_for_service_call = None
            if current_user:
                user_obj_for_service_call = AuthService.get_current_user(current_user)
                if not user_obj_for_service_call:
                     return None, f"User '{current_user}' not found for authorization."
            
            # Get submission for access control (takes User object)
            submission = FormSubmissionService.get_submission(submission_id, user_obj_for_service_call)
            if not submission:
                return None, "Form submission not found or access denied"

            # If submission is accessible, proceed to get table structure
            # The original access control logic here was based on the resolved `submission` and string `current_user`/`user_role`.
            # This is largely handled by get_submission now.

            table_structure, error = AnswerSubmittedService.get_table_structure(submission_id, question_text)
            if error:
                return None, error
                
            return table_structure, None
            
        except Exception as e:
            error_msg = f"Error getting table structure in controller: {str(e)}"
            logger.error(error_msg)
            return None, error_msg