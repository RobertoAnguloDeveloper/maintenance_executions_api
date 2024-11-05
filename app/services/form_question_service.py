# app/services/form_question_service.py

from app import db
from app.models.form_question import FormQuestion
from sqlalchemy.exc import IntegrityError
from datetime import datetime

class FormQuestionService:
    @staticmethod
    def create_form_question(form_id, question_id, order_number=None):
        """Create a new form question mapping"""
        try:
            # If no order number provided, get the next available one
            if order_number is None:
                max_order = db.session.query(db.func.max(FormQuestion.order_number))\
                    .filter_by(form_id=form_id).scalar()
                order_number = (max_order or 0) + 1

            form_question = FormQuestion(
                form_id=form_id,
                question_id=question_id,
                order_number=order_number
            )
            db.session.add(form_question)
            db.session.commit()
            return form_question, None

        except IntegrityError:
            db.session.rollback()
            return None, "Invalid form_id or question_id"
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def get_form_question(form_question_id):
        """Get a specific form question mapping"""
        return FormQuestion.query.get(form_question_id)

    @staticmethod
    def get_questions_by_form(form_id):
        """Get all questions for a specific form"""
        return FormQuestion.query\
            .filter_by(form_id=form_id)\
            .order_by(FormQuestion.order_number)\
            .all()

    @staticmethod
    def update_form_question(form_question_id, **kwargs):
        """Update a form question mapping"""
        try:
            form_question = FormQuestion.query.get(form_question_id)
            if not form_question:
                return None, "Form question not found"

            # Update fields
            for key, value in kwargs.items():
                if hasattr(form_question, key):
                    setattr(form_question, key, value)

            form_question.updated_at = datetime.utcnow()
            db.session.commit()
            return form_question, None

        except IntegrityError:
            db.session.rollback()
            return None, "Invalid question_id"
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def delete_form_question(form_question_id):
        """Delete a form question mapping"""
        try:
            form_question = FormQuestion.query.get(form_question_id)
            if not form_question:
                return False, "Form question not found"

            db.session.delete(form_question)
            db.session.commit()
            return True, None

        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def bulk_create_form_questions(form_id, questions):
        """
        Bulk create form questions
        
        Args:
            form_id (int): ID of the form
            questions (list): List of dicts with question_id and optional order_number
        """
        try:
            form_questions = []
            current_max_order = db.session.query(db.func.max(FormQuestion.order_number))\
                .filter_by(form_id=form_id).scalar() or 0

            for i, question in enumerate(questions, 1):
                form_question = FormQuestion(
                    form_id=form_id,
                    question_id=question['question_id'],
                    order_number=question.get('order_number', current_max_order + i)
                )
                form_questions.append(form_question)

            db.session.bulk_save_objects(form_questions)
            db.session.commit()
            return form_questions, None

        except IntegrityError:
            db.session.rollback()
            return None, "Invalid form_id or question_id"
        except Exception as e:
            db.session.rollback()
            return None, str(e)