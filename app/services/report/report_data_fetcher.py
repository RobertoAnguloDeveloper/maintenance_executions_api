# app/services/report/report_data_fetcher.py
from typing import List, Dict, Any, Type, Optional, Tuple
import logging
from sqlalchemy import inspect as sqla_inspect, Boolean # Added Boolean for type checking
from sqlalchemy.orm import Query, joinedload, selectinload, aliased
from app import db
from app.models import User # Assuming User model is in app.models
from app.utils.permission_manager import PermissionManager, EntityType
from .report_config import ANSWERS_PREFIX, ENTITY_CONFIG
from .report_utils import ReportUtils

logger = logging.getLogger(__name__)

class ReportDataFetcher:
    """Responsible for fetching and processing data for reports"""

    @staticmethod
    def apply_rbac_filters(query: Query, model_cls: type, user: User) -> Query:
        """
        Apply Role-Based Access Control filters to a query.
        This method ensures that users only see data they are permitted to access
        based on their role and environment.

        Args:
            query: SQLAlchemy query to modify.
            model_cls: Model class being queried.
            user: User making the request.

        Returns:
            Query with RBAC filters applied.
        """
        from app.models import (
            User, FormSubmission, Form, Role, Environment,
            AnswerSubmitted, Attachment, RolePermission, FormQuestion, FormAnswer,
            FormAssignment # Import the FormAssignment model
        )

        # Super users can see everything, no RBAC filters needed for them.
        if user.role and user.role.is_super_user:
            return query

        env_id = user.environment_id
        user_role_name = user.role.name if user.role else None

        # Apply RBAC rules based on the model class being queried.
        if model_cls == User:
            # Users can only see other users within their own environment.
            return query.filter(User.environment_id == env_id)
        elif model_cls == FormSubmission:
            # For FormSubmissions, access depends on the user's role.
            FormCreatorUser = aliased(User) # Alias for joining User table as form creator
            if user_role_name in ['site_manager', 'supervisor']:
                # Site managers and supervisors can see submissions for forms created by users in their environment.
                return query.join(Form, Form.id == FormSubmission.form_id)\
                            .join(FormCreatorUser, FormCreatorUser.id == Form.user_id)\
                            .filter(FormCreatorUser.environment_id == env_id)
            else:
                # Other users can only see submissions they made themselves.
                return query.filter(FormSubmission.submitted_by == user.username)
        elif model_cls == Form:
            # Users can see public forms or forms created by users in their environment.
            FormCreatorUser = aliased(User)
            return query.join(FormCreatorUser, FormCreatorUser.id == Form.user_id)\
                        .filter(db.or_(Form.is_public == True, FormCreatorUser.environment_id == env_id))
        elif model_cls == FormAssignment: # RBAC rule for the new FormAssignment entity
            # Users can see assignments for public forms or forms created by users in their environment.
            FormCreatorUser = aliased(User)
            return query.join(Form, Form.id == FormAssignment.form_id)\
                        .join(FormCreatorUser, FormCreatorUser.id == Form.user_id)\
                        .filter(db.or_(Form.is_public == True, FormCreatorUser.environment_id == env_id))
        elif model_cls == Environment:
            # Users can only see their own environment.
            return query.filter(Environment.id == env_id)
        elif model_cls == Role:
            # Users cannot see superuser roles unless they are superusers (handled above).
            return query.filter(Role.is_super_user == False)
        elif model_cls in [AnswerSubmitted, Attachment]:
            # For answers and attachments, access is tied to the form submission's form creator's environment.
            link_relationship = getattr(model_cls, 'form_submission', None)
            if link_relationship is None:
                logger.error(f"RBAC Error: No 'form_submission' relationship found on {model_cls.__name__} for linking.")
                return query.filter(False)  # No access if relationship is missing
            FormCreatorUser = aliased(User)
            return query.join(link_relationship)\
                        .join(Form, Form.id == FormSubmission.form_id)\
                        .join(FormCreatorUser, FormCreatorUser.id == Form.user_id)\
                        .filter(FormCreatorUser.environment_id == env_id)
        elif model_cls == RolePermission:
            # Users cannot see permissions for superuser roles.
            return query.join(Role, Role.id == RolePermission.role_id)\
                        .filter(Role.is_super_user == False)
        elif model_cls == FormQuestion:
            # Access to form questions is tied to the form's visibility (public or creator's environment).
            FormCreatorUser = aliased(User)
            return query.join(Form, Form.id == FormQuestion.form_id)\
                        .join(FormCreatorUser, FormCreatorUser.id == Form.user_id)\
                        .filter(db.or_(Form.is_public == True, FormCreatorUser.environment_id == env_id))
        elif model_cls == FormAnswer: # Predefined answers for form questions
            # Access to predefined form answers is tied to the form's visibility.
            FormCreatorUser = aliased(User)
            return query.join(FormQuestion, FormQuestion.id == FormAnswer.form_question_id)\
                        .join(Form, Form.id == FormQuestion.form_id)\
                        .join(FormCreatorUser, FormCreatorUser.id == Form.user_id)\
                        .filter(db.or_(Form.is_public == True, FormCreatorUser.environment_id == env_id))

        # Default RBAC filters if the model has common attributes like 'environment_id' or 'user_id'.
        if hasattr(model_cls, 'environment_id'):
            logger.warning(f"Applying default environment-based RBAC for {model_cls.__name__}")
            return query.filter(model_cls.environment_id == env_id)
        elif hasattr(model_cls, 'user_id'): # Generic fallback if an entity is user-specific
            logger.warning(f"Applying default user-specific RBAC for {model_cls.__name__}")
            return query.filter(model_cls.user_id == user.id)

        logger.warning(f"No specific RBAC rule defined for {model_cls.__name__} for user role {user_role_name}. Allowing access by default (may need review).")
        return query

    @staticmethod
    def apply_filters_and_sort(query: Query, model_cls: type, filters: List[Dict], sort_by: List[Dict]) -> Query:
        """
        Applies filtering and sorting to a SQLAlchemy query object.
        It uses ReportUtils.resolve_attribute_and_joins to handle nested fields
        and automatically add necessary joins with aliases.

        Args:
            query: The SQLAlchemy query to modify.
            model_cls: The model class being queried.
            filters: List of filter dictionaries, e.g., {"field": "name", "operator": "eq", "value": "Test"}.
            sort_by: List of sort dictionaries, e.g., {"field": "created_at", "direction": "desc"}.

        Returns:
            Modified SQLAlchemy query with filters and sorting applied.
        """
        from sqlalchemy import asc, desc # For sorting

        join_aliases: Dict[str, Any] = {} # Tracks aliases used for joins to avoid redundancy.

        # --- Apply Filters ---
        if filters:
            logger.debug(f"Applying filters for {model_cls.__name__}: {filters}")
            for f_idx, f_config in enumerate(filters):
                field = f_config.get("field")
                op = f_config.get("operator", "eq").lower() # Default operator is 'equals'
                value = f_config.get("value")

                if not field or (value is None and op not in ["isnull", "isnotnull"]):
                    logger.debug(f"Skipping filter #{f_idx} (missing field/value for relevant op): {f_config}")
                    continue

                logger.debug(f"Processing filter #{f_idx}: {field} {op} {value}")
                try:
                    # Resolve the attribute path and add necessary joins.
                    query, model_attr, join_aliases = ReportUtils.resolve_attribute_and_joins(
                        model_cls, field, query, join_aliases
                    )
                    if model_attr is None:
                        logger.warning(f"Could not resolve filter field: {field} for model {model_cls.__name__}")
                        continue

                    # Map operator strings to SQLAlchemy filter conditions.
                    # Ensure value types are compatible with model_attr types.
                    op_map = {
                        "eq": lambda attr, val: attr == val,
                        "neq": lambda attr, val: attr != val,
                        "like": lambda attr, val: attr.ilike(f"%{str(val)}%"), # Case-insensitive like
                        "notlike": lambda attr, val: ~attr.ilike(f"%{str(val)}%"),
                        "startswith": lambda attr, val: attr.ilike(f"{str(val)}%"),
                        "endswith": lambda attr, val: attr.ilike(f"%{str(val)}"),
                        "in": lambda attr, val: attr.in_(val) if isinstance(val, list) else None,
                        "notin": lambda attr, val: ~attr.in_(val) if isinstance(val, list) else None,
                        "gt": lambda attr, val: attr > val,
                        "lt": lambda attr, val: attr < val,
                        "gte": lambda attr, val: attr >= val,
                        "lte": lambda attr, val: attr <= val,
                        "between": lambda attr, val: ReportUtils.apply_between_filter(attr, field, val), # Uses helper
                        "isnull": lambda attr, val: attr == None, # val is ignored
                        "isnotnull": lambda attr, val: attr != None, # val is ignored
                    }
                    filter_func = op_map.get(op)
                    if filter_func:
                        condition = None
                        if op in ["isnull", "isnotnull"]:
                             condition = filter_func(model_attr, None) # Value is not used for isnull/isnotnull
                        else:
                            # Handle boolean string conversion for Boolean columns.
                            # sqla_inspect(model_attr.parententity).columns[model_attr.key].type
                            # The above is complex; simpler to check type of model_attr.type if available
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
                                    logger.warning(f"Could not interpret '{value}' as boolean for field '{field}'. Skipping filter.")
                                    continue
                            condition = filter_func(model_attr, value)

                        if condition is not None:
                            query = query.filter(condition)
                            logger.debug(f"Applied filter #{f_idx}: {field} {op} {value}")
                        else:
                            logger.warning(f"Invalid value/op for filter #{f_idx} ('{op}' on '{field}'): {value}")
                    else:
                        logger.warning(f"Unsupported filter operator '{op}' for filter #{f_idx} on field '{field}'")

                except Exception as e:
                    logger.warning(f"Could not apply filter #{f_idx} ({f_config}): {e}", exc_info=True)

        # --- Apply Sorting ---
        if sort_by:
            logger.debug(f"Applying sorting for {model_cls.__name__}: {sort_by}")
            for s_idx, s_config in enumerate(sort_by):
                field = s_config.get("field")
                direction = s_config.get("direction", "asc").lower() # Default direction is 'ascending'

                if not field:
                    logger.debug(f"Skipping sort #{s_idx} (missing field): {s_config}")
                    continue
                if direction not in ["asc", "desc"]:
                    logger.warning(f"Invalid sort direction '{direction}' for sort #{s_idx} on field '{field}'. Defaulting to 'asc'.")
                    direction = "asc"

                logger.debug(f"Processing sort #{s_idx}: {field} {direction.upper()}")
                try:
                    # Resolve the attribute path and add necessary joins for sorting.
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

        return query

    @staticmethod
    def get_load_options(model_cls: Type, requested_columns: List[str]) -> list:
        """
        Generate SQLAlchemy load options for eager loading relationships.
        This helps prevent N+1 query problems by fetching related data in fewer queries.

        Args:
            model_cls: The base model class.
            requested_columns: List of columns requested, possibly including dot-notated paths
                               for relationships (e.g., "creator.role.name").

        Returns:
            List of SQLAlchemy load options (e.g., [joinedload(...), selectinload(...)]).
        """
        options = []
        relationship_paths = set() # Stores unique paths to relationships

        # Identify all relationship paths from the requested columns.
        for col in requested_columns:
            if col.startswith(ANSWERS_PREFIX) and model_cls.__name__ == 'FormSubmission':
                # Special handling for dynamic answer columns in FormSubmission.
                relationship_paths.add('answers_submitted') # Eager load all submitted answers.
                continue

            parts = col.split('.')
            if len(parts) > 1:
                # For a path like "a.b.c", add "a" and "a.b" to relationship_paths.
                for i in range(1, len(parts)):
                    relationship_paths.add('.'.join(parts[:i]))

        # Sort paths to process deeper paths first, ensuring correct chaining of load options.
        # Example: Process "creator.role" before "creator".
        sorted_paths = sorted(list(relationship_paths), key=lambda x: (x.count('.'), x), reverse=True)
        
        processed_base_paths = set() # Tracks base relationships already handled to avoid redundant options.

        for path_str in sorted_paths:
            parts = path_str.split('.')
            base_path = parts[0] # The first part of the path (e.g., "creator" from "creator.role")

            # If only one part and it's already processed as part of a longer path, skip.
            if base_path in processed_base_paths and len(parts) == 1:
                continue

            current_load_option = None
            current_model = model_cls # Start traversal from the base model.

            try:
                # Build the load option by traversing the path.
                for i, part_name in enumerate(parts):
                    mapper = sqla_inspect(current_model) # Get SQLAlchemy mapper for the current model.

                    if part_name not in mapper.relationships:
                        logger.warning(f"Invalid relationship part '{part_name}' in path '{path_str}' for model {current_model.__name__}.")
                        current_load_option = None # Invalidate current option chain.
                        break

                    relationship = mapper.relationships[part_name]
                    # Use selectinload for to-many relationships, joinedload for to-one.
                    load_func = selectinload if relationship.uselist else joinedload

                    if i == 0: # First part of the path, create the initial load option.
                        current_load_option = load_func(getattr(current_model, part_name))
                    elif current_load_option: # Subsequent parts, chain the load option.
                        current_load_option = current_load_option.selectinload(getattr(current_model, part_name)) if relationship.uselist \
                                            else current_load_option.joinedload(getattr(current_model, part_name))

                    current_model = relationship.mapper.class_ # Move to the related model for the next part.

                if current_load_option is not None:
                    options.append(current_load_option)
                    processed_base_paths.add(base_path) # Mark this base path as processed.

            except AttributeError as ae:
                logger.error(f"AttributeError while building load option for path '{path_str}': {ae}")
            except Exception as e:
                logger.error(f"Unexpected error building load option for path '{path_str}': {e}", exc_info=True)

        return options

    @staticmethod
    def fetch_data(model_cls: type, filters: List[Dict], sort_by: List[Dict], user: User, requested_columns: List[str]) -> List[Any]:
        """
        Fetch data from the database with filters, sorting, permission checks, and eager loading.

        Args:
            model_cls: SQLAlchemy model class to query.
            filters: List of filter dictionaries.
            sort_by: List of sort dictionaries.
            user: The user making the request (for RBAC).
            requested_columns: List of columns to retrieve, used for optimizing loads.

        Returns:
            List of model instances.
        """
        try:
            query = db.session.query(model_cls)

            # Apply soft delete filter if the model supports it (has 'is_deleted' attribute).
            if hasattr(model_cls, 'is_deleted'):
                query = query.filter(model_cls.is_deleted == False)

            # Apply Role-Based Access Control filters.
            query = ReportDataFetcher.apply_rbac_filters(query, model_cls, user)

            # Apply user-provided filters and sorting.
            query = ReportDataFetcher.apply_filters_and_sort(query, model_cls, filters, sort_by)

            # Add eager loading options for related data to optimize query performance.
            load_options = ReportDataFetcher.get_load_options(model_cls, requested_columns)
            if load_options:
                query = query.options(*load_options)

            # Execute the query.
            results = query.all()
            logger.info(f"Fetched {len(results)} records for {model_cls.__name__} with applied filters and RBAC for user '{user.username}'.")

            return results
        except Exception as e:
            logger.error(f"Error fetching data for {model_cls.__name__}: {e}", exc_info=True)
            raise # Re-raise the exception to be handled by the caller.

    @staticmethod
    def flatten_data(objects: List[Any], columns: List[str], report_type: str) -> List[Dict[str, Any]]:
        """
        Converts a list of SQLAlchemy model objects into a list of flat dictionaries.
        Each dictionary represents a row, with keys corresponding to the requested columns.
        Handles dot-notation for related attributes and special formatting for FormSubmission answers.

        Args:
            objects: List of model instances.
            columns: List of column names (can include relationships with dot notation, e.g., "creator.name").
            report_type: The type of report being generated (e.g., "form_submissions"),
                         used for special handling like dynamic answer columns.

        Returns:
            List of dictionaries, where each dictionary is a flattened row of data.
        """
        from app.models import Question, QuestionType # Local import for specific use

        if not objects:
            return []

        flat_data_list = []
        question_info_map = {} # Cache for question type info, used for form_submissions

        # Pre-fetch question type information if dealing with form_submissions and dynamic answers.
        if report_type == 'form_submissions':
             all_questions_text_in_batch = set()
             # Collect all unique question texts from the current batch of submissions.
             for obj in objects:
                 if hasattr(obj, 'answers_submitted'):
                     for ans_sub in obj.answers_submitted:
                         if ans_sub and not ans_sub.is_deleted: # Check if submitted answer is not soft-deleted
                             all_questions_text_in_batch.add(ans_sub.question)

             if all_questions_text_in_batch:
                  # Query the database for question types associated with these texts.
                  questions_from_db = db.session.query(Question.text, QuestionType.type)\
                      .join(QuestionType, Question.question_type_id == QuestionType.id)\
                      .filter(Question.text.in_(list(all_questions_text_in_batch)), Question.is_deleted == False)\
                      .all()
                  question_info_map = {q_text: q_type for q_text, q_type in questions_from_db}

        # Process each object in the input list.
        for obj in objects:
            row_dict = {}
            dynamic_columns_requested_for_this_row = False

            # Populate standard columns using ReportUtils.get_attribute_recursive.
            for col_path in columns:
                 if col_path.startswith(ANSWERS_PREFIX) and report_type == 'form_submissions':
                     dynamic_columns_requested_for_this_row = True
                     continue # Dynamic columns handled separately below.
                 row_dict[col_path] = ReportUtils.get_attribute_recursive(obj, col_path)

            # Handle dynamic answer columns specifically for 'form_submissions' report type.
            if dynamic_columns_requested_for_this_row and report_type == 'form_submissions' and hasattr(obj, 'answers_submitted'):
                # Create a dictionary of answers for the current submission for quick lookup.
                submission_answers = {
                    ans.question: ans.answer
                    for ans in obj.answers_submitted
                    if ans and not ans.is_deleted # Consider only non-deleted submitted answers
                }

                # Populate dynamic answer columns based on the ANSWERS_PREFIX.
                for col_path in columns:
                    if col_path.startswith(ANSWERS_PREFIX):
                        try:
                            question_text = col_path.split(ANSWERS_PREFIX, 1)[1]
                            answer_value = submission_answers.get(question_text)
                            # Value formatting (e.g., date parsing) might be needed here based on question_info_map
                            # For now, it stores the raw answer value.
                            row_dict[col_path] = answer_value
                        except IndexError:
                            logger.warning(f"Invalid dynamic answer column format encountered: {col_path}")
                            row_dict[col_path] = None # Default to None if format is incorrect.

            flat_data_list.append(row_dict)

        return flat_data_list

    @staticmethod
    def sanitize_columns(requested_columns: List[str], entity_type: str, is_admin: bool = False) -> List[str]:
        """
        Sanitize and validate the list of requested columns against the entity's configuration.
        Removes sensitive columns for non-admins and hidden columns for everyone.
        Adds dynamic answer columns for 'form_submissions' if applicable.

        Args:
            requested_columns: List of columns requested by the user.
            entity_type: The type of entity being reported on (e.g., 'users', 'form_submissions').
            is_admin: Boolean indicating if the requesting user is an administrator.

        Returns:
            A sanitized list of column names valid for the report.
        """
        from app.models import Question # Local import for fetching question texts

        config = ENTITY_CONFIG.get(entity_type, {})
        available_columns_from_config = list(config.get('available_columns', [])) # Make a copy

        # Dynamically add answer columns for 'form_submissions' entity.
        if entity_type == 'form_submissions':
            try:
                # Fetch all non-deleted question texts from the database.
                # These will form the basis for dynamic answer columns.
                questions = db.session.query(Question.text).filter(Question.is_deleted == False).all()
                for question in questions:
                    if question.text: # Ensure question text is not empty
                        # Construct column name like "answers.What is your name?"
                        available_columns_from_config.append(f"{ANSWERS_PREFIX}{question.text}")
            except Exception as e:
                logger.error(f"Error fetching dynamic answer columns for 'form_submissions': {e}", exc_info=True)

        sensitive_columns = config.get('sensitive_columns', [])
        hidden_columns = config.get('hidden_columns', []) # Columns to always hide

        # If no columns were explicitly requested, use the default columns defined in config.
        if not requested_columns:
            requested_columns = list(config.get('default_columns', []))

        sanitized_columns = []
        for col in requested_columns:
            # Skip sensitive columns if the user is not an admin.
            if not is_admin and col in sensitive_columns:
                logger.debug(f"Sanitizing: '{col}' is sensitive, user is not admin. Skipping.")
                continue

            # Skip hidden columns for all users.
            if col in hidden_columns:
                logger.debug(f"Sanitizing: '{col}' is hidden. Skipping.")
                continue

            # Verify that the column is available for the entity (either in config or dynamically added).
            # For dynamic answer columns (form_submissions), they are added to available_columns_from_config.
            if col in available_columns_from_config:
                sanitized_columns.append(col)
            else:
                logger.warning(f"Column '{col}' requested for entity '{entity_type}' is not available or not permitted. Skipping.")

        # If all requested columns were filtered out (e.g., due to permissions or invalid names),
        # fall back to the default columns (after sanitizing them as well).
        if not sanitized_columns and requested_columns: # Only fallback if original request was not empty
            logger.warning(f"All requested columns for '{entity_type}' were filtered out. Falling back to defaults.")
            default_columns_for_fallback = list(config.get('default_columns', []))
            sanitized_columns = [
                col for col in default_columns_for_fallback
                if col not in hidden_columns and (is_admin or col not in sensitive_columns)
            ]
        elif not sanitized_columns and not requested_columns: # If no columns requested and defaults are also empty/filtered
             logger.warning(f"No columns available for '{entity_type}' after sanitization (no request, defaults empty/filtered).")


        return sanitized_columns

    @staticmethod
    def get_available_columns(entity_type: str) -> List[str]:
        """
        Get all potentially available columns for a given entity type, including dynamic ones.
        This list is used for validation and UI suggestions. It does NOT apply permission-based sanitization.

        Args:
            entity_type: The entity type (e.g., 'users', 'form_submissions').

        Returns:
            List of all available column names for the entity.
        """
        from app.models import Question # Local import

        config = ENTITY_CONFIG.get(entity_type, {})
        # Start with columns defined in the configuration.
        available_columns = list(config.get('available_columns', [])) # Make a copy

        # Add dynamic answer columns specifically for 'form_submissions'.
        if entity_type == 'form_submissions':
            try:
                questions = db.session.query(Question.text).filter(Question.is_deleted == False).all()
                for question in questions:
                    if question.text:
                        available_columns.append(f"{ANSWERS_PREFIX}{question.text}")
            except Exception as e:
                logger.error(f"Error dynamically getting available answer columns for 'form_submissions': {e}", exc_info=True)

        return available_columns
