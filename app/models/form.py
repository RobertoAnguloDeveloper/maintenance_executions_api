from app import db
from app.models.form_answer import FormAnswer
from app.models.timestamp_mixin import TimestampMixin

class Form(TimestampMixin, db.Model):
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

    def __repr__(self):
        return f'<Form {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'creator': {
                'id': self.creator.id,
                'username': self.creator.username,
                'first_name': self.creator.first_name,
                'last_name': self.creator.last_name,
                'environment_id': self.creator.environment_id
            } if self.creator else None,
            'questions': [{
                'id': fq.question.id,
                'text': fq.question.text,
                'type': fq.question.question_type.type,
                'order_number': fq.order_number,
                'has_remarks': fq.question.has_remarks,
                'possible_answers': [
                    {
                        'id': fa.answer.id,
                        'value': fa.answer.value,
                        'remarks': fa.answer.remarks
                    } for fa in FormAnswer.query.filter_by(form_question_id=fq.id).all()
                ] if fq.question.question_type.type in ['single_choice', 'multiple_choice'] else []
            } for fq in sorted(self.form_questions, key=lambda x: x.order_number)],
            'submissions_count': len(self.submissions)
        }