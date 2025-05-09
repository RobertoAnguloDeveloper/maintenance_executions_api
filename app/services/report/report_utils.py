# app/services/report/report_utils.py
from typing import Any, Dict, Optional, Tuple, List, Set, Type
import logging
from datetime import datetime, date
import pandas as pd
import numpy as np
import os
from sqlalchemy import inspect as sqla_inspect, or_, asc, desc, func, text, Boolean, String, Integer, Date, DateTime
from sqlalchemy.orm import Query, joinedload, selectinload, Session, aliased
from app import db

logger = logging.getLogger(__name__)

class ReportUtils:
    """Utility functions for report generation"""

    @staticmethod
    def get_attribute_recursive(obj: Any, attr_string: str) -> Any:
        """
        Recursively retrieves nested attributes from an object, formatting specific types.
        
        Args:
            obj: The object to retrieve attributes from
            attr_string: Dot-notation string path to the attribute
            
        Returns:
            The value of the attribute, formatted appropriately for type
        """
        value = obj
        try:
            for attr in attr_string.split('.'):
                if value is None: 
                    return None
                if '[' in attr and attr.endswith(']'):
                    attr_name, index_str = attr.split('[', 1)
                    index = int(index_str[:-1])
                    list_attr = getattr(value, attr_name, None)
                    value = list_attr[index] if isinstance(list_attr, list) and len(list_attr) > index else None
                else:
                    value = getattr(value, attr, None)
            
            # Format value based on type
            if isinstance(value, datetime): 
                return value.isoformat(sep=' ', timespec='seconds')
            if isinstance(value, date): 
                return value.isoformat()
            if isinstance(value, bool): 
                return "Yes" if value else "No"  # Keep boolean formatting consistent
            
            return value
        except (AttributeError, ValueError, IndexError, TypeError):
            return None

    @staticmethod
    def resolve_attribute_and_joins(base_model: Type, field_path: str, query: Query, current_aliases: Dict[str, Any]) -> Tuple[Query, Optional[Any], Dict[str, Any]]:
        """
        Helper to resolve a potentially nested attribute path (like 'form_submission.submitted_at')
        and ensure necessary joins are added to the query using aliases. It modifies the query
        object directly if joins are needed.

        Args:
            base_model: The starting SQLAlchemy model class (e.g., AnswerSubmitted).
            field_path: The dot-separated attribute path string (e.g., "form_submission.submitted_at").
            query: The current SQLAlchemy Query object to potentially modify.
            current_aliases: A dictionary tracking aliases already used for join paths.
                             Key: join path string (e.g., "form_submission"), Value: alias object.

        Returns:
            Tuple containing:
                - The potentially modified Query object (with joins added).
                - The resolved SQLAlchemy attribute object (e.g., AliasedClass.attribute) or None.
                - The updated dictionary of current_aliases.
        """
        parts = field_path.split('.')
        current_model_or_alias = base_model  # Start with the base model type
        current_path_key = ""  # Tracks the path for aliasing keys

        logger.debug(f"Resolving path: '{field_path}' starting from {base_model.__name__}")

        for i, part in enumerate(parts):
            is_last_part = (i == len(parts) - 1)

            # Inspect the current model or alias we are traversing from
            # If current_model_or_alias is an AliasedClass, inspect its mapper
            if isinstance(current_model_or_alias, type):  # It's a model class
                 current_mapper = sqla_inspect(current_model_or_alias)
                 current_class_for_attr = current_model_or_alias
            else:  # It's an AliasedClass instance
                 current_mapper = sqla_inspect(current_model_or_alias.entity)
                 current_class_for_attr = current_model_or_alias  # Use alias directly for getattr

            if is_last_part:
                # Last part should be a column/attribute on the current model/alias
                if hasattr(current_class_for_attr, part):
                    resolved_attribute = getattr(current_class_for_attr, part)
                    logger.debug(f"Resolved attribute '{field_path}' to {resolved_attribute}")
                    # Return the query (possibly modified with joins) and the final attribute
                    return query, resolved_attribute, current_aliases
                else:
                    logger.warning(f"Attribute '{part}' not found on {current_mapper.class_.__name__} (aliased: {not isinstance(current_model_or_alias, type)}) for path '{field_path}'")
                    return query, None, current_aliases
            else:
                # Intermediate part must be a relationship defined on the current mapper
                if part in current_mapper.relationships:
                    relationship = current_mapper.relationships[part]
                    related_model = relationship.mapper.class_
                    relationship_key = relationship.key  # The attribute name for the relationship (e.g., 'form_submission')

                    # Build the key for the alias dictionary (e.g., "form_submission" or "form_submission.form")
                    new_path_key = f"{current_path_key}.{relationship_key}" if current_path_key else relationship_key

                    if new_path_key not in current_aliases:
                        # Need to add a join with a new alias
                        logger.debug(f"Adding join for path '{new_path_key}' from {current_class_for_attr} using relationship '{relationship_key}'")
                        related_alias = aliased(related_model)
                        current_aliases[new_path_key] = related_alias  # Store the new alias

                        # Join from the previous model/alias to the new alias using the relationship attribute
                        # Ensure we use the correct source for the relationship attribute
                        join_source = current_model_or_alias if not isinstance(current_model_or_alias, type) else base_model
                        query = query.join(related_alias, getattr(join_source, relationship_key))
                        current_model_or_alias = related_alias  # Continue traversal from the new alias
                    else:
                        # Join already exists, just continue traversal from the existing alias
                        logger.debug(f"Reusing join alias for path '{new_path_key}'")
                        current_model_or_alias = current_aliases[new_path_key]  # Continue from the existing alias

                    current_path_key = new_path_key  # Update the path key for the next level

                else:
                    logger.warning(f"Relationship '{part}' not found on {current_mapper.class_.__name__} (aliased: {not isinstance(current_model_or_alias, type)}) for path '{field_path}'")
                    return query, None, current_aliases

        # Should not be reached if path is valid
        logger.error(f"Path resolution failed unexpectedly for '{field_path}'")
        return query, None, current_aliases

    @staticmethod
    def apply_between_filter(model_attr: Any, field_name: str, value: List) -> Optional[Any]:
        """
        Applies a 'between' filter, attempting date/datetime conversion.
        
        Args:
            model_attr: The model attribute to filter on
            field_name: The name of the field (used for date detection)
            value: List containing [start, end] values
            
        Returns:
            SQLAlchemy between expression or None if invalid
        """
        if not isinstance(value, list) or len(value) != 2: 
            return None
            
        try:
            start, end = value[0], value[1]
            col_type = getattr(model_attr, 'type', None)
            is_date_type = isinstance(col_type, (db.Date, db.DateTime)) if col_type and hasattr(db, 'Date') else False
            is_likely_date = any(sub in field_name.lower() for sub in ["at", "date"])
            
            if is_date_type or is_likely_date:
                start_dt = pd.to_datetime(start, errors='coerce')
                end_dt = pd.to_datetime(end, errors='coerce')
                
                if pd.notna(start_dt) and pd.notna(end_dt):
                    if isinstance(col_type, db.Date) and not isinstance(col_type, db.DateTime):
                         start_dt = start_dt.date()
                         end_dt = end_dt.date()
                    return model_attr.between(start_dt, end_dt)
                else: 
                    return None
            else: 
                return model_attr.between(start, end)
        except Exception as e:
            logger.warning(f"Error applying 'between' filter on {field_name}: {e}")
            return None

    @staticmethod
    def safe_value_counts(df: pd.DataFrame, column: str, top_n: Optional[int] = 10) -> Dict:
        """
        Safely calculate value counts for a column with handling for lists and other types
        
        Args:
            df: Pandas DataFrame
            column: Column name to count values for
            top_n: Number of top values to return
            
        Returns:
            Dictionary with value counts
        """
        if column not in df.columns or df[column].isnull().all():
            return {}
            
        try:
            # Handle columns that contain lists
            if df[column].apply(lambda x: isinstance(x, list)).any():
                counts = df[column].apply(lambda x: tuple(x) if isinstance(x, list) else x).value_counts()
            else:
                counts = df[column].value_counts()
                
            # Limit to top N if specified
            if top_n:
                counts = counts.nlargest(top_n)
                
            # Convert to regular Python types for serialization
            return {
                str(k): int(v) if isinstance(v, np.integer) else 
                        float(v) if isinstance(v, np.floating) else v 
                for k, v in counts.to_dict().items()
            }
        except Exception as e:
            logger.warning(f"Could not calculate value counts for column '{column}': {e}")
            return {}

    @staticmethod
    def detect_chart_columns(df: pd.DataFrame, report_type: str, config: Dict) -> Dict[str, List[str]]:
        """
        Detect columns that are suitable for different chart types
        
        Args:
            df: Pandas DataFrame with the data
            report_type: Type of report
            config: Report configuration
            
        Returns:
            Dictionary with columns suitable for different chart types
        """
        from .report_config import GENERIC_CATEGORICAL_COLS, MAX_UNIQUE_GENERIC_CHART
        
        chart_columns = {
            'bar_charts': [],
            'pie_charts': [],
            'time_series': [],
            'scatter_plots': [],
            'histograms': []
        }
        
        # Get hints from configuration
        hints = config.get('analysis_hints', {})
        chart_hints = config.get('chart_hints', {})
        
        # Use chart hints if available
        if chart_hints:
            for chart_type, columns in chart_hints.items():
                if chart_type in chart_columns:
                    chart_columns[chart_type].extend([
                        col for col in columns 
                        if col in df.columns
                    ])
        
        # Fill in with detected columns based on types
        for col in df.columns:
            # Skip columns with too many unique values
            unique_count = df[col].nunique()
            
            if unique_count <= 1:
                continue  # Skip columns with only one value
                
            col_type = df[col].dtype
            
            # Detect date columns for time series
            if pd.api.types.is_datetime64_any_dtype(col_type):
                if col not in chart_columns['time_series']:
                    chart_columns['time_series'].append(col)
            
            # Detect categorical columns for bar/pie charts
            elif (col in hints.get('categorical_columns', []) or
                  any(cat_name in col.lower() for cat_name in GENERIC_CATEGORICAL_COLS) or
                  pd.api.types.is_categorical_dtype(col_type) or
                  pd.api.types.is_object_dtype(col_type) or
                  pd.api.types.is_bool_dtype(col_type)):
                
                if unique_count <= MAX_UNIQUE_GENERIC_CHART:
                    if col not in chart_columns['bar_charts']:
                        chart_columns['bar_charts'].append(col)
                    
                    if unique_count <= 8 and col not in chart_columns['pie_charts']:
                        chart_columns['pie_charts'].append(col)
            
            # Detect numeric columns for histograms and scatter plots
            elif pd.api.types.is_numeric_dtype(col_type):
                if col not in chart_columns['histograms']:
                    chart_columns['histograms'].append(col)
                
                # For scatter plots, we need pairs of numeric columns
                for other_col in df.columns:
                    if (other_col != col and 
                        pd.api.types.is_numeric_dtype(df[other_col].dtype) and
                        df[other_col].nunique() > 5):
                        chart_columns['scatter_plots'].append(f"{col}-{other_col}")
        
        return chart_columns