# app/services/export_submission_service.py

import itertools
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime
import os
import logging
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle as ReportLabParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph as ReportLabParagraph, Spacer, Table as ReportLabTable, TableStyle as ReportLabTableStyle, Image as ReportLabImage, Flowable
from PIL import Image as PILImage # type: ignore
# from reportlab.lib.utils import ImageReader # type: ignore # Not explicitly used after ReportLabImage direct path usage
import io
import json
import re
from collections import defaultdict

from werkzeug.datastructures import FileStorage # type: ignore

# Assuming your models are correctly imported from your app structure
from app.models.form_submission import FormSubmission
from app.models.attachment import Attachment
from app.models.answer_submitted import AnswerSubmitted
from app.models.form import Form

# Imports for DOCX generation
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


logger = logging.getLogger(__name__)

# --- Default Style Configuration (for PDF) ---
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
    "title_font_size": 18,
    "title_font_color": colors.black,
    "title_alignment": 1, # ReportLab code for CENTER
    "title_space_after": 0.25 * inch,

    # Submission Info (Submitted by, Date)
    "info_font_family": "Helvetica",
    "info_font_size": 10,
    "info_font_color": colors.darkslategray,
    "info_label_font_family": "Helvetica-Bold",
    "info_space_after": 0.2 * inch,

    # Question
    "question_font_family": "Helvetica-Bold",
    "question_font_size": 11,
    "question_font_color": colors.black,
    "question_left_indent": 0,
    "question_space_before": 0.15 * inch,
    "question_space_after": 4,
    "question_leading": 14,

    # Answer
    "answer_font_family": "Helvetica",
    "answer_font_size": 10,
    "answer_font_color": colors.darkslategray,
    "answer_left_indent": 15,
    "answer_space_before": 2,
    "answer_space_after": 0.15 * inch,
    "answer_leading": 12,
    "qa_layout": "answer_below", # "answer_below" or "answer_same_line"
    "answer_same_line_max_length": 70,

    # Table Header
    "table_header_font_family": "Helvetica-Bold",
    "table_header_font_size": 9,
    "table_header_font_color": colors.black,
    "table_header_bg_color": colors.lightgrey, # PDF specific
    "table_header_padding": 3,
    "table_header_alignment": "CENTER", # String name for ParagraphStyle, TableStyle uses different enum

    # Table Cell
    "table_cell_font_family": "Helvetica",
    "table_cell_font_size": 8,
    "table_cell_font_color": colors.black,
    "table_cell_padding": 3,
    "table_cell_alignment": "LEFT", # String name for ParagraphStyle
    "table_grid_color": colors.grey, # PDF specific
    "table_grid_thickness": 0.5,

    # Signatures
    "signature_label_font_family": "Helvetica-Bold",
    "signature_label_font_size": 12,
    "signature_label_font_color": colors.black,
    "signature_text_font_family": "Helvetica",
    "signature_text_font_size": 9,
    "signature_text_font_color": colors.black,
    "signature_image_width": 2.0 * inch, # Note: inch is ReportLab, convert to Inches for DOCX
    "signature_image_height": 0.8 * inch, # Note: inch is ReportLab, convert to Inches for DOCX
    "signature_section_space_before": 0.3 * inch,
    "signature_space_between_vertical": 0.2 * inch,
}

# --- Helper functions for PDF styling (copied from previous response) ---
def _get_color_rl(color_input: Any, default_color: colors.Color) -> colors.Color: # Renamed for clarity
    if isinstance(color_input, colors.Color):
        return color_input
    if isinstance(color_input, str):
        try:
            if color_input.startswith("#"):
                return colors.HexColor(color_input)
            return getattr(colors, color_input.lower(), default_color)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid ReportLab color string '{color_input}'. Using default.")
            return default_color
    logger.warning(f"Invalid ReportLab color type '{type(color_input)}'. Using default.")
    return default_color

def _color_to_hex_string_rl(color_obj: colors.Color) -> str: # Renamed for clarity
    if hasattr(color_obj, 'hexval') and callable(getattr(color_obj, 'hexval')):
        return color_obj.hexval()
    r_float = max(0.0, min(1.0, color_obj.red))
    g_float = max(0.0, min(1.0, color_obj.green))
    b_float = max(0.0, min(1.0, color_obj.blue))
    r = int(r_float * 255)
    g = int(g_float * 255)
    b = int(b_float * 255)
    return f"#{r:02x}{g:02x}{b:02x}"

def _parse_numeric_value(value_input: Optional[Union[str, int, float]], default_numeric_value: float) -> float:
    if value_input is None:
        return default_numeric_value
    try:
        return float(value_input)
    except (ValueError, TypeError):
        logger.warning(f"Invalid numeric value '{value_input}'. Using default {default_numeric_value}.")
        return default_numeric_value

def _get_alignment_code_rl(align_input: Optional[Union[str, int]], default_align_str: str) -> int: # Renamed
    code_map = {"LEFT": 0, "CENTER": 1, "RIGHT": 2, "JUSTIFY": 4}
    if isinstance(align_input, int) and align_input in code_map.values():
        return align_input
    if isinstance(align_input, str):
        if align_input.isdigit():
            try:
                val = int(align_input)
                if val in code_map.values(): return val
            except ValueError: pass
        effective_align_str = align_input.upper()
        if effective_align_str in code_map:
            return code_map[effective_align_str]
    logger.warning(f"Invalid ReportLab alignment value '{align_input}'. Using default '{default_align_str}'.")
    return code_map.get(default_align_str.upper(), 1)

# --- Helper functions for DOCX styling ---
def _get_docx_alignment(align_input: Optional[Union[str, int]]) -> Optional[WD_ALIGN_PARAGRAPH]:
    if align_input is None:
        return None
    align_map_str = {
        "LEFT": WD_ALIGN_PARAGRAPH.LEFT,
        "CENTER": WD_ALIGN_PARAGRAPH.CENTER,
        "RIGHT": WD_ALIGN_PARAGRAPH.RIGHT,
        "JUSTIFY": WD_ALIGN_PARAGRAPH.JUSTIFY,
    }
    align_map_int = {
        0: WD_ALIGN_PARAGRAPH.LEFT,
        1: WD_ALIGN_PARAGRAPH.CENTER,
        2: WD_ALIGN_PARAGRAPH.RIGHT,
        4: WD_ALIGN_PARAGRAPH.JUSTIFY,
    }
    if isinstance(align_input, str):
        return align_map_str.get(align_input.upper())
    if isinstance(align_input, int):
        return align_map_int.get(align_input)
    return None

def _get_docx_color(color_str: Optional[str]) -> Optional[RGBColor]:
    if color_str and color_str.startswith("#") and len(color_str) == 7:
        try:
            return RGBColor(int(color_str[1:3], 16), int(color_str[3:5], 16), int(color_str[5:7], 16))
        except ValueError:
            logger.warning(f"Invalid hex color string for DOCX: '{color_str}'.")
            return None
    # TODO: Add mapping for common color names if needed
    logger.debug(f"Color string '{color_str}' not a direct hex, returning None for DOCX.")
    return None

