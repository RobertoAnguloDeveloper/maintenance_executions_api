# app/services/report_service.py

import xlsxwriter
import csv
import zipfile # Added for multi-CSV export
from io import BytesIO, StringIO
from typing import List, Dict, Tuple, Optional, Any
import pandas as pd # For data analysis
import matplotlib.pyplot as plt # For plotting
import seaborn as sns # For enhanced plotting
import matplotlib # Configure backend for non-GUI environment
matplotlib.use('Agg') # Use 'Agg' backend BEFORE importing pyplot

# --- PDF Generation ---
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib import colors

# --- DOCX Generation ---
from docx import Document
from docx.shared import Inches, Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

# --- PPTX Generation ---
from pptx import Presentation
from pptx.util import Inches as PptxInches, Pt as PptxPt
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.dml.color import RGBColor as PptxRGBColor

# --- App Imports ---
# Import all necessary models from your app.models package
from app.models import (
    User, FormSubmission, AnswerSubmitted, Form, Role, Environment,
    Question, Answer, QuestionType, Permission, RolePermission,
    FormQuestion, FormAnswer, Attachment # Add any other models you might report on
)
# Import permission manager components
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
# Import SQLAlchemy components
from sqlalchemy.orm import joinedload, selectinload, Query, aliased
from sqlalchemy import or_, asc, desc, inspect as sqla_inspect, func
from datetime import datetime
import logging
import traceback
import os # For plot saving/cleanup if needed

logger = logging.getLogger(__name__)


