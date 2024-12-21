# app/services/cmms_config_service.py

import os
import hashlib
import json
from typing import Dict, Optional, Tuple, BinaryIO
from datetime import datetime
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger(__name__)

class CMMSConfigService:
    # File size limit: 10MB
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
    
    # Allowed file extensions and their MIME types
    ALLOWED_EXTENSIONS = {
        'json': 'application/json',
        'pdf': 'application/pdf',
        'txt': 'text/plain',
        'csv': 'text/csv',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'xml': 'application/xml',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg'
    }
    
    def __init__(self, base_path: str):
        self.base_path = os.path.join(base_path, 'cmms_configs')
        os.makedirs(self.base_path, exist_ok=True)
        
        self.active_path = os.path.join(self.base_path, 'active')
        self.archive_path = os.path.join(self.base_path, 'archive')
        
        os.makedirs(self.active_path, exist_ok=True)
        os.makedirs(self.archive_path, exist_ok=True)
        
    def _validate_file_extension(self, filename: str) -> bool:
        """Validate if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS
               
    def _validate_file_size(self, file_size: int) -> bool:
        """Validate file size"""
        return file_size <= self.MAX_FILE_SIZE
        
    def _get_file_path(self, filename: str, archived: bool = False) -> str:
        """Get full file path"""
        target_dir = self.archive_path if archived else self.active_path
        return os.path.join(target_dir, secure_filename(filename))
        
    def _compute_hash(self, content: bytes) -> str:
        """Compute SHA-256 hash of file content"""
        return hashlib.sha256(content).hexdigest()
    
    def _get_metadata(self, file_path: str, content_hash: str) -> Dict:
        """Get file metadata"""
        file_stat = os.stat(file_path)
        file_ext = os.path.splitext(file_path)[1].lower()
        
        metadata = {
            "filename": os.path.basename(file_path),
            "path": file_path,
            "size": file_stat.st_size,
            "created_at": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            "content_hash": content_hash,
            "file_type": self.ALLOWED_EXTENSIONS.get(file_ext[1:], 'application/octet-stream')
        }
        
        return metadata
        
    def _validate_json_content(self, content: Dict) -> Tuple[bool, Optional[str]]:
        """Validate JSON configuration content"""
        required_fields = ['name', 'description', 'parameters']
        
        # Check required fields
        for field in required_fields:
            if field not in content:
                return False, f"Missing required field: {field}"
        
        # Validate parameters structure
        if not isinstance(content['parameters'], dict):
            return False, "Parameters must be an object"
            
        # Validate parameter values
        for key, value in content['parameters'].items():
            if not isinstance(key, str):
                return False, "Parameter keys must be strings"
            if not isinstance(value, (str, int, float, bool)):
                return False, f"Invalid value type for parameter: {key}"
                
        return True, None

    def create_config(self, filename: str, content: bytes) -> Tuple[Optional[Dict], Optional[str]]:
        """Create a new CMMS configuration file"""
        try:
            if not self._validate_file_extension(filename):
                return None, f"Invalid file type. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS.keys())}"
                
            if not self._validate_file_size(len(content)):
                return None, f"File size exceeds maximum limit of {self.MAX_FILE_SIZE/1024/1024}MB"
                
            file_path = self._get_file_path(filename)
            
            # Check if file already exists
            if os.path.exists(file_path):
                return None, "Configuration file already exists"
                
            # Write content to file
            with open(file_path, 'wb') as f:
                f.write(content)
                
            content_hash = self._compute_hash(content)
            metadata = self._get_metadata(file_path, content_hash)
            
            return metadata, None
                
        except Exception as e:
            logger.error(f"Error creating config file: {str(e)}")
            return None, str(e)
            
    def upload_config(self, file: BinaryIO, filename: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Upload a CMMS configuration file"""
        try:
            if not self._validate_file_extension(filename):
                return None, f"Invalid file type. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS.keys())}"
                
            # Read file content
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if not self._validate_file_size(file_size):
                return None, f"File size exceeds maximum limit of {self.MAX_FILE_SIZE/1024/1024}MB"
                
            content = file.read()
            file_path = self._get_file_path(filename)
            
            # Write file
            with open(file_path, 'wb') as f:
                f.write(content)
                
            content_hash = self._compute_hash(content)
            metadata = self._get_metadata(file_path, content_hash)
            
            return metadata, None
            
        except Exception as e:
            logger.error(f"Error uploading config file: {str(e)}")
            return None, str(e)
            
    def load_config(self, filename: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Load a CMMS configuration file"""
        try:
            if not self._validate_file_extension(filename):
                return None, f"Invalid file type. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS.keys())}"
                
            file_path = self._get_file_path(filename)
            
            if not os.path.exists(file_path):
                return None, "Configuration file not found"
                
            with open(file_path, 'rb') as f:
                content = f.read()
                
            content_hash = self._compute_hash(content)
            metadata = self._get_metadata(file_path, content_hash)
            metadata['content'] = content
            
            return metadata, None
            
        except Exception as e:
            logger.error(f"Error loading config file: {str(e)}")
            return None, str(e)
            
    def rename_config(self, old_filename: str, new_filename: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Rename a CMMS configuration file"""
        try:
            if not self._validate_file_extension(old_filename) or \
               not self._validate_file_extension(new_filename):
                return None, f"Invalid file type. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS.keys())}"
                
            old_path = self._get_file_path(old_filename)
            new_path = self._get_file_path(new_filename)
            
            if not os.path.exists(old_path):
                return None, "Source file not found"
                
            if os.path.exists(new_path):
                return None, "Destination filename already exists"
                
            # Rename file
            os.rename(old_path, new_path)
            
            with open(new_path, 'rb') as f:
                content = f.read()
                
            content_hash = self._compute_hash(content)
            metadata = self._get_metadata(new_path, content_hash)
            metadata['old_filename'] = old_filename
            metadata['new_filename'] = new_filename
            
            return metadata, None
            
        except Exception as e:
            logger.error(f"Error renaming config file: {str(e)}")
            return None, str(e)
            
    def delete_config(self, filename: str) -> Tuple[bool, Optional[str]]:
        """Archive a CMMS configuration file"""
        try:
            if not self._validate_file_extension(filename):
                return False, f"Invalid file type. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS.keys())}"
                
            file_path = self._get_file_path(filename)
            
            if not os.path.exists(file_path):
                return False, "Configuration file not found"
                
            # Move to archive with timestamp
            file_name, file_ext = os.path.splitext(filename)
            archive_filename = f"{file_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{file_ext}"
            archive_path = self._get_file_path(archive_filename, archived=True)
            
            os.rename(file_path, archive_path)
            return True, None
            
        except Exception as e:
            logger.error(f"Error deleting config file: {str(e)}")
            return False, str(e)