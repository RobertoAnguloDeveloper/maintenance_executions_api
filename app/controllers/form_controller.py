from app.services.form_service import FormService

class FormController:
    @staticmethod
    def create_form(title, description, user_id, question_id, answer_id, is_public=False):
        """
        Create a new form
        """
        return FormService.create_form(
            title=title,
            description=description,
            user_id=user_id,
            question_id=question_id,
            answer_id=answer_id,
            is_public=is_public
        )

    @staticmethod
    def get_form(form_id):
        """
        Get a form by ID with all relationships
        """
        return FormService.get_form(form_id)

    @staticmethod
    def get_forms_by_user(user_id):
        """
        Get all forms created by a user
        """
        return FormService.get_forms_by_user(user_id)

    @staticmethod
    def get_public_forms():
        """
        Get all public forms
        """
        return FormService.get_public_forms()

    @staticmethod
    def get_all_forms():
        """
        Get all forms
        """
        return FormService.get_all_forms()

    @staticmethod
    def update_form(form_id, **kwargs):
        """
        Update a form's details
        """
        return FormService.update_form(form_id, **kwargs)

    @staticmethod
    def delete_form(form_id):
        """
        Delete a form
        """
        return FormService.delete_form(form_id)

    @staticmethod
    def search_forms(query=None, user_id=None, is_public=None):
        """
        Search forms based on criteria
        """
        return FormService.search_forms(query, user_id, is_public)