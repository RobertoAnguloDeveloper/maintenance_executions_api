from asyncio.log import logger
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers import form_controller
from app.controllers.form_controller import FormController
from app.controllers.user_controller import UserController
from app.models.form import Form
from app.models.form_answer import FormAnswer
from app.models.form_question import FormQuestion
from app.models.form_submission import FormSubmission
from app.models.question import Question
from app.models.role import Role
from app.services.auth_service import AuthService
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from app import db
from app.utils.permission_manager import PermissionManager, EntityType, ActionType, RoleType
import logging

logger = logging.getLogger(__name__)
form_bp = Blueprint('forms', __name__)

@form_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def get_all_forms():
    """Get all forms with role-based filtering"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        is_public = request.args.get('is_public', type=bool)
        
        # Use RoleType constants instead of Role enum
        if user.role.name == RoleType.TECHNICIAN:
            # Technicians can only see public forms
            forms = FormController.get_public_forms()
        elif user.role.name in [RoleType.SUPERVISOR, RoleType.SITE_MANAGER]:
            # Supervisors and Site Managers see forms in their environment
            forms = FormController.get_forms_by_environment(user.environment_id)
        else:
            # Admins see all forms
            forms = FormController.get_all_forms(is_public=is_public)
        
        return jsonify([form.to_dict() for form in forms]), 200
        
    except Exception as e:
        logger.error(f"Error getting forms: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_bp.route('/<int:form_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def get_form(form_id):
    """Get a specific form with role-based access control"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        form = FormController.get_form(form_id)
        if not form:
            return jsonify({"error": "Form not found"}), 404

        # Role-based access control using RoleType
        if user.role.name == RoleType.TECHNICIAN:
            if not form.is_public:
                return jsonify({"error": "Unauthorized access"}), 403
        elif user.role.name in [RoleType.SUPERVISOR, RoleType.SITE_MANAGER]:
            if form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403

        return jsonify(form.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error getting form {form_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_bp.route('/creator/<string:username>', methods=['GET'])
@jwt_required()
@PermissionManager.require_role(RoleType.ADMIN)  # Only Admin can delete permissions
def get_forms_by_creator(username):
    """Get all forms created by a specific user"""
    current_user = get_jwt_identity()
    user = AuthService.get_current_user(current_user)
    
    # Users can only see their own forms unless they're admin
    if not user.role.is_super_user and current_user != username:
        return jsonify({"error": "Unauthorized access"}), 403

    forms = FormController.get_forms_by_creator(username)
    if forms is None:
        return jsonify({"error": "User not found"}), 404

    return jsonify([form.to_dict() for form in forms]), 200
    
@form_bp.route('/environment/<int:environment_id>', methods=['GET'])
@jwt_required()
def get_forms_by_environment(environment_id):
    """Get all forms associated with an environment"""
    print(f"Accessing forms for environment ID: {environment_id}")  # Debug log
    
    current_user = get_jwt_identity()
    user = AuthService.get_current_user(current_user)
    print(f"Current user: {user.username}, Environment: {user.environment_id}")  # Debug log

    # If user is not admin, they can only see forms from their environment
    if not user.role.is_super_user and user.environment_id != environment_id:
        print(f"Unauthorized access attempt by {user.username}")  # Debug log
        return jsonify({"error": "Unauthorized access"}), 403

    forms = FormController.get_forms_by_environment(environment_id)
    
    if forms is None:
        print(f"Environment {environment_id} not found")  # Debug log
        return jsonify({"error": "Environment not found"}), 404

    print(f"Found {len(forms)} forms for environment {environment_id}")  # Debug log
    return jsonify([{
        'id': form.id,
        'title': form.title,
        'description': form.description,
        'is_public': form.is_public,
        'created_at': form.created_at.isoformat() if form.created_at else None,
        'updated_at': form.updated_at.isoformat() if form.updated_at else None,
        'creator': {
            'id': form.creator.id,
            'username': form.creator.username,
            'environment_id': form.creator.environment.id,
            'environment_name': form.creator.environment.name
        } if form.creator else None,
        'questions_count': len(form.form_questions),
        'submissions_count': len(form.submissions)
    } for form in forms]), 200
    
@staticmethod
def get_forms_by_user_or_public(user_id, is_public=None):
    """Get forms created by user or public forms"""
    query = Form.query.filter(
        db.or_(
            Form.user_id == user_id,
            Form.is_public == True
        )
    ).options(
        joinedload(Form.creator),
        joinedload(Form.form_questions)
            .joinedload(FormQuestion.question)
            .joinedload(Question.question_type)
    )
    
    if is_public is not None:
        query = query.filter_by(is_public=is_public)
        
    return query.order_by(Form.created_at.desc()).all()
    
@form_bp.route('/public', methods=['GET'])
@jwt_required()
def get_public_forms():
    """Get all public forms"""
    forms = FormController.get_public_forms()
    return jsonify([form.to_dict() for form in forms]), 200

@form_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.FORMS)
def create_form():
    try:
        data = request.get_json()
        current_user = get_jwt_identity()
        logger.debug(f"Current user creating form: {current_user}")
        
        if not data.get('user_id'):
            user = AuthService.get_current_user(current_user)
            if not user:
                logger.error(f"User not found: {current_user}")
                return jsonify({"error": "User not found"}), 404
        else:
            user = UserController.get_user(data.get('user_id'))

        
        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = ['title']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        logger.debug(f"Creating form with data: {data}")

        try:
            new_form, error = FormController.create_form(
                title=data['title'],
                description=data.get('description'),
                user_id=user.id,
                is_public=data.get('is_public', False)
            )

            if error:
                logger.error(f"Error creating form: {error}")
                return jsonify({"error": error}), 400

            logger.info(f"Form created successfully by user {AuthService.get_current_user(current_user).username}")
            return jsonify({
                "message": "Form created successfully",
                "form": new_form.to_dict(),
                "form_creator": AuthService.get_current_user(current_user).username
            }), 201

        except Exception as e:
            logger.error(f"Database error while creating form: {str(e)}")
            return jsonify({"error": "Database error", "details": str(e)}), 500

    except Exception as e:
        logger.error(f"Error in create_form: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@form_bp.route('/<int:form_id>/questions', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="update", entity_type=EntityType.FORMS)
def add_questions_to_form(form_id):
    """Add new questions to an existing form"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Get the form
        form = FormController.get_form(form_id)
        if not form:
            return jsonify({"error": "Form not found"}), 404
            
        # Check environment access for non-admin roles
        if not user.role.is_super_user:
            if form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403

        data = request.get_json()
        if 'questions' not in data:
            return jsonify({"error": "Questions are required"}), 400

        updated_form, error = FormController.add_questions_to_form(
            form_id=form_id,
            questions=data['questions']
        )

        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Questions added to form {form_id} by user {user.username}")
        return jsonify({
            "message": "Questions added successfully",
            "form": updated_form.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error adding questions to form {form_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_bp.route('/<int:form_id>/submit', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.SUBMISSIONS)
def submit_form(form_id):
    """Submit a form with answers"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Get the form
        form = FormController.get_form(form_id)
        if not form:
            return jsonify({"error": "Form not found"}), 404
            
        # For technicians, check if form is public
        if user.role.name == RoleType.TECHNICIAN and not form.is_public:
            return jsonify({"error": "Unauthorized access to non-public form"}), 403
            
        # For other roles, check environment access
        if not user.role.is_super_user and user.role.name != RoleType.TECHNICIAN:
            if form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403

        data = request.get_json()
        if 'answers' not in data:
            return jsonify({"error": "Answers are required"}), 400

        submission, error = FormController.submit_form(
            form_id=form_id,
            username=current_user,
            answers=data['answers'],
            attachments=data.get('attachments')
        )

        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Form {form_id} submitted by user {user.username}")
        return jsonify({
            "message": "Form submitted successfully",
            "submission": submission.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error submitting form {form_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_bp.route('/<int:form_id>/submissions', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_form_submissions(form_id):
    """Get all submissions for a specific form"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Get the form
        form = FormController.get_form(form_id)
        if not form:
            return jsonify({"error": "Form not found"}), 404
            
        # For technicians, only show their own submissions
        if user.role.name == RoleType.TECHNICIAN:
            submissions = [s for s in form.submissions if s.submitted_by == current_user]
        # For other non-admin roles, check environment access
        elif not user.role.is_super_user:
            if form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403
            submissions = form.submissions
        # Admins can see all submissions
        else:
            submissions = form.submissions
            
        return jsonify([{
            'id': submission.id,
            'form_id': submission.form_id,
            'submitted_by': submission.submitted_by,
            'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
            'answers': [{
                'question': answer.form_answer.form_question.question.text,
                'answer': answer.form_answer.answer.value,
                'remarks': answer.form_answer.remarks
            } for answer in submission.answers_submitted],
            'attachments': [{
                'id': attachment.id,
                'file_type': attachment.file_type,
                'file_path': attachment.file_path,
                'is_signature': attachment.is_signature
            } for attachment in submission.attachments]
        } for submission in submissions]), 200

    except Exception as e:
        logger.error(f"Error getting submissions for form {form_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_bp.route('/<int:form_id>/statistics', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def get_form_statistics(form_id):
    """Get statistics for a specific form"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Get the form
        form = FormController.get_form(form_id)
        if not form:
            return jsonify({"error": "Form not found"}), 404
            
        # Technicians can't access statistics
        if user.role.name == RoleType.TECHNICIAN:
            return jsonify({"error": "Unauthorized access"}), 403
            
        # For other non-admin roles, check environment access
        if not user.role.is_super_user:
            if form.creator.environment_id != user.environment_id:
                return jsonify({"error": "Unauthorized access"}), 403

        stats = FormController.get_form_statistics(form_id)
        if not stats:
            return jsonify({"error": "Error generating statistics"}), 400

        return jsonify(stats), 200

    except Exception as e:
        logger.error(f"Error getting statistics for form {form_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_bp.route('/<int:form_id>', methods=['PUT'])
@jwt_required()
@PermissionManager.require_permission(action="update", entity_type=EntityType.FORMS)
def update_form(form_id):
    """Update a form with role-based access control"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Get the form
        form = FormController.get_form(form_id)
        if not form:
            return jsonify({"error": "Form not found"}), 404
            
        # Check environment access for non-admin roles
        if not user.role.is_super_user:
            if form.creator.environment_id != user.environment_id:
                return jsonify({
                    "error": "Unauthorized",
                    "message": "You can only update forms in your environment"
                }), 403

        # Get and validate update data
        data = request.get_json()
        allowed_fields = ['title', 'description', 'is_public']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        # Additional validation for public forms
        if 'is_public' in update_data:
            if user.role.name == Role.SUPERVISOR.value and update_data['is_public']:
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Supervisors cannot make forms public"
                }), 403

        # Special handling for admin-only operations
        if not user.role.is_super_user:
            # Prevent changing form ownership or environment
            restricted_fields = ['user_id', 'environment_id']
            if any(field in data for field in restricted_fields):
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Only administrators can change form ownership or environment"
                }), 403

        # Update the form
        updated_form, error = FormController.update_form(form_id, **update_data)
        
        if error:
            return jsonify({"error": error}), 400
            
        logger.info(f"Form {form_id} updated successfully by user {user.username}")
        return jsonify({
            "message": "Form updated successfully",
            "form": updated_form.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error updating form {form_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@form_bp.route('/<int:form_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.FORMS)
def delete_form(form_id):
    """Delete a form - restricted to Admin and Site Manager roles"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Get the form
        form = FormController.get_form(form_id)
        if not form:
            return jsonify({"error": "Form not found"}), 404

        # Check environment access for non-admin roles
        if not user.role.is_super_user:
            if form.creator.environment_id != user.environment_id:
                return jsonify({
                    "error": "Unauthorized",
                    "message": "You can only delete forms in your environment"
                }), 403

        # Additional validation for role-specific restrictions
        if user.role.name == Role.SUPERVISOR.value:
            # Check if the form has any submissions
            if form.submissions:
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Supervisors cannot delete forms with submissions"
                }), 403

        # Delete the form
        success, error = FormController.delete_form(form_id)
        if not success:
            return jsonify({"error": error}), 400

        logger.info(f"Form {form_id} deleted successfully by user {user.username}")
        return jsonify({
            "message": "Form deleted successfully"
        }), 200

    except Exception as e:
        logger.error(f"Error deleting form {form_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500