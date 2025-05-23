# app/services/report/report_formatters/report_csv_formatter.py
from typing import Dict, Any
from io import BytesIO, StringIO
import logging
import csv
import zipfile
from datetime import datetime, date
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
        # Single entity report
        if len(self.processed_data) == 1:
            report_type = list(self.processed_data.keys())[0]
            result = self.processed_data[report_type]
            
            # Handle errors
            if result.get('error'):
                raise ValueError(f"CSV Error: {result['error']}")
                
            data = result.get('data', [])
            columns = result.get('params', {}).get('columns', [])
            
            if not columns:
                raise ValueError("No columns for CSV.")
                
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
                     new_row[col] = val.isoformat() if isinstance(val, (datetime, date)) else ('' if val is None else str(val))
                 formatted_data.append(new_row)
                 
            writer.writerows(formatted_data)
            output.seek(0)
            
            return BytesIO(output.getvalue().encode('utf-8'))
            
        # Multiple entities - create ZIP file
        else:
            zip_buffer = BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for report_type, result in self.processed_data.items():
                    filename_base = result.get('params', {}).get('sheet_name', report_type)
                    
                    # Handle errors
                    if result.get('error'):
                        zipf.writestr(f"{filename_base}_error.txt", f"Error: {result['error']}")
                        continue
                        
                    data = result.get('data', [])
                    columns = result.get('params', {}).get('columns', [])
                    
                    if not columns:
                        zipf.writestr(f"{filename_base}_error.txt", f"No columns.")
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
                            new_row[col] = val.isoformat() if isinstance(val, (datetime, date)) else ('' if val is None else str(val))
                        formatted_data.append(new_row)
                        
                    writer.writerows(formatted_data)
                    csv_output.seek(0)
                    
                    zipf.writestr(f"{filename_base}.csv", csv_output.getvalue().encode('utf-8'))
                    
            zip_buffer.seek(0)
            return zip_buffer