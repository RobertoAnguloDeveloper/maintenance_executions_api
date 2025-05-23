# app/services/report/report_data_fetcher.py
from typing import List, Dict, Any, Type, Optional, Tuple
import logging
from sqlalchemy import inspect as sqla_inspect
from sqlalchemy.orm import Query, joinedload, selectinload, aliased
from app import db
from app.models import User
from app.utils.permission_manager import PermissionManager, EntityType
from .report_config import ANSWERS_PREFIX, ENTITY_CONFIG
from .report_utils import ReportUtils

logger = logging.getLogger(__name__)

class ReportDataFetcher:
    """Responsible for fetching and processing data for reports"""
    
    @staticmethod
    def apply_rbac_filters(query: Query, model_cls: type, user: User) -> Query:
        """
        Apply Role-Based Access Control filters to a query
        
        Args:
            query: SQLAlchemy query to modify
            model_cls: Model class being queried
            user: User making the request
            
        Returns:
            Query with RBAC filters applied
        """
        from app.models import (
            User, FormSubmission, Form, Role, Environment,
            AnswerSubmitted, Attachment, RolePermission, FormQuestion, FormAnswer
        )
        
        # Super users can see everything
        if user.role and user.role.is_super_user:
            return query
            
        env_id = user.environment_id
        user_role_name = user.role.name if user.role else None
        
        # Apply RBAC rules for different models
        if model_cls == User:
            return query.filter(User.environment_id == env_id)
        elif model_cls == FormSubmission:
            FormCreatorUser = aliased(User)
            if user_role_name in ['site_manager', 'supervisor']:
                return query.join(Form, Form.id == FormSubmission.form_id).join(
                    FormCreatorUser, FormCreatorUser.id == Form.user_id
                ).filter(FormCreatorUser.environment_id == env_id)
            else:
                return query.filter(FormSubmission.submitted_by == user.username)
        elif model_cls == Form:
            FormCreatorUser = aliased(User)
            return query.join(FormCreatorUser, FormCreatorUser.id == Form.user_id).filter(
                db.or_(Form.is_public == True, FormCreatorUser.environment_id == env_id)
            )
        elif model_cls == Environment:
            return query.filter(Environment.id == env_id)
        elif model_cls == Role:
            return query.filter(Role.is_super_user == False)
        elif model_cls in [AnswerSubmitted, Attachment]:
             link_relationship = getattr(model_cls, 'form_submission', None)
             if link_relationship is None:
                 logger.error(f"RBAC Error: {model_cls.__name__}")
                 return query.filter(False)  # No access
             FormCreatorUser = aliased(User)
             return query.join(link_relationship).join(
                 Form, Form.id == FormSubmission.form_id
             ).join(
                 FormCreatorUser, FormCreatorUser.id == Form.user_id
             ).filter(FormCreatorUser.environment_id == env_id)
        elif model_cls == RolePermission:
            return query.join(Role, Role.id == RolePermission.role_id).filter(Role.is_super_user == False)
        elif model_cls == FormQuestion:
            FormCreatorUser = aliased(User)
            return query.join(Form, Form.id == FormQuestion.form_id).join(
                FormCreatorUser, FormCreatorUser.id == Form.user_id
            ).filter(db.or_(Form.is_public == True, FormCreatorUser.environment_id == env_id))
        elif model_cls == FormAnswer:
            FormCreatorUser = aliased(User)
            return query.join(FormQuestion, FormQuestion.id == FormAnswer.form_question_id).join(
                Form, Form.id == FormQuestion.form_id
            ).join(
                FormCreatorUser, FormCreatorUser.id == Form.user_id
            ).filter(db.or_(Form.is_public == True, FormCreatorUser.environment_id == env_id))
            
        # Default filters for common attributes    
        if hasattr(model_cls, 'environment_id'):
            logger.warning(f"Applying default env RBAC for {model_cls.__name__}")
            return query.filter(model_cls.environment_id == env_id)
        elif hasattr(model_cls, 'user_id'):
            logger.warning(f"Applying default user RBAC for {model_cls.__name__}")
            return query.filter(model_cls.user_id == user.id)
            
        logger.warning(f"No specific RBAC rule for {model_cls.__name__} for role {user_role_name}. Allowing.")
        return query

    @staticmethod
    def apply_filters_and_sort(query: Query, model_cls: type, filters: List[Dict], sort_by: List[Dict]) -> Query:
        """
        Applies filtering and sorting to a SQLAlchemy query object, ensuring
        necessary joins are added correctly using aliases.
        
        Args:
            query: The SQLAlchemy query to modify
            model_cls: The model class being queried
            filters: List of filter dictionaries {field, operator, value}
            sort_by: List of sort dictionaries {field, direction}
            
        Returns:
            Modified SQLAlchemy query with filters and sorting applied
        """
        from sqlalchemy import asc, desc, Boolean
        
        # Keep track of aliases used for joins to avoid redundant joins
        # Key: relationship path string (e.g., "form_submission"), Value: alias object
        join_aliases: Dict[str, Any] = {}

        # --- Apply Filters ---
        if filters:
            logger.debug(f"Applying filters for {model_cls.__name__}: {filters}")
            for f_idx, f in enumerate(filters):
                field, op, value = f.get("field"), f.get("operator", "eq").lower(), f.get("value")
                if not field or (value is None and op not in ["isnull", "isnotnull"]):
                    logger.debug(f"Skipping filter #{f_idx} (missing field/value): {f}")
                    continue

                logger.debug(f"Processing filter #{f_idx}: {field} {op} {value}")
                try:
                    # Resolve attribute and add necessary joins FOR FILTERING
                    # Pass the current state of the query and aliases
                    query, model_attr, join_aliases = ReportUtils.resolve_attribute_and_joins(
                        model_cls, field, query, join_aliases
                    )
                    if model_attr is None:
                        logger.warning(f"Could not resolve filter field: {field}")
                        continue

                    # Apply the filter condition
                    op_map = {
                        "eq": lambda a, v: a == v,
                        "neq": lambda a, v: a != v,
                        "like": lambda a, v: a.ilike(f"%{str(v)}%"),
                        "notlike": lambda a, v: ~a.ilike(f"%{str(v)}%"),
                        "startswith": lambda a, v: a.ilike(f"{str(v)}%"),
                        "endswith": lambda a, v: a.ilike(f"%{str(v)}"),
                        "in": lambda a, v: a.in_(v) if isinstance(v, list) else None,
                        "notin": lambda a, v: ~a.in_(v) if isinstance(v, list) else None,
                        "gt": lambda a, v: a > v,
                        "lt": lambda a, v: a < v,
                        "gte": lambda a, v: a >= v,
                        "lte": lambda a, v: a <= v,
                        "between": lambda a, v: ReportUtils.apply_between_filter(a, field, v),
                        "isnull": lambda a, v: a == None,
                        "isnotnull": lambda a, v: a != None,
                    }
                    filter_func = op_map.get(op)
                    if filter_func:
                        condition = None
                        if op in ["isnull", "isnotnull"]:
                             condition = filter_func(model_attr, None)
                        else:
                            # Handle boolean string conversion
                            if isinstance(getattr(model_attr, 'type', None), Boolean) and isinstance(value, str):
                                bool_map = {
                                    'true': True, 'false': False, 
                                    'yes': True, 'no': False, 
                                    '1': True, '0': False,
                                    'on': True, 'off': False
                                }
                                value_lower = value.lower()
                                if value_lower in bool_map:
                                    value = bool_map[value_lower]
                                else:
                                    logger.warning(f"Could not interpret '{value}' as boolean for field '{field}'.")
                                    continue  # Skip filter if boolean conversion fails
                            condition = filter_func(model_attr, value)

                        if condition is not None:
                            query = query.filter(condition)
                            logger.debug(f"Applied filter #{f_idx}: {field} {op} {value}")
                        else:
                            logger.warning(f"Invalid filter value/op for filter #{f_idx} ('{op}' on field '{field}'): {value}")
                    else:
                        logger.warning(f"Unsupported filter operator '{op}' for filter #{f_idx} on field '{field}'")

                except Exception as e:
                    logger.warning(f"Could not apply filter #{f_idx} ({f}): {e}", exc_info=True)

        # --- Apply Sorting ---
        if sort_by:
            logger.debug(f"Applying sorting for {model_cls.__name__}: {sort_by}")
            for s_idx, s in enumerate(sort_by):
                field, direction = s.get("field"), s.get("direction", "asc").lower()
                if not field:
                    logger.debug(f"Skipping sort #{s_idx} (missing field)")
                    continue
                if direction not in ["asc", "desc"]:
                    logger.warning(f"Invalid sort direction '{direction}' for sort #{s_idx} on field '{field}'. Defaulting to 'asc'.")
                    direction = "asc"

                logger.debug(f"Processing sort #{s_idx}: {field} {direction.upper()}")
                try:
                    # Resolve attribute and add necessary joins FOR SORTING
                    # Pass the potentially modified query from filtering stage and current aliases
                    query, sort_attr, join_aliases = ReportUtils.resolve_attribute_and_joins(
                        model_cls, field, query, join_aliases
                    )

                    if sort_attr is not None:
                        order_func = desc if direction == "desc" else asc
                        query = query.order_by(order_func(sort_attr))
                        logger.debug(f"Applied sort #{s_idx}: {field} {direction.upper()}")
                    else:
                        logger.warning(f"Could not resolve sort field for sort #{s_idx}: {field}")
                except Exception as e:
                    logger.error(f"Error applying sort #{s_idx} for field '{field}': {e}", exc_info=True)

        return query  # Return the query with filters and sorts applied

    @staticmethod
    def get_load_options(model_cls: Type, requested_columns: List[str]) -> list:
        """
        Generate SQLAlchemy load options for eager loading relationships
        
        Args:
            model_cls: The model class
            requested_columns: List of columns requested, possibly with relationships
            
        Returns:
            List of SQLAlchemy load options to use with query.options()
        """
        options = []
        relationship_paths = set()
        
        for col in requested_columns:
            if col.startswith(ANSWERS_PREFIX) and model_cls.__name__ == 'FormSubmission':
                relationship_paths.add('answers_submitted')
                continue
                
            parts = col.split('.')
            if len(parts) > 1:
                for i in range(1, len(parts)):
                    relationship_paths.add('.'.join(parts[:i]))
                    
        processed_base_paths = set()
        sorted_paths = sorted(list(relationship_paths), key=lambda x: (x.count('.'), x), reverse=True)
        
        for path_str in sorted_paths:
            parts = path_str.split('.')
            base_path = parts[0]
            
            if base_path in processed_base_paths and len(parts) == 1:
                continue
                
            current_load_option = None
            current_model = model_cls
            
            try:
                for i, part in enumerate(parts):
                    mapper = sqla_inspect(current_model)
                    
                    if part not in mapper.relationships:
                        logger.warning(f"Invalid relationship '{part}' in path '{path_str}' for {current_model.__name__}.")
                        current_load_option = None
                        break
                        
                    relationship = mapper.relationships[part]
                    load_func = selectinload if relationship.uselist else joinedload
                    
                    if i == 0:
                        current_load_option = load_func(getattr(current_model, part))
                    elif current_load_option:
                        current_load_option = current_load_option.selectinload(getattr(current_model, part)) if relationship.uselist else current_load_option.joinedload(getattr(current_model, part))
                        
                    current_model = relationship.mapper.class_
                    
                if current_load_option is not None:
                    options.append(current_load_option)
                    processed_base_paths.add(base_path)
                    
            except AttributeError as ae:
                logger.error(f"AttributeError building load option for '{path_str}': {ae}")
            except Exception as e:
                logger.error(f"Error building load option for '{path_str}': {e}", exc_info=True)
                
        return options

    @staticmethod
    def fetch_data(model_cls: type, filters: List[Dict], sort_by: List[Dict], user: User, requested_columns: List[str]) -> List[Any]:
        """
        Fetch data from the database with filters, sorting and permission checks
        
        Args:
            model_cls: Model class to query
            filters: List of filter dictionaries
            sort_by: List of sort dictionaries
            user: User making the request
            requested_columns: Columns to retrieve
            
        Returns:
            List of model instances
        """
        try:
            query = db.session.query(model_cls)
            
            # Apply soft delete filter if model supports it
            if hasattr(model_cls, 'is_deleted'):
                query = query.filter(model_cls.is_deleted == False)
                
            # Apply RBAC filters
            query = ReportDataFetcher.apply_rbac_filters(query, model_cls, user)
            
            # Apply user-provided filters and sorting
            query = ReportDataFetcher.apply_filters_and_sort(query, model_cls, filters, sort_by)
            
            # Add eager loading options for related data
            load_options = ReportDataFetcher.get_load_options(model_cls, requested_columns)
            if load_options:
                query = query.options(*load_options)
                
            # Execute query
            results = query.all()
            logger.info(f"Fetched {len(results)} records for {model_cls.__name__}.")
            
            return results
        except Exception as e:
            logger.error(f"Error fetching data for {model_cls.__name__}: {e}", exc_info=True)
            raise

    @staticmethod
    def flatten_data(objects: List[Any], columns: List[str], report_type: str) -> List[Dict[str, Any]]:
        """
        Converts model objects into flat dictionaries with column values
        
        Args:
            objects: List of model instances
            columns: List of column names (can include relationships with dot notation)
            report_type: Type of report being generated
            
        Returns:
            List of dictionaries with column values
        """
        from app.models import Question, QuestionType
        
        if not objects:
            return []
            
        flat_data = []
        question_info_map = {}
        
        # Special handling for form submissions to get question type info
        if report_type == 'form_submissions':
             all_questions_text = set()
             for obj in objects:
                 if hasattr(obj, 'answers_submitted'):
                     for ans_sub in obj.answers_submitted:
                         if ans_sub and not ans_sub.is_deleted:
                             all_questions_text.add(ans_sub.question)
                             
             if all_questions_text:
                  questions_from_db = db.session.query(Question.text, QuestionType.type).join(
                      QuestionType, Question.question_type_id == QuestionType.id
                  ).filter(Question.text.in_(list(all_questions_text))).all()
                  question_info_map = {q_text: q_type for q_text, q_type in questions_from_db}
        
        # Process each object
        for obj in objects:
            row_dict = {}
            dynamic_columns_requested = False
            
            # Get standard columns
            for col in columns:
                 if col.startswith(ANSWERS_PREFIX) and report_type == 'form_submissions':
                     dynamic_columns_requested = True
                     continue
                 row_dict[col] = ReportUtils.get_attribute_recursive(obj, col)
            
            # Handle dynamic answer columns for form submissions
            if dynamic_columns_requested and report_type == 'form_submissions' and hasattr(obj, 'answers_submitted'):
                submission_answers = {
                    ans.question: ans.answer 
                    for ans in obj.answers_submitted 
                    if ans and not ans.is_deleted
                }
                
                for col in columns:
                    if col.startswith(ANSWERS_PREFIX):
                        try:
                            question_text = col.split(ANSWERS_PREFIX, 1)[1]
                            answer_value = submission_answers.get(question_text)
                            row_dict[col] = answer_value
                        except IndexError:
                            logger.warning(f"Invalid dynamic answer column format: {col}")
                            row_dict[col] = None
                            
            flat_data.append(row_dict)
            
        return flat_data

    @staticmethod
    def sanitize_columns(
        requested_columns: List[str], 
        entity_type: str, 
        is_admin: bool = False
    ) -> List[str]:
        """
        Sanitize and validate requested columns
        
        Args:
            requested_columns: Columns requested in the report
            entity_type: Type of entity being reported on
            is_admin: Whether the user is an admin
            
        Returns:
            Sanitized list of columns
        """
        from app.models import Question
        
        config = ENTITY_CONFIG.get(entity_type, {})
        available_columns = config.get('available_columns', [])
        
        # Add dynamic answer columns for form submissions
        if entity_type == 'form_submissions':
            try:
                # Get all question texts from the database
                questions = db.session.query(Question.text).filter(Question.is_deleted == False).all()
                for question in questions:
                    if question.text:
                        available_columns.append(f"{ANSWERS_PREFIX}{question.text}")
            except Exception as e:
                logger.error(f"Error getting dynamic columns for form_submissions: {e}")
        
        sensitive_columns = config.get('sensitive_columns', [])
        hidden_columns = config.get('hidden_columns', [])
        
        # If no columns specified, use default columns
        if not requested_columns:
            requested_columns = config.get('default_columns', [])
            
        # Filter out sensitive columns for non-admins
        sanitized_columns = []
        for col in requested_columns:
            # Skip sensitive columns for non-admins
            if not is_admin and col in sensitive_columns:
                continue
                
            # Skip hidden columns for everyone
            if col in hidden_columns:
                continue
                
            # Verify column is available (skip if not)
            if col in available_columns or col.startswith(ANSWERS_PREFIX):
                sanitized_columns.append(col)
            else:
                logger.warning(f"Column '{col}' not available for entity '{entity_type}'")
                
        # If we filtered out all columns, use defaults
        if not sanitized_columns:
            sanitized_columns = [
                col for col in config.get('default_columns', [])
                if col not in hidden_columns and (is_admin or col not in sensitive_columns)
            ]
            
        return sanitized_columns

    @staticmethod
    def get_available_columns(entity_type: str) -> List[str]:
        """
        Get all available columns for a given entity type
        
        Args:
            entity_type: The entity type (e.g., 'users', 'forms')
            
        Returns:
            List of available column names
        """
        from app.models import Question
        
        config = ENTITY_CONFIG.get(entity_type, {})
        available_columns = config.get('available_columns', [])
        
        # Add dynamic answer columns for form submissions
        if entity_type == 'form_submissions':
            try:
                # Get all question texts from the database
                questions = db.session.query(Question.text).filter(Question.is_deleted == False).all()
                for question in questions:
                    if question.text:
                        available_columns.append(f"{ANSWERS_PREFIX}{question.text}")
            except Exception as e:
                logger.error(f"Error getting dynamic columns for form_submissions: {e}")
                
        return available_columns