def _set_cell_background_color(cell, hex_color_string: str):
    """Sets background color of a table cell in DOCX."""
    if not hex_color_string or not hex_color_string.startswith("#"):
        logger.warning(f"Invalid hex color for cell background: {hex_color_string}")
        return
    clean_hex = hex_color_string.lstrip('#')
    try:
        # Ensure cell has tcPr if not present
        tcPr = cell._tc.get_or_add_tcPr()
        # Create shd element for shading
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), clean_hex)
        tcPr.append(shd)
    except Exception as e:
        logger.error(f"Error setting cell background color '{hex_color_string}': {e}")


class ExportSubmissionService:
    @staticmethod
    def _process_header_image(
        image_file: FileStorage, _opacity: float = 1.0, size: Optional[float] = None, # opacity is for PDF
        width_px: Optional[float] = None, height_px: Optional[float] = None # Use px for explicit dimensions
    ) -> Optional[BytesIO]:
        try:
            img_data = image_file.read()
            image_file.seek(0) # Reset file pointer
            img = PILImage.open(io.BytesIO(img_data))
            orig_width_px, orig_height_px = img.size
            new_width_px, new_height_px = float(orig_width_px), float(orig_height_px)

            if width_px is not None and height_px is not None:
                new_width_px, new_height_px = float(width_px), float(height_px)
            elif width_px is not None:
                new_width_px = float(width_px)
                new_height_px = new_width_px * (orig_height_px / orig_width_px) if orig_width_px > 0 else 0
            elif height_px is not None:
                new_height_px = float(height_px)
                new_width_px = new_height_px * (orig_width_px / orig_height_px) if orig_height_px > 0 else 0
            elif size is not None: # size is percentage
                scale_factor = float(size) / 100.0
                new_width_px *= scale_factor
                new_height_px *= scale_factor

            if new_width_px <= 0 or new_height_px <= 0:
                logger.warning(f"Invalid image dimensions after resize: {new_width_px}x{new_height_px}. Using original.")
                new_width_px, new_height_px = float(orig_width_px), float(orig_height_px)

            img_resized = img.resize((int(new_width_px), int(new_height_px)), PILImage.LANCZOS)

            img_format = img.format if img.format else 'PNG'
            if img_format.upper() == 'SVG': # PIL can't save SVG, convert to PNG
                img_format = 'PNG'
                if img_resized.mode == 'P':
                    img_resized = img_resized.convert('RGBA')

            result_io = io.BytesIO()
            img_resized.save(result_io, format=img_format)
            result_io.seek(0)
            # Store dimensions in pixels, conversion to Inches or Points happens in respective export methods
            setattr(result_io, 'img_width_px', new_width_px)
            setattr(result_io, 'img_height_px', new_height_px)
            return result_io
        except Exception as e:
            logger.error(f"Error processing header image: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def export_structured_submission_to_pdf(
        submission_id: int, upload_path: str,
        pdf_style_options: Optional[Dict[str, Any]] = None,
        header_image: Optional[FileStorage] = None, header_opacity: float = 1.0,
        header_size: Optional[float] = None, header_width: Optional[float] = None, header_height: Optional[float] = None,
        header_alignment: str = "center",
        include_signatures: bool = True, signatures_size: float = 100, signatures_alignment: str = "vertical"
    ) -> Tuple[Optional[BytesIO], Optional[str]]:

        final_config = DEFAULT_STYLE_CONFIG.copy()
        if pdf_style_options:
            logger.debug(f"Applying PDF style options: {pdf_style_options}")
            for key, user_value in pdf_style_options.items():
                if user_value is None or key not in DEFAULT_STYLE_CONFIG: continue
                default_value = DEFAULT_STYLE_CONFIG[key]
                if key.endswith("_color"):
                    final_config[key] = _get_color_rl(user_value, default_value if isinstance(default_value, colors.Color) else colors.black)
                elif key.endswith("_font_family") or key.endswith("_layout") or \
                     (key.endswith("_alignment") and isinstance(user_value, str) and not user_value.isdigit()):
                    final_config[key] = str(user_value)
                elif key.endswith("_alignment") and (isinstance(user_value, int) or (isinstance(user_value, str) and user_value.isdigit())):
                     final_config[key] = _get_alignment_code_rl(user_value, str(default_value)) # default_value for alignment might be int
                elif (isinstance(default_value, float) and default_value > 0 and inch > 1 and
                      (key.startswith("page_margin") or "_space_" in key or "signature_image_" in key or "signature_section_" in key or "_indent" in key or "_leading" in key or "_padding" in key or "_thickness" in key or "_size" in key)):
                    parsed_user_value = _parse_numeric_value(str(user_value), default_value / inch if default_value > 10 else default_value) # Heuristic for inch vs points
                    if default_value > 10: # Likely an inch measurement
                        final_config[key] = parsed_user_value * inch
                    else: # Likely a point measurement
                        final_config[key] = parsed_user_value
                elif isinstance(default_value, (int, float)): # For other numeric values (font sizes, lengths)
                     final_config[key] = _parse_numeric_value(str(user_value), default_value)
                else:
                    final_config[key] = user_value
        else:
            logger.debug("No PDF style options provided, using defaults for PDF.")

        try:
            submission = FormSubmission.query.filter_by(id=submission_id, is_deleted=False).first()
            if not submission: return None, "Submission not found"
            form = Form.query.filter_by(id=submission.form_id, is_deleted=False).first()
            if not form: return None, "Form not found"

            buffer = io.BytesIO()
            doc_pdf = SimpleDocTemplate(buffer, pagesize=letter,
                                    rightMargin=final_config["page_margin_right"], leftMargin=final_config["page_margin_left"],
                                    topMargin=final_config["page_margin_top"], bottomMargin=final_config["page_margin_bottom"],
                                    title=f"Form Submission - {form.title}")
            styles_pdf = getSampleStyleSheet()

            styles_pdf.add(ReportLabParagraphStyle(name='CustomFormTitle', fontName=str(final_config["title_font_family"]), fontSize=final_config["title_font_size"], textColor=final_config["title_font_color"], alignment=_get_alignment_code_rl(final_config.get("title_alignment"), "CENTER"), spaceAfter=final_config["title_space_after"], leading=final_config["title_font_size"] * 1.2))
            styles_pdf.add(ReportLabParagraphStyle(name='CustomInfoLabel', fontName=str(final_config["info_label_font_family"]), fontSize=final_config["info_font_size"], textColor=final_config["info_font_color"]))
            styles_pdf.add(ReportLabParagraphStyle(name='CustomInfoValue', fontName=str(final_config["info_font_family"]), fontSize=final_config["info_font_size"], textColor=final_config["info_font_color"]))
            styles_pdf.add(ReportLabParagraphStyle(name='CustomQuestion', fontName=str(final_config["question_font_family"]), fontSize=final_config["question_font_size"], textColor=final_config["question_font_color"], leftIndent=final_config["question_left_indent"], spaceBefore=final_config["question_space_before"], spaceAfter=final_config["question_space_after"], leading=final_config["question_leading"]))
            styles_pdf.add(ReportLabParagraphStyle(name='CustomAnswer', fontName=str(final_config["answer_font_family"]), fontSize=final_config["answer_font_size"], textColor=final_config["answer_font_color"], leftIndent=final_config["answer_left_indent"], spaceBefore=final_config["answer_space_before"], spaceAfter=final_config["answer_space_after"], leading=final_config["answer_leading"]))
            styles_pdf.add(ReportLabParagraphStyle(name='CustomQACombined', fontName=str(final_config["question_font_family"]), fontSize=final_config["question_font_size"], textColor=final_config["question_font_color"], leftIndent=final_config["question_left_indent"], spaceBefore=final_config["question_space_before"], spaceAfter=final_config["answer_space_after"], leading=final_config["question_leading"]))
            styles_pdf.add(ReportLabParagraphStyle(name='CustomTableHeader', fontName=str(final_config["table_header_font_family"]), fontSize=final_config["table_header_font_size"], textColor=final_config["table_header_font_color"], backColor=final_config["table_header_bg_color"], alignment=_get_alignment_code_rl(final_config.get("table_header_alignment"), "CENTER"), leading=final_config["table_header_font_size"] * 1.2, leftPadding=final_config["table_header_padding"], rightPadding=final_config["table_header_padding"], topPadding=final_config["table_header_padding"], bottomPadding=final_config["table_header_padding"]))
            styles_pdf.add(ReportLabParagraphStyle(name='CustomTableCell', fontName=str(final_config["table_cell_font_family"]), fontSize=final_config["table_cell_font_size"], textColor=final_config["table_cell_font_color"], alignment=_get_alignment_code_rl(final_config.get("table_cell_alignment"), "LEFT"), leading=final_config["table_cell_font_size"] * 1.2, leftPadding=final_config["table_cell_padding"], rightPadding=final_config["table_cell_padding"], topPadding=final_config["table_cell_padding"], bottomPadding=final_config["table_cell_padding"]))
            styles_pdf.add(ReportLabParagraphStyle(name='CustomSignatureLabel', fontName=str(final_config["signature_label_font_family"]), fontSize=final_config["signature_label_font_size"], textColor=final_config["signature_label_font_color"], spaceBefore=final_config["signature_section_space_before"], spaceAfter=4, alignment=_get_alignment_code_rl("LEFT", "LEFT")))
            styles_pdf.add(ReportLabParagraphStyle(name='CustomSignatureText', fontName=str(final_config["signature_text_font_family"]), fontSize=final_config["signature_text_font_size"], textColor=final_config["signature_text_font_color"], leading=final_config["signature_text_font_size"] * 1.2, alignment=_get_alignment_code_rl("LEFT", "LEFT")))

            story: List[Flowable] = []
            page_content_width = doc_pdf.width

            if header_image:
                processed_image_io = ExportSubmissionService._process_header_image(header_image, header_opacity, header_size, header_width, header_height)
                if processed_image_io and hasattr(processed_image_io, 'img_width_px') and hasattr(processed_image_io, 'img_height_px'):
                    img_w_px = getattr(processed_image_io, 'img_width_px')
                    img_h_px = getattr(processed_image_io, 'img_height_px')
                    img_w_pt = img_w_px * (72.0/96.0) # Assuming image DPI, common screen DPI is 96
                    img_h_pt = img_h_px * (72.0/96.0)

                    if not header_width and not header_height and (header_size is None or header_size == 100) and img_w_pt > page_content_width:
                        scale_ratio = page_content_width / img_w_pt
                        img_w_pt *= scale_ratio
                        img_h_pt *= scale_ratio
                    processed_image_io.seek(0)
                    img_obj = ReportLabImage(processed_image_io, width=img_w_pt, height=img_h_pt) # opacity handled by _process_header_image for PDF
                    align_val_h = header_alignment.upper()
                    if align_val_h not in ['LEFT', 'CENTER', 'RIGHT']: align_val_h = 'CENTER'
                    header_img_table = ReportLabTable([[img_obj]], colWidths=[page_content_width])
                    header_img_table.setStyle(ReportLabTableStyle([('ALIGN', (0,0), (0,0), align_val_h), ('VALIGN', (0,0), (0,0), 'MIDDLE'), ('LEFTPADDING', (0,0), (0,0), 0), ('RIGHTPADDING', (0,0), (0,0), 0), ('TOPPADDING', (0,0), (0,0), 0), ('BOTTOMPADDING', (0,0), (0,0), 0)]))
                    story.append(header_img_table)
                    story.append(Spacer(1, 0.1 * inch))

            story.append(ReportLabParagraph(form.title, styles_pdf['CustomFormTitle']))
            if form.description: story.append(ReportLabParagraph(form.description, styles_pdf['Normal']))

            info_data_styled = [
                [ReportLabParagraph(f'<b>Submitted by:</b>', styles_pdf['CustomInfoLabel']), ReportLabParagraph(str(submission.submitted_by or 'N/A'), styles_pdf['CustomInfoValue'])],
                [ReportLabParagraph(f'<b>Date:</b>', styles_pdf['CustomInfoLabel']), ReportLabParagraph(submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if submission.submitted_at else 'N/A', styles_pdf['CustomInfoValue'])]
            ]
            info_table_styled = ReportLabTable(info_data_styled, colWidths=[1.5 * inch, None])
            info_table_styled.setStyle(ReportLabTableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 2)]))
            story.append(info_table_styled)
            story.append(Spacer(1, final_config["info_space_after"]))

            all_answers = AnswerSubmitted.query.filter_by(form_submission_id=submission_id, is_deleted=False).all()
            non_signature_answers = [a for a in all_answers if a.question_type and a.question_type.lower() != 'signature']

            table_pattern_re = re.compile(r'^(Table\s+\d+)(?:\s+(.*))?$')
            pattern_based_tables_data = defaultdict(lambda: {'headers': [], 'rows': defaultdict(dict), 'row_order': [], 'raw_json_csv_data': None})
            cell_based_tables_data = defaultdict(lambda: {'name': '', 'headers': {}, 'cells': {}, 'row_indices': set(), 'col_indices': set(), 'header_row_present': False})
            choice_answer_groups = defaultdict(list); regular_answers = []

            for ans in non_signature_answers:
                q_text = ans.question if ans.question else "Untitled Question"; ans_type = ans.question_type.lower() if ans.question_type else ""
                if ans_type == 'table' and ans.column is not None and ans.row is not None:
                    table_id = q_text; cell_based_tables_data[table_id]['name'] = table_id
                    current_data = ans.cell_content if ans.cell_content is not None else ans.answer
                    current_data_str = str(current_data) if current_data is not None else ""
                    if ans.row == 0:
                        cell_based_tables_data[table_id]['headers'][ans.column] = current_data_str
                        cell_based_tables_data[table_id]['col_indices'].add(ans.column); cell_based_tables_data[table_id]['header_row_present'] = True
                    elif ans.row > 0:
                        cell_based_tables_data[table_id]['cells'][(ans.row, ans.column)] = current_data_str
                        cell_based_tables_data[table_id]['row_indices'].add(ans.row); cell_based_tables_data[table_id]['col_indices'].add(ans.column)
                    continue
                match_obj = table_pattern_re.match(q_text)
                if match_obj:
                    table_name = match_obj.group(1); qualifier = match_obj.group(2) or ""
                    if qualifier.lower().startswith('column '):
                        try: col_num = int(qualifier.lower().replace('column ', '').strip()) - 1
                        except ValueError: col_num = len(pattern_based_tables_data[table_name]['headers'])
                        pattern_based_tables_data[table_name]['headers'].append((col_num, str(ans.answer or "")))
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
                if ans_type in choice_based_types: choice_answer_groups[q_text].append(ans); continue
                regular_answers.append(ans)

            qa_layout = str(final_config.get("qa_layout", "answer_below"))
            answer_same_line_max_len = int(final_config.get("answer_same_line_max_length", 70))
            answer_color_for_html = _color_to_hex_string_rl(final_config["answer_font_color"])

            for ans_item in sorted(regular_answers, key=lambda a: a.question or ""):
                q_text_p = str(ans_item.question or "Untitled Question")
                ans_val_p = str(ans_item.answer) if ans_item.answer is not None else "No answer provided"
                if qa_layout == "answer_same_line" and isinstance(ans_item.answer, str) and len(ans_val_p) <= answer_same_line_max_len and '\n' not in ans_val_p:
                    combined_text = f"<b>{q_text_p}:</b> <font color='{answer_color_for_html}'>{ans_val_p}</font>"
                    story.append(ReportLabParagraph(combined_text, styles_pdf['CustomQACombined']))
                else:
                    story.append(ReportLabParagraph(q_text_p, styles_pdf['CustomQuestion'])); story.append(ReportLabParagraph(ans_val_p, styles_pdf['CustomAnswer']))

            for q_text_choice, ans_list_choice in choice_answer_groups.items():
                q_text_c_p = str(q_text_choice); combined_options = []
                for choice_ans in ans_list_choice:
                    if choice_ans.answer is not None and str(choice_ans.answer).strip() != "":
                        try:
                            parsed_json_options = json.loads(choice_ans.answer)
                            if isinstance(parsed_json_options, list): combined_options.extend([str(item) for item in parsed_json_options if str(item).strip() != ""])
                            else:
                                if str(parsed_json_options).strip() != "": combined_options.append(str(parsed_json_options))
                        except json.JSONDecodeError:
                             if str(choice_ans.answer).strip() != "": combined_options.append(str(choice_ans.answer))
                unique_options = list(dict.fromkeys(filter(None, combined_options)))
                ans_val_c_p = ", ".join(unique_options) if unique_options else "No selection"
                if qa_layout == "answer_same_line" and len(ans_val_c_p) <= answer_same_line_max_len and '\n' not in ans_val_c_p:
                    combined_text_c = f"<b>{q_text_c_p}:</b> <font color='{answer_color_for_html}'>{ans_val_c_p}</font>"
                    story.append(ReportLabParagraph(combined_text_c, styles_pdf['CustomQACombined']))
                else:
                    story.append(ReportLabParagraph(q_text_c_p, styles_pdf['CustomQuestion'])); story.append(ReportLabParagraph(ans_val_c_p, styles_pdf['CustomAnswer']))

            table_cell_padding_val = final_config["table_cell_padding"]
            table_grid_color_val = final_config["table_grid_color"]
            table_grid_thickness_val = final_config["table_grid_thickness"]
            table_header_bg_color_val = final_config["table_header_bg_color"]

            for table_id_cb, content_cb in cell_based_tables_data.items():
                story.append(ReportLabParagraph(str(content_cb['name']), styles_pdf['CustomQuestion']))
                all_cols_indices = content_cb['col_indices']; sorted_cols = sorted(list(all_cols_indices))
                data_row_indices = sorted([r for r in content_cb['row_indices'] if r > 0])
                header_styled_row_cb: List[ReportLabParagraph] = []; actual_col_count_cb = len(sorted_cols)
                if content_cb['header_row_present']:
                    for col_idx in sorted_cols: header_styled_row_cb.append(ReportLabParagraph(str(content_cb['headers'].get(col_idx, f"Col {col_idx+1}")), styles_pdf['CustomTableHeader']))
                elif actual_col_count_cb > 0 and data_row_indices:
                    header_styled_row_cb = [ReportLabParagraph(f"Column {idx+1}", styles_pdf['CustomTableHeader']) for idx in sorted_cols]
                table_rows_styled_cb: List[List[ReportLabParagraph]] = []
                if header_styled_row_cb: table_rows_styled_cb.append(header_styled_row_cb)
                for data_row_idx in data_row_indices: table_rows_styled_cb.append([ReportLabParagraph(str(content_cb['cells'].get((data_row_idx, col_idx), "")), styles_pdf['CustomTableCell']) for col_idx in sorted_cols])
                if table_rows_styled_cb:
                    col_widths_cb_val = [page_content_width / actual_col_count_cb] * actual_col_count_cb if actual_col_count_cb > 0 else [page_content_width]
                    rl_table_cb = ReportLabTable(table_rows_styled_cb, colWidths=col_widths_cb_val, repeatRows=1 if header_styled_row_cb else 0)
                    style_cmds_cb_list = [('GRID', (0,0), (-1,-1), table_grid_thickness_val, table_grid_color_val), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (0,0), (-1,-1), table_cell_padding_val), ('RIGHTPADDING', (0,0), (-1,-1), table_cell_padding_val), ('TOPPADDING', (0,0), (-1,-1), table_cell_padding_val), ('BOTTOMPADDING', (0,0), (-1,-1), table_cell_padding_val)]
                    if header_styled_row_cb: style_cmds_cb_list.append(('BACKGROUND', (0,0), (-1,0), table_header_bg_color_val))
                    rl_table_cb.setStyle(ReportLabTableStyle(style_cmds_cb_list)); story.append(rl_table_cb); story.append(Spacer(1, 0.15*inch))
                elif header_styled_row_cb:
                    col_widths_cb_val_h = [page_content_width / actual_col_count_cb] * actual_col_count_cb if actual_col_count_cb > 0 else [page_content_width]
                    rl_table_cb_h = ReportLabTable([header_styled_row_cb], colWidths=col_widths_cb_val_h)
                    rl_table_cb_h.setStyle(ReportLabTableStyle([('GRID', (0,0), (-1,-1), table_grid_thickness_val, table_grid_color_val), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BACKGROUND', (0,0), (-1,0), table_header_bg_color_val), ('LEFTPADDING', (0,0), (-1,-1), table_cell_padding_val), ('RIGHTPADDING', (0,0), (-1,-1), table_cell_padding_val), ('TOPPADDING', (0,0), (-1,-1), table_cell_padding_val), ('BOTTOMPADDING', (0,0), (-1,-1), table_cell_padding_val)]))
                    story.append(rl_table_cb_h); story.append(Spacer(1, 0.15*inch))
                else: story.append(ReportLabParagraph("No data for this table.", styles_pdf['CustomAnswer']))

            for table_name_pb, info_pb in pattern_based_tables_data.items():
                story.append(ReportLabParagraph(str(table_name_pb), styles_pdf['CustomQuestion']))
                data_for_pb_table_styled: List[List[ReportLabParagraph]] = []
                if info_pb['raw_json_csv_data']:
                    raw_str = info_pb['raw_json_csv_data']
                    try:
                        parsed = json.loads(raw_str)
                        if isinstance(parsed, list) and parsed:
                            if isinstance(parsed[0], dict):
                                headers = list(parsed[0].keys()); data_for_pb_table_styled.append([ReportLabParagraph(str(h), styles_pdf['CustomTableHeader']) for h in headers])
                                for item_dict in parsed: data_for_pb_table_styled.append([ReportLabParagraph(str(item_dict.get(h, "")), styles_pdf['CustomTableCell']) for h in headers])
                            elif isinstance(parsed[0], list):
                                data_for_pb_table_styled.append([ReportLabParagraph(str(h_item), styles_pdf['CustomTableHeader']) for h_item in parsed[0]])
                                for r_item_list in parsed[1:]: data_for_pb_table_styled.append([ReportLabParagraph(str(c_item), styles_pdf['CustomTableCell']) for c_item in r_item_list])
                    except json.JSONDecodeError:
                        if '\n' in raw_str:
                            lines = [line.strip() for line in raw_str.strip().split('\n')]; sep = '~' if lines and '~' in lines[0] else ','
                            if lines:
                                data_for_pb_table_styled.append([ReportLabParagraph(str(h.strip()), styles_pdf['CustomTableHeader']) for h in lines[0].split(sep)])
                                for data_line in lines[1:]: data_for_pb_table_styled.append([ReportLabParagraph(str(c.strip()), styles_pdf['CustomTableCell']) for c in data_line.split(sep)])
                if not data_for_pb_table_styled:
                    headers_from_pattern = sorted(info_pb['headers'], key=lambda x: x[0]); header_texts = [h_text for _, h_text in headers_from_pattern]
                    current_max_cols = len(header_texts); rows_from_pattern_dict = info_pb['rows']
                    if rows_from_pattern_dict: current_max_cols = max(current_max_cols, max((max(r.keys()) + 1 if r else 0) for r in rows_from_pattern_dict.values()))
                    if not header_texts and current_max_cols > 0: header_texts = [f"Column {i+1}" for i in range(current_max_cols)]
                    if header_texts: data_for_pb_table_styled.append([ReportLabParagraph(str(h), styles_pdf['CustomTableHeader']) for h in header_texts])
                    for r_idx_pat in sorted(info_pb['row_order']):
                        r_data_pat = rows_from_pattern_dict.get(r_idx_pat, {})
                        data_for_pb_table_styled.append([ReportLabParagraph(str(r_data_pat.get(c_idx_pat, "")), styles_pdf['CustomTableCell']) for c_idx_pat in range(current_max_cols)])
                if data_for_pb_table_styled:
                    actual_cols_pb_val = len(data_for_pb_table_styled[0]) if data_for_pb_table_styled else 1
                    col_widths_pb_val = [page_content_width / actual_cols_pb_val] * actual_cols_pb_val if actual_cols_pb_val > 0 else [page_content_width]
                    rl_table_pb = ReportLabTable(data_for_pb_table_styled, colWidths=col_widths_pb_val, repeatRows=1)
                    style_cmds_pb_list = [('GRID', (0,0), (-1,-1), table_grid_thickness_val, table_grid_color_val), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BACKGROUND', (0,0), (-1,0), table_header_bg_color_val), ('LEFTPADDING', (0,0), (-1,-1), table_cell_padding_val), ('RIGHTPADDING', (0,0), (-1,-1), table_cell_padding_val), ('TOPPADDING', (0,0), (-1,-1), table_cell_padding_val), ('BOTTOMPADDING', (0,0), (-1,-1), table_cell_padding_val)]
                    rl_table_pb.setStyle(ReportLabTableStyle(style_cmds_pb_list)); story.append(rl_table_pb); story.append(Spacer(1, 0.15*inch))
                else: story.append(ReportLabParagraph("No data available for this table.", styles_pdf['CustomAnswer']))

            if include_signatures:
                sig_attachments = Attachment.query.filter_by(form_submission_id=submission_id, is_signature=True, is_deleted=False).all()
                if sig_attachments:
                    story.append(ReportLabParagraph("Signatures:", styles_pdf['CustomSignatureLabel'])); story.append(Spacer(1, 0.05 * inch))
                    sig_scale = signatures_size / 100.0
                    sig_img_w_conf = final_config["signature_image_width"] * sig_scale
                    sig_img_h_conf = final_config["signature_image_height"] * sig_scale
                    if signatures_alignment.lower() == "horizontal" and len(sig_attachments) > 1:
                        effective_sig_width = sig_img_w_conf + (0.2 * inch)
                        max_sigs_per_row = int(page_content_width / effective_sig_width) if effective_sig_width > 0 else 1
                        max_sigs_per_row = max(1, min(max_sigs_per_row, len(sig_attachments), 4))
                        sig_rows_data_list = []; current_sig_row_items_list = []
                        for idx, att in enumerate(sig_attachments):
                            sig_block_elements_list: List[Flowable] = []; file_path = os.path.join(upload_path, att.file_path); sig_author = att.signature_author or "N/A"; sig_position = att.signature_position or "N/A"
                            if os.path.exists(file_path):
                                try: sig_block_elements_list.append(ReportLabImage(file_path, width=sig_img_w_conf, height=sig_img_h_conf))
                                except Exception: sig_block_elements_list.append(ReportLabParagraph("<i>[Image Error]</i>", styles_pdf['CustomSignatureText']))
                            else: sig_block_elements_list.append(ReportLabParagraph("<i>[Image Missing]</i>", styles_pdf['CustomSignatureText']))
                            sig_block_elements_list.append(Spacer(1,2)); sig_block_elements_list.append(ReportLabParagraph("<b>___________________________</b>", styles_pdf['CustomSignatureText'])); sig_block_elements_list.append(ReportLabParagraph(f"<b>Signed by:</b> {sig_author}", styles_pdf['CustomSignatureText'])); sig_block_elements_list.append(ReportLabParagraph(f"<b>Position:</b> {sig_position}", styles_pdf['CustomSignatureText']))
                            current_sig_row_items_list.append(sig_block_elements_list)
                            if len(current_sig_row_items_list) == max_sigs_per_row or idx == len(sig_attachments) - 1:
                                sig_rows_data_list.append(current_sig_row_items_list); current_sig_row_items_list = []
                        for sig_row_group_list in sig_rows_data_list:
                            if not sig_row_group_list: continue
                            col_w_sig_val = page_content_width / len(sig_row_group_list)
                            sig_table_this_row = ReportLabTable([sig_row_group_list], colWidths=[col_w_sig_val]*len(sig_row_group_list))
                            sig_table_this_row.setStyle(ReportLabTableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 2), ('RIGHTPADDING', (0,0), (-1,-1), 2)]))
                            story.append(sig_table_this_row); story.append(Spacer(1, 0.1*inch))
                    else:
                        for att in sig_attachments:
                            file_path = os.path.join(upload_path, att.file_path); sig_author_v = att.signature_author or "N/A"; sig_position_v = att.signature_position or "N/A"
                            if os.path.exists(file_path):
                                try: story.append(ReportLabImage(file_path, width=sig_img_w_conf, height=sig_img_h_conf))
                                except Exception: story.append(ReportLabParagraph("<i>[Signature Image Error]</i>", styles_pdf['CustomSignatureText']))
                            else: story.append(ReportLabParagraph("<i>[Signature Image Missing]</i>", styles_pdf['CustomSignatureText']))
                            story.append(Spacer(1,2)); story.append(ReportLabParagraph("<b>___________________________</b>", styles_pdf['CustomSignatureText'])); story.append(ReportLabParagraph(f"<b>Signed by:</b> {sig_author_v}", styles_pdf['CustomSignatureText'])); story.append(ReportLabParagraph(f"<b>Position:</b> {sig_position_v}", styles_pdf['CustomSignatureText'])); story.append(Spacer(1, final_config["signature_space_between_vertical"]))

            doc_pdf.build(story)
            buffer.seek(0)
            return buffer, None
        except Exception as e:
            logger.error(f"Error exporting structured submission to PDF: {submission_id} - {str(e)}", exc_info=True)
            return None, f"An error occurred during PDF generation: {str(e)}"

    @staticmethod
    def export_submission_to_pdf( # This is the simpler export, now also capable of using styles
        submission_id: int, upload_path: str,
        include_signatures: bool = True,
        header_image: Optional[FileStorage] = None,
        header_opacity: float = 1.0,
        header_size: Optional[float] = None,
        header_width: Optional[float] = None,
        header_height: Optional[float] = None,
        header_alignment: str = "center",
        signatures_size: float = 100,
        signatures_alignment: str = "vertical",
        pdf_style_options: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[BytesIO], Optional[str]]:
        logger.info(f"Calling export_structured_submission_to_pdf (as unified method) for submission_id: {submission_id}")
        return ExportSubmissionService.export_structured_submission_to_pdf(
            submission_id=submission_id,
            upload_path=upload_path,
            pdf_style_options=pdf_style_options,
            header_image=header_image,
            header_opacity=header_opacity,
            header_size=header_size,
            header_width=header_width,
            header_height=header_height,
            header_alignment=header_alignment,
            include_signatures=include_signatures,
            signatures_size=signatures_size,
            signatures_alignment=signatures_alignment
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
                except Exception as e_sig:
                    logger.warning(f"Could not parse signature metadata from filename '{attachment_item.file_path}': {str(e_sig)}")
            signatures_list.append({
                "path": file_path_item,
                "position": sig_pos_item or "Signature",
                "author": sig_auth_item or "Signer",
                "exists": exists_bool
            })
        return signatures_list

    # --- NEW DOCX EXPORT METHOD ---
    @staticmethod
    def export_submission_to_docx(
        submission_id: int,
        upload_path: str,
        style_options: Optional[Dict[str, Any]] = None, # Generic style options
        header_image_file: Optional[FileStorage] = None,
        header_size_percent: Optional[float] = None, # Percentage
        header_width_px: Optional[float] = None, # Pixels
        header_height_px: Optional[float] = None, # Pixels
        header_alignment_str: str = "center",
        include_signatures: bool = True,
        signatures_size_percent: float = 100, # Percentage
        signatures_alignment_str: str = "vertical"
    ) -> Tuple[Optional[BytesIO], Optional[str]]:
        """
        Exports a form submission to a DOCX document.
        """
        style_options = style_options or {}
        logger.info(f"Starting DOCX export for submission ID: {submission_id} with options: {style_options}")

        try:
            submission = FormSubmission.query.filter_by(id=submission_id, is_deleted=False).first()
            if not submission:
                return None, "Submission not found"
            form = Form.query.filter_by(id=submission.form_id, is_deleted=False).first()
            if not form:
                return None, "Form not found"

            doc = Document()
            # Set default font for the document (optional, can be based on style_options)
            # doc.styles['Normal'].font.name = style_options.get('default_font_family', 'Calibri')
            # doc.styles['Normal'].font.size = Pt(int(style_options.get('default_font_size', 11)))

            # --- Header Image ---
            if header_image_file:
                processed_image_io = ExportSubmissionService._process_header_image(
                    header_image_file,
                    size=header_size_percent,
                    width_px=header_width_px,
                    height_px=header_height_px
                )
                if processed_image_io and hasattr(processed_image_io, 'img_width_px') and hasattr(processed_image_io, 'img_height_px'):
                    img_width_px = getattr(processed_image_io, 'img_width_px')
                    # Convert pixels to inches for DOCX (assuming 96 DPI for pixel conversion)
                    img_width_inches = img_width_px / 96.0
                    processed_image_io.seek(0)
                    # Add picture with alignment
                    p_header_img = doc.add_paragraph()
                    run_header_img = p_header_img.add_run()
                    run_header_img.add_picture(processed_image_io, width=Inches(img_width_inches))
                    docx_header_align = _get_docx_alignment(header_alignment_str)
                    if docx_header_align:
                        p_header_img.alignment = docx_header_align
                    doc.add_paragraph() # Spacer

            # --- Title and Description ---
            title_p = doc.add_heading(form.title, level=1)
            title_align = _get_docx_alignment(style_options.get("title_alignment", "CENTER")) # Example: get from style_options
            if title_align: title_p.alignment = title_align
            # You can further style title_p.runs[0].font here based on style_options

            if form.description:
                desc_p = doc.add_paragraph(form.description)
                # Style desc_p as needed

            doc.add_paragraph() # Spacer

            # --- Submission Info ---
            info_table = doc.add_table(rows=2, cols=2)
            info_table.cell(0, 0).text = "Submitted by:"
            info_table.cell(0, 1).text = str(submission.submitted_by or 'N/A')
            info_table.cell(1, 0).text = "Date:"
            info_table.cell(1, 1).text = submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if submission.submitted_at else 'N/A'
            # Style info_table cells (bold labels, etc.)
            for i in range(2): # Bold labels
                 info_table.cell(i,0).paragraphs[0].runs[0].bold = True
            info_table.autofit = True # Optional: try to fit content
            doc.add_paragraph() # Spacer

            # --- Answers ---
            all_answers = AnswerSubmitted.query.filter_by(form_submission_id=submission_id, is_deleted=False).all()
            non_signature_answers = [a for a in all_answers if a.question_type and a.question_type.lower() != 'signature']

            # Prepare data structures (similar to PDF)
            table_pattern_re = re.compile(r'^(Table\s+\d+)(?:\s+(.*))?$')
            pattern_based_tables_data = defaultdict(lambda: {'name': '', 'headers': [], 'rows': defaultdict(dict), 'row_order': [], 'raw_json_csv_data': None})
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
                    if ans.row == 0: # Header row
                        cell_based_tables_data[table_id]['headers'][ans.column] = current_data_str
                        cell_based_tables_data[table_id]['col_indices'].add(ans.column)
                        cell_based_tables_data[table_id]['header_row_present'] = True
                    elif ans.row > 0: # Data row
                        cell_based_tables_data[table_id]['cells'][(ans.row, ans.column)] = current_data_str
                        cell_based_tables_data[table_id]['row_indices'].add(ans.row)
                        cell_based_tables_data[table_id]['col_indices'].add(ans.column)
                    continue

                match_obj = table_pattern_re.match(q_text)
                if match_obj:
                    table_name_str = match_obj.group(1)
                    pattern_based_tables_data[table_name_str]['name'] = table_name_str # Store the name
                    qualifier = match_obj.group(2) or ""
                    if qualifier.lower().startswith('column '):
                        try: col_num = int(qualifier.lower().replace('column ', '').strip()) - 1
                        except ValueError: col_num = len(pattern_based_tables_data[table_name_str]['headers'])
                        pattern_based_tables_data[table_name_str]['headers'].append((col_num, str(ans.answer or "")))
                    elif qualifier.lower().startswith('row '):
                        try:
                            row_parts = qualifier.lower().replace('row ', '').strip().split('.')
                            if len(row_parts) == 2:
                                row_num = int(row_parts[0]) - 1; col_num = int(row_parts[1]) - 1
                                if row_num not in pattern_based_tables_data[table_name_str]['row_order']:
                                    pattern_based_tables_data[table_name_str]['row_order'].append(row_num)
                                pattern_based_tables_data[table_name_str]['rows'][row_num][col_num] = str(ans.answer or "")
                        except (ValueError, IndexError): regular_answers.append(ans)
                    elif ans.answer:
                        pattern_based_tables_data[table_name_str]['raw_json_csv_data'] = ans.answer
                    else:
                        if ans.answer: regular_answers.append(ans)
                    continue

                choice_based_types = ['dropdown', 'select', 'multiselect', 'checkbox', 'multiple_choices', 'single_choice']
                if ans_type in choice_based_types:
                    choice_answer_groups[q_text].append(ans)
                    continue
                regular_answers.append(ans)

            # --- Render Regular Answers ---
            for ans_item in sorted(regular_answers, key=lambda a: a.question or ""):
                q_p = doc.add_paragraph()
                q_run = q_p.add_run(str(ans_item.question or "Untitled Question"))
                q_run.bold = True
                # Apply font styles from style_options if available
                # q_run.font.name = style_options.get('question_font_family', 'Calibri')
                # q_run.font.size = Pt(int(style_options.get('question_font_size', 11)))

                ans_val_p = str(ans_item.answer) if ans_item.answer is not None else "No answer provided"
                a_p = doc.add_paragraph(ans_val_p)
                a_p.paragraph_format.left_indent = Inches(0.25) # Indent answer
                # Apply font styles for answer
                doc.add_paragraph() # Spacer

            # --- Render Choice Answers ---
            for q_text_choice, ans_list_choice in choice_answer_groups.items():
                q_p = doc.add_paragraph()
                q_run = q_p.add_run(str(q_text_choice))
                q_run.bold = True

                combined_options = []
                for choice_ans in ans_list_choice:
                    if choice_ans.answer is not None and str(choice_ans.answer).strip() != "":
                        try:
                            parsed_json_options = json.loads(choice_ans.answer)
                            if isinstance(parsed_json_options, list):
                                combined_options.extend([str(item) for item in parsed_json_options if str(item).strip()])
                            elif str(parsed_json_options).strip():
                                combined_options.append(str(parsed_json_options))
                        except json.JSONDecodeError:
                            if str(choice_ans.answer).strip():
                                combined_options.append(str(choice_ans.answer))
                unique_options = list(dict.fromkeys(filter(None, combined_options)))
                ans_val_c_p = ", ".join(unique_options) if unique_options else "No selection"
                a_p = doc.add_paragraph(ans_val_c_p)
                a_p.paragraph_format.left_indent = Inches(0.25)
                doc.add_paragraph() # Spacer

            # --- Render Cell-Based Tables ---
            for table_id_cb, content_cb in cell_based_tables_data.items():
                doc.add_paragraph(str(content_cb['name']), style='Heading2') # Or add_run with bold
                sorted_cols = sorted(list(content_cb['col_indices']))
                data_row_indices = sorted([r for r in content_cb['row_indices'] if r > 0])
                num_cols = len(sorted_cols)
                num_data_rows = len(data_row_indices)
                has_header = content_cb['header_row_present'] or (num_cols > 0 and num_data_rows > 0) # Infer header if data exists

                if num_cols == 0 and not data_row_indices:
                    doc.add_paragraph("No data for this table.")
                    continue

                # Create table
                docx_table = doc.add_table(rows= (1 if has_header else 0) + num_data_rows, cols=num_cols if num_cols > 0 else 1)
                docx_table.style = 'TableGrid' # Apply a basic grid style
                docx_table.alignment = WD_TABLE_ALIGNMENT.CENTER # Center table on page

                # Populate header
                if has_header:
                    for c_idx, actual_col_idx in enumerate(sorted_cols):
                        cell = docx_table.cell(0, c_idx)
                        cell.text = str(content_cb['headers'].get(actual_col_idx, f"Column {actual_col_idx + 1}"))
                        cell.paragraphs[0].runs[0].bold = True
                        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                        # Optional: cell background color from style_options
                        # bg_color_hex = style_options.get("table_header_bg_color_hex") # e.g. "#D9D9D9"
                        # if bg_color_hex: _set_cell_background_color(cell, bg_color_hex)


                # Populate data rows
                for r_idx, actual_row_idx in enumerate(data_row_indices):
                    table_row_idx = (1 if has_header else 0) + r_idx
                    for c_idx, actual_col_idx in enumerate(sorted_cols):
                        cell_content_str = str(content_cb['cells'].get((actual_row_idx, actual_col_idx), ""))
                        cell = docx_table.cell(table_row_idx, c_idx)
                        cell.text = cell_content_str
                        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                doc.add_paragraph()

            # --- Render Pattern-Based Tables (and raw JSON/CSV) ---
            for table_name_pb, info_pb in pattern_based_tables_data.items():
                doc.add_paragraph(str(info_pb.get('name', table_name_pb)), style='Heading2')
                table_data_list: List[List[str]] = [] # List of lists of strings

                if info_pb['raw_json_csv_data']:
                    raw_str = info_pb['raw_json_csv_data']
                    try:
                        parsed = json.loads(raw_str)
                        if isinstance(parsed, list) and parsed:
                            if isinstance(parsed[0], dict):
                                headers = list(parsed[0].keys())
                                table_data_list.append(headers)
                                for item_dict in parsed:
                                    table_data_list.append([str(item_dict.get(h, "")) for h in headers])
                            elif isinstance(parsed[0], list):
                                table_data_list = [[str(cell) for cell in row] for row in parsed]
                    except json.JSONDecodeError:
                        if '\n' in raw_str:
                            lines = [line.strip() for line in raw_str.strip().split('\n')]
                            sep = '~' if lines and '~' in lines[0] else ','
                            if lines:
                                table_data_list = [[c.strip() for c in line.split(sep)] for line in lines]
                if not table_data_list:
                    headers_from_pattern = sorted(info_pb['headers'], key=lambda x: x[0])
                    header_texts = [h_text for _, h_text in headers_from_pattern]
                    current_max_cols = len(header_texts)
                    rows_from_pattern_dict = info_pb['rows']
                    if rows_from_pattern_dict:
                        current_max_cols = max(current_max_cols, max((max(r.keys()) + 1 if r else 0) for r in rows_from_pattern_dict.values()))
                    if not header_texts and current_max_cols > 0:
                        header_texts = [f"Column {i+1}" for i in range(current_max_cols)]
                    if header_texts: table_data_list.append(header_texts)
                    for r_idx_pat in sorted(info_pb['row_order']):
                        r_data_pat = rows_from_pattern_dict.get(r_idx_pat, {})
                        table_data_list.append([str(r_data_pat.get(c_idx_pat, "")) for c_idx_pat in range(current_max_cols)])

                if table_data_list:
                    num_rows = len(table_data_list)
                    num_cols = len(table_data_list[0]) if num_rows > 0 else 0
                    if num_rows > 0 and num_cols > 0:
                        docx_table_pb = doc.add_table(rows=num_rows, cols=num_cols)
                        docx_table_pb.style = 'TableGrid'
                        docx_table_pb.alignment = WD_TABLE_ALIGNMENT.CENTER
                        for r, row_data in enumerate(table_data_list):
                            for c, cell_data in enumerate(row_data):
                                cell = docx_table_pb.cell(r, c)
                                cell.text = cell_data
                                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                                if r == 0: # Header row
                                    cell.paragraphs[0].runs[0].bold = True
                                    cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                        doc.add_paragraph()
                else:
                    doc.add_paragraph("No data available for this table.")


            # --- Signatures ---
            if include_signatures:
                sig_attachments = ExportSubmissionService._get_signature_images(submission_id, upload_path)
                if sig_attachments:
                    doc.add_paragraph("Signatures:", style='Heading2')
                    sig_img_width_default_inches = _parse_numeric_value(style_options.get("signature_image_width"), 2.0) # Default 2 inches
                    sig_img_height_default_inches = _parse_numeric_value(style_options.get("signature_image_height"), 0.8) # Default 0.8 inches

                    sig_scale = signatures_size_percent / 100.0
                    sig_img_width_final_inches = sig_img_width_default_inches * sig_scale
                    # Height can be omitted in add_picture to maintain aspect ratio based on width

                    if signatures_alignment_str.lower() == "horizontal" and len(sig_attachments) > 1:
                        # For DOCX, horizontal layout is trickier. Using a table for horizontal alignment.
                        # Estimate how many can fit. A 6-inch wide page content area.
                        max_sigs_per_row = max(1, int(6.0 / (sig_img_width_final_inches + 0.5))) # +0.5 for spacing
                        max_sigs_per_row = min(max_sigs_per_row, len(sig_attachments), 3) # Cap at 3-4 for readability

                        sig_table = doc.add_table(rows=0, cols=max_sigs_per_row) # Add rows dynamically
                        sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
                        current_row_cells = []

                        for att in sig_attachments:
                            if not current_row_cells: # Start a new row in the table
                                current_row_cells = sig_table.add_row().cells

                            cell_idx = len(sig_table.rows[-1].cells) - len(current_row_cells)
                            cell = current_row_cells[cell_idx]

                            if att["exists"]:
                                try:
                                    cell.add_paragraph().add_run().add_picture(att["path"], width=Inches(sig_img_width_final_inches))
                                except Exception as e_img:
                                    logger.error(f"Error adding signature image {att['path']} to DOCX: {e_img}")
                                    cell.add_paragraph("<i>[Image Error]</i>")
                            else:
                                cell.add_paragraph("<i>[Image Missing]</i>")
                            cell.add_paragraph("___________________________")
                            cell.add_paragraph(f"Signed by: {att['author']}").runs[0].font.size = Pt(9)
                            cell.add_paragraph(f"Position: {att['position']}").runs[0].font.size = Pt(9)
                            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER # Center image if possible by centering paragraph
                            
                            # Remove the used cell from current_row_cells
                            current_row_cells = current_row_cells[1:] if len(current_row_cells) > 1 else []
                        doc.add_paragraph()

                    else: # Vertical alignment
                        for att in sig_attachments:
                            p_sig_img = doc.add_paragraph()
                            if att["exists"]:
                                try:
                                    p_sig_img.add_run().add_picture(att["path"], width=Inches(sig_img_width_final_inches))
                                except Exception as e_img:
                                    logger.error(f"Error adding signature image {att['path']} to DOCX: {e_img}")
                                    doc.add_paragraph("<i>[Image Error]</i>")
                            else:
                                doc.add_paragraph("<i>[Image Missing]</i>")
                            p_sig_img.alignment = WD_ALIGN_PARAGRAPH.CENTER # Center image
                            doc.add_paragraph("___________________________", alignment=WD_ALIGN_PARAGRAPH.CENTER)
                            doc.add_paragraph(f"Signed by: {att['author']}", alignment=WD_ALIGN_PARAGRAPH.CENTER).runs[0].font.size = Pt(9)
                            doc.add_paragraph(f"Position: {att['position']}", alignment=WD_ALIGN_PARAGRAPH.CENTER).runs[0].font.size = Pt(9)
                            doc.add_paragraph() # Spacer

            # --- Save DOCX to buffer ---
            buffer = io.BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            return buffer, None

        except Exception as e:
            logger.error(f"Error exporting submission {submission_id} to DOCX: {str(e)}", exc_info=True)
            return None, f"An error occurred during DOCX generation: {str(e)}"

