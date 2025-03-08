from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from config import Config
import logging
import sys
import os
from sqlalchemy import inspect
from flask_cors import CORS
import mimetypes

mimetypes.init()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def check_db_initialized(db_instance):
    """
    Check if the database has been initialized with basic data.
    
    Args:
        db_instance: SQLAlchemy instance
        
    Returns:
        bool: True if database is initialized, False otherwise
    """
    try:
        # First check if tables exist
        inspector = inspect(db_instance.engine)
        required_tables = ['roles', 'users', 'permissions', 'environments']
        existing_tables = inspector.get_table_names()
        
        if not all(table in existing_tables for table in required_tables):
            logger.info("Not all required tables exist")
            return False
        
        # Import models here to avoid circular imports
        from app.models.user import User
        from app.models.role import Role
        
        # Check if admin role exists
        admin_role = Role.query.filter_by(is_super_user=True).first()
        if not admin_role:
            logger.info("Admin role does not exist")
            return False
        
        # Check if admin user exists
        admin_user = User.query.filter_by(role_id=admin_role.id).first()
        if not admin_user:
            logger.info("Admin user does not exist")
            return False
        
        logger.info("Database is properly initialized")
        return True
        
    except Exception as e:
        logger.error(f"Error checking database initialization: {str(e)}")
        return False

def create_app(config_class=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    CORS(app, resources={
        r"/api/*": {
            "origins": ["*"],
            "methods": ["OPTIONS", "GET", "POST", "PUT", "DELETE"],
            "allow_headers": [
            "Content-Type", 
            "Authorization",
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Credentials",
            "Accept-Encoding"
        ],
        "supports_credentials": True,
        "expose_headers": ["Content-Type", "Authorization","Content-Length",
                "Content-Range","Accept-Ranges"]
        }
    })
    
    @app.after_request
    def after_request(response):
        # Allow file downloads from any origin
        if request.path.startswith('/api/cmms-configs/file/'):
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 
                'Content-Type, Authorization, X-Requested-With, Accept, Cache-Control, Accept-Encoding')
            response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
            response.headers.add('Access-Control-Expose-Headers',
                'Content-Length, Content-Range, Accept-Ranges')
            
            # Add specific headers for file downloads
            response.headers.add('Accept-Ranges', 'bytes')
            
            # Remove any problematic headers
            if 'Accept-Encoding' in response.headers:
                del response.headers['Accept-Encoding']
                
        return response
    
    try:
        # Initialize configuration
        if config_class is None:
            config_class = Config()
        
        # Load configuration
        app.config.from_object(config_class)
        
        # Ensure JWT config is explicitly set at app level
        app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'cmm-dev-2024')
        app.config['JWT_ACCESS_TOKEN_EXPIRES'] = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600))
        logger.info(f"JWT configuration initialized with consistent key")
        
        # Initialize extensions
        db.init_app(app)
        migrate.init_app(app, db)
        jwt.init_app(app)
        
        # Add JWT error handlers for better debugging
        @jwt.invalid_token_loader
        def invalid_token_callback(error_string):
            logger.error(f"Invalid token: {error_string}")
            return {"msg": error_string}, 422
            
        @jwt.expired_token_loader
        def expired_token_callback(jwt_header, jwt_payload):
            logger.warning(f"Expired token for user: {jwt_payload.get('sub', 'unknown')}")
            return {"msg": "Token has expired"}, 401
            
        @jwt.unauthorized_loader
        def missing_token_callback(error_string):
            logger.warning(f"Missing token: {error_string}")
            return {"msg": error_string}, 401

        with app.app_context():
            # Import models
            from app.models import (
                User, Role, Permission, RolePermission, Environment,
                QuestionType, Question, Answer, Form, FormQuestion,
                FormAnswer, FormSubmission, AnswerSubmitted, Attachment
            )
            
            # Register blueprints
            from app.views import register_blueprints
            register_blueprints(app)

            # Register CLI commands
            from management.commands import register_commands
            register_commands(app)

            # Initialize database if needed
            if not check_db_initialized(db):
                logger.info("Database not initialized. Starting initial setup...")
                db.create_all()
                
                from management.db_init import DatabaseInitializer
                initializer = DatabaseInitializer(app)
                success, error = initializer.init_db()
                    
                if not success:
                    logger.error(f"Failed to initialize admin user: {error}")
                    print("❌ Failed to initialize admin user. Please run 'flask database init'")
                    
            else:
                logger.info("Database already initialized")
                
        logger.info("✅ Application initialized successfully")
        return app
        
    except Exception as e:
        logger.error(f"❌ Application initialization failed: {str(e)}")
        raise

# Optional: Create the application instance
app = create_app()

# Register CLI commands with the application instance
if app is not None:
    with app.app_context():
        from management.commands import register_commands
        register_commands(app)