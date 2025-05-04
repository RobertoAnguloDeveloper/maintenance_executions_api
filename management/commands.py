# management/commands.py

import click
from flask.cli import with_appcontext
from app import db, create_app # Import create_app if needed for context outside Flask CLI runner
from .db_config import init_database_config
from .db_init import DatabaseInitializer
# Assuming create_test_data exists:
# from .create_test_data import TestDataCreator # Uncomment if you have this file
from app.models.token_blocklist import TokenBlocklist # Import the blocklist model
from datetime import datetime, timedelta, timezone # Import timedelta and timezone
import logging

logger = logging.getLogger("app") # Use the app logger

def register_commands(app):
    """Registers all custom command groups with the Flask app."""

    # --- Database Command Group ---
    @app.cli.group()
    def database():
        """Database management commands."""
        pass

    # Configure command
    @database.command()
    @with_appcontext # Add context if config reading needs it
    def configure():
        """Configure database connection."""
        # If init_database_config needs app context (e.g., for config reading):
        # with app.app_context():
        #    return init_database_config()
        # Otherwise, if it's self-contained:
        return init_database_config() # Keep original if context not needed

    # Init command
    @database.command()
    @with_appcontext
    def init():
        """Initialize database with required data."""
        # app context is provided by the decorator
        initializer = DatabaseInitializer(app)
        success, error = initializer.init_db()
        if success:
            click.echo("Database initialization completed successfully.")
        else:
            click.echo(f"❌ Error initializing database: {error}", err=True)

    # Create test data command (Uncomment if TestDataCreator exists)
    # @database.command()
    # @with_appcontext
    # def testdata():
    #     """Create test data for development."""
    #     click.echo("Creating test data...")
    #     creator = TestDataCreator(app) # Assuming TestDataCreator exists
    #     success, error = creator.create_test_data()
    #     if success:
    #         click.echo("Test data created successfully.")
    #     else:
    #         click.echo(f"❌ Error creating test data: {error}", err=True)

    # Full setup command
    @database.command()
    # Note: setup calls configure and init. Ensure context is handled correctly.
    # It might be better to make setup also use @with_appcontext and run configure inside it.
    def setup():
        """Complete database setup (configuration and initialization)."""
        click.echo("Step 1: Configuring database connection...")
        # Assuming configure doesn't strictly need app context based on original code
        # If it does, wrap it:
        # with app.app_context():
        #    config_success = init_database_config()
        config_success = init_database_config() # Keeping original structure

        if not config_success:
            click.echo("❌ Database configuration failed. Stopping setup.", err=True)
            return

        click.echo("\nStep 2: Initializing database...")
        # init() already uses @with_appcontext, but calling it via invoke might be cleaner
        # Or replicate logic here within context:
        with app.app_context():
            initializer = DatabaseInitializer(app)
            init_success, error = initializer.init_db()

        if not init_success:
            click.echo(f"\n❌ Database initialization failed: {error}", err=True)
            return

        # Uncomment Step 3 if testdata command is implemented
        # click.echo("\nStep 3: Creating test data...")
        # with app.app_context():
        #     creator = TestDataCreator(app)
        #     test_data_success, error = creator.create_test_data()
        #
        # if test_data_success:
        #     click.echo("\n✅ Database setup completed successfully!")
        # else:
        #     click.echo(f"\n❌ Test data creation failed: {error}", err=True)

        click.echo("\n✅ Database setup (config & init) completed successfully! Skipping test data generation.")


    # --- NEW: Cleanup Blocklist Command ---
    @database.command('cleanup-blocklist')
    @with_appcontext # Essential for accessing app.config and db.session
    def cleanup_token_blocklist():
        """Remove expired token JTIs from the blocklist."""
        click.echo("Starting cleanup of token blocklist...")
        try:
            # Get token expiry duration from config (ensure it's timedelta)
            # Using app.config directly because we have app context
            token_lifetime = app.config.get('JWT_ACCESS_TOKEN_EXPIRES')

            # Ensure token_lifetime is a timedelta object
            if isinstance(token_lifetime, (int, float)):
                token_lifetime = timedelta(seconds=int(token_lifetime))
            elif not isinstance(token_lifetime, timedelta):
                token_lifetime = timedelta(hours=1) # Safe fallback if config is missing/invalid
                logger.warning(f"JWT_ACCESS_TOKEN_EXPIRES not found or not a timedelta/int in config, using fallback: {token_lifetime}")

            # Calculate the cutoff time (NOW - (lifetime + buffer))
            # We delete entries CREATED before this time.
            buffer = timedelta(minutes=5) # Add a small buffer
            cutoff_time = datetime.now(timezone.utc) - token_lifetime - buffer
            click.echo(f"Calculated cutoff time (UTC): {cutoff_time.isoformat()}")
            logger.info(f"Cleaning up blocklist entries created before: {cutoff_time.isoformat()}")

            # Perform the deletion using bulk delete for efficiency
            num_deleted = db.session.query(TokenBlocklist).filter(
                TokenBlocklist.created_at < cutoff_time
            ).delete(synchronize_session=False) # synchronize_session=False is faster for bulk

            db.session.commit()

            click.echo(f"✅ Successfully deleted {num_deleted} expired token entries from the blocklist.")
            logger.info(f"Deleted {num_deleted} expired token entries from the blocklist.")

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error during blocklist cleanup: {str(e)}"
            logger.error(error_msg, exc_info=True)
            click.echo(f"❌ {error_msg}", err=True)

    # Return the main database command group
    return database

# If you have separate migration commands, ensure they are registered too.
# Example:
# from .migration_commands import register_migration_commands
# def register_all_commands(app):
#      register_commands(app) # Registers the 'database' group commands
#      register_migration_commands(app) # Registers the 'db_migration' group commands