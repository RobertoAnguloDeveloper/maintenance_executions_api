import click
from flask.cli import with_appcontext
from app import db
from .db_config import init_database_config
from .db_init import DatabaseInitializer
from .create_test_data import TestDataCreator

def register_commands(app):
    # Database command group
    @app.cli.group()
    def database():
        """Database management commands."""
        pass

    # Configure command
    @database.command()
    def configure():
        """Configure database connection."""
        return init_database_config()

    # Init command
    @database.command()
    @with_appcontext
    def init():
        """Initialize database with required data."""
        initializer = DatabaseInitializer(app)
        success, error = initializer.init_db()
        if success:
            click.echo("Database initialization completed successfully.")
        else:
            click.echo(f"Error initializing database: {error}", err=True)

    # Create test data command
    @database.command()
    @with_appcontext
    def testdata():
        """Create test data for development."""
        click.echo("Creating test data...")
        creator = TestDataCreator(app)
        success, error = creator.create_test_data()
        if success:
            click.echo("Test data created successfully.")
        else:
            click.echo(f"Error creating test data: {error}", err=True)

    # Full setup command
    @database.command()
    def setup():
        """Complete database setup (configuration and initialization)."""
        click.echo("Step 1: Configuring database connection...")
        config_success = init_database_config()
        
        if not config_success:
            click.echo("Database configuration failed. Stopping setup.", err=True)
            return

        click.echo("\nStep 2: Initializing database...")
        initializer = DatabaseInitializer(app)
        init_success, error = initializer.init_db()
        
        if not init_success:
            click.echo(f"\n❌ Database initialization failed: {error}", err=True)
            return
            
        click.echo("\nStep 3: Creating test data...")
        creator = TestDataCreator(app)
        test_data_success, error = creator.create_test_data()
        
        if test_data_success:
            click.echo("\n✅ Database setup completed successfully!")
        else:
            click.echo(f"\n❌ Test data creation failed: {error}", err=True)

    return database