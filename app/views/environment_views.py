from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.environment_controller import EnvironmentController
from app.services.auth_service import AuthService
from app.utils.permission_manager import ActionType, PermissionManager, EntityType, RoleType
import logging

logger = logging.getLogger(__name__)

environment_bp = Blueprint('environments', __name__)

@environment_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_role(RoleType.ADMIN)  # Only Admin can create environments
def create_environment():
    """Create a new environment - Admin only"""
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description')

        if not name:
            return jsonify({"error": "Name is required"}), 400

        new_environment, error = EnvironmentController.create_environment(name, description)
        if error:
            return jsonify({"error": error}), 400

        logger.info(f"Environment '{name}' created successfully")
        return jsonify({
            "message": "Environment created successfully",
            "environment": new_environment.to_dict()
        }), 201
    except Exception as e:
        logger.error(f"Error creating environment: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@environment_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action=ActionType.VIEW, entity_type=EntityType.ENVIRONMENTS)
def get_all_environments():
    """Get all environments with role-based filtering"""
    try:
        current_user = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user)
        
        if not current_user_obj:
            return jsonify({"error": "User not found"}), 404

        # Only admins can see deleted environments
        include_deleted = (current_user_obj.role.is_super_user and 
                         request.args.get('include_deleted', '').lower() == 'true')

        try:
            environments = EnvironmentController.get_all_environments(include_deleted=include_deleted)

            return jsonify([
                env.to_dict(
                    include_deleted=current_user_obj.role.is_super_user
                ) for env in environments if env
            ]), 200

        except Exception as e:
            logger.error(f"Database error while fetching environments: {str(e)}")
            return jsonify({"error": f"Database error: {str(e)}"}), 500

    except Exception as e:
        logger.error(f"Error in get_all_environments: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@environment_bp.route('/batch', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ENVIRONMENTS)
def get_batch_environments():
    """Get batch of environments with pagination"""
    try:
        # Get pagination parameters
        page = request.args.get('page', type=int, default=1)
        per_page = request.args.get('per_page', type=int, default=50)
        
        # Get filter parameters
        include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        
        # Apply role-based access control
        current_user = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user)
        
        # Call controller method with pagination
        total_count, environments = EnvironmentController.get_batch(
            page=page,
            per_page=per_page,
            include_deleted=include_deleted,
            current_user=current_user_obj
        )
        
        # Calculate total pages
        total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 0
        
        return jsonify({
            "metadata": {
                "total_items": total_count,
                "total_pages": total_pages,
                "current_page": page,
                "per_page": per_page,
            },
            "items": environments
        }), 200

    except Exception as e:
        logger.error(f"Error getting batch of environments: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

@environment_bp.route('/<int:environment_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ENVIRONMENTS)
def get_environment(environment_id):
    """Get a specific environment"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Check environment access
        if not user.role.is_super_user and user.environment_id != environment_id:
            return jsonify({"error": "Unauthorized access"}), 403

        environment = EnvironmentController.get_environment(environment_id)
        if environment:
            return jsonify(environment.to_dict()), 200
        return jsonify({"error": "Environment not found"}), 404
    except Exception as e:
        logger.error(f"Error getting environment {environment_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@environment_bp.route('/name/<string:name>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.ENVIRONMENTS)
def get_environment_by_name(name):
    """Get environment by name"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        environment = EnvironmentController.get_environment_by_name(name)
        if not environment:
            return jsonify({"error": "Environment not found"}), 404

        # Check environment access
        if not user.role.is_super_user and user.environment_id != environment.id:
            return jsonify({"error": "Unauthorized access"}), 403

        return jsonify(environment.to_dict()), 200
    except Exception as e:
        logger.error(f"Error getting environment by name '{name}': {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@environment_bp.route('/<int:environment_id>', methods=['PUT'])
@jwt_required()
@PermissionManager.require_role(RoleType.ADMIN)  # Only Admin can update environments
def update_environment(environment_id):
    """Update an environment - Admin only"""
    try:
        data = request.get_json()
        
        updated_environment, error = EnvironmentController.update_environment(environment_id, **data)
        if error:
            return jsonify({"error": error}), 400
        
        if updated_environment:
            logger.info(f"Environment {environment_id} updated successfully")
            return jsonify({
                "message": "Environment updated successfully", 
                "environment": updated_environment.to_dict()
            }), 200
        return jsonify({"error": "Environment not found"}), 404
    except Exception as e:
        logger.error(f"Error updating environment {environment_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@environment_bp.route('/<int:environment_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_role(RoleType.ADMIN)
def delete_environment(environment_id):
    """Delete an environment with cascade soft delete - Admin only"""
    try:
        current_user = get_jwt_identity()
        
        # Get the environment checking is_deleted=False
        environment = EnvironmentController.get_environment(environment_id)
        if not environment:
            return jsonify({"error": "Environment not found"}), 404

        # Prevent deletion of ADMIN environment
        if environment.name == "ADMIN":
            return jsonify({
                "error": "Cannot delete the ADMIN environment"
            }), 403

        success, error = EnvironmentController.delete_environment(environment_id)
        if success:
            logger.info(f"Environment {environment_id} and all associated data deleted by {current_user}")
            return jsonify({"message": "Environment and all associated data deleted successfully"}), 200
            
        return jsonify({"error": error}), 400
        
    except Exception as e:
        logger.error(f"Error deleting environment {environment_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@environment_bp.route('/<int:environment_id>/users', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.USERS)
def get_users_in_environment(environment_id):
    """Get users in an environment"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Check environment access
        if not user.role.is_super_user and user.environment_id != environment_id:
            return jsonify({"error": "Unauthorized access"}), 403

        users = EnvironmentController.get_users_in_environment(environment_id)
        
        if not users:
            if not EnvironmentController.get_environment(environment_id):
                return jsonify({"error": "Environment not found"}), 404
        
        if len(users) == 0:
            
            return jsonify({
                "environment_name": EnvironmentController.get_environment(environment_id).name,
                "users_count": len(users)
                }),200
        
        return jsonify([user.to_dict() for user in users]), 200
    
    except Exception as e:
        logger.error(f"Error getting users in environment {environment_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@environment_bp.route('/<int:environment_id>/forms', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def get_forms_in_environment(environment_id):
    """Get forms in an environment"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Check environment access
        if not user.role.is_super_user and user.environment_id != environment_id:
            return jsonify({"error": "Unauthorized access"}), 403

        forms = EnvironmentController.get_forms_in_environment(environment_id)
        return jsonify([form.to_dict() for form in forms]), 200
    except Exception as e:
        logger.error(f"Error getting forms in environment {environment_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500