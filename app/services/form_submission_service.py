from typing import Any, Dict, List, Optional, Tuple
from app import db
from app.models.form_submission import FormSubmission
from app.models.answer_submitted import AnswerSubmitted
from app.utils.permission_manager import RoleType
from app.models.attachment import Attachment
from app.models.form import Form
from app.models.user import User
from sqlalchemy.orm import joinedload, selectinload
from datetime import datetime, time, timezone
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
        Ensures necessary relationships are loaded for compact view.
        """
        try:
            filters = filters or {}
            
            query = FormSubmission.query.join(Form, FormSubmission.form_id == Form.id)\
                                       .filter(FormSubmission.is_deleted == False, Form.is_deleted == False)

            if not (user.role and user.role.is_super_user):
                accessible_form_ids = [form.id for form in FormAssignmentService.get_accessible_forms_for_user(user.id)]
                if not accessible_form_ids:
                    logger.debug(f"User {user.username} has no access to any forms. Returning no submissions.")
                    return [] 
                query = query.filter(FormSubmission.form_id.in_(accessible_form_ids))
            
            if not (user.role and user.role.is_super_user):
                if user.role.name == RoleType.TECHNICIAN:
                    query = query.filter(FormSubmission.submitted_by == user.username)
                elif user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    # Join with User model to filter by environment_id of the 'submitted_by' user
                    # Using an alias for the User table in this join to avoid conflicts if User is already joined.
                    SubmitterUser = db.aliased(User)
                    query = query.join(SubmitterUser, SubmitterUser.username == FormSubmission.submitted_by)\
                                 .filter(SubmitterUser.environment_id == user.environment_id, SubmitterUser.is_deleted == False)
            
            if 'form_id' in filters: 
                query = query.filter(FormSubmission.form_id == filters['form_id'])
            
            # Eager load relationships needed for to_compact_dict() and sorting
            query = query.options(
                joinedload(FormSubmission.form), # For form.title
                selectinload(FormSubmission.answers_submitted), # For answers_count
                selectinload(FormSubmission.attachments) # For attachments_count & signatures_count
            )
            
            submissions = query.all() # Get all matching submissions before Python-side sort/filter
            # The original query had .order_by(FormSubmission.submitted_at.desc()), 
            # we will apply sorting after potential date filtering in the compact method
            logger.info(f"Retrieved {len(submissions)} submissions for user {user.username} with filters: {filters} before compact processing.")
            return submissions

        except Exception as e:
            logger.error(f"Error in FormSubmissionService.get_all_submissions for user {user.username}: {str(e)}", exc_info=True)
            return []
        
    @staticmethod
    def get_all_submissions_compact_filtered_sorted(
        user: User, 
        start_date_str: Optional[str] = None,
        end_date_str: Optional[str] = None,
        sort_by: Optional[str] = 'submitted_at', # Default sort field
        sort_order: Optional[str] = 'desc',     # Default sort order
        form_id_filter: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        try:
            initial_filters = {}
            if form_id_filter:
                initial_filters['form_id'] = form_id_filter
            
            # Step 1: Fetch all accessible FormSubmission objects
            # get_all_submissions loads necessary relationships (form, answers_submitted, attachments)
            accessible_submissions = FormSubmissionService.get_all_submissions(user, initial_filters)

            # Step 2: Apply date filtering for 'submitted_at' in Python
            filtered_submissions: List[FormSubmission] = []
            if start_date_str and end_date_str:
                try:
                    start_dt: datetime
                    end_dt: datetime

                    if 'T' not in start_date_str:
                        start_dt_naive = datetime.strptime(start_date_str, "%Y-%m-%d")
                        start_dt = datetime.combine(start_dt_naive.date(), time.min, tzinfo=timezone.utc)
                    else:
                        start_dt = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                        if start_dt.tzinfo is None or start_dt.tzinfo.utcoffset(start_dt) is None:
                            start_dt = start_dt.replace(tzinfo=timezone.utc)

                    if 'T' not in end_date_str:
                        end_dt_naive = datetime.strptime(end_date_str, "%Y-%m-%d")
                        end_dt = datetime.combine(end_dt_naive.date(), time.max, tzinfo=timezone.utc)
                    else:
                        end_dt = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                        if end_dt.tzinfo is None or end_dt.tzinfo.utcoffset(end_dt) is None:
                            end_dt = end_dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    logger.warning(f"Invalid date format for submission filter: start='{start_date_str}', end='{end_date_str}'")
                    return [], "Invalid date format. Use YYYY-MM-DD or full ISO format."

                for sub in accessible_submissions:
                    if sub.submitted_at:
                        sub_date_aware: datetime
                        if sub.submitted_at.tzinfo is None or sub.submitted_at.tzinfo.utcoffset(sub.submitted_at) is None:
                            sub_date_aware = sub.submitted_at.replace(tzinfo=timezone.utc)
                        else:
                            sub_date_aware = sub.submitted_at.astimezone(timezone.utc)
                        
                        if start_dt <= sub_date_aware <= end_dt:
                            filtered_submissions.append(sub)
            else:
                filtered_submissions = accessible_submissions # No date filter, use all accessible
            
            # Step 3: Apply sorting in Python
            reverse_sort = (sort_order == 'desc')

            def get_sort_key_submission(sub_obj: FormSubmission) -> Any:
                min_utc_datetime = datetime.min.replace(tzinfo=timezone.utc)
                
                if sort_by == 'submitted_by':
                    return (sub_obj.submitted_by or "").lower()
                elif sort_by == 'form_title': # Ensure form object is loaded
                    return (sub_obj.form.title or "").lower() if sub_obj.form else ""
                # Default to submitted_at
                sub_dt_to_sort = sub_obj.submitted_at
                if sub_dt_to_sort is None: return min_utc_datetime
                
                # Ensure consistent timezone (UTC) for sorting
                if sub_dt_to_sort.tzinfo is None or sub_dt_to_sort.tzinfo.utcoffset(sub_dt_to_sort) is None:
                    return sub_dt_to_sort.replace(tzinfo=timezone.utc)
                return sub_dt_to_sort.astimezone(timezone.utc)

            filtered_submissions.sort(key=get_sort_key_submission, reverse=reverse_sort)

            # Step 4: Convert to compact dict using the new method
            compact_submission_list = [sub.to_compact_dict() for sub in filtered_submissions]
            
            return compact_submission_list, None

        except Exception as e:
            user_id_for_log = user.id if user else "Unknown"
            logger.error(f"Error in FormSubmissionService.get_all_submissions_compact_filtered_sorted for user {user_id_for_log}: {str(e)}", exc_info=True)
            return [], "An unexpected error occurred while retrieving compact submission list."

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
                joinedload(FormSubmission.form),
                selectinload(FormSubmission.answers_submitted),
                selectinload(FormSubmission.attachments)
            ).join(Form, FormSubmission.form_id == Form.id).filter(Form.is_deleted == False)


            include_deleted_submissions = filters.get('include_deleted', False)
            if not include_deleted_submissions:
                query = query.filter(FormSubmission.is_deleted == False)

            if not (current_user.role and current_user.role.is_super_user):
                accessible_form_ids = [form.id for form in FormAssignmentService.get_accessible_forms_for_user(current_user.id)]
                if not accessible_form_ids:
                    return 0, []
                query = query.filter(FormSubmission.form_id.in_(accessible_form_ids))

            if not (current_user.role and current_user.role.is_super_user):
                if current_user.role.name == RoleType.TECHNICIAN:
                    query = query.filter(FormSubmission.submitted_by == current_user.username)
                elif current_user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    # --- FIX STARTS HERE ---
                    # Remove the check for _legacy_setup_joins and perform the join.
                    # SQLAlchemy can handle joins, and we need this join for the filter below.
                    query = query.join(User, User.username == FormSubmission.submitted_by)
                    # --- FIX ENDS HERE ---
                    query = query.filter(User.environment_id == current_user.environment_id, User.is_deleted == False)

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

            total_count = query.count()
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
                    'status': getattr(sub, 'status', 'N/A'),
                    'answers_count': sum(1 for ans in sub.answers_submitted if not ans.is_deleted),
                    'attachments_count': sum(1 for att in sub.attachments if not att.is_deleted),
                    'is_editable': False
                }
                if current_user:
                    is_super = current_user.role and current_user.role.is_super_user
                    is_submitter = sub.submitted_by == current_user.username
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
            logger.error(f"Error in FormSubmissionService.get_batch: {str(e)}", exc_info=True) #
            return 0, []

    @staticmethod
    def get_submission(submission_id: int, current_user: User) -> Optional[FormSubmission]:
        """
        Get a specific form submission if the user has access to its parent form.
        Additional submission-level RBAC can be applied here if needed.
        """
        try:
            submission = FormSubmission.query.options(
                joinedload(FormSubmission.form),
                selectinload(FormSubmission.answers_submitted),
                selectinload(FormSubmission.attachments)
            ).filter_by(id=submission_id, is_deleted=False).first()

            if not submission:
                logger.warning(f"Submission ID {submission_id} not found or deleted.")
                return None

            if not FormAssignmentService.check_user_access_to_form(current_user.id, submission.form_id):
                logger.warning(f"User {current_user.username} denied access to form {submission.form_id} for submission {submission_id}.")
                return None

            if not (current_user.role and current_user.role.is_super_user):
                if current_user.role.name == RoleType.TECHNICIAN and submission.submitted_by != current_user.username:
                    logger.warning(f"Technician {current_user.username} denied access to submission {submission_id} by {submission.submitted_by}.")
                    return None
                elif current_user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    submitter = User.query.filter_by(username=submission.submitted_by, is_deleted=False).first()
                    if not submitter or submitter.environment_id != current_user.environment_id:
                        logger.warning(f"User {current_user.username} (SiteMgr/Supervisor) denied access to submission {submission_id} from different environment.")
                        return None

            logger.info(f"Submission ID {submission_id} retrieved successfully by user {current_user.username}.") #
            return submission
        except Exception as e:
            logger.error(f"Error retrieving submission {submission_id} for user {current_user.username}: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def update_submission(
        submission_id: int,
        current_user: User,
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

            submission.updated_at = datetime.utcnow()
            # Safely update status only if 'status' field exists and is in update_data
            if 'status' in update_data and hasattr(submission, 'status'):
                submission.status = update_data['status']
            elif 'status' in update_data:
                logger.warning(f"Attempted to update 'status' for submission ID {submission_id}, but FormSubmission model has no 'status' attribute.")


            if answers_data:
                from app.services.answer_submitted_service import AnswerSubmittedService
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

                    if answer_id:
                        existing_answer = AnswerSubmitted.query.filter_by(id=answer_id, form_submission_id=submission_id, is_deleted=False).first()
                        if existing_answer:
                            _, error = AnswerSubmittedService.update_answer_submitted(
                                answer_submitted_id=existing_answer.id,
                                answer_text=ans_text,
                                question_order=answer_data.get('question_order'),
                                column=answer_data.get('column'),
                                row=answer_data.get('row'),
                                cell_content=answer_data.get('cell_content')
                            )
                            if error: raise ValueError(f"Error updating answer ID {answer_id}: {error}")
                            processed_answer_ids.append(existing_answer.id)
                    else:
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

            submission.soft_delete()
            db.session.commit()
            logger.info(f"Submission ID {submission_id} soft-deleted by user {current_user.username}.")
            return True, None
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting submission ID {submission_id}: {str(e)}", exc_info=True)
            return False, "An unexpected error occurred while deleting the submission."

    @staticmethod
    def get_submission_answers(submission_id: int, current_user: User) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Get all active answers for a specific submission, if user has access to the submission."""
        submission = FormSubmissionService.get_submission(submission_id, current_user)
        if not submission:
            return [], "Submission not found or access denied."

        answers_data = [ans.to_dict() for ans in submission.answers_submitted if not ans.is_deleted]
        return answers_data, None

    @staticmethod
    def update_submission_status(submission_id: int, status: str, current_user: User) -> Tuple[Optional[FormSubmission], Optional[str]]:
        """Update submission status, if user has access."""
        submission = FormSubmissionService.get_submission(submission_id, current_user)
        if not submission:
            return None, "Submission not found or access denied to update status."

        # Safely update status only if 'status' field exists
        if hasattr(submission, 'status'):
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
        else:
            logger.warning(f"Attempted to update 'status' for submission ID {submission_id}, but FormSubmission model has no 'status' attribute.")
            return None, "Cannot update status: 'status' attribute does not exist on FormSubmission."