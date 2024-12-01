from typing import Any, Dict, List
from app import db
from app.models.soft_delete_mixin import SoftDeleteMixin
from app.models.timestamp_mixin import TimestampMixin
from datetime import datetime
from sqlalchemy.orm import joinedload

class FormSubmission(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'form_submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=False)
    submitted_by = db.Column(db.String(50), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    form = db.relationship('Form', back_populates='submissions')
    
    answers_submitted = db.relationship(
        'AnswerSubmitted',
        back_populates='form_submission',
        foreign_keys='AnswerSubmitted.form_submissions_id',
        cascade='all, delete-orphan'
    )
    attachments = db.relationship(
        'Attachment',
        back_populates='form_submission',
        foreign_keys='Attachment.form_submission_id',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<FormSubmission {self.id} by {self.submitted_by}>'

    def _get_form_info(self) -> Dict[str, Any]:
        """Get associated form information."""
        from app.models.form import Form
        form = Form.query.get(int(self.form_id))
        if not form:
            return None
        
        return {
            'id': form.id,
            'title': form.title,
            'description': form.description,
            'is_public': form.is_public
        }

    def _get_answers_list(self) -> List[Dict[str, Any]]:
        """Get formatted list of submitted answers."""
        answers = []
        for answer_submitted in self.answers_submitted:
            form_answer = answer_submitted.form_answer
            if form_answer:
                question = form_answer.form_question.question
                answer = form_answer.answer
                answers.append({
                    'question': question.text,
                    'answer': answer.value if answer else None,
                    'remarks': form_answer.remarks
                })
        return answers

    def _get_attachments_list(self) -> List[Dict[str, Any]]:
        """Get formatted list of attachments."""
        return [{
            'id': attachment.id,
            'file_type': attachment.file_type,
            'file_path': attachment.file_path,
            'is_signature': attachment.is_signature
        } for attachment in self.attachments]

    def to_dict(self):
        """Convert form submission to dictionary representation."""
        return {
            'id': self.id,
            'form': self._get_form_info(),
            'submitted_by': self.submitted_by,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'answers': [{
                'question': answer.form_answer.form_question.question.text,
                'question_type': answer.form_answer.get_question_type(),
                'value': answer.form_answer.answer.value if not answer.form_answer.requires_text_answer() else None,
                'text_answered': answer.text_answered if answer.form_answer.requires_text_answer() else None,
                'remarks': answer.form_answer.answer.remarks
            } for answer in self.answers_submitted],
            'attachments': self._get_attachments_list()
        }

    @classmethod
    def get_submission_with_relations(cls, submission_id: int):
        """Get submission with all necessary relationships loaded."""
        return cls.query.options(
            joinedload(cls.answers_submitted)
                .joinedload('form_answer')
                .joinedload('form_question')
                .joinedload('question'),
            joinedload(cls.attachments)
        ).get(submission_id)