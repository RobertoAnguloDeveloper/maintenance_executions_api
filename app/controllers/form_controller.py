# app/controllers/form_controller.py

from app.services.form_service import FormService

class FormController:
    @staticmethod
    def create_form(title, description, user_id, questions, is_public=False):
        """Create a new form with questions"""
        return FormService.create_form_with_questions(
            title=title,
            description=description,
            user_id=user_id,
            questions=questions,
            is_public=is_public
        )

    @staticmethod
    def get_form(form_id):
        """
        Get a form by ID with all relationships
        
        Args:
            form_id (int): ID of the form
            
        Returns:
            Form: Form object with loaded relationships or None if not found
        """
        return FormService.get_form(form_id)

    @staticmethod
    def get_forms_by_user(user_id):
        """Get all forms created by a user"""
        return FormService.get_forms_by_user(user_id)

    @staticmethod
    def get_forms_by_user_or_public(user_id, is_public=None):
        """Get forms created by user or public forms"""
        return FormService.get_forms_by_user_or_public(user_id, is_public)

    @staticmethod
    def get_forms_by_creator(username):
        """
        Get all forms created by a specific username
        
        Args:
            username (str): Username of the creator
            
        Returns:
            list: List of Form objects or None if user not found
        """
        return FormService.get_forms_by_creator(username)

    @staticmethod
    def get_public_forms():
        """
        Get all public forms
        
        Returns:
            list: List of public Form objects
        """
        return FormService.get_public_forms()
        
    @staticmethod
    def get_forms_by_environment(environment_id):
        """Get all forms related to an environment"""
        return FormService.get_forms_by_environment(environment_id)

    @staticmethod
    def get_all_forms(is_public=None):
        """Get all forms with optional public filter"""
        return FormService.get_all_forms(is_public=is_public)

    @staticmethod
    def update_form(form_id, **kwargs):
        """Update a form's details"""
        return FormService.update_form(form_id, **kwargs)

    @staticmethod
    def delete_form(form_id):
        """Delete a form"""
        return FormService.delete_form(form_id)

    @staticmethod
    def add_questions_to_form(form_id, questions):
        """Add new questions to an existing form"""
        return FormService.add_questions_to_form(form_id, questions)

    @staticmethod
    def reorder_questions(form_id, question_order):
        """Reorder questions in a form"""
        return FormService.reorder_questions(form_id, question_order)

    @staticmethod
    def submit_form(form_id, username, answers, attachments=None):
        """Submit a form with answers"""
        return FormService.submit_form(form_id, username, answers, attachments)

    @staticmethod
    def get_form_submissions(form_id):
        """Get all submissions for a form"""
        return FormService.get_form_submissions(form_id)

    @staticmethod
    def get_form_statistics(form_id):
        """Get statistics for a form"""
        return FormService.get_form_statistics(form_id)

    @staticmethod
    def search_forms(query=None, user_id=None, is_public=None):
        """Search forms based on criteria"""
        return FormService.search_forms(query, user_id, is_public)