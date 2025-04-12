# app/views/count_views.py

from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.environment import Environment
from app.models.question_type import QuestionType
from app.models.question import Question
from app.models.answer import Answer
from app.models.form import Form
from app.models.form_submission import FormSubmission
from app.models.answer_submitted import AnswerSubmitted
from app.models.attachment import Attachment
from app.models.role_permission import RolePermission
from app.models.form_question import FormQuestion
from app.models.form_answer import FormAnswer
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging

logger = logging.getLogger(__name__)

count_bp = Blueprint('counts', __name__)

@count_bp.route('/users', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.USERS)
def count_users():
    """Get count of users"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Check if user has admin role
        include_deleted = False
        if user.role.is_super_user:
            # Only admins can see counts with deleted records
            include_deleted = request.args.get('include_deleted', '').lower() == 'true'
            
        # Base query
        query = User.query
        
        # Filter by environment for non-admin users
        if not user.role.is_super_user:
            query = query.filter_by(environment_id=user.environment_id)
            
        # Filter deleted records
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
            
        count = query.count()
        
        return jsonify({
            "entity": "users",
            "count": count,
            "include_deleted": include_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user count: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@count_bp.route('/roles', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ROLES)
def count_roles():
    """Get count of roles"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only admins can see counts with deleted records
        include_deleted = False
        if user.role.is_super_user:
            include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        
        # Base query
        query = Role.query
        
        # Filter deleted records
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
            
        # Filter super user roles for non-admin users
        if not user.role.is_super_user:
            query = query.filter_by(is_super_user=False)
            
        count = query.count()
        
        return jsonify({
            "entity": "roles",
            "count": count,
            "include_deleted": include_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting role count: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@count_bp.route('/permissions', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ROLES)
def count_permissions():
    """Get count of permissions"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only admins can see counts with deleted records
        include_deleted = False
        if user.role.is_super_user:
            include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        
        # Base query
        query = Permission.query
        
        # Filter deleted records
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
            
        count = query.count()
        
        return jsonify({
            "entity": "permissions",
            "count": count,
            "include_deleted": include_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting permission count: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@count_bp.route('/environments', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ENVIRONMENTS)
def count_environments():
    """Get count of environments"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only admins can see counts with deleted records
        include_deleted = False
        if user.role.is_super_user:
            include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        
        # Base query
        query = Environment.query
        
        # Filter deleted records
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
            
        # For non-admin users, only count their environment
        if not user.role.is_super_user:
            query = query.filter_by(id=user.environment_id)
            
        count = query.count()
        
        return jsonify({
            "entity": "environments",
            "count": count,
            "include_deleted": include_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting environment count: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@count_bp.route('/question-types', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.QUESTION_TYPES)
def count_question_types():
    """Get count of question types"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only admins can see counts with deleted records
        include_deleted = False
        if user.role.is_super_user:
            include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        
        # Base query
        query = QuestionType.query
        
        # Filter deleted records
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
            
        count = query.count()
        
        return jsonify({
            "entity": "question_types",
            "count": count,
            "include_deleted": include_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting question type count: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@count_bp.route('/questions', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.QUESTIONS)
def count_questions():
    """Get count of questions"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only admins can see counts with deleted records
        include_deleted = False
        if user.role.is_super_user:
            include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        
        # Base query
        query = Question.query
        
        # Filter deleted records
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
            
        count = query.count()
        
        return jsonify({
            "entity": "questions",
            "count": count,
            "include_deleted": include_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting question count: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@count_bp.route('/answers', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ANSWERS)
def count_answers():
    """Get count of answers"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only admins can see counts with deleted records
        include_deleted = False
        if user.role.is_super_user:
            include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        
        # Base query
        query = Answer.query
        
        # Filter deleted records
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
            
        count = query.count()
        
        return jsonify({
            "entity": "answers",
            "count": count,
            "include_deleted": include_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting answer count: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@count_bp.route('/forms', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def count_forms():
    """Get count of forms"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only admins can see counts with deleted records
        include_deleted = False
        if user.role.is_super_user:
            include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        
        # Base query
        query = Form.query
        
        # Filter deleted records
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
            
        # For non-admin users, filter by environment or public forms
        if not user.role.is_super_user:
            query = query.filter(
                (Form.is_public == True) | 
                (Form.created_by.has(User.environment_id == user.environment_id))
            )
            
        count = query.count()
        
        return jsonify({
            "entity": "forms",
            "count": count,
            "include_deleted": include_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting form count: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@count_bp.route('/form-submissions', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def count_form_submissions():
    """Get count of form submissions"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only admins can see counts with deleted records
        include_deleted = False
        if user.role.is_super_user:
            include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        
        # Base query
        query = FormSubmission.query
        
        # Filter deleted records
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
            
        # For technicians, only show their own submissions
        if user.role.name == RoleType.TECHNICIAN:
            query = query.filter_by(submitted_by=current_user)
        # For site managers and supervisors, show all submissions in their environment
        elif not user.role.is_super_user:
            query = query.join(Form).join(User, Form.created_by).filter(User.environment_id == user.environment_id)
            
        count = query.count()
        
        return jsonify({
            "entity": "form_submissions",
            "count": count,
            "include_deleted": include_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting form submission count: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@count_bp.route('/answers-submitted', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def count_answers_submitted():
    """Get count of submitted answers"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only admins can see counts with deleted records
        include_deleted = False
        if user.role.is_super_user:
            include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        
        # Base query
        query = AnswerSubmitted.query
        
        # Filter deleted records
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
            
        # For technicians, only show their own submitted answers
        if user.role.name == RoleType.TECHNICIAN:
            query = query.join(FormSubmission).filter(FormSubmission.submitted_by == current_user)
        # For site managers and supervisors, show all submissions in their environment
        elif not user.role.is_super_user:
            query = query.join(FormSubmission).join(Form).join(User, Form.created_by).filter(User.environment_id == user.environment_id)
            
        count = query.count()
        
        return jsonify({
            "entity": "answers_submitted",
            "count": count,
            "include_deleted": include_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting submitted answers count: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@count_bp.route('/attachments', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ATTACHMENTS)
def count_attachments():
    """Get count of attachments"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only admins can see counts with deleted records
        include_deleted = False
        if user.role.is_super_user:
            include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        
        # Base query
        query = Attachment.query
        
        # Filter deleted records
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
            
        # For technicians, only show their own attachments
        if user.role.name == RoleType.TECHNICIAN:
            query = query.join(FormSubmission).filter(FormSubmission.submitted_by == current_user)
        # For site managers and supervisors, show all attachments in their environment
        elif not user.role.is_super_user:
            query = query.join(FormSubmission).join(Form).join(User, Form.created_by).filter(User.environment_id == user.environment_id)
            
        count = query.count()
        
        return jsonify({
            "entity": "attachments",
            "count": count,
            "include_deleted": include_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting attachment count: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@count_bp.route('/role-permissions', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ROLES)
def count_role_permissions():
    """Get count of role permissions"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only admins can see counts with deleted records
        include_deleted = False
        if user.role.is_super_user:
            include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        
        # Base query
        query = RolePermission.query
        
        # Filter deleted records
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
            
        # Filter super user roles for non-admin users
        if not user.role.is_super_user:
            query = query.join(Role).filter(Role.is_super_user == False)
            
        count = query.count()
        
        return jsonify({
            "entity": "role_permissions",
            "count": count,
            "include_deleted": include_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting role permission count: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@count_bp.route('/form-questions', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def count_form_questions():
    """Get count of form questions"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only admins can see counts with deleted records
        include_deleted = False
        if user.role.is_super_user:
            include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        
        # Base query
        query = FormQuestion.query
        
        # Filter deleted records
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
            
        # For non-admin users, filter by environment or public forms
        if not user.role.is_super_user:
            query = query.join(Form).filter(
                (Form.is_public == True) | 
                (Form.created_by.has(User.environment_id == user.environment_id))
            )
            
        count = query.count()
        
        return jsonify({
            "entity": "form_questions",
            "count": count,
            "include_deleted": include_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting form question count: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@count_bp.route('/form-answers', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def count_form_answers():
    """Get count of form answers"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only admins can see counts with deleted records
        include_deleted = False
        if user.role.is_super_user:
            include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        
        # Base query
        query = FormAnswer.query
        
        # Filter deleted records
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
            
        # For non-admin users, filter by environment or public forms
        if not user.role.is_super_user:
            query = query.join(FormQuestion).join(Form).filter(
                (Form.is_public == True) | 
                (Form.created_by.has(User.environment_id == user.environment_id))
            )
            
        count = query.count()
        
        return jsonify({
            "entity": "form_answers",
            "count": count,
            "include_deleted": include_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting form answer count: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

# Aggregate counts for all entities
@count_bp.route('', methods=['GET'])
@jwt_required()
def count_all_entities():
    """Get counts for all entities based on user permissions"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only admins can see counts with deleted records
        include_deleted = False
        if user.role.is_super_user:
            include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        
        # Initialize the response dictionary with all entities
        counts = {
            "users": 0,
            "roles": 0,
            "permissions": 0,
            "environments": 0,
            "question_types": 0,
            "questions": 0,
            "answers": 0,
            "forms": 0,
            "form_submissions": 0,
            "answers_submitted": 0,
            "attachments": 0,
            "role_permissions": 0,
            "form_questions": 0,
            "form_answers": 0
        }
        
        # Users count
        if PermissionManager.has_permission(user, "view", EntityType.USERS):
            query = User.query
            if not include_deleted:
                query = query.filter_by(is_deleted=False)
            if not user.role.is_super_user:
                query = query.filter_by(environment_id=user.environment_id)
            counts["users"] = query.count()
        
        # Roles count
        if PermissionManager.has_permission(user, "view", EntityType.ROLES):
            query = Role.query
            if not include_deleted:
                query = query.filter_by(is_deleted=False)
            if not user.role.is_super_user:
                query = query.filter_by(is_super_user=False)
            counts["roles"] = query.count()
        
        # Permissions count
        if PermissionManager.has_permission(user, "view", EntityType.ROLES):
            query = Permission.query
            if not include_deleted:
                query = query.filter_by(is_deleted=False)
            counts["permissions"] = query.count()
        
        # Environments count
        if PermissionManager.has_permission(user, "view", EntityType.ENVIRONMENTS):
            query = Environment.query
            if not include_deleted:
                query = query.filter_by(is_deleted=False)
            if not user.role.is_super_user:
                query = query.filter_by(id=user.environment_id)
            counts["environments"] = query.count()
        
        # Question Types count
        if PermissionManager.has_permission(user, "view", EntityType.QUESTION_TYPES):
            query = QuestionType.query
            if not include_deleted:
                query = query.filter_by(is_deleted=False)
            counts["question_types"] = query.count()
        
        # Questions count
        if PermissionManager.has_permission(user, "view", EntityType.QUESTIONS):
            query = Question.query
            if not include_deleted:
                query = query.filter_by(is_deleted=False)
            counts["questions"] = query.count()
        
        # Answers count
        if PermissionManager.has_permission(user, "view", EntityType.ANSWERS):
            query = Answer.query
            if not include_deleted:
                query = query.filter_by(is_deleted=False)
            counts["answers"] = query.count()
        
        # Forms count
        if PermissionManager.has_permission(user, "view", EntityType.FORMS):
            query = Form.query
            if not include_deleted:
                query = query.filter_by(is_deleted=False)
            if not user.role.is_super_user:
                query = query.filter(
                    (Form.is_public == True) | 
                    (Form.created_by.has(User.environment_id == user.environment_id))
                )
            counts["forms"] = query.count()
        
        # Form Submissions count
        if PermissionManager.has_permission(user, "view", EntityType.SUBMISSIONS):
            query = FormSubmission.query
            if not include_deleted:
                query = query.filter_by(is_deleted=False)
            if user.role.name == RoleType.TECHNICIAN:
                query = query.filter_by(submitted_by=current_user)
            elif not user.role.is_super_user:
                query = query.join(Form).join(User, Form.created_by).filter(User.environment_id == user.environment_id)
            counts["form_submissions"] = query.count()
        
        # Answers Submitted count
        if PermissionManager.has_permission(user, "view", EntityType.SUBMISSIONS):
            query = AnswerSubmitted.query
            if not include_deleted:
                query = query.filter_by(is_deleted=False)
            if user.role.name == RoleType.TECHNICIAN:
                query = query.join(FormSubmission).filter(FormSubmission.submitted_by == current_user)
            elif not user.role.is_super_user:
                query = query.join(FormSubmission).join(Form).join(User, Form.created_by).filter(User.environment_id == user.environment_id)
            counts["answers_submitted"] = query.count()
        
        # Attachments count
        if PermissionManager.has_permission(user, "view", EntityType.ATTACHMENTS):
            query = Attachment.query
            if not include_deleted:
                query = query.filter_by(is_deleted=False)
            if user.role.name == RoleType.TECHNICIAN:
                query = query.join(FormSubmission).filter(FormSubmission.submitted_by == current_user)
            elif not user.role.is_super_user:
                query = query.join(FormSubmission).join(Form).join(User, Form.created_by).filter(User.environment_id == user.environment_id)
            counts["attachments"] = query.count()
        
        # Role Permissions count
        if PermissionManager.has_permission(user, "view", EntityType.ROLES):
            query = RolePermission.query
            if not include_deleted:
                query = query.filter_by(is_deleted=False)
            if not user.role.is_super_user:
                query = query.join(Role).filter(Role.is_super_user == False)
            counts["role_permissions"] = query.count()
        
        # Form Questions count
        if PermissionManager.has_permission(user, "view", EntityType.FORMS):
            query = FormQuestion.query
            if not include_deleted:
                query = query.filter_by(is_deleted=False)
            if not user.role.is_super_user:
                query = query.join(Form).filter(
                    (Form.is_public == True) | 
                    (Form.created_by.has(User.environment_id == user.environment_id))
                )
            counts["form_questions"] = query.count()
        
        # Form Answers count
        if PermissionManager.has_permission(user, "view", EntityType.FORMS):
            query = FormAnswer.query
            if not include_deleted:
                query = query.filter_by(is_deleted=False)
            if not user.role.is_super_user:
                query = query.join(FormQuestion).join(Form).filter(
                    (Form.is_public == True) | 
                    (Form.created_by.has(User.environment_id == user.environment_id))
                )
            counts["form_answers"] = query.count()
        
        # Return the simple flat object structure as requested
        return jsonify(counts), 200
        
    except Exception as e:
        logger.error(f"Error getting aggregated counts: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500