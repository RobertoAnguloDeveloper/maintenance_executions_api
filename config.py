# config.py

import os
import getpass
from dotenv import load_dotenv
from datetime import timedelta
import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

load_dotenv()
logger = logging.getLogger(__name__)

class Config:
    """Application configuration class."""
    def __init__(self):
        self.SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32)
        self.JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or os.urandom(32)
        self.JWT_ACCESS_TOKEN_EXPIRES = 3600
        
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        self.SQLALCHEMY_DATABASE_URI = self._get_database_uri()

    def create_db_and_user(self, db_host, db_name, db_user, db_pass):
        """Create database and user if they don't exist."""
        try:
            # Connect to PostgreSQL server with superuser privileges
            conn = psycopg2.connect(
                host=db_host,
                user='postgres',  # Default superuser
                password=getpass.getpass("Enter PostgreSQL superuser (postgres) password: ")
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            # Check if user exists
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (db_user,))
            if not cursor.fetchone():
                # Create user if not exists
                cursor.execute(f"CREATE USER {db_user} WITH PASSWORD %s", (db_pass,))
                logger.info(f"Created database user: {db_user}")

            # Check if database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if not cursor.fetchone():
                # Create database if not exists
                cursor.execute(f"CREATE DATABASE {db_name} OWNER {db_user}")
                logger.info(f"Created database: {db_name}")

            # Grant privileges
            cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user}")
            
            cursor.close()
            conn.close()
            return True, None

        except Exception as e:
            logger.error(f"Error creating database/user: {str(e)}")
            return False, str(e)

    def _get_database_uri(self):
        """Get database URI from environment or prompt user."""
        db_url = os.environ.get('DATABASE_URL')
        
        if not db_url and os.isatty(0):
            print("\n⚠️  Database URL not found in environment variables.")
            
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
            
            # Ask to save to .env
            if input("\nSave credentials to .env file? (y/n): ").lower().strip() == 'y':
                try:
                    with open('.env', 'a') as f:
                        f.write("\n# Database Configuration\n")
                        f.write(f"DATABASE_URL={db_url}\n")
                    print("✅ Credentials saved to .env file")
                except Exception as e:
                    print(f"⚠️  Warning: Could not save to .env file: {str(e)}")

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
            error_msg = str(e)
            if 'password' in error_msg.lower():
                error_msg = "Authentication failed. Please check your credentials."
            return False, error_msg