# app/services/export_submission_service.py

import itertools
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
import os
import logging
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Flowable
from PIL import Image as PILImage
from reportlab.lib.utils import ImageReader
import io
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest
from app.models.form_submission import FormSubmission
from app.models.attachment import Attachment
from app.models.answer_submitted import AnswerSubmitted
from app.models.form import Form
from app.models.form_question import FormQuestion
from app.services.report.answer_formatters.answer_formatter_factory import AnswerFormatterFactory


logger = logging.getLogger(__name__)

# Global variables for PDF formatting
# Page layout settings
PAGE_MARGINS = {
    'top': 0.75 * inch,
    'bottom': 0.75 * inch,
    'left': 0.80 * inch,
    'right': 0.75 * inch
}

# Content spacing settings
TITLE_SPACING = {
    'before': 12,
    'after': 18
}

# Question formatting
QUESTION_FORMATTING = {
    'font_size': 12,
    'space_before': 8,
    'space_after': 1,
    'left_indent': 0
}

# Answer formatting
ANSWER_FORMATTING = {
    'font_size': 11,
    'space_before': 2,
    'space_after': 12,
    'left_indent': 20
}

# Signature formatting
SIGNATURE_FORMATTING = {
    'section_space_before': 1,
    'section_space_after': 1,
    'image_width': 3.5 * inch,
    'image_height': 1.4 * inch,
    'space_between': 1,
    'signature_space_after': 1
}

# Default image settings
DEFAULT_IMAGE_SETTINGS = {
    'max_width': 7.0 * inch,
    'default_opacity': 1.0
}


