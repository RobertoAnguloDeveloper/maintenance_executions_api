# app/services/entity_basic_service.py

from app import db
from app.models.answer import Answer
from app.models.answer_submitted import AnswerSubmitted
from app.models.attachment import Attachment
from app.models.environment import Environment
from app.models.form import Form
from app.models.form_answer import FormAnswer
from app.models.form_question import FormQuestion
from app.models.form_submission import FormSubmission
from app.models.permission import Permission
from app.models.question import Question
from app.models.question_type import QuestionType
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.services.base_service import BaseService
from sqlalchemy.orm import joinedload
import logging

logger = logging.getLogger(__name__)

class EntityBasicService(BaseService):
    """Service for retrieving basic entity information"""
    
    # Mapping of entity names to model classes
    ENTITY_MODELS = {
        'answers': Answer,
        'answers_submitted': AnswerSubmitted,
        'attachments': Attachment,
        'environments': Environment,
        'forms': Form,
        'form_answers': FormAnswer,
        'form_questions': FormQuestion,
        'form_submissions': FormSubmission,
        'permissions': Permission,
        'questions': Question,
        'question_types': QuestionType,
        'roles': Role,
        'role_permissions': RolePermission,
        'users': User
    }
    
    def __init__(self):
        super().__init__(None)  # No default model
    
    @staticmethod
    def get_all_entities_basic(include_deleted=False, page=1, per_page=20):
        """
        Get basic representations of all entities
        
        Args:
            include_deleted (bool): Whether to include soft-deleted entities
            page (int): Page number for pagination
            per_page (int): Number of items per page
            
        Returns:
            tuple: (response_data, status_code)
        """
        try:
            result = {}
            
            for entity_name, model_class in EntityBasicService.ENTITY_MODELS.items():
                # Get query based on include_deleted parameter
                if include_deleted:
                    query = model_class.query
                else:
                    # Only include non-deleted items if the model has is_deleted attribute
                    if hasattr(model_class, 'is_deleted'):
                        query = model_class.query.filter_by(is_deleted=False)
                    else:
                        query = model_class.query
                
                # Apply pagination
                paginated = query.paginate(page=page, per_page=per_page, error_out=False)
                
                # Convert entities to their basic dictionary representation
                entity_list = [entity.to_dict_basic() for entity in paginated.items]
                
                # Add pagination metadata
                result[entity_name] = {
                    'data': entity_list,
                    'pagination': {
                        'total': paginated.total,
                        'pages': paginated.pages,
                        'page': page,
                        'per_page': per_page,
                        'has_next': paginated.has_next,
                        'has_prev': paginated.has_prev
                    }
                }
            
            return result, 200
            
        except Exception as e:
            logger.error(f"Error getting all entities basic data: {str(e)}")
            return {"error": f"Failed to retrieve entities: {str(e)}"}, 500
    
    @staticmethod
    def get_entity_basic(entity_type, include_deleted=False, page=1, per_page=20):
        """
        Get basic representations of a specific entity type
        
        Args:
            entity_type (str): Type of entity to retrieve (e.g., 'users', 'forms')
            include_deleted (bool): Whether to include soft-deleted entities
            page (int): Page number for pagination
            per_page (int): Number of items per page
            
        Returns:
            tuple: (response_data, status_code)
        """
        try:
            # Check if entity type exists
            if entity_type not in EntityBasicService.ENTITY_MODELS:
                return {"error": f"Entity type '{entity_type}' not found"}, 404
            
            model_class = EntityBasicService.ENTITY_MODELS[entity_type]
            
            # Get query based on include_deleted parameter
            if include_deleted:
                query = model_class.query
            else:
                # Only include non-deleted items if the model has is_deleted attribute
                if hasattr(model_class, 'is_deleted'):
                    query = model_class.query.filter_by(is_deleted=False)
                else:
                    query = model_class.query
            
            # Apply pagination
            paginated = query.paginate(page=page, per_page=per_page, error_out=False)
            
            # Convert entities to their basic dictionary representation
            entity_list = [entity.to_dict_basic() for entity in paginated.items]
            
            # Add pagination metadata
            result = {
                'metadata': {
                    'total_items': paginated.total,
                    'total_pages': paginated.pages,
                    'current_page': page,
                    'per_page': per_page,
                    'has_next': paginated.has_next,
                    'has_prev': paginated.has_prev
                },
                'items': entity_list
            }
            
            return result, 200
            
        except Exception as e:
            logger.error(f"Error getting {entity_type} basic data: {str(e)}")
            return {"error": f"Failed to retrieve {entity_type}: {str(e)}"}, 500
            
    @staticmethod
    def get_entity_by_id_basic(entity_type, entity_id, include_deleted=False):
        """
        Get basic representation of a specific entity by ID
        
        Args:
            entity_type (str): Type of entity to retrieve (e.g., 'users', 'forms')
            entity_id (int): ID of the entity to retrieve
            include_deleted (bool): Whether to include soft-deleted entities
            
        Returns:
            tuple: (response_data, status_code)
        """
        try:
            # Check if entity type exists
            if entity_type not in EntityBasicService.ENTITY_MODELS:
                return {"error": f"Entity type '{entity_type}' not found"}, 404
            
            model_class = EntityBasicService.ENTITY_MODELS[entity_type]
            
            # Get entity by ID
            entity = model_class.query.get(entity_id)
            
            if not entity:
                return {"error": f"{entity_type.capitalize()} with ID {entity_id} not found"}, 404
            
            # Check if entity is deleted and include_deleted is False
            if hasattr(entity, 'is_deleted') and entity.is_deleted and not include_deleted:
                return {"error": f"{entity_type.capitalize()} with ID {entity_id} is deleted"}, 404
            
            # Convert entity to basic dictionary representation
            return entity.to_dict_basic(), 200
            
        except Exception as e:
            logger.error(f"Error getting {entity_type} {entity_id} basic data: {str(e)}")
            return {"error": f"Failed to retrieve {entity_type} {entity_id}: {str(e)}"}, 500
            
    @staticmethod
    def get_entities_by_ids_basic(entity_type, entity_ids, include_deleted=False):
        """
        Get basic representations of multiple entities by their IDs
        
        Args:
            entity_type (str): Type of entity to retrieve
            entity_ids (list): List of entity IDs to retrieve
            include_deleted (bool): Whether to include soft-deleted entities
            
        Returns:
            tuple: (response_data, status_code)
        """
        try:
            # Check if entity type exists
            if entity_type not in EntityBasicService.ENTITY_MODELS:
                return {"error": f"Entity type '{entity_type}' not found"}, 404
            
            model_class = EntityBasicService.ENTITY_MODELS[entity_type]
            
            # Get query based on include_deleted parameter
            query = model_class.query.filter(model_class.id.in_(entity_ids))
            
            if not include_deleted and hasattr(model_class, 'is_deleted'):
                query = query.filter_by(is_deleted=False)
            
            # Get entities
            entities = query.all()
            
            # Convert entities to basic dictionary representation
            result = {
                'items': [entity.to_dict_basic() for entity in entities],
                'count': len(entities)
            }
            
            return result, 200
            
        except Exception as e:
            logger.error(f"Error getting {entity_type} by IDs basic data: {str(e)}")
            return {"error": f"Failed to retrieve {entity_type} by IDs: {str(e)}"}, 500