# app/views/health_views.py

from flask import Blueprint, jsonify
from app.controllers.health_controller import HealthController
import logging

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)

@health_bp.route('/ping', methods=['GET'])
def ping():
    """Simple ping endpoint to check if the server is responsive"""
    try:
        result = HealthController.ping()
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error in ping endpoint: {str(e)}")
        return jsonify({"status": "error", "message": "Server error"}), 500

@health_bp.route('/status', methods=['GET'])
def health_status():
    """Get detailed health status of the server"""
    try:
        result = HealthController.get_health_status()
        
        # Determine HTTP status code based on health status
        status_code = 200
        if result.get('health_status') == 'degraded':
            status_code = 200  # Still return 200 but with degraded status
        elif result.get('health_status') == 'unhealthy':
            status_code = 503  # Service Unavailable
            
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"Error in health status endpoint: {str(e)}")
        return jsonify({"status": "error", "message": "Server error"}), 500