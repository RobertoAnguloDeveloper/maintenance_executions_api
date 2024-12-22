import os
import hashlib
import json
import mimetypes
from typing import Dict, Optional, Tuple, BinaryIO, Union
from datetime import datetime
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger(__name__)

class CMMSConfigService:
    """Service for managing CMMS configuration files."""
    
    DEFAULT_CONFIG_FILENAME = 'config.json'
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
    
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
        """
        Initialize service with directory structure.
        
        Args:
            base_path: Base path (uploads folder)
        """
        # Base directories
        self.base_path = base_path  # This is the 'uploads' folder
        self.cmms_files_path = os.path.join(self.base_path, 'cmms_files')
        self.configs_path = os.path.join(self.cmms_files_path, 'configs')
        
        # Initialize mimetypes
        mimetypes.init()
        
        # Initialize directory structure
        self._init_directories()

    def _init_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        required_paths = [self.cmms_files_path, self.configs_path]
        
        for path in required_paths:
            if not os.path.exists(path):
                os.makedirs(path)
                logger.info(f"Created directory: {path}")

    def _validate_file_extension(self, filename: str) -> bool:
        """
        Validate if file extension is allowed.
        
        Args:
            filename: Name of the file to validate
            
        Returns:
            bool: True if extension is allowed, False otherwise
        """
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS

    def _validate_file_size(self, file_size: int) -> bool:
        """
        Validate if file size is within limits.
        
        Args:
            file_size: Size of the file in bytes
            
        Returns:
            bool: True if size is within limits, False otherwise
        """
        return file_size <= self.MAX_FILE_SIZE

    def _validate_file_content(self, content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Validate file content type and structure.
        
        Args:
            content: File content as bytes
            filename: Name of the file
            
        Returns:
            tuple: (is_valid: bool, error_message: Optional[str])
        """
        try:
            # Get MIME type from extension
            mime_type, _ = mimetypes.guess_type(filename)
            extension = filename.rsplit('.', 1)[1].lower()
            expected_mime = self.ALLOWED_EXTENSIONS.get(extension)
            
            if not mime_type or mime_type != expected_mime:
                return False, f"Invalid file type. Expected {expected_mime}, got {mime_type}"

            # Additional validation for JSON files
            if extension == 'json':
                try:
                    json_content = json.loads(content)
                    if not isinstance(json_content, (dict, list)):
                        return False, "Invalid JSON structure"
                except json.JSONDecodeError:
                    return False, "Invalid JSON format"

            return True, None
            
        except Exception as e:
            logger.error(f"Error validating file content: {str(e)}")
            return False, str(e)

    def _compute_hash(self, content: bytes) -> str:
        """Compute SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()

    def _get_metadata(self, file_path: str, content_hash: str) -> Dict:
        """
        Get file metadata.
        
        Args:
            file_path: Path to the file
            content_hash: Hash of file content
            
        Returns:
            Dict: File metadata
        """
        file_stat = os.stat(file_path)
        file_ext = os.path.splitext(file_path)[1].lower()[1:]
        
        return {
            "filename": os.path.basename(file_path),
            "path": file_path,
            "size": file_stat.st_size,
            "created_at": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            "content_hash": content_hash,
            "file_type": self.ALLOWED_EXTENSIONS.get(file_ext, 'application/octet-stream')
        }

    def create_config(self, filename: str, content: bytes, current_user: str) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Create a new configuration file in configs directory.
        """
        try:
            if not self._validate_file_extension(filename):
                return None, f"Invalid file type. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS.keys())}"

            if not self._validate_file_size(len(content)):
                return None, f"File size exceeds maximum limit of {self.MAX_FILE_SIZE/1024/1024}MB"

            is_valid, error = self._validate_file_content(content, filename)
            if not is_valid:
                return None, error

            secure_name = secure_filename(filename)
            file_path = os.path.join(self.configs_path, secure_name)

            if os.path.exists(file_path):
                return None, "Configuration file already exists"

            with open(file_path, 'wb') as f:
                f.write(content)

            content_hash = self._compute_hash(content)
            metadata = self._get_metadata(file_path, content_hash)
            
            logger.info(f"Config file {filename} created by user {current_user}")
            return metadata, None

        except Exception as e:
            logger.error(f"Error creating config file: {str(e)}")
            return None, str(e)

    def upload_config(self, file: BinaryIO, filename: str) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Upload a configuration file to cmms_files/configs directory.
        """
        try:
            if not self._validate_file_extension(filename):
                return None, f"Invalid file type. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS.keys())}"

            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)

            if not self._validate_file_size(file_size):
                return None, f"File size exceeds maximum limit of {self.MAX_FILE_SIZE/1024/1024}MB"

            content = file.read()
            is_valid, error = self._validate_file_content(content, filename)
            if not is_valid:
                return None, error

            secure_name = secure_filename(filename)
            file_path = os.path.join(self.cmms_files_path, secure_name)

            with open(file_path, 'wb') as f:
                f.write(content)

            content_hash = self._compute_hash(content)
            metadata = self._get_metadata(file_path, content_hash)
            
            return metadata, None

        except Exception as e:
            logger.error(f"Error uploading config file: {str(e)}")
            return None, str(e)

    def load_config(self, filename: str) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Load a configuration file.
        """
        try:
            if not self._validate_file_extension(filename):
                return None, f"Invalid file type. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS.keys())}"

            secure_name = secure_filename(filename)
            file_path = os.path.join(self.configs_path, secure_name)

            if not os.path.exists(file_path):
                return None, "Configuration file not found"

            with open(file_path, 'rb') as f:
                content = f.read()

            content_hash = self._compute_hash(content)
            metadata = self._get_metadata(file_path, content_hash)

            # Parse content for JSON files
            if filename.lower().endswith('.json'):
                try:
                    metadata['content'] = json.loads(content)
                except json.JSONDecodeError:
                    return None, "Invalid JSON format"
            else:
                metadata['content'] = content

            return metadata, None

        except Exception as e:
            logger.error(f"Error loading config file: {str(e)}")
            return None, str(e)
        
    def find_file(self, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Search for a file in the cmms_files directory and its subdirectories.
        
        Args:
            filename: Name of the file to find
            
        Returns:
            tuple: (Full file path if found or None, Error message if any)
        """
        try:
            secure_name = secure_filename(filename)
            
            # Walk through the cmms_files directory
            for root, _, files in os.walk(self.cmms_files_path):
                if secure_name in files:
                    file_path = os.path.join(root, secure_name)
                    
                    # Verify the path is within allowed directory
                    if not os.path.commonpath([file_path, self.cmms_files_path]) == self.cmms_files_path:
                        return None, "Access denied: File path outside allowed directory"
                        
                    # Verify file exists and is readable
                    if not os.path.isfile(file_path) or not os.access(file_path, os.R_OK):
                        return None, "File not accessible"
                        
                    return file_path, None
                    
            return None, "File not found"
            
        except Exception as e:
            logger.error(f"Error searching for file {filename}: {str(e)}")
            return None, str(e)
            
    def get_file_info(self, file_path: str) -> Dict:
        """
        Get file information including MIME type.
        
        Args:
            file_path: Full path to the file
            
        Returns:
            Dict: File information including mime type and filename
        """
        mime_type, _ = mimetypes.guess_type(file_path)
        return {
            'path': file_path,
            'filename': os.path.basename(file_path),
            'mime_type': mime_type or 'application/octet-stream'
        }
        
    def rename_config(self, old_filename: str, new_filename: str) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Rename a configuration file in the cmms_files directory.
        
        Args:
            old_filename: Current name of the file
            new_filename: New name for the file
            
        Returns:
            tuple: (metadata: Optional[Dict], error: Optional[str])
        """
        try:
            # Validate new filename extension
            if not self._validate_file_extension(new_filename):
                return None, f"Invalid file type for new filename. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS.keys())}"
                
            # Secure both filenames
            secure_old_name = secure_filename(old_filename)
            secure_new_name = secure_filename(new_filename)
            
            # Build file paths - check in cmms_files directory first
            old_path = os.path.join(self.cmms_files_path, secure_old_name)
            new_path = os.path.join(self.cmms_files_path, secure_new_name)
            
            # If file not found in cmms_files, check configs directory
            if not os.path.exists(old_path):
                old_path = os.path.join(self.configs_path, secure_old_name)
                new_path = os.path.join(self.configs_path, secure_new_name)
                
                if not os.path.exists(old_path):
                    return None, "Source configuration file not found"
            
            # Check if destination filename already exists
            if os.path.exists(new_path):
                return None, "A file with the new name already exists"
                
            # Rename the file
            os.rename(old_path, new_path)
            
            # Read content for hash computation
            with open(new_path, 'rb') as f:
                content = f.read()
                
            content_hash = self._compute_hash(content)
            metadata = self._get_metadata(new_path, content_hash)
            
            logger.info(f"Config file renamed from {old_filename} to {new_filename}")
            return metadata, None
            
        except Exception as e:
            error_msg = f"Error renaming config file: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    def delete_config(self, filename: str, current_user: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a configuration file (hard delete).
        """
        try:
            secure_name = secure_filename(filename)
            file_path = os.path.join(self.configs_path, secure_name)

            if not os.path.exists(file_path):
                return False, "Configuration file not found"

            try:
                os.remove(file_path)
                logger.info(f"Config file {filename} deleted by user {current_user}")
                return True, None

            except OSError as e:
                error_msg = f"Error deleting file: {str(e)}"
                logger.error(error_msg)
                return False, error_msg

        except Exception as e:
            error_msg = f"Error in delete_config: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


    def check_config_file(self) -> Tuple[bool, Dict]:
        """
        Check if configuration file exists and get its metadata.
        """
        try:
            config_path = os.path.join(self.configs_path, self.DEFAULT_CONFIG_FILENAME)
            exists = os.path.exists(config_path)
            
            metadata = {
                "base_path": self.base_path,
                "cmms_files_path": self.cmms_files_path,
                "configs_path": self.configs_path
            }

            if exists:
                file_stat = os.stat(config_path)
                metadata.update({
                    "filename": self.DEFAULT_CONFIG_FILENAME,
                    "full_path": config_path,
                    "size": file_stat.st_size,
                    "last_modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                })
            else:
                metadata["expected_path"] = config_path

            return exists, metadata

        except Exception as e:
            logger.error(f"Error checking config file: {str(e)}")
            return False, {"error": str(e)}