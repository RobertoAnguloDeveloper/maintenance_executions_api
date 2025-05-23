# app/views/entity_basic_views.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.entity_basic_controller import EntityBasicController
from app.services.auth_service import AuthService
from app.utils.permission_manager import EntityType, PermissionManager, RoleType
import logging

logger = logging.getLogger(__name__)

# Create Blueprint for entity basic views
entity_basic_bp = Blueprint('entity_basic', __name__)

@entity_basic_bp.route('/basic', methods=['GET'])
@jwt_required()
def get_all_entities_basic():
    """
    Get basic representations of all entities
    
    Query parameters:
        include_deleted (bool): Whether to include soft-deleted entities (default: False)
        page (int): Page number for pagination (default: 1)
        per_page (int): Number of items per page (default: 20)
        
    Returns:
        JSON response with entity data and pagination information
    """
    try:
        # Get current user for role-based access control
        current_user = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user)
        if not current_user_obj:
            return jsonify({"error": "User not found"}), 404
            
        # Only admin users can access this endpoint
        if not current_user_obj.role.is_super_user:
            return jsonify({"error": "Unauthorized. Admin access required."}), 403
        
        # Only admins can see deleted entities
        include_deleted = request.args.get('include_deleted', '').lower() == 'true'
                         
        # Get pagination parameters with defaults
        try:
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 20))
            
        except ValueError:
            return jsonify({"error": "Invalid pagination parameters"}), 400
        
        # Call controller
        result, status_code = EntityBasicController.get_all_entities_basic(
            include_deleted=include_deleted,
            page=page,
            per_page=per_page
        )
        
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Error in get_all_entities_basic view: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@entity_basic_bp.route('/<entity_type>/basic', methods=['GET'])
@jwt_required()
def get_entity_basic(entity_type):
    """
    Get basic representations of a specific entity type
    
    Path parameters:
        entity_type (str): Type of entity to retrieve (e.g., 'users', 'forms')
        
    Query parameters:
        include_deleted (bool): Whether to include soft-deleted entities (default: False)
        page (int): Page number for pagination (default: 1)
        per_page (int): Number of items per page (default: 20)
        
    Returns:
        JSON response with entity data and pagination information
    """
    try:
        # Get current user for role-based access control
        current_user = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user)
        if not current_user_obj:
            return jsonify({"error": "User not found"}), 404
            
        # Check if entity type is valid
        try:
            entity_enum = next((e for e in EntityType if e.value == entity_type), None)
            if entity_enum and not current_user_obj.role.is_super_user:
                # Check permission for this specific entity type
                if not PermissionManager.has_permission(current_user_obj, "view", entity_enum):
                    return jsonify({"error": f"Unauthorized to view {entity_type}"}), 403
        except Exception as e:
            logger.warning(f"Entity type {entity_type} not found in EntityType enum: {str(e)}")
            # If entity type is not in enum, only admin can access
            if not current_user_obj.role.is_super_user:
                return jsonify({"error": "Unauthorized access"}), 403
        
        # Only admins can see deleted entities
        include_deleted = (current_user_obj.role.is_super_user and 
                         request.args.get('include_deleted', '').lower() == 'true')
        
        # Get pagination parameters with defaults
        try:
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 20))
            
            # Maximum per_page value to prevent performance issues
            if per_page > 100:
                per_page = 100
        except ValueError:
            return jsonify({"error": "Invalid pagination parameters"}), 400
        
        # Apply role-based restrictions for certain entity types
        if entity_type == 'users' and not current_user_obj.role.is_super_user:
            # Non-admin users can only see users in their environment
            # This would need custom handling in the service layer
            # For now, we'll continue with the standard approach
            pass
        
        # Call controller
        result, status_code = EntityBasicController.get_entity_basic(
            entity_type=entity_type,
            include_deleted=include_deleted,
            page=page,
            per_page=per_page
        )
        
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Error in get_entity_basic view: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@entity_basic_bp.route('/<entity_type>/<int:entity_id>/basic', methods=['GET'])
@jwt_required()
def get_entity_by_id_basic(entity_type, entity_id):
    """
    Get basic representation of a specific entity by ID
    
    Path parameters:
        entity_type (str): Type of entity to retrieve (e.g., 'users', 'forms')
        entity_id (int): ID of the entity to retrieve
        
    Query parameters:
        include_deleted (bool): Whether to include soft-deleted entities (default: False)
        
    Returns:
        JSON response with entity data
    """
    try:
        # Get current user for role-based access control
        current_user = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user)
        if not current_user_obj:
            return jsonify({"error": "User not found"}), 404
            
        # Check if entity type is valid
        try:
            entity_enum = next((e for e in EntityType if e.value == entity_type), None)
            if entity_enum and not current_user_obj.role.is_super_user:
                # Check permission for this specific entity type
                if not PermissionManager.has_permission(current_user_obj, "view", entity_enum):
                    return jsonify({"error": f"Unauthorized to view {entity_type}"}), 403
        except Exception as e:
            logger.warning(f"Entity type {entity_type} not found in EntityType enum: {str(e)}")
            # If entity type is not in enum, only admin can access
            if not current_user_obj.role.is_super_user:
                return jsonify({"error": "Unauthorized access"}), 403
        
        # Only admins can see deleted entities
        include_deleted = (current_user_obj.role.is_super_user and 
                         request.args.get('include_deleted', '').lower() == 'true')
        
        # Call controller
        result, status_code = EntityBasicController.get_entity_by_id_basic(
            entity_type=entity_type,
            entity_id=entity_id,
            include_deleted=include_deleted
        )
        
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Error in get_entity_by_id_basic view: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@entity_basic_bp.route('/<entity_type>/basic/batch', methods=['POST'])
@jwt_required()
def get_entities_by_ids_basic(entity_type):
    """
    Get basic representations of multiple entities by their IDs
    
    Path parameters:
        entity_type (str): Type of entity to retrieve
        
    Request body:
        {
            "ids": [1, 2, 3, ...]  # List of entity IDs to retrieve
        }
        
    Query parameters:
        include_deleted (bool): Whether to include soft-deleted entities (default: False)
        
    Returns:
        JSON response with entities data
    """
    try:
        # Get current user for role-based access control
        current_user = get_jwt_identity()
        current_user_obj = AuthService.get_current_user(current_user)
        if not current_user_obj:
            return jsonify({"error": "User not found"}), 404
            
        # Check if entity type is valid
        try:
            entity_enum = next((e for e in EntityType if e.value == entity_type), None)
            if entity_enum and not current_user_obj.role.is_super_user:
                # Check permission for this specific entity type
                if not PermissionManager.has_permission(current_user_obj, "view", entity_enum):
                    return jsonify({"error": f"Unauthorized to view {entity_type}"}), 403
        except Exception as e:
            logger.warning(f"Entity type {entity_type} not found in EntityType enum: {str(e)}")
            # If entity type is not in enum, only admin can access
            if not current_user_obj.role.is_super_user:
                return jsonify({"error": "Unauthorized access"}), 403
        
        # Parse request data
        data = request.get_json()
        if not data or 'ids' not in data or not isinstance(data['ids'], list):
            return jsonify({"error": "Invalid request format. Expected 'ids' list in JSON body"}), 400
            
        entity_ids = data['ids']
        
        # Only admins can see deleted entities
        include_deleted = (current_user_obj.role.is_super_user and 
                         request.args.get('include_deleted', '').lower() == 'true')
        
        # Call controller
        result, status_code = EntityBasicController.get_entities_by_ids_basic(
            entity_type=entity_type,
            entity_ids=entity_ids,
            include_deleted=include_deleted
        )
        
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Error in get_entities_by_ids_basic view: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500