import click
from flask.cli import with_appcontext
from flask_migrate import upgrade, downgrade
from app import db
import logging

logger = logging.getLogger(__name__)

def register_migration_commands(app):
    @app.cli.group()
    def db_migration():
        """Database migration commands."""
        pass

    @db_migration.command()
    @with_appcontext
    def upgrade_db():
        """Apply all pending migrations."""
        try:
            print("\n🚀 Starting database upgrade...")
            upgrade()
            print("✅ Database upgrade completed successfully!")
        except Exception as e:
            print(f"❌ Error during database upgrade: {str(e)}")
            logger.error(f"Database upgrade failed: {str(e)}")

    @db_migration.command()
    @with_appcontext
    def downgrade_db():
        """Revert last migration."""
        try:
            if click.confirm('⚠️  Are you sure you want to downgrade the database? This action cannot be undone!'):
                print("\n🔄 Starting database downgrade...")
                downgrade()
                print("✅ Database downgrade completed successfully!")
            else:
                print("Operation cancelled.")
        except Exception as e:
            print(f"❌ Error during database downgrade: {str(e)}")
            logger.error(f"Database downgrade failed: {str(e)}")

    @db_migration.command()
    @with_appcontext
    def verify_soft_delete():
        """Verify soft delete columns were added correctly."""
        try:
            print("\n🔍 Verifying soft delete columns...")
            
            inspector = db.inspect(db.engine)
            tables = [
                'users', 'roles', 'permissions', 'environments', 'questions',
                'question_types', 'answers', 'forms', 'form_questions',
                'form_answers', 'form_submissions', 'answers_submitted',
                'attachments', 'role_permissions'
            ]
            
            all_valid = True
            for table in tables:
                columns = [c['name'] for c in inspector.get_columns(table)]
                if 'is_deleted' not in columns or 'deleted_at' not in columns:
                    print(f"❌ Table '{table}' is missing soft delete columns!")
                    all_valid = False
                else:
                    print(f"✅ Table '{table}' has all required columns")
                    
            if all_valid:
                print("\n✅ All tables have the required soft delete columns!")
            else:
                print("\n❌ Some tables are missing soft delete columns!")
                
        except Exception as e:
            print(f"❌ Error during verification: {str(e)}")
            logger.error(f"Soft delete verification failed: {str(e)}")

    return db_migration