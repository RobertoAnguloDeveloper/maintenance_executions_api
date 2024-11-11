# app/controllers/form_controller.py

from app.models.form import Form
from app.services.form_service import FormService
import logging

logger = logging.getLogger(__name__)

class FormController:
    @staticmethod
    def create_form(title, description, user_id, is_public=False):
        """Create a new form with questions"""
        return FormService.create_form(
            title=title,
            description=description,
            user_id=user_id,
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
    def get_forms_by_environment(environment_id: int) -> list:
        """Get forms by environment with serialized response"""
        try:
            forms = FormService.get_forms_by_environment(environment_id)
            if forms is None:
                return None

            serialized_forms = []
            for form in forms:
                # Get submissions count
                submissions_count = FormService.get_form_submissions_count(form.id)

                # Format creator info
                creator_info = None
                if form.creator:
                    creator_info = {
                        'id': form.creator.id,
                        'assigned_to': {
                                        "user_id": form.creator.id,
                                        "username": form.creator.username,
                                        "role": {
                                                "id": form.creator.role.id if form.creator.role else None,
                                                "name": form.creator.role.name if form.creator.role else None,
                                                "description": form.creator.role.description if form.creator.role else None
                                                }
                                        },
                        'environment_id': form.creator.environment_id,
                        'environment_name': form.creator.environment.name if form.creator.environment else None
                    }

                # Create form dictionary
                form_dict = {
                    'id': form.id,
                    'title': form.title,
                    'description': form.description,
                    'is_public': form.is_public,
                    'created_at': form.created_at.isoformat() if form.created_at else None,
                    'updated_at': form.updated_at.isoformat() if form.updated_at else None,
                    'creator': creator_info,
                    'questions_count': len(form.form_questions),
                    'submissions_count': submissions_count
                }
                serialized_forms.append(form_dict)

            return serialized_forms

        except Exception as e:
            logger.error(f"Error formatting forms data: {str(e)}")
            raise

    @staticmethod
    def get_forms_by_user(user_id):
        """Get all forms created by a user"""
        return FormService.get_forms_by_user(user_id)

    @staticmethod
    def get_forms_by_user_or_public(user_id, is_public=None):
        """Get forms created by user or public forms"""
        return FormService.get_forms_by_user_or_public(user_id, is_public)

    @staticmethod
    def get_forms_by_creator(username: str) -> dict:
        """
        Get all forms created by a specific username with formatted response
        
        Args:
            username (str): Username of the creator
            
        Returns:
            dict: Dictionary containing list of serialized forms or None if user not found
        """
        try:
            forms = FormService.get_forms_by_creator(username)
            if forms is None:
                return None

            forms_data = []
            for form in forms:
                # Get submissions count
                submissions_count = FormService.get_form_submissions_count(form.id)

                # Format creator info
                creator_info = None
                if form.creator:
                    creator_info = {
                        'id': form.creator.id,
                        'username': form.creator.username,
                        'environment_id': form.creator.environment_id,
                        'environment_name': form.creator.environment.name if form.creator.environment else None
                    }

                # Create form dictionary
                form_dict = {
                    'id': form.id,
                    'title': form.title,
                    'description': form.description,
                    'is_public': form.is_public,
                    'created_at': form.created_at.isoformat() if form.created_at else None,
                    'updated_at': form.updated_at.isoformat() if form.updated_at else None,
                    'creator': creator_info,
                    'questions_count': len(form.form_questions),
                    'submissions_count': submissions_count
                }
                forms_data.append(form_dict)

            return {"forms": forms_data}

        except Exception as e:
            logger.error(f"Error formatting forms data: {str(e)}")
            raise

    @staticmethod
    def get_public_forms() -> dict:
        """
        Get all public forms with formatted response
        
        Returns:
            dict: Dictionary containing list of serialized public forms
        """
        try:
            forms = FormService.get_public_forms()
            forms_data = []
            
            for form in forms:
                # Get submissions count
                submissions_count = FormService.get_form_submissions_count(form.id)

                # Format creator info
                creator_info = None
                if form.creator:
                    creator_info = {
                        'id': form.creator.id,
                        'username': form.creator.username,
                        'environment_id': form.creator.environment_id,
                        'environment_name': form.creator.environment.name if form.creator.environment else None
                    }

                # Create form dictionary
                form_dict = {
                    'id': form.id,
                    'title': form.title,
                    'description': form.description,
                    'is_public': form.is_public,
                    'created_at': form.created_at.isoformat() if form.created_at else None,
                    'updated_at': form.updated_at.isoformat() if form.updated_at else None,
                    'creator': creator_info,
                    'questions_count': len(form.form_questions),
                    'submissions_count': submissions_count
                }
                forms_data.append(form_dict)

            return {"forms": forms_data}

        except Exception as e:
            logger.error(f"Error formatting public forms data: {str(e)}")
            raise
        

    @staticmethod
    def get_all_forms(is_public=None):
        """Get all forms with optional public filter"""
        return FormService.get_all_forms(is_public=is_public)

    @staticmethod
    def update_form(form_id: int, **kwargs) -> dict:
        """
        Update a form's details
        
        Args:
            form_id (int): ID of the form to update
            **kwargs: Fields to update (title, description, is_public)
                
        Returns:
            dict: Response containing updated form data or error
        """
        try:
            form, error = FormService.update_form(form_id, **kwargs)
            if error:
                return {"error": error}

            # Format creator info
            creator_info = None
            if form.creator:
                creator_info = {
                    'id': form.creator.id,
                    'username': form.creator.username,
                    'environment_id': form.creator.environment_id,
                    'environment_name': form.creator.environment.name if form.creator.environment else None
                }

            # Get submissions count
            submissions_count = FormService.get_form_submissions_count(form.id)

            # Create form dictionary
            return {
                "message": "Form updated successfully",
                "form": {
                    'id': form.id,
                    'title': form.title,
                    'description': form.description,
                    'is_public': form.is_public,
                    'created_at': form.created_at.isoformat() if form.created_at else None,
                    'updated_at': form.updated_at.isoformat() if form.updated_at else None,
                    'creator': creator_info,
                    'questions_count': len(form.form_questions),
                    'submissions_count': submissions_count
                }
            }

        except Exception as e:
            logger.error(f"Error formatting updated form data: {str(e)}")
            raise

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