# app/controllers/cmms_config_controller.py

from typing import Dict, List, Optional, Tuple, Union
from flask import current_app
import logging
from app.services.cmms_config_service import CMMSConfigService
from werkzeug.datastructures import FileStorage

logger = logging.getLogger(__name__)

class CMMSConfigController:
    @staticmethod
    def create_config(
        filename: str,
        content: Dict,
        current_user: str
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """Create a new CMMS configuration JSON file"""
        try:
            # Initialize service with upload path
            service = CMMSConfigService(current_app.config['UPLOAD_FOLDER'])
            
            # Create config file
            config, error = service.create_config(filename, content)
            if error:
                return None, error
                
            logger.info(f"Config file {filename} created by user {current_user}")
            return config, None
            
        except Exception as e:
            logger.error(f"Error in create_config controller: {str(e)}")
            return None, str(e)
            
    @staticmethod
    def upload_config(
        file: FileStorage,
        filename: str,
        current_user: str
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """Upload a CMMS configuration JSON file"""
        try:
            if not file:
                return None, "No file provided"
                
            service = CMMSConfigService(current_app.config['UPLOAD_FOLDER'])
            
            config, error = service.upload_config(file, filename)
            if error:
                return None, error
                
            logger.info(f"Config file {filename} uploaded by user {current_user}")
            return config, None
            
        except Exception as e:
            logger.error(f"Error in upload_config controller: {str(e)}")
            return None, str(e)
            
    @staticmethod
    def load_config(
        filename: str,
        current_user: str
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """Load a CMMS configuration JSON file"""
        try:
            service = CMMSConfigService(current_app.config['UPLOAD_FOLDER'])
            
            config, error = service.load_config(filename)
            if error:
                return None, error
                
            logger.info(f"Config file {filename} loaded by user {current_user}")
            return config, None
            
        except Exception as e:
            logger.error(f"Error in load_config controller: {str(e)}")
            return None, str(e)
            
    @staticmethod
    def rename_config(
        old_filename: str,
        new_filename: str,
        current_user: str
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """Rename a CMMS configuration JSON file"""
        try:
            service = CMMSConfigService(current_app.config['UPLOAD_FOLDER'])
            
            result, error = service.rename_config(old_filename, new_filename)
            if error:
                return None, error
                
            logger.info(f"Config file {old_filename} renamed to {new_filename} by user {current_user}")
            return result, None
            
        except Exception as e:
            logger.error(f"Error in rename_config controller: {str(e)}")
            return None, str(e)
            
    @staticmethod
    def delete_config(
        filename: str,
        current_user: str
    ) -> Tuple[bool, Optional[str]]:
        """Delete a CMMS configuration JSON file"""
        try:
            service = CMMSConfigService(current_app.config['UPLOAD_FOLDER'])
            
            success, error = service.delete_config(filename)
            if error:
                return False, error
                
            logger.info(f"Config file {filename} deleted by user {current_user}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error in delete_config controller: {str(e)}")
            return False, str(e)