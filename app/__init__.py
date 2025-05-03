# app/__init__.py
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
# Import setup_logging directly
from app.utils.logging_config import setup_logging
from config import Config
import logging
import sys
from sqlalchemy import inspect
from flask_cors import CORS
import mimetypes
import os # Import os
from flask_caching import Cache
from functools import wraps

# Initialize mimetypes database
mimetypes.init()

# --- Configure logging ONCE at the module level ---
# This ensures it runs only when the module is first imported,
# not every time create_app is called by the reloader.
# setup_logging() returns the configured logger instance for the app.
module_logger = setup_logging() # Use the specific app logger name

# Initialize extensions globally (outside factory is fine for these)
# They will be associated with an app instance later using init_app()
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

# Import the model here or inside create_app within context if preferred
from app.models.token_blocklist import TokenBlocklist

cache = Cache()  # Initialize in create_app with config

def cached_blocklist_check(expire=300):
    """Caching decorator for blocklist checks"""
    def decorator(f):
        @wraps(f)
        def decorated_function(jwt_header, jwt_payload):
            jti = jwt_payload.get("jti")
            if not jti:
                return False
                
            # Try to get from cache first
            cache_key = f"blocklist:{jti}"
            cached_result = cache.get(cache_key)
            
            if cached_result is not None:
                return cached_result
                
            # If not in cache, check database
            result = f(jwt_header, jwt_payload)
            
            # Cache the result (both positive and negative)
            cache.set(cache_key, result, timeout=expire)
            return result
        return decorated_function
    return decorator

@jwt.token_in_blocklist_loader
@cached_blocklist_check(expire=300)  # Cache results for 5 minutes
def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
    # Same implementation but with less logging
    jti = jwt_payload.get("jti")
    if not jti:
        return False

    try:
        is_revoked = TokenBlocklist.query.filter_by(jti=jti).scalar() is not None
        return is_revoked
    except Exception as e:
        app_logger = logging.getLogger("app")
        app_logger.error(f"Error checking blocklist: {e}", exc_info=True)
        return False  # Default to allowing if check fails

def check_db_initialized(db_instance):
    """
    Check if the database has been initialized with basic data.
    Uses the 'app' logger instance.
    """
    logger = logging.getLogger("app")
    
    # First check if we can connect to the database at all
    try:
        # Test basic connection
        connection = db_instance.engine.connect()
        connection.close()
    except Exception as e:
        # If we can't connect, log the error and return False
        logger.error(f"Database connection error: {str(e)}", exc_info=True)
        
        # Check if the error is encoding-related
        if 'utf-8' in str(e).lower() or 'codec' in str(e).lower():
            logger.error("Encoding issue detected in database URL. Please delete .env file and restart the app.")
            print("\n❌ Encoding issue detected in database URL.")
            print("Please delete the .env file and restart the application with 'flask run'.")
        
        return False
    
    try:
        # First check if tables exist using SQLAlchemy inspector
        inspector = inspect(db_instance.engine)
        required_tables = ['roles', 'users', 'permissions', 'environments', 'token_blocklist']
        existing_tables = inspector.get_table_names()

        if not all(table in existing_tables for table in required_tables):
            logger.debug("Not all required tables exist")
            return False

        # Import models locally to avoid circular imports
        from app.models.user import User
        from app.models.role import Role

        # Check if an admin role exists
        admin_role = Role.query.filter_by(is_super_user=True).first()
        if not admin_role:
            logger.debug("Admin role does not exist")
            return False

        # Check if admin user exists
        admin_user = User.query.filter_by(role_id=admin_role.id).first()
        if not admin_user:
            logger.debug("Admin user does not exist")
            return False

        # If all checks pass, the database seems initialized
        logger.debug("Database is properly initialized")
        return True

    except Exception as e:
        # Log any error during the check
        logger.error(f"Error checking database initialization: {str(e)}", exc_info=True)
        return False


