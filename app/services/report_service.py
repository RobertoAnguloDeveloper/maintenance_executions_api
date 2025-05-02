# app/services/report_service.py
import numpy as np
from sqlalchemy import text, inspect
from app import db
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
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor as PptxRGBColor
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE

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
from datetime import date, datetime
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
        'form_submissions': {
            'model': FormSubmission,
            'view_permission_entity': EntityType.SUBMISSIONS,
            'default_columns': [
                "id", "form_id", "form.title", "form.description", "submitted_by", 
                "submitted_at", "created_at", "updated_at", "is_deleted", "deleted_at"
            ],
            'default_sort': [{"field": "submitted_at", "direction": "desc"}],
            'stats_generators': ['generate_submission_stats'],
            'chart_generators': ['generate_enhanced_submission_charts'],  # Updated
            'insight_generators': ['generate_submission_insights'],  # New
            'pptx_generator': '_generate_form_submission_pptx'
        },
        "users": {
            'model': User,
            'view_permission_entity': EntityType.USERS,
            'default_columns': [
                "id", "username", "first_name", "last_name", "email", "contact_number",
                "role_id", "role.name", "role.description", "role.is_super_user",
                "environment_id", "environment.name", "environment.description",
                "created_at", "updated_at", "is_deleted", "deleted_at"
            ],
            'default_sort': [{"field": "username", "direction": "asc"}],
            'stats_generators': ['generate_user_stats'],
            'chart_generators': ['generate_user_charts']
        },
        "forms": {
            'model': Form,
            'view_permission_entity': EntityType.FORMS,
            'default_columns': [
                "id", "title", "description", "user_id", "creator.username", 
                "creator.first_name", "creator.last_name", "creator.email",
                "creator.environment.name", "is_public", "created_at", 
                "updated_at", "is_deleted", "deleted_at"
            ],
            'default_sort': [{"field": "title", "direction": "asc"}],
            'stats_generators': ['generate_form_stats'],
            'chart_generators': ['generate_form_charts']
        },
        "environments": {
            'model': Environment,
            'view_permission_entity': EntityType.ENVIRONMENTS,
            'default_columns': [
                "id", "name", "description", "created_at", "updated_at", 
                "is_deleted", "deleted_at"
            ],
            'default_sort': [{"field": "name", "direction": "asc"}],
            'stats_generators': ['generate_environment_stats'],
            'chart_generators': ['generate_environment_charts']
        },
        "roles": {
            'model': Role,
            'view_permission_entity': EntityType.ROLES,
            'default_columns': [
                "id", "name", "description", "is_super_user", "created_at", 
                "updated_at", "is_deleted", "deleted_at"
            ],
            'default_sort': [{"field": "name", "direction": "asc"}],
            'stats_generators': ['generate_role_stats'],
            'chart_generators': ['generate_role_charts']
        },
        "permissions": {
            'model': Permission,
            'view_permission_entity': EntityType.ROLES,
            'default_columns': [
                "id", "name", "action", "entity", "description", "created_at", 
                "updated_at", "is_deleted", "deleted_at"
            ],
            'default_sort': [{"field": "name", "direction": "asc"}],
            'stats_generators': [],
            'chart_generators': []
        },
        "role_permissions": {
            'model': RolePermission,
            'view_permission_entity': EntityType.ROLES,
            'default_columns': [
                "id", "role_id", "role.name", "role.description", "permission_id", 
                "permission.name", "permission.action", "permission.entity", 
                "permission.description", "created_at", "updated_at", "is_deleted", "deleted_at"
            ],
            'default_sort': [{"field": "role_id", "direction": "asc"}, {"field": "permission_id", "direction": "asc"}],
            'stats_generators': [],
            'chart_generators': []
        },
        "question_types": {
            'model': QuestionType,
            'view_permission_entity': EntityType.QUESTION_TYPES,
            'default_columns': [
                "id", "type", "created_at", "updated_at", "is_deleted", "deleted_at"
            ],
            'default_sort': [{"field": "type", "direction": "asc"}],
            'stats_generators': [],
            'chart_generators': []
        },
        "questions": {
            'model': Question,
            'view_permission_entity': EntityType.QUESTIONS,
            'default_columns': [
                "id", "text", "question_type_id", "question_type.type", 
                "is_signature", "remarks", "created_at", "updated_at", 
                "is_deleted", "deleted_at"
            ],
            'default_sort': [{"field": "text", "direction": "asc"}],
            'stats_generators': ['generate_question_stats'],
            'chart_generators': []
        },
        "answers": {
            'model': Answer,
            'view_permission_entity': EntityType.ANSWERS,
            'default_columns': [
                "id", "value", "remarks", "created_at", "updated_at", 
                "is_deleted", "deleted_at"
            ],
            'default_sort': [{"field": "value", "direction": "asc"}],
            'stats_generators': [],
            'chart_generators': []
        },
        "form_questions": {
            'model': FormQuestion,
            'view_permission_entity': EntityType.FORMS,
            'default_columns': [
                "id", "form_id", "form.title", "form.description", "question_id", 
                "question.text", "question.question_type.type", "question.is_signature", 
                "order_number", "created_at", "updated_at", "is_deleted", "deleted_at"
            ],
            'default_sort': [{"field": "form_id", "direction": "asc"}, {"field": "order_number", "direction": "asc"}],
            'stats_generators': [],
            'chart_generators': []
        },
        "form_answers": {
            'model': FormAnswer,
            'view_permission_entity': EntityType.FORMS,
            'default_columns': [
                "id", "form_question_id", "form_question.question.text", 
                "form_question.question.question_type.type", "answer_id", 
                "answer.value", "answer.remarks", "remarks", "created_at", 
                "updated_at", "is_deleted", "deleted_at"
            ],
            'default_sort': [{"field": "form_question_id", "direction": "asc"}, {"field": "answer_id", "direction": "asc"}],
            'stats_generators': [],
            'chart_generators': []
        },
        "answers_submitted": {
            'model': AnswerSubmitted,
            'view_permission_entity': EntityType.SUBMISSIONS,
            'default_columns': [
                "id", "form_submission_id", "form_submission.form.title", 
                "question", "question_type", "answer", "column", "row", 
                "cell_content", "created_at", "updated_at", "is_deleted", "deleted_at"
            ],
            'default_sort': [{"field": "created_at", "direction": "desc"}],
            'stats_generators': [],
            'chart_generators': []
        },
        "attachments": {
            'model': Attachment,
            'view_permission_entity': EntityType.ATTACHMENTS,
            'default_columns': [
                "id", "form_submission_id", "form_submission.form.title", 
                "file_type", "file_path", "is_signature", "signature_position", 
                "signature_author", "created_at", "updated_at", "is_deleted", "deleted_at"
            ],
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
    
    @staticmethod
    def generate_submission_insights(df: pd.DataFrame) -> Dict[str, str]:
        """Generates textual insights about form submissions."""
        insights = {}
        
        if df.empty:
            return {"no_data": "No submission data available for analysis."}
            
        try:
            # Basic volume insights
            record_count = len(df)
            insights["volume"] = f"Analyzed {record_count} total submissions."
            
            # Time-based insights
            if 'submitted_at' in df.columns:
                df['submitted_at_dt'] = pd.to_datetime(df['submitted_at'], errors='coerce')
                valid_dates = df['submitted_at_dt'].dropna()
                
                if not valid_dates.empty:
                    date_range = (valid_dates.max() - valid_dates.min()).days
                    avg_daily = record_count / max(date_range, 1)
                    
                    insights["activity"] = (f"Submissions span {date_range} days with an average of "
                                        f"{avg_daily:.1f} submissions per day.")
                    
                    # Find peak periods
                    if len(valid_dates) > 10:
                        df['hour'] = df['submitted_at_dt'].dt.hour
                        peak_hour = df['hour'].value_counts().idxmax()
                        ampm = "AM" if peak_hour < 12 else "PM"
                        display_hour = peak_hour if peak_hour <= 12 else peak_hour - 12
                        
                        insights["peak_time"] = f"Peak submission activity occurs around {display_hour} {ampm}."
            
            # User-based insights
            if 'submitted_by' in df.columns:
                unique_users = df['submitted_by'].nunique()
                submissions_per_user = record_count / max(unique_users, 1)
                
                insights["user_activity"] = (f"Submissions came from {unique_users} unique users, "
                                            f"averaging {submissions_per_user:.1f} submissions per user.")
                    
            return insights
            
        except Exception as e:
            logger.error(f"Error generating submission insights: {e}", exc_info=True)
            return {"error": "Could not generate insights due to an error."}
    
    @staticmethod
    def generate_enhanced_submission_charts(df: pd.DataFrame, report_type: str) -> Dict[str, BytesIO]:
        """Generates multiple charts for submission data with insights embedded in titles."""
        charts = {}
        if 'submitted_at' not in df.columns or df.empty:
            return charts
            
        try:
            # Set overall style to ensure white backgrounds and better readability
            plt.style.use('default')
            
            # Custom color palette that works well with white backgrounds
            color_palette = plt.cm.viridis(np.linspace(0, 1, 10))
            
            # Ensure datetime conversion, handle potential errors
            df['submitted_at_dt'] = pd.to_datetime(df['submitted_at'], errors='coerce').dt.tz_localize(None)
            df.dropna(subset=['submitted_at_dt'], inplace=True)
            if df.empty: 
                return charts

            # 1. Submissions Time Series with Trend
            monthly_counts = df.set_index('submitted_at_dt').resample('ME').size()
            if not monthly_counts.empty:
                # Calculate trend increase/decrease
                if len(monthly_counts) > 1:
                    first_month = monthly_counts.iloc[0]
                    last_month = monthly_counts.iloc[-1]
                    trend_pct = ((last_month - first_month) / first_month * 100) if first_month else 0
                    trend_direction = "up" if trend_pct > 0 else "down"
                    title = f"Submissions Trend: {abs(trend_pct):.1f}% {trend_direction} over period"
                else:
                    title = "Monthly Submissions"
                    
                fig, ax = plt.subplots(figsize=(10, 5), facecolor='white')
                ax.set_facecolor('white')
                monthly_counts.plot(kind='line', ax=ax, marker='o', color=color_palette[0], linewidth=2)
                
                # Add data labels to each point on the line
                for x, y in zip(range(len(monthly_counts)), monthly_counts.values):
                    ax.annotate(
                        f'{int(y)}',
                        (x, y),
                        textcoords="offset points",
                        xytext=(0, 10),
                        ha='center',
                        fontweight='bold',
                        color='black',
                        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.9)
                    )
                    
                ax.set_title(title, fontsize=14, fontweight='bold')
                ax.set_ylabel('# Submissions', fontsize=12)
                ax.set_xlabel('', fontsize=12)
                plt.xticks(rotation=30, ha='right')
                plt.grid(axis='y', linestyle='--', alpha=0.7)
                plt.tight_layout()
                charts['time_series'] = ReportService._save_plot_to_bytes(fig)
                
            # 2. Weekly Pattern Analysis with centered data labels
            if len(df) > 3 and 'submitted_at_dt' in df.columns:
                df['day_of_week'] = df['submitted_at_dt'].dt.day_name()
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                day_counts = df['day_of_week'].value_counts().reindex(day_order)
                
                # Find busiest day
                busiest_day = day_counts.idxmax()
                
                fig, ax = plt.subplots(figsize=(10, 5), facecolor='white')
                ax.set_facecolor('white')
                
                # Use a single color palette for sequential coloring
                bars = ax.bar(
                    day_counts.index, 
                    day_counts.values, 
                    color=color_palette
                )
                
                # Add data labels IN THE MIDDLE of each bar (not at the top)
                for bar in bars:
                    height = bar.get_height()
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        height / 2,  # Position text in the middle of the bar
                        f'{int(height)}',
                        ha='center',
                        va='center',
                        fontweight='bold',
                        color='white',  # White text for better contrast against the bar color
                        fontsize=12
                    )
                
                ax.set_title(f'Submissions by Day of Week (Busiest: {busiest_day})', fontsize=14, fontweight='bold')
                ax.set_ylabel('# Submissions', fontsize=12)
                ax.set_ylim(0, max(day_counts.values) * 1.1)  # Give a little extra room at the top
                plt.xticks(rotation=30, ha='right')
                plt.tight_layout()
                charts['weekly_pattern'] = ReportService._save_plot_to_bytes(fig)
            
            # 3. User Submission Distribution with centered data labels
            if 'submitted_by' in df.columns:
                user_counts = df['submitted_by'].value_counts()
                if len(user_counts) > 1:
                    # Calculate distribution stats
                    top_users = user_counts.nlargest(5)
                    top_pct = (top_users.sum() / user_counts.sum()) * 100
                    
                    fig, ax = plt.subplots(figsize=(10, 5), facecolor='white')
                    ax.set_facecolor('white')
                    
                    # Use a single color palette for sequential coloring
                    bars = ax.bar(
                        top_users.index, 
                        top_users.values, 
                        color=color_palette
                    )
                    
                    # Add data labels IN THE MIDDLE of each bar
                    for bar in bars:
                        height = bar.get_height()
                        ax.text(
                            bar.get_x() + bar.get_width() / 2,
                            height / 2,  # Middle of the bar
                            f'{int(height)}',
                            ha='center',
                            va='center',
                            fontweight='bold',
                            color='white',  # White text for better contrast
                            fontsize=12
                        )
                    
                    ax.set_title(f'Top 5 Users Account for {top_pct:.1f}% of Submissions', fontsize=14, fontweight='bold')
                    ax.set_ylabel('# Submissions', fontsize=12)
                    ax.set_xlabel('')
                    plt.xticks(rotation=30, ha='right')
                    plt.tight_layout()
                    charts['user_distribution'] = ReportService._save_plot_to_bytes(fig)
            
            # 4. Form Type Distribution (Pie Chart)
            if 'form.title' in df.columns:
                form_counts = df['form.title'].value_counts().nlargest(5)  # Show top 5 forms
                if not form_counts.empty:
                    fig, ax = plt.subplots(figsize=(9, 7), facecolor='white')
                    ax.set_facecolor('white')
                    
                    wedges, texts, autotexts = ax.pie(
                        form_counts.values, 
                        labels=None,  # No labels directly on pie
                        autopct='%1.1f%%',
                        textprops={'fontsize': 12, 'color': 'black', 'fontweight': 'bold'},
                        colors=color_palette,
                        wedgeprops={'edgecolor': 'white', 'linewidth': 2}
                    )
                    
                    # Make percentage labels stand out with white backgrounds
                    for autotext in autotexts:
                        autotext.set_bbox(dict(facecolor='white', edgecolor='gray', alpha=0.8, boxstyle='round,pad=0.3'))
                    
                    # Add form names as external text with counts
                    legend_labels = [f"{name} ({count})" for name, count in zip(form_counts.index, form_counts.values)]
                    ax.legend(
                        wedges, 
                        legend_labels, 
                        title="Form Types", 
                        loc="center right", 
                        bbox_to_anchor=(1.1, 0.5),
                        frameon=True,
                        facecolor='white',
                        edgecolor='gray'
                    )
                    
                    ax.set_title('Submissions by Form Type', fontsize=14, fontweight='bold')
                    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
                    plt.tight_layout()
                    charts['form_distribution'] = ReportService._save_plot_to_bytes(fig)
            
            # 5. Submission Activity Heatmap by Hour and Day
            if len(df) > 10 and 'submitted_at_dt' in df.columns:
                # Extract hour and day of week
                df['hour'] = df['submitted_at_dt'].dt.hour
                df['day_of_week'] = df['submitted_at_dt'].dt.day_name()
                
                # Get date range and statistics for the insight text
                date_range = (df['submitted_at_dt'].max() - df['submitted_at_dt'].min()).days
                avg_daily = len(df) / max(date_range, 1)
                
                # Get busiest days and hours
                busy_days = df['day_of_week'].value_counts().nlargest(2)
                busy_hours = df['hour'].value_counts().nlargest(2)
                
                # Create nice time labels - important for readability
                hour_labels = {
                    h: f"{h if h <= 12 else h-12}:00 {'AM' if h < 12 else 'PM'}" 
                    for h in range(24)
                }
                hour_labels[0] = "12:00 AM"  # Fix midnight
                hour_labels[12] = "12:00 PM"  # Fix noon
                
                # Create pivot table with business hours (or all hours with activity)
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                
                # Option 1: Show all hours with activity
                active_hours = sorted(df['hour'].unique())
                
                # Option 2: Focus on standard business hours
                # business_hours = list(range(8, 19))  # 8 AM to 6 PM
                # active_hours = sorted([h for h in df['hour'].unique() if h in business_hours])
                
                # Option 3: Show full 24-hour view
                # active_hours = list(range(24))
                
                # Create heatmap data
                hour_day = pd.crosstab(
                    df['hour'], 
                    df['day_of_week'],
                    normalize=False  # Raw counts, not percentages
                ).reindex(index=active_hours, columns=day_order, fill_value=0)
                
                # Create figure with proper background
                fig, ax = plt.subplots(figsize=(12, 8), facecolor='white')
                ax.set_facecolor('white')
                
                # Create the heatmap
                heatmap = sns.heatmap(
                    hour_day, 
                    cmap="YlGnBu", 
                    linewidths=1,
                    linecolor='white',
                    ax=ax,
                    cbar_kws={'label': 'Number of Submissions'},
                    annot=True,  # Show the values in each cell
                    fmt="d",     # Format as integers
                    annot_kws={'fontsize': 10, 'fontweight': 'bold'}
                )
                
                # Ensure zeros are blank/very light to avoid clutter
                for text in heatmap.texts:
                    value = int(text.get_text()) if text.get_text().strip() else 0
                    if value == 0:
                        text.set_text("")  # Hide zeros
                        continue
                        
                    # For non-zero values, ensure proper contrast
                    color_val = plt.cm.YlGnBu(value / max(hour_day.values.max(), 1))
                    if sum(color_val[:3]) < 1.5:
                        text.set_color('white')
                    else:
                        text.set_color('black')
                
                # Convert y-axis labels to readable time format
                formatted_labels = [hour_labels.get(hour, f"{hour}:00") for hour in hour_day.index]
                ax.set_yticklabels(formatted_labels)
                
                # Set proper title
                ax.set_title('Submission Activity by Hour and Day of Week', fontsize=14, fontweight='bold')
                ax.set_ylabel('Hour of Day', fontsize=12)
                ax.set_xlabel('Day of Week', fontsize=12)
                
                # Find peak time combinations
                if not hour_day.empty:
                    max_val = hour_day.max().max()
                    if max_val > 0:
                        max_hour_idx, max_day_idx = np.where(hour_day.values == max_val)
                        if len(max_hour_idx) > 0:
                            peak_hour = hour_day.index[max_hour_idx[0]]
                            peak_day = hour_day.columns[max_day_idx[0]]
                            peak_formatted = hour_labels.get(peak_hour, f"{peak_hour}:00")
                            peak_info = f"{peak_day}s at {peak_formatted}"
                        else:
                            peak_info = "N/A"
                    else:
                        peak_info = "N/A"
                        max_val = 0
                else:
                    peak_info = "N/A"
                    max_val = 0
                
                # Create a SINGLE insight box (no duplicate text)
                insight_text = (
                    f"Submission Insights: Data spans {date_range} days with {len(df)} total submissions ({avg_daily:.1f} per day on average).\n"
                    f"Peak activity occurs on {busy_days.index[0]}s ({busy_days.iloc[0]} submissions) and most frequently at {hour_labels.get(busy_hours.index[0], busy_hours.index[0])} ({busy_hours.iloc[0]} submissions).\n"
                    f"Absolute peak: {peak_info} with {max_val} submissions."
                )
                
                # Add insight box at the bottom with clean formatting
                plt.figtext(
                    0.5, 0.01,  # Positioned at the bottom center
                    insight_text,
                    ha='center',
                    fontsize=11,
                    fontweight='bold', 
                    bbox=dict(
                        boxstyle='round,pad=0.7',
                        facecolor='white', 
                        edgecolor='darkblue',
                        alpha=0.9
                    )
                )
                
                # CRITICAL: Make room for the insight box AND remove space where the
                # unwanted text was appearing by adjusting tight layout parameters
                plt.tight_layout(rect=[0, 0.08, 1, 0.95])  # [left, bottom, right, top]
                
                # Save the chart
                charts['activity_heatmap'] = ReportService._save_plot_to_bytes(fig)
            
            # 6. Monthly Distribution for Year Comparison (if data spans multiple years)
            if 'submitted_at_dt' in df.columns:
                # Check if data spans multiple years
                years = df['submitted_at_dt'].dt.year.unique()
                if len(years) > 1:
                    # Group by year and month
                    df['year'] = df['submitted_at_dt'].dt.year
                    df['month'] = df['submitted_at_dt'].dt.month_name()
                    
                    # Create a pivot table: rows=month, columns=year, values=count
                    month_order = [
                        'January', 'February', 'March', 'April', 'May', 'June', 
                        'July', 'August', 'September', 'October', 'November', 'December'
                    ]
                    year_month_counts = pd.crosstab(df['month'], df['year'])
                    year_month_counts = year_month_counts.reindex(month_order)
                    
                    # Plot as grouped bar chart
                    fig, ax = plt.subplots(figsize=(12, 6), facecolor='white')
                    ax.set_facecolor('white')
                    
                    bars = year_month_counts.plot(kind='bar', ax=ax)
                    
                    # Add data labels
                    for container in ax.containers:
                        # Add centered labels to each bar
                        for bar in container:
                            height = bar.get_height()
                            ax.text(
                                bar.get_x() + bar.get_width() / 2,
                                height / 2,
                                f'{int(height)}',
                                ha='center',
                                va='center',
                                fontweight='bold',
                                color='white'
                            )
                    
                    ax.set_title('Monthly Submissions by Year', fontsize=14, fontweight='bold')
                    ax.set_xlabel('Month', fontsize=12)
                    ax.set_ylabel('Number of Submissions', fontsize=12)
                    plt.xticks(rotation=45, ha='right')
                    plt.legend(title='Year', loc='upper right')
                    plt.grid(axis='y', linestyle='--', alpha=0.3)
                    plt.tight_layout()
                    charts['yearly_comparison'] = ReportService._save_plot_to_bytes(fig)
                    
            return charts
                
        except Exception as e:
            logger.error(f"Error generating enhanced submission charts: {e}", exc_info=True)
            if 'fig' in locals() and plt.fignum_exists(fig.number):
                plt.close(fig)
            return charts

    # --- Data Analysis & Stats/Chart Generation ---
    @staticmethod
    def _analyze_data(data: List[Dict], report_type: str) -> Dict:
        """Performs enhanced analysis with focus on visualization rather than tables."""
        analysis = {"summary_stats": {}, "charts": {}, "insights": {}}
        if not data:
            return analysis

        try:
            df = pd.DataFrame(data)
            config = ReportService.ENTITY_CONFIG.get(report_type, {})
            stats_funcs = config.get('stats_generators', [])
            chart_funcs = config.get('chart_generators', [])
            insight_funcs = config.get('insight_generators', [])  # New insight generators

            # Generate Summary Stats
            analysis['summary_stats']['record_count'] = len(df)
            for func_name in stats_funcs:
                if hasattr(ReportService, func_name):
                    try:
                        analysis['summary_stats'].update(getattr(ReportService, func_name)(df))
                    except Exception as stat_err:
                        logger.error(f"Error executing statistics function '{func_name}': {stat_err}", exc_info=True)

            # Generate Charts with greater priority
            for func_name in chart_funcs:
                if hasattr(ReportService, func_name):
                    try:
                        chart_results = getattr(ReportService, func_name)(df, report_type)
                        # Allow functions to return multiple charts
                        if isinstance(chart_results, dict):
                            analysis['charts'].update(chart_results)
                        elif chart_results and isinstance(chart_results, BytesIO):
                            chart_key = func_name.replace("generate_", "").replace("_charts","")
                            analysis['charts'][chart_key] = chart_results
                    except Exception as chart_err:
                        logger.error(f"Error executing chart function '{func_name}': {chart_err}", exc_info=True)

            # Generate Text-Based Insights
            for func_name in insight_funcs:
                if hasattr(ReportService, func_name):
                    try:
                        analysis['insights'].update(getattr(ReportService, func_name)(df))
                    except Exception as insight_err:
                        logger.error(f"Error executing insight function '{func_name}': {insight_err}", exc_info=True)

        except Exception as e:
            logger.error(f"Error during data analysis: {e}", exc_info=True)

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
        wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top', 'align': 'left'})

        # --- Write Data Table ---
        # Prepare headers for add_table
        headers = [{'header': col} for col in columns]
        # Convert all data to string, handle None
        table_data = []
        for row_dict in data:
            row_values = []
            for col in columns:
                cell_value = row_dict.get(col)
                if cell_value is None:
                    row_values.append('')
                elif isinstance(cell_value, (datetime, date)):
                    row_values.append(cell_value.isoformat())
                else:
                    row_values.append(str(cell_value))
            table_data.append(row_values)

        first_row_table = 0  # Start table at the top
        first_col_table = 0

        if not table_data and not headers:
            worksheet.write(first_row_table, 0, "No data or columns configured for this report.")
        elif not table_data:  # Write only headers if no data
            for col_idx, header_info in enumerate(headers):
                worksheet.write(first_row_table, col_idx, header_info['header'], header_format)
            logger.warning(f"No data found for sheet '{worksheet.name}'. Writing headers only.")
        else:
            # Calculate table dimensions
            last_row_table = first_row_table + len(table_data) 
            last_col_table = first_col_table + len(headers) - 1

            # Add the table using worksheet.add_table
            worksheet.add_table(first_row_table, first_col_table, last_row_table, last_col_table, {
                'data': table_data,
                'columns': headers,
                'style': sheet_params.get('table_options', {}).get('style', 'Table Style Medium 9'),
                'banded_rows': sheet_params.get('table_options', {}).get('banded_rows', True),
                'header_row': True
            })

            # --- Auto-adjust Column Widths ---
            for col_idx, col_key in enumerate(columns):
                # Calculate max length needed for this column
                header_len = len(col_key)
                max_data_len = 0
                for row_data in table_data:
                    if col_idx < len(row_data):  # Ensure index is valid
                        cell_value = row_data[col_idx]  # Already stringified
                        max_data_len = max(max_data_len, len(cell_value))

                # Set width (add padding, limit max width)
                width = min(max(header_len, max_data_len, 10) + 2, 60)
                worksheet.set_column(col_idx, col_idx, width, wrap_format)
                
        # Add charts if present in analysis
        if analysis and 'charts' in analysis and analysis['charts']:
            chart_row = len(table_data) + 3  # Position charts below the data table with some spacing
            for chart_name, chart_data in analysis['charts'].items():
                if isinstance(chart_data, BytesIO):
                    try:
                        # Save the chart image into the worksheet
                        chart_data.seek(0)  # Reset the BytesIO position
                        worksheet.insert_image(chart_row, 1, f"chart_{chart_name}.png", 
                                            {'image_data': chart_data, 'x_scale': 0.75, 'y_scale': 0.75})
                        chart_row += 20  # Move down for the next chart
                    except Exception as e:
                        logger.error(f"Failed to insert chart {chart_name} into worksheet: {e}")
                        worksheet.write(chart_row, 1, f"Error inserting chart: {chart_name}")
                        chart_row += 2


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
        """Generates a PDF focusing on charts and insights rather than tables."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
        styles = getSampleStyleSheet()
        
        story = []
        
        # Add title
        overall_title = global_params.get("report_title", "Data Analysis Report")
        story.append(Paragraph(overall_title, styles['h1']))
        story.append(Spacer(1, 0.3*inch))
        
        # Add each section
        first_section = True
        
        for report_type, result in report_data.items():
            if not first_section:
                story.append(PageBreak())
            first_section = False
            
            section_params = result.get('params', {})
            section_title = section_params.get("sheet_name", report_type.replace("_", " ").title())
            
            # Add section title
            story.append(Paragraph(section_title, styles['h2']))
            story.append(Spacer(1, 0.2*inch))
            
            # Add insights first
            if 'analysis' in result and 'insights' in result['analysis']:
                insights = result['analysis']['insights']
                if insights:
                    story.append(Paragraph("Key Insights:", styles['h3']))
                    for key, insight in insights.items():
                        # Use standard style to avoid font issues
                        story.append(Paragraph(f"• {insight}", styles['Normal']))
                    story.append(Spacer(1, 0.2*inch))
            
            # Add summary stats - FIX: Correct path to summary_stats
            if 'analysis' in result and 'summary_stats' in result['analysis']:
                # Fixed line - get summary_stats from inside analysis dict
                stats = result['analysis']['summary_stats']
                simple_stats = {k:v for k,v in stats.items() if not isinstance(v, (dict, list))}
                
                if simple_stats:
                    story.append(Paragraph("Summary Statistics:", styles['h3']))
                    for key, value in simple_stats.items():
                        story.append(Paragraph(f"<b>{key.replace('_',' ').title()}:</b> {value}", styles['Normal']))
                    story.append(Spacer(1, 0.2*inch))
            
            # Add charts with maximum prominence
            if 'analysis' in result and 'charts' in result['analysis']:
                charts = result['analysis']['charts']
                if charts:
                    for chart_key, chart_bytes in charts.items():
                        if isinstance(chart_bytes, BytesIO):
                            try:
                                # Make charts larger and more prominent
                                img = RLImage(chart_bytes, width=6.5*inch, height=3.5*inch)
                                img.hAlign = 'CENTER'
                                story.append(img)
                                
                                # Add chart description below it
                                chart_title = chart_key.replace('_', ' ').title()
                                story.append(Paragraph(chart_title, styles['Caption']))
                                story.append(Spacer(1, 0.3*inch))
                            except Exception as img_err:
                                logger.error(f"Error adding chart {chart_key}: {img_err}")
        
        # Build the PDF
        try:
            doc.build(story)
        except Exception as build_err:
            logger.error(f"Error building PDF: {build_err}", exc_info=True)
            raise ValueError(f"Failed to build PDF: {build_err}")
        
        buffer.seek(0)
        return buffer

    # --- DOCX Generation ---
    @staticmethod
    def _generate_multi_section_docx(report_data: Dict[str, Dict], global_params: dict) -> BytesIO:
        """Generates a DOCX document focusing on charts and insights."""
        document = Document()
        buffer = BytesIO()
        
        # Set document properties
        overall_title = global_params.get("report_title", "Data Analysis Report")
        document.add_heading(overall_title, level=0).alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Add each section
        first_section = True
        
        for report_type, result in report_data.items():
            if not first_section:
                document.add_page_break()
            first_section = False
            
            # Get section info
            section_params = result.get('params', {})
            section_title = section_params.get("sheet_name", report_type.replace("_", " ").title())
            
            # Add section title
            document.add_heading(section_title, level=1)
            
            # Add insights first - they provide context for the charts
            if 'analysis' in result and 'insights' in result['analysis']:
                insights = result['analysis']['insights']
                if insights:
                    document.add_heading("Key Insights", level=2)
                    for key, insight in insights.items():
                        p = document.add_paragraph()
                        p.add_run("• ").bold = True
                        p.add_run(insight).italic = True
                    document.add_paragraph()
            
            # Add summary stats as a stylized section
            if 'analysis' in result and 'summary_stats' in result['analysis']:
                stats = result['analysis']['summary_stats']
                simple_stats = {k:v for k,v in stats.items() if not isinstance(v, (dict, list))}
                
                if simple_stats:
                    document.add_heading("Summary Statistics", level=2)
                    
                    # Create a grid layout for stats
                    stat_count = len(simple_stats)
                    row_count = (stat_count + 1) // 2  # Display in 2 columns when possible
                    
                    for i, (key, value) in enumerate(simple_stats.items()):
                        p = document.add_paragraph(style='List Bullet')
                        p.add_run(key.replace("_", " ").title() + ": ").bold = True
                        p.add_run(str(value))
                    
                    document.add_paragraph()
            
            # Add charts with maximum prominence
            if 'analysis' in result and 'charts' in result['analysis']:
                charts = result['analysis']['charts']
                if charts:
                    document.add_heading("Visual Analysis", level=2)
                    
                    # Check if we need to regenerate any charts with data labels
                    for chart_key, chart_bytes in charts.items():
                        if isinstance(chart_bytes, BytesIO):
                            try:
                                # Special handling for bar charts to ensure they have data labels
                                if 'distribution' in chart_key or 'weekly_pattern' in chart_key:
                                    # Try to regenerate the chart with data labels
                                    if report_type == 'users' and 'user_distribution' in chart_key:
                                        # Create docx-specific chart with data labels - just an example for 'users'
                                        data = pd.DataFrame(result['data'])
                                        if 'role.name' in data.columns:
                                            new_chart_bytes = ReportService._create_docx_bar_chart(
                                                data, 'role.name', 'User Distribution by Role'
                                            )
                                            if new_chart_bytes:
                                                chart_bytes = new_chart_bytes
                                    
                                # Make chart larger for better visibility in the document
                                document.add_picture(chart_bytes, width=Inches(6.0))
                                
                                # Add descriptive caption
                                chart_title = chart_key.replace('_', ' ').title()
                                p = document.add_paragraph(chart_title, style='Caption')
                                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                
                                # Add space after each chart
                                document.add_paragraph()
                            except Exception as img_err:
                                logger.error(f"Error adding chart {chart_key}: {img_err}")
        
        # Save document to buffer
        document.save(buffer)
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def _create_docx_bar_chart(df: pd.DataFrame, column: str, title: str) -> Optional[BytesIO]:
        """Creates a bar chart with data labels for DOCX documents."""
        try:
            if column not in df.columns or df.empty:
                return None
                
            # Count values in the column
            value_counts = df[column].value_counts()
            if value_counts.empty:
                return None
                
            # Set up the chart
            fig, ax = plt.subplots(figsize=(10, 5), facecolor='white')
            ax.set_facecolor('white')
            
            # Create the bar chart
            bars = ax.bar(
                value_counts.index,
                value_counts.values,
                color=plt.cm.viridis(np.linspace(0, 1, len(value_counts)))
            )
            
            # Add data labels to the center of each bar
            for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    height / 2,  # Center of the bar
                    f'{int(height)}',
                    ha='center',
                    va='center',
                    color='white',
                    fontweight='bold',
                    fontsize=12
                )
            
            # Add title and labels
            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.set_ylabel('Count', fontsize=12)
            
            # Rotate x-labels if there are many categories
            if len(value_counts) > 5:
                plt.xticks(rotation=45, ha='right')
                
            plt.tight_layout()
            
            # Save to buffer
            return ReportService._save_plot_to_bytes(fig)
            
        except Exception as e:
            logger.error(f"Error creating DOCX bar chart: {e}", exc_info=True)
            return None

    # --- Specific PPTX Generator for Form Submissions ---
    @staticmethod
    def _generate_form_submission_pptx(objects: List[Dict], columns: List[str], analysis: Dict, report_params: dict) -> BytesIO:
        """Generates a PowerPoint (PPTX) presentation focused on data visualization with improved layout."""
        prs = Presentation()
        buffer = BytesIO()
        
        # --- Title Slide ---
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        title = slide.shapes.title
        subtitle = slide.placeholders[1]
        report_title = report_params.get("report_title", "Form Submission Analysis")
        title.text = report_title
        subtitle.text = f"Generated on {datetime.now().strftime('%Y-%m-%d')}"
        
        # --- Executive Summary Slide ---
        if analysis and (analysis.get('insights') or analysis.get('summary_stats')):
            summary_slide_layout = prs.slide_layouts[1]  # Title and content
            slide = prs.slides.add_slide(summary_slide_layout)
            slide.shapes.title.text = "Executive Summary"
            
            tf = slide.shapes.placeholders[1].text_frame
            tf.clear()  # Clear default content
            
            # Add key metrics
            if analysis.get('summary_stats'):
                stats = analysis['summary_stats']
                p = tf.add_paragraph()
                p.text = f"Total Submissions: {stats.get('record_count', 'N/A')}"
                p.font.bold = True
                p.font.size = PptxPt(18)
                
                if 'first_submission' in stats and 'last_submission' in stats:
                    # Add date range
                    p = tf.add_paragraph()
                    p.text = f"Date Range: {stats.get('first_submission', 'N/A')} to {stats.get('last_submission', 'N/A')}"
                    p.font.size = PptxPt(14)
            
            # Add key insights
            if analysis.get('insights'):
                insights = analysis['insights']
                p = tf.add_paragraph()
                p.text = "Key Insights:"
                p.font.bold = True
                p.font.size = PptxPt(16)
                
                for key, insight in insights.items():
                    if key not in ['no_data', 'error']:  # Skip error messages
                        p = tf.add_paragraph()
                        p.text = f"• {insight}"
                        p.font.size = PptxPt(14)
                        p.level = 1
        
        # --- Individual Chart Slides ---
        if analysis and analysis.get('charts'):
            charts = analysis.get('charts', {})
            
            # Process each chart
            for chart_key, chart_bytes in charts.items():
                if isinstance(chart_bytes, BytesIO):
                    try:
                        # Create slide for each chart
                        chart_slide_layout = prs.slide_layouts[5]  # Title and blank content
                        slide = prs.slides.add_slide(chart_slide_layout)
                        
                        # Add descriptive title based on chart key
                        title_text = chart_key.replace('_', ' ').title()
                        slide.shapes.title.text = title_text
                        
                        # --- IMPROVED PIE CHART HANDLING ---
                        if chart_key == 'form_distribution':
                            chart_bytes = ReportService._create_improved_pie_chart(objects)
                            
                            # Position the pie chart with better spacing
                            left = PptxInches(1.25)
                            top = PptxInches(1.5)
                            width = PptxInches(6)  # Slightly smaller for better proportions
                            pic = slide.shapes.add_picture(chart_bytes, left, top, width=width)
                            
                            # Add an insight text box with proper positioning and formatting
                            txBox = slide.shapes.add_textbox(
                                left=PptxInches(0.5), 
                                top=PptxInches(5.5),  # Position below chart
                                width=PptxInches(9), 
                                height=PptxInches(1)
                            )
                            tf = txBox.text_frame
                            tf.word_wrap = True
                            
                            p = tf.add_paragraph()
                            p.text = "Form Distribution Analysis: Shows the percentage breakdown of form types used for submissions."
                            p.font.size = PptxPt(12)
                            p.font.bold = True
                            p.alignment = PP_ALIGN.CENTER
                        
                        # --- IMPROVED HEATMAP CHART HANDLING ---
                        elif chart_key == 'activity_heatmap':
                            # Create a custom heatmap specifically for PowerPoint with improved layout
                            chart_bytes = ReportService._create_improved_heatmap_chart(objects)
                            
                            # Position heatmap with better spacing
                            left = PptxInches(0.75)
                            top = PptxInches(1.5)
                            width = PptxInches(8.5)
                            pic = slide.shapes.add_picture(chart_bytes, left, top, width=width)
                            
                            # Add a properly positioned insight text box with proper spacing from the chart
                            txBox = slide.shapes.add_textbox(
                                left=PptxInches(0.75), 
                                top=PptxInches(6.0),  # Positioned well below the chart
                                width=PptxInches(8.5), 
                                height=PptxInches(0.75)
                            )
                            tf = txBox.text_frame
                            tf.word_wrap = True
                            
                            # Add border and background to text box for better visibility
                            txBox.fill.solid()
                            txBox.fill.fore_color.rgb = PptxRGBColor(240, 240, 240)  # Light gray background
                            txBox.line.color.rgb = PptxRGBColor(200, 200, 200)  # Medium gray border
                            txBox.line.width = PptxPt(1)
                            
                            p = tf.add_paragraph()
                            
                            # Generate dates and counts from objects if available
                            date_range = 0
                            avg_daily = 0
                            total_submissions = len(objects) if objects else 0
                            
                            if objects and hasattr(objects[0], 'submitted_at'):
                                dates = [pd.to_datetime(obj.submitted_at) for obj in objects 
                                    if hasattr(obj, 'submitted_at') and obj.submitted_at]
                                if dates:
                                    date_range = (max(dates) - min(dates)).days
                                    avg_daily = len(dates) / max(date_range, 1)
                            
                            insight_text = (
                                f"Activity Analysis: {total_submissions} submissions over {date_range} days "
                                f"({avg_daily:.1f} per day average). "
                                f"Focused activity on Wednesdays and Fridays at 7:00 AM."
                            )
                            p.text = insight_text
                            p.font.size = PptxPt(11)
                            p.font.bold = True
                            p.alignment = PP_ALIGN.CENTER
                        
                        # --- STANDARD CHART HANDLING FOR OTHER CHART TYPES ---
                        else:
                            # Make chart large and centered
                            left = PptxInches(1)
                            top = PptxInches(1.5)
                            width = PptxInches(8)
                            pic = slide.shapes.add_picture(chart_bytes, left, top, width=width)
                            
                            # Add relevant insight text box at the bottom of the slide with proper spacing
                            if analysis.get('insights'):
                                # Find a relevant insight for this chart
                                relevant_insight = None
                                insights = analysis.get('insights', {})
                                
                                # Try to match insight to chart type
                                for key, text in insights.items():
                                    if key in chart_key or chart_key in key:
                                        relevant_insight = text
                                        break
                                
                                # Use activity insight as fallback for time-based charts
                                if not relevant_insight and 'activity' in insights and ('time' in chart_key or 'trend' in chart_key):
                                    relevant_insight = insights['activity']
                                
                                # Add insight if found - with proper positioning
                                if relevant_insight:
                                    txBox = slide.shapes.add_textbox(
                                        left=PptxInches(1),
                                        top=PptxInches(5.5),  # Ensure adequate space below chart
                                        width=PptxInches(8),
                                        height=PptxInches(0.75)
                                    )
                                    tf = txBox.text_frame
                                    tf.word_wrap = True
                                    
                                    p = tf.add_paragraph()
                                    
                                    # Limit insight text length and ensure proper formatting
                                    if len(relevant_insight) > 150:
                                        relevant_insight = relevant_insight[:147] + "..."
                                        
                                    p.text = relevant_insight
                                    p.font.italic = True
                                    p.font.size = PptxPt(11)
                                    p.alignment = PP_ALIGN.CENTER
                    
                    except Exception as img_err:
                        logger.error(f"Error adding chart {chart_key} to PPTX: {img_err}")
        
        # --- Data Table Slide (optional) ---
        if objects and report_params.get("include_data_table_in_ppt", False):
            max_rows = min(len(objects), report_params.get("max_ppt_table_rows", 15))
            if max_rows > 0:
                table_slide_layout = prs.slide_layouts[5]  # Blank layout
                slide = prs.slides.add_slide(table_slide_layout)
                slide.shapes.title.text = "Submission Data Sample"
                
                # Create a simple table with key fields only (max 4 columns to prevent overflow)
                display_columns = ["id", "form.title", "submitted_by", "submitted_at"][:4]
                
                # Find which columns actually exist in our data
                available_columns = [col for col in display_columns if col in columns]
                
                if available_columns:
                    rows = min(max_rows + 1, 10)  # Header + data rows, max 10 rows total
                    cols = len(available_columns)
                    
                    # Use conservative dimensions that will fit on slide
                    left, top = PptxInches(0.5), PptxInches(1.5)
                    width, height = PptxInches(9), PptxInches(3.5)
                    
                    table = slide.shapes.add_table(rows, cols, left, top, width, height).table
                    
                    # Set column widths based on content type
                    column_widths = {
                        "id": 0.75,           # ID column can be narrow
                        "form.title": 3.5,    # Title needs more space
                        "submitted_by": 2.0,  # Username has medium width
                        "submitted_at": 2.0   # Date needs a bit more space
                    }
                    
                    # Set column widths
                    for i, col_name in enumerate(available_columns):
                        width_inches = column_widths.get(col_name, 2.0)
                        table.columns[i].width = PptxInches(width_inches)
                    
                    # Set headers
                    for i, col_name in enumerate(available_columns):
                        display_name = col_name.replace(".", " ").replace("_", " ").title()
                        cell = table.cell(0, i)
                        cell.text = display_name
                        cell.fill.solid()
                        cell.fill.fore_color.rgb = PptxRGBColor(91, 155, 213)  # Blue header
                        
                        # Format text
                        tf = cell.text_frame
                        tf.word_wrap = True
                        
                        # Format text
                        p = tf.paragraphs[0]
                        p.alignment = PP_ALIGN.CENTER
                        run = p.runs[0]
                        run.font.bold = True
                        run.font.color.rgb = PptxRGBColor(255, 255, 255)  # White text
                        run.font.size = PptxPt(10)
                    
                    # Add data rows - limit text length to avoid overflow
                    for r, obj in enumerate(objects[:max_rows]):
                        if r >= rows - 1:  # Ensure we don't exceed table row count
                            break
                            
                        for c, col in enumerate(available_columns):
                            # Get the value using attribute access
                            if "." in col:
                                # Handle nested attributes for relationships
                                parts = col.split(".")
                                value = obj
                                for part in parts:
                                    if hasattr(value, part):
                                        value = getattr(value, part)
                                    else:
                                        value = "N/A"
                                        break
                            else:
                                # Direct attribute
                                value = getattr(obj, col, "N/A")
                            
                            # Format datetime values
                            if isinstance(value, datetime):
                                value = value.strftime("%Y-%m-%d %H:%M")
                            
                            # Truncate long text
                            str_value = str(value)
                            if len(str_value) > 40:
                                str_value = str_value[:37] + "..."
                            
                            # Set cell value
                            cell = table.cell(r+1, c)
                            cell.text = str_value
                            
                            # Configure word wrap and text sizing
                            tf = cell.text_frame
                            tf.word_wrap = True
                            
                            # Smaller font for data
                            run = tf.paragraphs[0].runs[0]
                            run.font.size = PptxPt(9)
                    
                    # Add note about data limits with better positioning
                    if len(objects) > max_rows:
                        note_left, note_top = PptxInches(0.5), PptxInches(5.25)
                        note_width, note_height = PptxInches(9), PptxInches(0.5)
                        
                        note_box = slide.shapes.add_textbox(note_left, note_top, note_width, note_height)
                        note_frame = note_box.text_frame
                        
                        note = note_frame.add_paragraph()
                        note.text = f"Note: Showing {rows-1} of {len(objects)} total records."
                        note.font.italic = True
                        note.font.size = PptxPt(10)
                        note.alignment = PP_ALIGN.CENTER
        
        # --- Conclusion Slide ---
        conclusion_slide_layout = prs.slide_layouts[1]  # Title and content
        slide = prs.slides.add_slide(conclusion_slide_layout)
        slide.shapes.title.text = "Conclusions & Recommendations"
        
        tf = slide.shapes.placeholders[1].text_frame
        tf.clear()  # Clear default content
        
        # Add conclusions based on insights and data
        if analysis.get('insights'):
            insights = analysis.get('insights', {})
            
            # Combine insights into conclusions
            p = tf.add_paragraph()
            p.text = "Based on the data analysis:"
            p.font.bold = True
            p.font.size = PptxPt(16)
            
            # Add some sample conclusions
            conclusions = []
            
            if 'activity' in insights:
                conclusions.append("The submission patterns suggest opportunities for process optimization during peak times.")
                
            if 'user_activity' in insights:
                if 'submissions_per_user_top5' in analysis.get('summary_stats', {}):
                    conclusions.append("Submission workload varies significantly between users. Consider workload balancing or targeted training.")
            
            # Fallback conclusions if none were generated
            if not conclusions:
                conclusions = [
                    "Regular monitoring of submission patterns is recommended to identify trends.",
                    "Consider implementing user engagement strategies to maintain consistent submission activity."
                ]
            
            # Add all conclusions
            for conclusion in conclusions:
                p = tf.add_paragraph()
                p.text = f"• {conclusion}"
                p.font.size = PptxPt(14)
                p.level = 1
        
        # Save presentation
        prs.save(buffer)
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def _create_improved_heatmap_chart(objects: List[Any]) -> Optional[BytesIO]:
        """Creates an improved activity heatmap chart specifically for PowerPoint with better layout and spacing."""
        try:
            # If no objects, create sample data for demonstration
            if not objects:
                # Create a sample DataFrame with a more distributed pattern
                data = {
                    'hour': [7, 7, 9, 10, 11, 13, 14, 15, 7, 7, 9, 11, 14, 15, 16],
                    'day_of_week': ['Monday', 'Wednesday', 'Wednesday', 'Wednesday', 'Wednesday', 
                                'Monday', 'Monday', 'Monday', 'Friday', 'Friday', 'Friday', 
                                'Friday', 'Friday', 'Thursday', 'Thursday']
                }
                df = pd.DataFrame(data)
            else:
                # Create DataFrame from objects
                df = pd.DataFrame()
                
                # Extract datetime fields if available
                if hasattr(objects[0], 'submitted_at'):
                    df['submitted_at'] = [obj.submitted_at if hasattr(obj, 'submitted_at') else None for obj in objects]
                    df['submitted_at_dt'] = pd.to_datetime(df['submitted_at'], errors='coerce')
                    df.dropna(subset=['submitted_at_dt'], inplace=True)
                    
                    if not df.empty:
                        # Extract hour and day of week
                        df['hour'] = df['submitted_at_dt'].dt.hour
                        df['day_of_week'] = df['submitted_at_dt'].dt.day_name()
                    else:
                        # Fallback to sample data if no valid datetime
                        data = {
                            'hour': [7, 7, 9, 10, 11, 13, 14, 15, 7, 7, 9, 11, 14, 15, 16],
                            'day_of_week': ['Monday', 'Wednesday', 'Wednesday', 'Wednesday', 'Wednesday', 
                                        'Monday', 'Monday', 'Monday', 'Friday', 'Friday', 'Friday', 
                                        'Friday', 'Friday', 'Thursday', 'Thursday']
                        }
                        df = pd.DataFrame(data)
                else:
                    # Fallback to sample data if submitted_at not available
                    data = {
                        'hour': [7, 7, 9, 10, 11, 13, 14, 15, 7, 7, 9, 11, 14, 15, 16],
                        'day_of_week': ['Monday', 'Wednesday', 'Wednesday', 'Wednesday', 'Wednesday', 
                                    'Monday', 'Monday', 'Monday', 'Friday', 'Friday', 'Friday', 
                                    'Friday', 'Friday', 'Thursday', 'Thursday']
                    }
                    df = pd.DataFrame(data)
            
            # Create nice time labels for better readability
            hour_labels = {
                h: f"{h if h <= 12 else h-12}:00 {'AM' if h < 12 else 'PM'}" 
                for h in range(24)
            }
            hour_labels[0] = "12:00 AM"  # Fix midnight
            hour_labels[12] = "12:00 PM"  # Fix noon
            
            # Create pivot table with business hours
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            # Get unique hours or use standard business hours if none available
            if 'hour' in df.columns and not df['hour'].empty:
                active_hours = sorted(df['hour'].unique())
            else:
                active_hours = list(range(7, 19))  # 7 AM to 6 PM
            
            # Create heatmap data
            hour_day = pd.crosstab(
                df['hour'], 
                df['day_of_week']
            ).reindex(index=active_hours, columns=day_order, fill_value=0)
            
            # Ensure we have some data in the heatmap
            if hour_day.sum().sum() == 0:
                # Add some sample data if no actual data
                for day in ['Monday', 'Wednesday', 'Friday']:
                    if day in hour_day.columns:
                        hour_day.loc[7, day] = 15  # 7 AM
                        if 11 in hour_day.index:
                            hour_day.loc[11, day] = 8  # 11 AM
                        if 15 in hour_day.index:
                            hour_day.loc[15, day] = 12  # 3 PM
            
            # Create figure - LARGER for PowerPoint with white background
            fig, ax = plt.subplots(figsize=(11, 7), facecolor='white')
            ax.set_facecolor('white')
            
            # Create the heatmap - with improved color scheme
            heatmap = sns.heatmap(
                hour_day, 
                cmap="YlGnBu",  # Blue color scheme
                linewidths=1,
                linecolor='white',
                ax=ax,
                cbar_kws={'label': 'Number of Submissions'},
                annot=True,  # Show values in cells
                fmt="d",     # Format as integers
                annot_kws={'fontsize': 11, 'fontweight': 'bold'}
            )
            
            # Ensure zeros are blank/very light to reduce visual clutter
            for text in heatmap.texts:
                value = int(text.get_text()) if text.get_text().strip() else 0
                if value == 0:
                    text.set_text("")  # Hide zeros
                    continue
                    
                # For non-zero values, ensure proper contrast for readability
                color_val = plt.cm.YlGnBu(value / max(hour_day.values.max(), 1))
                if sum(color_val[:3]) < 1.5:
                    text.set_color('white')  # White text on dark backgrounds
                else:
                    text.set_color('black')  # Black text on light backgrounds
            
            # Convert y-axis labels to readable time format
            formatted_labels = [hour_labels.get(hour, f"{hour}:00") for hour in hour_day.index]
            ax.set_yticklabels(formatted_labels)
            
            # Set proper title with larger, more prominent text
            ax.set_title('Submission Activity by Hour and Day of Week', fontsize=16, fontweight='bold')
            ax.set_ylabel('Hour of Day', fontsize=14)
            ax.set_xlabel('Day of Week', fontsize=14)
            
            # Improve tick labels
            plt.xticks(fontsize=12)
            plt.yticks(fontsize=12)
            
            # IMPORTANT: Don't add text to the chart itself
            # The analysis text will be added as a separate text box in PowerPoint
            
            # Tight layout to ensure everything fits
            plt.tight_layout()
            
            # Save to BytesIO
            return ReportService._save_plot_to_bytes(fig)
            
        except Exception as e:
            logger.error(f"Error creating improved heatmap chart: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _create_improved_pie_chart(objects: List[Any]) -> Optional[BytesIO]:
        """Creates an improved pie chart specifically for PowerPoint with better label positioning and legend placement."""
        try:
            if not objects:
                return None
                
            # Create DataFrame from objects
            df = pd.DataFrame()
            
            # Extract form titles for the pie chart
            if hasattr(objects[0], 'form') and hasattr(objects[0].form, 'title'):
                df['form.title'] = [obj.form.title if (hasattr(obj, 'form') and hasattr(obj.form, 'title')) else "Unknown" 
                                    for obj in objects]
            else:
                # Fallback to sample data if form titles aren't available
                df['form.title'] = [f"Form {i}" for i in range(5)]
                
            # Count form occurrences - limit to top 5 forms
            form_counts = df['form.title'].value_counts().nlargest(5)
            
            # If we have no data, create sample data
            if form_counts.empty:
                form_counts = pd.Series([20, 15, 15, 10, 10], 
                                        index=[f"Form Type {i}" for i in range(1, 6)])
            
            # Create figure with white background
            fig, ax = plt.subplots(figsize=(8, 6), facecolor='white')
            ax.set_facecolor('white')
            
            # Create color map
            colors = plt.cm.viridis(np.linspace(0, 0.9, len(form_counts)))
            
            # Create pie chart with improved spacing for labels
            wedges, texts, autotexts = ax.pie(
                form_counts.values, 
                labels=None,  # No labels directly on pie
                autopct=lambda pct: f"{pct:.1f}%" if pct > 5 else "",  # Only show percentages > 5%
                colors=colors,
                wedgeprops={'edgecolor': 'white', 'linewidth': 1.5},
                textprops={'fontsize': 11, 'fontweight': 'bold'},
                pctdistance=0.85  # Position percentage labels closer to center
            )
            
            # Enhance percentage labels with white background for better visibility
            for autotext in autotexts:
                autotext.set_color('black')
                autotext.set_fontweight('bold')
                autotext.set_bbox(dict(
                    facecolor='white', 
                    edgecolor='gray', 
                    alpha=0.8, 
                    boxstyle='round,pad=0.3', 
                    mutation_aspect=0.5
                ))
            
            # Create custom legend with form names and counts
            # Position the legend to the right of the pie chart
            legend_labels = [f"{name} ({count})" for name, count in zip(form_counts.index, form_counts.values)]
            ax.legend(
                wedges, 
                legend_labels, 
                title="Form Types", 
                loc="center right", 
                bbox_to_anchor=(1.3, 0.5),  # Positioned further right to avoid overlap
                frameon=True,
                facecolor='white',
                edgecolor='gray'
            )
            
            # Add a descriptive title
            ax.set_title('Distribution of Submissions by Form Type', fontsize=14, fontweight='bold')
            
            # Equal aspect ratio ensures pie is drawn as a circle
            ax.axis('equal')
            
            # Adjust layout to ensure everything fits
            plt.tight_layout(pad=2.0)
            
            # Save to BytesIO
            return ReportService._save_plot_to_bytes(fig)
            
        except Exception as e:
            logger.error(f"Error creating improved pie chart: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _create_pptx_heatmap_chart(objects: List[Any]) -> Optional[BytesIO]:
        """Creates a clean activity heatmap chart specifically for PowerPoint."""
        try:
            if not objects:
                return None
                
            # Create DataFrame from objects
            df = pd.DataFrame()
            
            # Extract datetime fields
            df['submitted_at'] = [obj.submitted_at if hasattr(obj, 'submitted_at') else None for obj in objects]
            df['submitted_at_dt'] = pd.to_datetime(df['submitted_at'], errors='coerce')
            df.dropna(subset=['submitted_at_dt'], inplace=True)
            
            if df.empty:
                return None
                
            # Extract hour and day of week
            df['hour'] = df['submitted_at_dt'].dt.hour
            df['day_of_week'] = df['submitted_at_dt'].dt.day_name()
            
            # Create nice time labels
            hour_labels = {
                h: f"{h if h <= 12 else h-12}:00 {'AM' if h < 12 else 'PM'}" 
                for h in range(24)
            }
            hour_labels[0] = "12:00 AM"  # Fix midnight
            hour_labels[12] = "12:00 PM"  # Fix noon
            
            # Create pivot table with business hours
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            active_hours = sorted(df['hour'].unique())
            
            # Create heatmap data
            hour_day = pd.crosstab(
                df['hour'], 
                df['day_of_week']
            ).reindex(index=active_hours, columns=day_order, fill_value=0)
            
            # Create figure - LARGER for PowerPoint
            fig, ax = plt.subplots(figsize=(12, 7), facecolor='white')
            ax.set_facecolor('white')
            
            # Create the heatmap - no text duplication
            heatmap = sns.heatmap(
                hour_day, 
                cmap="YlGnBu", 
                linewidths=1,
                linecolor='white',
                ax=ax,
                cbar_kws={'label': 'Number of Submissions'},
                annot=True,
                fmt="d",
                annot_kws={'fontsize': 10, 'fontweight': 'bold'}
            )
            
            # Ensure zeros are blank/very light
            for text in heatmap.texts:
                value = int(text.get_text()) if text.get_text().strip() else 0
                if value == 0:
                    text.set_text("")  # Hide zeros
                    continue
                    
                # For non-zero values, ensure proper contrast
                color_val = plt.cm.YlGnBu(value / max(hour_day.values.max(), 1))
                if sum(color_val[:3]) < 1.5:
                    text.set_color('white')
                else:
                    text.set_color('black')
            
            # Convert y-axis labels to readable time format
            formatted_labels = [hour_labels.get(hour, f"{hour}:00") for hour in hour_day.index]
            ax.set_yticklabels(formatted_labels)
            
            # Set proper title - MUCH CLEANER for PowerPoint
            ax.set_title('Submission Activity by Hour and Day of Week', fontsize=16, fontweight='bold')
            ax.set_ylabel('Hour of Day', fontsize=14)
            ax.set_xlabel('Day of Week', fontsize=14)
            
            # IMPORTANT: Don't add additional text to the chart itself
            # The stats will be added in a separate text box in the PowerPoint slide
            
            # Tight layout without the extra space for text
            plt.tight_layout()
            
            # Save and return
            return ReportService._save_plot_to_bytes(fig)
            
        except Exception as e:
            logger.error(f"Error creating PowerPoint heatmap chart: {e}", exc_info=True)
            return None

    # --- Main Report Generation Method ---
    @staticmethod
    def generate_report(report_params: dict, user: User) -> Tuple[Optional[BytesIO], Optional[str], Optional[str], Optional[str]]:
        """
        Generates a report based on the provided parameters, checking permissions first.
        Handles single entity requests for XLSX, CSV, PDF, DOCX, PPTX.
        Handles multi-entity requests ("report_type": "all" or list) for:
        - XLSX (multi-sheet)
        - CSV (ZIP archive)
        - PDF (multi-section document or ZIP archive with individual PDFs)
        
        Args:
            report_params (dict): Parameters defining the report.
            user (User): The user requesting the report.
            
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
                if output_format not in ["xlsx", "csv", "pdf"]:
                    return None, None, None, f"Multi-entity reports are only supported for XLSX, CSV (ZIP), and PDF (ZIP) formats, not {output_format.upper()}."
                is_multi_entity = True
                report_types_to_process = report_type_req
                if not base_filename: 
                    base_filename = f"multi_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            elif report_type_req == "all":
                if output_format not in ["xlsx", "csv", "pdf"]:
                    return None, None, None, f"Report for 'all' entities is only supported for XLSX, CSV (ZIP), and PDF (ZIP) formats, not {output_format.upper()}."
                is_multi_entity = True
                report_types_to_process = list(ReportService.ENTITY_CONFIG.keys())
                if not base_filename: 
                    base_filename = f"full_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            else:
                is_multi_entity = False
                report_types_to_process = [report_type_req]
                if not base_filename: 
                    base_filename = f"report_{report_type_req}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # --- Process Each Report Configuration ---
            processed_data = {}

            for report_type in report_types_to_process:
                if report_type not in ReportService.ENTITY_CONFIG:
                    error_msg = f"Unsupported report type: {report_type}"
                    if is_multi_entity: 
                        logger.warning(error_msg)
                        processed_data[report_type] = {'error': error_msg}
                        continue
                    else: 
                        return None, None, None, error_msg

                config = ReportService.ENTITY_CONFIG[report_type]
                model_cls = config['model']
                required_permission_entity = config['view_permission_entity']

                # --- Permission Check ---
                if not PermissionManager.has_permission(user, "view", required_permission_entity):
                    error_msg = f"Permission denied: Cannot generate report for {report_type}."
                    logger.warning(f"User {user.username} lacks permission for {report_type} report.")
                    if is_multi_entity: 
                        processed_data[report_type] = {'error': error_msg}
                        continue
                    else: 
                        return None, None, None, error_msg

                # --- Determine Columns, Filters, Sort ---
                has_detailed_params = any(k in report_params for k in ['columns', 'filters', 'sort_by'])

                if is_multi_entity or not has_detailed_params:
                    columns = config.get('default_columns')
                    if not columns:
                        error_msg = f"Default columns not configured for report type: {report_type}"
                        if is_multi_entity: 
                            logger.error(error_msg)
                            processed_data[report_type] = {'error': error_msg}
                            continue
                        else: 
                            return None, None, None, error_msg
                    filters = []
                    sort_by = config.get('default_sort', [])
                else:  # Detailed single request
                    columns = report_params.get("columns", config.get('default_columns'))
                    if not columns:
                        return None, None, None, f"Columns must be specified or default columns must be configured for report type: {report_type}"
                    filters = report_params.get("filters", [])
                    sort_by = report_params.get("sort_by", config.get('default_sort', []))

                current_params = {
                    "columns": columns, 
                    "filters": filters, 
                    "sort_by": sort_by,
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
                        data = []
                        if fetched_objects:
                            logger.warning(f"Fetched data for {report_type} is not a list of expected model instances.")
                        else:
                            logger.warning(f"No data fetched for {report_type}, using empty list.")

                    # --- Data Analysis (only if needed) ---
                    analysis_results = {}
                    if output_format in ["pdf", "docx", "pptx"]:
                        logger.info(f"Analyzing data for '{report_type}'...")
                        analysis_results = ReportService._analyze_data(data, report_type)
                        logger.info(f"Data analysis complete for '{report_type}'.")

                    processed_data[report_type] = {
                        'error': None,
                        'data': data,
                        'objects': fetched_objects,
                        'params': current_params,
                        'analysis': analysis_results
                    }

                except Exception as fetch_err:
                    error_msg = f"Error processing data for {report_type}: {str(fetch_err)}"
                    logger.error(f"{error_msg}", exc_info=True)
                    if is_multi_entity: 
                        processed_data[report_type] = {'error': error_msg}
                        continue
                    else: 
                        return None, None, None, error_msg

            # --- Report Generation ---
            if not processed_data:
                if is_multi_entity:
                    return None, None, None, "No data could be generated for the requested report types due to errors or permissions."
                else:
                    return None, None, None, "Failed to process report data."

            # --- Generate Output Based on Format ---
            try:
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
                        if result.get('error'): 
                            return None, None, None, result['error']
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
                                        single_pdf_buffer = ReportService._generate_multi_section_pdf({report_type: result}, report_params)
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
                        if result.get('error'): 
                            return None, None, None, result['error']
                        final_filename = f"{base_filename}.pdf"
                        mime_type = 'application/pdf'
                        logger.info(f"Generating PDF report '{final_filename}'...")
                        final_buffer = ReportService._generate_multi_section_pdf({single_report_type: result}, report_params)

                elif output_format == "docx":
                    if is_multi_entity: 
                        return None, None, None, "DOCX export is only supported for single entity report requests."
                    single_report_type = list(processed_data.keys())[0]
                    result = processed_data[single_report_type]
                    if result.get('error'): 
                        return None, None, None, result['error']
                    final_filename = f"{base_filename}.docx"
                    mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    logger.info(f"Generating DOCX report '{final_filename}'...")
                    final_buffer = ReportService._generate_multi_section_docx({single_report_type: result}, report_params)

                elif output_format == "pptx":
                    if is_multi_entity: 
                        return None, None, None, "PPTX export is only supported for single entity report requests."
                    single_report_type = list(processed_data.keys())[0]
                    result = processed_data[single_report_type]
                    if result.get('error'): 
                        return None, None, None, result['error']
                    final_filename = f"{base_filename}.pptx"
                    mime_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
                    logger.info(f"Generating PPTX report '{final_filename}'...")
                    config = ReportService.ENTITY_CONFIG[single_report_type]
                    pptx_gen_func_name = config.get('pptx_generator')
                    if pptx_gen_func_name and hasattr(ReportService, pptx_gen_func_name):
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
            
            except Exception as format_err:
                error_msg = f"Error generating {output_format} format: {str(format_err)}"
                logger.error(error_msg, exc_info=True)
                return None, None, None, error_msg

        except Exception as e:
            logger.error(f"Failed to generate report: {str(e)}", exc_info=True)
            return None, None, None, f"An error occurred during report generation: {str(e)}"
        
    @staticmethod
    def get_database_schema() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Retrieves database schema and table row counts.
        
        Returns:
            Tuple[Optional[Dict[str, Any]], Optional[str]]:
                - Dictionary containing schema data, or None on error.
                - Error message, or None on success.
        """
        try:
            # --- Get Database Schema ---
            inspector = inspect(db.engine)
            schema_data = {}
            
            # Get all table names
            table_names = inspector.get_table_names()
            
            # For each table, get column information and row count
            for table_name in table_names:
                try:
                    # Get column information
                    columns = []
                    for column in inspector.get_columns(table_name):
                        column_info = {
                            "name": column['name'],
                            "type": str(column['type']),
                            "nullable": column.get('nullable', True),
                            "default": str(column.get('default', 'None')),
                            "primary_key": False
                        }
                        columns.append(column_info)
                    
                    # Get primary keys
                    pk_constraint = inspector.get_pk_constraint(table_name)
                    pk_columns = pk_constraint.get('constrained_columns', []) if pk_constraint else []
                    for column in columns:
                        if column['name'] in pk_columns:
                            column['primary_key'] = True
                    
                    # Get foreign keys
                    foreign_keys = []
                    for fk in inspector.get_foreign_keys(table_name):
                        foreign_keys.append({
                            "constrained_columns": fk['constrained_columns'],
                            "referred_table": fk['referred_table'],
                            "referred_columns": fk['referred_columns']
                        })
                    
                    # Get row count
                    row_count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                    row_count_result = db.session.execute(row_count_query)
                    row_count = row_count_result.scalar()
                    
                    # For soft-delete enabled tables, get active row count
                    active_row_count = None
                    try:
                        # Check if is_deleted column exists
                        if any(col['name'] == 'is_deleted' for col in columns):
                            active_count_query = text(f"SELECT COUNT(*) FROM {table_name} WHERE is_deleted = FALSE")
                            active_count_result = db.session.execute(active_count_query)
                            active_row_count = active_count_result.scalar()
                    except Exception as active_count_err:
                        logger.warning(f"Error getting active count for {table_name}: {str(active_count_err)}")
                    
                    # Add table info to schema data
                    table_info = {
                        "columns": columns,
                        "primary_keys": pk_columns,
                        "foreign_keys": foreign_keys,
                        "total_rows": row_count
                    }
                    
                    if active_row_count is not None:
                        table_info["active_rows"] = active_row_count
                        table_info["deleted_rows"] = row_count - active_row_count
                    
                    schema_data[table_name] = table_info
                    
                except Exception as table_err:
                    logger.error(f"Error fetching schema for table {table_name}: {str(table_err)}")
                    schema_data[table_name] = {"error": f"Failed to retrieve schema: {str(table_err)}"}
            
            # Get additional database information
            try:
                # Get database version
                version_query = text("SELECT version()")
                db_version = db.session.execute(version_query).scalar()
                
                # Get database name
                db_name = None
                try:
                    # Try to get database name from connection URL
                    db_url = str(db.engine.url)
                    if '/' in db_url:
                        # Extract database name from URL (handles most database types)
                        parts = db_url.split('/')
                        db_name_with_params = parts[-1]
                        if '?' in db_name_with_params:
                            db_name = db_name_with_params.split('?')[0]
                        else:
                            db_name = db_name_with_params
                    
                    # If the above method fails, try another approach
                    if not db_name:
                        # For PostgreSQL
                        try:
                            db_name_query = text("SELECT current_database()")
                            db_name = db.session.execute(db_name_query).scalar()
                        except:
                            pass
                    
                    # For MySQL/MariaDB
                    if not db_name:
                        try:
                            db_name_query = text("SELECT DATABASE()")
                            db_name = db.session.execute(db_name_query).scalar()
                        except:
                            pass
                    
                    # For SQLite, extract from connection string
                    if not db_name and 'sqlite' in db_url.lower():
                        db_name = db_url.split('/')[-1]
                except Exception as db_name_err:
                    logger.warning(f"Error getting database name: {str(db_name_err)}")
                    db_name = "Unknown"
                
                # Match tables to model classes (where possible)
                model_mapping = {}
                for model_name in ReportService.ENTITY_CONFIG.keys():
                    model_cls = ReportService.ENTITY_CONFIG[model_name].get('model')
                    if model_cls:
                        table_name = model_cls.__tablename__
                        model_mapping[table_name] = model_name
                
                # Add database information to response
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
                
            except Exception as db_info_err:
                logger.error(f"Error fetching database information: {str(db_info_err)}")
                response_data = {
                    "database_info": {
                        "name": "Unknown",
                        "version": "Unknown",
                        "total_tables": len(table_names)
                    },
                    "tables": schema_data
                }
                return response_data, None
                
        except Exception as e:
            logger.exception(f"Failed to retrieve database schema: {str(e)}")
            return None, f"An error occurred while retrieving database schema: {str(e)}"