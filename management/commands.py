import click
from flask.cli import with_appcontext
from .db_config import init_database_config
from .db_init import DatabaseInitializer

def register_commands(app):
    @app.cli.group()
    def database():
        """Database management commands."""
        pass

    @database.command()
    def configure():
        """Configure database connection."""
        init_database_config()

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
        
        if init_success:
            click.echo("\n✅ Database setup completed successfully!")
        else:
            click.echo(f"\n❌ Database initialization failed: {error}", err=True)