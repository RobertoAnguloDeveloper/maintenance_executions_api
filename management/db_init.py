import logging
import getpass
from app.models.permission import Permission
from app.utils.helpers import validate_email
import re
from app import db
from app.models.user import User
from app.models.role import Role
from app.models.environment import Environment
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseInitializer:
    def __init__(self, app):
        self.app = app

    def prompt_admin_credentials(self):
        """Prompt for admin user details with validation."""
        print("\n=== Admin User Setup ===")
        print("Please enter the admin user details:")

        while True:
            username = input("Username (minimum 4 characters): ").strip()
            if len(username) < 4:
                print("❌ Username must be at least 4 characters long")
                continue
            if not re.match("^[a-zA-Z0-9_-]+$", username):
                print("❌ Username can only contain letters, numbers, underscores and hyphens")
                continue
            break

        while True:
            email = input("Email: ").strip()
            if not validate_email(email):
                print("❌ Please enter a valid email address")
                continue
            break

        while True:
            first_name = input("First Name: ").strip()
            if not first_name:
                print("❌ First name cannot be empty")
                continue
            break

        while True:
            last_name = input("Last Name: ").strip()
            if not last_name:
                print("❌ Last name cannot be empty")
                continue
            break

        while True:
            password = getpass.getpass("Password (minimum 8 characters): ")
            if len(password) < 8:
                print("❌ Password must be at least 8 characters long")
                continue
            
            confirm_password = getpass.getpass("Confirm password: ")
            if password != confirm_password:
                print("❌ Passwords do not match")
                continue
            break

        return {
            'username': username,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'password': password
        }

    def init_permissions(self):
        """Initialize or update all permissions."""
        permissions_config = {
            # User Management
            'view_users': 'Can view users',
            'create_users': 'Can create users',
            'update_users': 'Can update users',
            'delete_users': 'Can delete users',
            
            # Form Management
            'view_forms': 'Can view forms',
            'create_forms': 'Can create forms',
            'update_forms': 'Can update forms',
            'delete_forms': 'Can delete forms',
            'view_public_forms': 'Can view public forms only',
            
            # Question Management
            'view_questions': 'Can view questions',
            'create_questions': 'Can create questions',
            'update_questions': 'Can update questions',
            'delete_questions': 'Can delete questions',
            
            # Question Type Management
            'view_question_types': 'Can view question types',
            'create_question_types': 'Can create question types',
            'update_question_types': 'Can update question types',
            'delete_question_types': 'Can delete question types',
            
            # Answer Management
            'view_answers': 'Can view answers',
            'create_answers': 'Can create answers',
            'update_answers': 'Can update answers',
            'delete_answers': 'Can delete answers',
            
            # Form Submission Management
            'view_submissions': 'Can view form submissions',
            'create_submissions': 'Can create form submissions',
            'update_submissions': 'Can update form submissions',
            'delete_submissions': 'Can delete form submissions',
            'view_own_submissions': 'Can view own form submissions',
            'update_own_submissions': 'Can update own form submissions',
            'delete_own_submissions': 'Can delete own form submissions',
            
            # Attachment Management
            'view_attachments': 'Can view attachments',
            'create_attachments': 'Can create attachments',
            'update_attachments': 'Can update attachments',
            'delete_attachments': 'Can delete attachments',
            'view_own_attachments': 'Can view own attachments',
            'update_own_attachments': 'Can update own attachments',
            'delete_own_attachments': 'Can delete own attachments',
        }

        created_permissions = []
        for perm_name, description in permissions_config.items():
            permission = Permission.query.filter_by(name=perm_name).first()
            if permission:
                permission.description = description
                permission.updated_at = datetime.utcnow()
                logger.info(f"Updated permission: {perm_name}")
            else:
                permission = Permission(
                    name=perm_name,
                    description=description
                )
                db.session.add(permission)
                logger.info(f"Created permission: {perm_name}")
            
            created_permissions.append(permission)
        
        try:
            db.session.commit()
            return created_permissions
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating permissions: {str(e)}")
            raise

    def init_roles(self):
        """Initialize or update all roles with their specific permissions."""
        # Get all permissions first
        permissions = {p.name: p for p in self.init_permissions()}
        
        roles_config = {
            'Admin': {
                'description': 'Full system administrator',
                'is_super_user': True,
                'permissions': list(permissions.values())  # Admin gets all permissions
            },
            'Site Manager': {
                'description': 'Manager with full access within their environment',
                'is_super_user': False,
                'permissions': [
                    permissions['view_users'],permissions['create_users'],
                    permissions['update_users'],permissions['update_users'],permissions['delete_users'],
                    permissions['view_forms'], permissions['create_forms'],
                    permissions['update_forms'], permissions['delete_forms'],
                    permissions['view_questions'], permissions['create_questions'],
                    permissions['update_questions'], permissions['delete_questions'],
                    permissions['view_question_types'], permissions['create_question_types'],
                    permissions['update_question_types'], permissions['delete_question_types'],
                    permissions['view_answers'], permissions['create_answers'],
                    permissions['update_answers'], permissions['delete_answers'],
                    permissions['view_submissions'], permissions['create_submissions'],
                    permissions['update_submissions'], permissions['delete_submissions'],
                    permissions['view_attachments'], permissions['create_attachments'],
                    permissions['update_attachments'], permissions['delete_attachments']
                ]
            },
            'Supervisor': {
                'description': 'Supervisor with form management capabilities',
                'is_super_user': False,
                'permissions': [
                    permissions['view_forms'], permissions['create_forms'],
                    permissions['update_forms'], permissions['delete_forms'],
                    permissions['view_questions'], permissions['create_questions'],
                    permissions['update_questions'], permissions['delete_questions'],
                    permissions['view_question_types'], permissions['create_question_types'],
                    permissions['update_question_types'], permissions['delete_question_types'],
                    permissions['view_answers'], permissions['create_answers'],
                    permissions['update_answers'], permissions['delete_answers'],
                    permissions['view_submissions'], permissions['create_submissions'],
                    permissions['update_submissions'], permissions['delete_submissions'],
                    permissions['view_attachments'], permissions['create_attachments'],
                    permissions['update_attachments'], permissions['delete_attachments']
                ]
            },
            'Technician': {
                'description': 'Technical user with limited form access',
                'is_super_user': False,
                'permissions': [
                    permissions['view_public_forms'],
                    permissions['view_questions'],
                    permissions['view_question_types'],
                    permissions['view_answers'],
                    permissions['create_submissions'],
                    permissions['view_own_submissions'],
                    permissions['update_own_submissions'],
                    permissions['delete_own_submissions'],
                    permissions['create_attachments'],
                    permissions['view_own_attachments'],
                    permissions['update_own_attachments'],
                    permissions['delete_own_attachments']
                ]
            }
        }

        created_roles = []
        for role_name, details in roles_config.items():
            role = Role.query.filter_by(name=role_name).first()
            if role:
                role.description = details['description']
                role.is_super_user = details['is_super_user']
                role.updated_at = datetime.utcnow()
                # Update permissions
                role.permissions = details['permissions']
                logger.info(f"Updated role: {role_name}")
            else:
                role = Role(
                    name=role_name,
                    description=details['description'],
                    is_super_user=details['is_super_user'],
                    permissions=details['permissions']
                )
                db.session.add(role)
                logger.info(f"Created role: {role_name}")
            
            created_roles.append(role)
        
        try:
            db.session.commit()
            return created_roles
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating roles: {str(e)}")
            raise

    def init_admin_environment(self):
        """Initialize or update ADMIN environment."""
        env = Environment.query.filter_by(name="ADMIN").first()
        if not env:
            env = Environment(
                name="ADMIN",
                description="System Administration Environment"
            )
            db.session.add(env)
            logger.info("ADMIN environment created")
        else:
            env.description = "System Administration Environment"
            env.updated_at = datetime.utcnow()
            logger.info("ADMIN environment updated")
        return env

    def init_admin_user(self, role, env, admin_credentials):
        """Initialize or update admin user with provided credentials."""
        user = User.query.filter_by(username=admin_credentials['username']).first()
        
        if user:
            print(f"\n⚠️  Warning: User '{admin_credentials['username']}' already exists")
            if input("Do you want to update this user? (y/n): ").lower() != 'y':
                return user

        if not user:
            user = User(
                username=admin_credentials['username'],
                email=admin_credentials['email'],
                first_name=admin_credentials['first_name'],
                last_name=admin_credentials['last_name'],
                role_id=role.id,
                environment_id=env.id
            )
            db.session.add(user)
            logger.info("Admin user created")
        else:
            user.email = admin_credentials['email']
            user.first_name = admin_credentials['first_name']
            user.last_name = admin_credentials['last_name']
            user.role_id = role.id
            user.environment_id = env.id
            user.updated_at = datetime.utcnow()
            logger.info("Admin user updated")
        
        user.set_password(admin_credentials['password'])
        return user

    def init_db(self, check_empty=True):
        try:
            with self.app.app_context():
                if check_empty:
                    admin_role = Role.query.filter_by(is_super_user=True).first()
                    if admin_role and User.query.filter_by(role_id=admin_role.id).first():
                        logger.info("Admin user already exists. Skipping initialization.")
                        return True, None

                admin_credentials = self.prompt_admin_credentials()

                print("\n🚀 Starting database initialization...")
                
                print("\n1️⃣  Initializing permissions...")
                self.init_permissions()
                print("✅ Permissions initialized successfully")
                
                print("\n2️⃣  Initializing roles...")
                roles = self.init_roles()
                admin_role = next(role for role in roles if role.name == 'Admin')
                print("✅ Roles and permissions assigned successfully")
                
                print("\n3️⃣  Initializing admin environment...")
                env = self.init_admin_environment()
                print("✅ Admin environment initialized successfully")
                
                db.session.commit()
                
                print("\n4️⃣  Creating admin user...")
                user = self.init_admin_user(admin_role, env, admin_credentials)
                print("✅ Admin user initialized successfully")
                
                db.session.commit()
                
                print("\n✅ Database initialization completed successfully!")
                print("\nRole and Permission Summary:")
                for role in roles:
                    print(f"\n👤 {role.name}:")
                    print(f"   Description: {role.description}")
                    print(f"   Permissions: {len(role.permissions)}")
                
                print(f"\nYou can now login with:")
                print(f"Username: {admin_credentials['username']}")
                print("Password: *********")
                
                return True, None
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error during database initialization: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

def init_database():
    """Convenience function to run database initialization."""
    print("\n🔧 CMMS Database Initialization")
    print("==============================")
    
    try:
        from app import create_app
        app = create_app()
        initializer = DatabaseInitializer(app)
        success, error = initializer.init_db()
        
        if success:
            print("\n🎉 Success! Database has been initialized successfully.")
        else:
            print(f"\n❌ Error: {error}")
            print("Please check the logs for more details.")
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        print("Please check the logs for more details.")

if __name__ == "__main__":
    init_database()