from flask import Blueprint, render_template, redirect, url_for, request
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from app.services.auth_service import AuthService
from functools import wraps
import logging

logger = logging.getLogger(__name__)

frontend_bp = Blueprint('frontend', __name__, template_folder='templates')

def frontend_auth_required():
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            try:
                verify_jwt_in_request()
                current_user = get_jwt_identity()
                logger.info(f"Authenticated user accessing {request.path}: {current_user}")
                return fn(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Authentication failed for {request.path}: {str(e)}")
                return redirect(url_for('frontend.login'))
        return decorator
    return wrapper

@frontend_bp.route('/')
def index():
    logger.info("Accessing root path")
    return redirect(url_for('frontend.login'))

@frontend_bp.route('/login')
def login():
    logger.info("Accessing login page")
    # Check if user is already authenticated
    try:
        verify_jwt_in_request()
        logger.info("User already authenticated, redirecting to dashboard")
        return redirect(url_for('frontend.dashboard'))
    except Exception:
        logger.info("No valid authentication found, showing login page")
        return render_template('auth/login.html')

@frontend_bp.route('/dashboard')
def dashboard():
    try:
        # Get the token from the request header
        auth_header = request.headers.get('Authorization')
        logger.info(f"Dashboard access attempt. Auth header present: {bool(auth_header)}")
        
        if not auth_header:
            logger.warning("No Authorization header found")
            return redirect(url_for('frontend.login'))
        
        # Verify the token
        verify_jwt_in_request()
        current_user = get_jwt_identity()
        logger.info(f"Dashboard access granted for user: {current_user}")
        
        # Get user details
        user = AuthService.get_current_user(current_user)
        if not user:
            logger.error(f"User not found: {current_user}")
            return redirect(url_for('frontend.login'))
            
        return render_template('dashboard/index.html', user=user)
        
    except Exception as e:
        logger.error(f"Dashboard access error: {str(e)}")
        return redirect(url_for('frontend.login'))

@frontend_bp.route('/users')
@frontend_auth_required()
def users():
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        if not user.role.is_super_user:
            logger.warning(f"Unauthorized access attempt to users page by: {current_user}")
            return redirect(url_for('frontend.dashboard'))
        return render_template('users/index.html')
    except Exception as e:
        logger.error(f"Error accessing users page: {str(e)}")
        return redirect(url_for('frontend.login'))

@frontend_bp.route('/roles')
@frontend_auth_required()
def roles():
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        if not user.role.is_super_user:
            logger.warning(f"Unauthorized access attempt to roles page by: {current_user}")
            return redirect(url_for('frontend.dashboard'))
        return render_template('roles/index.html')
    except Exception as e:
        logger.error(f"Error accessing roles page: {str(e)}")
        return redirect(url_for('frontend.login'))

@frontend_bp.route('/forms')
@frontend_auth_required()
def forms():
    return render_template('forms/index.html')

@frontend_bp.route('/forms/create')
@frontend_auth_required()
def create_form():
    return render_template('forms/create.html')

@frontend_bp.route('/forms/<int:form_id>')
@frontend_auth_required()
def view_form(form_id):
    return render_template('forms/view.html', form_id=form_id)

@frontend_bp.route('/forms/<int:form_id>/edit')
@frontend_auth_required()
def edit_form(form_id):
    return render_template('forms/edit.html', form_id=form_id)

@frontend_bp.route('/submissions')
@frontend_auth_required()
def submissions():
    return render_template('submissions/index.html')

@frontend_bp.route('/submissions/<int:submission_id>')
@frontend_auth_required()
def view_submission(submission_id):
    return render_template('submissions/view.html', submission_id=submission_id)

@frontend_bp.route('/my-submissions')
@frontend_auth_required()
def my_submissions():
    return render_template('submissions/my_submissions.html')

@frontend_bp.route('/environments')
@frontend_auth_required()
def environments():
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        if not user.role.is_super_user:
            logger.warning(f"Unauthorized access attempt to environments page by: {current_user}")
            return redirect(url_for('frontend.dashboard'))
        return render_template('environments/index.html')
    except Exception as e:
        logger.error(f"Error accessing environments page: {str(e)}")
        return redirect(url_for('frontend.login'))

# Error handlers
@frontend_bp.errorhandler(404)
def page_not_found(e):
    logger.error(f"404 error: {str(e)}")
    return render_template('errors/404.html'), 404

@frontend_bp.errorhandler(500)
def internal_server_error(e):
    logger.error(f"500 error: {str(e)}")
    return render_template('errors/500.html'), 500

# Register the blueprint
def init_app(app):
    app.register_blueprint(frontend_bp)
    logger.info("Frontend blueprint registered")