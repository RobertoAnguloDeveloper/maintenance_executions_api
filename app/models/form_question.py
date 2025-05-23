from app import db
from app.models.question import Question
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin
import logging

logger = logging.getLogger(__name__)

class FormQuestion(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'form_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    order_number = db.Column(db.Integer)

    # Relationships
    form = db.relationship('Form', back_populates='form_questions')
    question = db.relationship('Question', back_populates='form_questions')
    form_answers = db.relationship('FormAnswer', back_populates='form_question', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<FormQuestion {self.form_id}:{self.question_id}>'
    
    def to_dict_basic(self) -> dict:
        """Return dictionary with basic fields only"""
        return {
            'id': self.id,
            'form_id': self.form_id,
            'question_id': self.question_id,
            'order_number': self.order_number,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_deleted': self.is_deleted,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    def to_dict(self):
        """Convert form question to dictionary with all related data"""
        try:
            # Get form answers with their values
            form_answers_data = []
            if self.form_answers:
                for form_answer in self.form_answers:
                    if not form_answer.is_deleted and form_answer.answer and not form_answer.answer.is_deleted:
                        form_answers_data.append({
                            'id': form_answer.answer.id,
                            'form_answer_id': form_answer.id,
                            'value': form_answer.answer.value
                        })

            # Build the response dictionary
            result = {
                'id': self.id,
                'form_id': self.form_id,
                'question_id': self.question_id,
                'order_number': self.order_number,
                'question': {
                    'text': self.question.text if self.question else None,
                    'type': self.question.question_type.type if self.question and self.question.question_type else None,
                    'remarks': self.question.remarks if self.question else None
                } if self.question else None,
                'form': {
                    'id': self.form.id,
                    'title': self.form.title,
                    'creator': self.form._get_creator_dict() if hasattr(self.form, '_get_creator_dict') else None
                } if self.form else None
            }

            # Only include possible answers for choice-type questions
            if self.question and self.question.question_type and \
            self.question.question_type.type in ['checkbox', 'multiple_choices', 'single_choice']:
                result['possible_answers'] = form_answers_data

            return result
        except Exception as e:
            logger.error(f"Error in form_question to_dict: {str(e)}")
            return {
                'id': self.id,
                'error': 'Error converting form question to dictionary'
            }