# app/services/report/report_analyzer.py
from typing import Dict, List, Any, Optional
import logging
import pandas as pd
from .report_utils import ReportUtils

logger = logging.getLogger(__name__)

class ReportAnalyzer:
    """
    Handles analysis of report data, including statistics, charts, and insights
    """
    
    @staticmethod
    def analyze_data(data: List[Dict[str, Any]], params: Dict[str, Any], report_type: str) -> Dict[str, Any]:
        """
        Analyze data for a report type using stats, chart, and insight generators
        
        Args:
            data: List of data dictionaries
            params: Report parameters
            report_type: Type of report
            
        Returns:
            Analysis dictionary with stats, charts, and insights
        """
        analysis: Dict[str, Any] = {
            "summary_stats": {}, 
            "charts": {}, 
            "insights": {}
        }
        
        if not data:
            analysis['insights']['status'] = "No data available for analysis."
            return analysis
            
        try:
            # Convert to pandas DataFrame for analysis
            df = pd.DataFrame(data)
            
            # Get analysis configuration
            config = params.get('_internal_config', {})
            
            # Basic statistics
            analysis['summary_stats']['record_count'] = len(df)
            
            # Store parameters and config for later use
            analysis['_internal_params'] = params
            analysis['_internal_config'] = config
            
            # Process date columns
            hints = config.get('analysis_hints', {})
            for col in hints.get('date_columns', []):
                if col in df.columns:
                    try:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                    except Exception as date_err:
                        logger.warning(f"Could not parse date column '{col}' for {report_type}: {date_err}")
            
            # Special processing for dynamic answer columns in form submissions
            from .report_config import ANSWERS_PREFIX
            if report_type == 'form_submissions' and ANSWERS_PREFIX in hints.get('dynamic_answer_prefix', ''):
                 question_info_map = params.get('_internal_question_info', {})
                 for col in df.columns:
                     if col.startswith(ANSWERS_PREFIX):
                         question_text = col.split(ANSWERS_PREFIX, 1)[1]
                         q_type = question_info_map.get(question_text)
                         
                         if q_type in ['date', 'datetime']:
                             try:
                                 df[col] = pd.to_datetime(df[col], errors='coerce')
                             except Exception as date_err:
                                 logger.warning(f"Could not parse dynamic date column '{col}': {date_err}")
                         elif q_type in ['integer', 'number']:
                             try:
                                 df[col] = pd.to_numeric(df[col], errors='coerce')
                             except Exception as num_err:
                                 logger.warning(f"Could not parse dynamic numeric column '{col}': {num_err}")
            
            # Store processed DataFrame for generators to use
            analysis['_internal_df'] = df
            
            # Run generators for stats, charts, and insights
            for gen_type in ['stats', 'chart', 'insight']:
                 key = f"{gen_type}_generators"
                 output_key = f"summary_stats" if gen_type == 'stats' else f"{gen_type}s"
                 
                 # Import the appropriate generator class based on gen_type
                 if gen_type == 'stats':
                     from .report_formatters.report_stats_generator import ReportStatsGenerator as Generator
                 elif gen_type == 'chart':
                     from .report_formatters.report_chart_generator import ReportChartGenerator as Generator
                 elif gen_type == 'insight':
                     from .report_formatters.report_insight_generator import ReportInsightGenerator as Generator
                 else:
                     continue  # Skip unknown generator types
                 
                 for func_name in config.get(key, []):
                     if hasattr(Generator, func_name):
                         try:
                             generator_func = getattr(Generator, func_name)
                             
                             if gen_type == 'stats':
                                 args = (df, params)
                             elif gen_type == 'chart':
                                 args = (df, analysis)  # Pass analysis for context
                             elif gen_type == 'insight':
                                 args = (df, analysis, params)
                             else:
                                 args = (df, params)
                                 
                             result = generator_func(*args)
                             if result and isinstance(result, dict):
                                 analysis[output_key].update(result)
                         except Exception as gen_err:
                             logger.error(f"Error executing {gen_type} function '{func_name}': {gen_err}", exc_info=True)
                             analysis[output_key][f'{func_name}_error'] = f"Failed: {gen_err}"
                             
        except Exception as e:
            logger.error(f"Error during data analysis for {report_type}: {e}", exc_info=True)
            analysis['error'] = f"Analysis failed: {e}"
            analysis['insights']['status'] = "Error during data analysis."
            
        # Clean up internal DataFrame before returning
        analysis.pop('_internal_df', None)
        analysis.pop('_internal_params', None)
        analysis.pop('_internal_config', None)
        
        return analysis