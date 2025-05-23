# app/services/report/report_formatters/cross_entity_chart_generator.py
from typing import Dict, List, Any, Optional, Tuple
import logging
from io import BytesIO
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib
from datetime import datetime, timedelta

# Use non-interactive backend for server environments
matplotlib.use('Agg')

logger = logging.getLogger(__name__)

class CrossEntityChartGenerator:
    """
    Generates charts that compare data across different entities.
    """
    
    @staticmethod
    def _setup_chart(figsize=(10, 6), style='seaborn-v0_8-whitegrid', title=None):
        """
        Set up a matplotlib figure and axes with consistent styling
        
        Args:
            figsize: Tuple of (width, height) for the figure
            style: Matplotlib style to use
            title: Optional chart title
            
        Returns:
            Tuple of (figure, axes)
        """
        plt.style.use(style)
        fig, ax = plt.subplots(figsize=figsize, facecolor='white')
        ax.set_facecolor('white')
        
        # Set up consistent font sizes
        plt.rcParams.update({
            'font.size': 11,
            'axes.titlesize': 14,
            'axes.labelsize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 10
        })
        
        if title:
            ax.set_title(title, fontsize=14, fontweight='bold')
            
        return fig, ax
    
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
                figure.tight_layout(pad=1.2)
            except ValueError:
                logger.warning("Tight layout failed for cross-entity chart.")
                
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
            logger.error(f"Failed to save cross-entity plot: {e}")
            return None
        finally:
            plt.close('all')
    
    @staticmethod
    def generate_comparison_chart(
        entity_dataframes: Dict[str, pd.DataFrame],
        chart_config: Dict[str, Any]
    ) -> Optional[BytesIO]:
        """
        Generate a chart comparing columns from different entities
        
        Args:
            entity_dataframes: Dictionary mapping entity names to their dataframes
            chart_config: Configuration dict with chart parameters
                    
        Returns:
            BytesIO buffer with the chart image or None on error
        """
        try:
            x_entity = chart_config.get('x_entity')
            x_column = chart_config.get('x_column')
            y_entity = chart_config.get('y_entity', x_entity)  # Default to same entity for single-entity charts
            y_column = chart_config.get('y_column')
            chart_type = chart_config.get('chart_type', 'scatter')
            title = chart_config.get('title', f"Comparison of {x_entity}.{x_column} vs {y_entity}.{y_column}")
            alignment = chart_config.get('alignment', 'index')
            
            # Validate inputs
            if not x_entity or not x_column or not y_column:
                logger.error("Missing required parameters for cross-entity chart")
                return CrossEntityChartGenerator._create_error_chart(
                    "Configuration Error",
                    "Missing required chart parameters: entity or column name"
                )
                
            # Check if dataframes exist
            if x_entity not in entity_dataframes:
                logger.error(f"Entity '{x_entity}' not found in available dataframes")
                return CrossEntityChartGenerator._create_error_chart(
                    f"Missing Entity: {x_entity}", 
                    f"The entity '{x_entity}' was not found. Please ensure it's included in the report_type parameter."
                )
                
            if y_entity not in entity_dataframes:
                logger.error(f"Entity '{y_entity}' not found in available dataframes")
                return CrossEntityChartGenerator._create_error_chart(
                    f"Missing Entity: {y_entity}", 
                    f"The entity '{y_entity}' was not found. Please ensure it's included in the report_type parameter."
                )
                
            x_df = entity_dataframes[x_entity]
            y_df = entity_dataframes[y_entity]
            
            # Check if dataframes are empty
            if len(x_df) == 0:
                logger.warning(f"Entity '{x_entity}' contains no data")
                return CrossEntityChartGenerator._create_error_chart(
                    f"No Data for: {x_entity}", 
                    f"The entity '{x_entity}' contains no data records."
                )
                
            if len(y_df) == 0:
                logger.warning(f"Entity '{y_entity}' contains no data")
                return CrossEntityChartGenerator._create_error_chart(
                    f"No Data for: {y_entity}", 
                    f"The entity '{y_entity}' contains no data records."
                )
            
            # Check if columns exist
            if x_column not in x_df.columns:
                logger.error(f"Column '{x_column}' not found in '{x_entity}' dataframe")
                available_cols = list(x_df.columns[:5])
                col_list = ", ".join(available_cols) + "..." if available_cols else "none"
                return CrossEntityChartGenerator._create_error_chart(
                    f"Missing Column: {x_column}", 
                    f"Column '{x_column}' not found in entity '{x_entity}'. Available columns: {col_list}"
                )
                
            if y_column not in y_df.columns:
                logger.error(f"Column '{y_column}' not found in '{y_entity}' dataframe")
                available_cols = list(y_df.columns[:5])
                col_list = ", ".join(available_cols) + "..." if available_cols else "none"
                return CrossEntityChartGenerator._create_error_chart(
                    f"Missing Column: {y_column}", 
                    f"Column '{y_column}' not found in entity '{y_entity}'. Available columns: {col_list}"
                )
            
            # Set up chart
            fig, ax = CrossEntityChartGenerator._setup_chart(figsize=(10, 6), title=title)
            
            # Process the data based on chart type and generate chart
            if chart_type == 'scatter':
                return CrossEntityChartGenerator._generate_scatter_chart(
                    x_df, x_column, y_df, y_column, 
                    title, alignment, fig, ax
                )
            elif chart_type == 'bar':
                return CrossEntityChartGenerator._generate_bar_chart(
                    x_df, x_column, y_df, y_column, 
                    title, alignment, fig, ax
                )
            elif chart_type == 'line':
                return CrossEntityChartGenerator._generate_line_chart(
                    x_df, x_column, y_df, y_column, 
                    title, alignment, fig, ax
                )
            elif chart_type == 'pie':
                return CrossEntityChartGenerator._generate_pie_chart(
                    x_df, x_column, y_df, y_column, 
                    title, alignment, fig, ax
                )
            elif chart_type == 'heatmap':
                return CrossEntityChartGenerator._generate_heatmap_chart(
                    x_df, x_column, y_df, y_column, 
                    title, alignment, fig, ax
                )
            else:
                logger.error(f"Unsupported chart type: {chart_type}")
                plt.close(fig)
                return CrossEntityChartGenerator._create_error_chart(
                    "Unsupported Chart Type",
                    f"Chart type '{chart_type}' is not supported. Use one of: scatter, bar, line, pie, heatmap."
                )
                
        except Exception as e:
            logger.exception(f"Error generating cross-entity chart: {e}")
            plt.close('all')
            return CrossEntityChartGenerator._create_error_chart(
                "Chart Generation Error", 
                f"Error generating chart: {str(e)}"
            )
        
    @staticmethod
    def _create_error_chart(error_title: str, error_message: str) -> Optional[BytesIO]:
        """
        Create a chart showing an error message
        
        Args:
            error_title: Short error title
            error_message: Detailed error message
            
        Returns:
            BytesIO buffer with error chart image
        """
        try:
            fig, ax = plt.subplots(figsize=(10, 6), facecolor='white')
            
            # Clear the axes for a blank canvas
            ax.set_axis_off()
            
            # Add the error title in red
            ax.text(0.5, 0.6, error_title, 
                    horizontalalignment='center',
                    verticalalignment='center',
                    fontsize=16, color='red',
                    transform=ax.transAxes,
                    weight='bold')
            
            # Add the error message with word wrapping
            ax.text(0.5, 0.4, error_message,
                    horizontalalignment='center',
                    verticalalignment='center',
                    fontsize=12, color='black',
                    transform=ax.transAxes,
                    wrap=True,
                    linespacing=1.5)
            
            # Create a buffer for the image
            img_buffer = BytesIO()
            fig.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close(fig)
            
            return img_buffer
        except Exception as e:
            logger.error(f"Error creating error chart: {e}")
            plt.close('all')
            return None

    @staticmethod
    def _generate_scatter_chart(
        x_df: pd.DataFrame, x_column: str,
        y_df: pd.DataFrame, y_column: str,
        title: str, alignment: str,
        fig: plt.Figure, ax: plt.Axes
    ) -> Optional[BytesIO]:
        """
        Generate a scatter chart comparing two columns
        """
        try:
            # For scatter plots, we need to align the data properly
            if alignment == 'time':
                # Time-based alignment (for datetime columns)
                if pd.api.types.is_datetime64_any_dtype(x_df[x_column]) and pd.api.types.is_datetime64_any_dtype(y_df[y_column]):
                    # Resample both series to same frequency and merge
                    x_series = x_df[x_column].sort_values()
                    y_series = y_df[y_column].sort_values()
                    
                    # Create date range covering both series
                    start_date = min(x_series.min(), y_series.min())
                    end_date = max(x_series.max(), y_series.max())
                    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
                    
                    # Count occurrences for each day
                    x_counts = x_series.groupby(x_series.dt.date).count()
                    y_counts = y_series.groupby(y_series.dt.date).count()
                    
                    # Plot with dates on x-axis
                    ax.scatter(x_counts.index, x_counts.values, label=f"{x_column}", alpha=0.7)
                    ax.scatter(y_counts.index, y_counts.values, label=f"{y_column}", alpha=0.7)
                    
                    ax.set_xlabel("Date")
                    ax.set_ylabel("Count")
                    plt.xticks(rotation=45)
                    plt.legend()
                    
                else:
                    logger.warning("Time alignment requested but columns are not datetime type")
                    # Fall back to regular scatter plot
                    ax.scatter(x_df[x_column], y_df[y_column], alpha=0.7)
                    ax.set_xlabel(x_column)
                    ax.set_ylabel(y_column)
                    
            elif alignment == 'category':
                # Category-based alignment
                # Get unique categories that exist in both columns
                x_values = x_df[x_column].value_counts()
                y_values = y_df[y_column].value_counts()
                
                # Find common categories
                common_categories = set(x_values.index).intersection(set(y_values.index))
                
                if common_categories:
                    # Filter to common categories and sort
                    x_filtered = {cat: x_values.get(cat, 0) for cat in common_categories}
                    y_filtered = {cat: y_values.get(cat, 0) for cat in common_categories}
                    
                    # Sort by x values
                    sorted_categories = sorted(common_categories, key=lambda cat: x_filtered[cat], reverse=True)
                    
                    # Create scatter with categories
                    ax.scatter(
                        [x_filtered[cat] for cat in sorted_categories],
                        [y_filtered[cat] for cat in sorted_categories],
                        alpha=0.7
                    )
                    
                    # Add labels for each point
                    for cat in sorted_categories:
                        ax.annotate(
                            str(cat),
                            (x_filtered[cat], y_filtered[cat]),
                            xytext=(5, 5),
                            textcoords='offset points',
                            fontsize=8
                        )
                    
                    ax.set_xlabel(f"{x_column}")
                    ax.set_ylabel(f"{y_column}")
                else:
                    logger.warning("No common categories found for category alignment")
                    # Fall back to regular value counts 
                    ax.scatter(
                        range(len(x_values.index[:10])), 
                        x_values.values[:10],
                        label=f"{x_column}"
                    )
                    ax.scatter(
                        range(len(y_values.index[:10])), 
                        y_values.values[:10],
                        label=f"{y_column}"
                    )
                    ax.set_xlabel("Category Index")
                    ax.set_ylabel("Count")
                    plt.legend()
            else:
                # Default to index alignment (just plot values)
                # Extract values
                x_values = x_df[x_column].dropna()
                y_values = y_df[y_column].dropna()
                
                # Determine if we're comparing distributions or direct relationships
                if len(x_values) != len(y_values):
                    # Different entities or lengths - plot distributions
                    ax.scatter(
                        range(min(10, len(x_values))), 
                        x_values[:10],
                        label=f"{x_column}", 
                        alpha=0.7
                    )
                    ax.scatter(
                        range(min(10, len(y_values))), 
                        y_values[:10],
                        label=f"{y_column}", 
                        alpha=0.7
                    )
                    ax.set_xlabel("Index")
                    ax.set_ylabel("Value")
                    plt.legend()
                else:
                    # Same entity and same length - direct comparison
                    ax.scatter(x_values, y_values, alpha=0.7)
                    ax.set_xlabel(x_column)
                    ax.set_ylabel(y_column)
                    
                    # Add regression line if numeric
                    if pd.api.types.is_numeric_dtype(x_values) and pd.api.types.is_numeric_dtype(y_values):
                        try:
                            from scipy import stats
                            slope, intercept, r_value, p_value, std_err = stats.linregress(x_values, y_values)
                            x_line = np.array([min(x_values), max(x_values)])
                            y_line = slope * x_line + intercept
                            ax.plot(x_line, y_line, 'r-', alpha=0.7)
                            ax.text(
                                0.05, 0.95, 
                                f'R² = {r_value**2:.3f}', 
                                transform=ax.transAxes,
                                verticalalignment='top'
                            )
                        except Exception as err:
                            logger.warning(f"Could not add regression line: {err}")
            
            # Add grid and return
            ax.grid(True, linestyle='--', alpha=0.7)
            return CrossEntityChartGenerator._save_plot_to_bytes(fig)
            
        except Exception as e:
            logger.exception(f"Error generating scatter chart: {e}")
            plt.close(fig)
            return None

    @staticmethod
    def _generate_bar_chart(
        x_df: pd.DataFrame, x_column: str,
        y_df: pd.DataFrame, y_column: str,
        title: str, alignment: str,
        fig: plt.Figure, ax: plt.Axes
    ) -> Optional[BytesIO]:
        """
        Generate a bar chart comparing two columns
        """
        try:
            # For bar charts, most common use case is comparing value frequencies
            x_values = x_df[x_column].value_counts().nlargest(10)
            y_values = y_df[y_column].value_counts().nlargest(10)
            
            if len(x_values) == 0 and len(y_values) == 0:
                logger.warning("No data for bar chart")
                return CrossEntityChartGenerator._create_error_chart(
                    "No Data Available",
                    f"No data available for chart comparing {x_column} with {y_column}."
                )
                
            # Determine max number of categories to display
            max_cats = max(len(x_values), len(y_values))
            if max_cats == 0:
                max_cats = 1  # Ensure at least one category
                
            # Create arrays of the correct length for both datasets
            x_indices = np.arange(max_cats)
            
            # Create equal-length arrays for bar heights, padding with zeros
            x_heights = np.zeros(max_cats)
            y_heights = np.zeros(max_cats)
            
            # Fill available data into arrays
            for i in range(max_cats):
                if i < len(x_values):
                    x_heights[i] = x_values.iloc[i]
                if i < len(y_values):
                    y_heights[i] = y_values.iloc[i]
            
            # Set up bars with equal-sized arrays
            bar_width = 0.35
            bars1 = ax.bar(x_indices - bar_width/2, x_heights, bar_width, 
                        label=f"{x_column}", alpha=0.7)
            bars2 = ax.bar(x_indices + bar_width/2, y_heights, bar_width, 
                        label=f"{y_column}", alpha=0.7)
            
            # Add labels and legend
            ax.set_xlabel("Categories")
            ax.set_ylabel("Count")
            ax.set_xticks(x_indices)
            
            # Handle x-axis labels
            labels = []
            for i in range(max_cats):
                if i < len(x_values.index):
                    labels.append(str(x_values.index[i]))
                elif i < len(y_values.index):
                    labels.append(str(y_values.index[i]))
                else:
                    labels.append(f"Category {i+1}")
            
            ax.set_xticklabels(labels, rotation=45, ha='right')
            ax.legend()
            
            # Add value labels on bars
            for bars in [bars1, bars2]:
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:
                        ax.annotate(
                            f'{int(height)}',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),
                            textcoords="offset points",
                            ha='center', va='bottom',
                            fontsize=8
                        )
            
            # Add grid and return
            ax.grid(True, linestyle='--', alpha=0.7, axis='y')
            return CrossEntityChartGenerator._save_plot_to_bytes(fig)
            
        except Exception as e:
            logger.exception(f"Error generating bar chart: {e}")
            plt.close(fig)
            return CrossEntityChartGenerator._create_error_chart(
                "Chart Generation Error",
                f"Error creating bar chart: {str(e)}"
            )

    @staticmethod
    def _generate_line_chart(
        x_df: pd.DataFrame, x_column: str,
        y_df: pd.DataFrame, y_column: str,
        title: str, alignment: str,
        fig: plt.Figure, ax: plt.Axes
    ) -> Optional[BytesIO]:
        """
        Generate a line chart comparing two columns
        """
        try:
            # For line charts, check if we're dealing with time series
            if pd.api.types.is_datetime64_any_dtype(x_df[x_column]) and pd.api.types.is_datetime64_any_dtype(y_df[y_column]):
                # Time-based alignment for time series
                # Group by month and count
                x_series = x_df[x_column].sort_values()
                y_series = y_df[y_column].sort_values()
                
                # Group by date and count occurrences
                x_counts = x_series.dt.floor('D').value_counts().sort_index()
                y_counts = y_series.dt.floor('D').value_counts().sort_index()
                
                # Create date range covering both series
                start_date = min(x_counts.index.min(), y_counts.index.min())
                end_date = max(x_counts.index.max(), y_counts.index.max())
                date_range = pd.date_range(start=start_date, end=end_date, freq='D')
                
                # Reindex to ensure all dates in range are included
                x_counts_reindexed = x_counts.reindex(date_range, fill_value=0)
                y_counts_reindexed = y_counts.reindex(date_range, fill_value=0)
                
                # Smooth with rolling average for better visualization
                window = min(7, len(x_counts_reindexed))
                if window > 1:
                    x_smooth = x_counts_reindexed.rolling(window=window, min_periods=1).mean()
                    y_smooth = y_counts_reindexed.rolling(window=window, min_periods=1).mean()
                else:
                    x_smooth = x_counts_reindexed
                    y_smooth = y_counts_reindexed
                
                # Plot
                ax.plot(x_smooth.index, x_smooth.values, marker='o', markersize=4, label=f"{x_column}")
                ax.plot(y_smooth.index, y_smooth.values, marker='x', markersize=4, label=f"{y_column}")
                
                # Format dates on x-axis
                plt.xticks(rotation=45)
                ax.set_xlabel("Date")
                ax.set_ylabel("Count")
                
            else:
                # For non-time series, plot value distributions
                x_values = x_df[x_column].value_counts().nlargest(10).sort_index()
                y_values = y_df[y_column].value_counts().nlargest(10).sort_index()
                
                # Plot
                ax.plot(range(len(x_values)), x_values.values, marker='o', label=f"{x_column}")
                ax.plot(range(len(y_values)), y_values.values, marker='x', label=f"{y_column}")
                
                # Set labels
                ax.set_xlabel("Index")
                ax.set_ylabel("Count")
                ax.set_xticks(range(max(len(x_values), len(y_values))))
                
                # Handle x-axis labels
                combined_categories = list(x_values.index) + list(y_values.index)
                unique_categories = []
                for cat in combined_categories:
                    if cat not in unique_categories:
                        unique_categories.append(cat)
                        
                if len(unique_categories) > len(range(max(len(x_values), len(y_values)))):
                    unique_categories = unique_categories[:max(len(x_values), len(y_values))]
                    
                ax.set_xticklabels(unique_categories, rotation=45, ha='right')
            
            # Add legend, grid and return
            ax.legend()
            ax.grid(True, linestyle='--', alpha=0.7)
            return CrossEntityChartGenerator._save_plot_to_bytes(fig)
            
        except Exception as e:
            logger.exception(f"Error generating line chart: {e}")
            plt.close(fig)
            return None

    @staticmethod
    def _generate_pie_chart(
        x_df: pd.DataFrame, x_column: str,
        y_df: pd.DataFrame, y_column: str,
        title: str, alignment: str,
        fig: plt.Figure, ax: plt.Axes
    ) -> Optional[BytesIO]:
        """
        Generate pie charts comparing two columns (side by side)
        """
        try:
            # Close the existing figure since we need a different layout
            plt.close(fig)
            
            # Create a new figure with two subplots side by side
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6), facecolor='white')
            
            # Get value counts
            x_values = x_df[x_column].value_counts().nlargest(8)
            y_values = y_df[y_column].value_counts().nlargest(8)
            
            # First pie chart
            ax1.pie(
                x_values.values,
                labels=x_values.index if len(x_values.index) <= 5 else None,
                autopct='%1.1f%%',
                startangle=90,
                shadow=False,
                wedgeprops={'edgecolor': 'white', 'linewidth': 1},
                textprops={'fontsize': 9}
            )
            ax1.set_title(f"{x_column}", fontsize=12)
            
            # Add legend if needed
            if len(x_values.index) > 5:
                ax1.legend(
                    x_values.index, 
                    loc="center left", 
                    bbox_to_anchor=(0, 0, 0.5, 1),
                    fontsize=8
                )
            
            # Second pie chart
            ax2.pie(
                y_values.values,
                labels=y_values.index if len(y_values.index) <= 5 else None,
                autopct='%1.1f%%',
                startangle=90,
                shadow=False,
                wedgeprops={'edgecolor': 'white', 'linewidth': 1},
                textprops={'fontsize': 9}
            )
            ax2.set_title(f"{y_column}", fontsize=12)
            
            # Add legend if needed
            if len(y_values.index) > 5:
                ax2.legend(
                    y_values.index, 
                    loc="center left", 
                    bbox_to_anchor=(1, 0, 0.5, 1),
                    fontsize=8
                )
            
            # Set equal aspect ratio
            ax1.axis('equal')
            ax2.axis('equal')
            
            # Add main title
            fig.suptitle(title, fontsize=14, fontweight='bold')
            
            # Adjust layout and return
            plt.tight_layout(rect=[0, 0, 1, 0.95])  # Make room for the title
            return CrossEntityChartGenerator._save_plot_to_bytes(fig)
            
        except Exception as e:
            logger.exception(f"Error generating pie chart: {e}")
            plt.close(fig)
            return None

    @staticmethod
    def _generate_heatmap_chart(
        x_df: pd.DataFrame, x_column: str,
        y_df: pd.DataFrame, y_column: str,
        title: str, alignment: str,
        fig: plt.Figure, ax: plt.Axes
    ) -> Optional[BytesIO]:
        """
        Generate a heatmap comparing two columns
        """
        try:
            # Close the existing figure
            plt.close(fig)
            
            # For heatmap, we need categorical data that can be cross-tabulated
            x_values = x_df[x_column].astype(str)
            y_values = y_df[y_column].astype(str)
            
            # Check if we're working with same entity
            if x_df is y_df and len(x_values) == len(y_values):
                # Direct cross-tabulation within same entity
                # Create a new dataframe with both columns
                combined_df = pd.DataFrame({
                    'x_col': x_values,
                    'y_col': y_values
                })
                
                # Create cross-tabulation
                crosstab = pd.crosstab(combined_df['x_col'], combined_df['y_col']).astype(float)
                
                # Limit size for readability
                if crosstab.shape[0] > 12 or crosstab.shape[1] > 12:
                    # Get top categories for both axes
                    top_x = combined_df['x_col'].value_counts().nlargest(10).index
                    top_y = combined_df['y_col'].value_counts().nlargest(10).index
                    crosstab = crosstab.loc[top_x.intersection(crosstab.index), top_y.intersection(crosstab.columns)]
            else:
                # Different entities or lengths - create frequency heatmap
                x_counts = x_values.value_counts().nlargest(10)
                y_counts = y_values.value_counts().nlargest(10)
                
                # Create mock data for heatmap
                index = x_counts.index
                columns = y_counts.index
                
                # Create empty dataframe with float data type
                crosstab = pd.DataFrame(0.0, index=index, columns=columns)
                
                # Calculate normalized frequencies
                x_sum = float(x_counts.sum())
                y_sum = float(y_counts.sum())
                product_sum = x_sum * y_sum
                
                # Fill with values - this is just a visualization of relative frequencies
                if product_sum > 0:  # Avoid division by zero
                    for i, x_cat in enumerate(index):
                        for j, y_cat in enumerate(columns):
                            x_count = float(x_counts[x_cat])
                            y_count = float(y_counts[y_cat])
                            normalized_value = (x_count * y_count) / product_sum
                            crosstab.iloc[i, j] = normalized_value
            
            # Create new figure with appropriate size
            figsize = (
                min(12, max(8, crosstab.shape[1] * 0.8)),
                min(10, max(6, crosstab.shape[0] * 0.6))
            )
            fig, ax = plt.subplots(figsize=figsize, facecolor='white')
            
            # Create heatmap
            sns.heatmap(
                crosstab,
                annot=True,
                fmt=".2f",
                cmap="YlGnBu",
                linewidths=0.5,
                ax=ax
            )
            
            # Set labels
            ax.set_xlabel(y_column)
            ax.set_ylabel(x_column)
            ax.set_title(title, fontsize=14, fontweight='bold')
            
            # Rotate axis labels for readability
            plt.xticks(rotation=45, ha='right')
            plt.yticks(rotation=0)
            
            # Adjust layout and return
            plt.tight_layout()
            return CrossEntityChartGenerator._save_plot_to_bytes(fig)
            
        except Exception as e:
            logger.exception(f"Error generating heatmap chart: {e}")
            plt.close('all')
            return CrossEntityChartGenerator._create_error_chart(
                "Chart Generation Error",
                f"Error creating heatmap chart: {str(e)}"
            )