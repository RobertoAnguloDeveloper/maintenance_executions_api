# app/controllers/entity_basic_controller.py

from app.services.entity_basic_service import EntityBasicService
import logging

logger = logging.getLogger(__name__)

class EntityBasicController:
    """Controller for handling basic entity requests"""
    
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
        logger.info(f"Getting all entities basic data (include_deleted={include_deleted}, page={page}, per_page={per_page})")
        return EntityBasicService.get_all_entities_basic(include_deleted, page, per_page)
    
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
        logger.info(f"Getting {entity_type} basic data (include_deleted={include_deleted}, page={page}, per_page={per_page})")
        return EntityBasicService.get_entity_basic(entity_type, include_deleted, page, per_page)
    
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
        logger.info(f"Getting {entity_type} {entity_id} basic data (include_deleted={include_deleted})")
        return EntityBasicService.get_entity_by_id_basic(entity_type, entity_id, include_deleted)
        
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
        logger.info(f"Getting {entity_type} by IDs {entity_ids} basic data (include_deleted={include_deleted})")
        return EntityBasicService.get_entities_by_ids_basic(entity_type, entity_ids, include_deleted)