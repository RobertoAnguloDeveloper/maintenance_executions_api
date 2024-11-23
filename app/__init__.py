from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from config import Config
import logging
import sys
from sqlalchemy import inspect
from flask_cors import CORS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        r"/*": {
            "origins": ["http://localhost:*",
                        "http://127.0.0.1:*"],
            "methods": ["OPTIONS", "GET", "POST", "PUT", "DELETE"],
            "allow_headers": [
            "Content-Type", 
            "Authorization",
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Credentials"
        ],
        "supports_credentials": True,
        "expose_headers": ["Content-Type", "Authorization"]
        }
    })
    
    try:
        # Initialize configuration
        if config_class is None:
            config_class = Config()
        
        # Load configuration
        app.config.from_object(config_class)
        
        # Initialize extensions
        db.init_app(app)
        migrate.init_app(app, db)
        jwt.init_app(app)

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