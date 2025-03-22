from app import db
from app.models.answer import Answer
from app.models.form_answer import FormAnswer
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

    # Relationships
    creator = db.relationship('User', back_populates='created_forms')
    form_questions = db.relationship('FormQuestion', back_populates='form', 
                                   cascade='all, delete-orphan',
                                   order_by='FormQuestion.order_number')
    submissions = db.relationship('FormSubmission', back_populates='form',
                                cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'<Form {self.title}>'

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

    def _get_submissions_count(self) -> int:
        """Get count of submissions for this form."""
        from app.models.form_submission import FormSubmission
        return FormSubmission.query.filter_by(form_id=str(self.id), is_deleted=False).count()

    def _get_question_answers(self, form_question) -> List[Dict[str, Any]]:
        """
        Get possible answers for a specific form question through form_answers.
        
        Args:
            form_question: FormQuestion object
                
        Returns:
            List of dictionaries containing answer data
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
                if form_answer.answer and form_answer.answer_id not in unique_answers:
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
        question_type = question.question_type.type

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
        if question_type in ['checkbox', 'multiple_choices']:
            formatted_question['possible_answers'] = self._get_question_answers(form_question)

        return formatted_question

    def _get_questions_list(self) -> List[Dict[str, Any]]:
        """Get formatted list of questions."""
        sorted_questions = sorted(self.form_questions, key=lambda x: x.order_number)
        return [self._format_question(fq) for fq in sorted_questions]

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
            'created_at': self._format_timestamp(self.created_at),
            'updated_at': self._format_timestamp(self.updated_at),
            'created_by': self._get_creator_dict(),
            'questions': self._get_questions_list(),
            'submissions_count': self._get_submissions_count()
        }

    @classmethod
    def get_form_with_relations(cls, form_id: int):
        """Get form with all necessary relationships loaded."""
        return cls.query.options(
            joinedload(cls.creator),
            joinedload(cls.form_questions)
                .joinedload('question')
                .joinedload('question_type'),
            joinedload(cls.form_questions)
                .joinedload('form_answers')
                .joinedload('answer')
        ).get(form_id)