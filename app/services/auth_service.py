from datetime import datetime, timezone
from flask_jwt_extended import create_access_token
from flask_jwt_extended.utils import decode_token as jwt_decode_token
from psycopg2 import IntegrityError
from werkzeug.security import check_password_hash
from app.models.token_blocklist import TokenBlocklist
from app.models.user import User
import logging
import json
import base64
from jwt.exceptions import PyJWTError
from app import db

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
    def add_jti_to_blocklist(jti: str) -> bool:
         """Adds a JTI to the blocklist database."""
         logger.debug(f"Attempting to add JTI to blocklist: {jti}") # DEBUG log
         try:
             blocked_token = TokenBlocklist(
                 jti=jti,
                 created_at=datetime.now(timezone.utc)
             )
             db.session.add(blocked_token)
             db.session.commit()
             logger.info(f"Successfully added JTI to blocklist: {jti}") # INFO on success
             return True
         except IntegrityError:
             db.session.rollback()
             logger.warning(f"Attempted to add duplicate JTI to blocklist: {jti}. Considered success.") # WARN duplicate
             return True # Treat as success if already blocked
         except Exception as e:
             db.session.rollback()
             # Log the full error if DB commit fails
             logger.error(f"Database error adding JTI {jti} to blocklist: {e}", exc_info=True) # ERROR with traceback
             return False

    @staticmethod
    def logout_user(token=None, username=None):
        """
        Handle user logout by adding token JTI to blocklist if a valid token is provided.
        """
        logger.debug(f"Logout request received. Token provided: {'Yes' if token else 'No'}") # DEBUG log
        try:
            if token:
                try:
                    logger.debug("Attempting to decode token for JTI...") # DEBUG log
                    decoded_token = jwt_decode_token(token)
                    jti = decoded_token.get('jti')
                    identity = decoded_token.get('sub', username)
                    logger.debug(f"Decoded token. JTI: {jti}, Identity: {identity}") # DEBUG log

                    if jti:
                        if AuthService.add_jti_to_blocklist(jti):
                            logger.info(f"User {identity or 'Unknown'} logged out successfully (Token {jti} blocklisted).")
                            return True, "Successfully logged out and token blocklisted."
                        else:
                            # Blocklist add failed (error logged in add_jti_to_blocklist)
                            return True, "Logout successful (server blocklist error)." # Still True for client
                    else:
                        logger.warning("Could not extract JTI from provided token during logout.")
                        return True, "Successfully logged out (JTI missing)." # Client still logs out

                except PyJWTError as e:
                    logger.warning(f"Invalid/Expired token provided during logout: {e}. Relying on client to clear token.")
                    return True, "Successfully logged out (token invalid)."
            else:
                 logger.info("Logout endpoint called without token. Relying on client.")
                 return True, "Successfully logged out."

        except Exception as e:
            logger.error(f"Unexpected error during logout processing: {str(e)}", exc_info=True)
            return True, "Successfully logged out (server error during processing)."