def create_app(config_class=None):
    """Create and configure the Flask application instance."""
    # Get the logger instance configured at the module level
    app_init_logger = logging.getLogger("app")

    # Create the Flask app instance
    app = Flask(__name__)

    # --- CORS setup ---
    # Configure Cross-Origin Resource Sharing for API endpoints
    CORS(app, resources={
        r"/api/*": {
            "origins": "*", # Allow requests from any origin (adjust for production)
            "methods": ["OPTIONS", "GET", "POST", "PUT", "DELETE"], # Allowed HTTP methods
            "allow_headers": [ # Headers the client is allowed to send
                "Content-Type",
                "Authorization",
                "Access-Control-Allow-Origin",
                "Access-Control-Allow-Credentials",
                "Accept-Encoding",
                "X-Requested-With",
                "Origin"
            ],
            "supports_credentials": True, # Allow credentials (like cookies, auth headers)
            "expose_headers": [ # Headers the server can expose to the client
                "Content-Type",
                "Authorization",
                "Content-Length",
                "Content-Range",
                "Accept-Ranges"
            ]
        }
    })

    # --- after_request handler for CORS Headers ---
    # Ensure CORS headers are added correctly, especially for preflight OPTIONS requests
    @app.after_request
    def after_request(response):
        # Add standard CORS headers for non-OPTIONS requests
        if request.method != 'OPTIONS':
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers',
                'Content-Type, Authorization, X-Requested-With, Origin')
            response.headers.add('Access-Control-Allow-Methods',
                'GET, POST, PUT, DELETE, OPTIONS')

        # Handle OPTIONS preflight requests specifically
        if request.method == 'OPTIONS':
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers',
                'Content-Type, Authorization, X-Requested-With, Origin')
            response.headers.add('Access-Control-Allow-Methods',
                'GET, POST, PUT, DELETE, OPTIONS')
            # Cache preflight response for 24 hours
            response.headers.add('Access-Control-Max-Age', '86400')

        return response

    try:
        # --- Configuration and Extensions Initialization ---
        # Load configuration from Config object or environment
        if config_class is None:
            config_class = Config()
        app.config.from_object(config_class)

        # Initialize Flask extensions with the app instance
        db.init_app(app)
        migrate.init_app(app, db)
        jwt.init_app(app)

        # --- Application Context ---
        # Operations requiring access to the app context (like database queries, imports)
        with app.app_context():
            # --- Import Models (within context) ---
            # Import models here to ensure they are registered with SQLAlchemy
            # Use noqa F401 to suppress unused import warnings if using linters
            from app.models import ( # noqa F401
                User, Role, Permission, RolePermission, Environment,
                QuestionType, Question, Answer, Form, FormQuestion,
                FormAnswer, FormSubmission, AnswerSubmitted, Attachment, TokenBlocklist 
            )

            # --- Register Blueprints (within context) ---
            from app.views import register_blueprints
            register_blueprints(app)

            # --- Register CLI Commands (within context) ---
            try:
                from management.commands import register_commands
                register_commands(app)
            except ImportError:
                app_init_logger.warning("management.commands not found or could not be imported. CLI commands might not be available.")

            # --- Conditional Database Initialization (Run only in main reloader process) ---
            # Check the Werkzeug environment variable to avoid running this twice in debug mode
            is_main_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'

            # Only perform DB checks and potential initialization in the main child process
            if is_main_process:
                app_init_logger.info("Running in main Werkzeug process. Checking DB status...")
                db_initialized = False
                
                # Try to create tables first
                try:
                    db.create_all()
                    app_init_logger.info("Database tables created (or already exist)")
                except Exception as e:
                    app_init_logger.error(f"Error creating database tables: {str(e)}", exc_info=True)
                    print(f"❌ Error creating database tables: {str(e)}")
                    print("Please check your database configuration in .env file.")
                    
                # Now check if the database is initialized with required data
                if not check_db_initialized(db):
                    app_init_logger.warning("Database not initialized. Attempting initial setup...")
                    try:
                        # Import the initializer class
                        from management.db_init import DatabaseInitializer
                        initializer = DatabaseInitializer(app)
                        # Call the initialization method
                        success, error = initializer.init_db(check_empty=False)

                        if not success:
                            # Log critical failure and print to console
                            app_init_logger.error(f"Failed to initialize database: {error}")
                            print(f"❌ Failed to initialize database: {error}")
                            print("Please run 'flask database init' manually.")
                        else:
                            app_init_logger.info("Database initialization completed successfully.")
                            db_initialized = True

                    except ImportError:
                        app_init_logger.error("Could not import DatabaseInitializer. Database might not be initialized.")
                        print("❌ Error: Could not import DatabaseInitializer. Run 'flask database init' manually.")
                    except Exception as init_db_e:
                        # Catch any other exception during DB initialization
                        app_init_logger.error(f"Exception during database initialization: {init_db_e}", exc_info=True)
                        print(f"❌ Exception during database initialization: {init_db_e}")
                else:
                    # Log that the DB is already set up
                    app_init_logger.info("Database already initialized (checked in main process).")
                    db_initialized = True

                # If initialization was successful, log it
                if db_initialized:
                    app_init_logger.info("✅ Database ready for use")

        # Log successful app initialization only once in the main process
        if is_main_process:
            app_init_logger.info("✅ Application initialized successfully (Main Process)")

        # Return the configured app instance
        return app

    except Exception as e:
        # Log critical errors during app creation using the module logger
        module_logger.error(f"❌ Application initialization failed critically: {str(e)}", exc_info=True)
        # Re-raise the exception to halt execution if startup fails
        raise

# Note: Removed app = create_app() from module level.
# The app instance should be created by the entry point (e.g., run.py or WSGI server).
