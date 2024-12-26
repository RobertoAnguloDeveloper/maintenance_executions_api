from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.cmms_config_controller import CMMSConfigController
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger(__name__)

cmms_config_bp = Blueprint('cmms-configs', __name__)

@cmms_config_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_role(RoleType.ADMIN)
def create_config():
    """Create a new CMMS configuration file"""
    try:
        # First verify JWT and get identity
        current_user = get_jwt_identity()
        if not current_user:
            return jsonify({"error": "Invalid or expired token"}), 401

        # Validate request data
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        required_fields = ['filename', 'content']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        # Validate filename
        if not isinstance(data['filename'], str):
            return jsonify({"error": "Filename must be a string"}), 400

        if not data['filename'].endswith('.json'):
            return jsonify({"error": "Only JSON files are supported for this endpoint"}), 400

        # Create config file
        config, error = CMMSConfigController.create_config(
            filename=data['filename'],
            content=data['content'],  # Pass the content as is, controller will handle conversion
            current_user=current_user
        )
        
        if error:
            return jsonify({"error": error}), 400
            
        return jsonify({
            "message": "Configuration file created successfully",
            "config": config
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating config file: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@cmms_config_bp.route('/upload', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.FORMS)
def upload_config():
    """Upload a CMMS configuration file"""
    try:
        current_user = get_jwt_identity()
        
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
            
        file = request.files['file']
        if not file or not file.filename:
            return jsonify({"error": "No selected file"}), 400
            
        # Upload config file
        config, error = CMMSConfigController.upload_config(
            file=file,
            filename=file.filename,
            current_user=current_user
        )
        
        if error:
            return jsonify({"error": error}), 400
            
        return jsonify({
            "message": "Configuration file uploaded successfully",
            "config": config
        }), 201
        
    except Exception as e:
        logger.error(f"Error uploading config file: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@cmms_config_bp.route('/file/<path:filename>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def get_file(filename):
    """Get a file from the CMMS directory structure"""
    try:
        current_user = get_jwt_identity()
        if not current_user:
            return jsonify({"error": "Invalid or expired token"}), 401
            
        # Find the file
        file_info, error = CMMSConfigController.find_file(filename, current_user)
        if error:
            return jsonify({"error": error}), 404
            
        try:
            # Configure send_file for streaming large files
            return send_file(
                file_info['path'],
                mimetype=file_info['mime_type'],
                as_attachment=False,  # Changed to False to allow browser handling
                download_name=file_info['filename'],
                max_age=0,  # Disable caching
                conditional=True  # Enable conditional requests
            )
            
        except Exception as e:
            logger.error(f"Error sending file: {str(e)}")
            return jsonify({"error": "Error accessing file"}), 500
            
    except Exception as e:
        logger.error(f"Error getting file {filename}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@cmms_config_bp.route('/configs/<filename>', methods=['PUT'])
@jwt_required()
@PermissionManager.require_role(RoleType.ADMIN)  # Only admin can update config files
def update_config_file(filename):
    """Update a JSON configuration file"""
    try:
        current_user = get_jwt_identity()
        if not current_user:
            return jsonify({"error": "Invalid or expired token"}), 401

        # Validate request data
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        if not 'content' in data:
            return jsonify({"error": "Content is required"}), 400

        # Update config file
        config, error = CMMSConfigController.update_config(
            filename=filename,
            content=data['content'],
            current_user=current_user
        )
        
        if error:
            return jsonify({"error": error}), 400
            
        return jsonify({
            "message": "Configuration file updated successfully",
            "config": config
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating config file: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@cmms_config_bp.route('/<filename>/rename', methods=['PUT'])
@jwt_required()
@PermissionManager.require_permission(action="update", entity_type=EntityType.FORMS)
def rename_config(filename):
    """Rename a CMMS configuration JSON file"""
    try:
        current_user = get_jwt_identity()
        
        data = request.get_json()
        if not data or 'new_filename' not in data:
            return jsonify({"error": "New filename is required"}), 400
            
        result, error = CMMSConfigController.rename_config(
            old_filename=secure_filename(filename),
            new_filename=secure_filename(data['new_filename']),
            current_user=current_user
        )
        
        if error:
            return jsonify({"error": error}), 400
            
        return jsonify({
            "message": "Configuration file renamed successfully",
            "config": result
        }), 200
        
    except Exception as e:
        logger.error(f"Error renaming config file: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@cmms_config_bp.route('/<filename>', methods=['GET'])
@jwt_required()
def load_config(filename):
    """Load a CMMS configuration file"""
    try:
        current_user = get_jwt_identity()
        if not current_user:
            return jsonify({"error": "Invalid or expired token"}), 401

        # Get file
        config, error = CMMSConfigController.load_config(
            filename=filename,
            current_user=current_user
        )
        
        if error:
            return jsonify({"error": error}), 404
            
        # For files that need to be downloaded
        if isinstance(config.get('content'), bytes):
            return send_file(
                config['path'],
                mimetype=config['file_type'],
                as_attachment=True,
                download_name=filename
            )
            
        # For JSON and text files, return as JSON response
        return jsonify(config), 200
        
    except Exception as e:
        logger.error(f"Error loading config file: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@cmms_config_bp.route('/<filename>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.FORMS)
def delete_config(filename):
    """Delete a CMMS configuration file"""
    try:
        current_user = get_jwt_identity()
        
        success, error = CMMSConfigController.delete_config(
            filename=filename,
            current_user=current_user
        )
        
        if not success:
            return jsonify({"error": error}), 404
            
        return jsonify({
            "message": "Configuration file deleted successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting config file: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@cmms_config_bp.route('/check', methods=['GET'])
@jwt_required()
def check_config_file():
    """Check if configuration file exists in the configs folder."""
    try:
        exists, metadata = CMMSConfigController.check_config_file()
        
        response = {
            "exists": exists,
            "metadata": metadata
        }
        
        # Add helpful message based on existence
        if exists:
            response["message"] = "Configuration file found in configs folder"
        else:
            response["message"] = "Configuration file not found in configs folder"
            
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error checking config file: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500