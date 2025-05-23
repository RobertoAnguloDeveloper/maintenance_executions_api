# app/services/report/answer_formatters/table_formatter.py
from typing import List, Dict
from reportlab.platypus import Flowable, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.units import inch
from .base_answer_formatter import BaseAnswerFormatter
import json
import logging

logger = logging.getLogger(__name__)

class TableAnswerFormatter(BaseAnswerFormatter):
    """Formatter for table question types"""
    
    def format(self, answer_text: str, styles: Dict) -> List[Flowable]:
        """Format table answer text into ReportLab flowables"""
        flowables = []
        
        if not answer_text or answer_text.strip() == "":
            return [Paragraph("No table data provided", styles['Answer'])]
        
        try:
            # Try to parse as JSON first
            try:
                table_data = json.loads(answer_text)
                
                # If it's a list of lists or list of dicts (common formats)
                if isinstance(table_data, list):
                    # Handle list of dictionaries (convert to list of lists with headers)
                    if table_data and isinstance(table_data[0], dict):
                        # Extract headers from the first dict
                        headers = list(table_data[0].keys())
                        
                        # Build table data with headers
                        rows = [headers]  # First row is headers
                        for item in table_data:
                            rows.append([str(item.get(header, "")) for header in headers])
                    
                    # Handle list of lists
                    elif table_data and isinstance(table_data[0], list):
                        rows = [[str(cell) for cell in row] for row in table_data]
                        
                    else:
                        # Fallback
                        rows = [["Data could not be formatted as a table"]]
                        
                    # Create column widths - auto sizing
                    col_count = len(rows[0]) if rows else 1
                    available_width = 6.5 * inch  # Approximate available width on the page
                    col_width = available_width / col_count
                    
                    # Create the table
                    pdf_table = Table(rows, colWidths=[col_width] * col_count)
                    
                    # Style the table
                    style = TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ])
                    pdf_table.setStyle(style)
                    
                    flowables.append(pdf_table)
                    flowables.append(Spacer(1, 5))
                else:
                    # Not a recognized format, display as text
                    flowables.append(Paragraph(answer_text, styles['Answer']))
                    
            except json.JSONDecodeError:
                # Not valid JSON, try parsing as CSV or display as is
                if "~" in answer_text or "," in answer_text:
                    # Try to parse as CSV-like format (using ~ or , as separators)
                    separator = "~" if "~" in answer_text else ","
                    
                    rows = []
                    for line in answer_text.strip().split("\n"):
                        rows.append([cell.strip() for cell in line.split(separator)])
                    
                    # Create the table with auto-sized columns
                    col_count = max([len(row) for row in rows]) if rows else 1
                    available_width = 6.5 * inch
                    col_width = available_width / col_count
                    
                    pdf_table = Table(rows, colWidths=[col_width] * col_count)
                    
                    # Style the table
                    style = TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ])
                    pdf_table.setStyle(style)
                    
                    flowables.append(pdf_table)
                    flowables.append(Spacer(1, 5))
                else:
                    # Display as regular text
                    flowables.append(Paragraph(answer_text, styles['Answer']))
        
        except Exception as e:
            logger.error(f"Error formatting table answer: {str(e)}")
            flowables.append(Paragraph(f"Table data could not be formatted: {answer_text}", styles['Answer']))
        
        return flowables