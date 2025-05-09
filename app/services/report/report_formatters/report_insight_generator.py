# app/services/report/report_insight_generator.py
from typing import Dict, List, Any
import logging
import pandas as pd

logger = logging.getLogger(__name__)

class ReportInsightGenerator:
    """
    Generates insights for reports based on data and statistics
    """
    
    @staticmethod
    def _generate_generic_insights(df: pd.DataFrame, analysis: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate generic insights for any entity type
        
        Args:
            df: Pandas DataFrame with entity data
            analysis: Analysis dictionary with stats and charts
            params: Report parameters
            
        Returns:
            Dictionary of insights
        """
        insights = {}
        stats = analysis.get('summary_stats', {})
        report_type = params.get("report_type", "this entity")
        record_count = stats.get('record_count', 0)

        if record_count == 0:
            # If 'status' isn't already set by a more specific insight generator
            if 'status' not in analysis.get('insights', {}):
                 insights["status"] = f"No data available for {report_type}."
            return insights

        # Avoid duplicating record count if a specific insight generator already added it
        # This relies on convention that specific insights might use keys like 'user_count', 'form_count', etc.
        existing_insights = analysis.get('insights', {})
        if not any(k in existing_insights for k in ['user_count', 'form_count', 'submission_count', 'record_summary', 'volume']):
            insights["record_summary"] = f"A total of {record_count} records were analyzed for {report_type}."
        
        # Date range insight
        date_range_key = next((k for k in stats if k.startswith('range_')), None)
        if date_range_key and isinstance(stats[date_range_key], dict):
            first = stats[date_range_key].get('first', 'N/A')
            last = stats[date_range_key].get('last', 'N/A')
            date_col_name = date_range_key.replace('range_', '').replace('_', ' ')
            
            if first == last:
                insights["date_info"] = f"All analyzed records share the same timestamp for '{date_col_name}': {first.split('T')[0]}."
            else:
                insights["date_range"] = f"Records for '{date_col_name}' span from {first.split('T')[0]} to {last.split('T')[0]}."

        # Top category insight
        count_keys = [k for k in stats if k.startswith('counts_')]
        if count_keys:
            # Sort keys to get a more consistent "primary" count key if multiple exist
            sorted_count_keys = sorted(count_keys, key=lambda k: (
                0 if 'name' in k or 'title' in k or 'type' in k else 1,  # Prioritize common categorical names
                len(stats.get(k, {})),  # Then by number of categories in the stat (fewer is often more focused)
                k  # Alphabetical as tie-breaker
            ))
            primary_count_key = sorted_count_keys[0]
            
            if stats.get(primary_count_key): 
                counts_for_top_key = stats[primary_count_key]
                col_name = primary_count_key.replace('counts_', '').replace('_', ' ')
                if counts_for_top_key:
                    top_value = next(iter(counts_for_top_key), 'N/A')
                    top_count = counts_for_top_key.get(top_value, 0)
                    
                    is_dominant = True
                    if len(counts_for_top_key) > 1:
                        # Convert values to list for sorting if it's a dict
                        all_counts_in_stat = list(counts_for_top_key.values())
                        all_counts_in_stat.sort(reverse=True)
                        second_value_count = all_counts_in_stat[1]
                        if top_count <= second_value_count or top_count <= 1:
                            is_dominant = False
                    elif top_count <= 1 and len(counts_for_top_key) == 1:  # Only one category and its count is 1
                         is_dominant = False

                    if is_dominant:
                        insights["top_category_info"] = f"For the column '{col_name}', the most common value was '{top_value}', occurring {top_count} times."
                    elif top_count > 0: 
                        insights["category_analysis_note"] = f"Distribution analysis was performed for '{col_name}'. The most frequent value found was '{top_value}' (occurrences: {top_count})."
        
        return insights
        
    @staticmethod
    def generate_submission_insights(df: pd.DataFrame, analysis: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate insights for form submissions
        
        Args:
            df: Pandas DataFrame with submission data
            analysis: Analysis dictionary with stats and charts
            params: Report parameters
            
        Returns:
            Dictionary of insights
        """
        insights = {}
        stats = analysis.get('summary_stats', {})
        record_count = stats.get('record_count', 0)
        
        if record_count == 0:
            return {"status": "No submission data available for analysis."}
        
        insights["volume"] = f"Analyzed {record_count} total submissions."
        
        if stats.get('overall_submission_range'):
            first = stats['overall_submission_range']['first'].split(' ')[0]
            last = stats['overall_submission_range']['last'].split(' ')[0]
            insights["date_range"] = f"Data spans from {first} to {last}."
        
        if stats.get('average_daily_submissions'):
            insights["activity_rate"] = f"Average daily submission rate: {stats['average_daily_submissions']:.1f}."
        
        if stats.get('submissions_per_user_top5'):
            top_user = next(iter(stats['submissions_per_user_top5']), 'N/A')
            insights["top_user"] = f"The most active user was '{top_user}'."
        
        if stats.get('submissions_per_form_top5'):
            top_form = next(iter(stats['submissions_per_form_top5']), 'N/A')
            insights["top_form"] = f"The most used form was '{top_form}'."
        
        # Look for department insights
        dept_stats_key = next((k for k in stats if k.startswith('counts_') and 'department' in k), None)
        if dept_stats_key and stats[dept_stats_key]:
            top_dept = next(iter(stats[dept_stats_key]), 'N/A')
            insights["top_department"] = f"'{top_dept}' submitted the most forms."
        
        return insights

    @staticmethod
    def generate_user_insights(df: pd.DataFrame, analysis: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate insights for users
        
        Args:
            df: Pandas DataFrame with user data
            analysis: Analysis dictionary with stats and charts
            params: Report parameters
            
        Returns:
            Dictionary of insights
        """
        insights = {}
        stats = analysis.get('summary_stats', {})
        record_count = stats.get('record_count', 0)
        
        if record_count == 0:
            return {"status": "No user data available for analysis."}
        
        insights["user_count"] = f"Analyzed {record_count} user records."
        
        if stats.get('users_per_role'):
            insights["role_distribution"] = f"Users are distributed across {len(stats['users_per_role'])} different roles."
            
            # Identify dominant role if any
            top_role = None
            top_count = 0
            for role, count in stats['users_per_role'].items():
                if count > top_count:
                    top_count = count
                    top_role = role
            
            if top_role and top_count > (record_count / 3):  # If role has more than 1/3 of users
                percentage = int((top_count / record_count) * 100)
                insights["dominant_role"] = f"The '{top_role}' role accounts for {percentage}% of all users."
        
        if stats.get('users_per_environment'):
            env_count = len(stats['users_per_environment'])
            insights["env_distribution"] = f"Users belong to {env_count} environment{'' if env_count == 1 else 's'}."
            
            # Identify environment with most users
            top_env = None
            top_env_count = 0
            for env, count in stats['users_per_environment'].items():
                if count > top_env_count:
                    top_env_count = count
                    top_env = env
            
            if top_env:
                percentage = int((top_env_count / record_count) * 100)
                insights["primary_environment"] = f"Environment '{top_env}' contains {percentage}% of all users."
        
        if stats.get('user_creation_range'):
            first_date = stats['user_creation_range']['first'].split('T')[0]
            last_date = stats['user_creation_range']['last'].split('T')[0]
            
            if first_date != last_date:
                insights["creation_period"] = f"Users were created between {first_date} and {last_date}."
            else:
                insights["creation_period"] = f"All users were created on {first_date}."
        
        return insights

    @staticmethod
    def generate_form_insights(df: pd.DataFrame, analysis: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate insights for forms
        
        Args:
            df: Pandas DataFrame with form data
            analysis: Analysis dictionary with stats and charts
            params: Report parameters
            
        Returns:
            Dictionary of insights
        """
        insights = {}
        stats = analysis.get('summary_stats', {})
        record_count = stats.get('record_count', 0)
        
        if record_count == 0:
            return {"status": "No form data available for analysis."}
        
        insights["form_count"] = f"Analyzed {record_count} form records."
        
        if stats.get('public_vs_private_forms'):
            public = stats['public_vs_private_forms'].get('Yes', 0)
            private = stats['public_vs_private_forms'].get('No', 0)
            insights["public_status"] = f"{public} public and {private} private forms found."
            
            # Calculate percentage
            if record_count > 0:
                public_percentage = int((public / record_count) * 100)
                insights["visibility_ratio"] = f"{public_percentage}% of forms are publicly accessible."
        
        if stats.get('forms_per_creator_top5'):
            top_creator = next(iter(stats['forms_per_creator_top5']), 'N/A')
            insights["creator_activity"] = f"The most active form creator is '{top_creator}'."
        
        if stats.get('forms_per_environment'):
            top_env = next(iter(stats['forms_per_environment']), 'N/A')
            insights["environment_distribution"] = f"Most forms belong to the '{top_env}' environment."
        
        return insights

    @staticmethod
    def generate_role_insights(df: pd.DataFrame, analysis: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate insights for roles
        
        Args:
            df: Pandas DataFrame with role data
            analysis: Analysis dictionary with stats and charts
            params: Report parameters
            
        Returns:
            Dictionary of insights
        """
        insights = {}
        stats = analysis.get('summary_stats', {})
        record_count = stats.get('record_count', 0)
        
        if record_count == 0:
            return {"status": "No role data available for analysis."}
        
        insights["role_count"] = f"Analyzed {record_count} role records."
        
        if stats.get('roles_by_superuser_status'):
            superuser_count = stats['roles_by_superuser_status'].get('Yes', 0)
            regular_count = stats['roles_by_superuser_status'].get('No', 0)
            
            insights["superuser_ratio"] = f"Found {superuser_count} superuser role(s) and {regular_count} regular role(s)."
            
            if superuser_count > 1:
                insights["superuser_warning"] = f"Having multiple superuser roles ({superuser_count}) may pose a security risk. Consider consolidating privileges."
        
        return insights