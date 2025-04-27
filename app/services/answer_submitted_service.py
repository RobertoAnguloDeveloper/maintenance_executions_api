from typing import Dict, List, Optional, Tuple
from app import db
from app.models.answer_submitted import AnswerSubmitted
from app.models.attachment import Attachment
from app.models.form import Form
from app.models.form_submission import FormSubmission
from app.models.question import Question
from datetime import datetime
from werkzeug.datastructures import FileStorage
from sqlalchemy.orm import joinedload
import os
import logging

from app.models.user import User
from app.utils.permission_manager import RoleType

logger = logging.getLogger(__name__)

class AnswerSubmittedService:
    @staticmethod
    def create_answer_submitted(
        form_submission_id: int,
        question_text: str,
        question_type_text: str,
        answer_text: str,
        is_signature: bool = False,
        signature_file: Optional[FileStorage] = None,
        upload_path: Optional[str] = None,
        column: Optional[int] = None,
        row: Optional[int] = None,
        cell_content: Optional[str] = None
    ) -> Tuple[Optional[AnswerSubmitted], Optional[str]]:
        """
        Create a new answer submission with signature handling and table support.
        
        Args:
            form_submission_id: ID of the form submission
            question_text: The text of the question
            question_type_text: The type of question (text, choice, table, etc.)
            answer_text: The answer text
            is_signature: Whether this answer requires a signature
            signature_file: File object for signature if applicable
            upload_path: Base path for file uploads
            column: Column position for table-type questions
            row: Row position for table-type questions
            cell_content: Cell content for table-type questions
            
        Returns:
            tuple: (Created AnswerSubmitted object or None, Error message or None)
        """
        try:
            # Verify form submission exists
            form_submission = FormSubmission.query.filter_by(
                id=form_submission_id,
                is_deleted=False
            ).first()
            
            if not form_submission:
                return None, "Form submission not found"

            # Remove '~' characters from question_text if it's a signature
            if is_signature and '~' in question_text:
                cleaned_question_text = question_text.replace('~', '')
                logger.info(f"Removed '~' characters from signature question text: '{question_text}' -> '{cleaned_question_text}'")
                question_text = cleaned_question_text

            # Create answer submission
            answer_submitted = AnswerSubmitted(
                form_submission_id=form_submission_id,
                question=question_text,
                question_type=question_type_text,
                answer=answer_text
            )

            # Handle table-type questions
            if question_type_text == 'table' and column is not None and row is not None:
                answer_submitted.column = column
                answer_submitted.row = row
                answer_submitted.cell_content = cell_content
                
            db.session.add(answer_submitted)

            # Handle signature if applicable
            if is_signature and signature_file and upload_path:
                # Create signature directory if it doesn't exist
                signature_dir = os.path.join(upload_path, 'signatures', str(form_submission_id))
                os.makedirs(signature_dir, exist_ok=True)

                # Save signature file
                filename = f"signature_{datetime.now().strftime('%Y%m%d_%H%M%S')}{os.path.splitext(signature_file.filename)[1]}"
                file_path = os.path.join('signatures', str(form_submission_id), filename)
                signature_file.save(os.path.join(upload_path, file_path))

                # Create attachment record
                attachment = Attachment(
                    form_submission_id=form_submission_id,
                    file_type=signature_file.content_type,
                    file_path=file_path,
                    is_signature=True
                )
                db.session.add(attachment)

            db.session.commit()
            return answer_submitted, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in create_answer_submitted: {str(e)}")
            return None, str(e)

    @staticmethod
    def bulk_create_answers_submitted(
        form_submission_id: int,
        answers_data: List[Dict],
        upload_path: Optional[str] = None
    ) -> Tuple[Optional[List[AnswerSubmitted]], Optional[str]]:
        """
        Bulk create answer submissions with table support.
        """
        try:
            created_submissions = []
            
            # Verify form submission exists
            form_submission = FormSubmission.query.filter_by(
                id=form_submission_id,
                is_deleted=False
            ).first()
            
            if not form_submission:
                return None, "Form submission not found"

            # Start transaction
            db.session.begin_nested()

            for data in answers_data:
                # Check if this is a signature question and clean the text if needed
                is_signature = data.get('is_signature', False)
                question_text = data['question_text']
                
                if is_signature and '~' in question_text:
                    cleaned_question_text = question_text.replace('~', '')
                    logger.info(f"Removed '~' characters from signature question text: '{question_text}' -> '{cleaned_question_text}'")
                    question_text = cleaned_question_text
                
                answer_submitted = AnswerSubmitted(
                    form_submission_id=form_submission_id,
                    question=question_text,
                    question_type=data['question_type_text'],
                    answer=data['answer_text']
                )
                
                # Handle table-type questions
                if data['question_type_text'] == 'table':
                    # Validate required fields for table type
                    if 'column' not in data or 'row' not in data:
                        db.session.rollback()
                        return None, "Column and row are required for table-type questions"
                        
                    answer_submitted.column = data['column']
                    answer_submitted.row = data['row']
                    answer_submitted.cell_content = data.get('cell_content')
                
                db.session.add(answer_submitted)
                created_submissions.append(answer_submitted)

            db.session.commit()
            return created_submissions, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in bulk_create_answers_submitted: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_answer_submitted(answer_submitted_id: int) -> Optional[AnswerSubmitted]:
        """Get a specific submitted answer"""
        return AnswerSubmitted.query.filter_by(
            id=answer_submitted_id,
            is_deleted=False
        ).first()

    @staticmethod
    def get_all_answers_submitted(filters: Optional[Dict] = None) -> List[AnswerSubmitted]:
        """Get all submitted answers with optional filtering"""
        try:
            query = AnswerSubmitted.query.filter_by(is_deleted=False)
            
            if filters:
                if 'form_submission_id' in filters:
                    query = query.filter_by(form_submission_id=filters['form_submission_id'])
                    
                if 'environment_id' in filters:
                    # Join tables to filter by environment
                    query = query.join(
                        FormSubmission, 
                        FormSubmission.id == AnswerSubmitted.form_submission_id
                    ).join(
                        User, 
                        User.username == FormSubmission.submitted_by
                    ).filter(
                        User.environment_id == filters['environment_id']
                    )
                    
                if 'submitted_by' in filters:
                    query = query.join(
                        FormSubmission, 
                        FormSubmission.id == AnswerSubmitted.form_submission_id
                    ).filter(
                        FormSubmission.submitted_by == filters['submitted_by']
                    )
                
                if 'question_type' in filters:
                    query = query.filter(AnswerSubmitted.question_type == filters['question_type'])
                
                # Table-specific filtering
                if 'column' in filters:
                    query = query.filter(AnswerSubmitted.column == filters['column'])
                
                if 'row' in filters:
                    query = query.filter(AnswerSubmitted.row == filters['row'])
            
            return query.order_by(AnswerSubmitted.created_at.desc()).all()
        except Exception as e:
            logger.error(f"Error in get_all_answers_submitted service: {str(e)}")
            return []
    
    @staticmethod
    def get_batch(page=1, per_page=50, **filters):
        """
        Get batch of submitted answers with pagination directly from database
        
        Args:
            page: Page number (starts from 1)
            per_page: Number of items per page
            **filters: Optional filters
            
        Returns:
            tuple: (total_count, answers_submitted)
        """
        try:
            # Calculate offset
            offset = (page - 1) * per_page if page > 0 and per_page > 0 else 0
            
            # Build base query with joins for efficiency
            query = AnswerSubmitted.query.options(
                joinedload(AnswerSubmitted.form_submission).joinedload(FormSubmission.form)
            )
            
            # Apply filters
            include_deleted = filters.get('include_deleted', False)
            if not include_deleted:
                query = query.filter(AnswerSubmitted.is_deleted == False)
            
            form_submission_id = filters.get('form_submission_id')
            if form_submission_id:
                query = query.filter(AnswerSubmitted.form_submission_id == form_submission_id)
                
            question_type = filters.get('question_type')
            if question_type:
                query = query.filter(AnswerSubmitted.question_type == question_type)
            
            # Table-specific filtering
            column = filters.get('column')
            if column is not None:
                query = query.filter(AnswerSubmitted.column == column)
            
            row = filters.get('row')
            if row is not None:
                query = query.filter(AnswerSubmitted.row == row)
            
            # Apply role-based access control
            current_user = filters.get('current_user')
            if current_user:
                if not current_user.role.is_super_user:
                    if current_user.role.name == RoleType.TECHNICIAN:
                        # Technicians can only see their own submissions
                        query = query.join(
                            FormSubmission, 
                            FormSubmission.id == AnswerSubmitted.form_submission_id
                        ).filter(FormSubmission.submitted_by == current_user.username)
                    elif current_user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                        # Site managers and supervisors can see submissions from users in their environment
                        query = query.join(
                            FormSubmission, 
                            FormSubmission.id == AnswerSubmitted.form_submission_id
                        ).join(
                            User, 
                            User.username == FormSubmission.submitted_by
                        ).filter(
                            User.environment_id == current_user.environment_id
                        )
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination
            answers_submitted = query.order_by(AnswerSubmitted.id).offset(offset).limit(per_page).all()
            
            # Convert to dictionary representation
            answers_submitted_data = [answer.to_dict() for answer in answers_submitted]
            
            return total_count, answers_submitted_data
            
        except Exception as e:
            logger.error(f"Error in answers submitted batch pagination service: {str(e)}")
            return 0, []

    @staticmethod
    def get_answers_by_submission(submission_id: int) -> Tuple[List[AnswerSubmitted], Optional[str]]:
        """Get all answers for a specific submission"""
        try:
            answers = AnswerSubmitted.query.filter_by(
                form_submission_id=submission_id,
                is_deleted=False
            ).all()
            return answers, None
        except Exception as e:
            logger.error(f"Error getting answers by submission: {str(e)}")
            return [], str(e)

    @staticmethod
    def update_answer_submitted(
        answer_submitted_id: int,
        answer_text: Optional[str] = None,
        column: Optional[int] = None,
        row: Optional[int] = None,
        cell_content: Optional[str] = None
    ) -> Tuple[Optional[AnswerSubmitted], Optional[str]]:
        """Update a submitted answer with table support"""
        try:
            answer = AnswerSubmitted.query.filter_by(
                id=answer_submitted_id,
                is_deleted=False
            ).first()
            
            if not answer:
                return None, "Answer submission not found"

            if answer_text is not None:
                answer.answer = answer_text
                
            # Update table-specific fields if this is a table-type question
            if answer.question_type == 'table':
                if column is not None:
                    answer.column = column
                if row is not None:
                    answer.row = row
                if cell_content is not None:
                    answer.cell_content = cell_content
                    
            answer.updated_at = datetime.utcnow()

            db.session.commit()
            return answer, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating answer submitted: {str(e)}")
            return None, str(e)

    @staticmethod
    def delete_answer_submitted(answer_submitted_id: int) -> Tuple[bool, Optional[str]]:
        """Soft delete a submitted answer"""
        try:
            answer = AnswerSubmitted.query.filter_by(
                id=answer_submitted_id,
                is_deleted=False
            ).first()
            
            if not answer:
                return False, "Answer submission not found"

            answer.soft_delete()
            db.session.commit()
            return True, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting answer submitted: {str(e)}")
            return False, str(e)
            
    @staticmethod
    def get_table_cells(submission_id: int, question_text: str) -> Tuple[List[AnswerSubmitted], Optional[str]]:
        """
        Get all cells for a table-type question in a specific submission
        
        Args:
            submission_id: ID of the form submission
            question_text: Text of the table question
            
        Returns:
            tuple: (List of AnswerSubmitted objects for table cells, Error message or None)
        """
        try:
            cells = AnswerSubmitted.query.filter_by(
                form_submission_id=submission_id,
                question=question_text,
                question_type='table',
                is_deleted=False
            ).order_by(AnswerSubmitted.row, AnswerSubmitted.column).all()
            
            return cells, None
            
        except Exception as e:
            logger.error(f"Error getting table cells: {str(e)}")
            return [], str(e)
            
    @staticmethod
    def get_table_structure(submission_id: int, question_text: str) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get the structure of a table-type question response
        
        Args:
            submission_id: ID of the form submission
            question_text: Text of the table question
            
        Returns:
            tuple: (Dictionary with table structure or None, Error message or None)
        """
        try:
            cells, error = AnswerSubmittedService.get_table_cells(submission_id, question_text)
            
            if error:
                return None, error
                
            if not cells:
                return None, "No table data found"
                
            # Determine table dimensions
            max_row = max(cell.row for cell in cells) if cells else 0
            max_column = max(cell.column for cell in cells) if cells else 0
            
            # Create table structure
            table = {
                'rows': max_row + 1,
                'columns': max_column + 1,
                'cells': {}
            }
            
            # Fill in cell data
            for cell in cells:
                row_key = str(cell.row)
                col_key = str(cell.column)
                
                if row_key not in table['cells']:
                    table['cells'][row_key] = {}
                    
                table['cells'][row_key][col_key] = {
                    'id': cell.id,
                    'content': cell.cell_content or '',
                    'answer': cell.answer or ''
                }
            
            return table, None
            
        except Exception as e:
            error_msg = f"Error getting table structure: {str(e)}"
            logger.error(error_msg)
            return None, error_msg