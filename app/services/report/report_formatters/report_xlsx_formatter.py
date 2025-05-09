# app/services/report/report_formatters/report_xlsx_formatter.py
from typing import Dict, Any, List, Set
from io import BytesIO
import logging
from datetime import datetime, date
import xlsxwriter
from ..report_formatter import ReportFormatter
from ..report_config import MAX_XLSX_SHEET_NAME_LEN

logger = logging.getLogger(__name__)

class ReportXlsxFormatter(ReportFormatter):
    """Formatter for Excel (XLSX) reports"""
    
    def generate(self) -> BytesIO:
        """
        Generate an Excel report with multiple sheets
        
        Returns:
            BytesIO buffer with the Excel report
        """
        output = BytesIO()
        
        with xlsxwriter.Workbook(output, {
            'in_memory': True,
            'remove_timezone': True,
            'strings_to_numbers': False,
            'strings_to_formulas': False
        }) as workbook:
            # Define common formats
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1,
                'align': 'center'
            })
            wrap_format = workbook.add_format({
                'text_wrap': True,
                'valign': 'top',
                'align': 'left'
            })

            # Process each report type
            for report_type, result in self.processed_data.items():
                # Handle errors
                if result.get('error'):
                    try:
                        sheet_name = f"ERROR_{report_type}"[:MAX_XLSX_SHEET_NAME_LEN]
                        worksheet = workbook.add_worksheet(sheet_name)
                        worksheet.write(0, 0, f"Error: {report_type}:")
                        worksheet.write(1, 0, str(result['error']))
                        worksheet.set_column(0, 0, 100, wrap_format)
                    except Exception as sheet_err:
                        logger.error(f"Could not write error sheet for {report_type}: {sheet_err}")
                    continue

                # Get data and parameters
                params = result.get('params', {})
                data = result.get('data', [])
                columns = params.get('columns', [])
                analysis = result.get('analysis', {})
                sheet_name = params.get("sheet_name", report_type.replace("_", " ").title())[:MAX_XLSX_SHEET_NAME_LEN]
                table_options = params.get('table_options', {})

                # Sort data by ID if present
                if data and columns and 'id' in columns:
                    try:
                        # Attempt numeric sort first
                        data.sort(key=lambda row: int(row['id']) if isinstance(row.get('id'), (int, float)) or (isinstance(row.get('id'), str) and row.get('id', '').isdigit()) else float('inf'))
                        logger.debug(f"Sorted data for sheet '{sheet_name}' by ID ascending.")
                    except (ValueError, TypeError) as sort_err:
                         logger.warning(f"Could not sort sheet '{sheet_name}' numerically by ID, attempting string sort: {sort_err}")
                         try:
                             # Fallback to string sort
                             data.sort(key=lambda row: str(row.get('id', '')))
                         except Exception as sort_err_str:
                             logger.error(f"String sort by ID also failed for sheet '{sheet_name}': {sort_err_str}")
                    except Exception as sort_err:
                        logger.error(f"Error sorting data for sheet '{sheet_name}' by ID: {sort_err}", exc_info=True)

                # Skip if no columns
                if not columns:
                    logger.warning(f"Skipping sheet {report_type}: No columns.")
                    continue

                try:
                    # Create worksheet and add title
                    worksheet = workbook.add_worksheet(sheet_name)
                    current_row = 0
                    
                    # Add report title
                    worksheet.merge_range(
                        current_row, 0,
                        current_row, max(3, len(columns)-1),
                        f"Report: {sheet_name}",
                        workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
                    )
                    current_row += 1
                    
                    # Add generation timestamp
                    worksheet.merge_range(
                        current_row, 0,
                        current_row, max(3, len(columns)-1),
                        f"Generated: {self.generation_timestamp}",
                        workbook.add_format({'italic': True, 'align': 'center'})
                    )
                    current_row += 2

                    # Prepare table data
                    table_data = []
                    col_max_lens = {i: len(str(columns[i])) for i in range(len(columns))}
                    
                    for row_dict in data:
                        row_values = []
                        for c_idx, col_key in enumerate(columns):
                            cell_value = row_dict.get(col_key)
                            
                            # Format cell value
                            if cell_value is None:
                                formatted_value = ''
                            elif isinstance(cell_value, bool):
                                formatted_value = "Yes" if cell_value else "No"
                            elif isinstance(cell_value, (datetime, date)):
                                try:
                                    formatted_value = cell_value
                                    col_max_lens[c_idx] = max(col_max_lens.get(c_idx, 0), 20)  # Fixed width for dates
                                except ValueError:
                                    formatted_value = str(cell_value.isoformat())
                                    col_max_lens[c_idx] = max(col_max_lens.get(c_idx, 0), len(formatted_value))
                            else:
                                formatted_value = str(cell_value)
                                col_max_lens[c_idx] = max(col_max_lens.get(c_idx, 0), len(formatted_value))
                                
                            row_values.append(formatted_value)
                            
                        table_data.append(row_values)

                    # Create table headers
                    table_headers = [{'header': col.replace(".", " ").replace("_", " ").title()} for col in columns]
                    first_row_table = current_row
                    first_col_table = 0

                    # Handle empty data or columns
                    if not data and not columns:
                        worksheet.write(first_row_table, 0, "No data or columns.")
                        current_row += 1
                    elif not data:
                        for col_idx, header_info in enumerate(table_headers):
                            worksheet.write(first_row_table, col_idx, header_info['header'], header_format)
                        current_row += 1
                    else:
                        # Add table with data
                        last_row_table = first_row_table + len(table_data)
                        last_col_table = first_col_table + len(columns) - 1
                        
                        worksheet.add_table(
                            first_row_table, first_col_table,
                            last_row_table, last_col_table,
                            {
                                'data': table_data,
                                'columns': table_headers,
                                'style': table_options.get('style', 'Table Style Medium 9'),
                                'name': f"{sheet_name.replace(' ','_')}_Table",
                                'header_row': True,
                                'banded_rows': table_options.get('banded_rows', True),
                                'autofilter': table_options.get('autofilter', True)
                            }
                        )
                        current_row = last_row_table + 1

                    # Set column widths
                    for col_idx, max_len in col_max_lens.items():
                        width = min(max(max_len, 10) + 2, 60)
                        worksheet.set_column(col_idx, col_idx, width, wrap_format)

                    # Add charts
                    chart_start_row = current_row + 2
                    chart_col = 1
                    
                    for chart_name, chart_bytes in analysis.get('charts', {}).items():
                        if isinstance(chart_bytes, BytesIO):
                            try:
                                chart_bytes.seek(0)
                                worksheet.write(chart_start_row, chart_col - 1, f"{chart_name.replace('_',' ').title()}:")
                                worksheet.insert_image(
                                    chart_start_row + 1, chart_col,
                                    f"chart_{chart_name}.png",
                                    {'image_data': chart_bytes, 'x_scale': 0.6, 'y_scale': 0.6}
                                )
                                chart_start_row += 20
                            except Exception as chart_err:
                                logger.error(f"Failed chart insert {chart_name}: {chart_err}")
                                worksheet.write(chart_start_row, chart_col - 1, f"Error chart: {chart_name}")
                                chart_start_row += 1
                                
                except Exception as sheet_err:
                    logger.error(f"Failed sheet '{sheet_name}': {sheet_err}", exc_info=True)
                    
                    # Create error sheet
                    try:
                        error_sheet_name = f"ERROR_{sheet_name[:25]}"
                        if error_sheet_name not in workbook.sheetnames:
                            error_worksheet = workbook.add_worksheet(error_sheet_name)
                            error_worksheet.write(0, 0, f"Failed generating original sheet '{sheet_name}'. Error:")
                            error_msg_str = str(sheet_err)
                            max_cell_len = 32767
                            error_worksheet.write(1, 0, error_msg_str[:max_cell_len])
                            error_worksheet.set_column(0, 0, 100)
                            logger.info(f"Created error sheet '{error_sheet_name}' due to failure on '{sheet_name}'.")
                        else:
                            logger.warning(f"Attempted to create error sheet '{error_sheet_name}', but it already exists.")
                    except Exception as inner_err:
                        logger.error(f"Could not write error sheet '{error_sheet_name}' after initial failure on '{sheet_name}': {inner_err}", exc_info=True)
                        
        output.seek(0)
        return output