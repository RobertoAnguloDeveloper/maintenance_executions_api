from functools import wraps
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.services.auth_service import AuthService
from flask import jsonify

def roles_required(*required_roles):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            current_user = get_jwt_identity()
            user = AuthService.get_current_user(current_user)
            
            if not user:
                return jsonify({"error": "User not found"}), 404
                
            # Super admin can access everything
            if user.role.is_super_user:
                return fn(*args, **kwargs)
                
            # Check if user's role is in required roles
            if user.role.name not in required_roles:
                return jsonify({
                    "error": "Unauthorized access",
                    "message": f"Role {user.role.name} is not authorized to access this resource"
                }), 403
                
            return fn(*args, **kwargs)
        return decorator
    return wrapper