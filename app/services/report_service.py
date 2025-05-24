# app/services/report/report_service.py
from typing import Dict, List, Any, Optional, Tuple, BinaryIO
from io import BytesIO
import logging
from datetime import datetime
from app import db # Assuming db is initialized in app
from app.models import User, ReportTemplate, Role, Environment # Ensure all necessary models are imported
from app.utils.permission_manager import PermissionManager # Assuming PermissionManager is correctly set up
from sqlalchemy import inspect, text # For database schema and direct queries

# Import configurations and helper classes from the report service package
from app.services.report.report_config import SUPPORTED_FORMATS, ENTITY_CONFIG, ENTITY_TO_MODEL, MODEL_TO_ENTITY, DEFAULT_REPORT_TITLE
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
    Main service for orchestrating report generation.
    Handles parameter processing, data fetching, analysis, and formatting.
    """

    @staticmethod
    def generate_report(report_params: dict, user: User) -> Tuple[Optional[BytesIO], Optional[str], Optional[str], Optional[str]]:
        """
        Generates a report based on provided parameters and user permissions.
        It can load configurations from a saved ReportTemplate if 'template_id' is given.
        Direct parameters in the request will override those from the template.

        Args:
            report_params (dict): Parameters defining the report.
                                  Must include 'report_type'. Can include 'template_id'.
            user (User): The user requesting the report.

        Returns:
            Tuple containing (BytesIO buffer | None, filename | None, mime_type | None, error_message | None)
        """
        final_report_params = {} # Merged parameters from template and request
        template_id = report_params.get('template_id')
        request_params = report_params.copy() # Keep original request params separate

        # 1. Load Template Configuration (if template_id is provided)
        if template_id:
            logger.info(f"Report request includes template_id: {template_id}. Loading template...")
            try:
                template_id = int(template_id) # Ensure template_id is an integer
                # Query for non-deleted template
                template = ReportTemplate.query.filter_by(id=template_id, is_deleted=False).first()

                if not template:
                    logger.warning(f"Template ID {template_id} not found for report generation.")
                    return None, None, None, f"Report template with ID {template_id} not found."

                # Permission check for the template
                is_form_owner = template.form and template.form.user_id == user.id
                is_admin_user = user.role and user.role.is_super_user

                if not is_form_owner and not template.is_public and not is_admin_user:
                    logger.warning(f"User '{user.username}' permission denied for template ID {template_id}.")
                    return None, None, None, f"Permission denied to use report template ID {template_id}."

                template_config = template.configuration
                if not isinstance(template_config, dict):
                     logger.error(f"Template ID {template_id} has invalid configuration (not a dict).")
                     return None, None, None, f"Report template {template_id} has invalid configuration."

                logger.info(f"Successfully loaded configuration from template '{template.name}' (ID: {template_id}).")
                final_report_params = template_config.copy()

            except ValueError:
                 logger.warning(f"Invalid template_id format: {template_id}")
                 return None, None, None, "Invalid template_id format. Must be an integer."
            except Exception as e:
                 logger.exception(f"Error loading report template ID {template_id}: {e}")
                 return None, None, None, f"An internal error occurred while loading the report template: {str(e)}"

        # 2. Merge/Override with Request Parameters
        request_params.pop('template_id', None)
        final_report_params.update(request_params)

        try:
            output_format = final_report_params.get("output_format", "xlsx").lower()
            if output_format not in SUPPORTED_FORMATS: #
                 return None, None, None, f"Unsupported format: {output_format}. Supported formats: {', '.join(SUPPORTED_FORMATS)}" #

            base_filename = final_report_params.get("filename")
            processed_data = ReportService._generate_report_data(final_report_params, user)

            if '_error' in processed_data:
                return None, None, None, processed_data['_error']['error']
            if not any(not result.get('error') for result in processed_data.values() if isinstance(result, dict)):
                all_errors = "; ".join([f"{rt}: {res['error']}" for rt, res in processed_data.items() if isinstance(res, dict) and res.get('error')])
                error_msg = f"No data generated. Errors: {all_errors}" if all_errors else "No data found for the specified parameters."
                return None, None, None, error_msg

            report_type_req = final_report_params.get("report_type")
            if not base_filename:
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                name_part = "custom_report"
                if report_type_req == "all": name_part = "full_report"
                elif isinstance(report_type_req, list): name_part = "multi_report"
                elif isinstance(report_type_req, str): name_part = f"report_{report_type_req.replace(' ','_')}"

                if template_id and 'template' in locals() and template:
                    safe_template_name = "".join(c if c.isalnum() else "_" for c in template.name)
                    base_filename = f"template_{safe_template_name}_{ts}"
                else:
                     base_filename = f"{name_part}_{ts}"

            final_buffer: Optional[BytesIO] = None
            final_filename: str = f"{base_filename}.{output_format}"
            mime_type: Optional[str] = None

            formatter_map = {
                "xlsx": ReportXlsxFormatter, "csv": ReportCsvFormatter, "pdf": ReportPdfFormatter,
                "docx": ReportDocxFormatter, "pptx": ReportPptxFormatter,
            }
            mime_map = {
                "xlsx": 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                "csv": 'application/zip' if isinstance(report_type_req, list) and len(report_type_req) > 1 and output_format == 'csv' and not final_report_params.get('separate_files', False) else 'text/csv',
                "pdf": 'application/pdf',
                "docx": 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                "pptx": 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            }

            if output_format in formatter_map:
                try:
                    formatter_class = formatter_map[output_format]
                    formatter = formatter_class(processed_data, final_report_params)
                    final_buffer = formatter.generate()
                    mime_type = mime_map[output_format]

                    if (output_format == 'csv' and
                        isinstance(report_type_req, list) and
                        len(report_type_req) > 1 and
                        not final_report_params.get('separate_files', False)):
                         final_filename = f"{base_filename}.zip" # This logic seems more appropriate for CSV if it also zips multi-entity.
                         mime_type = 'application/zip'

                except Exception as format_err:
                    logger.error(f"Error generating {output_format} report: {format_err}", exc_info=True)
                    return None, None, None, f"Error during {output_format} generation: {format_err}"
            else:
                 return None, None, None, f"Unsupported format: {output_format}"

            if final_buffer and isinstance(final_buffer, BytesIO):
                logger.info(f"{output_format.upper()} report '{final_filename}' generated successfully for user '{user.username}'. Template ID used: {template_id if template_id else 'None'}.")
                return final_buffer, final_filename, mime_type, None
            else:
                error_msg = f"Failed to generate a valid report buffer for {output_format}."
                logger.error(error_msg)
                return None, None, None, error_msg

        except Exception as e:
            logger.exception(f"Unexpected error in report generation for user '{user.username}', params: {final_report_params}: {e}")
            return None, None, None, f"An unexpected error occurred during report generation."


    @staticmethod
    def _generate_report_data(report_params: dict, user: User) -> Dict[str, Dict[str, Any]]:
        """
        Fetches, flattens, enriches (for form_assignments), and analyzes data for requested report types.
        """
        report_type_req = report_params.get("report_type")
        processed_data: Dict[str, Dict[str, Any]] = {}
        all_entity_dataframes = {}

        if not report_type_req:
            processed_data['_error'] = {'error': "Missing 'report_type' in final parameters."}
            return processed_data

        if report_type_req == "all":
            report_types_to_process = list(ENTITY_CONFIG.keys()) #
        elif isinstance(report_type_req, list):
            report_types_to_process = report_type_req
        elif isinstance(report_type_req, str):
            report_types_to_process = [report_type_req]
        else:
            processed_data['_error'] = {'error': "Invalid report_type parameter format."}
            return processed_data

        has_detailed_params = any(k in report_params for k in ['columns', 'filters', 'sort_by'])
        is_single_entity_request = len(report_types_to_process) == 1

        question_info_map = {}
        if 'form_submissions' in report_types_to_process:
            try:
                from app.models import Question, QuestionType # Local import
                questions_from_db = db.session.query(Question.text, QuestionType.type).join(
                    QuestionType, Question.question_type_id == QuestionType.id
                ).filter(Question.is_deleted == False).all()
                question_info_map = {q_text: q_type for q_text, q_type in questions_from_db}
            except Exception as q_err:
                logger.error(f"Could not pre-fetch question info for form_submissions: {q_err}")

        for report_type in report_types_to_process:
            if report_type not in ENTITY_CONFIG: #
                logger.warning(f"Configuration for report type '{report_type}' not found in ENTITY_CONFIG. Skipping.")
                processed_data[report_type] = {'error': f"Unsupported report type: {report_type}"}
                continue

            config = ENTITY_CONFIG[report_type] #
            model_cls = config.get('model')
            permission_entity_type = config.get('view_permission_entity')

            if not model_cls or not permission_entity_type:
                processed_data[report_type] = {'error': f"Core configuration (model or permission) missing for: {report_type}"}
                continue

            if not PermissionManager.has_permission(user, "view", permission_entity_type):
                processed_data[report_type] = {'error': f"Permission denied for {report_type} report."}
                logger.warning(f"User '{user.username}' permission denied for viewing entity type '{permission_entity_type.value}'.")
                continue

            current_entity_specific_params = report_params.get(report_type, {}) if isinstance(report_params.get(report_type), dict) else {}
            use_detailed_params_for_entity = (is_single_entity_request and has_detailed_params) or bool(current_entity_specific_params)

            columns = current_entity_specific_params.get("columns", report_params.get("columns") if is_single_entity_request else None)
            filters = current_entity_specific_params.get("filters", report_params.get("filters", []) if is_single_entity_request else [])
            sort_by = current_entity_specific_params.get("sort_by", report_params.get("sort_by", config.get('default_sort', [])) if is_single_entity_request else config.get('default_sort', []))

            if not use_detailed_params_for_entity or not columns:
                logger.debug(f"Using default column logic for {report_type}")
                columns = list(config.get('default_columns', []))
                if not columns: # Fallback if default_columns is empty
                    try:
                        columns = list(inspect(model_cls).columns.keys()) # Get direct model columns
                    except Exception as inspect_err:
                        logger.error(f"Could not inspect columns for {model_cls.__name__}: {inspect_err}")
                        processed_data[report_type] = {'error': f"Could not determine any columns for {report_type}."}
                        continue
                filters = [] # Reset to default
                sort_by = config.get('default_sort', [])


            if not columns or not isinstance(columns, list):
                logger.error(f"Column list for {report_type} is invalid or empty: {columns}")
                processed_data[report_type] = {'error': f"No columns determined for {report_type}."}
                continue

            is_admin_user = user.role and user.role.is_super_user
            final_columns = ReportDataFetcher.sanitize_columns(list(columns), report_type, is_admin_user) #

            # Ensure 'assigned_entity_identifier' is in final_columns if it's a default for form_assignments
            if report_type == 'form_assignments' and \
               'assigned_entity_identifier' in config.get('default_columns', []) and \
               'assigned_entity_identifier' not in final_columns:
                if 'assigned_entity_identifier' in ENTITY_CONFIG.get('form_assignments', {}).get('available_columns', []): #
                    final_columns.append('assigned_entity_identifier')
                    logger.debug(f"Safeguard: Added 'assigned_entity_identifier' to final_columns for {report_type}")


            if not final_columns:
                processed_data[report_type] = {'error': f"No accessible columns found for {report_type} after sanitization."}
                continue

            current_processing_params = {
                "columns": final_columns, "filters": filters, "sort_by": sort_by,
                "report_type": report_type,
                "report_title": report_params.get("report_title", DEFAULT_REPORT_TITLE), #
                "output_format": report_params.get("output_format", "xlsx").lower(),
                "_internal_question_info": question_info_map if report_type == 'form_submissions' else {},
                "_internal_config": config,
                "sheet_name": report_params.get(f"{report_type}_sheet_name", report_type.replace("_", " ").title()),
                "table_options": report_params.get(f"{report_type}_table_options", report_params.get("table_options", {})),
                "include_data_table_in_ppt": report_params.get("include_data_table_in_ppt", False),
                "charts": current_entity_specific_params.get("charts", report_params.get("charts", []) if is_single_entity_request else []),
            }

            try:
                logger.info(f"Fetching data for report type '{report_type}' for user '{user.username}' with columns: {final_columns}")
                fetched_objects = ReportDataFetcher.fetch_data(model_cls, filters, sort_by, user, final_columns) #
                data = ReportDataFetcher.flatten_data(fetched_objects, final_columns, report_type) #

                if report_type == 'form_assignments':
                    enriched_data = []
                    for row_dict in data:
                        enriched_row = row_dict.copy()
                        entity_name = enriched_row.get('entity_name') # This is singular from FormAssignment model
                        entity_id = enriched_row.get('entity_id')
                        identifier_value = "N/A"

                        # Construct the plural key for ENTITY_TO_MODEL lookup if entity_name is one of the standard assignable types
                        # This handles 'user' -> 'users', 'role' -> 'roles', 'environment' -> 'environments'
                        # For other entity_name values (if any), it uses entity_name directly.
                        model_lookup_key = entity_name
                        if entity_name in ['user', 'role', 'environment']:
                            model_lookup_key = entity_name + 's'


                        if entity_name and entity_id is not None and model_lookup_key in ENTITY_TO_MODEL: #
                            target_model_cls = ENTITY_TO_MODEL[model_lookup_key] #
                            target_entity_obj = db.session.query(target_model_cls).filter_by(id=entity_id, is_deleted=False).first()

                            if target_entity_obj:
                                # Use the original singular entity_name for these comparisons
                                if entity_name == 'user':
                                    identifier_value = getattr(target_entity_obj, 'username', 'N/A')
                                    if 'assigned_user_email' in final_columns: enriched_row['assigned_user_email'] = getattr(target_entity_obj, 'email', None)
                                    if 'assigned_user_fullname' in final_columns: enriched_row['assigned_user_fullname'] = f"{getattr(target_entity_obj, 'first_name','')} {getattr(target_entity_obj, 'last_name','')}".strip()
                                elif entity_name == 'role':
                                    identifier_value = getattr(target_entity_obj, 'name', 'N/A')
                                    if 'assigned_role_description' in final_columns: enriched_row['assigned_role_description'] = getattr(target_entity_obj, 'description', None)
                                elif entity_name == 'environment':
                                    identifier_value = getattr(target_entity_obj, 'name', 'N/A')
                                    if 'assigned_environment_description' in final_columns: enriched_row['assigned_environment_description'] = getattr(target_entity_obj, 'description', None)
                        
                        enriched_row['assigned_entity_identifier'] = identifier_value
                        enriched_data.append(enriched_row)
                    data = enriched_data
                
                try:
                    import pandas as pd
                    df = pd.DataFrame(data)
                    all_entity_dataframes[report_type] = df
                except ImportError:
                    logger.warning("Pandas library not found. Cross-entity charts will be limited.")
                except Exception as df_err:
                    logger.error(f"Error creating DataFrame for {report_type}: {df_err}", exc_info=True)
                
                analysis_results = ReportAnalyzer.analyze_data(data, current_processing_params, report_type) #
                
                processed_data[report_type] = {
                    'error': None, 'data': data, 'objects': fetched_objects,
                    'params': current_processing_params, 'analysis': analysis_results
                }
                logger.info(f"Successfully processed '{report_type}' ({len(data)} records) for user '{user.username}'.")

            except Exception as proc_err:
                logger.error(f"Error processing data for {report_type} for user '{user.username}': {proc_err}", exc_info=True)
                processed_data[report_type] = {
                    'error': f"Error processing data for {report_type}: {str(proc_err)}",
                    'params': current_processing_params, 'analysis': {}, 'data': [], 'objects': []
                }
        
        if 'cross_entity_charts' in report_params and isinstance(report_params['cross_entity_charts'], list):
            try:
                from .report.report_formatters.cross_entity_chart_generator import CrossEntityChartGenerator #
                for chart_config in report_params['cross_entity_charts']:
                    try:
                        chart_bytes = CrossEntityChartGenerator.generate_comparison_chart( #
                            all_entity_dataframes, chart_config
                        )
                        if chart_bytes:
                            x_entity = chart_config.get('x_entity')
                            y_entity = chart_config.get('y_entity', x_entity)
                            chart_key = f"cross_{chart_config.get('chart_type','scatter')}_{x_entity}_{chart_config.get('x_column')}_vs_{y_entity}_{chart_config.get('y_column')}"
                            for entity_name_for_chart in {x_entity, y_entity}:
                                if entity_name_for_chart in processed_data and not processed_data[entity_name_for_chart].get('error'):
                                    entity_result = processed_data[entity_name_for_chart]
                                    if 'analysis' not in entity_result: entity_result['analysis'] = {}
                                    if 'charts' not in entity_result['analysis']: entity_result['analysis']['charts'] = {}
                                    entity_result['analysis']['charts'][chart_key] = chart_bytes
                                    logger.debug(f"Added cross-entity chart '{chart_key}' to '{entity_name_for_chart}' analysis.")
                    except Exception as chart_err:
                        logger.error(f"Error generating a specific cross-entity chart: {chart_err}", exc_info=True)
            except ImportError:
                logger.warning("CrossEntityChartGenerator not available. Cross-entity charts will be skipped.")
            except Exception as e:
                logger.error(f"General error processing cross-entity charts: {e}", exc_info=True)

        processed_data['_all_entity_dataframes'] = all_entity_dataframes
        return processed_data

    @staticmethod
    def get_database_schema() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Retrieves database schema information including tables, columns, keys, and row counts.
        """
        try:
            inspector = inspect(db.engine)
            schema_data: Dict[str, Any] = {}
            table_names = inspector.get_table_names()

            for table_name in table_names:
                try:
                    cols = inspector.get_columns(table_name)
                    pk_constraint = inspector.get_pk_constraint(table_name)
                    pk_cols = pk_constraint.get('constrained_columns', []) if pk_constraint else []
                    fks = inspector.get_foreign_keys(table_name)

                    columns_info = [
                        {"name": c['name'], "type": str(c['type']), "nullable": c.get('nullable', True),
                         "default": str(c.get('default')), "primary_key": c['name'] in pk_cols}
                        for c in cols
                    ]
                    foreign_keys_info = [
                        {"constrained_columns": fk['constrained_columns'], "referred_table": fk['referred_table'],
                         "referred_columns": fk['referred_columns']}
                        for fk in fks
                    ]

                    total_rows = db.session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
                    active_rows = None
                    if any(c['name'] == 'is_deleted' for c in cols):
                        try:
                            active_rows = db.session.execute(text(f"SELECT COUNT(*) FROM {table_name} WHERE is_deleted = FALSE")).scalar()
                        except Exception as count_err:
                            logger.warning(f"Could not get active row count for table {table_name}: {count_err}")

                    table_info: Dict[str, Any] = {
                        "columns": columns_info, "primary_keys": pk_cols,
                        "foreign_keys": foreign_keys_info, "total_rows": total_rows
                    }
                    if active_rows is not None:
                        table_info["active_rows"] = active_rows
                        table_info["deleted_rows"] = total_rows - active_rows
                    schema_data[table_name] = table_info

                except Exception as table_err:
                    logger.error(f"Error fetching schema details for table {table_name}: {table_err}")
                    schema_data[table_name] = {"error": f"Failed to retrieve schema for {table_name}: {str(table_err)}"}

            db_name = db.engine.url.database
            db_dialect_name = db.engine.dialect.name
            db_version = "N/A"
            try:
                if db_dialect_name == 'postgresql':
                    db_version = db.session.execute(text("SELECT version()")).scalar()
                elif db_dialect_name == 'mysql':
                    db_version = db.session.execute(text("SELECT VERSION()")).scalar()
                elif db_dialect_name == 'sqlite':
                    db_version = db.session.execute(text("SELECT sqlite_version()")).scalar()
            except Exception as db_info_err:
                logger.warning(f"Could not retrieve database version for {db_dialect_name}: {db_info_err}")

            model_mapping = {
                cfg['model'].__tablename__: entity_name
                for entity_name, cfg in ENTITY_CONFIG.items() #
                if cfg.get('model') and hasattr(cfg['model'], '__tablename__')
            }

            response_data = {
                "database_info": {
                    "name": db_name, "dialect": db_dialect_name, "version": db_version,
                    "total_tables": len(table_names),
                    "application_models_mapped": len(model_mapping)
                },
                "model_to_table_mapping": model_mapping,
                "tables": schema_data
            }
            return response_data, None
        except Exception as e:
            logger.exception(f"Failed to retrieve database schema: {e}")
            return None, f"An unexpected error occurred while retrieving database schema: {str(e)}"

    @staticmethod
    def get_available_columns(entity_type: str) -> List[str]:
        """
        Delegates to ReportDataFetcher to get all available columns for an entity type.
        """
        return ReportDataFetcher.get_available_columns(entity_type)