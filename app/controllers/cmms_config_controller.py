from typing import Dict, List, Optional, Tuple, Union
from flask import current_app
import logging
from app.services.cmms_config_service import CMMSConfigService
from werkzeug.datastructures import FileStorage
import json

logger = logging.getLogger(__name__)

class CMMSConfigController:
    @staticmethod
    def create_config(
        filename: str,
        content: Union[str, dict, bytes],
        current_user: str
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """Create a new CMMS configuration file"""
        try:
            if not current_user:
                return None, "User not authenticated"

            # Convert content to bytes if it's a dict or str
            if isinstance(content, dict):
                content = json.dumps(content, indent=2).encode('utf-8')
            elif isinstance(content, str):
                content = content.encode('utf-8')
            elif not isinstance(content, bytes):
                return None, "Content must be string, dict or bytes"

            # Initialize service with base path (uploads folder)
            service = CMMSConfigService(current_app.config['UPLOAD_FOLDER'])
            
            # Create config file
            config, error = service.create_config(filename, content, current_user)
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
        """Upload a CMMS configuration file"""
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
        """Load a CMMS configuration file"""
        try:
            if not current_user:
                return None, "User not authenticated"
                
            service = CMMSConfigService(current_app.config['UPLOAD_FOLDER'])
            
            # Load file
            config, error = service.load_config(filename)
            if error:
                return None, error
                
            logger.info(f"Config file {filename} loaded by user {current_user}")
            return config, None
            
        except Exception as e:
            logger.error(f"Error in load_config controller: {str(e)}")
            return None, str(e)
        
    @staticmethod
    def find_file(
        filename: str,
        current_user: str
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """Find a file in the CMMS directory structure"""
        try:
            if not current_user:
                return None, "User not authenticated"
                
            service = CMMSConfigService(current_app.config['UPLOAD_FOLDER'])
            
            # Find the file
            file_path, error = service.find_file(filename)
            if error:
                return None, error
                
            # Get file information
            file_info = service.get_file_info(file_path)
            
            logger.info(f"File {filename} found and accessed by user {current_user}")
            return file_info, None
            
        except Exception as e:
            logger.error(f"Error finding file: {str(e)}")
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
        """Delete a CMMS configuration file"""
        try:
            service = CMMSConfigService(current_app.config['UPLOAD_FOLDER'])
            
            success, error = service.delete_config(filename, current_user)
            if error:
                return False, error
                
            logger.info(f"Config file {filename} deleted by user {current_user}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error in delete_config controller: {str(e)}")
            return False, str(e)
            
    @staticmethod
    def check_config_file() -> Tuple[bool, Dict]:
        """Check if configuration file exists in the configs folder."""
        try:
            service = CMMSConfigService(current_app.config['UPLOAD_FOLDER'])
            exists, metadata = service.check_config_file()
            
            if exists:
                logger.info(f"Configuration file found at: {metadata['full_path']}")
            else:
                logger.info(f"Configuration file not found. Expected at: {metadata['expected_path']}")
            
            return exists, metadata
            
        except Exception as e:
            logger.error(f"Error in check_config_file controller: {str(e)}")
            return False, {"error": str(e)}