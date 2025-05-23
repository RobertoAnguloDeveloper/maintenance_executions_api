# app/views/__init__.py

# Import existing blueprints
from .user_views import user_bp
from .role_views import role_bp
from .permission_views import permission_bp
from .environment_views import environment_bp
from .question_type_views import question_type_bp
from .question_views import question_bp
from .answer_views import answer_bp
from .form_views import form_bp
from .form_submission_views import form_submission_bp
from .answer_submitted_views import answer_submitted_bp
from .attachment_views import attachment_bp
from .role_permission_views import role_permission_bp
from .form_question_views import form_question_bp
from .form_answer_views import form_answer_bp
from .health_views import health_bp
from .export_views import export_bp
from .cmms_config_views import cmms_config_bp
from .export_submission_views import export_submission_bp
from .count_views import count_bp
from .entity_basic_views import entity_basic_bp
# Import the new report blueprint
from .report_views import report_bp
from .report_template_views import report_template_bp

from flask import jsonify

# Define the standalone ping function
def ping_standalone():
    """Simple ping endpoint at root level, will be registered as /api/ping"""
    return jsonify({"status": "pong", "message": "Server is running"}), 200

def register_blueprints(app):
    """Register all blueprints with the Flask application"""
    blueprints = [
        (user_bp, '/api/users'),
        (role_bp, '/api/roles'),
        (permission_bp, '/api/permissions'),
        (environment_bp, '/api/environments'),
        (question_type_bp, '/api/question-types'),
        (question_bp, '/api/questions'),
        (answer_bp, '/api/answers'),
        (form_bp, '/api/forms'),
        (form_submission_bp, '/api/form-submissions'),
        (answer_submitted_bp, '/api/answers-submitted'),
        (attachment_bp, '/api/attachments'),
        (role_permission_bp, '/api/role-permissions'),
        (form_question_bp, '/api/form-questions'),
        (form_answer_bp, '/api/form-answers'),
        (export_bp, '/api/export'),
        (health_bp, '/api/health'),
        (cmms_config_bp,'/api/cmms-configs'),
        (export_submission_bp, '/api/export_submissions'),
        (count_bp, '/api/counts'),
        (entity_basic_bp, '/api/entity_basic'),
        # Add the new report blueprint registration
        (report_bp, '/api/reports'),
        (report_template_bp, '/api/report-templates')
    ]

    # Iterate through the blueprints list and register each one
    for blueprint, url_prefix in blueprints:
        app.register_blueprint(blueprint, url_prefix=url_prefix)

    # Register a standalone ping endpoint at /api/ping
    app.route('/api/ping', methods=['GET'])(ping_standalone)