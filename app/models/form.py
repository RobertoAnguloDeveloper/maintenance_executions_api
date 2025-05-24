# app/models/form.py

from app import db
from app.models.answer import Answer # Not directly used but good for context
from app.models.form_answer import FormAnswer
from app.models.form_question import FormQuestion
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin
from sqlalchemy.orm import joinedload
from sqlalchemy import select, func
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class Form(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'forms'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_public = db.Column(db.Boolean, nullable=False, default=False)
    attachments_required = db.Column(db.Boolean, nullable=False, default=False) # New field

    # Relationships
    creator = db.relationship('User', back_populates='created_forms')
    report_templates = db.relationship('ReportTemplate', back_populates='form',
                                        cascade='all, delete-orphan',
                                        order_by='ReportTemplate.created_at.desc()')
    form_questions = db.relationship('FormQuestion', back_populates='form', 
                                   cascade='all, delete-orphan',
                                   order_by='FormQuestion.order_number')
    submissions = db.relationship('FormSubmission', back_populates='form',
                                cascade='all, delete-orphan')
    # New relationship
    form_assignments = db.relationship('FormAssignment', back_populates='form',
                                    cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'<Form {self.title}>'
    
    def to_dict_basic(self) -> dict:
        """Return dictionary with basic fields only"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'user_id': self.user_id,
            'is_public': self.is_public,
            'attachments_required': self.attachments_required, # New field
            'created_at': self._format_timestamp(self.created_at),
            'updated_at': self._format_timestamp(self.updated_at),
            'is_deleted': self.is_deleted,
            'deleted_at': self._format_timestamp(self.deleted_at)
        }

    def _get_creator_dict(self) -> Dict[str, Any]:
        """Get creator information as a dictionary."""
        if not self.creator:
            return None
            
        return {
            'id': self.creator.id,
            'username': self.creator.username,
            'first_name': self.creator.first_name,
            'last_name': self.creator.last_name,
            'email': self.creator.email,
            'fullname': self.creator.first_name+" "+self.creator.last_name,
            'environment': {
                            "id": self.creator.environment_id,
                            "name": self.creator.environment.name if self.creator.environment else None
                            }
        }

    def _get_simplified_creator_dict(self) -> Dict[str, Any]:
        """Get simplified creator information as a dictionary for batch responses."""
        if not self.creator:
            return None
            
        return {
            'id': self.creator.id,
            'fullname': self.creator.first_name+" "+self.creator.last_name
        }

    def _get_submissions_count(self) -> int:
        """Get count of submissions for this form."""
        from app.models.form_submission import FormSubmission # Local import
        return FormSubmission.query.filter_by(form_id=self.id, is_deleted=False).count()

    def _get_questions_count(self) -> int:
        """Get count of non-deleted questions for this form."""
        return len([q for q in self.form_questions if not q.is_deleted])

    def _get_Youtubes(self, form_question) -> List[Dict[str, Any]]:
        """
        Get possible answers for a specific form question through form_answers.
        """
        try:
            # Get all form_answers for this form_question using eager loading
            form_answers = FormAnswer.query.options(
                joinedload(FormAnswer.answer)
            ).filter_by(
                form_question_id=form_question.id,
                is_deleted=False  # Add soft delete filter
            ).join(
                Answer, FormAnswer.answer_id == Answer.id  # Join with Answer table
            ).order_by(
                Answer.id  # Order by Answer ID to maintain consistent order
            ).all()

            # Create a dictionary of unique answers based on answer_id
            unique_answers = {}
            for form_answer in form_answers:
                if form_answer.answer and form_answer.answer_id not in unique_answers: # Check if answer is not soft-deleted
                    unique_answers[form_answer.answer_id] = {
                        'id': form_answer.answer.id,
                        'form_answer_id': form_answer.id,
                        'value': form_answer.answer.value
                    }

            # Return a list of answers ordered by answer ID
            return [unique_answers[answer_id] for answer_id in sorted(unique_answers.keys())]

        except Exception as e:
            logger.error(f"Error getting answers for question {form_question.id}: {str(e)}")
            return []

    def _format_question(self, form_question) -> Dict[str, Any]:
        """
        Format a single question with its details.
        Only include possible answers for choice-type questions.
        """
        question = form_question.question
        if not question or question.is_deleted: # Check if question is soft-deleted
             return None # Skip soft-deleted questions

        question_type = question.question_type.type if question.question_type and not question.question_type.is_deleted else None # Check question_type

        # Base question data
        formatted_question = {
            'id': question.id,
            'form_question_id': form_question.id,
            'text': question.text,
            'type': question_type,
            'is_signature': question.is_signature,
            'order_number': form_question.order_number,
            'remarks': question.remarks
        }

        # Add possible answers only for choice-type questions
        if question_type in ['checkbox', 'multiple_choices','table', 'dropdown', 'single_choice']:
            formatted_question['possible_answers'] = self._get_Youtubes(form_question)

        return formatted_question

    def _get_questions_list(self) -> List[Dict[str, Any]]:
        """Get formatted list of questions, excluding soft-deleted ones."""
        # Filter out form_questions that are soft-deleted or link to soft-deleted questions
        active_form_questions = [
            fq for fq in self.form_questions 
            if not fq.is_deleted and fq.question and not fq.question.is_deleted
        ]
        sorted_questions = sorted(active_form_questions, key=lambda x: x.order_number if x.order_number is not None else float('inf'))
        
        formatted_list = []
        for fq in sorted_questions:
            formatted_q = self._format_question(fq)
            if formatted_q: # Ensure None is not added if _format_question returns it
                 formatted_list.append(formatted_q)
        return formatted_list


    def _format_timestamp(self, timestamp) -> str:
        """Format timestamp to ISO format."""
        return timestamp.isoformat() if timestamp else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert form to dictionary representation."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'is_public': self.is_public,
            'attachments_required': self.attachments_required, # New field
            'created_at': self._format_timestamp(self.created_at),
            'updated_at': self._format_timestamp(self.updated_at),
            'created_by': self._get_creator_dict(),
            'questions': self._get_questions_list(),
            'submissions_count': self._get_submissions_count()
        }
        
    def to_batch_dict(self) -> Dict[str, Any]:
        """
        Convert form to simplified dictionary representation for batch responses.
        Returns only the essential attributes needed for the forms/batch endpoint.
        """
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'is_public': self.is_public,
            'attachments_required': self.attachments_required, # New field
            'created_at': self._format_timestamp(self.created_at),
            'updated_at': self._format_timestamp(self.updated_at),
            'created_by': self._get_simplified_creator_dict(),
            'questions_count': self._get_questions_count(),
            'submissions_count': self._get_submissions_count()
            # 'is_editable' will be added in the controller/service
        }

    @classmethod
    def get_form_with_relations(cls, form_id: int):
        """Get form with all necessary relationships loaded."""
        return cls.query.options(
            joinedload(cls.creator),
            joinedload(cls.form_questions)
                .joinedload(FormQuestion.question) # Updated to use FormQuestion.question
                .joinedload('question_type'),
            joinedload(cls.form_questions)
                .joinedload(FormQuestion.form_answers) # Updated to use FormQuestion.form_answers
                .joinedload(FormAnswer.answer) # Updated to use FormAnswer.answer
        ).filter(cls.id == form_id, cls.is_deleted == False).first() # Added is_deleted filter