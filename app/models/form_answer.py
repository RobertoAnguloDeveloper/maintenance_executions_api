from app import db
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin
from datetime import datetime

class FormAnswer(TimestampMixin, SoftDeleteMixin, db.Model):
    """
    Model representing possible answers for a form question.
    This model serves as a mapping between form questions and their possible answers.
    """
    __tablename__ = 'form_answers'
    
    id = db.Column(db.Integer, primary_key=True)
    form_question_id = db.Column(db.Integer, db.ForeignKey('form_questions.id', ondelete='CASCADE'), nullable=False)
    answer_id = db.Column(db.Integer, db.ForeignKey('answers.id'), nullable=False)
    remarks = db.Column(db.Text)

    # Relationships
    form_question = db.relationship('FormQuestion', back_populates='form_answers')
    answer = db.relationship('Answer', back_populates='form_answers')

    def __init__(self, form_question_id=None, answer_id=None, remarks=None):
        self.form_question_id = form_question_id
        self.answer_id = answer_id
        self.remarks = remarks

    def __repr__(self):
        return f'<FormAnswer {self.id} - Question: {self.form_question_id}, Answer: {self.answer_id}>'
    
    def to_dict_basic(self) -> dict:
        """Return dictionary with basic fields only"""
        return {
            'id': self.id,
            'form_question_id': self.form_question_id,
            'answer_id': self.answer_id,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_deleted': self.is_deleted,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    def soft_delete(self):
        """Perform soft delete"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()

    def restore(self):
        """Restore from soft delete"""
        self.is_deleted = False
        self.deleted_at = None

    def get_question_type(self) -> str:
        """Get the question type for this form answer"""
        if self.form_question and self.form_question.question:
            return self.form_question.question.question_type.type
        return None

    def requires_text_answer(self) -> bool:
        """Check if this form answer requires text input"""
        question_type = self.get_question_type()
        return question_type in ['text', 'date', 'datetime']

    def to_dict(self) -> dict:
        """Convert form answer to dictionary representation"""
        return {
            'id': self.id,
            'form_question': {
                "id": self.form_question_id,
                "form": {
                    "id": self.form_question.form.id,
                    "title": self.form_question.form.title
                } if self.form_question and self.form_question.form else None,
                "question": {
                    "id": self.form_question.question.id,
                    "text": self.form_question.question.text,
                    "type": self.get_question_type(),
                    "is_signature": self.form_question.question.is_signature
                } if self.form_question and self.form_question.question else None
            } if self.form_question else None,
            'answer': self.answer.to_dict() if self.answer else None,
            'remarks': self.remarks,
            'requires_text_answer': self.requires_text_answer(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def get_active(cls):
        """Get all non-deleted form answers"""
        return cls.query.filter_by(is_deleted=False)

    @classmethod
    def get_deleted(cls):
        """Get all deleted form answers"""
        return cls.query.filter_by(is_deleted=True)

    @classmethod
    def get_all_with_deleted(cls):
        """Get all form answers including deleted ones"""
        return cls.query