import os
import getpass
from dotenv import load_dotenv
from datetime import timedelta
import logging

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

def prompt_for_credentials():
    """Prompt user for database credentials."""
    try:
        print("\n=== Database Configuration ===")
        print("Please enter your database credentials:")
        db_host = input("Database host: ").strip()
        if not db_host:
            raise ValueError("Database host cannot be empty")

        db_name = input("Database name: ").strip()
        if not db_name:
            raise ValueError("Database name cannot be empty")

        db_user = input("Database username: ").strip()
        if not db_user:
            raise ValueError("Database username cannot be empty")

        db_pass = getpass.getpass("Database password: ").strip()
        if not db_pass:
            raise ValueError("Database password cannot be empty")
        
        # Create connection string
        db_url = f"postgresql://{db_user}:{db_pass}@{db_host}/{db_name}"
        
        # Ask if want to save to .env
        save = input("\nSave credentials to .env file? (y/n): ").lower().strip() == 'y'
        if save:
            try:
                with open('.env', 'a') as f:
                    f.write("\n# Database Configuration")
                    f.write(f"\nDATABASE_URL={db_url}")
                print("✅ Credentials saved to .env file")
            except Exception as e:
                print(f"⚠️  Warning: Could not save to .env file: {str(e)}")
        
        return db_url
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
        return None
    except Exception as e:
        print(f"\n❌ Error during credential input: {str(e)}")
        return None

class Config:
    """Application configuration class."""
    def __init__(self):
        # Security settings
        self.SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32)
        self.JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or os.urandom(32)
        self.JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
        
        # SQLAlchemy settings
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        self.SQLALCHEMY_DATABASE_URI = self._get_database_uri()

    def _get_database_uri(self):
        """Get database URI from environment or prompt user."""
        # Try to get from environment first
        db_url = os.environ.get('DATABASE_URL')
        
        # If no environment variable and running in terminal
        if not db_url and os.isatty(0):  # Check if running in terminal
            print("\n⚠️  Database URL not found in environment variables.")
            db_url = prompt_for_credentials()
            
            if db_url:
                # Test connection before accepting
                success, error = self.test_database_connection(db_url)
                if success:
                    print("✅ Database connection successful!")
                    return db_url
                else:
                    print(f"❌ Database connection failed: {error}")
                    return None
        
        if not db_url:
            raise ValueError("Database URL is required. Please set DATABASE_URL environment variable or run in interactive mode.")
            
        return db_url

    @staticmethod
    def test_database_connection(db_url):
        """Test database connection with provided credentials."""
        try:
            from sqlalchemy import create_engine
            engine = create_engine(db_url)
            connection = engine.connect()
            connection.close()
            return True, None
        except Exception as e:
            # Ensure password is not included in error message
            error_msg = str(e)
            if 'password' in error_msg.lower():
                error_msg = "Authentication failed. Please check your credentials."
            return False, error_msg