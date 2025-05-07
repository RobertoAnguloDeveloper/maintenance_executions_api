# app/controllers/report_template_controller.py

from flask import current_app
from app import db
from app.models import ReportTemplate, User
from app.services.auth_service import AuthService # Assuming AuthService can check roles/permissions if needed
from app.utils.permission_manager import RoleType # Import RoleType for permission checks
from typing import Dict, Any, Tuple, List, Optional
import logging

# Get the logger instance configured in app/__init__.py
logger = logging.getLogger("app")

class ReportTemplateController:
    """
    Controller for managing Report Templates.
    Handles CRUD operations and permission checks.
    """

    @staticmethod
    def create_template(data: Dict[str, Any], user: User) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        """
        Creates a new report template.

        Args:
            data (dict): Data for the new template (name, description, configuration, is_public).
            user (User): The user creating the template.

        Returns:
            Tuple[Optional[Dict[str, Any]], Optional[str], int]: (template_data, error_message, status_code)
        """
        logger.info(f"User '{user.username}' attempting to create report template.")
        name = data.get('name')
        configuration = data.get('configuration')
        description = data.get('description')
        is_public = data.get('is_public', False) # Default to False if not provided

        # --- Input Validation ---
        if not name or not isinstance(name, str) or not name.strip():
            logger.warning("Create template failed: Missing or invalid name.")
            return None, "Missing or invalid required field: name", 400
        if not configuration or not isinstance(configuration, dict):
            # Basic check for dict type. More specific validation of the configuration
            # structure itself might be needed depending on requirements.
            logger.warning("Create template failed: Missing or invalid configuration.")
            return None, "Missing or invalid required field: configuration (must be a JSON object)", 400
        if not isinstance(is_public, bool):
            logger.warning("Create template failed: Invalid is_public flag.")
            return None, "Invalid value for is_public (must be true or false)", 400
        if description is not None and not isinstance(description, str):
             logger.warning("Create template failed: Invalid description type.")
             return None, "Invalid value for description (must be a string)", 400


        try:
            # --- Create and Save Template ---
            new_template = ReportTemplate(
                name=name.strip(),
                description=description.strip() if description else None,
                user_id=user.id, # Associate with the current user
                configuration=configuration, # Store the JSON config
                is_public=is_public
            )
            db.session.add(new_template)
            db.session.commit()
            logger.info(f"Report template '{new_template.name}' (ID: {new_template.id}) created successfully by user '{user.username}'.")
            # Return the created template's data and 201 status
            return new_template.to_dict(), None, 201

        except Exception as e:
            db.session.rollback() # Rollback transaction on error
            logger.exception(f"Error creating report template for user '{user.username}': {e}")
            return None, f"An internal error occurred while creating the template.", 500 # Avoid exposing raw error details

    @staticmethod
    def list_templates(user: User) -> Tuple[List[Dict[str, Any]], Optional[str], int]:
        """
        Lists report templates accessible to the user (own templates + public templates).

        Args:
            user (User): The user requesting the list.

        Returns:
            Tuple[List[Dict[str, Any]], Optional[str], int]: (template_list, error_message, status_code)
        """
        logger.info(f"User '{user.username}' requesting list of report templates.")
        try:
            # Use the classmethod defined in the ReportTemplate model
            accessible_templates = ReportTemplate.find_for_user(user.id, include_public=True)
            # Use the basic dictionary representation for list views
            template_list = [template.to_dict_basic() for template in accessible_templates]
            logger.debug(f"Found {len(template_list)} templates accessible by user '{user.username}'.")
            return template_list, None, 200

        except Exception as e:
            logger.exception(f"Error listing report templates for user '{user.username}': {e}")
            return [], f"An internal error occurred while listing templates.", 500

    @staticmethod
    def get_template(template_id: int, user: User) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        """
        Retrieves a specific report template if it exists and is accessible by the user.

        Args:
            template_id (int): The ID of the template to retrieve.
            user (User): The user requesting the template.

        Returns:
            Tuple[Optional[Dict[str, Any]], Optional[str], int]: (template_data, error_message, status_code)
        """
        logger.info(f"User '{user.username}' requesting report template ID: {template_id}.")
        try:
            # Find non-deleted template by ID
            template = ReportTemplate.find_by_id(template_id)

            if not template:
                logger.warning(f"Template ID {template_id} not found for user '{user.username}'.")
                return None, "Report template not found", 404

            # --- Permission Check ---
            # User must own the template, OR the template must be public, OR the user must be an admin.
            is_owner = template.user_id == user.id
            is_admin = user.role and user.role.name == RoleType.ADMIN # Check if user is admin

            if not is_owner and not template.is_public and not is_admin:
                logger.warning(f"User '{user.username}' permission denied for template ID {template_id}.")
                return None, "Permission denied to access this report template", 403

            logger.debug(f"Template ID {template_id} retrieved successfully for user '{user.username}'.")
            # Return the full dictionary representation for a single item view
            return template.to_dict(), None, 200

        except Exception as e:
            logger.exception(f"Error retrieving template ID {template_id} for user '{user.username}': {e}")
            return None, f"An internal error occurred while retrieving the template.", 500

    @staticmethod
    def update_template(template_id: int, data: Dict[str, Any], user: User) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        """
        Updates an existing report template if the user has permission (owner or admin).

        Args:
            template_id (int): The ID of the template to update.
            data (dict): Data containing fields to update (name, description, configuration, is_public).
            user (User): The user attempting the update.

        Returns:
            Tuple[Optional[Dict[str, Any]], Optional[str], int]: (updated_template_data, error_message, status_code)
        """
        logger.info(f"User '{user.username}' attempting to update template ID: {template_id}.")
        try:
            template = ReportTemplate.find_by_id(template_id)

            if not template:
                logger.warning(f"Update failed: Template ID {template_id} not found for user '{user.username}'.")
                return None, "Report template not found", 404

            # --- Permission Check ---
            # Only the owner or an admin can update a template.
            is_owner = template.user_id == user.id
            is_admin = user.role and user.role.name == RoleType.ADMIN

            if not is_owner and not is_admin:
                logger.warning(f"User '{user.username}' permission denied for updating template ID {template_id}.")
                return None, "Permission denied to update this report template", 403

            # --- Update Fields ---
            updated = False # Flag to track if any changes were made
            if 'name' in data:
                if isinstance(data['name'], str) and data['name'].strip():
                    template.name = data['name'].strip()
                    updated = True
                else:
                    return None, "Invalid value for name", 400
            if 'description' in data: # Allow setting description to empty string or null
                if data['description'] is None or isinstance(data['description'], str):
                    template.description = str(data['description']).strip() if data['description'] else None
                    updated = True
                else:
                     return None, "Invalid value for description", 400
            if 'configuration' in data:
                if isinstance(data['configuration'], dict):
                    template.configuration = data['configuration']
                    updated = True
                else:
                    return None, "Invalid value for configuration (must be JSON object)", 400
            if 'is_public' in data:
                if isinstance(data['is_public'], bool):
                    # Optional: Add check if only admins can make templates public?
                    # if data['is_public'] and not is_admin:
                    #     return None, "Only administrators can make templates public", 403
                    template.is_public = data['is_public']
                    updated = True
                else:
                    return None, "Invalid value for is_public (must be true or false)", 400

            # If no valid fields were provided for update
            if not updated:
                 logger.warning(f"Update attempt for template ID {template_id} by '{user.username}' provided no valid fields.")
                 return None, "No valid fields provided for update", 400

            # Commit changes to the database
            db.session.commit()
            logger.info(f"Template ID {template_id} updated successfully by user '{user.username}'.")
            # Return the updated template data
            return template.to_dict(), None, 200

        except Exception as e:
            db.session.rollback() # Rollback transaction on error
            logger.exception(f"Error updating template ID {template_id} for user '{user.username}': {e}")
            return None, f"An internal error occurred while updating the template.", 500

    @staticmethod
    def delete_template(template_id: int, user: User) -> Tuple[Optional[str], int]:
        """
        Soft-deletes a report template if the user has permission (owner or admin).

        Args:
            template_id (int): The ID of the template to delete.
            user (User): The user attempting the deletion.

        Returns:
            Tuple[Optional[str], int]: (error_message, status_code)
        """
        logger.info(f"User '{user.username}' attempting to delete template ID: {template_id}.")
        try:
            template = ReportTemplate.find_by_id(template_id)

            if not template:
                logger.warning(f"Delete failed: Template ID {template_id} not found for user '{user.username}'.")
                return "Report template not found", 404

            # --- Permission Check ---
            # Only the owner or an admin can delete a template.
            is_owner = template.user_id == user.id
            is_admin = user.role and user.role.name == RoleType.ADMIN

            if not is_owner and not is_admin:
                logger.warning(f"User '{user.username}' permission denied for deleting template ID {template_id}.")
                return "Permission denied to delete this report template", 403

            # Perform soft delete using the mixin method
            template.soft_delete()
            db.session.commit()
            logger.info(f"Template ID {template_id} soft-deleted successfully by user '{user.username}'.")
            # Return success with no content
            return None, 204

        except Exception as e:
            db.session.rollback() # Rollback transaction on error
            logger.exception(f"Error deleting template ID {template_id} for user '{user.username}': {e}")
            return f"An internal error occurred while deleting the template.", 500
