from datetime import datetime
from typing import Dict, List, Optional, Tuple
from flask import current_app
from app.models.form import Form
from app.models.user import User as UserModel # Renamed to avoid conflict with variable 'user'
from app.models.form_submission import FormSubmission
from app.services.form_submission_service import FormSubmissionService
from app.services.auth_service import AuthService # Import AuthService
from app.utils.permission_manager import RoleType # Assuming RoleType is imported for comparisons
import logging

logger = logging.getLogger(__name__)

class FormSubmissionController:
    @staticmethod
    def create_submission(
        form_id: int,
        username: str, # username string from JWT
        answers_data: Optional[List[Dict]] = None,
        submitted_at: Optional[datetime] = None
    ) -> Tuple[Optional[FormSubmission], Optional[str]]:
        try:
            form = Form.query.filter_by(id=form_id, is_deleted=False).first()
            if not form:
                return None, "Form not found"

            upload_path = current_app.config.get('UPLOAD_FOLDER')

            submission, error = FormSubmissionService.create_submission(
                form_id=form_id,
                username=username, # Service expects username string
                answers_data=answers_data,
                upload_path=upload_path,
                submitted_at=submitted_at
            )
            
            if error:
                return None, error
            return submission, None
        except Exception as e:
            logger.exception(f"Error in create_submission controller: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_all_submissions(
        user: UserModel, # Expecting User OBJECT from view
        filters: Dict = None
    ) -> List[FormSubmission]:
        try:
            # The filters dict might be modified or passed as-is to the service.
            # The service's get_all_submissions already handles RBAC based on the passed User object.
            return FormSubmissionService.get_all_submissions(user, filters or {})
        except Exception as e:
            logger.exception(f"Error in get_all_submissions controller: {str(e)}")
            return []
        
    @staticmethod
    def get_all_submissions_compact(
        user: UserModel, # Expecting User OBJECT from view
        filters: Dict = None
    ) -> List[Dict]:
        try:
            # Assuming FormSubmissionService.get_all_submissions_compact exists
            # or this logic is handled by get_batch or by compacting full submissions.
            # For now, maintaining consistency with get_all_submissions.
            # The service method FormSubmissionService.get_batch returns compact data.
            # This method might be better served by calling get_batch and returning its items.
            # For now, to align with previous structure if it was calling a non-existent compact service:
            submissions = FormSubmissionService.get_all_submissions(user, filters or {})
            return [sub.to_dict_basic() for sub in submissions] # Example
        except Exception as e:
            logger.exception(f"Error in get_all_submissions_compact controller: {str(e)}")
            return []
        
    @staticmethod
    def get_batch(page=1, per_page=50, **filters):
        # The view should pass 'current_user' as a User object in filters.
        # FormSubmissionService.get_batch expects 'current_user': User object.
        return FormSubmissionService.get_batch(page, per_page, **filters)

    @staticmethod
    def get_submission(submission_id: int, current_user_identity: str) -> Optional[FormSubmission]:
        """Get a specific submission. current_user_identity is the JWT username string."""
        try:
            user_obj = AuthService.get_current_user(current_user_identity) #
            if not user_obj:
                logger.warning(f"User identity '{current_user_identity}' not found for get_submission.")
                return None 
                
            # FormSubmissionService.get_submission handles access checks using the user_obj
            return FormSubmissionService.get_submission(submission_id, current_user=user_obj) #
        except Exception as e:
            logger.exception(f"Error getting submission {submission_id}: {str(e)}")
            return None
        
    @staticmethod
    def get_user_submissions(
        username: str, # Target username
        # current_requesting_user_identity: str, # This would be needed if complex auth is done here
        filters: Optional[Dict] = None
    ) -> Tuple[List[FormSubmission], Optional[str]]:
        try:
            # This controller method fetches submissions for a specific 'username'.
            # Authorization (who can call this for whom) should ideally be handled in the view
            # or by passing the 'requesting_user_object' to the service if the service needs it.
            # The provided FormSubmissionService.get_submissions_by_user (if it exists)
            # or get_all_submissions (with user_obj of the *target user* for their own data, 
            # or an admin user_obj to see anyone's data based on filters) would be used.

            # Assuming the view has authorized the requesting user.
            # To get submissions *by* a specific username using get_all_submissions:
            target_user_obj = AuthService.get_current_user(username) #
            if not target_user_obj:
                return [], f"Target user '{username}' not found."

            effective_filters = filters or {}
            # If using get_all_submissions, it needs the User object for RBAC.
            # If the intent is "get all submissions visible to 'target_user_obj' that were submitted by 'username'",
            # then target_user_obj is passed to get_all_submissions.
            # If it's "get all submissions submitted by 'username', with visibility determined by 'requesting_user_obj'",
            # then requesting_user_obj is passed.

            # Given the method name, it's likely "get all submissions *submitted by* username".
            # The get_all_submissions service method already filters by current_user if they are not admin.
            # If an admin is calling this, they should be able to see it.
            # If the user themselves are calling this, it should also work.
            
            # For simplicity and consistency, if this is meant for general fetch by username,
            # and the current_user requesting it has view permissions:
            # We'll assume `get_all_submissions` is the primary fetch mechanism and add a filter.
            
            # This needs the *requesting user's User object* if get_all_submissions is used.
            # The current signature of this controller method doesn't take the *requesting user*.
            # This is a design consideration. For now, let's assume the view ensures only authorized
            # users (e.g., the user themselves or an admin) call this endpoint.
            # The service `get_all_submissions` uses its `user` param for RBAC.

            # If we assume the `user` passed to `get_all_submissions` defines the visibility scope:
            # Option 1: Scope is defined by the target user (they see what they are allowed to see of their own)
            # user_for_rbac = target_user_obj

            # Option 2: Scope is defined by an implicit "current requesting user" (not passed to this method)
            # This controller method needs the requesting user's identity if it's to use get_all_submissions
            # in a context other than the target user viewing their own.

            # For now, aligning with how other methods pass User object to service:
            # The `get_my_submissions` view calls this with `current_user_jwt_identity` as `username`.
            requesting_user_obj = AuthService.get_current_user(username) #
            if not requesting_user_obj:
                 return [], f"User {username} not found for permission context."

            effective_filters['submitted_by'] = username
            submissions = FormSubmissionService.get_all_submissions(user=requesting_user_obj, filters=effective_filters)
            return submissions, None

        except Exception as e:
            error_msg = f"Error getting user submissions for '{username}': {str(e)}"
            logger.exception(error_msg)
            return [], error_msg

    @staticmethod
    def get_submission_answers(
        submission_id: int,
        current_user_identity: str, # username string from view
        user_role_name: str      # role name string from view (unused by service call below)
    ) -> Tuple[List[Dict], Optional[str]]:
        try:
            user_obj = AuthService.get_current_user(current_user_identity) #
            if not user_obj:
                return [], f"User '{current_user_identity}' not found for fetching submission answers."

            # Corrected: Call FormSubmissionService.get_submission_answers with User object
            # It does not take user_role_name as a parameter.
            answers_data, error_msg = FormSubmissionService.get_submission_answers(
                submission_id=submission_id,
                current_user=user_obj  # Pass the resolved User object
            )
            
            if error_msg:
                return [], error_msg
            
            return answers_data, None

        except Exception as e:
            logger.exception(f"Error getting submission answers for ID {submission_id} in controller: {str(e)}") #
            return [], str(e)
        
    @staticmethod
    def update_submission(
        submission_id: int,
        current_user_identity: str, 
        user_role_name: str, # Used for controller-level auth checks if any
        update_data: Dict,
        answers_data: Optional[List[Dict]] = None
    ) -> Tuple[Optional[FormSubmission], Optional[str]]:
        try:
            user_obj = AuthService.get_current_user(current_user_identity) #
            if not user_obj:
                return None, f"User '{current_user_identity}' not found for update operation."

            # Perform controller-level authorization if necessary, using user_obj and user_role_name.
            # Example:
            # submission_to_check = FormSubmissionService.get_submission(submission_id, user_obj)
            # if not submission_to_check:
            #     return None, "Submission not found or access denied for update."
            # if user_role_name != RoleType.ADMIN.value and submission_to_check.submitted_by != user_obj.username:
            #     # Add more granular checks based on role, environment, time limits etc.
            #     return None, "Permission denied to update this submission."

            submission, error = FormSubmissionService.update_submission(
                submission_id=submission_id,
                current_user=user_obj, # Pass User object
                update_data=update_data,
                answers_data=answers_data,
                upload_path=current_app.config.get('UPLOAD_FOLDER')
            )
            
            if error:
                return None, error
            return submission, None
        except Exception as e:
            logger.exception(f"Error in update_submission controller for ID {submission_id}: {str(e)}")
            return None, str(e)

    @staticmethod
    def delete_submission(
        submission_id: int,
        current_user_identity: str, 
        user_role_name: str # Used for controller-level auth checks if any
    ) -> Tuple[bool, Optional[str]]:
        try:
            user_obj = AuthService.get_current_user(current_user_identity) #
            if not user_obj:
                return False, f"User '{current_user_identity}' not found for delete operation."

            # Perform controller-level authorization similar to update_submission if needed.
            # submission_to_check = FormSubmissionService.get_submission(submission_id, user_obj)
            # if not submission_to_check:
            #    return False, "Submission not found or access denied for delete."
            # ... (additional permission checks based on user_obj and user_role_name)

            return FormSubmissionService.delete_submission(
                submission_id=submission_id,
                current_user=user_obj # Pass User object
            )
        except Exception as e:
            logger.exception(f"Error deleting submission ID {submission_id}: {str(e)}")
            return False, str(e)