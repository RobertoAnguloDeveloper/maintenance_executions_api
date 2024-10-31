from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app(config_class=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
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

        # Import models
        from app.models import (
            user,
            role,
            role_permission,
            permission,
            environment,
            form,
            question_type,
            question,
            form_submission,
            answer,
            attachment
        )

        # Import blueprints registration function
        from app.views import register_blueprints
        
        # Register all blueprints
        register_blueprints(app)
        
        logger.info("✅ Application initialized successfully")
        return app
        
    except Exception as e:
        logger.error(f"❌ Application initialization failed: {str(e)}")
        raise