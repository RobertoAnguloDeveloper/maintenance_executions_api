from app import db
from app.models.form import Form
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from sqlalchemy.orm import joinedload

class FormService:
    @staticmethod
    def create_form(title, description, user_id, question_id, answer_id, is_public=False):
        """
        Create a new form with the provided details
        """
        try:
            new_form = Form(
                title=title,
                description=description,
                user_id=user_id,
                question_id=question_id,
                answer_id=answer_id,
                is_public=is_public
            )
            db.session.add(new_form)
            db.session.commit()
            return new_form, None
        except IntegrityError as e:
            db.session.rollback()
            return None, "Invalid user_id, question_id, or answer_id"
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def get_form(form_id):
        """
        Get a form with all its relationships loaded
        """
        return Form.query.options(
            joinedload(Form.creator),
            joinedload(Form.question),
            joinedload(Form.answer)
        ).get(form_id)

    @staticmethod
    def get_forms_by_user(user_id):
        """
        Get all forms created by a specific user
        """
        return Form.query.filter_by(user_id=user_id).order_by(Form.created_at.desc()).all()

    @staticmethod
    def get_public_forms():
        """
        Get all public forms
        """
        return Form.query.filter_by(is_public=True).order_by(Form.created_at.desc()).all()

    @staticmethod
    def get_all_forms():
        """
        Get all forms with their relationships
        """
        return Form.query.options(
            joinedload(Form.creator),
            joinedload(Form.question),
            joinedload(Form.answer)
        ).order_by(Form.created_at.desc()).all()

    @staticmethod
    def update_form(form_id, **kwargs):
        """
        Update form details
        """
        form = Form.query.get(form_id)
        if form:
            try:
                for key, value in kwargs.items():
                    if hasattr(form, key):
                        setattr(form, key, value)
                db.session.commit()
                return form, None
            except IntegrityError:
                db.session.rollback()
                return None, "Invalid user_id, question_id, or answer_id"
            except Exception as e:
                db.session.rollback()
                return None, str(e)
        return None, "Form not found"

    @staticmethod
    def delete_form(form_id):
        """
        Delete a form and its relationships
        """
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

    @staticmethod
    def search_forms(query=None, user_id=None, is_public=None):
        """
        Search forms based on various criteria
        """
        forms = Form.query
        if query:
            forms = forms.filter(Form.title.ilike(f"%{query}%"))
        if user_id is not None:
            forms = forms.filter_by(user_id=user_id)
        if is_public is not None:
            forms = forms.filter_by(is_public=is_public)
        return forms.order_by(Form.created_at.desc()).all()