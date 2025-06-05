# app/services/form_service.py

from datetime import datetime, time, timezone
from typing import Dict, List, Optional, Tuple, Union, Any
from app.models.answer import Answer
from app.models.answer_submitted import AnswerSubmitted
from app.models.attachment import Attachment
from app.models.form_answer import FormAnswer
from app.models.form_assignment import FormAssignment
from app.models.form_submission import FormSubmission
from app.models.question import Question
from app.models.question_type import QuestionType
from app.models.user import User
from app.services.base_service import BaseService
from app.models.form import Form
from app.models.form_question import FormQuestion
from app import db # Assuming db is initialized in app
from sqlalchemy.orm import joinedload, selectinload, contains_eager
from sqlalchemy.exc import IntegrityError
import logging

# Import the FormAssignmentService to use its access check logic
from app.services.form_assignment_service import FormAssignmentService
from app.utils.permission_manager import RoleType # Assuming RoleType is available

logger = logging.getLogger(__name__)

class FormService(BaseService):
    def __init__(self):
        super().__init__(Form)

    @classmethod
    def _get_base_query(cls, include_creator_env=True, include_questions=True):
        """Base query with common joins and filters, with options to include joins."""
        query = Form.query
        if include_creator_env:
            query = query.options(joinedload(Form.creator).joinedload(User.environment))
        if include_questions:
            query = query.options(
                joinedload(Form.form_questions)
                    .joinedload(FormQuestion.question)
                    .joinedload(Question.question_type)
            )
        return query.filter(Form.is_deleted == False)


    @classmethod
    def _handle_transaction(cls, operation: callable, *args, **kwargs) -> Tuple[Optional[Any], Optional[str]]:
        """Generic transaction handler"""
        try:
            result = operation(*args, **kwargs)
            db.session.commit()
            return result, None
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Database integrity error: {str(e.orig)}") # Log original error for details
            if "forms_title_key" in str(e.orig).lower() or ("unique constraint" in str(e.orig).lower() and "title" in str(e.orig).lower()):
                 return None, "A form with this title already exists."
            elif "forms_user_id_fkey" in str(e.orig).lower():
                 return None, "Invalid user ID provided for form creation."
            return None, "A database integrity error occurred. Please check your input."
        except ValueError as ve: # Catch specific ValueErrors raised by operations
            db.session.rollback()
            logger.warning(f"Validation error during operation: {str(ve)}")
            return None, str(ve)
        except Exception as e:
            db.session.rollback()
            logger.error(f"Operation error: {str(e)}", exc_info=True)
            return None, "An unexpected error occurred."

    @staticmethod
    def get_all_forms(user: User, is_public: Optional[bool] = None) -> List[Form]:
        """
        Get all forms accessible to the user, respecting assignments.
        Admins see all forms (can be filtered by is_public).
        Other users see forms based on FormAssignmentService logic.
        """
        try:
            if user.role and user.role.is_super_user:
                # Admins see all non-deleted forms, optionally filtered by is_public
                query = FormService._get_base_query()
                if is_public is not None:
                    query = query.filter(Form.is_public == is_public)
                return query.order_by(Form.created_at.desc()).all()
            else:
                # For non-admins, use FormAssignmentService to get all accessible forms
                # This list already respects all assignment rules, creator access, and admin override (though admin handled above).
                accessible_forms = FormAssignmentService.get_accessible_forms_for_user(user.id)

                # Further filter this list if is_public parameter is provided
                if is_public is not None:
                    accessible_forms = [form for form in accessible_forms if form.is_public == is_public]

                # Sort the final list (get_accessible_forms_for_user might already sort, but good to be explicit)
                return sorted(accessible_forms, key=lambda f: f.created_at, reverse=True)

        except Exception as e:
            logger.error(f"Error in FormService.get_all_forms for user {user.id if user else 'Unknown'}: {str(e)}", exc_info=True)
            raise # Or return [] depending on desired error handling for controllers

    @staticmethod
    def get_all_forms_basic_info(current_user: User) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Get basic information (id, title, description, user_id, is_public, attachments_required)
        for all forms accessible to the current_user.
        """
        try:
            accessible_forms = FormAssignmentService.get_accessible_forms_for_user(current_user.id)
            if accessible_forms is None: # Should not happen if service returns [] on error
                return [], "Error retrieving accessible forms."

            # Using to_dict_basic which includes the required fields.
            # If a more stripped-down version is needed, a new method in Form model could be created.
            basic_forms_info = [form.to_dict_basic() for form in accessible_forms]
            
            # If you strictly want ONLY the specified fields and nothing else from to_dict_basic:
            # required_keys = ['id', 'title', 'description', 'user_id', 'is_public', 'attachments_required']
            # filtered_basic_forms_info = []
            # for form_dict in basic_forms_info:
            #     filtered_dict = {key: form_dict.get(key) for key in required_keys}
            #     filtered_basic_forms_info.append(filtered_dict)
            # return filtered_basic_forms_info, None
            
            return basic_forms_info, None
            
        except Exception as e:
            logger.error(f"Error in FormService.get_all_forms_basic_info for user {current_user.id}: {str(e)}", exc_info=True)
            return [], "An unexpected error occurred while retrieving basic form information."


    @staticmethod
    def get_batch(page: int = 1, per_page: int = 50, **filters: Any) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Get batch of forms with pagination, respecting new access rules.
        Filters include: include_deleted, is_public, user_id (creator), environment_id, current_user, only_editable.
        """
        try:
            current_user: Optional[User] = filters.get('current_user')
            if not current_user:
                logger.error("FormService.get_batch called without 'current_user' in filters.")
                return 0, []

            # Base query with common options, initially not filtering by is_deleted yet
            query = Form.query.options(
                joinedload(Form.creator).joinedload(User.environment),
                joinedload(Form.form_questions).joinedload(FormQuestion.question).joinedload(Question.question_type)
            )

            # Apply access control first for non-admins
            if not (current_user.role and current_user.role.is_super_user):
                accessible_form_ids = [form.id for form in FormAssignmentService.get_accessible_forms_for_user(current_user.id)]
                if not accessible_form_ids: # User has no access to any forms
                    return 0, []
                query = query.filter(Form.id.in_(accessible_form_ids))

            # Now apply standard filters
            include_deleted = filters.get('include_deleted', False)
            if not include_deleted:
                query = query.filter(Form.is_deleted == False)
            else: # If include_deleted is true, superuser check might be needed if not already implied
                if not (current_user.role and current_user.role.is_super_user):
                    # Non-admins should not be able to force include_deleted=True if they don't own the form.
                    # The accessible_form_ids logic already filters by non-deleted forms.
                    # This path (include_deleted=True for non-admin) should ideally not occur or be restricted.
                    logger.warning(f"Non-admin user {current_user.username} attempted to list deleted forms via get_batch.")
                    # Force is_deleted == False for non-admins if they pass include_deleted=True
                    query = query.filter(Form.is_deleted == False)


            is_public_filter = filters.get('is_public')
            if is_public_filter is not None:
                query = query.filter(Form.is_public == is_public_filter)

            creator_user_id = filters.get('user_id') # Filter by form's creator
            if creator_user_id:
                query = query.filter(Form.user_id == creator_user_id)

            environment_id_filter = filters.get('environment_id') # Filter by creator's environment
            if environment_id_filter:
                query = query.join(User, User.id == Form.user_id).filter(User.environment_id == environment_id_filter)

            only_editable = filters.get('only_editable', False)
            if only_editable and not (current_user.role and current_user.role.is_super_user):
                # Non-admins can only edit their own forms from the set they can access
                query = query.filter(Form.user_id == current_user.id)

            total_count = query.count()
            total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 0
            page = max(1, min(page, total_pages if total_pages > 0 else 1)) # Ensure page is within bounds
            offset = (page - 1) * per_page

            forms = query.order_by(Form.id.desc()).offset(offset).limit(per_page).all()
            forms_data = [form.to_batch_dict() for form in forms] # Uses a simplified dict for batch views

            # Add 'is_editable' flag based on current user
            for form_dict in forms_data:
                is_super = current_user.role and current_user.role.is_super_user
                is_creator = form_dict.get('created_by', {}).get('id') == current_user.id
                form_dict['is_editable'] = is_super or is_creator

            return total_count, forms_data

        except Exception as e:
            logger.error(f"Error in FormService.get_batch: {str(e)}", exc_info=True)
            return 0, []
        
    @staticmethod
    def get_all_forms_compact_filtered_sorted(
        current_user: User,
        date_filter_field: Optional[str] = None,
        start_date_str: Optional[str] = None,
        end_date_str: Optional[str] = None,
        sort_by: Optional[str] = 'updated_at',
        sort_order: Optional[str] = 'desc',
        only_editable: bool = False # Add new parameter
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        try:
            # 1. Get all forms accessible to the user (list of Form objects)
            accessible_forms: List[Form] = FormAssignmentService.get_accessible_forms_for_user(current_user.id)
            if accessible_forms is None:
                logger.info(f"No accessible forms found or error for user {current_user.id if current_user else 'Unknown'}.")
                return [], "Error retrieving accessible forms."

            # 2. Apply 'only_editable' filter (Python-side filtering)
            # This filter is applied *before* date filtering and sorting.
            if only_editable and not (current_user.role and current_user.role.is_super_user): # (logic from get_batch)
                # Non-admins can only edit their own forms from the set they can access
                accessible_forms = [form for form in accessible_forms if form.user_id == current_user.id] # (logic from get_batch)
            
            # 3. Apply date filtering (using the already corrected date parsing logic)
            processed_forms_for_date_filter: List[Form] = []
            if date_filter_field and start_date_str and end_date_str:
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
                    logger.warning(f"Invalid date format provided for filtering: start_date='{start_date_str}', end_date='{end_date_str}'")
                    return [], "Invalid date format. Use YYYY-MM-DD or full ISO format (e.g., YYYY-MM-DDTHH:MM:SSZ)."

                # Iterate over the list that might have already been filtered by 'only_editable'
                for form_obj in accessible_forms: 
                    form_date_original: Optional[datetime] = None
                    if date_filter_field == 'created_at':
                        form_date_original = form_obj.created_at
                    elif date_filter_field == 'updated_at':
                        form_date_original = form_obj.updated_at
                    
                    if form_date_original:
                        form_date_for_comparison: datetime
                        if form_date_original.tzinfo is None or form_date_original.tzinfo.utcoffset(form_date_original) is None:
                            form_date_for_comparison = form_date_original.replace(tzinfo=timezone.utc)
                        else:
                            form_date_for_comparison = form_date_original.astimezone(timezone.utc)
                        
                        if start_dt <= form_date_for_comparison <= end_dt:
                            processed_forms_for_date_filter.append(form_obj)
            else:
                # If no date filter, use the list (already potentially filtered by 'only_editable')
                processed_forms_for_date_filter = accessible_forms 
            
            # 4. Apply sorting (on the potentially smaller list)
            reverse_sort = (sort_order == 'desc')
            
            def get_sort_key(form_obj_to_sort: Form) -> Any:
                def make_comparable_utc(dt_val: Optional[datetime], default_if_none: datetime) -> datetime:
                    if dt_val is None:
                        return default_if_none 
                    
                    if dt_val.tzinfo is None or dt_val.tzinfo.utcoffset(dt_val) is None:
                        return dt_val.replace(tzinfo=timezone.utc)
                    else:
                        return dt_val.astimezone(timezone.utc)

                min_utc_datetime = datetime.min.replace(tzinfo=timezone.utc)

                if sort_by == 'title':
                    return (form_obj_to_sort.title or "").lower() 
                elif sort_by == 'created_at':
                    return make_comparable_utc(form_obj_to_sort.created_at, min_utc_datetime)
                return make_comparable_utc(form_obj_to_sort.updated_at, min_utc_datetime)

            processed_forms_for_date_filter.sort(key=get_sort_key, reverse=reverse_sort)
            
            # 5. Convert to compact dict
            compact_forms_info = [form_obj.to_compact_dict() for form_obj in processed_forms_for_date_filter] #
            
            return compact_forms_info, None
            
        except Exception as e:
            user_id_for_log = current_user.id if current_user else "Unknown"
            logger.error(f"Error in FormService.get_all_forms_compact_filtered_sorted for user {user_id_for_log}: {str(e)}", exc_info=True)
            return [], "An unexpected error occurred while retrieving compact form information."

    @staticmethod
    def get_form(form_id: int) -> Optional[Form]:
        """
        Get a non-deleted form by its ID, with related data eager-loaded.
        Access control should be handled by the caller (e.g., Controller/View)
        using FormAssignmentService.check_user_access_to_form().
        """
        try:
            return Form.query.options(
                joinedload(Form.creator).joinedload(User.environment),
                joinedload(Form.form_questions)
                    .joinedload(FormQuestion.question)
                    .joinedload(Question.question_type),
                joinedload(Form.form_questions) # For pre-defined answers (FormAnswer)
                    .joinedload(FormQuestion.form_answers)
                    .joinedload(FormAnswer.answer)
            ).filter_by(id=form_id, is_deleted=False).first()
        except Exception as e:
            logger.error(f"Error getting form ID {form_id}: {str(e)}", exc_info=True)
            # raise # Or return None depending on how controllers handle it
            return None


    @staticmethod
    def get_forms_by_environment(environment_id: int, current_user: User) -> List[Form]:
        """
        Get non-deleted forms created by users in a specific environment,
        that are accessible to the current_user.
        """
        try:
            # First, get all forms created by users in the target environment
            env_forms_query = FormService._get_base_query().join(User, Form.user_id == User.id)\
                                                    .filter(User.environment_id == environment_id)

            env_forms = env_forms_query.all()

            # Then, filter this list by what the current_user can actually access
            accessible_env_forms = []
            if current_user.role and current_user.role.is_super_user:
                accessible_env_forms = env_forms # Admin sees all forms from that env
            else:
                for form in env_forms:
                    if FormAssignmentService.check_user_access_to_form(current_user.id, form.id):
                        accessible_env_forms.append(form)

            return sorted(accessible_env_forms, key=lambda f: f.created_at, reverse=True)
        except Exception as e:
            logger.error(f"Error in get_forms_by_environment for env {environment_id}: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def get_public_forms(current_user: User) -> List[Form]: # Added current_user for access check
        """Get public forms accessible to the current user."""
        try:
            # Fetch all forms marked as public and not deleted
            public_forms_query = FormService._get_base_query().filter(Form.is_public == True)
            all_public_forms = public_forms_query.all()

            # Filter based on the new assignment logic
            accessible_public_forms = []
            for form in all_public_forms:
                if FormAssignmentService.check_user_access_to_form(current_user.id, form.id):
                    accessible_public_forms.append(form)

            return sorted(accessible_public_forms, key=lambda f: f.created_at, reverse=True)
        except Exception as e:
            logger.error(f"Error in get_public_forms: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def get_forms_by_creator(username: str, current_user: User) -> List[Form]:
        """
        Get all forms created by a specific user, that are accessible to the current_user.
        """
        try:
            creator = User.query.filter_by(username=username, is_deleted=False).first()
            if not creator:
                return [] # Creator not found

            creator_forms_query = FormService._get_base_query().filter(Form.user_id == creator.id)
            all_creator_forms = creator_forms_query.all()

            # Filter based on what the current_user can access
            accessible_creator_forms = []
            if current_user.role and current_user.role.is_super_user:
                accessible_creator_forms = all_creator_forms # Admin sees all
            elif current_user.id == creator.id: # The creator is requesting their own forms
                accessible_creator_forms = all_creator_forms
            else:
                for form in all_creator_forms:
                    if FormAssignmentService.check_user_access_to_form(current_user.id, form.id):
                        accessible_creator_forms.append(form)

            return sorted(accessible_creator_forms, key=lambda f: f.created_at, reverse=True)
        except Exception as e:
            logger.error(f"Error in get_forms_by_creator for '{username}': {str(e)}", exc_info=True)
            return []

    @classmethod
    def create_form(cls, title: str, description: Optional[str], user_id: int, is_public: bool = False, attachments_required: bool = False) -> Tuple[Optional[Form], Optional[str]]:
        """Create a new form"""
        # Access control (who can create forms) should be handled in the Controller/View layer.
        def _create():
            # Check if user exists and is not deleted
            user = User.query.filter_by(id=user_id, is_deleted=False).first()
            if not user:
                raise ValueError(f"User with ID {user_id} not found or is deleted. Cannot create form.")

            form = Form(
                title=title.strip(), # Ensure title is stripped
                description=description.strip() if description else None,
                user_id=user_id,
                is_public=is_public,
                attachments_required=attachments_required
            )
            db.session.add(form)
            # No flush needed here, _handle_transaction will commit.
            return form
        return cls._handle_transaction(_create)


    @staticmethod
    def update_form(form_id: int, **kwargs: Any) -> Tuple[Optional[Form], Optional[str]]:
        """
        Update a form's details.
        Access control (who can update this specific form) should be handled by the caller.
        """
        try:
            form = Form.query.filter_by(id=form_id, is_deleted=False).first()
            if not form:
                return None, "Form not found or has been deleted."

            allowed_fields = ['title', 'description', 'is_public', 'attachments_required']
            updated_fields_count = 0
            for key, value in kwargs.items():
                if key in allowed_fields:
                    if key == 'title' and not str(value).strip(): # Title cannot be empty
                        return None, "Form title cannot be empty."
                    setattr(form, key, value.strip() if isinstance(value, str) else value)
                    updated_fields_count += 1

            if updated_fields_count == 0:
                return form, "No valid fields provided for update." # Or None, "..." if no change isn't an error

            form.updated_at = datetime.utcnow()
            db.session.commit()
            return form, None

        except IntegrityError as e: # Catch specific IntegrityError for unique title constraint
            db.session.rollback()
            logger.error(f"Database integrity error during form update ID {form_id}: {str(e.orig)}")
            if "forms_title_key" in str(e.orig).lower() or ("unique constraint" in str(e.orig).lower() and "title" in str(e.orig).lower()):
                return None, "A form with this title already exists."
            return None, "A database integrity error occurred during update."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating form ID {form_id}: {str(e)}", exc_info=True)
            return None, "An unexpected error occurred while updating the form."

    @classmethod
    def add_questions_to_form(cls, form_id: int, questions_data: List[Dict[str, Any]]) -> Tuple[Optional[Form], Optional[str]]:
        """
        Add new questions to an existing form.
        Access control should be handled by the caller.
        """
        def _add_questions_op():
            form = Form.query.options(joinedload(Form.form_questions)).filter_by(id=form_id, is_deleted=False).first()
            if not form:
                raise ValueError("Form not found or has been deleted.")

            max_order = db.session.query(db.func.max(FormQuestion.order_number))\
                .filter_by(form_id=form_id, is_deleted=False).scalar() or 0

            new_form_questions = []
            for i, q_data in enumerate(questions_data, start=1):
                question_id = q_data.get('question_id')
                if not question_id:
                    raise ValueError("Each question entry must have a 'question_id'.")

                question_obj = Question.query.filter_by(id=question_id, is_deleted=False).first()
                if not question_obj:
                    raise ValueError(f"Question with ID {question_id} not found or is deleted.")

                existing_link = FormQuestion.query.filter_by(
                    form_id=form_id, question_id=question_id, is_deleted=False
                ).first()
                if existing_link:
                    logger.warning(f"Question ID {question_id} already actively linked to form ID {form_id}. Skipping.")
                    continue # Skip if already actively linked

                order_number = q_data.get('order_number', max_order + i)
                form_question = FormQuestion(
                    form_id=form_id,
                    question_id=question_id,
                    order_number=order_number
                )
                db.session.add(form_question)
                new_form_questions.append(form_question)

            if not new_form_questions and questions_data: # If data was provided but all were skipped
                 logger.info(f"No new questions were added to form {form_id} as they might already exist.")
                 # return form, "No new questions added; they may already exist or data was empty." # Optionally return a message

            # form.updated_at = datetime.utcnow() # Handled by TimestampMixin potentially, or explicitly set if needed
            return form # Return the form instance

        return cls._handle_transaction(_add_questions_op)


    @classmethod
    def reorder_questions(cls, form_id: int, question_order: List[Tuple[int, int]]) -> Tuple[Optional[Form], Optional[str]]:
        """
        Reorder questions in a form. question_order is a list of (form_question_id, new_order_number).
        Access control should be handled by the caller.
        """
        def _reorder_op():
            form = Form.query.filter_by(id=form_id, is_deleted=False).first()
            if not form:
                raise ValueError("Form not found or has been deleted.")

            form_question_ids_in_request = {fq_id for fq_id, _ in question_order}

            # Fetch existing, non-deleted FormQuestion objects for this form
            form_questions_map = {
                fq.id: fq for fq in FormQuestion.query.filter(
                    FormQuestion.form_id == form_id,
                    FormQuestion.id.in_(form_question_ids_in_request),
                    FormQuestion.is_deleted == False
                ).all()
            }

            if len(form_questions_map) != len(form_question_ids_in_request):
                missing_ids = form_question_ids_in_request - set(form_questions_map.keys())
                raise ValueError(f"One or more FormQuestion IDs are invalid, do not belong to form {form_id}, or are deleted: {missing_ids}")

            for form_question_id, new_order in question_order:
                form_question_to_update = form_questions_map.get(form_question_id)
                if form_question_to_update: # Should always be true due to check above
                    form_question_to_update.order_number = new_order
                    # form_question_to_update.updated_at = datetime.utcnow() # Handled by TimestampMixin

            # form.updated_at = datetime.utcnow() # Handled by TimestampMixin
            return form
        return cls._handle_transaction(_reorder_op)

    @classmethod
    def submit_form(cls, form_id: int, username: str, answers: List[Dict[str, Any]]) -> Tuple[Optional[FormSubmission], Optional[str]]:
        """
        Submit a form with answers.
        Access control (can user submit THIS form) should be handled by the caller.
        """
        from app.services.answer_submitted_service import AnswerSubmittedService # Local import to avoid circularity if any

        def _submit_op():
            form = Form.query.filter_by(id=form_id, is_deleted=False).first()
            if not form:
                raise ValueError(f"Form with ID {form_id} not found or is deleted.")

            user = User.query.filter_by(username=username, is_deleted=False).first()
            if not user:
                raise ValueError(f"User '{username}' not found or is deleted.")

            submission = FormSubmission(
                form_id=form_id,
                submitted_by=username, # Storing username
                submitted_at=datetime.utcnow()
            )
            db.session.add(submission)
            db.session.flush() # To get submission.id

            # Use AnswerSubmittedService for creating answers for better encapsulation
            # Assuming answers_data structure is compatible with what AnswerSubmittedService expects
            # e.g., each dict in 'answers' has 'question_text', 'question_type_text', 'answer_text', etc.
            # This part might need adjustment based on the exact structure of 'answers'
            if answers:
                # This is a simplified call; if signatures or table data is complex,
                # it might need to be handled differently or by a more specialized bulk create in AnswerSubmittedService.
                # For now, assuming a bulk create that can handle the structure in 'answers'.
                # If AnswerSubmittedService.bulk_create_answers_submitted expects specific file handling,
                # that logic would need to be here or refactored.

                # We'll iterate and call the single create method for clarity on file handling needs.
                upload_path = db.get_app().config.get('UPLOAD_FOLDER') # Get app config for upload path

                for answer_data in answers:
                    signature_file = answer_data.pop('signature_file', None) # Extract if present
                    _, error = AnswerSubmittedService.create_answer_submitted(
                        form_submission_id=submission.id,
                        question_text=answer_data.get('question_text'),
                        question_type_text=answer_data.get('question_type_text'),
                        answer_text=answer_data.get('answer_text'),
                        question_order=answer_data.get('question_order'),
                        is_signature=answer_data.get('is_signature', False),
                        signature_file=signature_file, # Pass the FileStorage object if any
                        upload_path=upload_path,
                        column=answer_data.get('column'),
                        row=answer_data.get('row'),
                        cell_content=answer_data.get('cell_content')
                    )
                    if error:
                        # If one answer fails, the whole submission transaction should roll back.
                        raise ValueError(f"Error creating submitted answer for question '{answer_data.get('question_text')}': {error}")
            return submission
        return cls._handle_transaction(_submit_op)


    @staticmethod
    def get_form_submissions(form_id: int, current_user: User) -> List[FormSubmission]:
        """
        Get all non-deleted submissions for a specific form, respecting user access to the form.
        Actual RBAC on submissions (e.g., technician sees only own) is handled in FormSubmissionService.
        """
        # This method should primarily ensure the user can access the form itself.
        # The fine-grained filtering of submissions is then done by FormSubmissionService.
        if not FormAssignmentService.check_user_access_to_form(current_user.id, form_id):
            logger.warning(f"User {current_user.username} attempted to access submissions for form {form_id} without permission.")
            return []

        # Delegate to FormSubmissionService which should handle its own RBAC on submissions.
        # We pass current_user to get_all_submissions for its internal RBAC.
        from app.services.form_submission_service import FormSubmissionService # Local import
        return FormSubmissionService.get_all_submissions(user=current_user, filters={'form_id': form_id})


    @staticmethod
    def get_form_statistics(form_id: int, current_user: User) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive statistics for a form.
        Access control to the form should be checked by the caller.
        """
        # Caller (Controller/View) should use FormAssignmentService.check_user_access_to_form()
        try:
            form = Form.query.filter_by(id=form_id, is_deleted=False).first()
            if not form:
                logger.warning(f"Form statistics requested for non-existent or deleted form ID: {form_id}")
                return None

            # Further role-based restrictions (e.g., technicians cannot see stats)
            if current_user.role and current_user.role.name == RoleType.TECHNICIAN:
                logger.warning(f"Technician {current_user.username} attempted to access stats for form {form_id}.")
                return {"error": "Technicians are not authorized to view form statistics."}


            submissions_q = FormSubmission.query.filter_by(form_id=form.id, is_deleted=False)

            # Apply submission-level RBAC before calculating stats if necessary.
            # For example, if stats should only reflect submissions visible to the current user.
            # This depends on requirements. For now, stats are on ALL submissions of an accessible form.
            # If stats need to be user-view-specific:
            # accessible_submission_ids = [s.id for s in FormSubmissionService.get_all_submissions(user=current_user, filters={'form_id': form.id})]
            # submissions = FormSubmission.query.filter(FormSubmission.id.in_(accessible_submission_ids)).all()
            submissions = submissions_q.all()


            stats: Dict[str, Any] = {
                'form_id': form.id,
                'form_title': form.title,
                'total_submissions': len(submissions),
                'submission_trends': {'daily': {}, 'weekly': {}, 'monthly': {}},
                'questions_stats': {},
                'completion_rate': 0.0 # Initialize as float
            }

            if submissions:
                for sub in submissions:
                    if not sub.submitted_at: continue # Skip if no submission timestamp
                    date_iso = sub.submitted_at.date().isoformat()
                    week_iso = f"{sub.submitted_at.year}-W{sub.submitted_at.isocalendar()[1]:02d}"
                    month_iso = sub.submitted_at.strftime('%Y-%m')

                    stats['submission_trends']['daily'][date_iso] = stats['submission_trends']['daily'].get(date_iso, 0) + 1
                    stats['submission_trends']['weekly'][week_iso] = stats['submission_trends']['weekly'].get(week_iso, 0) + 1
                    stats['submission_trends']['monthly'][month_iso] = stats['submission_trends']['monthly'].get(month_iso, 0) + 1

                active_form_questions = [fq for fq in form.form_questions if not fq.is_deleted and fq.question and not fq.question.is_deleted]
                total_questions_in_form = len(active_form_questions)

                for fq_obj in active_form_questions:
                    q_text = fq_obj.question.text
                    q_type = fq_obj.question.question_type.type if fq_obj.question.question_type else "N/A"

                    # Count answers submitted for this specific question text within this form's submissions.
                    # This query could be slow if done per question. Consider alternatives for many questions.
                    ans_for_q_count = db.session.query(AnswerSubmitted.id)\
                        .join(FormSubmission, FormSubmission.id == AnswerSubmitted.form_submission_id)\
                        .filter(FormSubmission.form_id == form_id, FormSubmission.is_deleted == False,
                                AnswerSubmitted.question == q_text, AnswerSubmitted.is_deleted == False)\
                        .count()

                    stats['questions_stats'][str(fq_obj.question_id)] = {
                        'question_text': q_text, 'question_type': q_type,
                        'total_responses': ans_for_q_count,
                        # Add more stats per question if needed (e.g., distinct answers for choice questions)
                    }

                if total_questions_in_form > 0 and len(submissions) > 0:
                    completed_submissions_count = 0
                    for sub in submissions:
                        # Count unique questions answered in this submission
                        answered_q_texts_in_sub = {ans.question for ans in sub.answers_submitted if not ans.is_deleted}
                        if len(answered_q_texts_in_sub) >= total_questions_in_form:
                            completed_submissions_count += 1
                    stats['completion_rate'] = round((completed_submissions_count / len(submissions)) * 100, 2)

            return stats
        except Exception as e:
            logger.error(f"Error generating form statistics for form ID {form_id}: {str(e)}", exc_info=True)
            return None # Or return a dict with an error message

    @classmethod
    def delete_form(cls, form_id: int, current_user: User) -> Tuple[bool, Union[Dict[str, int], str]]:
        """
        Soft-deletes a form and its direct structural components (FormQuestion, FormAnswer).
        FormSubmissions related to this form are PRESERVED by default.
        Access control (who can delete) should be handled by the caller.
        """
        # Caller (Controller/View) should use FormAssignmentService.check_user_access_to_form()
        # and then check if current_user is the form.creator or an admin.
        def _delete_op():
            form = Form.query.filter_by(id=form_id, is_deleted=False).first()
            if not form:
                raise ValueError("Form not found or already deleted.")

            # Authorization check (redundant if caller does it, but good for service integrity)
            if not (current_user.role and current_user.role.is_super_user) and form.user_id != current_user.id:
                raise PermissionError("User does not have permission to delete this form.")


            deletion_stats = {'form_questions': 0, 'form_answers': 0, 'form_assignments':0, 'report_templates':0}

            # Soft delete FormQuestion and their FormAnswer entries
            for fq in FormQuestion.query.filter_by(form_id=form.id, is_deleted=False).all():
                for fa in FormAnswer.query.filter_by(form_question_id=fq.id, is_deleted=False).all():
                    fa.soft_delete()
                    deletion_stats['form_answers'] += 1
                fq.soft_delete()
                deletion_stats['form_questions'] += 1

            # Soft delete FormAssignment entries associated with this form
            for fa_assign in FormAssignment.query.filter_by(form_id=form.id, is_deleted=False).all():
                fa_assign.soft_delete()
                deletion_stats['form_assignments'] += 1

            # Soft delete ReportTemplate entries associated with this form
            from app.models import ReportTemplate # Local import
            for rt in ReportTemplate.query.filter_by(form_id=form.id, is_deleted=False).all():
                rt.soft_delete()
                deletion_stats['report_templates'] += 1

            form.soft_delete()
            # form.updated_at = datetime.utcnow() # Handled by SoftDeleteMixin
            return deletion_stats # Return stats on success

        return cls._handle_transaction(_delete_op)


    @staticmethod
    def search_forms(
        current_user: User,
        search_text: Optional[str] = None,
        creator_user_id: Optional[int] = None,
        is_public: Optional[bool] = None,
        environment_id: Optional[int] = None # Filter by form creator's environment
    ) -> List[Form]:
        """
        Search forms with filters, respecting user access based on new assignment rules.
        """
        try:
            # Start with forms accessible to the current user
            accessible_forms = FormAssignmentService.get_accessible_forms_for_user(current_user.id)
            if not accessible_forms:
                return []

            accessible_form_ids = [form.id for form in accessible_forms]

            # Build query on top of accessible forms
            query = FormService._get_base_query(include_questions=False) # Don't need questions for search list
            query = query.filter(Form.id.in_(accessible_form_ids))

            if search_text:
                query = query.filter(
                    db.or_(
                        Form.title.ilike(f'%{search_text}%'),
                        Form.description.ilike(f'%{search_text}%')
                    )
                )
            if creator_user_id is not None:
                query = query.filter(Form.user_id == creator_user_id)
            if is_public is not None:
                query = query.filter(Form.is_public == is_public)
            if environment_id is not None: # Filter by form creator's environment
                query = query.join(User, Form.user_id == User.id).filter(User.environment_id == environment_id)

            return query.order_by(Form.created_at.desc()).all()
        except Exception as e:
            logger.error(f"Error in FormService.search_forms: {str(e)}", exc_info=True)
            return []