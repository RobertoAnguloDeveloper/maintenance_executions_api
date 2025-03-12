import logging
import getpass
from app.models.permission import Permission
from app.models.question_type import QuestionType
from app.utils.helpers import validate_email
import re
from app import db
from app.models.user import User
from app.models.role import Role
from app.models.environment import Environment
from datetime import datetime
from sqlalchemy import text

logger = logging.getLogger(__name__)

class DatabaseInitializer:
    def ensure_database_exists(self):
        """Ensure database and required extensions exist."""
        try:
            with self.app.app_context():
                db.engine.connect()
                
                # Create extensions if they don't exist using SQLAlchemy text()
                db.session.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
                db.session.commit()
                
                return True, None
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            return False, str(e)
    
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
        """Initialize or update all permissions with clear categorization."""
        permissions_config = {
            # User Management
            'view_users': 'Can view users within their environment',
            'create_users': 'Can create users within their environment',
            'update_users': 'Can update users within their environment',
            'delete_users': 'Can delete users within their environment',
            
            # Environment Management
            'view_environments': 'Can view environments',
            'create_environments': 'Can create environments',
            'update_environments': 'Can update all environments',
            'delete_environments': 'Can delete environments',
            
            # Role Management
            'view_roles': 'Can view roles within their environment',
            'create_roles': 'Can create roles within their environment',
            'update_roles': 'Can update roles within their environment',
            'delete_roles': 'Can delete roles within their environment',
            
            # Permission Management
            'view_permissions': 'Can view permissions within their environment',
            'create_permissions': 'Can create permissions within their environment',
            'update_permissions': 'Can update permissions within their environment',
            'delete_permissions': 'Can delete permissions within their environment',
            
            # Role Permission Management
            'view_role_permissions': 'Can view role_permissions within their environment',
            'create_role_permissions': 'Can create role_permissions within their environment',
            'update_role_permissions': 'Can update role_permissions within their environment',
            'delete_role_permissions': 'Can delete role_permissions within their environment',
            
            # Form Management
            'view_forms': 'Can view forms within their environment',
            'create_forms': 'Can create forms within their environment',
            'update_forms': 'Can update forms within their environment',
            'delete_forms': 'Can delete forms within their environment',
            
            # Question Management
            'view_questions': 'Can view questions',
            'create_questions': 'Can create questions within their environment',
            'update_questions': 'Can update questions within their environment',
            'delete_questions': 'Can delete questions within their environment',
            
            # Form Question Management
            'view_form_questions': 'Can view form_questions',
            'create_form_questions': 'Can create form_questions within their environment',
            'update_form_questions': 'Can update form_questions within their environment',
            'delete_form_questions': 'Can delete form_questions within their environment',
            
            # Question Type Management
            'view_question_types': 'Can view question types',
            'create_question_types': 'Can create question types',
            'update_question_types': 'Can update question types',
            'delete_question_types': 'Can delete question types',
            
            # Answer Management
            'view_answers': 'Can view answers within their environment',
            'create_answers': 'Can create answers within their environment',
            'update_answers': 'Can update answers within their environment',
            'delete_answers': 'Can delete answers within their environment',
            
            # Form Answer Management
            'view_form_answers': 'Can view form_answers',
            'create_form_answers': 'Can create form_answers within their environment',
            'update_form_answers': 'Can update form_answers within their environment',
            'delete_form_answers': 'Can delete form_answers within their environment',
            
            # Answer Submitted Management
            'view_answers_submitted': 'Can view answers_submitted',
            'create_answers_submitted': 'Can create answers_submitted within their environment',
            'update_answers_submitted': 'Can update answers_submitted within their environment',
            'delete_answers_submitted': 'Can delete answers_submitted within their environment',
            
            # Form Submission Management
            'view_form_submissions': 'Can view form submissions within their environment',
            'create_form_submissions': 'Can create form submissions',
            'update_form_submissions': 'Can update submissions within their environment',
            'delete_form_submissions': 'Can delete submissions within their environment',
            
            # Attachment Management
            'view_attachments': 'Can view attachments within their environment',
            'create_attachments': 'Can create attachments',
            'update_attachments': 'Can update attachments within their environment',
            'delete_attachments': 'Can delete attachments within their environment',
        }

        # Valid actions and entities based on requirements
        valid_actions = ["create", "update", "view", "delete"]
        valid_entities = [
            "users", "environments", "roles", "permissions", "role_permissions",
            "forms", "form_questions", "questions", "question_types", 
            "form_submissions", "form_answers", "answers", "answers_submitted", 
            "attachments"
        ]

        created_permissions = []
        for perm_name, description in permissions_config.items():
            # Parse action and entity from permission name
            parts = perm_name.split('_', 1)
            
            # Default values
            action = "view"  # Default action
            entity = "users"  # Default entity
            
            if len(parts) == 2:
                action_part, entity_part = parts
                
                # Validate action
                if action_part in valid_actions:
                    action = action_part
                
                # Handle special cases and validate entity
                if entity_part == "all_users":
                    entity = "users"
                elif entity_part == "public_forms":
                    entity = "forms"
                elif entity_part == "own_submissions":
                    entity = "form_submissions"
                elif entity_part == "own_attachments":
                    entity = "attachments"
                elif entity_part in valid_entities:
                    entity = entity_part
                elif entity_part.endswith('s') and entity_part[:-1] in valid_entities:
                    entity = entity_part
                
            # Handle special cases that don't follow the pattern
            if perm_name.startswith('manage_'):
                action = "update"  # manage implies update capability
                entity_part = perm_name.split('_', 1)[1]
                if entity_part == "all_users":
                    entity = "users"
                elif entity_part == "all_forms":
                    entity = "forms"
                elif entity_part == "environments":
                    entity = "environments"

            permission = Permission.query.filter_by(name=perm_name).first()
            if permission:
                permission.description = description
                permission.action = action
                permission.entity = entity
                permission.updated_at = datetime.utcnow()
                logger.info(f"Updated permission: {perm_name} with action={action}, entity={entity}")
            else:
                permission = Permission(
                    name=perm_name,
                    description=description,
                    action=action,
                    entity=entity
                )
                db.session.add(permission)
                logger.info(f"Created permission: {perm_name} with action={action}, entity={entity}")
            
            created_permissions.append(permission)
        
        try:
            db.session.commit()
            return created_permissions
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating permissions: {str(e)}")
            raise

    def init_roles(self):
        """Initialize or update all roles with carefully defined permission sets."""
        # Get all permissions first
        permissions = {p.name: p for p in self.init_permissions()}
        
        roles_config = {
            'Admin': {
                'description': 'Full system administrator with unrestricted access',
                'is_super_user': True,
                'permissions': list(permissions.values())  # Admin gets all permissions
            },
            'Site Manager': {
                'description': 'Manager with full access within their environment',
                'is_super_user': False,
                'permissions': [
                    # User Management - Limited to viewing within environment
                    permissions['view_users'],
                    
                    # Form Management - Full access within environment
                    permissions['view_forms'],
                    permissions['create_forms'],
                    permissions['update_forms'],
                    permissions['delete_forms'],
                    
                    # Question Management
                    permissions['view_questions'],
                    permissions['create_questions'],
                    permissions['update_questions'],
                    permissions['delete_questions'],
                    
                    # Form Question Management
                    permissions['view_form_questions'],
                    permissions['create_form_questions'],
                    permissions['update_form_questions'],
                    permissions['delete_form_questions'],
                    
                    # Question Type Management
                    permissions['view_question_types'],
                    
                    # Answer Management
                    permissions['view_answers'],
                    permissions['create_answers'],
                    permissions['update_answers'],
                    permissions['delete_answers'],
                    
                    # Form Answer Management
                    permissions['view_form_answers'],
                    permissions['create_form_answers'],
                    permissions['update_form_answers'],
                    permissions['delete_form_answers'],
                    
                    # Answer Submitted Management
                    permissions['view_answers_submitted'],
                    permissions['create_answers_submitted'],
                    permissions['update_answers_submitted'],
                    
                    # Form Submission Management
                    permissions['view_form_submissions'],
                    permissions['create_form_submissions'],
                    permissions['update_form_submissions'],
                    
                    # Attachment Management
                    permissions['view_attachments'],
                    permissions['create_attachments'],
                    permissions['update_attachments'],
                    
                    # Environment Access
                    permissions['view_environments']
                ]
            },
            'Supervisor': {
                'description': 'Supervisor with form management capabilities',
                'is_super_user': False,
                'permissions': [
                    # User Management - Limited to viewing within environment
                    permissions['view_users'],
                    
                    # Form Management
                    permissions['view_forms'],
                    
                    # Question Management
                    permissions['view_questions'],

                    # Question Type Management
                    permissions['view_question_types'],
                    
                    # Answer Management
                    permissions['view_answers'],
                    
                    # Answer Submitted Management
                    permissions['view_answers_submitted'],
                    permissions['create_answers_submitted'],
                    
                    # Form Submission Management
                    permissions['view_form_submissions'],
                    permissions['create_form_submissions'],
                    
                    # Attachment Management
                    permissions['view_attachments'],
                    permissions['create_attachments'],
                    
                    # Environment Access
                    permissions['view_environments']
                ]
            },
            'Technician': {
                'description': 'Technical staff with form submission capabilities',
                'is_super_user': False,
                'permissions': [
                    # User Management - Limited to viewing within environment
                    permissions['view_users'],
                    
                    # Form Management
                    permissions['view_forms'],
                    
                    # Question Management
                    permissions['view_questions'],

                    # Question Type Management
                    permissions['view_question_types'],
                    
                    # Answer Management
                    permissions['view_answers'],
                    
                    # Answer Submitted Management
                    permissions['view_answers_submitted'],
                    permissions['create_answers_submitted'],
                    
                    # Form Submission Management
                    permissions['view_form_submissions'],
                    permissions['create_form_submissions'],
                    
                    # Attachment Management
                    permissions['view_attachments'],
                    permissions['create_attachments'],
                    
                    # Environment Access
                    permissions['view_environments']
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
        
    def init_question_types(self):
        """Initialize default question types."""
        try:
            default_types = [
                'text', 'multiple_choices', 
                'checkbox', 'date', 
                'datetime', 'user', 'signature'
            ]
            
            created_types = []
            for type_name in default_types:
                question_type = QuestionType.query.filter_by(type=type_name).first()
                
                if not question_type:
                    question_type = QuestionType(type=type_name)
                    db.session.add(question_type)
                    logger.info(f"Created question type: {type_name}")
                else:
                    # Ensure the type is not marked as deleted
                    if question_type.is_deleted:
                        question_type.is_deleted = False
                        question_type.deleted_at = None
                        question_type.updated_at = datetime.utcnow()
                        logger.info(f"Restored question type: {type_name}")
                    
                created_types.append(question_type)
            
            db.session.commit()
            return True, None
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error initializing question types: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

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
        """Initialize the database with proper error handling and validation."""
        try:
            # First ensure database exists and is accessible
            success, error = self.ensure_database_exists()
            if not success:
                return False, error

            with self.app.app_context():
                # Create all tables
                db.create_all()
                
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
                
                print("\n4️⃣  Initializing question types...")
                success, error = self.init_question_types()
                if not success:
                    return False, error
                print("✅ Question types initialized successfully")
                
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