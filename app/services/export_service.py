# app/services/export_service.py

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.style import WD_STYLE_TYPE
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from werkzeug.exceptions import BadRequest

logger = logging.getLogger(__name__)

class ExportService:
    def __init__(self):
        self.supported_formats = ['PDF', 'DOCX']
        self.margin = 40

    def export_as_pdf(self, form_data: Dict[str, Any]) -> bytes:
        """
        Export form as fillable PDF
        """
        try:
            self._validate_form_data(form_data)
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=50,
                leftMargin=50,
                topMargin=50,
                bottomMargin=50
            )

            # Prepare styles
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                name='FormTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=20,
                alignment=1  # Center
            ))
            styles.add(ParagraphStyle(
                name='FormField',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=20,
                leading=16
            ))
            styles.add(ParagraphStyle(
                name='Answer',
                parent=styles['Normal'],
                fontSize=12,
                leftIndent=20,
                spaceAfter=15
            ))

            # Build content
            story = []

            # Header
            story.append(Paragraph(form_data['title'], styles['FormTitle']))
            if form_data.get('description'):
                story.append(Paragraph(form_data['description'], styles['Normal']))
            story.append(Spacer(1, 20))

            # Form Information
            story.append(Paragraph("Form Information:", styles['Heading2']))
            story.append(Paragraph(f"Environment: {form_data['created_by']['environment']['name']}", styles['Normal']))
            story.append(Paragraph(f"Created by: {form_data['created_by']['fullname']}", styles['Normal']))
            story.append(Spacer(1, 20))

            # Response Information
            story.append(Paragraph("Response Information:", styles['Heading2']))
            story.append(Paragraph("Name: _________________________________", styles['FormField']))
            story.append(Paragraph("Date: _________________________________", styles['FormField']))
            story.append(Spacer(1, 20))

            # Questions
            story.append(Paragraph("Questions:", styles['Heading2']))
            for i, question in enumerate(form_data.get('questions', []), 1):
                # Question text with number
                story.append(Paragraph(f"{i}. {question['text']}", styles['FormField']))
                
                # Add appropriate answer field based on question type
                if question['type'] == 'text':
                    story.append(Paragraph("Answer: _________________________________", styles['Answer']))
                
                elif question['type'] == 'checkbox':
                    # If there are predefined possible answers, use them
                    if question.get('possible_answers'):
                        for answer in question['possible_answers']:
                            story.append(Paragraph(f"□ {answer['value']}", styles['Answer']))
                    else:
                        story.append(Paragraph("□ Yes    □ No", styles['Answer']))
                
                elif question['type'] == 'multiple_choices':
                    if question.get('possible_answers'):
                        for answer in question['possible_answers']:
                            story.append(Paragraph(f"□ {answer['value']}", styles['Answer']))
                    else:
                        story.append(Paragraph("(No options available)", styles['Answer']))

                # Add remarks field if applicable
                if question.get('remarks'):
                    story.append(Paragraph(f"Remarks: {question['remarks']}", styles['Answer']))

                story.append(Spacer(1, 10))

            # Signature section
            story.append(Spacer(1, 30))
            story.append(Paragraph("Signatures:", styles['Heading2']))
            story.append(Paragraph("Completed by: _______________________________", styles['FormField']))
            story.append(Paragraph("Date: ____________________", styles['FormField']))
            story.append(Paragraph("Reviewed by: ________________________________", styles['FormField']))
            story.append(Paragraph("Date: ____________________", styles['FormField']))

            # Build PDF
            doc.build(story)
            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            raise BadRequest(f"Error generating PDF: {str(e)}")

    def export_as_docx(self, form_data: Dict[str, Any]) -> bytes:
        """
        Export form as fillable DOCX
        """
        try:
            self._validate_form_data(form_data)
            doc = Document()
            
            # Add title
            title = doc.add_heading(form_data['title'], 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Add description if present
            if form_data.get('description'):
                desc = doc.add_paragraph(form_data['description'])
                desc.alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_paragraph()

            # Form Information
            doc.add_heading('Form Information:', level=1)
            doc.add_paragraph(f"Environment: {form_data['created_by']['environment']['name']}")
            doc.add_paragraph(f"Created by: {form_data['created_by']['fullname']}")
            doc.add_paragraph()

            # Response Information
            doc.add_heading('Response Information:', level=1)
            doc.add_paragraph("Name: _________________________________")
            doc.add_paragraph("Date: _________________________________")
            doc.add_paragraph()

            # Questions
            doc.add_heading('Questions:', level=1)
            
            # Iterate through questions
            for i, question in enumerate(form_data.get('questions', []), 1):
                # Question text with number
                p = doc.add_paragraph()
                p.add_run(f"{i}. {question['text']}").bold = True
                
                # Add appropriate answer field based on question type
                if question['type'] == 'text':
                    doc.add_paragraph("Answer: _________________________________")
                
                elif question['type'] == 'checkbox':
                    # If there are predefined possible answers, use them
                    if question.get('possible_answers'):
                        for answer in question['possible_answers']:
                            p = doc.add_paragraph()
                            p.add_run(f"□ {answer['value']}")
                            p.style = 'List Bullet'  # Add bullets for better formatting
                    else:
                        doc.add_paragraph("□ Yes    □ No    □ N/A")
                
                elif question['type'] == 'multiple_choices':
                    if question.get('possible_answers'):
                        for answer in question['possible_answers']:
                            p = doc.add_paragraph()
                            p.add_run(f"□ {answer['value']}")
                            p.style = 'List Bullet'
                    else:
                        doc.add_paragraph("(No options available)")
                
                # Add remarks field if exists
                if question.get('remarks'):
                    p = doc.add_paragraph()
                    p.add_run("Remarks: ").bold = True
                    p.add_run(question['remarks'])
                
                doc.add_paragraph()  # Add spacing between questions

            # Signature section
            doc.add_heading('Signatures:', level=1)
            doc.add_paragraph("Completed by: _______________________________")
            doc.add_paragraph("Date: ____________________")
            doc.add_paragraph()
            doc.add_paragraph("Reviewed by: ________________________________")
            doc.add_paragraph("Date: ____________________")

            # Save to buffer
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Error generating DOCX: {str(e)}")
            raise BadRequest(f"Error generating DOCX: {str(e)}")

    @staticmethod
    def get_supported_formats() -> List[str]:
        """Get list of supported export formats"""
        return ['PDF', 'DOCX']
    
    def _validate_form_data(self, form_data: Dict[str, Any]) -> None:
        """Validate form data structure before export"""
        required_fields = ['title', 'created_by', 'questions']
        for field in required_fields:
            if field not in form_data:
                raise ValueError(f"Missing required field: {field}")
                
        if not isinstance(form_data['questions'], list):
            raise ValueError("Questions must be a list")
            
        for question in form_data['questions']:
            if 'text' not in question or 'type' not in question:
                raise ValueError("Each question must have 'text' and 'type' fields")

    def validate_format(self, format: str) -> None:
        """Validate export format"""
        if format.upper() not in self.supported_formats:
            raise ValueError(
                f"Unsupported format: {format}. Supported formats: {', '.join(self.supported_formats)}"
            )