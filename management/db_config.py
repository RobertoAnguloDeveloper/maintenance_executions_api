from config import Config
import os

def init_database_config():
    """Initialize database configuration with user prompts."""
    config = Config()
    
    print("\n=== Database Configuration Setup ===")
    print("This script will help you configure the database connection.")
    
    # Get database URL (this will prompt if not in environment)
    db_url = config.SQLALCHEMY_DATABASE_URI
    
    # Test connection
    print("\nTesting database connection...")
    success, error = Config.test_database_connection(db_url)
    
    if success:
        print("✅ Database connection successful!")
        print(f"\nConnection string: {db_url.replace(db_url.split('@')[0].split('://')[-1], '***:***')}")
    else:
        print("❌ Database connection failed!")
        print(f"Error: {error}")
        print("\nPlease check your credentials and try again.")

if __name__ == "__main__":
    init_database_config()