class ExportSubmissionService:
    """Service for exporting form submissions to PDF"""
    
    @staticmethod
    def _process_header_image(
        image_file: FileStorage, 
        opacity: float = 1.0,
        size: Optional[float] = None,
        width: Optional[float] = None,
        height: Optional[float] = None
    ) -> Optional[BytesIO]:
        """
        Process a header image file applying the specified opacity and sizing
        
        Args:
            image_file: The uploaded image file
            opacity: Opacity value between 0.0 and 1.0
            size: Optional size percentage (100 = original size, 200 = double size)
            width: Optional specific width (ignores aspect ratio if height also provided)
            height: Optional specific height (ignores aspect ratio if width also provided)
            
        Returns:
            BytesIO: Processed image as BytesIO or None if processing fails
        """
        try:
            # Validate opacity range
            opacity = max(0.0, min(1.0, opacity))
            
            # Read image data
            img_data = image_file.read()
            img_file = io.BytesIO(img_data)
            
            # Open with PIL
            img = PILImage.open(img_file)
            
            # Handle resizing based on provided parameters
            orig_width, orig_height = img.size
            new_width, new_height = orig_width, orig_height
            
            if width is not None and height is not None:
                # Specific dimensions provided - ignore aspect ratio
                new_width = width
                new_height = height
                img = img.resize((int(new_width), int(new_height)), PILImage.LANCZOS)
            elif width is not None:
                # Only width provided - maintain aspect ratio
                aspect_ratio = orig_height / orig_width
                new_width = width
                new_height = width * aspect_ratio
                img = img.resize((int(new_width), int(new_height)), PILImage.LANCZOS)
            elif height is not None:
                # Only height provided - maintain aspect ratio
                aspect_ratio = orig_width / orig_height
                new_height = height
                new_width = height * aspect_ratio
                img = img.resize((int(new_width), int(new_height)), PILImage.LANCZOS)
            elif size is not None:
                # Scale by percentage (100 = original size)
                scale_factor = size / 100.0
                new_width = orig_width * scale_factor
                new_height = orig_height * scale_factor
                img = img.resize((int(new_width), int(new_height)), PILImage.LANCZOS)
            
            # Convert to RGBA if not already
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Apply opacity (multiply alpha channel)
            pixels = img.load()
            width, height = img.size
            for y in range(height):
                for x in range(width):
                    r, g, b, a = pixels[x, y]
                    pixels[x, y] = (r, g, b, int(a * opacity))
            
            # Save to BytesIO
            result_io = io.BytesIO()
            img.save(result_io, format='PNG')
            result_io.seek(0)
            
            # Store dimensions for later use
            result_io.img_width = new_width
            result_io.img_height = new_height
            
            return result_io
        
        except Exception as e:
            logger.error(f"Error processing header image: {str(e)}")
            return None
        
    @staticmethod
    def _consolidate_table_questions(answers):
        """
        Consolidate table-related questions into structured table data
        
        Args:
            answers: List of AnswerSubmitted instances
            
        Returns:
            Tuple of (consolidated answers, table data dictionary)
        """
        import re
        from collections import defaultdict
        
        table_pattern = re.compile(r'^(Table\s+\d+)(?:\s+(.*))?$')
        table_data = defaultdict(lambda: {'headers': [], 'rows': []})
        non_table_answers = []
        table_answers = []
        
        # First pass: identify table questions and categorize them
        for answer in answers:
            question = answer.question
            match = table_pattern.match(question) if question else None
            
            if match and answer.question_type and answer.question_type.lower() == 'table':
                table_name = match.group(1)
                qualifier = match.group(2) or ""
                table_answers.append((table_name, qualifier, answer))
            else:
                non_table_answers.append(answer)
        
        # Process table questions to extract headers and rows
        for table_name, table_questions in itertools.groupby(
            sorted(table_answers, key=lambda x: x[0]), 
            key=lambda x: x[0]
        ):
            col_headers = []
            rows = defaultdict(dict)
            row_order = []
            
            # Process each answer in this table group
            for _, qualifier, answer in table_questions:
                # Check if it's a column header (Column X)
                if qualifier and qualifier.lower().startswith('column '):
                    try:
                        col_num = int(qualifier.lower().replace('column ', '').strip()) - 1
                        col_headers.append((col_num, answer.answer or ""))
                    except ValueError:
                        col_headers.append((len(col_headers), answer.answer or ""))
                
                # Check if it's a row cell (Row X.Y)
                elif qualifier and qualifier.lower().startswith('row '):
                    try:
                        row_parts = qualifier.lower().replace('row ', '').strip().split('.')
                        if len(row_parts) == 2:
                            row_num = int(row_parts[0]) - 1
                            col_num = int(row_parts[1]) - 1
                            
                            if row_num not in row_order:
                                row_order.append(row_num)
                                
                            rows[row_num][col_num] = answer.answer or ""
                    except ValueError:
                        # Handle non-standard format
                        pass
                
                # Handle any other format
                elif answer.answer:
                    # Try to extract structured data from the answer itself
                    try:
                        import json
                        try:
                            table_json = json.loads(answer.answer)
                            if isinstance(table_json, list):
                                # Handle different JSON table formats
                                if table_json and isinstance(table_json[0], dict):
                                    # Dict format with keys as headers
                                    headers = list(table_json[0].keys())
                                    col_headers = [(i, h) for i, h in enumerate(headers)]
                                    
                                    # Extract rows
                                    for i, row_data in enumerate(table_json):
                                        rows[i] = {j: str(val) for j, (_, val) 
                                                in enumerate(zip(headers, [row_data.get(h, "") for h in headers]))}
                                        if i not in row_order:
                                            row_order.append(i)
                                
                                elif table_json and isinstance(table_json[0], list):
                                    # List of lists format
                                    if len(table_json) > 1:
                                        # First row as headers
                                        col_headers = [(i, str(h)) for i, h in enumerate(table_json[0])]
                                        
                                        # Remaining rows as data
                                        for i, row_data in enumerate(table_json[1:]):
                                            rows[i] = {j: str(val) for j, val in enumerate(row_data)}
                                            if i not in row_order:
                                                row_order.append(i)
                        except json.JSONDecodeError:
                            # Not JSON, could be CSV-like
                            if ',' in answer.answer or '~' in answer.answer:
                                separator = '~' if '~' in answer.answer else ','
                                table_lines = answer.answer.strip().split('\n')
                                
                                if table_lines:
                                    # Process header row
                                    header_cells = [cell.strip() for cell in table_lines[0].split(separator)]
                                    col_headers = [(i, h) for i, h in enumerate(header_cells)]
                                    
                                    # Process data rows
                                    for i, line in enumerate(table_lines[1:]):
                                        cells = [cell.strip() for cell in line.split(separator)]
                                        rows[i] = {j: val for j, val in enumerate(cells)}
                                        if i not in row_order:
                                            row_order.append(i)
                                    
                    except Exception as e:
                        logger.error(f"Error parsing table data: {str(e)}")
            
            # Sort headers by column number
            col_headers.sort(key=lambda x: x[0])
            headers_list = [h for _, h in col_headers]
            
            # Sort rows by row number and fill in any missing cells
            max_cols = max([max(row.keys()) for row in rows.values()]) + 1 if rows else len(headers_list)
            table_rows = []
            
            for row_num in sorted(row_order):
                row_data = rows.get(row_num, {})
                table_row = []
                
                for col in range(max_cols):
                    table_row.append(row_data.get(col, ""))
                
                table_rows.append(table_row)
            
            # Store the processed table data
            table_data[table_name] = {
                'headers': headers_list or [""] * max_cols,
                'rows': table_rows
            }
        
        return non_table_answers, dict(table_data)
    
    @staticmethod
    def export_submission_to_pdf(
        submission_id: int,
        upload_path: str,
        include_signatures: bool = True,
        header_image: Optional[FileStorage] = None,
        header_opacity: float = DEFAULT_IMAGE_SETTINGS['default_opacity'],
        header_size: Optional[float] = None,
        header_width: Optional[float] = None,
        header_height: Optional[float] = None,
        header_alignment: str = "center",
        signatures_size: float = 100,
        signatures_alignment: str = "vertical"
    ) -> Tuple[Optional[BytesIO], Optional[str]]:
        """
        Export a form submission to PDF with all answers, optional signatures, and header image
        
        Args:
            submission_id: ID of the form submission
            upload_path: Path to uploads folder for retrieving signatures
            include_signatures: Whether to include signature images or not
            header_image: Optional image to use as header
            header_opacity: Opacity for the header image (0.0 to 1.0)
            header_size: Optional size percentage (keeping aspect ratio)
            header_width: Optional specific width in pixels (ignores aspect ratio if height also provided)
            header_height: Optional specific height in pixels (ignores aspect ratio if width also provided)
            header_alignment: Alignment of the header image (left, center, right)
            signatures_size: Size percentage for signature images (100 = original size)
            signatures_alignment: Layout for signatures (vertical, horizontal)
            
        Returns:
            Tuple containing BytesIO PDF buffer or None, and error message or None
        """
        try:
            # Get the submission with all needed relationships
            submission = FormSubmission.query.filter_by(
                id=submission_id,
                is_deleted=False
            ).first()
            
            if not submission:
                return None, "Submission not found"
                
            # Get form details
            form = Form.query.filter_by(
                id=submission.form_id,
                is_deleted=False
            ).first()
            
            if not form:
                return None, "Form not found"
                
            # Create a buffer for the PDF
            buffer = BytesIO()
            
            # Create document using global settings
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=PAGE_MARGINS['right'],
                leftMargin=PAGE_MARGINS['left'],
                topMargin=PAGE_MARGINS['top'],
                bottomMargin=PAGE_MARGINS['bottom'],
                title=f"Form Submission - {form.title}"
            )
            
            # Prepare styles using global settings
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                name='FormTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=TITLE_SPACING['after'],
                alignment=1  # Center alignment for title
            ))
            styles.add(ParagraphStyle(
                name='Question',
                parent=styles['Heading2'],
                fontSize=QUESTION_FORMATTING['font_size'],
                spaceBefore=QUESTION_FORMATTING['space_before'],
                spaceAfter=QUESTION_FORMATTING['space_after'],
                leftIndent=QUESTION_FORMATTING['left_indent']
            ))
            styles.add(ParagraphStyle(
                name='Answer',
                parent=styles['Normal'],
                fontSize=ANSWER_FORMATTING['font_size'],
                spaceBefore=ANSWER_FORMATTING['space_before'],
                spaceAfter=ANSWER_FORMATTING['space_after'],
                leftIndent=ANSWER_FORMATTING['left_indent']
            ))
            styles.add(ParagraphStyle(
                name='SignatureLabel',
                parent=styles['Heading3'],
                fontSize=11,
                spaceAfter=1,
                alignment=0,  # Left alignment for signature labels
                leftIndent=0  # No indent for signature labels
            ))
            
            # Add specialized styles for table and dropdown formatters
            styles.add(ParagraphStyle(
                name='TableHeader',
                parent=styles['Normal'],
                fontSize=10,
                fontName='Helvetica-Bold',
                alignment=1,  # Center
                spaceAfter=6
            ))
            
            styles.add(ParagraphStyle(
                name='TableCell',
                parent=styles['Normal'],
                fontSize=9,
                spaceAfter=0
            ))
            
            styles.add(ParagraphStyle(
                name='BulletItem',
                parent=styles['Normal'],
                fontSize=ANSWER_FORMATTING['font_size'],
                spaceBefore=1,
                spaceAfter=1,
                leftIndent=ANSWER_FORMATTING['left_indent'] + 10,
                bulletIndent=ANSWER_FORMATTING['left_indent']
            ))
            
            # Create the content
            story = []
            
            # Process and add header image if provided
            if header_image:
                processed_image = ExportSubmissionService._process_header_image(
                    header_image, 
                    opacity=header_opacity,
                    size=header_size,
                    width=header_width,
                    height=header_height
                )
                
                if processed_image and hasattr(processed_image, 'img_width') and hasattr(processed_image, 'img_height'):
                    # Get image dimensions
                    img_width = processed_image.img_width
                    img_height = processed_image.img_height
                    
                    # Calculate aspect ratio and scale to fit page width if not explicitly sized
                    if header_width is None and header_height is None and header_size is None:
                        max_width = DEFAULT_IMAGE_SETTINGS['max_width']
                        if img_width > max_width:
                            scale_factor = max_width / img_width
                            img_width = max_width
                            img_height = img_height * scale_factor
                    
                    # Calculate alignment for image
                    page_width = letter[0] - PAGE_MARGINS['left'] - PAGE_MARGINS['right']
                    
                    # Set horizontal alignment
                    if header_alignment.lower() == "left":
                        # Left alignment - no horizontal adjustment needed
                        alignment = "LEFT"
                    elif header_alignment.lower() == "right":
                        # Right alignment
                        alignment = "RIGHT"
                    else:
                        # Center alignment (default)
                        alignment = "CENTER"
                    
                    # Create a table for the image with alignment
                    img_table = Table(
                        [[Image(processed_image, width=img_width, height=img_height)]],
                        colWidths=[page_width]
                    )
                    img_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (0, 0), alignment),
                        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                    ]))
                    story.append(img_table)
                    story.append(Spacer(1, 1))
            
            # Add title and description
            story.append(Paragraph(form.title, styles['FormTitle']))
            if form.description:
                story.append(Paragraph(form.description, styles['Normal']))
            story.append(Spacer(1, 12))
            
            # Add submission info in a more organized way
            info_data = [
                ['Submitted by:', submission.submitted_by],
                ['Date:', submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S')]
            ]
            
            # Create a table for submission info with proper styling
            info_table = Table(info_data, colWidths=[1.5*inch, 5.28*inch])
            info_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                ('LEFTPADDING', (0, 0), (0, -1), 0),  # No left padding for first column
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 1))
            
            # Get all answers excluding signature type questions
            answers = AnswerSubmitted.query.filter_by(
                form_submission_id=submission_id,
                is_deleted=False
            ).all()
            
            # Filter out signature questions
            non_signature_answers = [a for a in answers if a.question_type.lower() != 'signature']
            
            # Consolidate table questions and dropdown questions
            import itertools
            from collections import defaultdict
            import re
            
            # Process tables - identify and group table-related answers
            table_pattern = re.compile(r'^(Table\s+\d+)(?:\s+(.*))?$')
            table_data = defaultdict(lambda: {'headers': [], 'rows': []})
            dropdown_groups = defaultdict(list)
            regular_answers = []
            
            # First pass: identify and categorize questions
            for answer in non_signature_answers:
                question = answer.question
                answer_type = answer.question_type.lower() if answer.question_type else ""
                
                # Check if it's a table question
                if question:
                    match = table_pattern.match(question)
                    if match and answer_type == 'table':
                        table_name = match.group(1)
                        qualifier = match.group(2) or ""
                        
                        # Extract table structure information
                        if qualifier.lower().startswith('column '):
                            try:
                                col_num = int(qualifier.lower().replace('column ', '').strip()) - 1
                                table_data[table_name]['headers'].append((col_num, answer.answer or ""))
                            except ValueError:
                                table_data[table_name]['headers'].append((len(table_data[table_name]['headers']), answer.answer or ""))
                        elif qualifier.lower().startswith('row '):
                            try:
                                row_parts = qualifier.lower().replace('row ', '').strip().split('.')
                                if len(row_parts) == 2:
                                    row_num = int(row_parts[0]) - 1
                                    col_num = int(row_parts[1]) - 1
                                    
                                    # Ensure we have enough rows
                                    while len(table_data[table_name]['rows']) <= row_num:
                                        table_data[table_name]['rows'].append({})
                                    
                                    # Add cell data
                                    table_data[table_name]['rows'][row_num][col_num] = answer.answer or ""
                            except (ValueError, IndexError) as e:
                                logger.warning(f"Error processing table row: {str(e)}")
                        else:
                            # Try to parse from the answer itself if it contains structured data
                            if answer.answer:
                                try:
                                    import json
                                    try:
                                        # Try to parse as JSON
                                        table_json = json.loads(answer.answer)
                                        if isinstance(table_json, list):
                                            # Process tables in JSON format
                                            if table_json and isinstance(table_json[0], dict):
                                                # Dictionary format with headers
                                                headers = list(table_json[0].keys())
                                                for i, header in enumerate(headers):
                                                    table_data[table_name]['headers'].append((i, header))
                                                    
                                                # Extract rows
                                                for i, row_data in enumerate(table_json):
                                                    row_dict = {}
                                                    for j, header in enumerate(headers):
                                                        row_dict[j] = str(row_data.get(header, ""))
                                                        
                                                    # Add to rows
                                                    if i >= len(table_data[table_name]['rows']):
                                                        table_data[table_name]['rows'].append(row_dict)
                                                    else:
                                                        table_data[table_name]['rows'][i].update(row_dict)
                                            
                                            elif table_json and isinstance(table_json[0], list):
                                                # List of lists format
                                                if len(table_json) > 0:
                                                    # First row might be headers
                                                    for i, header in enumerate(table_json[0]):
                                                        table_data[table_name]['headers'].append((i, str(header)))
                                                    
                                                    # Remaining rows as data
                                                    for i, row_data in enumerate(table_json[1:], 0):
                                                        row_dict = {}
                                                        for j, cell in enumerate(row_data):
                                                            row_dict[j] = str(cell)
                                                        
                                                        # Add to rows
                                                        if i >= len(table_data[table_name]['rows']):
                                                            table_data[table_name]['rows'].append(row_dict)
                                                        else:
                                                            table_data[table_name]['rows'][i].update(row_dict)
                                    except json.JSONDecodeError:
                                        # Not JSON, try CSV-like format
                                        if '\n' in answer.answer and (',' in answer.answer or '~' in answer.answer):
                                            separator = '~' if '~' in answer.answer else ','
                                            lines = answer.answer.strip().split('\n')
                                            
                                            # Process header row
                                            if lines:
                                                header_cells = lines[0].split(separator)
                                                for i, header in enumerate(header_cells):
                                                    table_data[table_name]['headers'].append((i, header.strip()))
                                                
                                                # Process data rows
                                                for i, line in enumerate(lines[1:], 0):
                                                    cells = line.split(separator)
                                                    row_dict = {}
                                                    for j, cell in enumerate(cells):
                                                        row_dict[j] = cell.strip()
                                                    
                                                    # Add to rows
                                                    if i >= len(table_data[table_name]['rows']):
                                                        table_data[table_name]['rows'].append(row_dict)
                                                    else:
                                                        table_data[table_name]['rows'][i].update(row_dict)
                                except Exception as e:
                                    logger.error(f"Error parsing table data: {str(e)}")
                                    regular_answers.append(answer)
                        continue
                    
                    # Check if it's a dropdown question
                    elif answer_type in ['dropdown', 'select', 'multiselect']:
                        # Group dropdowns with the same question text
                        dropdown_groups[question].append(answer)
                        continue
                
                # Default - regular answer
                regular_answers.append(answer)
            
            # Process table data into structured tables
            structured_tables = {}
            for table_name, table_content in table_data.items():
                # Sort headers by column index
                headers = sorted(table_content['headers'], key=lambda x: x[0])
                header_row = [h for _, h in headers]
                
                # Determine max columns
                max_cols = max([max(row.keys()) for row in table_content['rows']]) + 1 if table_content['rows'] and table_content['rows'][0] else len(header_row)
                
                # Prepare structured table data
                rows = []
                for row_dict in table_content['rows']:
                    table_row = []
                    for col in range(max_cols):
                        table_row.append(row_dict.get(col, ""))
                    rows.append(table_row)
                
                # Store processed table
                structured_tables[table_name] = {
                    'headers': header_row,
                    'rows': rows
                }
            
            # Process dropdown groups
            dropdown_data = {}
            for question, answers_list in dropdown_groups.items():
                combined_values = []
                
                for answer in answers_list:
                    if answer.answer:
                        try:
                            # Try parsing as JSON
                            import json
                            try:
                                data = json.loads(answer.answer)
                                if isinstance(data, list):
                                    combined_values.extend(data)
                                else:
                                    combined_values.append(str(data))
                            except json.JSONDecodeError:
                                # Not JSON, check if comma-separated
                                if ',' in answer.answer:
                                    values = [v.strip() for v in answer.answer.split(',')]
                                    combined_values.extend(values)
                                else:
                                    combined_values.append(answer.answer)
                        except Exception as e:
                            logger.error(f"Error processing dropdown: {str(e)}")
                            combined_values.append(answer.answer)
                
                # Store processed dropdown
                dropdown_data[question] = combined_values
            
            # Sort regular answers for display
            sorted_regular_answers = sorted(regular_answers, key=lambda a: a.question)
            
            # Add regular questions and answers first
            for answer in sorted_regular_answers:
                q_text = f"{answer.question}"
                story.append(Paragraph(q_text, styles['Question']))
                
                # Use our formatter for non-grouped questions
                answer_flowables = ExportSubmissionService._format_answer_by_type(answer, styles)
                story.extend(answer_flowables)
            
            # Add dropdown questions
            for question, values in dropdown_data.items():
                # Add question
                story.append(Paragraph(question, styles['Question']))
                
                # Format values as bulleted list if multiple values
                if len(values) > 1:
                    bullets = ""
                    for value in values:
                        bullets += f"• {value}<br/>"
                    story.append(Paragraph(bullets, styles['Answer']))
                elif len(values) == 1:
                    # Single value
                    story.append(Paragraph(values[0], styles['Answer']))
                else:
                    # No values
                    story.append(Paragraph("No selection", styles['Answer']))
            
            # Add tables
            for table_name, table_content in structured_tables.items():
                # Add table title
                story.append(Paragraph(table_name, styles['Question']))
                
                # Build complete table with headers and data
                headers = table_content['headers']
                rows = table_content['rows']
                
                if headers or rows:
                    # Create full table data including headers
                    table_data = [headers] + rows
                    
                    # Create column widths - auto sizing based on content
                    col_count = len(headers) if headers else (len(rows[0]) if rows else 1)
                    available_width = 6.5 * inch  # Approximate available width on the page
                    col_width = available_width / col_count
                    col_widths = [col_width] * col_count
                    
                    # Create the table
                    pdf_table = Table(table_data, colWidths=col_widths)
                    
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
                    
                    # Add table to the story
                    story.append(pdf_table)
                    story.append(Spacer(1, 10))
                else:
                    # No data found for this table
                    story.append(Paragraph("No data available for this table", styles['Answer']))
                    story.append(Spacer(1, 5))
            
            # Add signatures if requested
            if include_signatures:
                # Get all signature attachments
                attachments = Attachment.query.filter_by(
                    form_submission_id=submission_id,
                    is_signature=True,
                    is_deleted=False
                ).all()
                
                if attachments:
                    story.append(Spacer(1, SIGNATURE_FORMATTING['section_space_before']))
                    story.append(Paragraph("Signatures:", styles['Heading2']))
                    story.append(Spacer(1, 1))
                    
                    # Apply signature size scaling
                    scale_factor = signatures_size / 100.0
                    sig_width = SIGNATURE_FORMATTING['image_width'] * scale_factor
                    sig_height = SIGNATURE_FORMATTING['image_height'] * scale_factor
                    
                    # Handle horizontal alignment (multiple signatures in a row)
                    if signatures_alignment.lower() == "horizontal" and len(attachments) > 1:
                        # Calculate available width
                        available_width = letter[0] - PAGE_MARGINS['left'] - PAGE_MARGINS['right']
                        
                        # Calculate how many signatures can fit on one row
                        # Use a smaller width to allow for spacing between columns
                        sig_col_width = sig_width * 1.2  # Add 20% for spacing
                        sigs_per_row = min(len(attachments), max(1, int(available_width / sig_col_width)))
                        
                        # Prepare data for the table - group signatures into rows
                        table_data = []
                        current_row = []
                        
                        for idx, attachment in enumerate(attachments):
                            file_path = os.path.join(upload_path, attachment.file_path)
                            exists = os.path.exists(file_path)
                            
                            # Extract signature metadata
                            signature_position = attachment.signature_position
                            signature_author = attachment.signature_author
                            
                            # Try to extract from filename if not in attachment record
                            if not signature_position or not signature_author:
                                try:
                                    filename = os.path.basename(attachment.file_path)
                                    parts = filename.split('+')
                                    
                                    if len(parts) >= 4:
                                        if not signature_position:
                                            signature_position = parts[1].replace('_', ' ')
                                        if not signature_author:
                                            signature_author = parts[2].replace('_', ' ')
                                except Exception as e:
                                    logger.warning(f"Could not parse signature metadata from filename: {str(e)}")
                            
                            # Create a signature block
                            sig_elements = []
                            
                            # Add the signature image if it exists - NO SPACER AFTER IMAGE
                            if exists:
                                try:
                                    img = Image(file_path, width=sig_width, height=sig_height)
                                    sig_elements.append(img)
                                    # REMOVED SPACER HERE
                                except Exception as img_error:
                                    logger.warning(f"Error adding signature image: {str(img_error)}")
                                    sig_elements.append(Paragraph("Image could not be loaded", styles['Normal']))
                                    # REMOVED SPACER HERE
                            
                            # Add signature line and information
                            sig_elements.append(Paragraph("<b>________________________________</b>", styles['Normal']))
                            if signature_author:
                                sig_elements.append(Paragraph(f"<b>Signed by:</b> {signature_author}", styles['Normal']))
                            if signature_position:
                                sig_elements.append(Paragraph(f"<b>Position:</b> {signature_position}", styles['Normal']))
                            
                            # Add to current row
                            current_row.append(sig_elements)
                            
                            # If we've filled a row or this is the last attachment, add the row to the table data
                            if len(current_row) == sigs_per_row or idx == len(attachments) - 1:
                                # Pad row with empty cells if needed
                                while len(current_row) < sigs_per_row:
                                    current_row.append([])
                                    
                                table_data.append(current_row)
                                current_row = []
                        
                        # Create column widths
                        col_width = available_width / sigs_per_row
                        col_widths = [col_width] * sigs_per_row
                        
                        # Create signature table
                        for row in table_data:
                            # Create a sub-table for each cell
                            row_data = []
                            for cell_elements in row:
                                if cell_elements:  # Skip empty cells
                                    # Create a nested table for each signature
                                    sig_table = Table(
                                        [[element] for element in cell_elements],
                                        colWidths=[col_width * 0.95]  # Slightly smaller for margin
                                    )
                                    sig_table.setStyle(TableStyle([
                                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                        # Tighten spacing within the signature block
                                        ('TOPPADDING', (0, 0), (-1, -1), 0),
                                        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                                    ]))
                                    row_data.append(sig_table)
                                else:
                                    row_data.append("")  # Empty cell
                            
                            # Add row to story
                            sig_row_table = Table(
                                [row_data],
                                colWidths=col_widths
                            )
                            sig_row_table.setStyle(TableStyle([
                                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                ('TOPPADDING', (0, 0), (-1, -1), 0),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                            ]))
                            story.append(sig_row_table)
                    
                    else:
                        # Vertical layout (default) - one signature per row
                        for attachment in attachments:
                            file_path = os.path.join(upload_path, attachment.file_path)
                            exists = os.path.exists(file_path)
                            
                            # Extract signature metadata
                            signature_position = attachment.signature_position
                            signature_author = attachment.signature_author
                            
                            # Try to extract from filename if not in attachment record
                            if not signature_position or not signature_author:
                                try:
                                    filename = os.path.basename(attachment.file_path)
                                    parts = filename.split('+')
                                    
                                    if len(parts) >= 4:
                                        # Format: {form_submission_id}+{signature_position}+{signature_author}+{timestamp}
                                        if not signature_position:
                                            signature_position = parts[1].replace('_', ' ')
                                        if not signature_author:
                                            signature_author = parts[2].replace('_', ' ')
                                except Exception as e:
                                    logger.warning(f"Could not parse signature metadata from filename: {str(e)}")
                            
                            if exists:
                                try:
                                    # 1. First, add the signature image with the new size
                                    img = Image(file_path, 
                                            width=sig_width, 
                                            height=sig_height)
                                    
                                    # Create a table with zero left padding to push image to the left
                                    sig_table = Table(
                                        [[img]],
                                        colWidths=[7*inch]
                                    )
                                    sig_table.setStyle(TableStyle([
                                        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                                        ('VALIGN', (0, 0), (0, 0), 'TOP'),
                                        ('LEFTPADDING', (0, 0), (0, 0), 0),
                                        ('RIGHTPADDING', (0, 0), (0, 0), 0),
                                        ('TOPPADDING', (0, 0), (0, 0), 0),
                                        ('BOTTOMPADDING', (0, 0), (0, 0), 0),
                                    ]))
                                    
                                    story.append(sig_table)
                                    # REMOVED SPACER HERE
                                    
                                    # 2. Next, add signature author below the image
                                    if signature_author:
                                        story.append(Paragraph(f"<b>________________________________</b>", styles['Normal']))
                                        story.append(Paragraph(f"<b>Signed by:</b> {signature_author}", styles['Normal']))
                                        # REMOVED SPACER HERE
                                    
                                    # 3. Finally, add signature position below the author
                                    if signature_position:
                                        story.append(Paragraph(f"<b>Position:</b> {signature_position}", styles['Normal']))
                                    
                                    # Add spacing after each signature
                                    story.append(Spacer(1, SIGNATURE_FORMATTING['space_between']))
                                    
                                except Exception as img_error:
                                    logger.warning(f"Error adding signature image: {str(img_error)}")
                                    story.append(Paragraph("Image could not be loaded", styles['Normal']))
                                    # REMOVED SPACER HERE
                            else:
                                # Add signature information even if image can't be found
                                if signature_author:
                                    story.append(Paragraph(f"<b>________________________________</b>", styles['Normal']))
                                    story.append(Paragraph(f"<b>Signed by:</b> {signature_author}", styles['Normal']))
                                if signature_position:
                                    story.append(Paragraph(f"<b>Position:</b> {signature_position}", styles['Normal']))
                                story.append(Spacer(1, SIGNATURE_FORMATTING['space_between']))
                    
                    # Add spacing after signature section
                    story.append(Spacer(1, SIGNATURE_FORMATTING['section_space_after']))
            
            # Build the PDF
            doc.build(story)
            buffer.seek(0)
            return buffer, None
            
        except Exception as e:
            logger.error(f"Error exporting submission to PDF: {str(e)}")
            return None, str(e)
        
    @staticmethod
    def _format_answer_simple(answer, styles):
        """
        Simple answer formatter that doesn't rely on external modules
        This is a fallback to ensure the PDF generation always works
        
        Args:
            answer: AnswerSubmitted instance
            styles: ReportLab styles dictionary
            
        Returns:
            List of Flowable objects for the PDF
        """
        # Get answer text, handle None values
        answer_text = answer.answer if answer.answer and hasattr(answer, 'answer') else "No answer provided"
        
        # Just format as a paragraph - this is ultra-safe
        return [Paragraph(answer_text, styles['Answer'])]
        
    @staticmethod
    def _format_answer(answer, styles):
        """
        Format an answer using the appropriate formatter based on question type
        
        Args:
            answer: AnswerSubmitted instance
            styles: ReportLab styles dictionary
            
        Returns:
            List of Flowable objects for the PDF
        """
        from .report.answer_formatters import AnswerFormatterFactory
        
        # Get the question type
        question_type = answer.question_type.lower() if hasattr(answer, 'question_type') and answer.question_type else None
        
        # Get answer text, handle None values
        answer_text = answer.answer if answer.answer else None
        
        # Use formatter factory to get the right formatter
        formatter = AnswerFormatterFactory.get_formatter(question_type)
        
        # Return the formatted flowables
        return formatter.format(answer_text, styles)
        
    @staticmethod
    def _format_answer_by_type(answer, styles):
        """
        Format an answer based on its question type
        This is a self-contained method that doesn't rely on external modules
        
        Args:
            answer: AnswerSubmitted instance
            styles: ReportLab styles dictionary
            
        Returns:
            List of Flowable objects for the PDF
        """
        from reportlab.platypus import Paragraph, Table, TableStyle, Spacer
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        import json
        
        # Safety check - if styles is None, create a minimal styles dict
        if styles is None:
            from reportlab.lib.styles import getSampleStyleSheet
            styles = getSampleStyleSheet()
        
        # Get the question type
        question_type = ""
        if hasattr(answer, 'question_type') and answer.question_type:
            question_type = answer.question_type.lower()
        
        # Get answer text, handle None values
        answer_text = ""
        if hasattr(answer, 'answer') and answer.answer:
            answer_text = answer.answer
        else:
            return [Paragraph("No answer provided", styles['Answer'])]
        
        # Format based on question type
        if question_type == "table":
            # Table handling
            try:
                # Try parsing as JSON
                try:
                    table_data = json.loads(answer_text)
                    
                    # Handle list of dicts or list of lists
                    if isinstance(table_data, list):
                        if table_data and isinstance(table_data[0], dict):
                            # Convert dict list to table with headers
                            headers = list(table_data[0].keys())
                            rows = [headers]
                            for item in table_data:
                                rows.append([str(item.get(h, "")) for h in headers])
                        elif table_data and isinstance(table_data[0], list):
                            # Already in list of lists format
                            rows = [[str(cell) for cell in row] for row in table_data]
                        else:
                            return [Paragraph(answer_text, styles['Answer'])]
                        
                        # Create table
                        col_count = len(rows[0]) if rows else 1
                        available_width = 6.5 * inch
                        col_width = available_width / col_count
                        
                        table = Table(rows, colWidths=[col_width] * col_count)
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, -1), 9),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                        ]))
                        
                        return [table, Spacer(1, 5)]
                    else:
                        return [Paragraph(answer_text, styles['Answer'])]
                
                except json.JSONDecodeError:
                    # Try CSV-like format
                    if "~" in answer_text or "," in answer_text:
                        separator = "~" if "~" in answer_text else ","
                        
                        rows = []
                        for line in answer_text.strip().split("\n"):
                            rows.append([cell.strip() for cell in line.split(separator)])
                        
                        col_count = max([len(row) for row in rows]) if rows else 1
                        available_width = 6.5 * inch
                        col_width = available_width / col_count
                        
                        table = Table(rows, colWidths=[col_width] * col_count)
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, -1), 9),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                        ]))
                        
                        return [table, Spacer(1, 5)]
                    else:
                        return [Paragraph(answer_text, styles['Answer'])]
                        
            except Exception as e:
                logger.error(f"Error formatting table: {str(e)}")
                return [Paragraph(answer_text, styles['Answer'])]
                
        elif question_type in ["dropdown", "select", "multiselect"]:
            # Dropdown handling
            try:
                # Check if it's a JSON list
                try:
                    data = json.loads(answer_text)
                    if isinstance(data, list):
                        # Format as a bulleted list - with proper indentation and spacing
                        from reportlab.platypus import ListFlowable, ListItem
                        
                        if 'BulletItem' in styles:
                            bullet_style = styles['BulletItem']
                        else:
                            bullet_style = styles['Answer']
                        
                        # If only one item, just show it without bullets
                        if len(data) == 1:
                            return [Paragraph(str(data[0]), styles['Answer'])]
                        
                        # For multiple items, create a proper bulleted list
                        bullets = []
                        for item in data:
                            bullets.append(ListItem(Paragraph(str(item), bullet_style), leftIndent=20))
                        
                        # Return a properly formatted list
                        list_flowable = ListFlowable(
                            bullets,
                            bulletType='bullet',
                            start=None,
                            bulletFormat=None,
                            leftIndent=20,
                            bulletFontName='Helvetica',
                            bulletFontSize=9
                        )
                        
                        return [list_flowable]
                    else:
                        # Single value as JSON
                        return [Paragraph(str(data), styles['Answer'])]
                        
                except json.JSONDecodeError:
                    # Might be a delimiter-separated list
                    if ',' in answer_text:
                        options = [opt.strip() for opt in answer_text.split(',')]
                        if len(options) > 1:
                            bullets = ""
                            for item in options:
                                bullets += f"• {item}<br/>"
                            return [Paragraph(bullets, styles['Answer'])]
                    
                    # Not JSON or delimited list, just return the text
                    return [Paragraph(answer_text, styles['Answer'])]
                    
            except Exception as e:
                logger.error(f"Error formatting dropdown: {str(e)}")
                return [Paragraph(answer_text, styles['Answer'])]

    @staticmethod
    def _format_table_answer(answer_text, styles):
        """
        Format table type answers for PDF display
        
        Args:
            answer_text: String containing table data (expected format: JSON or CSV-like)
            styles: ReportLab styles dictionary
            
        Returns:
            List of Flowable objects
        """
        flowables = []
        
        try:
            # Try to parse as JSON first
            import json
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

    @staticmethod
    def _format_dropdown_answer(answer_text, styles):
        """
        Format dropdown type answers for PDF display
        
        Args:
            answer_text: Selected option text
            styles: ReportLab styles dictionary
            
        Returns:
            Paragraph flowable
        """
        try:
            # Check if it's a multi-select dropdown (might be JSON array)
            import json
            try:
                data = json.loads(answer_text)
                if isinstance(data, list):
                    # Format as a bulleted list
                    bullets = ""
                    for item in data:
                        bullets += f"• {item}<br/>"
                    return Paragraph(bullets, styles['Answer'])
                else:
                    # Single value as JSON
                    return Paragraph(str(data), styles['Answer'])
            except json.JSONDecodeError:
                # Not JSON, just return the text
                return Paragraph(answer_text, styles['Answer'])
        except Exception as e:
            logger.error(f"Error formatting dropdown answer: {str(e)}")
            return Paragraph(answer_text, styles['Answer'])

    @staticmethod
    def _get_signature_images(submission_id: int, upload_path: str) -> List[Dict]:
        """
        Get all signature images for a submission with proper metadata extraction
        
        Args:
            submission_id: ID of the form submission
            upload_path: Path to uploads folder
            
        Returns:
            List of signature image details including paths, authors, and positions
        """
        signatures = []
        
        # Get all signature attachments
        attachments = Attachment.query.filter_by(
            form_submission_id=submission_id,
            is_signature=True,
            is_deleted=False
        ).all()
        
        # Process each attachment
        for attachment in attachments:
            # Get the file path
            file_path = os.path.join(upload_path, attachment.file_path)
            exists = os.path.exists(file_path)
            
            # Try to extract author and position from filename or use model fields
            signature_position = attachment.signature_position
            signature_author = attachment.signature_author
            
            # If not available in model, try to extract from filename
            if not signature_position or not signature_author:
                try:
                    # Parse the filename which should have format: {id}+{position}+{author}+{timestamp}.ext
                    filename = os.path.basename(attachment.file_path)
                    parts = filename.split('+')
                    
                    if len(parts) >= 4:
                        # First part is submission ID
                        # Second part is position
                        if not signature_position:
                            signature_position = parts[1].replace('_', ' ')
                        
                        # Third part is author
                        if not signature_author:
                            signature_author = parts[2].replace('_', ' ')
                except Exception as e:
                    logger.warning(f"Could not parse signature metadata from filename: {str(e)}")
            
            signatures.append({
                "path": file_path,
                "position": signature_position or "Signature",
                "author": signature_author or "Signer",
                "exists": exists
            })
        
        return signatures