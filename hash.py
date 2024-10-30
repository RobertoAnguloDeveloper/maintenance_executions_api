from app import create_app, db
from app.models.user import User
from app.models.role import Role
from app.models.environment import Environment
from datetime import datetime

app = create_app()
with app.app_context():
    # Create or update Role
    role = Role.query.filter_by(name="Super admin").first()
    if not role:
        role = Role(name="Super admin", description="Can create all", is_super_user=True)
        db.session.add(role)
        print("Super admin role created")
    else:
        role.description = "Can create all"
        role.is_super_user = True
        role.updated_at = datetime.utcnow()
        print("Super admin role updated")

    # Create or update Environment
    env = Environment.query.filter_by(name="ADMIN").first()
    if not env:
        env = Environment(name="ADMIN", description="Only administrators")
        db.session.add(env)
        print("ADMIN environment created")
    else:
        env.description = "Only administrators"
        env.updated_at = datetime.utcnow()
        print("ADMIN environment updated")

    # Commit to ensure Role and Environment have IDs
    db.session.commit()

    # Create or update User
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
        print("Admin user created")
    else:
        user.first_name = "ADMIN"
        user.last_name = "ADMIN"
        user.email = "dataanalyst-2@plgims.com"
        user.role_id = role.id
        user.environment_id = env.id
        user.updated_at = datetime.utcnow()
        print("Admin user updated")

    # Set or update password
    user.set_password('123')
    
    # Commit all changes
    db.session.commit()
    print("Admin user and password set/updated successfully")