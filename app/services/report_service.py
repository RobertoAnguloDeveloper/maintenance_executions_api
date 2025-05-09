# app/services/report/report_service.py
from typing import Dict, List, Any, Optional, Tuple, BinaryIO
from io import BytesIO
import logging
from datetime import datetime
from app import db
from app.models import User, ReportTemplate
from app.utils.permission_manager import PermissionManager
from sqlalchemy import inspect, text

from app.services.report.report_config import SUPPORTED_FORMATS, ENTITY_CONFIG, ENTITY_TO_MODEL
from .report.report_data_fetcher import ReportDataFetcher
from .report.report_analyzer import ReportAnalyzer
from .report.report_formatters import (
    ReportXlsxFormatter,
    ReportCsvFormatter,
    ReportPdfFormatter,
    ReportDocxFormatter,
    ReportPptxFormatter
)

logger = logging.getLogger(__name__)

class ReportService:
    """
    Main service for report generation
    """
    
    @staticmethod
    def generate_report(report_params: dict, user: User) -> Tuple[Optional[BytesIO], Optional[str], Optional[str], Optional[str]]:
        """
        Generates a report based on parameters, handling permissions and multiple formats.
        Can load configuration from a saved ReportTemplate if 'template_id' is provided.

        Args:
            report_params (dict): Parameters defining the report. Can include 'template_id'.
                                  Direct parameters override template configuration.
            user (User): The user requesting the report.

        Returns:
            Tuple containing (BytesIO buffer | None, filename | None, mime_type | None, error_message | None)
        """
        final_report_params = {}
        template_id = report_params.get('template_id')
        request_params = report_params.copy()  # Keep original request params separate

        # 1. Load Template Configuration (if template_id provided)
        if template_id:
            logger.info(f"Report request includes template_id: {template_id}. Loading template...")
            try:
                template_id = int(template_id)
                template = ReportTemplate.query.filter_by(id=template_id, is_deleted=False).first()

                if not template:
                    logger.warning(f"Template ID {template_id} not found for report generation.")
                    return None, None, None, f"Report template with ID {template_id} not found."

                # Check permissions for the template
                is_owner = template.user_id == user.id
                is_admin = user.role and user.role.name == 'admin'
                if not is_owner and not template.is_public and not is_admin:
                    logger.warning(f"User '{user.username}' permission denied for template ID {template_id}.")
                    return None, None, None, f"Permission denied to use report template ID {template_id}."

                # Load configuration from the template
                template_config = template.configuration
                if not isinstance(template_config, dict):
                     logger.error(f"Template ID {template_id} has invalid configuration (not a dict).")
                     return None, None, None, f"Report template {template_id} has invalid configuration."

                logger.info(f"Successfully loaded configuration from template '{template.name}' (ID: {template_id}).")
                final_report_params = template_config.copy()  # Start with template config

            except ValueError:
                 logger.warning(f"Invalid template_id format: {template_id}")
                 return None, None, None, "Invalid template_id format. Must be an integer."
            except Exception as e:
                 logger.exception(f"Error loading report template ID {template_id}: {e}")
                 return None, None, None, f"An internal error occurred while loading the report template: {str(e)}"

        # 2. Merge/Override with Request Parameters
        # Parameters directly in the request override those from the template
        # Remove 'template_id' from request_params before merging if it exists
        request_params.pop('template_id', None)
        final_report_params.update(request_params)  # Direct request params take precedence

        # --- Proceed with existing report generation logic using final_report_params ---
        try:
            # 3. Initial setup (format, filename base from final params)
            output_format = final_report_params.get("output_format", "xlsx").lower()
            if output_format not in SUPPORTED_FORMATS:
                 return None, None, None, f"Unsupported format: {output_format}. Supported formats: {', '.join(SUPPORTED_FORMATS)}"

            base_filename = final_report_params.get("filename")  # Filename can come from template or request

            # 4. Process data for requested entities using final_report_params
            # The _generate_report_data method now receives the potentially merged params
            processed_data = ReportService._generate_report_data(final_report_params, user)

            # 5. Handle errors from data processing
            if '_error' in processed_data:
                return None, None, None, processed_data['_error']['error']
            if not any(not res.get('error') for res in processed_data.values()):
                all_errors = "; ".join([f"{rt}: {res['error']}" for rt, res in processed_data.items() if res.get('error')])
                error_msg = f"No data generated. Errors: {all_errors}" if all_errors else "No data found for the specified parameters."
                return None, None, None, error_msg

            # 6. Determine final filename (if not provided in params)
            report_type_req = final_report_params.get("report_type")  # Get report type from final params
            if not base_filename:
                ts = datetime.now().strftime('%Y%m%d_%H%M')
                name_part = "custom_report"
                if report_type_req == "all":
                    name_part = "full_report"
                elif isinstance(report_type_req, list):
                    name_part = "multi_report"
                elif isinstance(report_type_req, str):
                    name_part = f"report_{report_type_req}"
                    
                # If loaded from template, maybe use template name?
                if template_id and 'template' in locals() and template:
                    safe_template_name = "".join(c if c.isalnum() else "_" for c in template.name)
                    base_filename = f"template_{safe_template_name}_{ts}"
                else:
                     base_filename = f"{name_part}_{ts}"

            # 7. Prepare for format generation
            final_buffer: Optional[BytesIO] = None
            final_filename: str = f"{base_filename}.{output_format}"
            mime_type: Optional[str] = None
            
            # Define format-specific formatters
            formatter_map = {
                "xlsx": ReportXlsxFormatter,
                "csv": ReportCsvFormatter,
                "pdf": ReportPdfFormatter,
                "docx": ReportDocxFormatter,
                "pptx": ReportPptxFormatter,
            }
            
            # Define MIME types
            mime_map = {
                "xlsx": 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                "csv": 'application/zip' if isinstance(report_type_req, list) and len(report_type_req) > 1 else 'text/csv',
                "pdf": 'application/pdf',
                "docx": 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                "pptx": 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            }

            # 8. Generate the report file using the appropriate formatter
            if output_format in formatter_map:
                try:
                    formatter_class = formatter_map[output_format]
                    formatter = formatter_class(processed_data, final_report_params)
                    final_buffer = formatter.generate()
                    mime_type = mime_map[output_format]
                    
                    # Adjust filename for multi-CSV zip
                    if (output_format == 'csv' and
                        isinstance(report_type_req, list) and
                        len(report_type_req) > 1):
                         final_filename = f"{base_filename}.zip"
                         mime_type = 'application/zip'  # Ensure mime type is zip for multi-csv
                         
                except Exception as format_err:
                    # Handle errors during format generation
                    logger.error(f"Error generating {output_format}: {format_err}", exc_info=True)
                    return None, None, None, f"Error during {output_format} generation: {format_err}"
            else:
                # This case should be caught earlier by the format check
                 return None, None, None, f"Unsupported format: {output_format}"

            # 9. Return result or handle buffer failure
            if final_buffer and isinstance(final_buffer, BytesIO):
                logger.info(f"{output_format.upper()} report '{final_filename}' generated successfully for user '{user.username}'. Template ID used: {template_id if template_id else 'None'}.")
                return final_buffer, final_filename, mime_type, None
            else:
                # This case means the generator function ran without error but didn't return a valid BytesIO buffer
                error_msg = f"Failed to generate buffer for {output_format}."
                logger.error(error_msg)
                return None, None, None, error_msg

        # Handle any unexpected errors during the whole process
        except Exception as e:
            logger.exception(f"Unexpected error in report generation for user '{user.username}', params: {final_report_params}: {e}")
            return None, None, None, f"An unexpected error occurred during report generation."

    @staticmethod
    def _generate_report_data(report_params: dict, user: User) -> Dict[str, Dict[str, Any]]:
        """Fetches, flattens, and analyzes data for requested report types based on merged params."""
        report_type_req = report_params.get("report_type")
        processed_data: Dict[str, Dict[str, Any]] = {}

        if not report_type_req:
             processed_data['_error'] = {'error': "Missing 'report_type' in final parameters."}
             return processed_data

        if report_type_req == "all":
            report_types_to_process = list(ENTITY_CONFIG.keys())
        elif isinstance(report_type_req, list):
            report_types_to_process = report_type_req
        elif isinstance(report_type_req, str):
            report_types_to_process = [report_type_req]
        else:
            processed_data['_error'] = {'error': "Invalid report_type parameter."}
            return processed_data

        # Determine if detailed parameters (columns, filters, sort) are present
        has_detailed_params = any(k in report_params for k in ['columns', 'filters', 'sort_by'])
        is_single_entity_request = len(report_types_to_process) == 1

        # Pre-fetch question info for form submissions if needed
        question_info_map = {}
        if 'form_submissions' in report_types_to_process:
            try:
                from app.models import Question, QuestionType
                questions_from_db = db.session.query(Question.text, QuestionType.type).join(
                    QuestionType, Question.question_type_id == QuestionType.id
                ).filter(Question.is_deleted == False).all()
                question_info_map = {q_text: q_type for q_text, q_type in questions_from_db}
            except Exception as q_err:
                logger.error(f"Could not pre-fetch question info: {q_err}")

        # Process each report type
        for report_type in report_types_to_process:
            if report_type not in ENTITY_CONFIG:
                processed_data[report_type] = {'error': f"Unsupported report type: {report_type}"}
                continue
                
            config = ENTITY_CONFIG[report_type]
            model_cls = config.get('model')
            permission_entity = config.get('view_permission_entity')
            
            if not model_cls or not permission_entity:
                processed_data[report_type] = {'error': f"Configuration incomplete for: {report_type}"}
                continue

            # Check user permission
            if not PermissionManager.has_permission(user, "view", permission_entity):
                processed_data[report_type] = {'error': f"Permission denied for {report_type} report."}
                logger.warning(f"User '{user.username}' permission denied for viewing entity '{permission_entity.value}'.")
                continue

            # Determine whether to use detailed parameters or defaults
            use_detailed_params = is_single_entity_request and has_detailed_params

            # Initialize parameters
            columns = None
            filters = []
            sort_by = config.get('default_sort', [])

            if use_detailed_params:
                # Use parameters from the final merged dictionary
                columns = report_params.get("columns")  # Use user's columns if provided
                filters = report_params.get("filters", [])
                sort_by = report_params.get("sort_by", config.get('default_sort', []))
                logger.debug(f"Using detailed params for {report_type}: cols={len(columns) if columns else 'None'}, filters={len(filters)}, sort={len(sort_by)}")
            else:
                # Use default column logic
                logger.debug(f"Using default column logic for {report_type}")
                try:
                    # Inspect model columns
                    columns = list(inspect(model_cls).columns.keys())
                    logger.debug(f"Using default all direct columns for {report_type}: {len(columns)} columns")
                except Exception as inspect_err:
                     logger.error(f"Could not inspect columns for {model_cls.__name__}: {inspect_err}")
                     columns = config.get('default_columns', [])  # Fallback to config default
                     if not columns:
                         processed_data[report_type] = {'error': f"Could not determine default columns for {report_type}."}
                         continue
                         
                # Add default related columns if defined in config
                default_related_cols = config.get('default_columns', [])
                if default_related_cols:
                    inspected_cols_set = set(columns)
                    for d_col in default_related_cols:
                        if '.' in d_col and d_col not in inspected_cols_set:
                            columns.append(d_col)
                
                # Reset filters and sort to defaults
                filters = []
                sort_by = config.get('default_sort', [])

            # Validate columns
            if not columns or not isinstance(columns, list):
                logger.error(f"Column list for {report_type} ended up invalid: {columns}")
                processed_data[report_type] = {'error': f"Could not determine columns for {report_type}."}
                continue

            # Filter sensitive columns for non-admin users
            is_admin = user.role and user.role.is_super_user
            columns = ReportDataFetcher.sanitize_columns(columns, report_type, is_admin)

            if not columns:
                processed_data[report_type] = {'error': f"No accessible columns for {report_type}."}
                continue

            # Construct entity-specific parameters
            current_entity_params = {
                "columns": columns,
                "filters": filters,
                "sort_by": sort_by,
                "report_type": report_type,
                "report_title": report_params.get("report_title", "Data Analysis Report"),
                "output_format": report_params.get("output_format", "xlsx").lower(),
                "_internal_question_info": question_info_map if report_type == 'form_submissions' else {},
                "_internal_config": config,
                "sheet_name": report_params.get(f"{report_type}_sheet_name", report_type.replace("_", " ").title()),
                "table_options": report_params.get(f"{report_type}_table_options", report_params.get("table_options", {})),
                "include_data_table_in_ppt": report_params.get("include_data_table_in_ppt", False),
                "charts": report_params.get("charts", []),
            }
            
            # Process entity data
            try:
                logger.info(f"Processing report type '{report_type}' for user '{user.username}'...")
                
                # Fetch raw data objects
                fetched_objects = ReportDataFetcher.fetch_data(model_cls, filters, sort_by, user, columns)
                
                # Flatten to dictionaries
                data = ReportDataFetcher.flatten_data(fetched_objects, columns, report_type)
                
                # Analyze data
                analysis_results = ReportAnalyzer.analyze_data(data, current_entity_params, report_type)
                
                # Store results
                processed_data[report_type] = {
                    'error': None,
                    'data': data,
                    'objects': fetched_objects,
                    'params': current_entity_params,
                    'analysis': analysis_results
                }
                
                logger.info(f"Successfully processed '{report_type}' ({len(data)} records) for user '{user.username}'.")
                
            except Exception as proc_err:
                logger.error(f"Error processing data for {report_type} for user '{user.username}': {proc_err}", exc_info=True)
                processed_data[report_type] = {
                    'error': f"Error processing data: {proc_err}",
                    'params': current_entity_params,
                    'analysis': {},
                    'data': [],
                    'objects': []
                }
                
        return processed_data

    @staticmethod
    def get_database_schema() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Retrieves database schema and table row counts
        
        Returns:
            Tuple containing (schema_data, error_message)
        """
        try:
            inspector = inspect(db.engine)
            schema_data = {}
            table_names = inspector.get_table_names()
            
            for table_name in table_names:
                try:
                    # Get columns, primary keys, and foreign keys
                    cols = inspector.get_columns(table_name)
                    pk_constraint = inspector.get_pk_constraint(table_name)
                    pk_cols = pk_constraint.get('constrained_columns', []) if pk_constraint else []
                    fks = inspector.get_foreign_keys(table_name)
                    
                    # Format column info
                    columns_info = [
                        {
                            "name": c['name'],
                            "type": str(c['type']),
                            "nullable": c.get('nullable', True),
                            "default": str(c.get('default')),
                            "primary_key": c['name'] in pk_cols
                        }
                        for c in cols
                    ]
                    
                    # Format foreign key info
                    foreign_keys_info = [
                        {
                            "constrained_columns": fk['constrained_columns'],
                            "referred_table": fk['referred_table'],
                            "referred_columns": fk['referred_columns']
                        }
                        for fk in fks
                    ]
                    
                    # Get row counts
                    total_rows = db.session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
                    active_rows = None
                    
                    if any(c['name'] == 'is_deleted' for c in cols):
                        try:
                            active_rows = db.session.execute(text(f"SELECT COUNT(*) FROM {table_name} WHERE is_deleted = FALSE")).scalar()
                        except Exception as count_err:
                            logger.warning(f"Could not get active count for {table_name}: {count_err}")
                    
                    # Create table info
                    table_info = {
                        "columns": columns_info,
                        "primary_keys": pk_cols,
                        "foreign_keys": foreign_keys_info,
                        "total_rows": total_rows
                    }
                    
                    if active_rows is not None:
                        table_info["active_rows"] = active_rows
                        table_info["deleted_rows"] = total_rows - active_rows
                        
                    schema_data[table_name] = table_info
                    
                except Exception as table_err:
                    logger.error(f"Error fetching schema for table {table_name}: {table_err}")
                    schema_data[table_name] = {"error": f"Failed schema: {table_err}"}
            
            # Get database info
            db_name = db.engine.url.database
            db_version = "N/A"
            
            try:
                if db.engine.dialect.name == 'postgresql':
                    db_version = db.session.execute(text("SELECT version()")).scalar()
                elif db.engine.dialect.name == 'mysql':
                    db_version = db.session.execute(text("SELECT VERSION()")).scalar()
            except Exception as db_info_err:
                logger.warning(f"Could not retrieve DB version: {db_info_err}")
            
            # Create model mapping
            model_mapping = {
                m_cfg['model'].__tablename__: m_name
                for m_name, m_cfg in ENTITY_CONFIG.items()
                if m_cfg.get('model')
            }
            
            # Build response
            response_data = {
                "database_info": {
                    "name": db_name,
                    "version": db_version,
                    "total_tables": len(table_names),
                    "application_models": len(model_mapping)
                },
                "model_mapping": model_mapping,
                "tables": schema_data
            }
            
            return response_data, None
            
        except Exception as e:
            logger.exception(f"Failed to retrieve DB schema: {e}")
            return None, f"Error retrieving schema: {e}"

    @staticmethod
    def get_available_columns(entity_type: str) -> List[str]:
        """
        Get all available columns for a given entity type
        
        Args:
            entity_type: The entity type (e.g., 'users', 'forms')
            
        Returns:
            List of available column names
        """
        return ReportDataFetcher.get_available_columns(entity_type)