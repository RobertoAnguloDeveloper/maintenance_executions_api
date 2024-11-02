from app import db
from app.models.form import Form
from app.models.form_question import FormQuestion
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

class FormService:
    @staticmethod
    def create_form(title, description, user_id, questions, is_public=False):
        """
        Create a new form with questions
        
        Args:
            title (str): Form title
            description (str): Form description
            user_id (int): ID of the user creating the form
            questions (list): List of dicts with question_id and order_number
            is_public (bool): Whether the form is public
            
        Returns:
            tuple: (Form, error_message)
        """
        try:
            new_form = Form(
                title=title,
                description=description,
                user_id=user_id,
                is_public=is_public
            )
            db.session.add(new_form)
            
            # Add questions with order
            for q in questions:
                form_question = FormQuestion(
                    form=new_form,
                    question_id=q['question_id'],
                    order_number=q.get('order_number')
                )
                db.session.add(form_question)
            
            db.session.commit()
            return new_form, None
        except IntegrityError:
            db.session.rollback()
            return None, "Invalid user_id or question_id"
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def get_form(form_id):
        """Get a form with all its relationships loaded"""
        return Form.query.options(
            joinedload(Form.form_questions).joinedload(FormQuestion.question)
        ).get(form_id)

    @staticmethod
    def update_form(form_id, **kwargs):
        """Update form details and questions"""
        form = Form.query.get(form_id)
        if not form:
            return None, "Form not found"

        try:
            # Update basic form details
            for key, value in kwargs.items():
                if key != 'questions' and hasattr(form, key):
                    setattr(form, key, value)

            # Update questions if provided
            if 'questions' in kwargs:
                # Remove existing questions
                FormQuestion.query.filter_by(form_id=form_id).delete()
                
                # Add new questions
                for q in kwargs['questions']:
                    form_question = FormQuestion(
                        form=form,
                        question_id=q['question_id'],
                        order_number=q.get('order_number')
                    )
                    db.session.add(form_question)

            db.session.commit()
            return form, None
        except IntegrityError:
            db.session.rollback()
            return None, "Invalid question_id provided"
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def delete_form(form_id):
        """Delete a form and its related data"""
        form = Form.query.get(form_id)
        if form:
            try:
                db.session.delete(form)
                db.session.commit()
                return True, None
            except Exception as e:
                db.session.rollback()
                return False, str(e)
        return False, "Form not found"