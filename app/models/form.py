from app import db
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin
from sqlalchemy.orm import joinedload
from sqlalchemy import select, func
from typing import List, Dict, Any

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
            'environment_id': self.creator.environment_id
        }

    def _get_submissions_count(self) -> int:
        """Get count of submissions for this form."""
        from app.models.form_submission import FormSubmission
        return FormSubmission.query.filter_by(form_submitted=str(self.id)).count()

    def _get_question_answers(self, form_question) -> List[Dict[str, Any]]:
        """Get possible answers for a specific form question through form_answers."""
        if form_question.question.question_type.type not in ['single_choice', 'multiple_choice', 'single-choice']:
            return []

        from app.models.form_answer import FormAnswer
        form_answers = FormAnswer.query.filter_by(form_question_id=form_question.id).all()
        
        return [{
            'id': form_answer.answer.id,
            'value': form_answer.answer.value,
            'remarks': form_answer.remarks
        } for form_answer in form_answers if form_answer.answer]

    def _format_question(self, form_question) -> Dict[str, Any]:
        """Format a single question with its details."""
        question = form_question.question
        return {
            'id': question.id,
            'text': question.text,
            'type': question.question_type.type,
            'order_number': form_question.order_number,
            'has_remarks': question.has_remarks,
            'possible_answers': self._get_question_answers(form_question)
        }

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
            'assigned_to': self._get_creator_dict(),
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