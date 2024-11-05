# app/services/answer_submitted_service.py

from app import db
from app.models.answers_submitted import AnswerSubmitted
from sqlalchemy.exc import IntegrityError
from datetime import datetime

class AnswerSubmittedService:
    @staticmethod
    def create_answer_submitted(form_answer_id, form_submission_id):
        """Create a new submitted answer"""
        try:
            # Check if answer already submitted for this submission
            existing = AnswerSubmitted.query.filter_by(
                form_answer_id=form_answer_id,
                form_submission_id=form_submission_id
            ).first()
            
            if existing:
                return None, "Answer already submitted for this submission"

            answer_submitted = AnswerSubmitted(
                form_answer_id=form_answer_id,
                form_submission_id=form_submission_id
            )
            db.session.add(answer_submitted)
            db.session.commit()
            return answer_submitted, None

        except IntegrityError:
            db.session.rollback()
            return None, "Invalid form_answer_id or form_submission_id"
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def get_answer_submitted(answer_submitted_id):
        """Get a specific submitted answer"""
        return AnswerSubmitted.query.get(answer_submitted_id)

    @staticmethod
    def get_answers_by_submission(submission_id):
        """Get all submitted answers for a form submission"""
        return AnswerSubmitted.query\
            .filter_by(form_submission_id=submission_id)\
            .order_by(AnswerSubmitted.created_at)\
            .all()

    @staticmethod
    def delete_answer_submitted(answer_submitted_id):
        """Delete a submitted answer"""
        try:
            answer_submitted = AnswerSubmitted.query.get(answer_submitted_id)
            if not answer_submitted:
                return False, "Submitted answer not found"

            db.session.delete(answer_submitted)
            db.session.commit()
            return True, None

        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def get_answers_by_user(username):
        """Get all submitted answers for a specific user"""
        return (AnswerSubmitted.query
                .join(AnswerSubmitted.form_submission)
                .filter_by(submitted_by=username)
                .all())

    @staticmethod
    def get_submission_statistics(submission_id):
        """Get statistics for a form submission"""
        try:
            submitted_answers = AnswerSubmitted.query\
                .filter_by(form_submission_id=submission_id)\
                .all()

            return {
                'total_answers': len(submitted_answers),
                'submission_time': submitted_answers[0].form_submission.submitted_at if submitted_answers else None,
                'has_remarks': any(sa.form_answer.remarks for sa in submitted_answers),
                'answer_types': [sa.form_answer.form_question.question.question_type.type for sa in submitted_answers]
            }

        except Exception as e:
            return None