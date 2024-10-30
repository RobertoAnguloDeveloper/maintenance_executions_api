from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from config import Config

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

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
        question_type,  # New model
        question,
        form_submission,
        answer,
        attachment
    )

    # Import blueprints registration function
    from app.views import register_blueprints
    
    # Register all blueprints
    register_blueprints(app)

    return app