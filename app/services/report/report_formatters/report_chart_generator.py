# app/services/report/report_chart_generator.py
from typing import Dict, List, Any, Optional, Tuple
import logging
from io import BytesIO
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib

from app.services.report.report_config import MAX_UNIQUE_GENERIC_CHART
matplotlib.use('Agg')  # Use Agg backend for non-interactive mode


logger = logging.getLogger(__name__)

class ReportChartGenerator:
    """
    Generates charts for reports
    """
    
    @staticmethod
    def _save_plot_to_bytes(figure) -> Optional[BytesIO]:
        """
        Save a matplotlib figure to a BytesIO buffer
        
        Args:
            figure: matplotlib figure object
            
        Returns:
            BytesIO buffer with the saved figure or None on error
        """
        if not figure:
            return None
            
        try:
            img_buffer = BytesIO()
            
            # Try to adjust layout
            try:
                figure.tight_layout(pad=1.1)
            except ValueError:
                logger.warning("Tight layout failed.")
                
            # Save figure to buffer
            figure.savefig(
                img_buffer,
                format='png',
                dpi=150,
                bbox_inches='tight',
                facecolor=figure.get_facecolor()
            )
            
            img_buffer.seek(0)
            plt.close(figure)
            return img_buffer
        except Exception as e:
            logger.error(f"Failed to save plot: {e}")
            return None
        finally:
            plt.close('all')

    @staticmethod
    def _setup_chart(figsize=(10, 5), style='seaborn-v0_8-whitegrid') -> Tuple[plt.Figure, plt.Axes]:
        """
        Set up a matplotlib figure and axes with consistent styling
        
        Args:
            figsize: Tuple of (width, height) for the figure
            style: Matplotlib style to use
            
        Returns:
            Tuple of (figure, axes)
        """
        plt.style.use(style)
        fig, ax = plt.subplots(figsize=figsize, facecolor='white')
        ax.set_facecolor('white')
        
        # Set up consistent font sizes
        plt.rcParams.update({
            'font.size': 10,
            'axes.titlesize': 14,
            'axes.labelsize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 10
        })
        
        return fig, ax

    @staticmethod
    def _add_bar_labels(ax: plt.Axes, bars: Any, location: str = 'edge', color: str = 'black', fontsize=9, **kwargs):
        """
        Add value labels to bars in a bar chart
        
        Args:
            ax: matplotlib Axes object
            bars: Bar container or patches
            location: Label location ('edge' or 'center')
            color: Label color
            fontsize: Font size for labels
            **kwargs: Additional arguments for annotate
        """
        try:
            patches = bars.patches if hasattr(bars, 'patches') else bars
            for bar in patches:
                x_offset = 0
                y_offset = 0
                height = bar.get_height()
                width = bar.get_width()
                
                if height == 0 and width == 0:
                    continue
                    
                if height > 0:
                    y_pos = height if location == 'edge' else height / 2
                    x_pos = bar.get_x() + width / 2
                    va = 'bottom' if location == 'edge' else 'center'
                    ha = 'center'
                    label_text = f'{int(height)}' if height == int(height) else f'{height:.1f}'
                    text_color = color if location != 'edge' else 'black'
                    y_offset = 3 if location == 'edge' else 0
                elif width > 0:
                    x_pos = width if location == 'edge' else width / 2
                    y_pos = bar.get_y() + bar.get_height() / 2
                    ha = 'left' if location == 'edge' else 'center'
                    va = 'center'
                    label_text = f'{int(width)}' if width == int(width) else f'{width:.1f}'
                    text_color = color if location != 'edge' else 'black'
                    x_offset = 3 if location == 'edge' else 0
                else:
                    continue
                    
                ax.annotate(
                    label_text,
                    (x_pos, y_pos),
                    xytext=(x_offset, y_offset),
                    textcoords="offset points",
                    ha=ha,
                    va=va,
                    color=text_color,
                    fontsize=fontsize,
                    fontweight='bold' if location == 'center' else 'normal',
                    **kwargs
                )
        except Exception as e:
            logger.error(f"Error adding bar labels: {e}")

    @staticmethod
    def _create_bar_chart(data: pd.Series, title: str, xlabel: str, ylabel: str, figsize=(8,4), palette="viridis", add_labels=True) -> Optional[BytesIO]:
        """
        Create a bar chart from a pandas Series
        
        Args:
            data: Pandas Series with data to plot
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            figsize: Tuple of (width, height) for the figure
            palette: Color palette to use
            add_labels: Whether to add value labels to bars
            
        Returns:
            BytesIO buffer with the saved chart or None on error
        """
        if data.empty:
            return None
            
        try:
            fig, ax = ReportChartGenerator._setup_chart(figsize=figsize)
            x_data = data.index.astype(str)
            y_data = data.values
            
            bars = sns.barplot(
                x=x_data,
                y=y_data,
                ax=ax,
                hue=x_data,
                palette=palette,
                width=0.6,
                legend=False
            )
            
            if add_labels:
                try:
                    ReportChartGenerator._add_bar_labels(ax, bars.patches, location='edge', fontsize=9)
                except AttributeError:
                    ReportChartGenerator._add_bar_labels(ax, bars, location='edge', fontsize=9)
                    
            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.set_ylabel(ylabel, fontsize=12)
            ax.set_xlabel(xlabel, fontsize=12)
            ax.set_ylim(0, max(y_data.max() * 1.15, 1))
            
            if len(x_data) > 5 or max(len(label) for label in x_data) > 15:
                plt.xticks(rotation=45, ha='right')
            else:
                plt.xticks(rotation=0)
                
            plt.grid(axis='y', linestyle='--', alpha=0.6)
            return ReportChartGenerator._save_plot_to_bytes(fig)
            
        except Exception as e:
            logger.error(f"Error generating bar chart '{title}': {e}", exc_info=True)
            return None
            
        finally:
            plt.close('all')

    @staticmethod
    def _create_pie_chart(data: pd.Series, title: str, figsize=(7, 5)) -> Optional[BytesIO]:
        """
        Create a pie chart from a pandas Series
        
        Args:
            data: Pandas Series with data to plot
            title: Chart title
            figsize: Tuple of (width, height) for the figure
            
        Returns:
            BytesIO buffer with the saved chart or None on error
        """
        if data.empty:
            return None
            
        try:
            fig, ax = ReportChartGenerator._setup_chart(figsize=figsize)
            
            # Add a small explode effect to the smallest slice
            explode = [0.1 if i == data.argmin() else 0 for i in range(len(data))] if len(data) > 3 else None
            
            wedges, texts, autotexts = ax.pie(
                data.values,
                labels=data.index.astype(str),
                autopct='%1.1f%%',
                startangle=90,
                pctdistance=0.85,
                explode=explode,
                colors=sns.color_palette("viridis", len(data)),
                wedgeprops={'edgecolor': 'white', 'linewidth': 1},
                textprops={'fontsize': 9}
            )
            
            # Make percentage labels white and bold
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                
            ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
            ax.axis('equal')
            
            # Use a legend for charts with many slices
            if len(data) > 6:
                plt.legend(
                    wedges,
                    data.index.astype(str),
                    title="Categories",
                    loc="center left",
                    bbox_to_anchor=(1, 0, 0.5, 1)
                )
                [txt.set_visible(False) for txt in texts]
                [autotext.set_visible(False) for autotext in autotexts]
                
            return ReportChartGenerator._save_plot_to_bytes(fig)
            
        except Exception as e:
            logger.error(f"Error generating pie chart '{title}': {e}", exc_info=True)
            return None
            
        finally:
            plt.close('all')

    @staticmethod
    def _create_activity_heatmap(df: pd.DataFrame, date_col: str) -> Optional[BytesIO]:
        """
        Create a heatmap of activity by hour and day of week
        
        Args:
            df: Pandas DataFrame with data
            date_col: Name of the date column to use
            
        Returns:
            BytesIO buffer with the saved chart or None on error
        """
        if df.empty or date_col not in df.columns:
            return None
            
        try:
            # Ensure date column is datetime type and localized
            if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                
            if df[date_col].dt.tz is not None:
                df[date_col] = df[date_col].dt.tz_localize(None)
                
            # Drop rows with missing dates
            df.dropna(subset=[date_col], inplace=True)
            if df.empty:
                return None
                
            # Extract hour and day of week
            df['hour'] = df[date_col].dt.hour
            df['day_of_week'] = df[date_col].dt.day_name()
            
            # Define day order for consistent display
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            # Create the hour/day cross-tabulation
            hour_day = pd.crosstab(
                df['hour'],
                df['day_of_week']
            ).reindex(
                index=range(24),
                columns=day_order,
                fill_value=0
            )
            
            if hour_day.sum().sum() == 0:
                return None
                
            # Create the heatmap
            fig, ax = ReportChartGenerator._setup_chart(figsize=(10, 8))
            heatmap = sns.heatmap(
                hour_day,
                cmap="YlGnBu",
                linewidths=0.5,
                linecolor='lightgrey',
                ax=ax,
                cbar_kws={'label': 'Number of Submissions'},
                annot=True,
                fmt="d",
                annot_kws={'fontsize': 8}
            )
            
            # Format hour labels with AM/PM
            hour_labels = {h: f"{h % 12 if h % 12 != 0 else 12} {'AM' if h < 12 else 'PM'}" for h in range(24)}
            ax.set_yticks(np.arange(len(hour_day.index)) + 0.5)
            ax.set_yticklabels([hour_labels.get(h, '') for h in hour_day.index], rotation=0)
            
            # Set title and labels
            ax.set_title('Submission Activity by Hour and Day', fontsize=14, fontweight='bold')
            ax.set_ylabel('Hour of Day', fontsize=12)
            ax.set_xlabel('Day of Week', fontsize=12)
            plt.xticks(rotation=30, ha='right')
            
            return ReportChartGenerator._save_plot_to_bytes(fig)
            
        except Exception as e:
            logger.error(f"Error creating activity heatmap: {e}", exc_info=True)
            return None
            
        finally:
            plt.close('all')

    @staticmethod
    def _generate_generic_charts(df: pd.DataFrame, analysis: Dict[str, Any]) -> Dict[str, BytesIO]:
        """
        Generate generic charts for any entity type
        
        Args:
            df: Pandas DataFrame with entity data
            analysis: Analysis dictionary with stats
            
        Returns:
            Dictionary of chart names mapped to BytesIO buffers
        """
        charts = {}
        stats = analysis.get('summary_stats', {})
        params = analysis.get('_internal_params', {})
        report_type = params.get("report_type", "entity")
        
        logger.info(f"Generating generic charts for {report_type}")
        
        chart_count = 0 
        MAX_GENERIC_CHARTS = 3 
        
        # Handle explicitly requested charts from parameters
        requested_charts = params.get("charts", [])
        if requested_charts and isinstance(requested_charts, list):
            # Process each requested chart
            for chart_request in requested_charts:
                if chart_count >= MAX_GENERIC_CHARTS:
                    break
                    
                chart_type = chart_request.get("type", "bar")
                chart_column = chart_request.get("column")
                chart_title = chart_request.get("title")
                
                if not chart_column or chart_column not in df.columns:
                    logger.warning(f"Requested chart column '{chart_column}' not found in data")
                    continue
                
                try:
                    unique_values = df[chart_column].nunique()
                    if unique_values <= 1:
                        logger.info(f"Skipping chart for '{chart_column}' - only one unique value")
                        continue
                    
                    # Set default title if not provided
                    if not chart_title:
                        chart_title = f"Distribution of {chart_column.replace('_', ' ').title()}"
                        
                    chart_key = f"requested_{chart_type}_{chart_column}".replace(".", "_")
                    
                    if chart_type == "bar":
                        counts = df[chart_column].value_counts()
                        chart_bytes = ReportChartGenerator._create_bar_chart(
                            counts,
                            chart_title,
                            chart_column.replace("_", " ").title(),
                            "Count",
                            palette="viridis"
                        )
                        if chart_bytes:
                            charts[chart_key] = chart_bytes
                            chart_count += 1
                    
                    elif chart_type == "pie" and unique_values <= 8:
                        counts = df[chart_column].value_counts()
                        chart_bytes = ReportChartGenerator._create_pie_chart(
                            counts,
                            chart_title,
                            figsize=(6, 4)
                        )
                        if chart_bytes:
                            charts[chart_key] = chart_bytes
                            chart_count += 1
                    
                    elif chart_type == "line" and pd.api.types.is_datetime64_any_dtype(df[chart_column].dtype):
                        # Time series chart
                        try:
                            df_ts = df.set_index(chart_column)
                            ts_counts = df_ts.resample('ME').size()
                            
                            if not ts_counts.empty and len(ts_counts) > 1:
                                fig, ax = ReportChartGenerator._setup_chart(figsize=(10, 4))
                                ts_counts.plot(
                                    kind='line',
                                    ax=ax,
                                    marker='o',
                                    color=sns.color_palette("viridis", 1)[0],
                                    linewidth=2
                                )
                                ax.set_title(chart_title, fontsize=14, fontweight='bold')
                                ax.set_ylabel('Count', fontsize=12)
                                ax.set_xlabel('')
                                plt.xticks(rotation=30, ha='right')
                                plt.grid(axis='y', linestyle='--', alpha=0.6)
                                charts[chart_key] = ReportChartGenerator._save_plot_to_bytes(fig)
                                chart_count += 1
                        except Exception as e:
                            logger.error(f"Error generating time series chart for '{chart_column}': {e}")
                    
                except Exception as e:
                    logger.error(f"Error generating requested chart for '{chart_column}': {e}")
                    
        # Generate automatic charts from stats if we haven't hit the limit
        for key, value_counts_dict in stats.items():
            if chart_count >= MAX_GENERIC_CHARTS:
                break
            
            if key.startswith('counts_') and isinstance(value_counts_dict, dict) and value_counts_dict:
                try:
                    counts_series = pd.Series(value_counts_dict)
                    col_name_from_key = key.replace('counts_', '').replace('_', ' ')
                    chart_title = f"Distribution by {col_name_from_key.title()}"
                    chart_key_name = f"generic_dist_{key.replace('counts_','')[:20].replace('.', '_')}"

                    if not counts_series.empty and len(counts_series.index) <= MAX_UNIQUE_GENERIC_CHART:
                        chart_bytes = ReportChartGenerator._create_bar_chart(
                            data=counts_series,
                            title=chart_title,
                            xlabel=col_name_from_key.title(),
                            ylabel='# Records',
                            palette='Spectral',
                            figsize=(8, max(4, len(counts_series.index) * 0.5))
                        )
                        if chart_bytes:
                            charts[chart_key_name] = chart_bytes
                            chart_count += 1
                except Exception as e:
                    logger.error(f"Error generating generic chart for key '{key}' in {report_type}: {e}", exc_info=True)
        
        # Message if no charts were generated but data exists
        if chart_count == 0 and stats.get('record_count', 0) > 0:
            logger.info(f"No generic charts were generated for {report_type} despite having data")
            if 'insights' not in analysis:
                analysis['insights'] = {}
            
            has_suppression_insight = any(k.startswith('suppressed_chart_info_') for k in analysis.get('insights', {}).keys())

            if not has_suppression_insight:
                analysis['insights']['no_generic_charts_note'] = (
                    "No generic distribution charts were generated for this section. "
                    "This can occur if data columns have too many unique values, too few unique values, "
                    "or if other chart generation limits were met."
                )

        logger.debug(f"Generated {len(charts)} generic charts for {report_type}")
        return charts

    @staticmethod
    def generate_submission_charts(df: pd.DataFrame, analysis: Dict[str, Any]) -> Dict[str, BytesIO]:
        """
        Generate charts for form submissions
        
        Args:
            df: Pandas DataFrame with submission data
            analysis: Analysis dictionary with stats
            
        Returns:
            Dictionary of chart names mapped to BytesIO buffers
        """
        charts = {}
        stats = analysis.get('summary_stats', {})
        params = analysis.get('_internal_params', {})
        
        if df.empty:
            return charts
            
        config = analysis.get('_internal_config', {})
        hints = config.get('analysis_hints', {})
        
        # For time series charts, we need a date column
        date_col = next((c for c in hints.get('date_columns', []) if c == 'submitted_at'), None)
        if not date_col or date_col not in df.columns or not pd.api.types.is_datetime64_any_dtype(df[date_col]) or df[date_col].isnull().all():
            logger.warning("Submission charts require valid 'submitted_at'")
        else:
            # Monthly submission trend chart
            try:
                df_ts = df.set_index('submitted_at')
                monthly_counts = df_ts.resample('ME').size()
                
                if not monthly_counts.empty and len(monthly_counts) > 1:
                    fig, ax = ReportChartGenerator._setup_chart(figsize=(10, 4))
                    monthly_counts.plot(
                        kind='line',
                        ax=ax,
                        marker='o',
                        color=sns.color_palette("viridis", 1)[0],
                        linewidth=2
                    )
                    ax.set_title("Submissions Trend (Monthly)", fontsize=14, fontweight='bold')
                    ax.set_ylabel('# Submissions', fontsize=12)
                    ax.set_xlabel('')
                    plt.xticks(rotation=30, ha='right')
                    plt.grid(axis='y', linestyle='--', alpha=0.6)
                    charts['time_series_monthly'] = ReportChartGenerator._save_plot_to_bytes(fig)
            except Exception as e:
                logger.error(f"Error generating monthly time series: {e}")
        
            # Activity heatmap
            try:
                charts['activity_heatmap'] = ReportChartGenerator._create_activity_heatmap(df, date_col=date_col)
            except Exception as e:
                logger.error(f"Error generating activity heatmap: {e}")
        
        # User distribution chart
        try:
            user_dist_stats = stats.get('submissions_per_user_top5')
            if user_dist_stats and isinstance(user_dist_stats, dict):
                user_counts = pd.Series(user_dist_stats)
                if not user_counts.empty:
                    charts['user_distribution'] = ReportChartGenerator._create_bar_chart(
                        user_counts,
                        'Top 5 Users by Submissions',
                        'Username',
                        '# Submissions',
                        figsize=(8, 4),
                        palette='viridis'
                    )
        except Exception as e:
            logger.error(f"Error generating user dist chart: {e}")
        
        # Form distribution chart
        try:
            form_dist_stats = stats.get('submissions_per_form_top5')
            if form_dist_stats and isinstance(form_dist_stats, dict):
                form_counts = pd.Series(form_dist_stats)
                if not form_counts.empty:
                    charts['form_distribution'] = ReportChartGenerator._create_pie_chart(
                        form_counts,
                        'Submissions by Form Type (Top 5)',
                        figsize=(7, 5.5)
                    )
        except Exception as e:
            logger.error(f"Error generating form dist chart: {e}")
        
        # Dynamic charts from stats
        try:
            for key, value_counts in stats.items():
                 if key.startswith('counts_') and isinstance(value_counts, dict):
                      question_text = key.replace('counts_', '').replace('_', ' ').title()
                      counts_series = pd.Series(value_counts)
                      if not counts_series.empty:
                          chart_key = f'dist_{key.replace("counts_","")[:20]}'
                          charts[chart_key] = ReportChartGenerator._create_bar_chart(
                              counts_series,
                              f'Distribution by: {question_text}',
                              'Answer',
                              '# Submissions',
                              figsize=(8, 4),
                              palette='viridis'
                          )
        except Exception as e:
            logger.error(f"Error generating dynamic charts from stats: {e}")
        
        return charts

    @staticmethod
    def generate_user_charts(df: pd.DataFrame, analysis: Dict[str, Any]) -> Dict[str, BytesIO]:
        """
        Generate charts for users
        
        Args:
            df: Pandas DataFrame with user data
            analysis: Analysis dictionary with stats
            
        Returns:
            Dictionary of chart names mapped to BytesIO buffers
        """
        charts = {}
        stats = analysis.get('summary_stats', {})
        
        if df.empty:
            return charts

        # Role distribution chart
        role_counts_data = stats.get('users_per_role')
        if role_counts_data:
            role_counts = pd.Series(role_counts_data)
            if not role_counts.empty:
                try:
                    charts['user_role_distribution'] = ReportChartGenerator._create_bar_chart(
                        role_counts,
                        'User Count by Role',
                        'Role',
                        '# Users',
                        palette='Blues_d'
                    )
                except Exception as e:
                    logger.error(f"Error creating user_role_distribution chart: {e}", exc_info=True)
                    charts['user_role_distribution_error'] = f"Failed to generate: {e}"

        # Environment distribution chart
        env_counts_data = stats.get('users_per_environment')
        if env_counts_data:
            env_counts = pd.Series(env_counts_data)
            if not env_counts.empty:
                try:
                    charts['user_environment_distribution'] = ReportChartGenerator._create_bar_chart(
                        env_counts,
                        'User Count by Environment',
                        'Environment',
                        '# Users',
                        palette='Greens_d'
                    )
                except Exception as e:
                    logger.error(f"Error creating user_environment_distribution chart: {e}", exc_info=True)
                    charts['user_environment_distribution_error'] = f"Failed to generate: {e}"
        
        # User creation trend chart
        if 'created_at' in df.columns and pd.api.types.is_datetime64_any_dtype(df['created_at']):
            try:
                df_ts = df.set_index('created_at')
                monthly_counts = df_ts.resample('ME').size()
                
                if not monthly_counts.empty and len(monthly_counts) > 1:
                    fig, ax = ReportChartGenerator._setup_chart(figsize=(10, 4))
                    monthly_counts.plot(
                        kind='line',
                        ax=ax,
                        marker='o',
                        color=sns.color_palette("Purples", 2)[1],
                        linewidth=2
                    )
                    ax.set_title("User Creation Trend (Monthly)", fontsize=14, fontweight='bold')
                    ax.set_ylabel('# Users Created', fontsize=12)
                    ax.set_xlabel('')
                    plt.xticks(rotation=30, ha='right')
                    plt.grid(axis='y', linestyle='--', alpha=0.6)
                    charts['user_creation_trend'] = ReportChartGenerator._save_plot_to_bytes(fig)
            except Exception as e:
                logger.error(f"Error generating user creation trend chart: {e}")
                
        return charts

    @staticmethod
    def generate_role_charts(df: pd.DataFrame, analysis: Dict[str, Any]) -> Dict[str, BytesIO]:
        """
        Generate charts for roles
        
        Args:
            df: Pandas DataFrame with role data
            analysis: Analysis dictionary with stats
            
        Returns:
            Dictionary of chart names mapped to BytesIO buffers
        """
        charts = {}
        stats = analysis.get('summary_stats', {})
        
        if df.empty:
            return charts
            
        # Superuser status pie chart
        if stats.get('roles_by_superuser_status'):
            superuser_counts = pd.Series(stats['roles_by_superuser_status'])
            if not superuser_counts.empty:
                try:
                    charts['role_superuser_status'] = ReportChartGenerator._create_pie_chart(
                        superuser_counts,
                        'Roles by Superuser Status',
                        figsize=(6, 4)
                    )
                except Exception as e:
                    logger.error(f"Error creating role_superuser_status chart: {e}")
        
        return charts

    @staticmethod
    def generate_form_charts(df: pd.DataFrame, analysis: Dict[str, Any]) -> Dict[str, BytesIO]:
        """
        Generate charts for forms
        
        Args:
            df: Pandas DataFrame with form data
            analysis: Analysis dictionary with stats
            
        Returns:
            Dictionary of chart names mapped to BytesIO buffers
        """
        charts = {}
        stats = analysis.get('summary_stats', {})
        
        if df.empty:
            return charts
            
        # Public vs Private chart
        if stats.get('public_vs_private_forms'):
            status_counts = pd.Series(stats['public_vs_private_forms'])
            if not status_counts.empty:
                charts['form_public_private'] = ReportChartGenerator._create_pie_chart(
                    status_counts,
                    'Forms: Public vs. Private',
                    figsize=(6, 4)
                )
        
        # Top creators chart
        if stats.get('forms_per_creator_top5'):
            creator_counts = pd.Series(stats['forms_per_creator_top5'])
            if not creator_counts.empty:
                charts['forms_per_creator'] = ReportChartGenerator._create_bar_chart(
                    creator_counts,
                    'Top Form Creators',
                    'Creator Username',
                    '# Forms',
                    palette='Oranges_d'
                )
        
        # Form creation trend chart
        if 'created_at' in df.columns and pd.api.types.is_datetime64_any_dtype(df['created_at']):
            try:
                df_ts = df.set_index('created_at')
                monthly_counts = df_ts.resample('ME').size()
                
                if not monthly_counts.empty and len(monthly_counts) > 1:
                    fig, ax = ReportChartGenerator._setup_chart(figsize=(10, 4))
                    monthly_counts.plot(
                        kind='line',
                        ax=ax,
                        marker='o',
                        color=sns.color_palette("OrRd", 3)[1],
                        linewidth=2
                    )
                    ax.set_title("Form Creation Trend (Monthly)", fontsize=14, fontweight='bold')
                    ax.set_ylabel('# Forms Created', fontsize=12)
                    ax.set_xlabel('')
                    plt.xticks(rotation=30, ha='right')
                    plt.grid(axis='y', linestyle='--', alpha=0.6)
                    charts['form_creation_trend'] = ReportChartGenerator._save_plot_to_bytes(fig)
            except Exception as e:
                logger.error(f"Error generating form creation trend chart: {e}")
        
        return charts

    @staticmethod
    def generate_permission_charts(df: pd.DataFrame, analysis: Dict[str, Any]) -> Dict[str, BytesIO]:
        """
        Generate charts for permissions
        
        Args:
            df: Pandas DataFrame with permission data
            analysis: Analysis dictionary with stats
            
        Returns:
            Dictionary of chart names mapped to BytesIO buffers
        """
        charts = {}
        stats = analysis.get('summary_stats', {})
        
        if df.empty:
            return charts
            
        # Permissions by action chart
        if stats.get('permissions_by_action'):
            action_counts = pd.Series(stats['permissions_by_action'])
            if not action_counts.empty:
                try:
                    charts['permissions_by_action'] = ReportChartGenerator._create_pie_chart(
                        action_counts,
                        'Permissions by Action Type',
                        figsize=(6, 4)
                    )
                except Exception as e:
                    logger.error(f"Error creating permissions_by_action chart: {e}")
        
        # Permissions by entity chart
        if stats.get('permissions_by_entity'):
            entity_counts = pd.Series(stats['permissions_by_entity'])
            if not entity_counts.empty:
                try:
                    charts['permissions_by_entity'] = ReportChartGenerator._create_bar_chart(
                        entity_counts,
                        'Permissions by Entity Type',
                        'Entity',
                        '# Permissions',
                        palette='Paired'
                    )
                except Exception as e:
                    logger.error(f"Error creating permissions_by_entity chart: {e}")
        
        return charts

    @staticmethod
    def generate_environment_charts(df: pd.DataFrame, analysis: Dict[str, Any]) -> Dict[str, BytesIO]:
        """
        Generate charts for environments
        
        Args:
            df: Pandas DataFrame with environment data
            analysis: Analysis dictionary with stats
            
        Returns:
            Dictionary of chart names mapped to BytesIO buffers
        """
        charts = {}
        stats = analysis.get('summary_stats', {})
        
        if df.empty:
            return charts
            
        # Environment creation date chart
        if 'created_at' in df.columns and pd.api.types.is_datetime64_any_dtype(df['created_at']):
            try:
                # Sort environments by creation date
                sorted_df = df.sort_values('created_at')
                
                if len(sorted_df) > 0:
                    fig, ax = ReportChartGenerator._setup_chart(figsize=(10, 5))
                    bars = ax.bar(
                        sorted_df['name'].astype(str),
                        range(1, len(sorted_df) + 1),
                        color=sns.color_palette("viridis", len(sorted_df))
                    )
                    
                    # Add creation dates as labels
                    for i, (idx, row) in enumerate(sorted_df.iterrows()):
                        date_str = row['created_at'].strftime('%Y-%m-%d')
                        ax.text(
                            i,
                            0.1,
                            date_str,
                            ha='center',
                            va='bottom',
                            rotation=90,
                            color='darkblue',
                            fontsize=8
                        )
                    
                    ax.set_title("Environments by Creation Order", fontsize=14, fontweight='bold')
                    ax.set_ylabel('Creation Sequence', fontsize=12)
                    ax.set_xlabel('Environment Name', fontsize=12)
                    
                    if len(sorted_df) > 5:
                        plt.xticks(rotation=45, ha='right')
                        
                    charts['environment_creation_sequence'] = ReportChartGenerator._save_plot_to_bytes(fig)
            except Exception as e:
                logger.error(f"Error generating environment creation chart: {e}")
        
        return charts

    @staticmethod
    def generate_answers_submitted_charts(df: pd.DataFrame, analysis: Dict[str, Any]) -> Dict[str, BytesIO]:
        """
        Generate charts for submitted answers
        
        Args:
            df: Pandas DataFrame with submitted answer data
            analysis: Analysis dictionary with stats
            
        Returns:
            Dictionary of chart names mapped to BytesIO buffers
        """
        charts = {}
        stats = analysis.get('summary_stats', {})
        
        if df.empty:
            return charts
            
        # Question types chart
        if stats.get('answers_per_question_type'):
            qtype_counts = pd.Series(stats['answers_per_question_type'])
            if not qtype_counts.empty:
                try:
                    charts['answers_by_question_type'] = ReportChartGenerator._create_pie_chart(
                        qtype_counts,
                        'Answers by Question Type',
                        figsize=(6, 4)
                    )
                except Exception as e:
                    logger.error(f"Error creating answers_by_question_type chart: {e}")
        
        # Questions chart
        if stats.get('answers_per_question_text_top10'):
            question_counts = pd.Series(stats['answers_per_question_text_top10'])
            if not question_counts.empty:
                try:
                    charts['answers_by_question'] = ReportChartGenerator._create_bar_chart(
                        question_counts,
                        'Top 10 Questions by Answer Count',
                        'Question',
                        '# Answers',
                        figsize=(10, 5),
                        palette='plasma'
                    )
                except Exception as e:
                    logger.error(f"Error creating answers_by_question chart: {e}")
        
        # Forms chart
        if stats.get('answers_per_form_top10'):
            form_counts = pd.Series(stats['answers_per_form_top10'])
            if not form_counts.empty:
                try:
                    charts['answers_by_form'] = ReportChartGenerator._create_bar_chart(
                        form_counts,
                        'Top 10 Forms by Answer Count',
                        'Form',
                        '# Answers',
                        figsize=(10, 5),
                        palette='Spectral'
                    )
                except Exception as e:
                    logger.error(f"Error creating answers_by_form chart: {e}")
        
        return charts

    @staticmethod
    def generate_attachment_charts(df: pd.DataFrame, analysis: Dict[str, Any]) -> Dict[str, BytesIO]:
        """
        Generate charts for attachments
        
        Args:
            df: Pandas DataFrame with attachment data
            analysis: Analysis dictionary with stats
            
        Returns:
            Dictionary of chart names mapped to BytesIO buffers
        """
        charts = {}
        stats = analysis.get('summary_stats', {})
        
        if df.empty:
            return charts
            
        # File types chart
        if stats.get('attachments_by_type'):
            filetype_counts = pd.Series(stats['attachments_by_type'])
            if not filetype_counts.empty:
                try:
                    charts['attachments_by_file_type'] = ReportChartGenerator._create_pie_chart(
                        filetype_counts,
                        'Attachments by File Type',
                        figsize=(6, 4)
                    )
                except Exception as e:
                    logger.error(f"Error creating attachments_by_file_type chart: {e}")
        
        # Signature status chart
        if stats.get('attachments_by_signature_status'):
            signature_counts = pd.Series(stats['attachments_by_signature_status'])
            if not signature_counts.empty:
                try:
                    charts['attachments_by_signature'] = ReportChartGenerator._create_pie_chart(
                        signature_counts,
                        'Attachments by Signature Status',
                        figsize=(6, 4)
                    )
                except Exception as e:
                    logger.error(f"Error creating attachments_by_signature chart: {e}")
        
        # Authors chart
        if stats.get('attachments_per_author_top5'):
            author_counts = pd.Series(stats['attachments_per_author_top5'])
            if not author_counts.empty:
                try:
                    charts['attachments_by_author'] = ReportChartGenerator._create_bar_chart(
                        author_counts,
                        'Top 5 Authors by Attachment Count',
                        'Author',
                        '# Attachments',
                        figsize=(8, 4),
                        palette='Greens_d'
                    )
                except Exception as e:
                    logger.error(f"Error creating attachments_by_author chart: {e}")
        
        # Forms chart
        if stats.get('attachments_per_form_top5'):
            form_counts = pd.Series(stats['attachments_per_form_top5'])
            if not form_counts.empty:
                try:
                    charts['attachments_by_form'] = ReportChartGenerator._create_bar_chart(
                        form_counts,
                        'Top 5 Forms by Attachment Count',
                        'Form',
                        '# Attachments',
                        figsize=(8, 4),
                        palette='Blues_d'
                    )
                except Exception as e:
                    logger.error(f"Error creating attachments_by_form chart: {e}")
        
        return charts