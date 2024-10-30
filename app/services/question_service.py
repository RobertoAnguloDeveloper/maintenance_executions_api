from app import db
from app.models.question import Question
from sqlalchemy.exc import IntegrityError
from datetime import datetime

class QuestionService:
    @staticmethod
    def create_question(text, question_type_id, order_number, has_remarks=False):
        try:
            new_question = Question(
                text=text,
                question_type_id=question_type_id,
                order_number=order_number,
                has_remarks=has_remarks
            )
            db.session.add(new_question)
            db.session.commit()
            return new_question, None
        except IntegrityError:
            db.session.rollback()
            return None, "Error creating question. Please check the question_type_id."
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def get_question(question_id):
        return Question.query.get(question_id)

    @staticmethod
    def get_questions_by_type(question_type_id):
        return Question.query.filter_by(question_type_id=question_type_id).order_by(Question.order_number).all()

    @staticmethod
    def get_all_questions():
        return Question.query.order_by(Question.order_number).all()

    @staticmethod
    def update_question(question_id, **kwargs):
        question = Question.query.get(question_id)
        if question:
            try:
                for key, value in kwargs.items():
                    if hasattr(question, key):
                        setattr(question, key, value)
                db.session.commit()
                return question, None
            except IntegrityError:
                db.session.rollback()
                return None, "Error updating question. Please check the question_type_id."
            except Exception as e:
                db.session.rollback()
                return None, str(e)
        return None, "Question not found"

    @staticmethod
    def delete_question(question_id):
        question = Question.query.get(question_id)
        if question:
            try:
                db.session.delete(question)
                db.session.commit()
                return True, None
            except Exception as e:
                db.session.rollback()
                return False, str(e)
        return False, "Question not found"

    @staticmethod
    def reorder_questions(questions_order):
        """
        Update the order of multiple questions
        :param questions_order: List of tuples (question_id, new_order)
        """
        try:
            for question_id, new_order in questions_order:
                question = Question.query.get(question_id)
                if question:
                    question.order_number = new_order
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, str(e)