# app/services/report/report_formatters/report_csv_formatter.py
from typing import Dict, Any
from io import BytesIO, StringIO
import logging
import csv
import zipfile
from datetime import datetime, date
# Ensure the relative import path is correct based on your project structure
from ..report_formatter import ReportFormatter

logger = logging.getLogger(__name__)

class ReportCsvFormatter(ReportFormatter):
    """Formatter for CSV reports"""

    def generate(self) -> BytesIO:
        """
        Generate a CSV report (single file or ZIP of multiple files)

        Returns:
            BytesIO buffer with the CSV report
        """
        actual_report_entities = {
            rt: res for rt, res in self.processed_data.items()
            if not rt.startswith('_') # Skip internal keys like _all_entity_dataframes
        }

        if not actual_report_entities:
            # No actual reportable entities found (could be all errors or empty request)
            logger.warning("No actual reportable entities found for CSV generation.")
            output = StringIO()
            # Create a CSV with a header indicating no data or an error message
            all_errors = self.get_all_errors()
            if all_errors:
                header = ["Error"]
                data_rows = [[all_errors]]
            else:
                header = ["Message"]
                data_rows = [["No data to report."]]

            writer = csv.writer(output)
            writer.writerow(header)
            writer.writerows(data_rows)
            output.seek(0)
            return BytesIO(output.getvalue().encode('utf-8'))

        # Single entity report
        if len(actual_report_entities) == 1:
            report_type = list(actual_report_entities.keys())[0]
            result = actual_report_entities[report_type]

            # Handle errors for the single entity
            if result.get('error'):
                logger.error(f"Error generating CSV for single entity {report_type}: {result['error']}")
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(["Error"])
                writer.writerow([f"Error for {report_type}: {result['error']}"])
                output.seek(0)
                return BytesIO(output.getvalue().encode('utf-8'))

            data = result.get('data', [])
            # Ensure params exist and have columns, provide default if not
            params_data = result.get('params', {})
            columns = params_data.get('columns', []) if isinstance(params_data, dict) else []


            if not columns:
                # This case should ideally be caught earlier, but handle defensively
                logger.warning(f"No columns specified for CSV report: {report_type}")
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(["Error"])
                writer.writerow([f"No columns available for report: {report_type}"])
                output.seek(0)
                return BytesIO(output.getvalue().encode('utf-8'))

            # Create CSV
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=columns, quoting=csv.QUOTE_MINIMAL, extrasaction='ignore')
            writer.writeheader()

            # Format data for CSV
            formatted_data = []
            for row_dict in data:
                 new_row = {}
                 for col in columns:
                     val = row_dict.get(col)
                     # Ensure val is a string before calling isoformat for datetime objects
                     if isinstance(val, (datetime, date)):
                         new_row[col] = val.isoformat()
                     elif val is None:
                         new_row[col] = ''
                     else:
                         new_row[col] = str(val)
                 formatted_data.append(new_row)

            writer.writerows(formatted_data)
            output.seek(0)

            return BytesIO(output.getvalue().encode('utf-8'))

        # Multiple entities - create ZIP file
        else: # This means len(actual_report_entities) > 1
            zip_buffer = BytesIO()

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for report_type, result in actual_report_entities.items(): # Iterate over filtered entities
                    # Ensure params exist and have sheet_name, provide default if not
                    params_data = result.get('params', {})
                    filename_base = params_data.get('sheet_name', report_type) if isinstance(params_data, dict) else report_type


                    # Handle errors
                    if result.get('error'):
                        zipf.writestr(f"{filename_base}_error.txt", f"Error for {report_type}: {result['error']}")
                        continue

                    data = result.get('data', [])
                    # Ensure params exist and have columns, provide default if not for columns as well
                    columns = params_data.get('columns', []) if isinstance(params_data, dict) else []


                    if not columns:
                        zipf.writestr(f"{filename_base}_error.txt", f"No columns for {report_type}.")
                        continue

                    # Create CSV
                    csv_output = StringIO()
                    writer = csv.DictWriter(csv_output, fieldnames=columns, quoting=csv.QUOTE_MINIMAL, extrasaction='ignore')
                    writer.writeheader()

                    # Format data for CSV
                    formatted_data = []
                    for row_dict in data:
                        new_row = {}
                        for col in columns:
                            val = row_dict.get(col)
                            if isinstance(val, (datetime, date)):
                                new_row[col] = val.isoformat()
                            elif val is None:
                                new_row[col] = ''
                            else:
                                new_row[col] = str(val)
                        formatted_data.append(new_row)

                    writer.writerows(formatted_data)
                    csv_output.seek(0)

                    zipf.writestr(f"{filename_base}.csv", csv_output.getvalue().encode('utf-8'))

            zip_buffer.seek(0)
            return zip_buffer