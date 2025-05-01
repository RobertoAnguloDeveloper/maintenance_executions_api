# config.py

import os
import getpass
from dotenv import load_dotenv
from datetime import timedelta
import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import secrets  # For generating secure random keys

# Try to load .env, but don't fail if it doesn't exist
try:
    load_dotenv(raise_error_if_not_found=False)
except Exception:
    pass  # Ignore any errors during dotenv loading

logger = logging.getLogger(__name__)

class Config:
    """Application configuration class."""
    def __init__(self):
        # Check if .env exists, if not, create it
        self._ensure_env_file_exists()
        
        # Now load the environment variables (which might have just been created)
        try:
            load_dotenv(override=True)
        except Exception:
            pass
        
        # Set up configuration values
        self.SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(24)
        self.JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or secrets.token_hex(24)
        self.JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600))
        
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        self.SQLALCHEMY_DATABASE_URI = self._get_database_uri()
        
        # Add these new configurations
        self.UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
        self.MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
        
        print("Upload Folder")
        print(self.UPLOAD_FOLDER)
        
        # Ensure upload directory exists
        if not os.path.exists(self.UPLOAD_FOLDER):
            os.makedirs(self.UPLOAD_FOLDER)

    def _ensure_env_file_exists(self):
        """Check if .env file exists, create it if it doesn't."""
        env_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '.env')
        
        if not os.path.exists(env_path):
            # .env file doesn't exist, create it with default values
            try:
                # Create a secure random key for SECRET_KEY and JWT_SECRET_KEY
                secret_key = secrets.token_hex(24)
                jwt_secret_key = secrets.token_hex(24)
                
                with open(env_path, 'w', encoding='utf-8') as f:
                    f.write("# Auto-generated .env file\n\n")
                    f.write("# Security Configuration\n")
                    f.write(f"SECRET_KEY={secret_key}\n")
                    f.write(f"JWT_SECRET_KEY={jwt_secret_key}\n\n")
                    f.write("# Application Settings\n")
                    f.write("JWT_ACCESS_TOKEN_EXPIRES=3600\n\n")
                    # Database URL will be added by _get_database_uri()
                
                logger.info(f"Created new .env file at {env_path}")
                print(f"✅ Created new .env file at {env_path}")
            except Exception as e:
                logger.error(f"Failed to create .env file: {str(e)}")
                print(f"⚠️ Warning: Could not create .env file: {str(e)}")

    def create_db_and_user(self, db_host, db_name, db_user, db_pass):
        """Create database and user if they don't exist."""
        try:
            # Connect to PostgreSQL server with superuser privileges
            print("\n📊 Connecting to PostgreSQL server...")
            conn = psycopg2.connect(
                host=db_host,
                user='postgres',  # Default superuser
                password=getpass.getpass("Enter PostgreSQL superuser (postgres) password: ")
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            print(f"✅ Connected to PostgreSQL server on {db_host}")

            # Check if user exists
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (db_user,))
            if not cursor.fetchone():
                # Create user if not exists
                cursor.execute(f"CREATE USER {db_user} WITH PASSWORD %s", (db_pass,))
                logger.info(f"Created database user: {db_user}")
                print(f"✅ Created database user: {db_user}")
            else:
                print(f"✅ User {db_user} already exists")

            # Check if database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if not cursor.fetchone():
                # Create database if not exists
                cursor.execute(f"CREATE DATABASE {db_name} OWNER {db_user}")
                logger.info(f"Created database: {db_name}")
                print(f"✅ Created database: {db_name}")
            else:
                print(f"✅ Database {db_name} already exists")

            # Grant privileges
            cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user}")
            print(f"✅ Granted privileges to {db_user} on {db_name}")
            
            cursor.close()
            conn.close()
            return True, None

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error creating database/user: {error_msg}")
            return False, error_msg

    def _get_database_uri(self):
        """Get database URI from environment or prompt user."""
        db_url = os.environ.get('DATABASE_URL')
        
        # Handle potential encoding issues
        if db_url:
            try:
                # Test if the URL is valid UTF-8
                db_url.encode('utf-8').decode('utf-8')
            except (UnicodeDecodeError, UnicodeEncodeError):
                # If there's an encoding issue, reset db_url to force reconfiguration
                logger.warning("Invalid encoding in DATABASE_URL. Reconfiguring...")
                db_url = None
        
        if not db_url and os.isatty(0):
            print("\n⚠️  Database URL not found in environment variables or invalid.")
            print("🔄 Starting database configuration...")
            
            # Get database connection details
            db_host = input("Database host (default: localhost): ").strip() or 'localhost'
            db_name = input("Database name: ").strip()
            db_user = input("Database username: ").strip()
            db_pass = getpass.getpass("Database password: ").strip()

            # Create database and user if needed
            success, error = self.create_db_and_user(db_host, db_name, db_user, db_pass)
            if not success:
                raise Exception(f"Failed to create database/user: {error}")

            db_url = f"postgresql://{db_user}:{db_pass}@{db_host}/{db_name}"
            
            # Always save to .env in this automated setup
            try:
                env_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '.env')
                
                # Read existing content if file exists
                existing_content = ""
                if os.path.exists(env_path):
                    with open(env_path, 'r', encoding='utf-8') as f:
                        existing_content = f.read()
                
                # Check if DATABASE_URL already exists in the file
                if "DATABASE_URL=" in existing_content:
                    # Replace the existing DATABASE_URL line
                    import re
                    existing_content = re.sub(
                        r'DATABASE_URL=.*(\r\n|\r|\n|$)', 
                        f'DATABASE_URL={db_url}\n', 
                        existing_content
                    )
                    
                    with open(env_path, 'w', encoding='utf-8') as f:
                        f.write(existing_content)
                else:
                    # Append DATABASE_URL to the file
                    with open(env_path, 'a', encoding='utf-8') as f:
                        f.write("\n# Database Configuration\n")
                        f.write(f"DATABASE_URL={db_url}\n")
                
                # Set the environment variable directly for the current process
                os.environ['DATABASE_URL'] = db_url
                
                print("✅ Database credentials saved to .env file")
            except Exception as e:
                logger.error(f"Error saving to .env file: {str(e)}")
                print(f"⚠️  Warning: Could not save to .env file: {str(e)}")
                # Set the environment variable even if we couldn't save to .env
                os.environ['DATABASE_URL'] = db_url

        if not db_url:
            raise ValueError("Database URL is required. Please set DATABASE_URL environment variable or run in interactive mode.")
            
        return db_url

    @staticmethod
    def test_database_connection(db_url):
        """Test database connection with provided credentials."""
        try:
            print("🔄 Testing database connection...")
            from sqlalchemy import create_engine
            engine = create_engine(db_url)
            connection = engine.connect()
            connection.close()
            print("✅ Database connection successful!")
            return True, None
        except Exception as e:
            error_msg = str(e)
            if 'password' in error_msg.lower():
                error_msg = "Authentication failed. Please check your credentials."
            elif 'utf-8' in error_msg.lower():
                error_msg = "Encoding error in connection string. Please reconfigure the database."
            return False, error_msg