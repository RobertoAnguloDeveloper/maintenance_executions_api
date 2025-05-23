# app/services/report/report_stats_generator.py
from typing import Dict, List, Any, Optional
import logging
import pandas as pd
import numpy as np

from app.services.report.report_config import ANSWERS_PREFIX, MAX_UNIQUE_GENERIC_CHART
from app.services.report.report_utils import ReportUtils

logger = logging.getLogger(__name__)

class ReportStatsGenerator:
    """
    Generates statistics for reports
    """
    
    @staticmethod
    def _generate_generic_stats(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate generic statistics for any entity type
        
        Args:
            df: Pandas DataFrame with entity data
            params: Report parameters
            
        Returns:
            Dictionary of statistics
        """
        
        stats: Dict[str, Any] = {}
        report_type = params.get("report_type", "unknown_entity")
        logger.info(f"Generating generic stats for {report_type}")

        if df.empty:
            stats['record_count'] = 0
            return stats

        stats['record_count'] = len(df)
        
        # --- Generic Categorical Stats ---
        categorical_stats_count = 0
        MAX_GENERIC_CATEGORICAL_STATS = 5  # Limit the number of distinct categorical columns we generate stats for

        # Iterate through all columns present in the DataFrame
        for col_name in df.columns:
            if categorical_stats_count >= MAX_GENERIC_CATEGORICAL_STATS:
                break

            # Ensure col_name is treated as a string for operations
            current_col_name_str = str(col_name)

            is_suitable_categorical = False
            # Use dropna=True so that uniqueness is not affected by presence of NaNs for decision-making
            num_unique = df[current_col_name_str].nunique(dropna=True) 
            
            # Define range for what's considered a "countable" or "categorical" column for stats
            # We allow more unique values for stats (top_n will limit) than for direct charting.
            is_in_stat_range = 1 < num_unique <= (MAX_UNIQUE_GENERIC_CHART * 2)  # 2-30 unique values

            col_dtype = df[current_col_name_str].dtype
            
            # Determine if column is suitable for categorical stats
            if pd.api.types.is_bool_dtype(col_dtype):
                is_suitable_categorical = True
            elif pd.api.types.is_integer_dtype(col_dtype):
                # For integers (like IDs), keep the stricter unique check
                if 1 < num_unique <= (MAX_UNIQUE_GENERIC_CHART * 2):
                    is_suitable_categorical = True
            elif pd.api.types.is_string_dtype(col_dtype) or col_dtype == 'object':
                # For strings/objects, be more lenient on total unique count
                if 1 < num_unique:
                    is_suitable_categorical = True
            
            if is_suitable_categorical:
                col_stats_values = ReportUtils.safe_value_counts(df, current_col_name_str, top_n=10)
                if col_stats_values:
                    safe_col_key = ''.join(c if c.isalnum() else '_' for c in current_col_name_str)[:30]
                    stats[f'counts_{safe_col_key}'] = col_stats_values
                    categorical_stats_count += 1
                    logger.debug(f"Generated generic count stat for column '{current_col_name_str}' in {report_type}")

        # --- Generic Date Range Stats ---
        # This logic prioritizes hinted date columns but also scans the DataFrame
        hinted_date_cols = params.get('_internal_config', {}).get('analysis_hints', {}).get('date_columns', [])
        date_candidates = set(hinted_date_cols)
        
        for col_name in df.columns:  # Also check all df columns for datetime types
            if pd.api.types.is_datetime64_any_dtype(df[str(col_name)].dtype):
                date_candidates.add(str(col_name))
        
        # Generate stat for the first valid date column found
        for col_name_str in list(date_candidates):  # Iterate a copy
            if col_name_str in df.columns and pd.api.types.is_datetime64_any_dtype(df[col_name_str].dtype):
                valid_dates = df[col_name_str].dropna()
                if not valid_dates.empty:
                    safe_col_key = ''.join(c if c.isalnum() else '_' for c in col_name_str)[:30]
                    stats[f'range_{safe_col_key}'] = {
                        'first': valid_dates.min().isoformat(),
                        'last': valid_dates.max().isoformat()
                    }
                    logger.debug(f"Generated generic date range stat for column '{col_name_str}' in {report_type}")
                    break  # Only take the first date column found for a generic range stat

        logger.debug(f"Generated generic stats for {report_type}: {list(stats.keys())}")
        return stats
        
    @staticmethod
    def generate_submission_stats(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate statistics for form submissions
        
        Args:
            df: Pandas DataFrame with submission data
            params: Report parameters
            
        Returns:
            Dictionary of statistics
        """
        stats = {}
        question_info = params.get('_internal_question_info', {})
        
        # Process dynamic answer columns
        for col in df.columns:
            if col.startswith(ANSWERS_PREFIX):
                 question_text = col.split(ANSWERS_PREFIX, 1)[1]
                 q_type = question_info.get(question_text)
                 
                 # Generate stats for categorical question types
                 if q_type in ['multiple_choices', 'dropdown', 'user', 'checkbox', 'single_choice']:
                     col_stats = ReportUtils.safe_value_counts(df, col, top_n=10)
                     if col_stats:
                         safe_col_name = question_text.lower().replace(" ", "_").replace("?", "")[:30]
                         stats[f'counts_{safe_col_name}'] = col_stats
                 
                 # Generate stats for date/time question types
                 elif q_type in ['date', 'datetime'] and pd.api.types.is_datetime64_any_dtype(df[col]):
                      valid_dates = df[col].dropna()
                      if not valid_dates.empty:
                          safe_col_name = question_text.lower().replace(" ", "_").replace("?", "")[:30]
                          stats[f'range_{safe_col_name}'] = {
                              'first': valid_dates.min().isoformat(), 
                              'last': valid_dates.max().isoformat()
                          }
        
        # Submitter statistics
        submitter_stats = ReportUtils.safe_value_counts(df, 'submitted_by', top_n=5)
        if submitter_stats:
            stats['submissions_per_user_top5'] = submitter_stats
        
        # Form statistics
        form_stats = ReportUtils.safe_value_counts(df, 'form.title', top_n=5)
        if form_stats:
            stats['submissions_per_form_top5'] = form_stats
        
        # Submission date range and trends
        if 'submitted_at' in df.columns and pd.api.types.is_datetime64_any_dtype(df['submitted_at']):
             valid_dates = df['submitted_at'].dropna()
             if not valid_dates.empty:
                 stats['overall_submission_range'] = {
                     'first': valid_dates.min().isoformat(), 
                     'last': valid_dates.max().isoformat()
                 }
                 
                 # Calculate average daily submissions
                 date_range_days = (valid_dates.max() - valid_dates.min()).days
                 if date_range_days is not None and date_range_days >= 0:
                     stats['average_daily_submissions'] = round(len(df) / max(date_range_days, 1), 1)
                 else:
                     stats['average_daily_submissions'] = len(df)
                     
                 # Count submissions by day of week
                 day_counts = df['submitted_at'].dt.day_name().value_counts()
                 if not day_counts.empty:
                     day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                     ordered_day_counts = {day: int(day_counts.get(day, 0)) for day in day_order}
                     stats['submissions_by_day'] = ordered_day_counts
                     
                 # Count submissions by hour
                 hour_counts = df['submitted_at'].dt.hour.value_counts().sort_index()
                 if not hour_counts.empty:
                     stats['submissions_by_hour'] = {str(hour): int(count) for hour, count in hour_counts.items()}
        
        return stats
        
    @staticmethod
    def generate_user_stats(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate statistics for users
        
        Args:
            df: Pandas DataFrame with user data
            params: Report parameters
            
        Returns:
            Dictionary of statistics
        """
        stats = {}
        
        # User distribution by role
        stats['users_per_role'] = ReportUtils.safe_value_counts(df, 'role.name')
        
        # User distribution by environment
        stats['users_per_environment'] = ReportUtils.safe_value_counts(df, 'environment.name')
        
        # User creation trends
        if 'created_at' in df.columns and pd.api.types.is_datetime64_any_dtype(df['created_at']):
            valid_dates = df['created_at'].dropna()
            if not valid_dates.empty:
                stats['user_creation_range'] = {
                    'first': valid_dates.min().isoformat(),
                    'last': valid_dates.max().isoformat()
                }
                
                # Count users by month/year of creation
                if len(valid_dates) > 5:  # Only if we have enough users
                    try:
                        monthly_counts = df.set_index('created_at').resample('ME').size()
                        stats['users_created_by_month'] = {
                            str(idx.date()): int(count) 
                            for idx, count in monthly_counts.items() 
                            if count > 0
                        }
                    except Exception as e:
                        logger.warning(f"Error generating monthly user creation stats: {e}")
        
        return stats
        
    @staticmethod
    def generate_form_stats(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate statistics for forms
        
        Args:
            df: Pandas DataFrame with form data
            params: Report parameters
            
        Returns:
            Dictionary of statistics
        """
        stats = {}
        
        # Forms per creator
        stats['forms_per_creator_top5'] = ReportUtils.safe_value_counts(df, 'creator.username', top_n=5)
        
        # Forms per environment
        stats['forms_per_environment'] = ReportUtils.safe_value_counts(df, 'creator.environment.name')
        
        # Public vs private forms
        if 'is_public' in df.columns:
            stats['public_vs_private_forms'] = ReportUtils.safe_value_counts(df, 'is_public')
        
        # Form creation trends
        if 'created_at' in df.columns and pd.api.types.is_datetime64_any_dtype(df['created_at']):
            valid_dates = df['created_at'].dropna()
            if not valid_dates.empty:
                stats['form_creation_range'] = {
                    'first': valid_dates.min().isoformat(),
                    'last': valid_dates.max().isoformat()
                }
                
                # Count forms by month/year of creation
                if len(valid_dates) > 5:  # Only if we have enough forms
                    try:
                        monthly_counts = df.set_index('created_at').resample('ME').size()
                        stats['forms_created_by_month'] = {
                            str(idx.date()): int(count) 
                            for idx, count in monthly_counts.items() 
                            if count > 0
                        }
                    except Exception as e:
                        logger.warning(f"Error generating monthly form creation stats: {e}")
        
        return stats

    @staticmethod
    def generate_environment_stats(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate statistics for environments
        
        Args:
            df: Pandas DataFrame with environment data
            params: Report parameters
            
        Returns:
            Dictionary of statistics
        """
        stats = {
            'total_environments_reported': len(df)
        }
        
        # Count environments by creation date ranges
        if 'created_at' in df.columns and pd.api.types.is_datetime64_any_dtype(df['created_at']):
            valid_dates = df['created_at'].dropna()
            if not valid_dates.empty:
                stats['environment_creation_range'] = {
                    'first': valid_dates.min().isoformat(),
                    'last': valid_dates.max().isoformat()
                }
        
        return stats

    @staticmethod
    def generate_role_stats(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate statistics for roles
        
        Args:
            df: Pandas DataFrame with role data
            params: Report parameters
            
        Returns:
            Dictionary of statistics
        """
        stats = {}
        
        # Roles by superuser status
        if 'is_super_user' in df.columns:
            stats['roles_by_superuser_status'] = ReportUtils.safe_value_counts(df, 'is_super_user')
        
        # Count total roles
        stats['total_roles'] = len(df)
        
        return stats

    @staticmethod
    def generate_question_type_stats(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate statistics for question types
        
        Args:
            df: Pandas DataFrame with question type data
            params: Report parameters
            
        Returns:
            Dictionary of statistics
        """
        stats = {}
        
        # Count question types
        stats['question_types_count'] = ReportUtils.safe_value_counts(df, 'type')
        stats['total_question_types'] = len(df)
        
        return stats

    @staticmethod
    def generate_question_stats(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate statistics for questions
        
        Args:
            df: Pandas DataFrame with question data
            params: Report parameters
            
        Returns:
            Dictionary of statistics
        """
        stats = {}
        
        # Questions by type
        stats['questions_by_type'] = ReportUtils.safe_value_counts(df, 'question_type.type')
        
        # Questions by signature status
        if 'is_signature' in df.columns:
            stats['questions_by_signature_status'] = ReportUtils.safe_value_counts(df, 'is_signature')
        
        return stats

    @staticmethod
    def generate_permission_stats(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate statistics for permissions
        
        Args:
            df: Pandas DataFrame with permission data
            params: Report parameters
            
        Returns:
            Dictionary of statistics
        """
        stats = {}
        
        # Permissions by action
        stats['permissions_by_action'] = ReportUtils.safe_value_counts(df, 'action')
        
        # Permissions by entity
        stats['permissions_by_entity'] = ReportUtils.safe_value_counts(df, 'entity')
        
        return stats

    @staticmethod
    def generate_role_permission_stats(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate statistics for role permissions
        
        Args:
            df: Pandas DataFrame with role permission data
            params: Report parameters
            
        Returns:
            Dictionary of statistics
        """
        stats = {}
        
        # Permissions per role
        role_counts = df.groupby('role.name').size()
        stats['permissions_per_role'] = {
            str(role): int(count) for role, count in role_counts.items()
        }
        
        return stats

    @staticmethod
    def generate_form_question_stats(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate statistics for form questions
        
        Args:
            df: Pandas DataFrame with form question data
            params: Report parameters
            
        Returns:
            Dictionary of statistics
        """
        stats = {}
        
        # Questions count by form
        form_question_counts = df.groupby('form.title').size()
        stats['questions_per_form'] = {
            str(form): int(count) for form, count in form_question_counts.items()
        }
        
        # Questions by type
        stats['form_questions_by_type'] = ReportUtils.safe_value_counts(df, 'question.question_type.type')
        
        return stats

    @staticmethod
    def generate_answers_submitted_stats(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate statistics for submitted answers
        
        Args:
            df: Pandas DataFrame with submitted answer data
            params: Report parameters
            
        Returns:
            Dictionary of statistics
        """
        stats = {}
        
        # Answers by question type
        stats['answers_per_question_type'] = ReportUtils.safe_value_counts(df, 'question_type', top_n=10)
        
        # Answers by question text
        stats['answers_per_question_text_top10'] = ReportUtils.safe_value_counts(df, 'question', top_n=10)
        
        # Answers by form
        stats['answers_per_form_top10'] = ReportUtils.safe_value_counts(df, 'form_submission.form.title', top_n=10)
        
        return stats

    @staticmethod
    def generate_attachment_stats(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate statistics for attachments
        
        Args:
            df: Pandas DataFrame with attachment data
            params: Report parameters
            
        Returns:
            Dictionary of statistics
        """
        stats = {}
        
        # Attachments by file type
        stats['attachments_by_type'] = ReportUtils.safe_value_counts(df, 'file_type')
        
        # Attachments by signature status
        if 'is_signature' in df.columns:
            stats['attachments_by_signature_status'] = ReportUtils.safe_value_counts(df, 'is_signature')
        
        # Attachments by author
        stats['attachments_per_author_top5'] = ReportUtils.safe_value_counts(df, 'signature_author', top_n=5)
        
        # Attachments per form
        stats['attachments_per_form_top5'] = ReportUtils.safe_value_counts(df, 'form_submission.form.title', top_n=5)
        
        return stats