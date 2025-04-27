from flask_jwt_extended import create_access_token, get_jwt, decode_token
from werkzeug.security import check_password_hash
from app.models.user import User
import logging
import json
import base64
from jwt.exceptions import PyJWTError

logger = logging.getLogger(__name__)

class AuthService:
    @staticmethod
    def authenticate_user(username, password):
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            # Include role in token
            additional_claims = {
                'role': user.role.name,
                'is_super_user': user.role.is_super_user
            }
            access_token = create_access_token(
                identity=username,
                additional_claims=additional_claims
            )
            return access_token
        return None

    @staticmethod
    def get_current_user(username):
        return User.query.filter_by(username=username).first()
    
    @staticmethod
    def extract_user_info_from_token(token):
        """
        Extract user identity from JWT token
        
        Args:
            token (str): Raw JWT token string
            
        Returns:
            dict: Dictionary containing extracted user info or empty dict if extraction fails
        """
        if not token:
            return {}
            
        try:
            # First try the standard way using flask-jwt-extended
            from flask_jwt_extended import decode_token
            try:
                decoded = decode_token(token)
                # For internal tokens
                result = {
                    'sub': decoded.get('sub', None),
                    'identity': decoded.get('sub', None),
                    'is_internal': True
                }
                return result
            except:
                # If that fails, try manual decoding for external tokens
                pass
                
            # Manual decoding for external tokens
            token_parts = token.split('.')
            if len(token_parts) >= 2:
                # Handle padding for base64 decoding
                payload = token_parts[1]
                payload += '=' * (4 - len(payload) % 4)
                
                try:
                    decoded = json.loads(base64.b64decode(payload))
                    
                    # Extract all potentially useful identity fields
                    result = {
                        'is_internal': False,
                        'sub': decoded.get('sub', None),
                        'username': decoded.get('username', None),
                        'preferred_username': decoded.get('preferred_username', None),
                        'user_name': decoded.get('user_name', None),
                        'email': decoded.get('email', None),
                        'name': decoded.get('name', None),
                        'full_name': decoded.get('full_name', None),
                        'first_name': decoded.get('first_name', None),
                        'last_name': decoded.get('last_name', None)
                    }
                    
                    # Determine best identity field to use
                    for field in ['username', 'preferred_username', 'user_name', 'sub']:
                        if result.get(field):
                            result['identity'] = result[field]
                            return result
                            
                    # Try email as fallback
                    if result.get('email'):
                        result['identity'] = result['email']
                    
                    return result
                        
                except Exception as e:
                    logger.debug(f"Error decoding token payload: {str(e)}")
                    
            return {}
        except Exception as e:
            logger.debug(f"Error extracting user info from token: {str(e)}")
            return {}
        
    @staticmethod
    def lookup_user_from_token_info(token_info):
        """
        Look up user in database from token info
        
        Args:
            token_info (dict): Dictionary of token information
            
        Returns:
            User: User instance or None
        """
        if not token_info or not isinstance(token_info, dict):
            return None
            
        # For internal tokens, we can directly find by username
        if token_info.get('is_internal') and token_info.get('identity'):
            return User.query.filter_by(username=token_info['identity']).first()
            
        # For external tokens, try various fields
        queries = []
        
        # Try username fields
        if token_info.get('username'):
            queries.append(User.username == token_info['username'])
            
        if token_info.get('preferred_username'):
            queries.append(User.username == token_info['preferred_username'])
            
        if token_info.get('user_name'):
            queries.append(User.username == token_info['user_name'])
            
        # Try email
        if token_info.get('email'):
            queries.append(User.email == token_info['email'])
            
        # Try name matching
        if token_info.get('full_name') and ' ' in token_info['full_name']:
            parts = token_info['full_name'].split(' ', 1)
            if len(parts) == 2:
                first, last = parts
                queries.append((User.first_name == first) & (User.last_name == last))
                
        if token_info.get('first_name') and token_info.get('last_name'):
            queries.append((User.first_name == token_info['first_name']) & 
                          (User.last_name == token_info['last_name']))
                
        # Try each query until we find a match
        from sqlalchemy import or_
        if queries:
            return User.query.filter(or_(*queries)).first()
            
        return None
        
    @staticmethod
    def logout_user(token=None, username=None):
        """
        Handle user logout with enhanced token extraction
        
        Args:
            token (str): Raw JWT token (optional)
            username (str): Username of the user logging out (optional)
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # If we have a username directly provided
            if username:
                user = User.query.filter_by(username=username).first()
                if user:
                    logger.info(f"User {username} logged out successfully")
                    return True, "Successfully logged out"
            
            # Try to extract user info from token if provided
            if token:
                token_info = AuthService.extract_user_info_from_token(token)
                
                # Try to find user in our database
                if token_info:
                    user = AuthService.lookup_user_from_token_info(token_info)
                    
                    if user:
                        # We found a matching user in our system
                        logger.info(f"User {user.username} logged out successfully")
                        return True, "Successfully logged out"
                    
                    # Get best username to log from token info
                    identity = (token_info.get('identity') or 
                               token_info.get('username') or 
                               token_info.get('preferred_username') or 
                               token_info.get('user_name') or 
                               token_info.get('sub'))
                    
                    if identity:
                        # External user
                        logger.info(f"External user with identity '{identity}' logged out successfully")
                        return True, "Successfully logged out"
            
            # Default success even if we couldn't identify the user
            logger.info("Anonymous user logged out successfully")
            return True, "Successfully logged out"
            
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")
            return False, "Error processing logout"