class ReportService:
    """
    Service responsible for generating customizable reports for various entities,
    respecting user permissions. Supports XLSX, CSV, PDF, DOCX, PPTX formats.
    Handles multi-entity requests differently based on format (XLSX: multi-sheet, CSV: zip, PDF/DOCX/PPTX: single-entity only).
    """

    # --- Configuration Mapping (Expandable) ---
    ENTITY_CONFIG = {
        "form_submissions": {
            'model': FormSubmission, 'view_permission_entity': EntityType.SUBMISSIONS,
            'default_columns': ["id", "form_id", "form.title", "submitted_by", "submitted_at", "updated_at"],
            'default_sort': [{"field": "submitted_at", "direction": "desc"}],
            'stats_generators': ['generate_submission_stats'],
            'chart_generators': ['generate_submission_charts'],
            'pptx_generator': '_generate_form_submission_pptx' # Specific PPTX generator
        },
        "users": {
            'model': User, 'view_permission_entity': EntityType.USERS,
            'default_columns': ["id", "username", "first_name", "last_name", "email", "role.name", "environment.name", "created_at", "is_deleted"],
            'default_sort': [{"field": "username", "direction": "asc"}],
            'stats_generators': ['generate_user_stats'],
            'chart_generators': ['generate_user_charts']
            # No specific pptx_generator, will use default or error
        },
        "forms": {
            'model': Form, 'view_permission_entity': EntityType.FORMS,
            'default_columns': ["id", "title", "description", "is_public", "creator.username", "creator.environment.name", "created_at"],
             'default_sort': [{"field": "title", "direction": "asc"}],
             'stats_generators': ['generate_form_stats'],
             'chart_generators': ['generate_form_charts']
       },
        "environments": {
            'model': Environment, 'view_permission_entity': EntityType.ENVIRONMENTS,
            'default_columns': ["id", "name", "description", "created_at"],
             'default_sort': [{"field": "name", "direction": "asc"}],
             'stats_generators': ['generate_environment_stats'],
             'chart_generators': ['generate_environment_charts']
        },
         "roles": {
            'model': Role, 'view_permission_entity': EntityType.ROLES,
            'default_columns': ["id", "name", "description", "is_super_user", "created_at"],
             'default_sort': [{"field": "name", "direction": "asc"}],
             'stats_generators': ['generate_role_stats'],
             'chart_generators': ['generate_role_charts']
        },
         "permissions": {
            'model': Permission, 'view_permission_entity': EntityType.ROLES, # Assuming tied to role view perm
            'default_columns': ["id", "name", "action", "entity", "description"],
             'default_sort': [{"field": "name", "direction": "asc"}],
             'stats_generators': [], 'chart_generators': []
        },
         "role_permissions": {
            'model': RolePermission, 'view_permission_entity': EntityType.ROLES, # Assuming tied to role view perm
            'default_columns': ["id", "role_id", "role.name", "permission_id", "permission.name"],
            'default_sort': [{"field": "role_id", "direction": "asc"}, {"field": "permission_id", "direction": "asc"}],
            'stats_generators': [], 'chart_generators': []
        },
        "question_types": {
            'model': QuestionType, 'view_permission_entity': EntityType.QUESTION_TYPES,
            'default_columns': ["id", "type", "created_at"],
            'default_sort': [{"field": "type", "direction": "asc"}],
            'stats_generators': [], 'chart_generators': []
        },
         "questions": {
            'model': Question, 'view_permission_entity': EntityType.QUESTIONS,
            'default_columns': ["id", "text", "question_type.type", "remarks", "is_signature", "created_at"],
            'default_sort': [{"field": "text", "direction": "asc"}],
            'stats_generators': ['generate_question_stats'],
            'chart_generators': []
        },
        "answers": { # Predefined answers
            'model': Answer, 'view_permission_entity': EntityType.ANSWERS,
            'default_columns': ["id", "value", "remarks", "created_at"],
            'default_sort': [{"field": "value", "direction": "asc"}],
            'stats_generators': [], 'chart_generators': []
        },
        "form_questions": { # Link table
            'model': FormQuestion, 'view_permission_entity': EntityType.FORMS,
            'default_columns': ["id", "form_id", "form.title", "question_id", "question.text", "order_number"],
            'default_sort': [{"field": "form_id", "direction": "asc"}, {"field": "order_number", "direction": "asc"}],
            'stats_generators': [], 'chart_generators': []
        },
        "form_answers": { # Link table for possible answers
            'model': FormAnswer, 'view_permission_entity': EntityType.FORMS,
            'default_columns': ["id", "form_question_id", "form_question.question.text", "answer_id", "answer.value"],
            'default_sort': [{"field": "form_question_id", "direction": "asc"}, {"field": "answer_id", "direction": "asc"}],
            'stats_generators': [], 'chart_generators': []
        },
        "answers_submitted": { # Submitted answers
            'model': AnswerSubmitted, 'view_permission_entity': EntityType.SUBMISSIONS,
            'default_columns': ["id", "form_submission_id", "question", "question_type", "answer", "column", "row", "cell_content", "created_at"],
             'default_sort': [{"field": "created_at", "direction": "desc"}],
             'stats_generators': [], 'chart_generators': [] # Stats/charts better on FormSubmission level
        },
        "attachments": {
            'model': Attachment, 'view_permission_entity': EntityType.ATTACHMENTS,
            'default_columns': ["id", "form_submission_id", "file_type", "file_path", "is_signature", "signature_position", "signature_author", "created_at"],
             'default_sort': [{"field": "created_at", "direction": "desc"}],
             'stats_generators': ['generate_attachment_stats'],
             'chart_generators': []
        },
    }

    # --- Helper Methods ---
    @staticmethod
    def _get_attribute_recursive(obj: Any, attr_string: str) -> Any:
        """Recursively retrieves nested attributes or list items."""
        attrs = attr_string.split('.')
        value = obj
        try:
            for attr in attrs:
                if value is None: return None
                # Handle list index access like 'items[0]'
                if '[' in attr and attr.endswith(']'):
                     attr_name, index_str = attr.split('[', 1)
                     index = int(index_str[:-1]) # Get index from like '[0]'
                     list_attr = getattr(value, attr_name, None)
                     # Check if it's a list and index is valid
                     if isinstance(list_attr, list) and len(list_attr) > index:
                         value = list_attr[index]
                     else:
                         value = None # Index out of bounds or not a list
                else:
                     # Regular attribute access
                    value = getattr(value, attr, None)
            # Format specific types for output
            if isinstance(value, datetime):
                return value.isoformat() # Standard ISO format
            if isinstance(value, bool):
                return "Yes" if value else "No" # User-friendly boolean
            return value
        except (AttributeError, ValueError, IndexError):
            logger.debug(f"Error accessing attribute '{attr_string}' on object {obj}")
            return None # Return None if any part of the chain fails

    @staticmethod
    def _apply_filters_and_sort(query: Query, model_cls: type, filters: List[Dict], sort_by: List[Dict], user: User) -> Query:
        """Applies filtering and sorting to a SQLAlchemy query object."""
        joined_models = {model_cls} # Track joined models to avoid duplicate joins for filters

        # Apply Filters
        for f in filters:
            field = f.get("field")
            op = f.get("operator", "eq").lower() # Default operator is 'eq'
            value = f.get("value")

            if not field or value is None: # Skip invalid filters
                logger.warning(f"Skipping invalid filter: {f}")
                continue

            current_model_alias = model_cls # Start with the base model
            model_attr = None
            parts = field.split('.')
            processed_joins_filter = set() # Track joins specifically for this filter path

            try:
                # Traverse relationships defined in the field string (e.g., 'role.name')
                for i, part in enumerate(parts):
                    mapper = sqla_inspect(current_model_alias)
                    is_last_part = (i == len(parts) - 1)

                    if is_last_part:
                        # Last part is the attribute to filter on
                        if part in mapper.columns or part in mapper.synonyms or part in mapper.column_attrs:
                            model_attr = getattr(current_model_alias, part)
                        else:
                            logger.warning(f"Filter field attribute '{part}' not found on model {current_model_alias.__name__}")
                            model_attr = None
                            break # Stop processing this filter field
                    else:
                        # Intermediate part is a relationship
                        if part in mapper.relationships:
                            related_model = mapper.relationships[part].mapper.class_
                            relationship_attr = getattr(current_model_alias, part)
                            join_key = (current_model_alias, related_model, relationship_attr.key)

                            # Join only if not already joined *for this specific filter path*
                            if join_key not in processed_joins_filter:
                                # Also check if the model wasn't joined globally yet
                                if related_model not in joined_models:
                                    query = query.join(relationship_attr)
                                    joined_models.add(related_model) # Add to global set
                                processed_joins_filter.add(join_key)

                            current_model_alias = related_model # Move to the related model for the next part
                        else:
                            logger.warning(f"Filter field relationship '{part}' not found on model {current_model_alias.__name__}")
                            model_attr = None
                            break # Stop processing this filter field
            except Exception as e:
                logger.error(f"Error processing filter field path '{field}': {e}")
                model_attr = None

            # Apply the filter operation if the attribute was found
            if model_attr is not None:
                try:
                    if op == "eq":
                        query = query.filter(model_attr == value)
                    elif op == "neq":
                        query = query.filter(model_attr != value)
                    elif op == "like":
                        query = query.filter(model_attr.ilike(f"%{value}%"))
                    elif op == "in" and isinstance(value, list):
                        query = query.filter(model_attr.in_(value))
                    elif op == "gt":
                        query = query.filter(model_attr > value)
                    elif op == "lt":
                        query = query.filter(model_attr < value)
                    elif op == "gte":
                        query = query.filter(model_attr >= value)
                    elif op == "lte":
                        query = query.filter(model_attr <= value)
                    elif op == "between" and isinstance(value, list) and len(value) == 2:
                        # Handle potential date/datetime conversion for 'between'
                        try:
                            # Attempt conversion if field name suggests date/time
                            if "at" in field.lower() or "date" in field.lower():
                                start = datetime.fromisoformat(str(value[0]))
                                end = datetime.fromisoformat(str(value[1]))
                                query = query.filter(model_attr.between(start, end))
                            else: # Assume numeric/string between
                                query = query.filter(model_attr.between(value[0], value[1]))
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid value format for 'between' filter on field {field}: {value}")
                    else:
                        logger.warning(f"Unsupported filter operator '{op}' for field '{field}'")
                except Exception as filter_ex:
                    logger.warning(f"Could not apply filter {f}: {filter_ex}")

        # Apply Sorting (similar logic for traversing relationships)
        joined_models_sort = {model_cls} # Track joins separately for sorting
        for s in sort_by:
            field = s.get("field")
            direction = s.get("direction", "asc").lower() # Default direction 'asc'
            if not field: continue

            current_model_alias = model_cls
            sort_attr = None
            parts = field.split('.')
            processed_joins_sort = set() # Track joins for this sort path

            try:
                for i, part in enumerate(parts):
                    mapper = sqla_inspect(current_model_alias)
                    is_last_part = (i == len(parts) - 1)

                    if is_last_part:
                        if part in mapper.columns or part in mapper.synonyms or part in mapper.column_attrs:
                            sort_attr = getattr(current_model_alias, part)
                        else:
                            logger.warning(f"Sort field attribute '{part}' not found on model {current_model_alias.__name__}")
                            sort_attr = None; break
                    else:
                        if part in mapper.relationships:
                            related_model = mapper.relationships[part].mapper.class_
                            relationship_attr = getattr(current_model_alias, part)
                            join_key = (current_model_alias, related_model, relationship_attr.key)
                            if join_key not in processed_joins_sort:
                                # Join only if not joined globally *or* for this sort path yet
                                if related_model not in joined_models and related_model not in joined_models_sort:
                                    query = query.join(relationship_attr)
                                    joined_models_sort.add(related_model) # Track sort join
                                processed_joins_sort.add(join_key)
                            current_model_alias = related_model
                        else:
                             logger.warning(f"Sort field relationship '{part}' not found on model {current_model_alias.__name__}")
                             sort_attr = None; break
            except Exception as e:
                logger.error(f"Error processing sort field path '{field}': {e}")
                sort_attr = None

            if sort_attr is not None:
                query = query.order_by(desc(sort_attr) if direction == "desc" else asc(sort_attr))

        return query


    @staticmethod
    def _fetch_data(model_cls: type, filters: List[Dict], sort_by: List[Dict], user: User, requested_columns: List[str]) -> List[Any]:
        """Fetches data based on model, filters, sort, user permissions, and loads necessary relationships."""
        try:
            query = model_cls.query

            # Base filter: Exclude soft-deleted records by default
            if hasattr(model_cls, 'is_deleted'):
                query = query.filter(model_cls.is_deleted == False)

            # Apply Role-Based Access Control Filters (if not admin)
            if not user.role.is_super_user:
                env_id = user.environment_id
                if model_cls == User:
                    # Non-admins can only see users in their own environment
                    query = query.filter(User.environment_id == env_id)
                elif model_cls == FormSubmission:
                     # Site Managers/Supervisors see submissions in their env; others see their own
                    if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                        # Need to join through Form -> User to filter by environment
                        query = query.join(Form, Form.id == FormSubmission.form_id) \
                                     .join(User, User.id == Form.user_id) \
                                     .filter(User.environment_id == env_id)
                    else: # Assuming technician or other role
                        query = query.filter(FormSubmission.submitted_by == user.username)
                elif model_cls == Form:
                     # Non-admins see public forms OR forms created by someone in their environment
                    query = query.join(User, User.id == Form.user_id)\
                                 .filter(or_(Form.is_public == True, User.environment_id == env_id))
                elif model_cls == Environment:
                     # Non-admins only see their own environment
                    query = query.filter(Environment.id == env_id)
                elif model_cls == Role:
                     # Non-admins cannot see super user roles
                    query = query.filter(Role.is_super_user == False)
                # Add similar RBAC filters for other models as needed...
                elif model_cls == AnswerSubmitted:
                     # Filter based on the submitter's environment
                     query = query.join(FormSubmission, FormSubmission.id == AnswerSubmitted.form_submission_id)\
                                  .join(Form, Form.id == FormSubmission.form_id)\
                                  .join(User, User.id == Form.user_id)\
                                  .filter(User.environment_id == env_id)
                elif model_cls == Attachment:
                     # Filter based on the submitter's environment
                     query = query.join(FormSubmission, FormSubmission.id == Attachment.form_submission_id)\
                                  .join(Form, Form.id == FormSubmission.form_id)\
                                  .join(User, User.id == Form.user_id)\
                                  .filter(User.environment_id == env_id)
                elif model_cls == RolePermission:
                     # Filter based on non-super-user roles
                     query = query.join(Role, Role.id == RolePermission.role_id)\
                                  .filter(Role.is_super_user == False)
                elif model_cls == FormQuestion:
                      # Filter based on public forms or forms in user's environment
                     query = query.join(Form, Form.id == FormQuestion.form_id)\
                                  .join(User, User.id == Form.user_id)\
                                  .filter(or_(Form.is_public == True, User.environment_id == env_id))
                elif model_cls == FormAnswer:
                     # Filter based on public forms or forms in user's environment
                     query = query.join(FormQuestion, FormQuestion.id == FormAnswer.form_question_id)\
                                  .join(Form, Form.id == FormQuestion.form_id)\
                                  .join(User, User.id == Form.user_id)\
                                  .filter(or_(Form.is_public == True, User.environment_id == env_id))


            # Apply user-defined filters and sorting
            query = ReportService._apply_filters_and_sort(query, model_cls, filters, sort_by, user)

            # Determine necessary relationships to load based on requested columns
            load_options = []
            # --- Dynamically determine joins based on columns ---
            relationships_to_load = set()
            for col in requested_columns:
                parts = col.split('.')
                if len(parts) > 1:
                    # Add relationship path segments (e.g., 'creator', 'creator.environment')
                    for i in range(1, len(parts)):
                        relationships_to_load.add('.'.join(parts[:i]))

            # --- Build SQLAlchemy load options ---
            if model_cls == User:
                if 'role' in relationships_to_load: load_options.append(joinedload(User.role))
                if 'environment' in relationships_to_load: load_options.append(joinedload(User.environment))
            elif model_cls == FormSubmission:
                if 'form.creator.environment' in relationships_to_load: load_options.append(joinedload(FormSubmission.form).joinedload(Form.creator).joinedload(User.environment))
                elif 'form.creator' in relationships_to_load: load_options.append(joinedload(FormSubmission.form).joinedload(Form.creator))
                elif 'form' in relationships_to_load: load_options.append(joinedload(FormSubmission.form))
                if 'answers_submitted' in relationships_to_load or any(c.startswith('answers.') for c in requested_columns): load_options.append(selectinload(FormSubmission.answers_submitted))
                if 'attachments' in relationships_to_load: load_options.append(selectinload(FormSubmission.attachments))
            elif model_cls == Form:
                 if 'creator.environment' in relationships_to_load: load_options.append(joinedload(Form.creator).joinedload(User.environment))
                 elif 'creator' in relationships_to_load: load_options.append(joinedload(Form.creator))
                 if any(c.startswith('form_questions.question.question_type') for c in requested_columns): load_options.append(selectinload(Form.form_questions).joinedload(FormQuestion.question).joinedload(Question.question_type))
                 elif any(c.startswith('form_questions.question') for c in requested_columns): load_options.append(selectinload(Form.form_questions).joinedload(FormQuestion.question))
                 elif 'form_questions' in relationships_to_load: load_options.append(selectinload(Form.form_questions))
            elif model_cls == RolePermission:
                 if 'role' in relationships_to_load: load_options.append(joinedload(RolePermission.role))
                 if 'permission' in relationships_to_load: load_options.append(joinedload(RolePermission.permission))
            elif model_cls == Question:
                 if 'question_type' in relationships_to_load: load_options.append(joinedload(Question.question_type))
            elif model_cls == FormQuestion:
                 if 'form.creator' in relationships_to_load: load_options.append(joinedload(FormQuestion.form).joinedload(Form.creator))
                 elif 'form' in relationships_to_load: load_options.append(joinedload(FormQuestion.form))
                 if 'question.question_type' in relationships_to_load: load_options.append(joinedload(FormQuestion.question).joinedload(Question.question_type))
                 elif 'question' in relationships_to_load: load_options.append(joinedload(FormQuestion.question))
                 if 'form_answers.answer' in relationships_to_load: load_options.append(selectinload(FormQuestion.form_answers).joinedload(FormAnswer.answer))
                 elif 'form_answers' in relationships_to_load: load_options.append(selectinload(FormQuestion.form_answers))
            elif model_cls == FormAnswer:
                 if 'form_question.question.question_type' in relationships_to_load: load_options.append(joinedload(FormAnswer.form_question).joinedload(FormQuestion.question).joinedload(Question.question_type))
                 elif 'form_question.question' in relationships_to_load: load_options.append(joinedload(FormAnswer.form_question).joinedload(FormQuestion.question))
                 elif 'form_question' in relationships_to_load: load_options.append(joinedload(FormAnswer.form_question))
                 if 'answer' in relationships_to_load: load_options.append(joinedload(FormAnswer.answer))
            elif model_cls == AnswerSubmitted:
                 if 'form_submission.form' in relationships_to_load: load_options.append(joinedload(AnswerSubmitted.form_submission).joinedload(FormSubmission.form))
                 elif 'form_submission' in relationships_to_load: load_options.append(joinedload(AnswerSubmitted.form_submission))
            elif model_cls == Attachment:
                 if 'form_submission.form' in relationships_to_load: load_options.append(joinedload(Attachment.form_submission).joinedload(FormSubmission.form))
                 elif 'form_submission' in relationships_to_load: load_options.append(joinedload(Attachment.form_submission))


            # Apply load options if any were generated
            if load_options:
                query = query.options(*load_options)

            # Execute query and return results
            return query.all()

        except Exception as e:
            logger.error(f"Error fetching data for {model_cls.__name__} report: {str(e)}")
            logger.error(traceback.format_exc()) # Log full traceback for debugging
            raise # Re-raise the exception to be caught by the calling function


    @staticmethod
    def _flatten_data(objects: List[Any], columns: List[str]) -> List[Dict]:
        """Flattens a list of objects into a list of dictionaries based on specified columns."""
        flat_data = []
        if not objects:
            return flat_data

        # Check if the primary objects are FormSubmissions to handle 'answers.' prefix specially
        is_submission_report = isinstance(objects[0], FormSubmission)
        answer_columns = [col for col in columns if col.startswith("answers.")] if is_submission_report else []
        regular_columns = [col for col in columns if not col.startswith("answers.")]

        for obj in objects:
            row_dict = {}
            # Process regular columns using recursive getter
            for col in regular_columns:
                row_dict[col] = ReportService._get_attribute_recursive(obj, col)

            # Process special 'answers.' columns for FormSubmission reports
            if is_submission_report and answer_columns:
                 # Create a dictionary of answers for the current submission for quick lookup
                 submission_answers = {ans.question: ans.answer
                                       for ans in getattr(obj, 'answers_submitted', [])
                                       if not ans.is_deleted} # Include soft delete check

                 for col in answer_columns:
                    try:
                        # Extract question text after 'answers.'
                        question_text = col.split(".", 1)[1]
                        row_dict[col] = submission_answers.get(question_text, None) # Get answer by question text
                    except IndexError:
                        logger.warning(f"Invalid answer column format: {col}")
                        row_dict[col] = None
                    except Exception as e: # Catch potential errors during lookup
                         logger.error(f"Error processing answer column '{col}': {e}")
                         row_dict[col] = f"Error: {e}" # Indicate error in output

            flat_data.append(row_dict)
        return flat_data

    # --- Data Analysis & Stats/Chart Generation ---
    @staticmethod
    def _analyze_data(data: List[Dict], report_type: str) -> Dict:
        """Performs basic analysis and generates charts/stats if configured."""
        analysis = {"summary_stats": {}, "charts": {}}
        if not data: # Don't analyze if no data
            return analysis

        try:
            df = pd.DataFrame(data)
            config = ReportService.ENTITY_CONFIG.get(report_type, {})
            stats_funcs = config.get('stats_generators', [])
            chart_funcs = config.get('chart_generators', [])

            # --- Generate Summary Stats ---
            analysis['summary_stats']['record_count'] = len(df) # Basic count
            for func_name in stats_funcs:
                if hasattr(ReportService, func_name):
                    try:
                        # Call the static stats generator method
                        analysis['summary_stats'].update(getattr(ReportService, func_name)(df))
                    except Exception as stat_err:
                        logger.error(f"Error executing statistics function '{func_name}' for {report_type}: {stat_err}", exc_info=True)
                        analysis['summary_stats'][f'{func_name}_error'] = str(stat_err) # Add error info
                else:
                    logger.warning(f"Statistics generator function '{func_name}' not found in ReportService.")

            # --- Generate Charts ---
            for func_name in chart_funcs:
                 if hasattr(ReportService, func_name):
                    try:
                        # Call the static chart generator method
                        chart_bytes = getattr(ReportService, func_name)(df, report_type)
                        # Store the chart BytesIO object if successfully generated
                        if chart_bytes and isinstance(chart_bytes, BytesIO):
                            chart_key = func_name.replace("generate_", "").replace("_charts","") # e.g., 'submission_trend'
                            analysis['charts'][chart_key] = chart_bytes
                        elif chart_bytes: # Log if it returned something unexpected
                            logger.warning(f"Chart generator '{func_name}' for {report_type} did not return a BytesIO object.")
                    except Exception as chart_err:
                        logger.error(f"Error executing chart function '{func_name}' for {report_type}: {chart_err}", exc_info=True)
                        # Optionally add chart error info to analysis dict if needed
                 else:
                    logger.warning(f"Chart generator function '{func_name}' not found in ReportService.")

        except Exception as e:
            logger.error(f"Error during data analysis for {report_type}: {e}", exc_info=True)
            analysis['summary_stats']['analysis_error'] = "Data analysis failed" # Add overall error

        return analysis


    # --- Specific Stats/Chart Generators (EXAMPLES - IMPLEMENT REAL LOGIC) ---
    @staticmethod
    def _save_plot_to_bytes(figure) -> Optional[BytesIO]:
         """Saves a matplotlib figure to a BytesIO object."""
         try:
             img_buffer = BytesIO()
             # Use tight_layout before saving to adjust spacing
             figure.tight_layout()
             figure.savefig(img_buffer, format='png', bbox_inches='tight') # Save PNG to buffer
             img_buffer.seek(0) # Rewind buffer
             plt.close(figure) # Close the figure to free memory
             return img_buffer
         except Exception as e:
             logger.error(f"Failed to save plot to BytesIO: {e}")
             if 'figure' in locals() and plt.fignum_exists(figure.number):
                 plt.close(figure) # Ensure figure is closed on error too
             return None

    @staticmethod
    def generate_submission_stats(df: pd.DataFrame) -> Dict:
        """Generates statistics specific to FormSubmission data."""
        stats = {}
        if 'submitted_by' in df.columns:
            stats['submissions_per_user_top5'] = df['submitted_by'].value_counts().nlargest(5).to_dict()
        if 'submitted_at' in df.columns:
             # Convert to datetime safely
             df['submitted_at_dt'] = pd.to_datetime(df['submitted_at'], errors='coerce')
             if not df['submitted_at_dt'].isnull().all(): # Check if conversion worked
                 stats['first_submission'] = df['submitted_at_dt'].min().isoformat()
                 stats['last_submission'] = df['submitted_at_dt'].max().isoformat()
        return stats

    @staticmethod
    def generate_user_stats(df: pd.DataFrame) -> Dict:
        """Generates statistics specific to User data."""
        stats = {}
        if 'role.name' in df.columns:
            stats['users_per_role'] = df['role.name'].value_counts().to_dict()
        if 'environment.name' in df.columns:
            stats['users_per_environment'] = df['environment.name'].value_counts().to_dict()
        if 'created_at' in df.columns:
             df['created_at_dt'] = pd.to_datetime(df['created_at'], errors='coerce')
             if not df['created_at_dt'].isnull().all():
                 # Resample by month end ('ME') for monthly counts
                 stats['users_created_monthly'] = df.set_index('created_at_dt').resample('ME').size().to_dict()
        return stats

    @staticmethod
    def generate_form_stats(df: pd.DataFrame) -> Dict:
        """Generates statistics specific to Form data."""
        stats = {}
        if 'creator.username' in df.columns:
            stats['forms_per_creator_top5'] = df['creator.username'].value_counts().nlargest(5).to_dict()
        if 'is_public' in df.columns:
            # Convert 'Yes'/'No' string back to boolean safely
            df['is_public_bool'] = df['is_public'].apply(lambda x: True if str(x).lower() == 'yes' else False if str(x).lower() == 'no' else None)
            stats['public_vs_private_forms'] = df['is_public_bool'].value_counts().rename(index={True:'Public', False:'Private'}).to_dict()
        return stats

    @staticmethod
    def generate_environment_stats(df: pd.DataFrame) -> Dict:
        """Basic stats for environments."""
        return {'total_environments': len(df)} # Example stat

    @staticmethod
    def generate_role_stats(df: pd.DataFrame) -> Dict:
        """Generates statistics specific to Role data."""
        stats = {}
        if 'is_super_user' in df.columns:
             # Convert 'Yes'/'No' string back to boolean safely
             df['is_super_user_bool'] = df['is_super_user'].apply(lambda x: True if str(x).lower() == 'yes' else False if str(x).lower() == 'no' else None)
             # Ensure the result is an integer for JSON compatibility
             stats['super_user_roles_count'] = int(df['is_super_user_bool'].sum())
        return stats

    @staticmethod
    def generate_question_stats(df: pd.DataFrame) -> Dict:
        """Generates statistics specific to Question data."""
        stats = {}
        if 'question_type.type' in df.columns:
            stats['questions_per_type'] = df['question_type.type'].value_counts().to_dict()
        return stats

    @staticmethod
    def generate_attachment_stats(df: pd.DataFrame) -> Dict:
        """Generates statistics specific to Attachment data."""
        stats = {}
        if 'file_type' in df.columns:
            stats['attachments_by_type'] = df['file_type'].value_counts().to_dict()
        if 'is_signature' in df.columns:
            df['is_signature_bool'] = df['is_signature'].apply(lambda x: True if str(x).lower() == 'yes' else False if str(x).lower() == 'no' else None)
            stats['signature_attachments_count'] = int(df['is_signature_bool'].sum()) # Ensure integer
        return stats

    # --- Chart Generators ---
    @staticmethod
    def generate_submission_charts(df: pd.DataFrame, report_type: str) -> Optional[BytesIO]:
        """Generates a monthly submission trend chart."""
        if 'submitted_at' not in df.columns or df.empty:
            return None
        try:
            # Ensure datetime conversion, handle potential errors, remove timezone
            df['submitted_at_dt'] = pd.to_datetime(df['submitted_at'], errors='coerce').dt.tz_localize(None)
            # Drop rows where conversion failed
            df.dropna(subset=['submitted_at_dt'], inplace=True)
            if df.empty: return None # Return if no valid dates

            # Resample by Month End ('ME')
            monthly_counts = df.set_index('submitted_at_dt').resample('ME').size()
            if monthly_counts.empty: return None # No data after resampling

            fig, ax = plt.subplots(figsize=(10, 4)) # Adjust figure size
            monthly_counts.plot(kind='line', ax=ax, marker='o')
            ax.set_title('Submissions Trend (Monthly)')
            ax.set_ylabel('# Submissions')
            ax.set_xlabel('Month')
            plt.xticks(rotation=30, ha='right') # Rotate labels for readability
            return ReportService._save_plot_to_bytes(fig)
        except Exception as e:
            logger.error(f"Error generating submission chart: {e}", exc_info=True)
            # Ensure figure is closed if created
            if 'fig' in locals() and plt.fignum_exists(fig.number):
                 plt.close(fig)
            return None


    @staticmethod
    def generate_user_charts(df: pd.DataFrame, report_type: str) -> Optional[BytesIO]:
        """Generates a bar chart of user counts per role."""
        if 'role.name' not in df.columns or df.empty:
            return None
        try:
            role_counts = df['role.name'].value_counts()
            if role_counts.empty: return None

            fig, ax = plt.subplots(figsize=(8, 4)) # Adjust size
            # Use seaborn for potentially better aesthetics
            sns.barplot(x=role_counts.index, y=role_counts.values, ax=ax, palette="viridis")
            ax.set_title('User Count by Role')
            ax.set_ylabel('# Users')
            ax.set_xlabel('Role')
            plt.xticks(rotation=30, ha='right') # Rotate labels
            return ReportService._save_plot_to_bytes(fig)
        except Exception as e:
            logger.error(f"Error generating user chart: {e}", exc_info=True)
            if 'fig' in locals() and plt.fignum_exists(fig.number):
                 plt.close(fig)
            return None


    @staticmethod
    def generate_form_charts(df: pd.DataFrame, report_type: str) -> Optional[BytesIO]:
        """Generates a pie chart for public vs. private forms."""
        if 'is_public' not in df.columns or df.empty:
            return None
        try:
            # Convert 'Yes'/'No' string back to boolean safely
            df['is_public_bool'] = df['is_public'].apply(lambda x: True if str(x).lower() == 'yes' else False if str(x).lower() == 'no' else None)
            status_counts = df['is_public_bool'].value_counts().rename(index={True:'Public', False:'Private'})
            if status_counts.empty: return None

            fig, ax = plt.subplots(figsize=(5, 5)) # Adjust size
            status_counts.plot(kind='pie', ax=ax, autopct='%1.1f%%', startangle=90, colors=['skyblue', 'lightcoral'])
            ax.set_title('Forms: Public vs. Private')
            ax.set_ylabel('') # Hide default y-label for pie charts
            return ReportService._save_plot_to_bytes(fig)
        except Exception as e:
            logger.error(f"Error generating form chart: {e}", exc_info=True)
            if 'fig' in locals() and plt.fignum_exists(fig.number):
                 plt.close(fig)
            return None

    @staticmethod
    def generate_environment_charts(df: pd.DataFrame, report_type: str) -> Optional[BytesIO]:
        """Placeholder for environment charts."""
        # Example: Could potentially plot user count per environment if joined
        logger.info("Environment chart generation not implemented.")
        return None

    @staticmethod
    def generate_role_charts(df: pd.DataFrame, report_type: str) -> Optional[BytesIO]:
        """Placeholder for role charts."""
        # Example: Could plot roles vs super_user status
        logger.info("Role chart generation not implemented.")
        return None


    # --- Report Generation Methods ---
    @staticmethod
    def _write_sheet_data_with_analysis(worksheet: xlsxwriter.worksheet.Worksheet, workbook: xlsxwriter.Workbook, data: List[Dict], columns: List[str], analysis: Dict, sheet_params: dict):
        """Writes flattened data, stats, and charts to an XLSX worksheet."""

        # Define formats
        header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'top', 'fg_color': '#D7E4BC', 'border': 1, 'align': 'center'})
        wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top', 'align': 'left'}) # For data cells

        # --- Write Data Table ---
        # Prepare headers for add_table
        headers = [{'header': col} for col in columns]
        # Convert all data to string, handle None
        table_data = [[str(row_dict.get(col)) if row_dict.get(col) is not None else '' for col in columns] for row_dict in data]

        first_row_table = 0 # Start table at the top
        first_col_table = 0

        if not table_data and not headers:
             worksheet.write(first_row_table, 0, "No data or columns configured for this report.")
        elif not table_data: # Write only headers if no data
            for col_idx, header_info in enumerate(headers):
                 worksheet.write(first_row_table, col_idx, header_info['header'], header_format)
            logger.warning(f"No data found for sheet '{worksheet.name}'. Writing headers only.")
        else:
            # Calculate table dimensions
            last_row_table = first_row_table + len(table_data) # +1 for header implicitly handled by add_table
            last_col_table = first_col_table + len(headers) - 1

            # Add the table using worksheet.add_table
            worksheet.add_table(first_row_table, first_col_table, last_row_table, last_col_table, {
                'data': table_data,
                'columns': headers,
                'style': sheet_params.get('table_options', {}).get('style', 'Table Style Medium 9'), # Default style
                'banded_rows': sheet_params.get('table_options', {}).get('banded_rows', True),
                'header_row': True # Let add_table handle the header format
            })

            # --- Auto-adjust Column Widths (Basic) ---
            # Note: This is an approximation. Accurate width calculation is complex.
            for col_idx, col_key in enumerate(columns):
                # Calculate max length needed for this column
                header_len = len(col_key)
                max_data_len = 0
                for row_data in table_data:
                    cell_value = row_data[col_idx] # Already stringified
                    max_data_len = max(max_data_len, len(cell_value))

                # Set width (add padding, limit max width)
                # Adjust multiplier based on font size if needed
                width = min(max(header_len, max_data_len, 10) + 2, 60)
                worksheet.set_column(col_idx, col_idx, width, wrap_format) # Apply wrap format to data columns


    @staticmethod
    def _generate_multi_sheet_xlsx(report_data: Dict[str, Dict], global_params: dict) -> BytesIO:
        """Generates a multi-sheet XLSX workbook."""
        output = BytesIO()
        # Options to improve memory usage and compatibility
        workbook = xlsxwriter.Workbook(output, {'in_memory': True, 'remove_timezone': True})

        for report_type, result in report_data.items():
            # Skip sheets with errors
            if result.get('error'):
                logger.warning(f"Skipping sheet for {report_type} due to error: {result['error']}")
                continue # Move to the next report type

            # Determine sheet name (limit length for compatibility)
            sheet_name = result.get('params', {}).get("sheet_name", report_type.replace("_", " ").title())[:31] # Max 31 chars
            worksheet = workbook.add_worksheet(sheet_name)

            # Write data, stats, charts to the sheet
            if 'data' in result and 'params' in result and 'columns' in result['params']:
                ReportService._write_sheet_data_with_analysis(
                    worksheet=worksheet,
                    workbook=workbook,
                    data=result['data'],
                    columns=result['params']['columns'],
                    analysis=result.get('analysis',{}), # Pass analysis results
                    sheet_params=result['params'] # Pass sheet-specific params
                )
            else:
                 logger.warning(f"Missing required data or parameters for sheet '{sheet_name}'.")
                 worksheet.write(0, 0, "Report data or configuration missing.") # Indicate issue on sheet

        workbook.close() # Finalize workbook
        output.seek(0) # Rewind buffer
        return output

    # --- CSV Generation ---
    @staticmethod
    def _generate_csv_report(data: List[Dict], columns: List[str], analysis: Dict) -> BytesIO:
        """Generates a single CSV report in memory."""
        output = StringIO()
        # Use DictWriter for better handling of missing keys and quoting
        writer = csv.DictWriter(output, fieldnames=columns, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for row_dict in data:
            # Ensure only requested columns are written, handle missing keys gracefully
            filtered_row = {col: str(row_dict.get(col)) if row_dict.get(col) is not None else '' for col in columns}
            writer.writerow(filtered_row)
        output.seek(0)
        # Return as BytesIO encoded in UTF-8 (common for CSV)
        return BytesIO(output.getvalue().encode('utf-8'))

    @staticmethod
    def _generate_multi_csv_zip(report_data: Dict[str, Dict], global_params: dict) -> BytesIO:
        """Generates a ZIP archive containing multiple CSV files."""
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for report_type, result in report_data.items():
                if result.get('error'):
                    logger.warning(f"Skipping CSV for {report_type} due to error: {result['error']}")
                    # Optionally write an error file to the zip
                    error_filename = f"{report_type}_error.txt"
                    zipf.writestr(error_filename, f"Error generating report: {result['error']}")
                    continue

                if 'data' in result and 'params' in result and 'columns' in result['params']:
                    csv_filename = f"{report_type}.csv"
                    logger.info(f"Generating CSV data for {csv_filename}...")
                    # Use _generate_csv_report which returns BytesIO
                    csv_bytes_io = ReportService._generate_csv_report(
                        result['data'],
                        result['params']['columns'],
                        result.get('analysis', {}) # Pass analysis even if not used by CSV
                    )
                    # Write the content of BytesIO to the zip file
                    zipf.writestr(csv_filename, csv_bytes_io.getvalue())
                    logger.info(f"Added {csv_filename} to ZIP archive.")
                else:
                    logger.warning(f"Missing data or columns for CSV '{report_type}', skipping.")
                    # Optionally write an empty file or error file
                    zipf.writestr(f"{report_type}_nodata.txt", "No data or columns configured for this report type.")

        zip_buffer.seek(0)
        return zip_buffer

    # --- PDF Generation ---
    @staticmethod
    def _generate_multi_section_pdf(report_data: Dict[str, Dict], global_params: dict) -> BytesIO:
        """Generates a single PDF document with sections for each entity."""
        buffer = BytesIO()
        # Use letter size, adjust if needed
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                leftMargin=0.75*inch, rightMargin=0.75*inch,
                                topMargin=0.75*inch, bottomMargin=0.75*inch)
        styles = getSampleStyleSheet()
        story = []
        first_section = True

        # Overall Title (Optional)
        overall_title = global_params.get("report_title", "Full System Report")
        story.append(Paragraph(overall_title, styles['h1']))
        story.append(Spacer(1, 0.3*inch))

        for report_type, result in report_data.items():
            if not first_section:
                story.append(PageBreak()) # Add page break before each new section (except the first)
            first_section = False

            if result.get('error'):
                logger.warning(f"Adding error section for {report_type} to PDF.")
                story.append(Paragraph(f"Error: {report_type.replace('_',' ').title()}", styles['h2']))
                story.append(Paragraph(f"Could not generate report: {result['error']}", styles['Normal']))
                continue

            # Ensure data and params exist
            if 'data' not in result or 'params' not in result or 'columns' not in result['params']:
                 logger.warning(f"Missing data/params/columns for PDF section '{report_type}'.")
                 story.append(Paragraph(f"Error: {report_type.replace('_',' ').title()}", styles['h2']))
                 story.append(Paragraph("Report configuration incomplete.", styles['Normal']))
                 continue

            data = result['data']
            columns = result['params']['columns']
            analysis = result.get('analysis', {})
            section_params = result['params']
            section_title = section_params.get("sheet_name", report_type.replace("_", " ").title()) # Use sheet name as section title

            # --- Section Title ---
            story.append(Paragraph(section_title, styles['h2']))
            story.append(Spacer(1, 0.2*inch))

            # --- Summary Stats ---
            if analysis and analysis.get('summary_stats'):
                story.append(Paragraph("Summary Statistics:", styles['h3']))
                stats = analysis['summary_stats']; simple_stats = {k:v for k,v in stats.items() if not isinstance(v, (dict, list))}
                for key, value in simple_stats.items(): story.append(Paragraph(f"<b>{key.replace('_',' ').title()}:</b> {value}", styles['Normal']))
                story.append(Spacer(1, 0.1*inch))

            # --- Data Table ---
            if data:
                table_data = [columns]; table_data.extend([[str(row.get(col, '')) for col in columns] for row in data])
                # Adjust page size based on columns for this specific table
                num_cols = len(columns)
                # Determine if landscape is needed (heuristic)
                # Calculate approximate text width (very rough estimate)
                avg_char_width = 5 # points per char (adjust based on font/size)
                total_text_width_est = sum(max(len(str(row.get(c,''))) for row in data+[{}]) * avg_char_width for c in columns) + num_cols * 10 # Add padding
                page_width_points = letter[0] - 1.5 * inch * 72 # Usable width in points
                if num_cols > 7 or total_text_width_est > page_width_points * 1.5: # Use landscape if many columns or estimate is wide
                    current_pagesize = landscape(letter)
                else:
                    current_pagesize = letter

                available_width = current_pagesize[0] - 1.5*inch # Account for margins

                col_width = available_width / num_cols if num_cols > 0 else available_width;
                col_widths = [col_width] * num_cols
                # Create and style the table
                style = TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.darkgrey),
                                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                                    ('FONTSIZE', (0, 0), (-1, -1), 7), # Small font for tables
                                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE')])
                table = Table(table_data, colWidths=col_widths, repeatRows=1); table.setStyle(style);
                story.append(table); story.append(Spacer(1, 0.2*inch))
            else:
                 story.append(Paragraph("No data available for this section.", styles['Italic']))
                 story.append(Spacer(1, 0.2*inch))

            # --- Charts ---
            if analysis and analysis.get('charts'):
                story.append(Paragraph("Charts:", styles['h3']))
                for chart_key, chart_bytes in analysis['charts'].items():
                     if isinstance(chart_bytes, BytesIO):
                         try: img = RLImage(chart_bytes, width=5*inch, height=2.5*inch); img.hAlign = 'CENTER'; story.append(img); story.append(Spacer(1, 0.1*inch))
                         except Exception as img_err: logger.error(f"Error adding chart {chart_key} to PDF: {img_err}"); story.append(Paragraph(f"<i>Error displaying chart: {chart_key}</i>", styles['Italic']))
                     else: logger.warning(f"Chart data for {chart_key} is not BytesIO.")

        try:
            doc.build(story)
        except Exception as build_err:
             logger.error(f"Error building multi-section PDF document: {build_err}", exc_info=True)
             raise ValueError(f"Failed to build PDF: {build_err}")

        buffer.seek(0)
        return buffer

    # --- DOCX Generation ---
    @staticmethod
    def _generate_multi_section_docx(report_data: Dict[str, Dict], global_params: dict) -> BytesIO:
        """Generates a single DOCX document with sections for each entity."""
        document = Document()
        buffer = BytesIO()
        first_section = True

        # Overall Title (Optional)
        overall_title = global_params.get("report_title", "Full System Report")
        document.add_heading(overall_title, level=0).alignment = WD_ALIGN_PARAGRAPH.CENTER
        document.add_paragraph()

        for report_type, result in report_data.items():
            if not first_section:
                document.add_page_break()
            first_section = False

            section_params = result.get('params', {})
            section_title = section_params.get("sheet_name", report_type.replace("_", " ").title())
            document.add_heading(section_title, level=1) # Section heading

            if result.get('error'):
                logger.warning(f"Adding error section for {report_type} to DOCX.")
                document.add_paragraph(f"Could not generate report: {result['error']}")
                continue

            if 'data' not in result or 'params' not in result or 'columns' not in result['params']:
                 logger.warning(f"Missing data/params/columns for DOCX section '{report_type}'.")
                 document.add_paragraph("Report configuration incomplete.")
                 continue

            data = result['data']
            columns = result['params']['columns']
            analysis = result.get('analysis', {})

            # --- Summary Stats ---
            if analysis and analysis.get('summary_stats'):
                document.add_heading("Summary Statistics", level=2)
                stats = analysis['summary_stats']; simple_stats = {k:v for k,v in stats.items() if not isinstance(v, (dict, list))}
                for key, value in simple_stats.items(): p = document.add_paragraph(); p.add_run(key.replace("_"," ").title() + ": ").bold = True; p.add_run(str(value))
                document.add_paragraph()

            # --- Data Table ---
            if data:
                try:
                    table = document.add_table(rows=1, cols=len(columns)); table.style = 'Table Grid'; table.autofit = False; table.allow_autofit = False
                    hdr_cells = table.rows[0].cells
                    for i, col_name in enumerate(columns): hdr_cells[i].text = col_name; hdr_cells[i].paragraphs[0].runs[0].font.bold = True; hdr_cells[i].paragraphs[0].runs[0].font.size = Pt(9)

                    for row_data in data:
                        row_cells = table.add_row().cells
                        for i, col_name in enumerate(columns): cell_value = str(row_data.get(col_name, '')); row_cells[i].text = cell_value; row_cells[i].paragraphs[0].runs[0].font.size = Pt(8)
                    document.add_paragraph()
                except Exception as table_err: logger.error(f"Error creating DOCX table for {report_type}: {table_err}"); document.add_paragraph(f"Error creating data table: {table_err}")
            else:
                 document.add_paragraph("No data available for this section.")
                 document.add_paragraph()

            # --- Charts ---
            if analysis and analysis.get('charts'):
                 document.add_heading("Charts", level=2)
                 for chart_key, chart_bytes in analysis['charts'].items():
                     if isinstance(chart_bytes, BytesIO):
                         try: document.add_picture(chart_bytes, width=Inches(5.5)); document.add_paragraph(chart_key.replace("_"," ").title(), style='Caption')
                         except Exception as img_err: logger.error(f"Error adding chart {chart_key} to DOCX: {img_err}"); document.add_paragraph(f"Error displaying chart: {chart_key}")
                     else: logger.warning(f"Chart data for {chart_key} is not BytesIO.")

        document.save(buffer)
        buffer.seek(0)
        return buffer

    # --- Specific PPTX Generator for Form Submissions ---
    @staticmethod
    def _generate_form_submission_pptx(objects: List[Dict], columns: List[str], analysis: Dict, report_params: dict) -> BytesIO:
        """Generates a specific PowerPoint (PPTX) report for Form Submissions."""
        # Note: data parameter renamed to objects to reflect passing original objects
        prs = Presentation()
        buffer = BytesIO()

        # --- Title Slide ---
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        title = slide.shapes.title
        subtitle = slide.placeholders[1]
        report_title = report_params.get("report_title", "Form Submission Report")
        title.text = report_title
        subtitle.text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # --- Summary Stats Slide ---
        if analysis and analysis.get('summary_stats'):
            stats_slide_layout = prs.slide_layouts[5] # Blank layout
            slide = prs.slides.add_slide(stats_slide_layout)
            shapes = slide.shapes
            shapes.title.text = "Submission Statistics"
            left, top, width, height = PptxInches(0.5), PptxInches(1.0), PptxInches(8.0), PptxInches(5.5)
            txBox = shapes.add_textbox(left, top, width, height)
            tf = txBox.text_frame; tf.word_wrap = True
            stats = analysis['summary_stats']
            p = tf.add_paragraph(); p.text = f"Total Submissions: {stats.get('record_count', 'N/A')}"; p.font.bold = True; p.font.size = PptxPt(18)
            p = tf.add_paragraph(); p.text = f"First Submission: {stats.get('first_submission', 'N/A')}"; p.font.size = PptxPt(14)
            p = tf.add_paragraph(); p.text = f"Last Submission: {stats.get('last_submission', 'N/A')}"; p.font.size = PptxPt(14)
            if 'submissions_per_user_top5' in stats:
                 p = tf.add_paragraph(); p.text = "\nTop Submitters:"; p.font.bold = True; p.font.size = PptxPt(16)
                 for user, count in stats['submissions_per_user_top5'].items():
                     p = tf.add_paragraph(); p.text = f"- {user}: {count}"; p.font.size = PptxPt(12); p.level = 1

        # --- Chart Slides ---
        if analysis and analysis.get('charts'):
             for chart_key, chart_bytes in analysis['charts'].items():
                 if isinstance(chart_bytes, BytesIO):
                     try:
                         chart_slide_layout = prs.slide_layouts[5] # Blank layout
                         slide = prs.slides.add_slide(chart_slide_layout)
                         shapes = slide.shapes
                         shapes.title.text = chart_key.replace("_"," ").title()
                         left, top, width = PptxInches(1), PptxInches(1.5), PptxInches(8)
                         pic = shapes.add_picture(chart_bytes, left, top, width=width)
                     except Exception as img_err:
                         logger.error(f"Error adding chart {chart_key} to PPTX: {img_err}")
                         error_slide_layout = prs.slide_layouts[5]
                         slide = prs.slides.add_slide(error_slide_layout)
                         shapes = slide.shapes; shapes.title.text = f"Error: {chart_key}"
                         tf = shapes.add_textbox(PptxInches(1), PptxInches(1.5), PptxInches(8), PptxInches(1)).text_frame
                         tf.text = f"Could not generate chart: {img_err}"
                 else: logger.warning(f"Chart data for {chart_key} is not BytesIO.")

        # --- Data Table Slide (Optional) ---
        if objects and report_params.get("include_data_table_in_ppt", True): # Use original objects
            table_slide_layout = prs.slide_layouts[5] # Blank layout
            slide = prs.slides.add_slide(table_slide_layout)
            shapes = slide.shapes; shapes.title.text = "Submission Data Sample"
            table_columns = ReportService.ENTITY_CONFIG['form_submissions']['default_columns']
            max_ppt_rows = report_params.get("max_ppt_table_rows", 15)
            rows = min(len(objects), max_ppt_rows) + 1 # Limit rows + header
            cols = len(table_columns);
            left, top, width, height = PptxInches(0.3), PptxInches(1.2), PptxInches(9.4), PptxInches(5.8)

            try:
                table = shapes.add_table(rows, cols, left, top, width, height).table
                widths = [0.5, 0.7, 2.5, 1.5, 2.0, 2.0]
                for i, w in enumerate(widths):
                    if i < cols: table.columns[i].width = PptxInches(w)

                for c_idx, col_name in enumerate(table_columns):
                    cell = table.cell(0, c_idx)
                    cell.text = col_name.replace("_", " ").title()
                    cell.text_frame.paragraphs[0].font.bold = True
                    cell.text_frame.paragraphs[0].font.size = PptxPt(10)
                    cell.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE

                for r_idx, row_data_obj in enumerate(objects[:max_ppt_rows]): # Iterate original objects
                    for c_idx, col_name in enumerate(table_columns):
                        cell_value = str(ReportService._get_attribute_recursive(row_data_obj, col_name) or '')
                        cell = table.cell(r_idx + 1, c_idx)
                        cell.text = cell_value
                        cell.text_frame.paragraphs[0].font.size = PptxPt(9)
                        cell.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE

            except Exception as table_err:
                logger.error(f"Error creating PPTX table: {table_err}", exc_info=True)
                tf = shapes.add_textbox(left, top, width, height).text_frame
                tf.text = f"Error creating data table: {table_err}"

        prs.save(buffer); buffer.seek(0); return buffer

    # --- Main Report Generation Method ---
    @staticmethod
    def generate_report(report_params: dict, user: User) -> Tuple[Optional[BytesIO], Optional[str], Optional[str], Optional[str]]:
        """
        Generates a report based on the provided parameters, checking permissions first.
        Handles single entity requests for XLSX, CSV, PDF, DOCX, PPTX.
        Handles multi-entity requests ("report_type": "all" or list) for:
          - XLSX (multi-sheet)
          - CSV (ZIP archive)
          - PDF (ZIP archive)
        DOCX/PPTX multi-entity requests are not supported.

        Returns:
            Tuple[Optional[BytesIO], Optional[str], Optional[str], Optional[str]]:
                - BytesIO buffer containing the report file, or None on error.
                - Filename for the report, or None on error.
                - MIME type for the response, or None on error.
                - Error message string, or None on success.
        """
        try:
            report_type_req = report_params.get("report_type")
            output_format = report_params.get("output_format", "xlsx").lower()
            base_filename = report_params.get("filename")

            # --- Parameter Validation ---
            if not report_type_req:
                return None, None, None, "Missing required report parameter: report_type"

            supported_formats = ["xlsx", "csv", "pdf", "docx", "pptx"]
            if output_format not in supported_formats:
                return None, None, None, f"Unsupported output format: {output_format}. Supported: {', '.join(supported_formats)}"

            # --- Determine Report Types and Mode ---
            is_multi_entity = False
            report_types_to_process = []

            if isinstance(report_type_req, list):
                if output_format not in ["xlsx", "csv", "pdf"]: # Allow PDF for multi via ZIP
                     return None, None, None, f"Multi-entity reports are only supported for XLSX, CSV (ZIP), and PDF (ZIP) formats, not {output_format.upper()}."
                is_multi_entity = True
                report_types_to_process = report_type_req
                if not base_filename: base_filename = f"multi_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            elif report_type_req == "all":
                if output_format not in ["xlsx", "csv", "pdf"]: # Allow PDF for multi via ZIP
                     return None, None, None, f"Report for 'all' entities is only supported for XLSX, CSV (ZIP), and PDF (ZIP) formats, not {output_format.upper()}."
                is_multi_entity = True
                report_types_to_process = list(ReportService.ENTITY_CONFIG.keys())
                if not base_filename: base_filename = f"full_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            else: # Single entity request
                is_multi_entity = False
                report_types_to_process = [report_type_req]
                if not base_filename: base_filename = f"report_{report_type_req}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # --- Process Each Report Configuration ---
            processed_data = {}

            for report_type in report_types_to_process:
                 if report_type not in ReportService.ENTITY_CONFIG:
                     error_msg = f"Unsupported report type: {report_type}"
                     if is_multi_entity: logger.warning(error_msg); processed_data[report_type] = {'error': error_msg}; continue
                     else: return None, None, None, error_msg

                 config = ReportService.ENTITY_CONFIG[report_type]
                 model_cls = config['model']
                 required_permission_entity = config['view_permission_entity']

                 # --- Permission Check ---
                 if not PermissionManager.has_permission(user, "view", required_permission_entity):
                     error_msg = f"Permission denied: Cannot generate report for {report_type}."
                     logger.warning(f"User {user.username} lacks permission for {report_type} report.")
                     if is_multi_entity: processed_data[report_type] = {'error': error_msg}; continue
                     else: return None, None, None, error_msg

                 # --- Determine Columns, Filters, Sort ---
                 has_detailed_params = any(k in report_params for k in ['columns', 'filters', 'sort_by'])

                 if is_multi_entity or not has_detailed_params:
                     columns = config.get('default_columns')
                     if not columns:
                         error_msg = f"Default columns not configured for report type: {report_type}"
                         if is_multi_entity: logger.error(error_msg); processed_data[report_type] = {'error': error_msg}; continue
                         else: return None, None, None, error_msg
                     filters = []
                     sort_by = config.get('default_sort', [])
                 else: # Detailed single request
                     columns = report_params.get("columns", config.get('default_columns'))
                     if not columns:
                          return None, None, None, f"Columns must be specified or default columns must be configured for report type: {report_type}"
                     filters = report_params.get("filters", [])
                     sort_by = report_params.get("sort_by", config.get('default_sort', []))

                 current_params = {
                     "columns": columns, "filters": filters, "sort_by": sort_by,
                     "report_type": report_type,
                     "sheet_name": report_params.get(f"{report_type}_sheet_name", report_type.replace("_", " ").title()),
                     "table_options": report_params.get(f"{report_type}_table_options", report_params.get("table_options", {})),
                     "include_data_table_in_ppt": report_params.get("include_data_table_in_ppt", False),
                     "max_ppt_table_rows": report_params.get("max_ppt_table_rows", 15),
                     "report_title": report_params.get("report_title")
                 }

                 # --- Data Fetching & Processing ---
                 try:
                     logger.info(f"Fetching data for report type '{report_type}'...")
                     fetched_objects = ReportService._fetch_data(model_cls, current_params['filters'], current_params['sort_by'], user, current_params['columns'])
                     logger.info(f"Fetched {len(fetched_objects)} records for '{report_type}'.")

                     logger.info(f"Flattening data for '{report_type}'...")
                     if fetched_objects and isinstance(fetched_objects[0], model_cls):
                         data = ReportService._flatten_data(fetched_objects, current_params['columns'])
                         logger.info(f"Flattened data generated for '{report_type}'.")
                     else:
                         # Handle cases where fetch might return non-model objects or be empty
                         data = []
                         if fetched_objects: # Log if fetched_objects is not None but not expected type
                             logger.warning(f"Fetched data for {report_type} is not a list of expected model instances.")
                         else: # Log if fetch returned None or empty list
                              logger.warning(f"No data fetched for {report_type}, using empty list.")


                     # --- Data Analysis (only if needed) ---
                     analysis_results = {}
                     if output_format in ["pdf", "docx", "pptx"]:
                         logger.info(f"Analyzing data for '{report_type}'...")
                         analysis_results = ReportService._analyze_data(data, report_type)
                         logger.info(f"Data analysis complete for '{report_type}'.")

                     processed_data[report_type] = {
                         'error': None,
                         'data': data,            # Use flattened data
                         'objects': fetched_objects, # Store original objects for PPTX/complex cases
                         'params': current_params,
                         'analysis': analysis_results
                     }

                 except Exception as fetch_err:
                     error_msg = f"Error processing data for {report_type}."
                     logger.error(f"{error_msg}: {fetch_err}", exc_info=True)
                     if is_multi_entity: processed_data[report_type] = {'error': error_msg}; continue
                     else: return None, None, None, error_msg


            # --- Report Generation ---
            final_buffer = None
            final_filename = None
            mime_type = None

            if not processed_data and is_multi_entity:
                 return None, None, None, "No data could be generated for the requested report types due to errors or permissions."

            # --- Generate Output Based on Format ---
            if output_format == "xlsx":
                final_filename = f"{base_filename}.xlsx"
                mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                logger.info(f"Generating XLSX report '{final_filename}'...")
                final_buffer = ReportService._generate_multi_sheet_xlsx(processed_data, report_params)

            elif output_format == "csv":
                 if is_multi_entity:
                     final_filename = f"{base_filename}.zip"
                     mime_type = 'application/zip'
                     logger.info(f"Generating Multi-CSV ZIP report '{final_filename}'...")
                     final_buffer = ReportService._generate_multi_csv_zip(processed_data, report_params)
                 else:
                     single_report_type = list(processed_data.keys())[0]
                     result = processed_data[single_report_type]
                     if result.get('error'): return None, None, None, result['error']
                     final_filename = f"{base_filename}.csv"
                     mime_type = 'text/csv'
                     logger.info(f"Generating CSV report '{final_filename}'...")
                     final_buffer = ReportService._generate_csv_report(result['data'], result['params']['columns'], result['analysis'])

            elif output_format == "pdf":
                 if is_multi_entity:
                     final_filename = f"{base_filename}_pdfs.zip"
                     mime_type = 'application/zip'
                     logger.info(f"Generating Multi-PDF ZIP report '{final_filename}'...")
                     zip_buffer = BytesIO()
                     with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                         # Generate Consolidated PDF first
                         logger.info("Generating consolidated PDF for ZIP archive...")
                         try:
                             consolidated_pdf_buffer = ReportService._generate_multi_section_pdf(processed_data, report_params)
                             zipf.writestr("_consolidated_report.pdf", consolidated_pdf_buffer.getvalue())
                             logger.info("Added _consolidated_report.pdf to ZIP archive.")
                         except Exception as consol_err:
                             logger.error(f"Error generating consolidated PDF for ZIP: {consol_err}", exc_info=True)
                             zipf.writestr("_consolidated_report_error.txt", f"Error generating consolidated PDF: {consol_err}")

                         # Generate Individual PDFs
                         for report_type, result in processed_data.items():
                             if result.get('error'):
                                 logger.warning(f"Skipping individual PDF for {report_type} in ZIP due to error: {result['error']}")
                                 zipf.writestr(f"{report_type}_error.txt", f"Error generating report: {result['error']}")
                                 continue
                             if 'data' in result and 'params' in result and 'columns' in result['params']:
                                 pdf_filename = f"{report_type}.pdf"
                                 logger.info(f"Generating individual PDF data for {pdf_filename}...")
                                 try:
                                     # Generate single PDF section in memory
                                     single_pdf_buffer = ReportService._generate_multi_section_pdf({report_type: result}, report_params) # Generate single section
                                     zipf.writestr(pdf_filename, single_pdf_buffer.getvalue())
                                     logger.info(f"Added {pdf_filename} to ZIP archive.")
                                 except Exception as pdf_zip_err:
                                     logger.error(f"Error generating individual PDF for {report_type} for ZIP: {pdf_zip_err}", exc_info=True)
                                     zipf.writestr(f"{report_type}_error.txt", f"Error generating individual PDF: {pdf_zip_err}")
                             else:
                                 logger.warning(f"Missing data/params/columns for PDF '{report_type}', skipping ZIP entry.")
                                 zipf.writestr(f"{report_type}_nodata.txt", "No data or columns configured.")
                     zip_buffer.seek(0)
                     final_buffer = zip_buffer
                 else:
                     # Generate single PDF
                     single_report_type = list(processed_data.keys())[0]
                     result = processed_data[single_report_type]
                     if result.get('error'): return None, None, None, result['error']
                     final_filename = f"{base_filename}.pdf"
                     mime_type = 'application/pdf'
                     logger.info(f"Generating PDF report '{final_filename}'...")
                     final_buffer = ReportService._generate_multi_section_pdf({single_report_type: result}, report_params)

            elif output_format == "docx":
                 if is_multi_entity: return None, None, None, "DOCX export is only supported for single entity report requests."
                 single_report_type = list(processed_data.keys())[0]
                 result = processed_data[single_report_type]
                 if result.get('error'): return None, None, None, result['error']
                 final_filename = f"{base_filename}.docx"
                 mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                 logger.info(f"Generating DOCX report '{final_filename}'...")
                 final_buffer = ReportService._generate_multi_section_docx({single_report_type: result}, report_params)


            elif output_format == "pptx":
                 if is_multi_entity: return None, None, None, "PPTX export is only supported for single entity report requests."
                 single_report_type = list(processed_data.keys())[0]
                 result = processed_data[single_report_type]
                 if result.get('error'): return None, None, None, result['error']
                 final_filename = f"{base_filename}.pptx"
                 mime_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
                 logger.info(f"Generating PPTX report '{final_filename}'...")
                 config = ReportService.ENTITY_CONFIG[single_report_type]
                 pptx_gen_func_name = config.get('pptx_generator')
                 if pptx_gen_func_name and hasattr(ReportService, pptx_gen_func_name):
                      # Pass original objects ('objects') to PPTX generator
                      final_buffer = getattr(ReportService, pptx_gen_func_name)(result['objects'], result['params']['columns'], result['analysis'], result['params'])
                 else:
                      logger.error(f"PPTX generation not specifically implemented for report type: {single_report_type}")
                      return None, None, None, f"PPTX generation is not supported for report type: {single_report_type}"

            else:
                 return None, None, None, f"Internal error: Unhandled output format: {output_format}"

            # --- Final Return ---
            if final_buffer:
                logger.info(f"{output_format.upper()} report '{final_filename}' generated successfully.")
                return final_buffer, final_filename, mime_type, None
            else:
                 logger.error(f"Report generation failed for format {output_format}, buffer is None.")
                 return None, None, None, f"Failed to generate report in {output_format} format."

        except Exception as e:
            logger.error(f"Failed to generate report: {str(e)}")
            logger.error(traceback.format_exc())
            return None, None, None, f"An error occurred during report generation. Please check logs for details."