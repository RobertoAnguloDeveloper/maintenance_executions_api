from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash
from app.models.user import User

class AuthService:
    @staticmethod
    def authenticate_user(username, password):
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            access_token = create_access_token(identity=username)
            return access_token
        return None

    @staticmethod
    def get_current_user(username):
        return User.query.filter_by(username=username).first()