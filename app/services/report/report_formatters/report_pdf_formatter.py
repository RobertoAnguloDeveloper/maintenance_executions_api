# app/services/report/report_formatters/report_pdf_formatter.py
from typing import Dict, Any, List, Optional
from io import BytesIO
import logging
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors

from ..report_formatter import ReportFormatter

logger = logging.getLogger(__name__)

class ReportPdfFormatter(ReportFormatter):
    """Formatter for PDF reports"""
    
    def generate(self) -> BytesIO:
        """
        Generate a PDF report
        
        Returns:
            BytesIO buffer with the PDF report
        """
        buffer = BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        styles = getSampleStyleSheet()
        story = []
        
        # Add report title
        title_style = ParagraphStyle(
            name='TitleStyle',
            parent=styles['Title'],
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=0.3*inch
        )
        story.append(Paragraph(self.report_title, title_style))
        
        # Add generation timestamp
        gen_time_style = ParagraphStyle(
            name='GenTimeStyle',
            parent=styles['Italic'],
            fontSize=10,
            alignment=TA_CENTER,
            spaceAfter=0.3*inch
        )
        story.append(Paragraph(f"Generated: {self.generation_timestamp}", gen_time_style))
        
        # Process each report type
        first_section = True
        for report_type, result in self.processed_data.items():
            # Skip internal data
            if report_type.startswith('_'):
                continue
                
            # Handle errors
            if result.get('error'):
                story.append(Paragraph(f"Error: {report_type}:", styles['Heading2']))
                story.append(Paragraph(str(result['error']), styles['Italic']))
                story.append(Spacer(1, 0.2*inch))
                continue
                
            analysis = result.get('analysis', {})
            params = result.get('params', {})
            section_title = params.get("sheet_name", report_type.replace("_", " ").title())
            
            # Add page break between sections
            if not first_section:
                story.append(PageBreak())
            first_section = False
            
            # Add section title
            story.append(Paragraph(section_title, styles['Heading1']))
            story.append(Spacer(1, 0.1*inch))
            
            # Add insights
            if analysis.get('insights'):
                story.append(Paragraph("Key Insights:", styles['Heading2']))
                
                for key, insight_text in analysis['insights'].items():
                    if key != 'status':
                        bullet_style = ParagraphStyle(
                            name='BulletStyle',
                            parent=styles['Normal'],
                            leftIndent=20,
                            firstLineIndent=-20,
                            spaceBefore=5
                        )
                        story.append(Paragraph(f"• {insight_text}", bullet_style))
                        
                story.append(Spacer(1, 0.2*inch))
                
            # Add stats
            if analysis.get('summary_stats'):
                story.append(Paragraph("Summary Statistics:", styles['Heading2']))
                
                # Filter out complex stats and internal data
                simple_stats = {
                    k: v for k, v in analysis['summary_stats'].items()
                    if not k.startswith('_') and 
                    not isinstance(v, (dict, list)) and
                    v is not None
                }
                
                if simple_stats:
                    for key, value in simple_stats.items():
                        formatted_key = key.replace('_', ' ').title()
                        story.append(Paragraph(f"<b>{formatted_key}:</b> {value}", styles['Normal']))
                        
                story.append(Spacer(1, 0.2*inch))
                
            # Add data table (sample)
            data = result.get('data', [])
            columns = params.get('columns', [])
            
            if data and columns:
                story.append(Paragraph("Data Sample:", styles['Heading2']))
                
                # Limit rows for sample
                max_rows = min(10, len(data))
                sample_data = data[:max_rows]
                
                # Create header row
                header_row = [col.replace('.', ' ').replace('_', ' ').title() for col in columns]
                
                # Create data rows
                table_data = [header_row]
                for row_dict in sample_data:
                    row_values = []
                    for col in columns:
                        val = row_dict.get(col)
                        if isinstance(val, bool):
                            val = "Yes" if val else "No"
                        elif val is None:
                            val = ""
                        row_values.append(str(val))
                    table_data.append(row_values)
                
                # Create table with styling
                table_style = [
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.beige, colors.white])
                ]
                
                # Create table with automatic width and row height calculations
                col_widths = [1.5*inch] * len(columns)
                if len(columns) > 4:
                    col_widths = [None] * len(columns)  # Auto-width for many columns
                    
                table = Table(table_data, colWidths=col_widths, repeatRows=1)
                table.setStyle(TableStyle(table_style))
                
                # Add table to story
                story.append(table)
                
                # Add note about sample data
                if len(data) > max_rows:
                    note_style = ParagraphStyle(
                        name='NoteStyle',
                        parent=styles['Italic'],
                        fontSize=8,
                        alignment=TA_LEFT,
                        spaceBefore=10
                    )
                    story.append(Paragraph(f"Note: Showing {max_rows} of {len(data)} records.", note_style))
                    
                story.append(Spacer(1, 0.3*inch))
                
            # Add charts
            if analysis.get('charts'):
                story.append(Paragraph("Visual Analysis:", styles['Heading2']))
                
                for chart_key, chart_bytes in analysis['charts'].items():
                    if isinstance(chart_bytes, BytesIO):
                        try:
                            chart_bytes.seek(0)
                            chart_title = chart_key.replace('_', ' ').title()
                            
                            # Add chart title
                            caption_style = ParagraphStyle(
                                name='CaptionStyle',
                                parent=styles['Normal'],
                                fontSize=12,
                                alignment=TA_CENTER,
                                spaceBefore=10,
                                spaceAfter=5
                            )
                            story.append(Paragraph(chart_title, caption_style))
                            
                            # Add chart image
                            img = Image(chart_bytes, width=6*inch, height=3.5*inch)
                            img.hAlign = 'CENTER'
                            story.append(img)
                            story.append(Spacer(1, 0.2*inch))
                        except Exception as e:
                            logger.error(f"Error adding chart {chart_key} to PDF: {e}")
                            story.append(Paragraph(f"Error displaying chart: {chart_key}", styles['Italic']))
                
        # Build PDF document
        try:
            doc.build(story)
        except Exception as e:
            logger.error(f"Error building PDF: {e}")
            
            # Create error PDF
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            error_story = [
                Paragraph("Error Building PDF Report", styles['Heading1']),
                Paragraph(str(e), styles['Normal'])
            ]
            
            try:
                doc.build(error_story)
            except Exception:
                return BytesIO(b"Failed to generate PDF report.")
                
        buffer.seek(0)
        return buffer