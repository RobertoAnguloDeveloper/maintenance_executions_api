# app/views/endpoints_lister_views.py

from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required
from app.utils.permission_manager import PermissionManager, RoleType # Assuming RoleType.ADMIN is defined
from app.services.auth_service import AuthService # To get current user for role check if needed by PermissionManager
import logging
import inspect # To get docstrings

logger = logging.getLogger(__name__)

endpoints_lister_bp = Blueprint('endpoints_lister', __name__)

@endpoints_lister_bp.route('/all', methods=['GET'])
@jwt_required()
@PermissionManager.require_role(RoleType.ADMIN) # Restrict to Admin users
def list_all_endpoints():
    """
    Lists all registered URL rules in the application, including their
    HTTP methods, endpoint names, and descriptions (from docstrings).
    Accessible only by Admin users.
    """
    try:
        output = []
        # Exclude static and internal Flask endpoints if desired
        excluded_endpoints = {'static', '_debug_toolbar.*'} 

        for rule in current_app.url_map.iter_rules():
            # Check if the endpoint should be excluded
            if any(rule.endpoint.startswith(excluded) for excluded in excluded_endpoints if '*' not in excluded) or \
               any(rule.endpoint == excluded.replace('.*', '') for excluded in excluded_endpoints if '*' in excluded and rule.endpoint.startswith(excluded.split('.')[0])):
                # A more robust regex might be better for wildcard exclusions
                # For now, this handles simple cases like 'static' and '_debug_toolbar.endpoints'
                if rule.endpoint.startswith('_debug_toolbar'): # Basic wildcard handling
                    continue
                if rule.endpoint == 'static':
                    continue


            methods = ','.join(sorted(list(rule.methods)))
            
            # Get the view function and its docstring
            description = "No description available."
            if rule.endpoint in current_app.view_functions:
                view_func = current_app.view_functions[rule.endpoint]
                docstring = inspect.getdoc(view_func)
                if docstring:
                    description = docstring.strip().split('\n')[0] # First line of docstring

            # Get blueprint name if available
            blueprint_name = "N/A"
            if '.' in rule.endpoint:
                blueprint_name = rule.endpoint.split('.')[0]
                # Attempt to find the blueprint object to get its import name for more context
                # This part can be complex if blueprints are nested or registered in non-standard ways
                # For simplicity, we'll stick to the endpoint's prefix
                # Example: if rule.endpoint is 'user_bp.get_user', blueprint_name will be 'user_bp'

            endpoint_info = {
                'path': str(rule),
                'methods': methods,
                'endpoint_name': rule.endpoint,
                'blueprint': blueprint_name,
                'description': description
            }
            output.append(endpoint_info)
        
        # Sort by blueprint and then path for better readability
        output.sort(key=lambda x: (x['blueprint'], x['path']))

        return jsonify(endpoints=output), 200

    except Exception as e:
        logger.error(f"Error listing endpoints: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error while listing endpoints"}), 500

def register_endpoints_lister_blueprint(app):
    """
    Helper function to register this blueprint, though typically registration
    is handled in app/views/__init__.py.
    """
    app.register_blueprint(endpoints_lister_bp, url_prefix='/api/service-discovery')
    logger.info("Endpoints Lister blueprint registered at /api/service-discovery")

