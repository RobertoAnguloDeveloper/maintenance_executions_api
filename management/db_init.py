from app import create_app, db
from app.models.user import User
from app.models.role import Role
from app.models.environment import Environment
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DatabaseInitializer:
    def __init__(self, app=None):
        self.app = app or create_app()
    
    def init_super_admin_role(self):
        """Initialize or update Super admin role."""
        role = Role.query.filter_by(name="Super admin").first()
        if not role:
            role = Role(
                name="Super admin",
                description="Can create all",
                is_super_user=True
            )
            db.session.add(role)
            logger.info("Super admin role created")
        else:
            role.description = "Can create all"
            role.is_super_user = True
            role.updated_at = datetime.utcnow()
            logger.info("Super admin role updated")
        return role

    def init_admin_environment(self):
        """Initialize or update ADMIN environment."""
        env = Environment.query.filter_by(name="ADMIN").first()
        if not env:
            env = Environment(
                name="ADMIN",
                description="Only administrators"
            )
            db.session.add(env)
            logger.info("ADMIN environment created")
        else:
            env.description = "Only administrators"
            env.updated_at = datetime.utcnow()
            logger.info("ADMIN environment updated")
        return env

    def init_admin_user(self, role, env):
        """Initialize or update admin user."""
        user = User.query.filter_by(username='admin').first()
        if not user:
            user = User(
                first_name="ADMIN",
                last_name="ADMIN",
                email="dataanalyst-2@plgims.com",
                username="admin",
                role_id=role.id,
                environment_id=env.id
            )
            db.session.add(user)
            logger.info("Admin user created")
        else:
            user.first_name = "ADMIN"
            user.last_name = "ADMIN"
            user.email = "dataanalyst-2@plgims.com"
            user.role_id = role.id
            user.environment_id = env.id
            user.updated_at = datetime.utcnow()
            logger.info("Admin user updated")
        
        user.set_password('123')
        return user

    def init_db(self):
        """Initialize all database components."""
        try:
            with self.app.app_context():
                # Initialize role
                role = self.init_super_admin_role()
                
                # Initialize environment
                env = self.init_admin_environment()
                
                # Commit to ensure IDs are available
                db.session.commit()
                
                # Initialize admin user
                user = self.init_admin_user(role, env)
                
                # Commit all changes
                db.session.commit()
                logger.info("Database initialization completed successfully")
                return True, None
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error during database initialization: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

def init_database():
    """Convenience function to run database initialization."""
    initializer = DatabaseInitializer()
    success, error = initializer.init_db()
    if success:
        print("Database initialization completed successfully")
    else:
        print(f"Error during database initialization: {error}")

if __name__ == "__main__":
    init_database()