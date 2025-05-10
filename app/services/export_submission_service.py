# app/services/export_submission_service.py

import itertools
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime
import os
import logging
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, pt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Flowable
from PIL import Image as PILImage # type: ignore
from reportlab.lib.utils import ImageReader
import io
import json
import re
from collections import defaultdict

from werkzeug.datastructures import FileStorage # type: ignore

from app.models.form_submission import FormSubmission
from app.models.attachment import Attachment
from app.models.answer_submitted import AnswerSubmitted
from app.models.form import Form

logger = logging.getLogger(__name__)

# --- Default Style Configuration ---
DEFAULT_STYLE_CONFIG: Dict[str, Any] = {
    # Page Layout
    "page_margin_top": 0.75 * inch,
    "page_margin_bottom": 0.75 * inch,
    "page_margin_left": 0.75 * inch,
    "page_margin_right": 0.75 * inch,
    "default_font_family": "Helvetica",
    "default_font_color": colors.black,

    # Title
    "title_font_family": "Helvetica-Bold",
    "title_font_size": 18 * pt,
    "title_font_color": colors.black,
    "title_alignment": 1, # 0=left, 1=center, 2=right, 4=justify
    "title_space_after": 0.25 * inch,

    # Submission Info (Submitted by, Date)
    "info_font_family": "Helvetica",
    "info_font_size": 10 * pt,
    "info_font_color": colors.darkgrey,
    "info_label_font_family": "Helvetica-Bold",
    "info_space_after": 0.2 * inch,

    # Question
    "question_font_family": "Helvetica-Bold",
    "question_font_size": 11 * pt,
    "question_font_color": colors.black,
    "question_left_indent": 0 * pt,
    "question_space_before": 0.15 * inch,
    "question_space_after": 4 * pt,
    "question_leading": 14 * pt,

    # Answer
    "answer_font_family": "Helvetica",
    "answer_font_size": 10 * pt,
    "answer_font_color": colors.darkslategrey,
    "answer_left_indent": 15 * pt,
    "answer_space_before": 2 * pt,
    "answer_space_after": 0.15 * inch,
    "answer_leading": 12 * pt,
    "qa_layout": "answer_below",  # "answer_below" or "answer_same_line"
    "answer_same_line_max_length": 70, # Max length for answer to be on same line

    # Table Header
    "table_header_font_family": "Helvetica-Bold",
    "table_header_font_size": 9 * pt,
    "table_header_font_color": colors.black,
    "table_header_bg_color": colors.lightgrey,
    "table_header_padding": 3 * pt, # Single value for all sides
    "table_header_alignment": "CENTER", # LEFT, CENTER, RIGHT

    # Table Cell
    "table_cell_font_family": "Helvetica",
    "table_cell_font_size": 8 * pt,
    "table_cell_font_color": colors.black,
    "table_cell_padding": 3 * pt, # Single value for all sides
    "table_cell_alignment": "LEFT", # LEFT, CENTER, RIGHT
    "table_grid_color": colors.grey,
    "table_grid_thickness": 0.5 * pt,

    # Signatures
    "signature_label_font_family": "Helvetica-Bold",
    "signature_label_font_size": 12 * pt,
    "signature_label_font_color": colors.black,
    "signature_text_font_family": "Helvetica",
    "signature_text_font_size": 9 * pt,
    "signature_text_font_color": colors.black,
    "signature_image_width": 2.0 * inch,
    "signature_image_height": 0.8 * inch,
    "signature_section_space_before": 0.3 * inch,
    "signature_space_between_vertical": 0.2 * inch,
}

def _get_color(color_input: Any, default_color: colors.Color) -> colors.Color:
    """Converts a color input (hex string, name, or ReportLab Color) to a ReportLab Color."""
    if isinstance(color_input, colors.Color):
        return color_input
    if isinstance(color_input, str):
        try:
            return colors.HexColor(color_input)
        except ValueError:
            try:
                # Try common color names if HexColor fails
                return getattr(colors, color_input.lower(), default_color)
            except AttributeError:
                return default_color
    return default_color

def _get_float_unit(value: Any, default_value: float, unit: float = 1.0) -> float:
    """Converts input to float and applies unit, returns default if error."""
    try:
        return float(value) * unit
    except (ValueError, TypeError):
        return default_value


