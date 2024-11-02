from app import db
from app.models.form_answer import FormAnswer
from sqlalchemy.exc import IntegrityError

class FormAnswerService:
    @staticmethod
    def create_form_answer(form_question_id, answer_id, remarks=None):
        """
        Create a new form answer
        
        Args:
            form_question_id (int): ID of the form question
            answer_id (int): ID of the answer
            remarks (str): Optional remarks
            
        Returns:
            tuple: (FormAnswer, error_message)
        """
        try:
            form_answer = FormAnswer(
                form_question_id=form_question_id,
                answer_id=answer_id,
                remarks=remarks
            )
            db.session.add(form_answer)
            db.session.commit()
            return form_answer, None
        except IntegrityError:
            db.session.rollback()
            return None, "Invalid form_question_id or answer_id"
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def get_answers_by_form_question(form_question_id):
        """Get all answers for a specific form question"""
        return FormAnswer.query.filter_by(form_question_id=form_question_id).all()

    @staticmethod
    def update_form_answer(form_answer_id, **kwargs):
        """Update a form answer"""
        form_answer = FormAnswer.query.get(form_answer_id)
        if form_answer:
            try:
                for key, value in kwargs.items():
                    if hasattr(form_answer, key):
                        setattr(form_answer, key, value)
                db.session.commit()
                return form_answer, None
            except IntegrityError:
                db.session.rollback()
                return None, "Invalid answer_id provided"
            except Exception as e:
                db.session.rollback()
                return None, str(e)
        return None, "Form answer not found"

    @staticmethod
    def delete_form_answer(form_answer_id):
        """Delete a form answer"""
        form_answer = FormAnswer.query.get(form_answer_id)
        if form_answer:
            try:
                db.session.delete(form_answer)
                db.session.commit()
                return True, None
            except Exception as e:
                db.session.rollback()
                return False, str(e)
        return False, "Form answer not found"