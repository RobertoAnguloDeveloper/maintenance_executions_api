from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import zipfile
from app.services.report_service import ReportService
from app.models import User
from io import BytesIO
import logging

from app.utils.permission_manager import PermissionManager

logger = logging.getLogger(__name__)

class ReportController:
    """
    Controller for handling report generation requests.
    """

    @staticmethod
    def generate_custom_report(report_params: dict, user: User) -> Tuple[Optional[BytesIO], Optional[str], Optional[str], Optional[str]]:
        """
        Generates a custom report by calling the ReportService.
        Can optionally package multiple entity reports into a ZIP file.

        Args:
            report_params (dict): Parameters defining the report.
                - report_type: string or list - Entity or entities to include
                - output_format: string - Output format (xlsx, csv, pdf, docx, pptx)
                - separate_files: boolean - Whether to package entities as separate files in a ZIP
                - (other standard report parameters)
            user (User): The user requesting the report.

        Returns:
            Tuple[Optional[BytesIO], Optional[str], Optional[str], Optional[str]]:
                - BytesIO buffer with report data, or None on error.
                - Filename, or None on error.
                - MIME type, or None on error.
                - Error message, or None on success.
        """
        logger.info(f"Generating report for user {user.username} with params: {report_params}")
        
        try:
            # Check if we need to generate separate files in a ZIP package
            separate_files = report_params.get('separate_files', False)
            report_type = report_params.get('report_type', [])
            
            # For multi-entity reports with separate_files flag, generate a ZIP package
            should_generate_zip = separate_files and (
                isinstance(report_type, list) and len(report_type) > 1 or
                report_type == "all"
            )
            
            if should_generate_zip:
                logger.info(f"Generating ZIP package of separate reports for user {user.username}")
                return ReportController.generate_zip_package(report_params, user)
            else:
                # Use the standard report generation
                buffer, filename, mime_type, error = ReportService.generate_report(report_params, user)

                # Handle potential errors from the service
                if error:
                    logger.error(f"Report generation failed for user {user.username}: {error}")
                    # Return None for buffer, filename, mime_type and the error message
                    return None, None, None, error

                # Validate return values
                if not buffer or not filename or not mime_type:
                    error_msg = "Report service returned incomplete results"
                    logger.error(f"{error_msg} for user {user.username}")
                    return None, None, None, error_msg

                # Log success and return all results
                logger.info(f"Report '{filename}' generated successfully for user {user.username}")
                return buffer, filename, mime_type, None

        except Exception as e:
            # Catch unexpected errors during controller execution
            logger.exception(f"Unexpected error in ReportController for user {user.username}: {e}")
            # Return None for buffer, filename, mime_type and a generic error message
            return None, None, None, f"An unexpected error occurred while generating the report: {str(e)}"
        
    @staticmethod
    def get_report_parameters(user: User) -> Dict[str, Any]:
        """
        Retrieves all available report parameters and their options.
        
        Args:
            user (User): The user requesting the parameters.
            
        Returns:
            Dictionary with all parameter details
        """
        try:
            from app.services.report.report_config import (
                SUPPORTED_FORMATS, ENTITY_CONFIG, VISUAL_FORMATS, 
                DEFAULT_CHART_TYPES, MODEL_TO_ENTITY
            )
            
            # Check which entities the user has permission to view
            available_entities = {}
            for entity_name, config in ENTITY_CONFIG.items():
                permission_entity = config.get('view_permission_entity')
                if permission_entity and PermissionManager.has_permission(user, "view", permission_entity):
                    # Get model class
                    model_cls = config.get('model')
                    
                    # Get entity metadata
                    available_entities[entity_name] = {
                        "name": entity_name,
                        "display_name": entity_name.replace('_', ' ').title(),
                        "description": config.get('description', f"{entity_name.replace('_', ' ').title()} data"),
                        "available_columns": ReportService.get_available_columns(entity_name),
                        "default_columns": config.get('default_columns', []),
                        "analysis_hints": {
                            "date_columns": config.get('analysis_hints', {}).get('date_columns', []),
                            "categorical_columns": config.get('analysis_hints', {}).get('categorical_columns', []),
                            "numerical_columns": config.get('analysis_hints', {}).get('numerical_columns', []),
                        }
                    }
            
            # Compile parameter details
            parameters = {
                "report_type": {
                    "type": "string or array",
                    "required": True,
                    "description": "Entity or entities to include in the report",
                    "options": list(available_entities.keys()),
                    "example": "users",
                    "example_array": ["users", "forms", "form_submissions"]
                },
                "output_format": {
                    "type": "string",
                    "required": False,
                    "default": "xlsx",
                    "description": "Output format for the report",
                    "options": SUPPORTED_FORMATS,
                    "example": "pdf"
                },
                "columns": {
                    "type": "array",
                    "required": False,
                    "description": "Specific columns to include (entity-specific)",
                    "example": ["id", "username", "email", "role.name"]
                },
                "filters": {
                    "type": "array",
                    "required": False,
                    "description": "Filters to apply to the data",
                    "structure": {
                        "field": "Column name to filter on",
                        "operator": "Comparison operator",
                        "value": "Value to compare against"
                    },
                    "operators": [
                        "eq", "neq", "like", "notlike", "startswith", "endswith", 
                        "in", "notin", "gt", "lt", "gte", "lte", "between", 
                        "isnull", "isnotnull"
                    ],
                    "example": [
                        {"field": "environment.name", "operator": "eq", "value": "Production"},
                        {"field": "created_at", "operator": "between", "value": ["2023-01-01", "2023-12-31"]}
                    ]
                },
                "sort_by": {
                    "type": "array",
                    "required": False,
                    "description": "Sorting options for the data",
                    "structure": {
                        "field": "Column name to sort by",
                        "direction": "Sort direction ('asc' or 'desc')"
                    },
                    "example": [
                        {"field": "username", "direction": "asc"}
                    ]
                },
                "filename": {
                    "type": "string",
                    "required": False,
                    "description": "Custom filename (without extension)",
                    "example": "user_report_2023"
                },
                "report_title": {
                    "type": "string",
                    "required": False,
                    "description": "Custom report title",
                    "example": "User Activity Analysis"
                },
                "template_id": {
                    "type": "integer",
                    "required": False,
                    "description": "ID of a saved report template to use",
                    "example": 123
                },
                "include_data_table_in_ppt": {
                    "type": "boolean",
                    "required": False,
                    "default": False,
                    "description": "Include data table in PPTX presentations",
                    "example": True
                },
                "charts": {
                    "type": "array",
                    "required": False,
                    "description": "Custom chart configurations for a single entity",
                    "structure": {
                        "type": "Chart type",
                        "column": "Data column to visualize",
                        "title": "Chart title"
                    },
                    "chart_types": DEFAULT_CHART_TYPES,
                    "example": [
                        {
                            "type": "bar",
                            "column": "role.name",
                            "title": "Users by Role"
                        },
                        {
                            "type": "pie",
                            "column": "environment.name",
                            "title": "Users by Environment"
                        }
                    ]
                },
                "cross_entity_charts": {
                    "type": "array",
                    "required": False,
                    "description": "Chart configurations for comparing data across entities",
                    "structure": {
                        "x_entity": "Entity name for x-axis data",
                        "x_column": "Column name from x_entity",
                        "y_entity": "Entity name for y-axis data",
                        "y_column": "Column name from y_entity",
                        "chart_type": "Type of chart",
                        "title": "Chart title",
                        "alignment": "Data alignment method"
                    },
                    "chart_types": ["scatter", "bar", "line", "pie", "heatmap"],
                    "alignment_options": ["time", "category", "index"],
                    "example": [
                        {
                            "x_entity": "users",
                            "x_column": "role.name",
                            "y_entity": "form_submissions",
                            "y_column": "submitted_by",
                            "chart_type": "bar",
                            "title": "User Roles vs Submission Activity"
                        }
                    ]
                },
                "separate_files": {
                    "type": "boolean",
                    "required": False,
                    "default": False,
                    "description": "Package multiple entity reports as separate files in a ZIP",
                    "example": True
                },
                "entity_specific_params": {
                    "type": "object",
                    "required": False,
                    "description": "Entity-specific parameters (use entity name as key)",
                    "example": {
                        "users": {
                            "filters": [
                                {"field": "created_at", "operator": "between", "value": ["2023-01-01", "2023-12-31"]}
                            ]
                        },
                        "forms": {
                            "columns": ["id", "title", "description", "is_public"]
                        }
                    }
                }
            }
            
            # Include available entities and their details
            parameters["available_entities"] = available_entities
            
            return parameters
            
        except Exception as e:
            logger.exception(f"Error retrieving report parameters: {e}")
            raise
    
    @staticmethod
    def generate_zip_package(report_params: dict, user: User) -> Tuple[Optional[BytesIO], Optional[str], Optional[str], Optional[str]]:
        """
        Generates multiple reports and packages them into a ZIP file.

        Args:
            report_params (dict): Parameters defining the reports to generate.
            user (User): The user requesting the reports.

        Returns:
            Tuple[Optional[BytesIO], Optional[str], Optional[str], Optional[str]]:
                - BytesIO buffer with ZIP data, or None on error.
                - Filename, or None on error.
                - MIME type, or None on error.
                - Error message, or None on success.
        """
        try:
            # Get report configuration
            report_types = report_params.get('report_type', [])
            output_format = report_params.get('output_format', 'xlsx').lower()
            report_title = report_params.get('report_title', 'Data Report')
            
            # Generate timestamp for default filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            filename_base = report_params.get('filename', f"reports_{timestamp}")
            
            # Handle 'all' report type
            if report_types == "all":
                from app.services.report.report_config import ENTITY_CONFIG
                report_types = list(ENTITY_CONFIG.keys())
                
            logger.info(f"Generating ZIP package with {len(report_types)} reports in '{output_format}' format for user {user.username}")
            
            # Create a ZIP file in memory
            memory_file = BytesIO()
            with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add a README.txt file to the ZIP with report information
                readme_content = (
                    f"Report Package: {report_title}\n"
                    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"User: {user.username}\n"
                    f"Format: {output_format}\n"
                    f"Entities: {', '.join(report_types)}\n\n"
                    f"This ZIP archive contains separate reports for each entity."
                )
                zf.writestr("README.txt", readme_content)
                
                # Track success and failures for summary
                success_count = 0
                error_count = 0
                entity_results = {}
                
                # Generate individual reports for each entity
                for report_type in report_types:
                    try:
                        logger.info(f"Generating {output_format} report for entity '{report_type}'")
                        
                        # Create report params for this entity only
                        entity_params = report_params.copy()
                        entity_params['report_type'] = report_type
                        entity_params.pop('separate_files', None)  # Remove separate_files flag
                        
                        # Remove other entity-specific parameters to avoid confusion
                        for entity_name in report_types:
                            if entity_name in entity_params and entity_name != report_type:
                                entity_params.pop(entity_name, None)
                        
                        # Check for entity-specific parameters and apply them
                        if report_type in report_params and isinstance(report_params[report_type], dict):
                            entity_specific_params = report_params[report_type]
                            for param_key, param_value in entity_specific_params.items():
                                entity_params[param_key] = param_value
                        
                        # Look for general filters that might apply to this entity
                        if 'filters' in report_params and isinstance(report_params['filters'], list):
                            entity_filters = []
                            for filter_item in report_params['filters']:
                                # Check if filter is entity-specific
                                field = filter_item.get('field', '')
                                
                                # Either it's a general filter or it targets this entity
                                if '.' not in field:
                                    # General filter, use as is
                                    entity_filters.append(filter_item)
                                elif field.startswith(f"{report_type}."):
                                    # Entity-specific filter, remove the prefix
                                    clean_filter = filter_item.copy()
                                    clean_filter['field'] = field[len(f"{report_type}."):]
                                    entity_filters.append(clean_filter)
                                    
                            # Set the adjusted filters
                            if entity_filters:
                                entity_params['filters'] = entity_filters
                        
                        # Important: Create a custom filename for each entity to avoid collisions
                        entity_filename_base = f"{filename_base}_{report_type}"
                        entity_params['filename'] = entity_filename_base
                        
                        # Override the report title to include entity name
                        entity_params['report_title'] = f"{report_title} - {report_type.replace('_', ' ').title()}"
                        
                        # Generate the report
                        buffer, entity_filename, mime_type, error = ReportService.generate_report(entity_params, user)
                        
                        if error:
                            # If there's an error, add an error text file
                            error_filename = f"{report_type}_error.txt"
                            error_content = f"Error generating {report_type} report:\n{error}"
                            zf.writestr(error_filename, error_content)
                            logger.error(f"Error generating {report_type} report for ZIP package: {error}")
                            error_count += 1
                            entity_results[report_type] = {'status': 'error', 'message': error}
                        elif buffer:
                            # Add the report to the ZIP with a unique filename
                            # Ensure entity name is part of the filename to avoid collisions
                            if entity_filename == f"{filename_base}.{output_format}" or '/' in entity_filename:
                                # If filename wasn't properly customized or contains path separators
                                proper_filename = f"{report_type}_{filename_base}.{output_format}"
                                zf.writestr(proper_filename, buffer.getvalue())
                                logger.info(f"Added '{proper_filename}' to ZIP package")
                                entity_results[report_type] = {'status': 'success', 'filename': proper_filename}
                            else:
                                zf.writestr(entity_filename, buffer.getvalue())
                                logger.info(f"Added '{entity_filename}' to ZIP package")
                                entity_results[report_type] = {'status': 'success', 'filename': entity_filename}
                            success_count += 1
                        else:
                            # Unexpected case: no error but also no buffer
                            error_filename = f"{report_type}_error.txt"
                            error_content = f"No data returned for {report_type} report"
                            zf.writestr(error_filename, error_content)
                            logger.warning(f"No data returned for {report_type} report")
                            error_count += 1
                            entity_results[report_type] = {'status': 'error', 'message': 'No data returned'}
                            
                    except Exception as entity_err:
                        # Handle errors for individual entities
                        logger.exception(f"Error processing entity '{report_type}' for ZIP package: {entity_err}")
                        error_filename = f"{report_type}_error.txt"
                        error_content = f"Error processing {report_type} report:\n{str(entity_err)}"
                        zf.writestr(error_filename, error_content)
                        error_count += 1
                        entity_results[report_type] = {'status': 'error', 'message': str(entity_err)}
                
                # Add a summary file to the ZIP
                summary_content = (
                    f"Report Package Summary\n"
                    f"=====================\n\n"
                    f"Total reports attempted: {len(report_types)}\n"
                    f"Successful: {success_count}\n"
                    f"Failed: {error_count}\n\n"
                    f"Entity Status:\n"
                )
                
                for entity, result in entity_results.items():
                    if result['status'] == 'success':
                        summary_content += f"- {entity}: Success ({result['filename']})\n"
                    else:
                        summary_content += f"- {entity}: Error ({result['message']})\n"
                
                zf.writestr("_SUMMARY.txt", summary_content)
            
            # Reset the file pointer and return
            memory_file.seek(0)
            filename = f"{filename_base}.zip"
            mime_type = 'application/zip'
            
            # Only report success if at least one report succeeded
            if success_count > 0:
                logger.info(f"ZIP package '{filename}' generated with {success_count} successful reports and {error_count} errors")
                return memory_file, filename, mime_type, None
            else:
                error_msg = f"Failed to generate any reports in the ZIP package. All {error_count} entities had errors."
                logger.error(error_msg)
                return None, None, None, error_msg
            
        except Exception as e:
            # Catch unexpected errors during ZIP package generation
            logger.exception(f"Unexpected error generating ZIP package for user {user.username}: {e}")
            return None, None, None, f"An unexpected error occurred while generating the ZIP package: {str(e)}"
    
    @staticmethod
    def get_available_columns(entity_type: str, user: User) -> List[str]:
        """
        Get available columns for a given entity type.
        
        Args:
            entity_type: The entity type to get columns for
            user: The user making the request
            
        Returns:
            List of available column names
        """
        logger.info(f"Getting available columns for entity '{entity_type}' for user {user.username}")
        try:
            # Use the ReportService to get available columns
            columns = ReportService.get_available_columns(entity_type)
            
            # Filter columns based on user role (is_admin)
            is_admin = user.role and user.role.is_super_user
            
            # Get configuration for the entity
            from app.services.report.report_config import ENTITY_CONFIG
            config = ENTITY_CONFIG.get(entity_type, {})
            sensitive_columns = config.get('sensitive_columns', [])
            hidden_columns = config.get('hidden_columns', [])
            
            # Filter out sensitive and hidden columns
            filtered_columns = []
            for col in columns:
                # Skip sensitive columns for non-admins
                if not is_admin and col in sensitive_columns:
                    continue
                    
                # Skip hidden columns for everyone
                if col in hidden_columns:
                    continue
                    
                filtered_columns.append(col)
                
            logger.info(f"Found {len(filtered_columns)} available columns for entity '{entity_type}'")
            return filtered_columns
            
        except Exception as e:
            logger.exception(f"Error getting available columns for entity '{entity_type}': {e}")
            raise
    
    @staticmethod
    def get_database_schema(user: User) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Retrieves database schema information by calling the ReportService.
        
        Args:
            user (User): The user requesting the schema information.
            
        Returns:
            Tuple[Optional[Dict[str, Any]], Optional[str]]:
                - Dictionary containing schema data, or None on error.
                - Error message, or None on success.
        """
        logger.info(f"Retrieving database schema for user {user.username}")
        try:
            # Call the schema service method from ReportService
            schema_data, error = ReportService.get_database_schema()
            
            if error:
                logger.error(f"Schema retrieval failed: {error}")
                return None, error
                
            if not schema_data:
                error_msg = "Schema service returned empty results"
                logger.error(error_msg)
                return None, error_msg
                
            logger.info(f"Database schema retrieved successfully")
            return schema_data, None
            
        except Exception as e:
            logger.exception(f"Unexpected error retrieving database schema: {e}")
            return None, f"An unexpected error occurred while retrieving database schema: {str(e)}"