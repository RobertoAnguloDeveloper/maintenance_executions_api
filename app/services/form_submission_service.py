from typing import Dict, List, Optional, Tuple
from app import db
from app.models.form_submission import FormSubmission
from app.models.answer_submitted import AnswerSubmitted
from app.utils.permission_manager import RoleType
from app.models.attachment import Attachment
from app.models.form import Form
from sqlalchemy.orm import joinedload
from datetime import datetime
import logging
import os

from app.models.user import User

logger = logging.getLogger(__name__)

class FormSubmissionService:
    @staticmethod
    def create_submission(
        form_id: int,
        username: str,
        answers_data: List[Dict] = None,
        upload_path: Optional[str] = None
    ) -> Tuple[Optional[FormSubmission], Optional[str]]:
        """
        Create a new form submission with answers and handle signatures
        
        Args:
            form_id: ID of the form being submitted
            username: Username of the submitter
            answers_data: List of answer data dictionaries
            upload_path: Base path for file uploads
            
        Returns:
            tuple: (Created FormSubmission object or None, Error message or None)
        """
        try:
            # Verify form exists and is active
            form = Form.query.filter_by(id=form_id, is_deleted=False).first()
            if not form:
                return None, "Form not found or inactive"

            # Create submission
            submission = FormSubmission(
                form_id=form_id,
                submitted_by=username,
                submitted_at=datetime.utcnow()
            )
            db.session.add(submission)
            db.session.flush()

            # Process answers if provided
            if answers_data:
                for answer_data in answers_data:
                    # Create answer submission
                    answer = AnswerSubmitted(
                        form_submission_id=submission.id,
                        question=answer_data['question_text'],
                        answer=answer_data['answer_text']
                    )
                    db.session.add(answer)

                    # Handle signature if required
                    if answer_data.get('is_signature') and answer_data.get('signature_file'):
                        if not upload_path:
                            return None, "Upload path not provided for signature file"

                        # Create signature directory
                        signature_dir = os.path.join(upload_path, 'signatures', str(submission.id))
                        os.makedirs(signature_dir, exist_ok=True)

                        # Save signature file
                        signature_file = answer_data['signature_file']
                        filename = f"signature_{datetime.now().strftime('%Y%m%d_%H%M%S')}{os.path.splitext(signature_file.filename)[1]}"
                        file_path = os.path.join('signatures', str(submission.id), filename)
                        signature_file.save(os.path.join(upload_path, file_path))

                        # Create attachment record
                        attachment = Attachment(
                            form_submission_id=submission.id,
                            file_type=signature_file.content_type,
                            file_path=file_path,
                            is_signature=True
                        )
                        db.session.add(attachment)

            db.session.commit()
            return submission, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating form submission: {str(e)}")
            return None, str(e)
        
    @staticmethod
    def get_all_submissions(user: User, filters: Optional[Dict] = None) -> List[FormSubmission]:
        """
        Get all form submissions with role-based filtering and access control.
        
        Args:
            user: Current user object for role-based access
            filters: Optional dictionary containing filters:
                - form_id: Filter by specific form
                - date_range: Dict with 'start' and 'end' dates
                - environment_id: Filter by environment
                - submitted_by: Filter by submitter username
                - consider_public: Consider public forms across environments
                
        Returns:
            List[FormSubmission]: List of form submissions matching criteria
        """
        try:
            # Base query with proper joins and filters
            query = (FormSubmission.query
                .join(Form)
                .filter(
                    FormSubmission.is_deleted == False
                ))
            
            # Apply role-based filtering
            consider_public = filters.get('consider_public', False) if filters else False
            
            if not user.role.is_super_user:
                if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    # Can only see submissions in their environment
                    # Plus public forms if consider_public is True
                    if consider_public:
                        query = (query
                            .join(User, User.id == Form.user_id)
                            .filter(
                                db.or_(
                                    User.environment_id == user.environment_id,
                                    Form.is_public == True
                                )
                            ))
                    else:
                        query = (query
                            .join(User, User.id == Form.user_id)
                            .filter(User.environment_id == user.environment_id))
                else:
                    # Regular users can only see their own submissions
                    query = query.filter(FormSubmission.submitted_by == user.username)

            # Apply optional filters
            if filters:
                if 'form_id' in filters:
                    query = query.filter(FormSubmission.form_id == filters['form_id'])
                    
                if 'environment_id' in filters and not consider_public:
                    # Only apply environment filter if not considering public forms
                    # or if explicitly handling public forms in the query above
                    query = (query
                        .join(User, User.id == Form.user_id, isouter=True)
                        .filter(User.environment_id == filters['environment_id']))
                        
                if 'submitted_by' in filters:
                    query = query.filter(
                        FormSubmission.submitted_by == filters['submitted_by']
                    )
                    
                if 'date_range' in filters:
                    date_range = filters['date_range']
                    if date_range.get('start'):
                        query = query.filter(
                            FormSubmission.submitted_at >= date_range['start']
                        )
                    if date_range.get('end'):
                        query = query.filter(
                            FormSubmission.submitted_at <= date_range['end']
                        )

            # Add eager loading for related data
            query = (query.options(
                joinedload(FormSubmission.form),
                joinedload(FormSubmission.answers_submitted),
                joinedload(FormSubmission.attachments)
            ))

            # Order by submission date, most recent first
            submissions = query.order_by(FormSubmission.submitted_at.desc()).all()
            
            return submissions

        except Exception as e:
            logger.error(f"Error getting submissions: {str(e)}")
            return []
        
    @staticmethod
    def get_all_submissions_compact(user: User, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Get all form submissions in a compact format with minimal information.
        
        Args:
            user: Current user object for role-based access
            filters: Optional dictionary containing filters:
                - form_id: Filter by specific form
                - date_range: Dict with 'start' and 'end' dates
                - environment_id: Filter by environment
                - submitted_by: Filter by submitter username
                - consider_public: Consider public forms across environments
                
        Returns:
            List[Dict]: List of compact form submissions with specific field order
        """
        try:
            # Base query with proper joins and filters
            query = (FormSubmission.query
                .join(Form)
                .filter(
                    FormSubmission.is_deleted == False
                ))
            
            # Apply role-based filtering
            consider_public = filters.get('consider_public', False) if filters else False
            
            if not user.role.is_super_user:
                if user.role.name == RoleType.TECHNICIAN:
                    # Technicians can only see their own submissions
                    query = query.filter(FormSubmission.submitted_by == user.username)
                elif user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                    # Site managers and supervisors can see submissions in their environment
                    # Plus public forms if consider_public is True
                    if consider_public:
                        query = (query
                            .join(User, User.id == Form.user_id)
                            .filter(
                                db.or_(
                                    User.environment_id == user.environment_id,
                                    Form.is_public == True
                                )
                            ))
                    else:
                        query = (query
                            .join(User, User.id == Form.user_id)
                            .filter(User.environment_id == user.environment_id))
                else:
                    # Other roles can only see their own submissions
                    query = query.filter(FormSubmission.submitted_by == user.username)
            
            # Apply optional filters
            if filters:
                if 'form_id' in filters:
                    query = query.filter(FormSubmission.form_id == filters['form_id'])
                    
                if 'environment_id' in filters and not consider_public:
                    # Only apply environment filter if not considering public forms
                    # or if explicitly handling public forms in the query above
                    query = (query
                        .join(User, User.id == Form.user_id, isouter=True)
                        .filter(User.environment_id == filters['environment_id']))
                        
                if 'submitted_by' in filters:
                    query = query.filter(
                        FormSubmission.submitted_by == filters['submitted_by']
                    )
                    
                if 'date_range' in filters:
                    date_range = filters['date_range']
                    if date_range.get('start'):
                        query = query.filter(
                            FormSubmission.submitted_at >= date_range['start']
                        )
                    if date_range.get('end'):
                        query = query.filter(
                            FormSubmission.submitted_at <= date_range['end']
                        )

            # Add eager loading for related data
            query = (query.options(
                joinedload(FormSubmission.form),
                joinedload(FormSubmission.answers_submitted),
                joinedload(FormSubmission.attachments)
            ))

            # Order by submission date, most recent first
            submissions = query.order_by(FormSubmission.submitted_at.desc()).all()
            
            # Transform to compact format with fields in exact order specified
            compact_submissions = []
            for submission in submissions:
                # Create dict with keys in the exact order required
                submission_dict = {
                    'id': submission.id,
                    'form_id': submission.form_id,
                    'form': {
                        'id': submission.form.id,
                        'title': submission.form.title
                    } if submission.form else None,
                    'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
                    'submitted_by': submission.submitted_by,
                    'answers_count': len([answer for answer in submission.answers_submitted if not answer.is_deleted]),
                    'attachments_count': len([attachment for attachment in submission.attachments if not attachment.is_deleted])
                }
                compact_submissions.append(submission_dict)
                
            return compact_submissions

        except Exception as e:
            logger.error(f"Error getting compact submissions: {str(e)}")
            return []
        
    @staticmethod
    def get_batch(page=1, per_page=50, **filters):
        """
        Get batch of form submissions with pagination in compact format
        
        Args:
            page: Page number (starts from 1)
            per_page: Number of items per page
            **filters: Optional filters
                
        Returns:
            tuple: (total_count, form_submissions)
        """
        try:
            # Build base query with joins for efficiency
            query = FormSubmission.query.options(
                joinedload(FormSubmission.form),
                joinedload(FormSubmission.answers_submitted),
                joinedload(FormSubmission.attachments)
            )
            
            # Apply filters
            include_deleted = filters.get('include_deleted', False)
            if not include_deleted:
                query = query.filter(FormSubmission.is_deleted == False)
            
            form_id = filters.get('form_id')
            if form_id:
                query = query.filter(FormSubmission.form_id == form_id)
                
            submitted_by = filters.get('submitted_by')
            if submitted_by:
                query = query.filter(FormSubmission.submitted_by == submitted_by)
                
            date_range = filters.get('date_range')
            if date_range:
                if date_range.get('start'):
                    query = query.filter(FormSubmission.submitted_at >= date_range['start'])
                if date_range.get('end'):
                    query = query.filter(FormSubmission.submitted_at <= date_range['end'])
            
            # Apply role-based access control
            current_user = filters.get('current_user')
            consider_public = filters.get('consider_public', False)
            
            if current_user:
                # Normal role-based filtering for viewing submissions
                if not current_user.role.is_super_user:
                    if current_user.role.name == RoleType.TECHNICIAN:
                        # Technicians can only see their own submissions
                        query = query.filter(FormSubmission.submitted_by == current_user.username)
                    elif current_user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                        # Site managers and supervisors can see submissions in their environment
                        # Plus public forms if consider_public is True
                        if consider_public:
                            query = query.join(
                                Form, 
                                Form.id == FormSubmission.form_id
                            ).join(
                                User, 
                                User.id == Form.user_id
                            ).filter(
                                db.or_(
                                    User.environment_id == current_user.environment_id,
                                    Form.is_public == True
                                )
                            )
                        else:
                            query = query.join(
                                Form, 
                                Form.id == FormSubmission.form_id
                            ).join(
                                User, 
                                User.id == Form.user_id
                            ).filter(
                                User.environment_id == current_user.environment_id
                            )
            
            # Get total count
            total_count = query.count()
            
            # Calculate total pages
            total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 0
            
            # Ensure requested page is valid
            if page > total_pages and total_pages > 0:
                # If requested page exceeds total pages, use the last page
                page = total_pages
            elif page < 1:
                # If page is less than 1, use the first page
                page = 1
                
            # Calculate offset based on adjusted page number
            offset = (page - 1) * per_page
            
            # Apply pagination with adjusted page
            form_submissions = query.order_by(
                FormSubmission.submitted_at.desc()
            ).offset(offset).limit(per_page).all()
            
            # Transform to compact format with fields in exact order specified
            compact_submissions = []
            for submission in form_submissions:
                # Create dict with keys in the exact order required
                submission_dict = {
                    'id': submission.id,
                    'form_id': submission.form_id,
                    'form': {
                        'id': submission.form.id,
                        'title': submission.form.title
                    } if submission.form else None,
                    'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
                    'submitted_by': submission.submitted_by,
                    'answers_count': len([answer for answer in submission.answers_submitted if not answer.is_deleted]),
                    'attachments_count': len([attachment for attachment in submission.attachments if not attachment.is_deleted]),
                    'is_editable': False  # Default value, will be updated below
                }
                
                # Add "is_editable" flag based on role and age
                if current_user:
                    submitted_at = submission.submitted_at
                    if current_user.role.is_super_user:
                        # Admins can edit all submissions
                        submission_dict['is_editable'] = True
                    elif current_user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                        # Site managers and supervisors can edit submissions in their environment
                        # or public forms that are less than 7 days old
                        if submitted_at and (datetime.utcnow() - submitted_at).days <= 7:
                            is_public = submission.form.is_public if submission.form else False
                            if is_public or (submission.form and submission.form.creator and 
                                            submission.form.creator.environment_id == current_user.environment_id):
                                submission_dict['is_editable'] = True
                    elif submission.submitted_by == current_user.username:
                        # Regular users can edit their own submissions that are less than 7 days old
                        if submitted_at and (datetime.utcnow() - submitted_at).days <= 7:
                            submission_dict['is_editable'] = True
                
                compact_submissions.append(submission_dict)
            
            return total_count, compact_submissions
                
        except Exception as e:
            logger.error(f"Error in form submission batch pagination service: {str(e)}")
            return 0, []
        
    @staticmethod
    def get_user_environment_id(username: str) -> Optional[int]:
        """Get the environment ID for a user"""
        try:
            user = User.query.filter_by(username=username).first()
            return user.environment_id if user else None
        except Exception as e:
            logger.error(f"Error getting user environment ID: {str(e)}")
            return None
        
    @staticmethod
    def get_submission(submission_id: int) -> Optional[FormSubmission]:
        """
        Get a specific form submission with all related data
        
        Args:
            submission_id: ID of the submission
            
        Returns:
            Optional[FormSubmission]: FormSubmission object if found, None otherwise
        """
        try:
            return (FormSubmission.query
                .filter_by(
                    id=submission_id,
                    is_deleted=False
                )
                .options(
                    joinedload(FormSubmission.form),
                    joinedload(FormSubmission.answers_submitted),
                    joinedload(FormSubmission.attachments)
                )
                .first())
        except Exception as e:
            logger.error(f"Error retrieving submission {submission_id}: {str(e)}")
            return None
        
    @staticmethod
    def get_submissions_by_user(username: str, filters: Dict = None) -> List[FormSubmission]:
        """
        Get all submissions for a specific user with optional filtering.
        Args:
            username: Username of the submitter
            filters: Optional dictionary containing filters
                - start_date: Start date for filtering
                - end_date: End date for filtering
                - form_id: Filter by specific form
                
        Returns:
            List[FormSubmission]: List of form submissions
        """
        try:
            query = FormSubmission.query.filter_by(
                submitted_by=username,
                is_deleted=False
            )

            if filters:
                if 'start_date' in filters:
                    query = query.filter(FormSubmission.submitted_at >= filters['start_date'])
                if 'end_date' in filters:
                    query = query.filter(FormSubmission.submitted_at <= filters['end_date'])
                if 'form_id' in filters:
                    query = query.filter_by(form_id=filters['form_id'])

            return query.order_by(FormSubmission.submitted_at.desc()).all()

        except Exception as e:
            logger.error(f"Error getting submissions for user {username}: {str(e)}")
            return []
        
    @staticmethod
    def update_submission(
        submission_id: int,
        update_data: Dict,
        answers_data: List[Dict] = None,
        upload_path: Optional[str] = None
    ) -> Tuple[Optional[FormSubmission], Optional[str]]:
        """
        Update an existing form submission with answers and handle signatures
        
        Args:
            submission_id: ID of the submission to update
            update_data: Dictionary of fields to update
            answers_data: List of answer data dictionaries
            upload_path: Base path for file uploads
            
        Returns:
            tuple: (Updated FormSubmission object or None, Error message or None)
        """
        try:
            # Retrieve the submission
            submission = FormSubmission.query.filter_by(id=submission_id, is_deleted=False).first()
            if not submission:
                return None, "Submission not found"

            # Update submission timestamp
            submission.updated_at = datetime.utcnow()
            
            # Process status update if provided
            if 'status' in update_data:
                submission.status = update_data['status']

            # Update answers if provided
            if answers_data:
                # Keep track of processed answer IDs
                processed_answer_ids = []
                
                for answer_data in answers_data:
                    answer_id = answer_data.get('id')
                    
                    if answer_id:
                        # Update existing answer
                        answer = AnswerSubmitted.query.filter_by(
                            id=answer_id,
                            form_submission_id=submission_id,
                            is_deleted=False
                        ).first()
                        
                        if answer:
                            answer.answer = answer_data.get('answer_text', answer.answer)
                            answer.updated_at = datetime.utcnow()
                            processed_answer_ids.append(answer_id)
                    else:
                        # Create new answer
                        answer = AnswerSubmitted(
                            form_submission_id=submission_id,
                            question=answer_data['question_text'],
                            answer=answer_data['answer_text']
                        )
                        db.session.add(answer)
                        db.session.flush()
                        processed_answer_ids.append(answer.id)
                    
                    # Handle signature if required
                    if answer_data.get('is_signature') and answer_data.get('signature_file'):
                        if not upload_path:
                            return None, "Upload path not provided for signature file"

                        # Create signature directory
                        signature_dir = os.path.join(upload_path, 'signatures', str(submission_id))
                        os.makedirs(signature_dir, exist_ok=True)

                        # Save signature file
                        signature_file = answer_data['signature_file']
                        filename = f"signature_{datetime.now().strftime('%Y%m%d_%H%M%S')}{os.path.splitext(signature_file.filename)[1]}"
                        file_path = os.path.join('signatures', str(submission_id), filename)
                        signature_file.save(os.path.join(upload_path, file_path))

                        # Check if there's an existing signature attachment
                        existing_signature = Attachment.query.filter_by(
                            form_submission_id=submission_id,
                            is_signature=True,
                            is_deleted=False
                        ).first()
                        
                        if existing_signature:
                            # Soft delete the old signature
                            existing_signature.soft_delete()
                        
                        # Create new attachment record
                        attachment = Attachment(
                            form_submission_id=submission_id,
                            file_type=signature_file.content_type,
                            file_path=file_path,
                            is_signature=True
                        )
                        db.session.add(attachment)
                
                # If deletion flag is provided in update_data, handle removal of unprocessed answers
                if update_data.get('delete_unprocessed_answers'):
                    unprocessed_answers = AnswerSubmitted.query.filter(
                        AnswerSubmitted.form_submission_id == submission_id,
                        AnswerSubmitted.is_deleted == False,
                        ~AnswerSubmitted.id.in_(processed_answer_ids)
                    ).all()
                    
                    for answer in unprocessed_answers:
                        answer.soft_delete()

            db.session.commit()
            return submission, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating form submission: {str(e)}")
            return None, str(e)

    @staticmethod
    def delete_submission(submission_id: int) -> Tuple[bool, Optional[str]]:
        """
        Delete a submission while preserving related answer and attachment data.
        """
        try:
            submission = FormSubmission.query.filter_by(
                id=submission_id,
                is_deleted=False
            ).first()
            
            if not submission:
                return False, "Submission not found"

            # Only soft delete the submission itself
            # without touching related answers or attachments
            submission.soft_delete()
            db.session.commit()
            
            logger.info(f"Submission {submission_id} marked as deleted while preserving related data")
            return True, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting submission: {str(e)}")
            return False, str(e)

    @staticmethod
    def get_submission_answers(submission_id: int) -> Tuple[List[Dict], Optional[str]]:
        """Get all answers for a specific submission"""
        try:
            submission = FormSubmission.query.filter_by(
                id=submission_id,
                is_deleted=False
            ).first()
            
            if not submission:
                return [], "Submission not found"

            answers = []
            for answer in submission.answers_submitted:
                if not answer.is_deleted:
                    answer_dict = answer.to_dict()
                    # Add signature info if available
                    signature = next((att for att in submission.attachments 
                                   if att.is_signature and not att.is_deleted), None)
                    if signature:
                        answer_dict['signature'] = signature.to_dict()
                    answers.append(answer_dict)

            return answers, None

        except Exception as e:
            logger.error(f"Error getting submission answers: {str(e)}")
            return [], str(e)

    @staticmethod
    def update_submission_status(
        submission_id: int,
        status: str
    ) -> Tuple[Optional[FormSubmission], Optional[str]]:
        """Update submission status"""
        try:
            submission = FormSubmission.query.filter_by(
                id=submission_id,
                is_deleted=False
            ).first()
            
            if not submission:
                return None, "Submission not found"

            # Update status and timestamps
            submission.status = status
            submission.updated_at = datetime.utcnow()
            
            db.session.commit()
            return submission, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating submission status: {str(e)}")
            return None, str(e)