from .user_views import user_bp
from .role_views import role_bp
from .permission_views import permission_bp
from .environment_views import environment_bp
from .question_type_views import question_type_bp
from .question_views import question_bp
from .answer_views import answer_bp
from .form_views import form_bp
from .form_submission_views import form_submission_bp
from .attachment_views import attachment_bp

def register_blueprints(app):
    """Register all blueprints with the app"""
    blueprints = [
        (user_bp, '/api/users'),
        (role_bp, '/api/roles'),
        (permission_bp, '/api/permissions'),
        (environment_bp, '/api/environments'),
        (question_type_bp, '/api/question_types'),
        (question_bp, '/api/questions'),
        (answer_bp, '/api/answers'),
        (form_bp, '/api/forms'),
        (form_submission_bp, '/api/form_submissions'),
        (attachment_bp, '/api/attachments'),
    ]

    for blueprint, url_prefix in blueprints:
        app.register_blueprint(blueprint, url_prefix=url_prefix)