class ExportSubmissionService:
    @staticmethod
    def _process_header_image(
        image_file: FileStorage, opacity: float = 1.0, size: Optional[float] = None,
        width: Optional[float] = None, height: Optional[float] = None
    ) -> Optional[BytesIO]:
        try:
            opacity = max(0.0, min(1.0, opacity))
            img_data = image_file.read()
            image_file.seek(0) 

            img = PILImage.open(io.BytesIO(img_data))
            orig_width, orig_height = img.size
            new_width, new_height = float(orig_width), float(orig_height)

            if width is not None and height is not None:
                new_width, new_height = float(width), float(height)
            elif width is not None:
                new_width = float(width)
                new_height = new_width * (orig_height / orig_width) if orig_width > 0 else 0
            elif height is not None:
                new_height = float(height)
                new_width = new_height * (orig_width / orig_height) if orig_height > 0 else 0
            elif size is not None:
                scale_factor = float(size) / 100.0
                new_width *= scale_factor
                new_height *= scale_factor
            
            if new_width <=0 or new_height <=0 :
                logger.warning(f"Invalid image dimensions after resize: {new_width}x{new_height}. Using original.")
                new_width, new_height = float(orig_width), float(orig_height)

            img = img.resize((int(new_width), int(new_height)), PILImage.LANCZOS)

            if img.mode != 'RGBA':
                img = img.convert('RGBA')

            alpha_channel = img.split()[3]
            alpha_with_opacity = alpha_channel.point(lambda i: int(i * opacity))
            img.putalpha(alpha_with_opacity)

            result_io = io.BytesIO()
            img.save(result_io, format='PNG')
            result_io.seek(0)

            setattr(result_io, 'img_width', new_width)
            setattr(result_io, 'img_height', new_height)
            return result_io
        except Exception as e:
            logger.error(f"Error processing header image: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def export_structured_submission_to_pdf(
        submission_id: int, upload_path: str,
        pdf_style_options: Optional[Dict[str, Any]] = None,
        # Header image options remain separate for clarity in controller/view
        header_image: Optional[FileStorage] = None, header_opacity: float = 1.0,
        header_size: Optional[float] = None, header_width: Optional[float] = None, header_height: Optional[float] = None,
        header_alignment: str = "center",
        # Signature options also separate for now
        include_signatures: bool = True, signatures_size: float = 100, signatures_alignment: str = "vertical"
    ) -> Tuple[Optional[BytesIO], Optional[str]]:
        
        styles_config = DEFAULT_STYLE_CONFIG.copy()
        if pdf_style_options:
            styles_config.update(pdf_style_options)

        try:
            submission = FormSubmission.query.filter_by(id=submission_id, is_deleted=False).first()
            if not submission: return None, "Submission not found"
            form = Form.query.filter_by(id=submission.form_id, is_deleted=False).first()
            if not form: return None, "Form not found"

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter,
                                    rightMargin=_get_float_unit(styles_config.get("page_margin_right"), DEFAULT_STYLE_CONFIG["page_margin_right"]),
                                    leftMargin=_get_float_unit(styles_config.get("page_margin_left"), DEFAULT_STYLE_CONFIG["page_margin_left"]),
                                    topMargin=_get_float_unit(styles_config.get("page_margin_top"), DEFAULT_STYLE_CONFIG["page_margin_top"]),
                                    bottomMargin=_get_float_unit(styles_config.get("page_margin_bottom"), DEFAULT_STYLE_CONFIG["page_margin_bottom"]),
                                    title=f"Form Submission - {form.title}")

            styles = getSampleStyleSheet()
            
            styles.add(ParagraphStyle(
                name='CustomFormTitle', fontName=styles_config["title_font_family"],
                fontSize=_get_float_unit(styles_config["title_font_size"], DEFAULT_STYLE_CONFIG["title_font_size"]),
                textColor=_get_color(styles_config["title_font_color"], DEFAULT_STYLE_CONFIG["title_font_color"]),
                alignment=int(styles_config.get("title_alignment", DEFAULT_STYLE_CONFIG["title_alignment"])), # Ensure int
                spaceAfter=_get_float_unit(styles_config["title_space_after"], DEFAULT_STYLE_CONFIG["title_space_after"]),
                leading=_get_float_unit(styles_config["title_font_size"], DEFAULT_STYLE_CONFIG["title_font_size"]) * 1.2
            ))
            styles.add(ParagraphStyle(
                name='CustomInfoLabel', fontName=styles_config["info_label_font_family"],
                fontSize=_get_float_unit(styles_config["info_font_size"], DEFAULT_STYLE_CONFIG["info_font_size"]),
                textColor=_get_color(styles_config["info_font_color"], DEFAULT_STYLE_CONFIG["info_font_color"]),
            ))
            styles.add(ParagraphStyle(
                name='CustomInfoValue', fontName=styles_config["info_font_family"],
                fontSize=_get_float_unit(styles_config["info_font_size"], DEFAULT_STYLE_CONFIG["info_font_size"]),
                textColor=_get_color(styles_config["info_font_color"], DEFAULT_STYLE_CONFIG["info_font_color"]),
            ))
            styles.add(ParagraphStyle(
                name='CustomQuestion', fontName=styles_config["question_font_family"],
                fontSize=_get_float_unit(styles_config["question_font_size"], DEFAULT_STYLE_CONFIG["question_font_size"]),
                textColor=_get_color(styles_config["question_font_color"], DEFAULT_STYLE_CONFIG["question_font_color"]),
                leftIndent=_get_float_unit(styles_config["question_left_indent"], DEFAULT_STYLE_CONFIG["question_left_indent"]),
                spaceBefore=_get_float_unit(styles_config["question_space_before"], DEFAULT_STYLE_CONFIG["question_space_before"]),
                spaceAfter=_get_float_unit(styles_config["question_space_after"], DEFAULT_STYLE_CONFIG["question_space_after"]),
                leading=_get_float_unit(styles_config["question_leading"], DEFAULT_STYLE_CONFIG["question_leading"])
            ))
            styles.add(ParagraphStyle(
                name='CustomAnswer', fontName=styles_config["answer_font_family"],
                fontSize=_get_float_unit(styles_config["answer_font_size"], DEFAULT_STYLE_CONFIG["answer_font_size"]),
                textColor=_get_color(styles_config["answer_font_color"], DEFAULT_STYLE_CONFIG["answer_font_color"]),
                leftIndent=_get_float_unit(styles_config["answer_left_indent"], DEFAULT_STYLE_CONFIG["answer_left_indent"]),
                spaceBefore=_get_float_unit(styles_config["answer_space_before"], DEFAULT_STYLE_CONFIG["answer_space_before"]),
                spaceAfter=_get_float_unit(styles_config["answer_space_after"], DEFAULT_STYLE_CONFIG["answer_space_after"]),
                leading=_get_float_unit(styles_config["answer_leading"], DEFAULT_STYLE_CONFIG["answer_leading"])
            ))
            styles.add(ParagraphStyle( # For Q&A on same line
                name='CustomQACombined', fontName=styles_config["question_font_family"], # Use question font as base
                fontSize=_get_float_unit(styles_config["question_font_size"], DEFAULT_STYLE_CONFIG["question_font_size"]),
                textColor=_get_color(styles_config["question_font_color"], DEFAULT_STYLE_CONFIG["question_font_color"]),
                leftIndent=_get_float_unit(styles_config["question_left_indent"], DEFAULT_STYLE_CONFIG["question_left_indent"]),
                spaceBefore=_get_float_unit(styles_config["question_space_before"], DEFAULT_STYLE_CONFIG["question_space_before"]),
                spaceAfter=_get_float_unit(styles_config["answer_space_after"], DEFAULT_STYLE_CONFIG["answer_space_after"]), # Use answer's space after
                leading=_get_float_unit(styles_config["question_leading"], DEFAULT_STYLE_CONFIG["question_leading"])
            ))

            styles.add(ParagraphStyle(
                name='CustomTableHeader', fontName=styles_config["table_header_font_family"],
                fontSize=_get_float_unit(styles_config["table_header_font_size"], DEFAULT_STYLE_CONFIG["table_header_font_size"]),
                textColor=_get_color(styles_config["table_header_font_color"], DEFAULT_STYLE_CONFIG["table_header_font_color"]),
                backColor=_get_color(styles_config["table_header_bg_color"], DEFAULT_STYLE_CONFIG["table_header_bg_color"]),
                alignment=getattr(TableStyle, styles_config.get("table_header_alignment", "CENTER").upper(), 1), #CENTER
                leading=_get_float_unit(styles_config["table_header_font_size"], DEFAULT_STYLE_CONFIG["table_header_font_size"]) * 1.2,
                leftPadding=_get_float_unit(styles_config["table_cell_padding"], DEFAULT_STYLE_CONFIG["table_cell_padding"]), # Use cell padding for consistency
                rightPadding=_get_float_unit(styles_config["table_cell_padding"], DEFAULT_STYLE_CONFIG["table_cell_padding"]),
                topPadding=_get_float_unit(styles_config["table_cell_padding"], DEFAULT_STYLE_CONFIG["table_cell_padding"]),
                bottomPadding=_get_float_unit(styles_config["table_cell_padding"], DEFAULT_STYLE_CONFIG["table_cell_padding"]),
            ))
            styles.add(ParagraphStyle(
                name='CustomTableCell', fontName=styles_config["table_cell_font_family"],
                fontSize=_get_float_unit(styles_config["table_cell_font_size"], DEFAULT_STYLE_CONFIG["table_cell_font_size"]),
                textColor=_get_color(styles_config["table_cell_font_color"], DEFAULT_STYLE_CONFIG["table_cell_font_color"]),
                alignment=getattr(TableStyle, styles_config.get("table_cell_alignment", "LEFT").upper(), 0), # LEFT
                leading=_get_float_unit(styles_config["table_cell_font_size"], DEFAULT_STYLE_CONFIG["table_cell_font_size"]) * 1.2,
                leftPadding=_get_float_unit(styles_config["table_cell_padding"], DEFAULT_STYLE_CONFIG["table_cell_padding"]),
                rightPadding=_get_float_unit(styles_config["table_cell_padding"], DEFAULT_STYLE_CONFIG["table_cell_padding"]),
                topPadding=_get_float_unit(styles_config["table_cell_padding"], DEFAULT_STYLE_CONFIG["table_cell_padding"]),
                bottomPadding=_get_float_unit(styles_config["table_cell_padding"], DEFAULT_STYLE_CONFIG["table_cell_padding"]),
            ))
            styles.add(ParagraphStyle(
                name='CustomSignatureLabel', fontName=styles_config["signature_label_font_family"],
                fontSize=_get_float_unit(styles_config["signature_label_font_size"], DEFAULT_STYLE_CONFIG["signature_label_font_size"]),
                textColor=_get_color(styles_config["signature_label_font_color"], DEFAULT_STYLE_CONFIG["signature_label_font_color"]),
                spaceBefore=_get_float_unit(styles_config["signature_section_space_before"], DEFAULT_STYLE_CONFIG["signature_section_space_before"]),
                spaceAfter=4*pt, alignment=0
            ))
            styles.add(ParagraphStyle(
                name='CustomSignatureText', fontName=styles_config["signature_text_font_family"],
                fontSize=_get_float_unit(styles_config["signature_text_font_size"], DEFAULT_STYLE_CONFIG["signature_text_font_size"]),
                textColor=_get_color(styles_config["signature_text_font_color"], DEFAULT_STYLE_CONFIG["signature_text_font_color"]),
                leading=_get_float_unit(styles_config["signature_text_font_size"], DEFAULT_STYLE_CONFIG["signature_text_font_size"]) * 1.2,
                alignment=0
            ))

            story: List[Flowable] = []
            page_content_width = doc.width # Use doc.width for available content area

            if header_image:
                processed_image_io = ExportSubmissionService._process_header_image(
                    header_image, header_opacity, header_size, header_width, header_height
                )
                if processed_image_io and hasattr(processed_image_io, 'img_width') and hasattr(processed_image_io, 'img_height'):
                    img_w_attr = getattr(processed_image_io, 'img_width')
                    img_h_attr = getattr(processed_image_io, 'img_height')
                    
                    if not header_width and not header_height and not header_size: # Scale to fit if no specific size
                         if img_w_attr > page_content_width:
                            scale_ratio = page_content_width / img_w_attr
                            img_w_attr *= scale_ratio
                            img_h_attr *= scale_ratio
                    
                    img_obj = Image(processed_image_io, width=img_w_attr, height=img_h_attr)
                    align_val_h = header_alignment.upper()
                    if align_val_h not in ['LEFT', 'CENTER', 'RIGHT']: align_val_h = 'CENTER'
                    
                    header_img_table = Table([[img_obj]], colWidths=[page_content_width])
                    header_img_table.setStyle(TableStyle([('ALIGN', (0,0), (0,0), align_val_h), ('VALIGN', (0,0), (0,0), 'MIDDLE'),
                                                       ('LEFTPADDING', (0,0), (0,0), 0), ('RIGHTPADDING', (0,0), (0,0), 0),
                                                       ('TOPPADDING', (0,0), (0,0), 0), ('BOTTOMPADDING', (0,0), (0,0), 0)]))
                    story.append(header_img_table)
                    story.append(Spacer(1, 0.1 * inch))

            story.append(Paragraph(form.title, styles['CustomFormTitle']))
            if form.description:
                story.append(Paragraph(form.description, styles['Normal'])) # Could also make this customizable
            
            info_data_styled = [
                [Paragraph('<b>Submitted by:</b>', styles['CustomInfoLabel']), Paragraph(str(submission.submitted_by or 'N/A'), styles['CustomInfoValue'])],
                [Paragraph('<b>Date:</b>', styles['CustomInfoLabel']), Paragraph(submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if submission.submitted_at else 'N/A', styles['CustomInfoValue'])]
            ]
            info_table_styled = Table(info_data_styled, colWidths=[1.5 * inch, None])
            info_table_styled.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 2)]))
            story.append(info_table_styled)
            story.append(Spacer(1, _get_float_unit(styles_config["info_space_after"], DEFAULT_STYLE_CONFIG["info_space_after"])))
            
            all_answers = AnswerSubmitted.query.filter_by(form_submission_id=submission_id, is_deleted=False).all()
            non_signature_answers = [a for a in all_answers if a.question_type and a.question_type.lower() != 'signature']

            table_pattern_re = re.compile(r'^(Table\s+\d+)(?:\s+(.*))?$')
            pattern_based_tables_data = defaultdict(lambda: {'headers': [], 'rows': defaultdict(dict), 'row_order': [], 'raw_json_csv_data': None})
            cell_based_tables_data = defaultdict(lambda: {'name': '', 'headers': {}, 'cells': {}, 'row_indices': set(), 'col_indices': set(), 'header_row_present': False})
            choice_answer_groups = defaultdict(list)
            regular_answers = []

            for ans in non_signature_answers:
                q_text = ans.question if ans.question else "Untitled Question"
                ans_type = ans.question_type.lower() if ans.question_type else ""

                if ans_type == 'table' and ans.column is not None and ans.row is not None:
                    table_id = q_text
                    cell_based_tables_data[table_id]['name'] = table_id
                    current_data = ans.cell_content if ans.cell_content is not None else ans.answer
                    current_data_str = str(current_data) if current_data is not None else ""
                    if ans.row == 0: 
                        cell_based_tables_data[table_id]['headers'][ans.column] = current_data_str
                        cell_based_tables_data[table_id]['col_indices'].add(ans.column)
                        cell_based_tables_data[table_id]['header_row_present'] = True
                    elif ans.row > 0: 
                        data_row_index = ans.row 
                        cell_based_tables_data[table_id]['cells'][(data_row_index, ans.column)] = current_data_str
                        cell_based_tables_data[table_id]['row_indices'].add(data_row_index)
                        cell_based_tables_data[table_id]['col_indices'].add(ans.column)
                    continue
                
                match_obj = table_pattern_re.match(q_text)
                if match_obj:
                    table_name = match_obj.group(1)
                    qualifier = match_obj.group(2) or ""
                    if qualifier.lower().startswith('column '):
                        try:
                            col_num = int(qualifier.lower().replace('column ', '').strip()) - 1
                            pattern_based_tables_data[table_name]['headers'].append((col_num, str(ans.answer or "")))
                        except ValueError:
                            pattern_based_tables_data[table_name]['headers'].append((len(pattern_based_tables_data[table_name]['headers']), str(ans.answer or "")))
                    elif qualifier.lower().startswith('row '):
                        try:
                            row_parts = qualifier.lower().replace('row ', '').strip().split('.')
                            if len(row_parts) == 2:
                                row_num = int(row_parts[0]) - 1; col_num = int(row_parts[1]) - 1
                                if row_num not in pattern_based_tables_data[table_name]['row_order']: pattern_based_tables_data[table_name]['row_order'].append(row_num)
                                pattern_based_tables_data[table_name]['rows'][row_num][col_num] = str(ans.answer or "")
                        except (ValueError, IndexError): regular_answers.append(ans)
                    elif ans.answer: pattern_based_tables_data[table_name]['raw_json_csv_data'] = ans.answer
                    else: 
                        if ans.answer: regular_answers.append(ans)
                    continue

                choice_based_types = ['dropdown', 'select', 'multiselect', 'checkbox', 'multiple_choices', 'single_choice']
                if ans_type in choice_based_types:
                    choice_answer_groups[q_text].append(ans)
                    continue
                
                regular_answers.append(ans)
            
            qa_layout = styles_config.get("qa_layout", "answer_below")
            answer_same_line_max_len = int(styles_config.get("answer_same_line_max_length", 70))

            for ans_item in sorted(regular_answers, key=lambda a: a.question or ""):
                q_text_p = str(ans_item.question or "Untitled Question")
                ans_val_p = str(ans_item.answer) if ans_item.answer is not None else "No answer provided"
                
                if qa_layout == "answer_same_line" and isinstance(ans_item.answer, str) and len(ans_val_p) <= answer_same_line_max_len and '\n' not in ans_val_p:
                    # Create bold question text part
                    question_part = f"<b>{q_text_p}:</b> "
                    # Create answer text part with answer font and color (requires more complex Paragraph creation or HTML-like string)
                    # For simplicity, we use one style but ideally answer part would use answer_style.
                    # This is a limitation of simple concatenation into one Paragraph.
                    # A more robust way is a 2-col table for each Q&A if same line is critical for all styles.
                    combined_text = f"{question_part} {ans_val_p}"
                    story.append(Paragraph(combined_text, styles['CustomQACombined']))
                else:
                    story.append(Paragraph(q_text_p, styles['CustomQuestion']))
                    story.append(Paragraph(ans_val_p, styles['CustomAnswer']))

            for q_text_choice, ans_list_choice in choice_answer_groups.items():
                q_text_c_p = str(q_text_choice)
                combined_options = []
                for choice_ans in ans_list_choice:
                    if choice_ans.answer is not None and str(choice_ans.answer).strip() != "":
                        try:
                            parsed_json_options = json.loads(choice_ans.answer)
                            if isinstance(parsed_json_options, list):
                                combined_options.extend([str(item) for item in parsed_json_options if str(item).strip() != ""])
                            else:
                                if str(parsed_json_options).strip() != "": combined_options.append(str(parsed_json_options))
                        except json.JSONDecodeError:
                             if str(choice_ans.answer).strip() != "": combined_options.append(str(choice_ans.answer))
                
                unique_options = list(dict.fromkeys(filter(None, combined_options)))
                ans_val_c_p = ", ".join(unique_options) if unique_options else "No selection"

                if qa_layout == "answer_same_line" and len(ans_val_c_p) <= answer_same_line_max_len and '\n' not in ans_val_c_p:
                    combined_text_c = f"<b>{q_text_c_p}:</b> {ans_val_c_p}"
                    story.append(Paragraph(combined_text_c, styles['CustomQACombined']))
                else:
                    story.append(Paragraph(q_text_c_p, styles['CustomQuestion']))
                    story.append(Paragraph(ans_val_c_p, styles['CustomAnswer']))
            
            table_cell_padding = _get_float_unit(styles_config.get("table_cell_padding"), DEFAULT_STYLE_CONFIG["table_cell_padding"])
            table_grid_color = _get_color(styles_config.get("table_grid_color"), DEFAULT_STYLE_CONFIG["table_grid_color"])
            table_grid_thickness = _get_float_unit(styles_config.get("table_grid_thickness"), DEFAULT_STYLE_CONFIG["table_grid_thickness"])

            for table_id_cb, content_cb in cell_based_tables_data.items():
                story.append(Paragraph(str(content_cb['name']), styles['CustomQuestion']))
                all_cols_indices = content_cb['col_indices']
                sorted_cols = sorted(list(all_cols_indices))
                data_row_indices = sorted([r for r in content_cb['row_indices'] if r > 0])
                header_styled_row_cb: List[Paragraph] = []
                actual_col_count_cb = len(sorted_cols)

                if content_cb['header_row_present']: 
                    for col_idx in sorted_cols:
                        header_text = str(content_cb['headers'].get(col_idx, f"Col {col_idx+1}"))
                        header_styled_row_cb.append(Paragraph(header_text, styles['CustomTableHeader']))
                elif actual_col_count_cb > 0 and not content_cb['header_row_present'] and data_row_indices: 
                    header_styled_row_cb = [Paragraph(f"Column {idx+1}", styles['CustomTableHeader']) for idx in sorted_cols]
                
                table_rows_styled_cb: List[List[Paragraph]] = []
                if header_styled_row_cb: table_rows_styled_cb.append(header_styled_row_cb)

                for data_row_idx in data_row_indices: 
                    current_row_styled_cb = [Paragraph(str(content_cb['cells'].get((data_row_idx, col_idx), "")), styles['CustomTableCell']) for col_idx in sorted_cols]
                    table_rows_styled_cb.append(current_row_styled_cb)

                if table_rows_styled_cb: 
                    col_widths_cb_val = [page_content_width / actual_col_count_cb] * actual_col_count_cb if actual_col_count_cb > 0 else [page_content_width]
                    rl_table_cb = Table(table_rows_styled_cb, colWidths=col_widths_cb_val, repeatRows=1 if header_styled_row_cb else 0)
                    style_cmds_cb_list = [('GRID', (0,0), (-1,-1), table_grid_thickness, table_grid_color), 
                                          ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                                          ('LEFTPADDING', (0,0), (-1,-1), table_cell_padding), 
                                          ('RIGHTPADDING', (0,0), (-1,-1), table_cell_padding),
                                          ('TOPPADDING', (0,0), (-1,-1), table_cell_padding),
                                          ('BOTTOMPADDING', (0,0), (-1,-1), table_cell_padding)]
                    if header_styled_row_cb: style_cmds_cb_list.append(('BACKGROUND', (0,0), (-1,0), _get_color(styles_config["table_header_bg_color"], DEFAULT_STYLE_CONFIG["table_header_bg_color"])))
                    rl_table_cb.setStyle(TableStyle(style_cmds_cb_list))
                    story.append(rl_table_cb)
                    story.append(Spacer(1, 0.15*inch))
                elif header_styled_row_cb: 
                    col_widths_cb_val_h = [page_content_width / actual_col_count_cb] * actual_col_count_cb if actual_col_count_cb > 0 else [page_content_width]
                    rl_table_cb_h = Table([header_styled_row_cb], colWidths=col_widths_cb_val_h)
                    rl_table_cb_h.setStyle(TableStyle([('GRID', (0,0), (-1,-1), table_grid_thickness, table_grid_color), 
                                                     ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), 
                                                     ('BACKGROUND', (0,0), (-1,0), _get_color(styles_config["table_header_bg_color"], DEFAULT_STYLE_CONFIG["table_header_bg_color"])),
                                                     ('LEFTPADDING', (0,0), (-1,-1), table_cell_padding), 
                                                     ('RIGHTPADDING', (0,0), (-1,-1), table_cell_padding),
                                                     ('TOPPADDING', (0,0), (-1,-1), table_cell_padding),
                                                     ('BOTTOMPADDING', (0,0), (-1,-1), table_cell_padding)]))
                    story.append(rl_table_cb_h)
                    story.append(Spacer(1, 0.15*inch))
                else:
                    story.append(Paragraph("No data for this table.", styles['CustomAnswer']))

            for table_name_pb, info_pb in pattern_based_tables_data.items():
                story.append(Paragraph(str(table_name_pb), styles['CustomQuestion']))
                data_for_pb_table_styled: List[List[Paragraph]] = []
                if info_pb['raw_json_csv_data']:
                    raw_str = info_pb['raw_json_csv_data']
                    try: 
                        parsed = json.loads(raw_str)
                        if isinstance(parsed, list) and parsed:
                            if isinstance(parsed[0], dict):
                                headers = list(parsed[0].keys())
                                data_for_pb_table_styled.append([Paragraph(str(h), styles['CustomTableHeader']) for h in headers])
                                for item_dict in parsed: data_for_pb_table_styled.append([Paragraph(str(item_dict.get(h, "")), styles['CustomTableCell']) for h in headers])
                            elif isinstance(parsed[0], list): 
                                data_for_pb_table_styled.append([Paragraph(str(h_item), styles['CustomTableHeader']) for h_item in parsed[0]])
                                for r_item_list in parsed[1:]: data_for_pb_table_styled.append([Paragraph(str(c_item), styles['CustomTableCell']) for c_item in r_item_list])
                    except json.JSONDecodeError: 
                        if '\n' in raw_str:
                            lines = [line.strip() for line in raw_str.strip().split('\n')]; sep = '~' if '~' in lines[0] else ','
                            if lines:
                                data_for_pb_table_styled.append([Paragraph(str(h.strip()), styles['CustomTableHeader']) for h in lines[0].split(sep)])
                                for data_line in lines[1:]: data_for_pb_table_styled.append([Paragraph(str(c.strip()), styles['CustomTableCell']) for c in data_line.split(sep)])
                if not data_for_pb_table_styled: 
                    headers_from_pattern = sorted(info_pb['headers'], key=lambda x: x[0]); header_texts = [h_text for _, h_text in headers_from_pattern]
                    current_max_cols = len(header_texts); rows_from_pattern_dict = info_pb['rows']
                    if rows_from_pattern_dict: current_max_cols = max(current_max_cols, max(max(r.keys())+1 if r else 0 for r in rows_from_pattern_dict.values()))
                    if not header_texts and current_max_cols > 0: header_texts = [f"Column {i+1}" for i in range(current_max_cols)]
                    if header_texts: data_for_pb_table_styled.append([Paragraph(str(h), styles['CustomTableHeader']) for h in header_texts])
                    for r_idx_pat in sorted(info_pb['row_order']):
                        r_data_pat = rows_from_pattern_dict.get(r_idx_pat, {})
                        data_for_pb_table_styled.append([Paragraph(str(r_data_pat.get(c_idx_pat, "")), styles['CustomTableCell']) for c_idx_pat in range(current_max_cols)])
                
                if data_for_pb_table_styled:
                    actual_cols_pb_val = len(data_for_pb_table_styled[0]) if data_for_pb_table_styled else 1
                    col_widths_pb_val = [page_content_width / actual_cols_pb_val] * actual_cols_pb_val if actual_cols_pb_val > 0 else [page_content_width]
                    rl_table_pb = Table(data_for_pb_table_styled, colWidths=col_widths_pb_val, repeatRows=1)
                    style_cmds_pb_list = [('GRID', (0,0), (-1,-1), table_grid_thickness, table_grid_color), 
                                          ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), 
                                          ('BACKGROUND', (0,0), (-1,0), _get_color(styles_config["table_header_bg_color"], DEFAULT_STYLE_CONFIG["table_header_bg_color"])),
                                          ('LEFTPADDING', (0,0), (-1,-1), table_cell_padding), 
                                          ('RIGHTPADDING', (0,0), (-1,-1), table_cell_padding),
                                          ('TOPPADDING', (0,0), (-1,-1), table_cell_padding),
                                          ('BOTTOMPADDING', (0,0), (-1,-1), table_cell_padding)]
                    rl_table_pb.setStyle(TableStyle(style_cmds_pb_list))
                    story.append(rl_table_pb)
                    story.append(Spacer(1, 0.15*inch))
                else: story.append(Paragraph("No data available for this table.", styles['CustomAnswer']))

            if include_signatures:
                sig_attachments = Attachment.query.filter_by(form_submission_id=submission_id, is_signature=True, is_deleted=False).all()
                if sig_attachments:
                    story.append(Paragraph("Signatures:", styles['CustomSignatureLabel'])) 
                    story.append(Spacer(1, 0.05 * inch)) # Reduced space
                    
                    sig_scale = signatures_size / 100.0
                    sig_img_w_conf = _get_float_unit(styles_config.get("signature_image_width"), DEFAULT_STYLE_CONFIG["signature_image_width"]) * sig_scale
                    sig_img_h_conf = _get_float_unit(styles_config.get("signature_image_height"), DEFAULT_STYLE_CONFIG["signature_image_height"]) * sig_scale
                    
                    if signatures_alignment.lower() == "horizontal" and len(sig_attachments) > 1:
                        max_sigs_per_row = int(page_content_width / (sig_img_w_conf + 0.2*inch)) if sig_img_w_conf > 0 else 1
                        max_sigs_per_row = max(1, min(max_sigs_per_row, len(sig_attachments), 4)) # Limit to e.g. 4 per row
                        
                        sig_rows_data_list = []
                        current_sig_row_items_list = []
                        for idx, att in enumerate(sig_attachments):
                            sig_block_elements_list: List[Flowable] = []
                            file_path = os.path.join(upload_path, att.file_path)
                            sig_author = att.signature_author or "N/A"
                            sig_position = att.signature_position or "N/A"
                            if os.path.exists(file_path):
                                try: sig_block_elements_list.append(Image(file_path, width=sig_img_w_conf, height=sig_img_h_conf))
                                except Exception: sig_block_elements_list.append(Paragraph("<i>[Image Error]</i>", styles['CustomSignatureText']))
                            else: sig_block_elements_list.append(Paragraph("<i>[Image Missing]</i>", styles['CustomSignatureText']))
                            
                            sig_block_elements_list.append(Spacer(1,2*pt))
                            sig_block_elements_list.append(Paragraph("<b>___________________________</b>", styles['CustomSignatureText']))
                            sig_block_elements_list.append(Paragraph(f"<b>Signed by:</b> {sig_author}", styles['CustomSignatureText']))
                            sig_block_elements_list.append(Paragraph(f"<b>Position:</b> {sig_position}", styles['CustomSignatureText']))
                            current_sig_row_items_list.append(sig_block_elements_list)

                            if len(current_sig_row_items_list) == max_sigs_per_row or idx == len(sig_attachments) - 1:
                                sig_rows_data_list.append(current_sig_row_items_list)
                                current_sig_row_items_list = []
                        
                        for sig_row_group_list in sig_rows_data_list:
                            col_w_sig_val = page_content_width / len(sig_row_group_list) if sig_row_group_list else page_content_width
                            sig_table_this_row = Table([sig_row_group_list], colWidths=[col_w_sig_val]*len(sig_row_group_list))
                            sig_table_this_row.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), 
                                                                  ('LEFTPADDING', (0,0), (-1,-1), 2*pt), # Minimal padding
                                                                  ('RIGHTPADDING', (0,0), (-1,-1), 2*pt)]))
                            story.append(sig_table_this_row)
                            story.append(Spacer(1, 0.1*inch))
                    else: 
                        for att in sig_attachments:
                            file_path = os.path.join(upload_path, att.file_path); sig_author_v = att.signature_author or "N/A"; sig_position_v = att.signature_position or "N/A"
                            if os.path.exists(file_path):
                                try: story.append(Image(file_path, width=sig_img_w_conf, height=sig_img_h_conf))
                                except Exception: story.append(Paragraph("<i>[Signature Image Error]</i>", styles['CustomSignatureText']))
                            else: story.append(Paragraph("<i>[Signature Image Missing]</i>", styles['CustomSignatureText']))
                            story.append(Spacer(1,2*pt))
                            story.append(Paragraph("<b>___________________________</b>", styles['CustomSignatureText']))
                            story.append(Paragraph(f"<b>Signed by:</b> {sig_author_v}", styles['CustomSignatureText']))
                            story.append(Paragraph(f"<b>Position:</b> {sig_position_v}", styles['CustomSignatureText']))
                            story.append(Spacer(1, _get_float_unit(styles_config.get("signature_space_between_vertical", DEFAULT_STYLE_CONFIG["signature_space_between_vertical"]))))
            
            doc.build(story)
            buffer.seek(0)
            return buffer, None
        except Exception as e:
            logger.error(f"Error exporting structured submission to PDF: {submission_id} - {str(e)}", exc_info=True)
            return None, f"An error occurred during PDF generation: {str(e)}"

    @staticmethod
    def export_submission_to_pdf( # This is now primarily a wrapper
        submission_id: int, upload_path: str, include_signatures: bool = True,
        header_image: Optional[FileStorage] = None, header_opacity: float = 1.0,
        header_size: Optional[float] = None, header_width: Optional[float] = None, header_height: Optional[float] = None,
        header_alignment: str = "center", signatures_size: float = 100, signatures_alignment: str = "vertical",
        pdf_style_options: Optional[Dict[str, Any]] = None # Pass through style options
    ) -> Tuple[Optional[BytesIO], Optional[str]]:
        logger.info(f"Calling export_structured_submission_to_pdf for submission_id: {submission_id} with custom styles.")
        return ExportSubmissionService.export_structured_submission_to_pdf(
            submission_id=submission_id, upload_path=upload_path,
            pdf_style_options=pdf_style_options, # Pass the new style options
            header_image=header_image, header_opacity=header_opacity, header_size=header_size,
            header_width=header_width, header_height=header_height, header_alignment=header_alignment,
            include_signatures=include_signatures, signatures_size=signatures_size, signatures_alignment=signatures_alignment
        )

    @staticmethod
    def _get_signature_images(submission_id: int, upload_path: str) -> List[Dict]:
        signatures_list = [] 
        attachments_list = Attachment.query.filter_by(form_submission_id=submission_id, is_signature=True, is_deleted=False).all()
        for attachment_item in attachments_list: 
            file_path_item = os.path.join(upload_path, attachment_item.file_path); exists_bool = os.path.exists(file_path_item) 
            sig_pos_item = attachment_item.signature_position; sig_auth_item = attachment_item.signature_author 
            if not sig_pos_item or not sig_auth_item:
                try:
                    filename_str = os.path.basename(attachment_item.file_path); parts_list = filename_str.split('+') 
                    if len(parts_list) >= 4:
                        if not sig_pos_item: sig_pos_item = parts_list[1].replace('_', ' ')
                        if not sig_auth_item: sig_auth_item = parts_list[2].replace('_', ' ')
                except Exception as e_sig: logger.warning(f"Could not parse signature metadata from filename: {str(e_sig)}")
            signatures_list.append({"path": file_path_item, "position": sig_pos_item or "Signature", "author": sig_auth_item or "Signer", "exists": exists_bool})
        return signatures_list