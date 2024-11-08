# app/utils/exceptions.py

from werkzeug.exceptions import HTTPException

class ValidationError(HTTPException):
    """Custom exception for validation errors"""
    code = 400
    
    def __init__(self, description=None, response=None):
        super().__init__(description=description, response=response)
        self.description = description

class ResourceNotFoundError(HTTPException):
    """Custom exception for resource not found"""
    code = 404
    
    def __init__(self, description=None, response=None):
        super().__init__(description=description, response=response)
        self.description = description

class AuthorizationError(HTTPException):
    """Custom exception for authorization errors"""
    code = 403
    
    def __init__(self, description=None, response=None):
        super().__init__(description=description, response=response)
        self.description = description

class FileValidationError(ValidationError):
    """Custom exception for file validation errors"""
    def __init__(self, description=None, response=None):
        super().__init__(description=description, response=response)