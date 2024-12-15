from typing import Dict, List, Optional, Tuple
from app import db
from app.models.answer_submitted import AnswerSubmitted
from app.models.attachment import Attachment
from app.models.form_submission import FormSubmission
from app.models.question import Question
from datetime import datetime
from werkzeug.datastructures import FileStorage
import os
import logging

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
        upload_path: Optional[str] = None
    ) -> Tuple[Optional[AnswerSubmitted], Optional[str]]:
        """
        Create a new answer submission with signature handling.
        
        Args:
            form_submission_id: ID of the form submission
            question_text: The text of the question
            answer_text: The answer text
            is_signature: Whether this answer requires a signature
            signature_file: File object for signature if applicable
            upload_path: Base path for file uploads
            
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

            # Create answer submission
            answer_submitted = AnswerSubmitted(
                form_submission_id=form_submission_id,
                question=question_text,
                question_type=question_type_text,
                answer=answer_text
            )
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
        Bulk create answer submissions with signature handling.
        
        Args:
            form_submission_id: ID of the form submission
            answers_data: List of dictionaries containing answer data
            upload_path: Base path for file uploads
            
        Returns:
            tuple: (List of created AnswerSubmitted objects or None, Error message or None)
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

            for data in answers_data:
                question_text = data.get('question_text')
                question_type_text = data.get('question_type')
                answer_text = data.get('answer_text')
                is_signature = data.get('is_signature', False)
                signature_file = data.get('signature_file')

                if not question_text or not answer_text:
                    return None, "Question text and answer text are required"

                answer_submitted = AnswerSubmitted(
                    form_submission_id=form_submission_id,
                    question=question_text,
                    question_type=question_type_text,
                    answer=answer_text
                )
                db.session.add(answer_submitted)
                created_submissions.append(answer_submitted)

                # Handle signature if applicable
                if is_signature and signature_file and upload_path:
                    # Create signature directory
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
        query = AnswerSubmitted.query.filter_by(is_deleted=False)
        
        if filters:
            if 'form_submission_id' in filters:
                query = query.filter_by(form_submission_id=filters['form_submission_id'])
        
        return query.order_by(AnswerSubmitted.created_at.desc()).all()

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
        answer_text: Optional[str] = None
    ) -> Tuple[Optional[AnswerSubmitted], Optional[str]]:
        """Update a submitted answer"""
        try:
            answer = AnswerSubmitted.query.filter_by(
                id=answer_submitted_id,
                is_deleted=False
            ).first()
            
            if not answer:
                return None, "Answer submission not found"

            if answer_text is not None:
                answer.answer = answer_text
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