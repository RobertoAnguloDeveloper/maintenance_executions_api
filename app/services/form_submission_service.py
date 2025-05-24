from typing import Any, Dict, List, Optional, Tuple
from app import db
from app.models.form_submission import FormSubmission
from app.models.answer_submitted import AnswerSubmitted
from app.utils.permission_manager import RoleType
from app.models.attachment import Attachment
from app.models.form import Form
from app.models.user import User
from sqlalchemy.orm import joinedload, selectinload
from datetime import datetime
import logging
import os

# Import FormAssignmentService to use its access checking logic
from app.services.form_assignment_service import FormAssignmentService

logger = logging.getLogger(__name__)

class FormSubmissionService:
    @staticmethod
    def create_submission(
        form_id: int,
        username: str, # Username of the submitter
        answers_data: Optional[List[Dict]] = None, # Using Optional for clarity
        upload_path: Optional[str] = None,
        submitted_at: Optional[datetime] = None
    ) -> Tuple[Optional[FormSubmission], Optional[str]]:
        """
        Create a new form submission with answers and handle signatures.
        Access control (can user submit to this form?) should be handled by the caller (Controller/View)
        using FormAssignmentService.check_user_access_to_form().
        """
        try:
            form = Form.query.filter_by(id=form_id, is_deleted=False).first()
            if not form:
                return None, "Form not found or is inactive."

            # User performing the submission must exist
            submitter_user = User.query.filter_by(username=username, is_deleted=False).first()
            if not submitter_user:
                return None, f"User '{username}' not found or is inactive."

            submission = FormSubmission(
                form_id=form_id,
                submitted_by=username, # Storing username
                submitted_at=submitted_at or datetime.utcnow() # Use provided or current time
            )
            db.session.add(submission)
            db.session.flush() # To get submission.id for answers and attachments

            if answers_data:
                from app.services.answer_submitted_service import AnswerSubmittedService # Local import
                for answer_data in answers_data:
                    signature_file = answer_data.pop('signature_file', None) # Extract FileStorage if present
                    
                    # Ensure all required fields for AnswerSubmittedService are present
                    q_text = answer_data.get('question_text')
                    q_type_text = answer_data.get('question_type_text')
                    ans_text = answer_data.get('answer_text')

                    if not all([q_text, q_type_text]): # ans_text can be None for some types
                        db.session.rollback() # Rollback the whole submission
                        return None, f"Missing question_text or question_type_text for an answer."

                    _, error = AnswerSubmittedService.create_answer_submitted(
                        form_submission_id=submission.id,
                        question_text=q_text,
                        question_type_text=q_type_text,
                        answer_text=ans_text,
                        question_order=answer_data.get('question_order'),
                        is_signature=answer_data.get('is_signature', False),
                        signature_file=signature_file,
                        upload_path=upload_path,
                        column=answer_data.get('column'),
                        row=answer_data.get('row'),
                        cell_content=answer_data.get('cell_content')
                    )
                    if error:
                        db.session.rollback() # Rollback the whole submission if any answer fails
                        return None, f"Error creating submitted answer: {error}"
            
            db.session.commit()
            logger.info(f"Form submission ID {submission.id} created successfully for form {form_id} by user {username}.")
            return submission, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating form submission for form {form_id} by {username}: {str(e)}", exc_info=True)
            return None, "An unexpected error occurred while creating the submission."

    @staticmethod
    def get_all_submissions(user: User, filters: Optional[Dict] = None) -> List[FormSubmission]:
        """
        Get all form submissions, considering form access based on assignments
        and then applying role-based filters on submissions.
        """
        try:
            filters = filters or {}
            
            # Start with a base query for non-deleted submissions and non-deleted parent forms
            query = FormSubmission.query.join(Form, FormSubmission.form_id == Form.id)\
                                       .filter(FormSubmission.is_deleted == False, Form.is_deleted == False)

            # 1. Filter by forms accessible to the current user
            if not (user.role and user.role.is_super_user):
                accessible_form_ids = [form.id for form in FormAssignmentService.get_accessible_forms_for_user(user.id)]
                if not accessible_form_ids:
                    logger.debug(f"User {user.username} has no access to any forms. Returning no submissions.")
                    return [] # User has no access to any forms, thus no submissions
                query = query.filter(FormSubmission.form_id.in_(accessible_form_ids))
            
            # 2. Apply additional role-based filtering on the submissions themselves
            if not (user.role and user.role.is_super_user):
                if user.role.name == RoleType.TECHNICIAN:
                    # Technicians can only see their own submissions (within the forms they can access)
                    query = query.filter(FormSubmission.submitted_by == user.username)
                elif user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    # Site managers/supervisors see submissions from their environment
                    # (within the forms they can access)
                    query = query.join(User, User.username == FormSubmission.submitted_by)\
                                 .filter(User.environment_id == user.environment_id, User.is_deleted == False)
            
            # Apply optional filters from the request
            if 'form_id' in filters: # This can further narrow down from accessible forms
                query = query.filter(FormSubmission.form_id == filters['form_id'])
            
            if 'submitted_by' in filters: # Filter by specific submitter
                query = query.filter(FormSubmission.submitted_by == filters['submitted_by'])
            
            if 'date_range' in filters:
                date_range = filters['date_range']
                if date_range.get('start'): query = query.filter(FormSubmission.submitted_at >= date_range['start'])
                if date_range.get('end'): query = query.filter(FormSubmission.submitted_at <= date_range['end'])
            
            # Eager load related data for efficiency
            query = query.options(
                joinedload(FormSubmission.form), # Form details are often needed
                selectinload(FormSubmission.answers_submitted).filter_by(is_deleted=False), # Only active answers
                selectinload(FormSubmission.attachments).filter_by(is_deleted=False) # Only active attachments
            )
            
            submissions = query.order_by(FormSubmission.submitted_at.desc()).all()
            logger.info(f"Retrieved {len(submissions)} submissions for user {user.username} with filters: {filters}")
            return submissions

        except Exception as e:
            logger.error(f"Error in FormSubmissionService.get_all_submissions for user {user.username}: {str(e)}", exc_info=True)
            return []


    @staticmethod
    def get_batch(page: int = 1, per_page: int = 50, **filters: Any) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Get batch of form submissions with pagination, respecting new form access rules.
        Filters include: include_deleted (submissions), form_id, submitted_by, date_range, current_user.
        """
        try:
            current_user: Optional[User] = filters.get('current_user')
            if not current_user:
                logger.error("FormSubmissionService.get_batch called without 'current_user' in filters.")
                return 0, []

            query = FormSubmission.query.options(
                joinedload(FormSubmission.form), # Eager load form for title, etc.
                selectinload(FormSubmission.answers_submitted).filter_by(is_deleted=False),
                selectinload(FormSubmission.attachments).filter_by(is_deleted=False)
            ).join(Form, FormSubmission.form_id == Form.id).filter(Form.is_deleted == False)


            include_deleted_submissions = filters.get('include_deleted', False)
            if not include_deleted_submissions:
                query = query.filter(FormSubmission.is_deleted == False)
            # Note: if include_deleted_submissions is True, admins might see submissions for deleted forms if not filtered by Form.is_deleted

            # 1. Filter by forms accessible to the user
            if not (current_user.role and current_user.role.is_super_user):
                accessible_form_ids = [form.id for form in FormAssignmentService.get_accessible_forms_for_user(current_user.id)]
                if not accessible_form_ids:
                    return 0, []
                query = query.filter(FormSubmission.form_id.in_(accessible_form_ids))

            # 2. Apply other role-based filtering on submissions
            if not (current_user.role and current_user.role.is_super_user):
                if current_user.role.name == RoleType.TECHNICIAN:
                    query = query.filter(FormSubmission.submitted_by == current_user.username)
                elif current_user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    # Ensure User join is present if not already from other filters
                    if User not in [j.entity.class_ for j in query._legacy_setup_joins]: # Check if User is already joined
                         query = query.join(User, User.username == FormSubmission.submitted_by)
                    query = query.filter(User.environment_id == current_user.environment_id, User.is_deleted == False)
            
            # Apply other specific filters from request
            form_id_filter = filters.get('form_id')
            if form_id_filter:
                query = query.filter(FormSubmission.form_id == form_id_filter)
            
            submitted_by_filter = filters.get('submitted_by')
            if submitted_by_filter:
                query = query.filter(FormSubmission.submitted_by == submitted_by_filter)

            date_range = filters.get('date_range')
            if date_range:
                if date_range.get('start'): query = query.filter(FormSubmission.submitted_at >= date_range['start'])
                if date_range.get('end'): query = query.filter(FormSubmission.submitted_at <= date_range['end'])

            total_count = query.count() # Count after all filters
            total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 0
            page = max(1, min(page, total_pages if total_pages > 0 else 1))
            offset = (page - 1) * per_page

            form_submissions = query.order_by(FormSubmission.submitted_at.desc()).offset(offset).limit(per_page).all()
            
            compact_submissions = []
            for sub in form_submissions:
                sub_dict = {
                    'id': sub.id, 'form_id': sub.form_id,
                    'form': {'id': sub.form.id, 'title': sub.form.title} if sub.form else None,
                    'submitted_at': sub.submitted_at.isoformat() if sub.submitted_at else None,
                    'submitted_by': sub.submitted_by,
                    'status': sub.status, # Include status
                    'answers_count': len(sub.answers_submitted), # Eager loaded, so this is efficient
                    'attachments_count': len(sub.attachments), # Eager loaded
                    'is_editable': False # Default
                }
                # is_editable logic (can be complex, depends on business rules)
                if current_user:
                    is_super = current_user.role and current_user.role.is_super_user
                    is_submitter = sub.submitted_by == current_user.username
                    # Example: editable if superuser, or submitter within 7 days
                    can_edit_based_on_role_and_env = False
                    if not is_super and not is_submitter and current_user.role and current_user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                        submitter_obj = User.query.filter_by(username=sub.submitted_by, is_deleted=False).first()
                        if submitter_obj and submitter_obj.environment_id == current_user.environment_id:
                            can_edit_based_on_role_and_env = True
                    
                    time_limit_passed = (datetime.utcnow() - sub.submitted_at).days > 7 if sub.submitted_at else True

                    if is_super or \
                       (is_submitter and not time_limit_passed) or \
                       (can_edit_based_on_role_and_env and not time_limit_passed) :
                        sub_dict['is_editable'] = True
                compact_submissions.append(sub_dict)
            
            return total_count, compact_submissions
                
        except Exception as e:
            logger.error(f"Error in FormSubmissionService.get_batch: {str(e)}", exc_info=True)
            return 0, []

    @staticmethod
    def get_submission(submission_id: int, current_user: User) -> Optional[FormSubmission]:
        """
        Get a specific form submission if the user has access to its parent form.
        Additional submission-level RBAC can be applied here if needed.
        """
        try:
            submission = FormSubmission.query.options(
                joinedload(FormSubmission.form), # Eager load form to check access
                selectinload(FormSubmission.answers_submitted).filter_by(is_deleted=False),
                selectinload(FormSubmission.attachments).filter_by(is_deleted=False)
            ).filter_by(id=submission_id, is_deleted=False).first()

            if not submission:
                logger.warning(f"Submission ID {submission_id} not found or deleted.")
                return None

            # Check access to the parent form
            if not FormAssignmentService.check_user_access_to_form(current_user.id, submission.form_id):
                logger.warning(f"User {current_user.username} denied access to form {submission.form_id} for submission {submission_id}.")
                return None # User cannot access the form this submission belongs to

            # Apply further submission-specific RBAC if necessary
            if not (current_user.role and current_user.role.is_super_user):
                if current_user.role.name == RoleType.TECHNICIAN and submission.submitted_by != current_user.username:
                    logger.warning(f"Technician {current_user.username} denied access to submission {submission_id} by {submission.submitted_by}.")
                    return None
                elif current_user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    submitter = User.query.filter_by(username=submission.submitted_by, is_deleted=False).first()
                    if not submitter or submitter.environment_id != current_user.environment_id:
                        logger.warning(f"User {current_user.username} (SiteMgr/Supervisor) denied access to submission {submission_id} from different environment.")
                        return None
            
            logger.info(f"Submission ID {submission_id} retrieved successfully by user {current_user.username}.")
            return submission
        except Exception as e:
            logger.error(f"Error retrieving submission {submission_id} for user {current_user.username}: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def update_submission(
        submission_id: int,
        current_user: User, # Pass the User object
        update_data: Dict,
        answers_data: Optional[List[Dict]] = None,
        upload_path: Optional[str] = None
    ) -> Tuple[Optional[FormSubmission], Optional[str]]:
        """
        Update an existing form submission.
        Access control (can user update THIS submission?) should be handled by the caller (Controller/View)
        based on form access, submission ownership, role, and time limits.
        """
        try:
            submission = FormSubmission.query.filter_by(id=submission_id, is_deleted=False).first()
            if not submission:
                return None, "Submission not found or has been deleted."

            # Authorization should be performed by the controller before calling this.
            # Example checks that would be in controller:
            # if not FormAssignmentService.check_user_access_to_form(current_user.id, submission.form_id): return None, "Access Denied"
            # if not (current_user.role.is_super_user or (submission.submitted_by == current_user.username and not time_limit_exceeded)): return None, "Update conditions not met"

            submission.updated_at = datetime.utcnow()
            if 'status' in update_data:
                submission.status = update_data['status']

            if answers_data:
                from app.services.answer_submitted_service import AnswerSubmittedService # Local import
                processed_answer_ids = []
                for answer_data in answers_data:
                    answer_id = answer_data.get('id')
                    signature_file = answer_data.pop('signature_file', None)
                    q_text = answer_data.get('question_text')
                    q_type_text = answer_data.get('question_type_text')
                    ans_text = answer_data.get('answer_text')

                    if not all([q_text, q_type_text]):
                        db.session.rollback()
                        return None, f"Missing question_text or question_type_text for an answer during update."

                    if answer_id: # Update existing answer
                        existing_answer = AnswerSubmitted.query.filter_by(id=answer_id, form_submission_id=submission_id, is_deleted=False).first()
                        if existing_answer:
                            _, error = AnswerSubmittedService.update_answer_submitted(
                                answer_submitted_id=existing_answer.id,
                                answer_text=ans_text, # Pass only relevant fields
                                question_order=answer_data.get('question_order'),
                                column=answer_data.get('column'),
                                row=answer_data.get('row'),
                                cell_content=answer_data.get('cell_content')
                            )
                            if error: raise ValueError(f"Error updating answer ID {answer_id}: {error}")
                            processed_answer_ids.append(existing_answer.id)
                    else: # Create new answer
                        new_ans, error = AnswerSubmittedService.create_answer_submitted(
                            form_submission_id=submission.id, question_text=q_text, question_type_text=q_type_text,
                            answer_text=ans_text, question_order=answer_data.get('question_order'),
                            is_signature=answer_data.get('is_signature', False), signature_file=signature_file,
                            upload_path=upload_path, column=answer_data.get('column'), row=answer_data.get('row'),
                            cell_content=answer_data.get('cell_content')
                        )
                        if error: raise ValueError(f"Error creating new answer: {error}")
                        if new_ans: processed_answer_ids.append(new_ans.id)
                
                if update_data.get('delete_unprocessed_answers'):
                    AnswerSubmitted.query.filter(
                        AnswerSubmitted.form_submission_id == submission_id,
                        AnswerSubmitted.is_deleted == False,
                        ~AnswerSubmitted.id.in_(processed_answer_ids)
                    ).update({"is_deleted": True, "deleted_at": datetime.utcnow()}, synchronize_session=False)

            db.session.commit()
            logger.info(f"Submission ID {submission_id} updated by user {current_user.username}.")
            return submission, None
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating form submission ID {submission_id}: {str(e)}", exc_info=True)
            return None, "An unexpected error occurred while updating the submission."

    @staticmethod
    def delete_submission(submission_id: int, current_user: User) -> Tuple[bool, Optional[str]]:
        """
        Soft delete a submission.
        Access control should be handled by the caller.
        """
        try:
            submission = FormSubmission.query.filter_by(id=submission_id, is_deleted=False).first()
            if not submission:
                return False, "Submission not found or already deleted."

            # Authorization should be done by the controller.
            # Example: if not (current_user.role.is_super_user or (submission.submitted_by == current_user.username and not time_limit_exceeded)): return False, "Permission denied"

            # Soft delete the submission itself. Associated answers/attachments are not deleted here by default.
            # If cascading soft delete of answers/attachments is needed, that logic would be added.
            submission.soft_delete()
            db.session.commit()
            logger.info(f"Submission ID {submission_id} soft-deleted by user {current_user.username}.")
            return True, None
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting submission ID {submission_id}: {str(e)}", exc_info=True)
            return False, "An unexpected error occurred while deleting the submission."

    # get_submission_answers and update_submission_status remain largely the same,
    # assuming access to the parent submission is checked by the controller.
    @staticmethod
    def get_submission_answers(submission_id: int, current_user: User) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Get all active answers for a specific submission, if user has access to the submission."""
        submission = FormSubmissionService.get_submission(submission_id, current_user) # This now checks form access
        if not submission:
            return [], "Submission not found or access denied."
        
        # answers_submitted relationship is already filtered for is_deleted=False by eager loading options
        answers_data = [ans.to_dict() for ans in submission.answers_submitted]
        return answers_data, None

    @staticmethod
    def update_submission_status(submission_id: int, status: str, current_user: User) -> Tuple[Optional[FormSubmission], Optional[str]]:
        """Update submission status, if user has access."""
        # Access control for updating status should be in the controller.
        # Typically, more roles than just the submitter might be able to change status.
        submission = FormSubmissionService.get_submission(submission_id, current_user)
        if not submission:
            return None, "Submission not found or access denied to update status."
        
        # Add specific role checks here if only certain roles can update status
        # e.g., if not current_user.role.is_super_user and current_user.role.name not in [RoleType.SITE_MANAGER]:
        #    return None, "Permission denied to update submission status."

        try:
            submission.status = status
            submission.updated_at = datetime.utcnow()
            db.session.commit()
            logger.info(f"Status of submission ID {submission_id} updated to '{status}' by user {current_user.username}.")
            return submission, None
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating status for submission {submission_id}: {str(e)}", exc_info=True)
            return None, "Failed to update submission status."

