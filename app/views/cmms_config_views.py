# app/views/cmms_config_views.py

from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.cmms_config_controller import CMMSConfigController
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType
import logging
from werkzeug.utils import secure_filename
import os

logger = logging.getLogger(__name__)

cmms_config_bp = Blueprint('cmms-configs', __name__)

@cmms_config_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.FORMS)
def create_config():
    """Create a new CMMS configuration JSON file"""
    try:
        current_user = get_jwt_identity()
        
        # Validate request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        required_fields = ['filename', 'content']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
            
        # Create config file
        config, error = CMMSConfigController.create_config(
            filename=data['filename'],
            content=data['content'],
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
    """Upload a CMMS configuration JSON file"""
    try:
        current_user = get_jwt_identity()
        
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
            
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({"error": "No selected file"}), 400
            
        # Upload config file
        config, error = CMMSConfigController.upload_config(
            file=file,
            filename=secure_filename(file.filename),
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

@cmms_config_bp.route('/<filename>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.FORMS)
def load_config(filename):
    """Load a CMMS configuration JSON file"""
    try:
        current_user = get_jwt_identity()
        
        config, error = CMMSConfigController.load_config(
            filename=secure_filename(filename),
            current_user=current_user
        )
        
        if error:
            return jsonify({"error": error}), 404
            
        return jsonify(config), 200
        
    except Exception as e:
        logger.error(f"Error loading config file: {str(e)}")
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

@cmms_config_bp.route('/<filename>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.FORMS)
def delete_config(filename):
    """Delete a CMMS configuration JSON file"""
    try:
        current_user = get_jwt_identity()
        
        success, error = CMMSConfigController.delete_config(
            filename=secure_filename(filename),
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