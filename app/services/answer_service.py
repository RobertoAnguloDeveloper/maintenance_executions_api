from app import db
from app.models.answer import Answer
from sqlalchemy.exc import IntegrityError
from datetime import datetime

class AnswerService:
    @staticmethod
    def create_answer(value, remarks=None):
        """
        Create a new answer with the given value and optional remarks
        """
        try:
            new_answer = Answer(
                value=value,
                remarks=remarks
            )
            db.session.add(new_answer)
            db.session.commit()
            return new_answer, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def get_answer(answer_id):
        """
        Retrieve an answer by its ID
        """
        return Answer.query.filter_by(id=answer_id, is_deleted=False).first()

    @staticmethod
    def get_answers_by_form(form_id):
        """
        Get all answers associated with a specific form
        """
        return Answer.query.join(Answer.forms).filter_by(id=form_id, is_deleted=False).all()

    @staticmethod
    def get_all_answers(include_deleted=False):
        """Get all answers"""
        query = Answer.query
        if not include_deleted:
            query = query.filter(Answer.is_deleted == False)
        return query.order_by(Answer.id).all()

    @staticmethod
    def update_answer(answer_id, value=None, remarks=None):
        """
        Update an existing answer
        """
        answer = Answer.query.get(answer_id)
        if answer:
            try:
                if value is not None:
                    answer.value = value
                if remarks is not None:
                    answer.remarks = remarks
                db.session.commit()
                return answer, None
            except Exception as e:
                db.session.rollback()
                return None, str(e)
        return None, "Answer not found"

    @staticmethod
    def delete_answer(answer_id):
        """Soft delete an answer"""
        try:
            answer = Answer.query.get(answer_id)
            if answer:
                answer.soft_delete()
                db.session.commit()
                return True, None
            return False, "Answer not found"
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def bulk_create_answers(answers_data):
        """
        Create multiple answers at once
        :param answers_data: List of dictionaries containing answer data
        """
        try:
            new_answers = []
            for data in answers_data:
                answer = Answer(
                    value=data.get('value'),
                    remarks=data.get('remarks')
                )
                new_answers.append(answer)
            
            db.session.bulk_save_objects(new_answers)
            db.session.commit()
            return new_answers, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)