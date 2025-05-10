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
from reportlab.lib.units import inch # pt is removed
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Flowable
from PIL import Image as PILImage # type: ignore
from reportlab.lib.utils import ImageReader # type: ignore
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

logger = logging.getLogger(__name__)

# --- Default Style Configuration ---
# Point-based values are now simple numbers. ReportLab styles will interpret them as points.
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
    "title_font_size": 18, # Points
    "title_font_color": colors.black,
    "title_alignment": 1, # 0=left, 1=center, 2=right, 4=justify
    "title_space_after": 0.25 * inch,

    # Submission Info (Submitted by, Date)
    "info_font_family": "Helvetica",
    "info_font_size": 10, # Points
    "info_font_color": colors.darkslategray,
    "info_label_font_family": "Helvetica-Bold",
    "info_space_after": 0.2 * inch,

    # Question
    "question_font_family": "Helvetica-Bold",
    "question_font_size": 11, # Points
    "question_font_color": colors.black,
    "question_left_indent": 0, # Points
    "question_space_before": 0.15 * inch,
    "question_space_after": 4, # Points
    "question_leading": 14, # Points

    # Answer
    "answer_font_family": "Helvetica",
    "answer_font_size": 10, # Points
    "answer_font_color": colors.darkslategray,
    "answer_left_indent": 15, # Points
    "answer_space_before": 2, # Points
    "answer_space_after": 0.15 * inch,
    "answer_leading": 12, # Points
    "qa_layout": "answer_below",
    "answer_same_line_max_length": 70,

    # Table Header
    "table_header_font_family": "Helvetica-Bold",
    "table_header_font_size": 9, # Points
    "table_header_font_color": colors.black,
    "table_header_bg_color": colors.lightgrey,
    "table_header_padding": 3, # Points
    "table_header_alignment": "CENTER", # For ParagraphStyle: LEFT, CENTER, RIGHT, JUSTIFY

    # Table Cell
    "table_cell_font_family": "Helvetica",
    "table_cell_font_size": 8, # Points
    "table_cell_font_color": colors.black,
    "table_cell_padding": 3, # Points
    "table_cell_alignment": "LEFT", # For ParagraphStyle: LEFT, CENTER, RIGHT, JUSTIFY
    "table_grid_color": colors.grey,
    "table_grid_thickness": 0.5, # Points

    # Signatures
    "signature_label_font_family": "Helvetica-Bold",
    "signature_label_font_size": 12, # Points
    "signature_label_font_color": colors.black,
    "signature_text_font_family": "Helvetica",
    "signature_text_font_size": 9, # Points
    "signature_text_font_color": colors.black,
    "signature_image_width": 2.0 * inch,
    "signature_image_height": 0.8 * inch,
    "signature_section_space_before": 0.3 * inch,
    "signature_space_between_vertical": 0.2 * inch,
}

def _get_color(color_input: Any, default_color: colors.Color) -> colors.Color:
    if isinstance(color_input, colors.Color):
        return color_input
    if isinstance(color_input, str):
        try:
            if color_input.startswith("#"):
                return colors.HexColor(color_input)
            return getattr(colors, color_input.lower(), default_color)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid color string '{color_input}'. Using default.")
            return default_color
    logger.warning(f"Invalid color type '{type(color_input)}'. Using default.")
    return default_color

def _parse_numeric_value(value_str: Optional[str], default_numeric_value: float) -> float:
    """Safely parses a string to a float, returning default if None or invalid."""
    if value_str is None:
        return default_numeric_value
    try:
        return float(value_str)
    except (ValueError, TypeError):
        logger.warning(f"Invalid numeric value string '{value_str}'. Using default {default_numeric_value}.")
        return default_numeric_value

def _get_alignment_code(align_str: Optional[str], default_align_str: str) -> int:
    """Converts alignment string (LEFT, CENTER, RIGHT, JUSTIFY) to ReportLab integer code."""
    effective_align_str = (align_str or default_align_str).upper()
    if effective_align_str == "LEFT": return 0
    if effective_align_str == "CENTER": return 1
    if effective_align_str == "RIGHT": return 2
    if effective_align_str == "JUSTIFY": return 4
    logger.warning(f"Invalid alignment string '{align_str}'. Using default '{default_align_str}'.")
    # Fallback to default if string is unrecognized
    if default_align_str.upper() == "LEFT": return 0
    if default_align_str.upper() == "CENTER": return 1
    if default_align_str.upper() == "RIGHT": return 2
    if default_align_str.upper() == "JUSTIFY": return 4
    return 1 # Absolute default: Center

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
            if img.mode != 'RGBA': img = img.convert('RGBA')
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
        header_image: Optional[FileStorage] = None, header_opacity: float = 1.0,
        header_size: Optional[float] = None, header_width: Optional[float] = None, header_height: Optional[float] = None,
        header_alignment: str = "center",
        include_signatures: bool = True, signatures_size: float = 100, signatures_alignment: str = "vertical"
    ) -> Tuple[Optional[BytesIO], Optional[str]]:
        
        # Initialize final config with defaults
        final_config = DEFAULT_STYLE_CONFIG.copy()

        # Merge user-provided options
        if pdf_style_options:
            for key, user_value in pdf_style_options.items():
                if user_value is None: continue # Skip if user explicitly passed None (or it wasn't set)

                default_value = DEFAULT_STYLE_CONFIG.get(key)
                
                if key.endswith("_color"):
                    final_config[key] = _get_color(user_value, default_value)
                elif key.endswith("_font_family") or key.endswith("_layout") or key.endswith("_alignment"): # String based like alignments for table style
                    final_config[key] = str(user_value)
                elif isinstance(default_value, float) and default_value > 0 and inch > 1 and (key.startswith("page_margin") or key.endswith("_space_after") or key.endswith("_space_before") or key.startswith("signature_image") or key.startswith("signature_section") or key.startswith("signature_space")):
                    # These are inch based values in default config
                    final_config[key] = _parse_numeric_value(str(user_value), default_value / inch) * inch
                else: # Assumed to be point-based numeric values
                    final_config[key] = _parse_numeric_value(str(user_value), default_value)
        
        try:
            submission = FormSubmission.query.filter_by(id=submission_id, is_deleted=False).first()
            if not submission: return None, "Submission not found"
            form = Form.query.filter_by(id=submission.form_id, is_deleted=False).first()
            if not form: return None, "Form not found"

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter,
                                    rightMargin=final_config["page_margin_right"], leftMargin=final_config["page_margin_left"],
                                    topMargin=final_config["page_margin_top"], bottomMargin=final_config["page_margin_bottom"],
                                    title=f"Form Submission - {form.title}")

            styles = getSampleStyleSheet()
            
            styles.add(ParagraphStyle(name='CustomFormTitle', fontName=final_config["title_font_family"], fontSize=final_config["title_font_size"],
                                      textColor=final_config["title_font_color"], alignment=_get_alignment_code(str(final_config.get("title_alignment")), "CENTER"),
                                      spaceAfter=final_config["title_space_after"], leading=final_config["title_font_size"] * 1.2))
            styles.add(ParagraphStyle(name='CustomInfoLabel', fontName=final_config["info_label_font_family"], fontSize=final_config["info_font_size"], textColor=final_config["info_font_color"]))
            styles.add(ParagraphStyle(name='CustomInfoValue', fontName=final_config["info_font_family"], fontSize=final_config["info_font_size"], textColor=final_config["info_font_color"]))
            styles.add(ParagraphStyle(name='CustomQuestion', fontName=final_config["question_font_family"], fontSize=final_config["question_font_size"],
                                      textColor=final_config["question_font_color"], leftIndent=final_config["question_left_indent"],
                                      spaceBefore=final_config["question_space_before"], spaceAfter=final_config["question_space_after"], leading=final_config["question_leading"]))
            styles.add(ParagraphStyle(name='CustomAnswer', fontName=final_config["answer_font_family"], fontSize=final_config["answer_font_size"],
                                      textColor=final_config["answer_font_color"], leftIndent=final_config["answer_left_indent"],
                                      spaceBefore=final_config["answer_space_before"], spaceAfter=final_config["answer_space_after"], leading=final_config["answer_leading"]))
            styles.add(ParagraphStyle(name='CustomQACombined', fontName=final_config["question_font_family"], fontSize=final_config["question_font_size"],
                                      textColor=final_config["question_font_color"], leftIndent=final_config["question_left_indent"],
                                      spaceBefore=final_config["question_space_before"], spaceAfter=final_config["answer_space_after"], leading=final_config["question_leading"]))
            styles.add(ParagraphStyle(name='CustomTableHeader', fontName=final_config["table_header_font_family"], fontSize=final_config["table_header_font_size"],
                                      textColor=final_config["table_header_font_color"], backColor=final_config["table_header_bg_color"],
                                      alignment=_get_alignment_code(final_config.get("table_header_alignment"), "CENTER"),
                                      leading=final_config["table_header_font_size"] * 1.2,
                                      leftPadding=final_config["table_header_padding"], rightPadding=final_config["table_header_padding"],
                                      topPadding=final_config["table_header_padding"], bottomPadding=final_config["table_header_padding"]))
            styles.add(ParagraphStyle(name='CustomTableCell', fontName=final_config["table_cell_font_family"], fontSize=final_config["table_cell_font_size"],
                                      textColor=final_config["table_cell_font_color"],
                                      alignment=_get_alignment_code(final_config.get("table_cell_alignment"), "LEFT"),
                                      leading=final_config["table_cell_font_size"] * 1.2,
                                      leftPadding=final_config["table_cell_padding"], rightPadding=final_config["table_cell_padding"],
                                      topPadding=final_config["table_cell_padding"], bottomPadding=final_config["table_cell_padding"]))
            styles.add(ParagraphStyle(name='CustomSignatureLabel', fontName=final_config["signature_label_font_family"], fontSize=final_config["signature_label_font_size"],
                                      textColor=final_config["signature_label_font_color"], spaceBefore=final_config["signature_section_space_before"],
                                      spaceAfter=4, alignment=0)) # 4 points
            styles.add(ParagraphStyle(name='CustomSignatureText', fontName=final_config["signature_text_font_family"], fontSize=final_config["signature_text_font_size"],
                                      textColor=final_config["signature_text_font_color"], leading=final_config["signature_text_font_size"] * 1.2, alignment=0))

            story: List[Flowable] = []
            page_content_width = doc.width 

            if header_image:
                processed_image_io = ExportSubmissionService._process_header_image(header_image, header_opacity, header_size, header_width, header_height)
                if processed_image_io and hasattr(processed_image_io, 'img_width') and hasattr(processed_image_io, 'img_height'):
                    img_w_attr = getattr(processed_image_io, 'img_width'); img_h_attr = getattr(processed_image_io, 'img_height')
                    if not header_width and not header_height and not header_size and img_w_attr > page_content_width:
                        scale_ratio = page_content_width / img_w_attr; img_w_attr *= scale_ratio; img_h_attr *= scale_ratio
                    img_obj = Image(processed_image_io, width=img_w_attr, height=img_h_attr)
                    align_val_h = header_alignment.upper()
                    if align_val_h not in ['LEFT', 'CENTER', 'RIGHT']: align_val_h = 'CENTER'
                    header_img_table = Table([[img_obj]], colWidths=[page_content_width])
                    header_img_table.setStyle(TableStyle([('ALIGN', (0,0), (0,0), align_val_h), ('VALIGN', (0,0), (0,0), 'MIDDLE'),
                                                       ('LEFTPADDING', (0,0), (0,0), 0), ('RIGHTPADDING', (0,0), (0,0), 0),
                                                       ('TOPPADDING', (0,0), (0,0), 0), ('BOTTOMPADDING', (0,0), (0,0), 0)]))
                    story.append(header_img_table); story.append(Spacer(1, 0.1 * inch))

            story.append(Paragraph(form.title, styles['CustomFormTitle']))
            if form.description: story.append(Paragraph(form.description, styles['Normal']))
            
            info_data_styled = [[Paragraph('<b>Submitted by:</b>', styles['CustomInfoLabel']), Paragraph(str(submission.submitted_by or 'N/A'), styles['CustomInfoValue'])],
                                [Paragraph('<b>Date:</b>', styles['CustomInfoLabel']), Paragraph(submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if submission.submitted_at else 'N/A', styles['CustomInfoValue'])]]
            info_table_styled = Table(info_data_styled, colWidths=[1.5 * inch, None])
            info_table_styled.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 2)]))
            story.append(info_table_styled); story.append(Spacer(1, final_config["info_space_after"]))
            
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
            answer_font_color_hex = final_config["answer_font_color"].hex()


            for ans_item in sorted(regular_answers, key=lambda a: a.question or ""):
                q_text_p = str(ans_item.question or "Untitled Question")
                ans_val_p = str(ans_item.answer) if ans_item.answer is not None else "No answer provided"
                if qa_layout == "answer_same_line" and isinstance(ans_item.answer, str) and len(ans_val_p) <= answer_same_line_max_len and '\n' not in ans_val_p:
                    combined_text = f"<b>{q_text_p}:</b> <font color='{answer_font_color_hex}'>{ans_val_p}</font>"
                    story.append(Paragraph(combined_text, styles['CustomQACombined']))
                else:
                    story.append(Paragraph(q_text_p, styles['CustomQuestion'])); story.append(Paragraph(ans_val_p, styles['CustomAnswer']))

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
                    combined_text_c = f"<b>{q_text_c_p}:</b> <font color='{answer_font_color_hex}'>{ans_val_c_p}</font>"
                    story.append(Paragraph(combined_text_c, styles['CustomQACombined']))
                else:
                    story.append(Paragraph(q_text_c_p, styles['CustomQuestion'])); story.append(Paragraph(ans_val_c_p, styles['CustomAnswer']))
            
            table_cell_padding_val = final_config["table_cell_padding"]
            table_grid_color_val = final_config["table_grid_color"]
            table_grid_thickness_val = final_config["table_grid_thickness"]
            table_header_bg_color_val = final_config["table_header_bg_color"]

            for table_id_cb, content_cb in cell_based_tables_data.items():
                story.append(Paragraph(str(content_cb['name']), styles['CustomQuestion']))
                all_cols_indices = content_cb['col_indices']; sorted_cols = sorted(list(all_cols_indices))
                data_row_indices = sorted([r for r in content_cb['row_indices'] if r > 0])
                header_styled_row_cb: List[Paragraph] = []; actual_col_count_cb = len(sorted_cols)
                if content_cb['header_row_present']: 
                    for col_idx in sorted_cols: header_styled_row_cb.append(Paragraph(str(content_cb['headers'].get(col_idx, f"Col {col_idx+1}")), styles['CustomTableHeader']))
                elif actual_col_count_cb > 0 and not content_cb['header_row_present'] and data_row_indices: 
                    header_styled_row_cb = [Paragraph(f"Column {idx+1}", styles['CustomTableHeader']) for idx in sorted_cols]
                table_rows_styled_cb: List[List[Paragraph]] = []
                if header_styled_row_cb: table_rows_styled_cb.append(header_styled_row_cb)
                for data_row_idx in data_row_indices: table_rows_styled_cb.append([Paragraph(str(content_cb['cells'].get((data_row_idx, col_idx), "")), styles['CustomTableCell']) for col_idx in sorted_cols])
                if table_rows_styled_cb: 
                    col_widths_cb_val = [page_content_width / actual_col_count_cb] * actual_col_count_cb if actual_col_count_cb > 0 else [page_content_width]
                    rl_table_cb = Table(table_rows_styled_cb, colWidths=col_widths_cb_val, repeatRows=1 if header_styled_row_cb else 0)
                    style_cmds_cb_list = [('GRID', (0,0), (-1,-1), table_grid_thickness_val, table_grid_color_val), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                                          ('LEFTPADDING', (0,0), (-1,-1), table_cell_padding_val), ('RIGHTPADDING', (0,0), (-1,-1), table_cell_padding_val),
                                          ('TOPPADDING', (0,0), (-1,-1), table_cell_padding_val), ('BOTTOMPADDING', (0,0), (-1,-1), table_cell_padding_val)]
                    if header_styled_row_cb: style_cmds_cb_list.append(('BACKGROUND', (0,0), (-1,0), table_header_bg_color_val))
                    rl_table_cb.setStyle(TableStyle(style_cmds_cb_list)); story.append(rl_table_cb); story.append(Spacer(1, 0.15*inch))
                elif header_styled_row_cb: 
                    col_widths_cb_val_h = [page_content_width / actual_col_count_cb] * actual_col_count_cb if actual_col_count_cb > 0 else [page_content_width]
                    rl_table_cb_h = Table([header_styled_row_cb], colWidths=col_widths_cb_val_h)
                    rl_table_cb_h.setStyle(TableStyle([('GRID', (0,0), (-1,-1), table_grid_thickness_val, table_grid_color_val), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), 
                                                     ('BACKGROUND', (0,0), (-1,0), table_header_bg_color_val),
                                                     ('LEFTPADDING', (0,0), (-1,-1), table_cell_padding_val), ('RIGHTPADDING', (0,0), (-1,-1), table_cell_padding_val),
                                                     ('TOPPADDING', (0,0), (-1,-1), table_cell_padding_val), ('BOTTOMPADDING', (0,0), (-1,-1), table_cell_padding_val)]))
                    story.append(rl_table_cb_h); story.append(Spacer(1, 0.15*inch))
                else: story.append(Paragraph("No data for this table.", styles['CustomAnswer']))

            for table_name_pb, info_pb in pattern_based_tables_data.items():
                story.append(Paragraph(str(table_name_pb), styles['CustomQuestion']))
                data_for_pb_table_styled: List[List[Paragraph]] = []
                if info_pb['raw_json_csv_data']:
                    raw_str = info_pb['raw_json_csv_data']
                    try: 
                        parsed = json.loads(raw_str)
                        if isinstance(parsed, list) and parsed:
                            if isinstance(parsed[0], dict):
                                headers = list(parsed[0].keys()); data_for_pb_table_styled.append([Paragraph(str(h), styles['CustomTableHeader']) for h in headers])
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
                    style_cmds_pb_list = [('GRID', (0,0), (-1,-1), table_grid_thickness_val, table_grid_color_val), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), 
                                          ('BACKGROUND', (0,0), (-1,0), table_header_bg_color_val),
                                          ('LEFTPADDING', (0,0), (-1,-1), table_cell_padding_val), ('RIGHTPADDING', (0,0), (-1,-1), table_cell_padding_val),
                                          ('TOPPADDING', (0,0), (-1,-1), table_cell_padding_val), ('BOTTOMPADDING', (0,0), (-1,-1), table_cell_padding_val)]
                    rl_table_pb.setStyle(TableStyle(style_cmds_pb_list)); story.append(rl_table_pb); story.append(Spacer(1, 0.15*inch))
                else: story.append(Paragraph("No data available for this table.", styles['CustomAnswer']))

            if include_signatures:
                sig_attachments = Attachment.query.filter_by(form_submission_id=submission_id, is_signature=True, is_deleted=False).all()
                if sig_attachments:
                    story.append(Paragraph("Signatures:", styles['CustomSignatureLabel'])); story.append(Spacer(1, 0.05 * inch))
                    sig_scale = signatures_size / 100.0
                    sig_img_w_conf = final_config["signature_image_width"] * sig_scale
                    sig_img_h_conf = final_config["signature_image_height"] * sig_scale
                    if signatures_alignment.lower() == "horizontal" and len(sig_attachments) > 1:
                        max_sigs_per_row = int(page_content_width / (sig_img_w_conf + 0.2*inch)) if sig_img_w_conf > 0 else 1
                        max_sigs_per_row = max(1, min(max_sigs_per_row, len(sig_attachments), 4))
                        sig_rows_data_list = []; current_sig_row_items_list = []
                        for idx, att in enumerate(sig_attachments):
                            sig_block_elements_list: List[Flowable] = []; file_path = os.path.join(upload_path, att.file_path); sig_author = att.signature_author or "N/A"; sig_position = att.signature_position or "N/A"
                            if os.path.exists(file_path):
                                try: sig_block_elements_list.append(Image(file_path, width=sig_img_w_conf, height=sig_img_h_conf))
                                except Exception: sig_block_elements_list.append(Paragraph("<i>[Image Error]</i>", styles['CustomSignatureText']))
                            else: sig_block_elements_list.append(Paragraph("<i>[Image Missing]</i>", styles['CustomSignatureText']))
                            sig_block_elements_list.append(Spacer(1,2)); sig_block_elements_list.append(Paragraph("<b>___________________________</b>", styles['CustomSignatureText'])); sig_block_elements_list.append(Paragraph(f"<b>Signed by:</b> {sig_author}", styles['CustomSignatureText'])); sig_block_elements_list.append(Paragraph(f"<b>Position:</b> {sig_position}", styles['CustomSignatureText']))
                            current_sig_row_items_list.append(sig_block_elements_list)
                            if len(current_sig_row_items_list) == max_sigs_per_row or idx == len(sig_attachments) - 1:
                                sig_rows_data_list.append(current_sig_row_items_list); current_sig_row_items_list = []
                        for sig_row_group_list in sig_rows_data_list:
                            col_w_sig_val = page_content_width / len(sig_row_group_list) if sig_row_group_list else page_content_width
                            sig_table_this_row = Table([sig_row_group_list], colWidths=[col_w_sig_val]*len(sig_row_group_list))
                            sig_table_this_row.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 2), ('RIGHTPADDING', (0,0), (-1,-1), 2)])) # Using points directly
                            story.append(sig_table_this_row); story.append(Spacer(1, 0.1*inch))
                    else: 
                        for att in sig_attachments:
                            file_path = os.path.join(upload_path, att.file_path); sig_author_v = att.signature_author or "N/A"; sig_position_v = att.signature_position or "N/A"
                            if os.path.exists(file_path):
                                try: story.append(Image(file_path, width=sig_img_w_conf, height=sig_img_h_conf))
                                except Exception: story.append(Paragraph("<i>[Signature Image Error]</i>", styles['CustomSignatureText']))
                            else: story.append(Paragraph("<i>[Signature Image Missing]</i>", styles['CustomSignatureText']))
                            story.append(Spacer(1,2)); story.append(Paragraph("<b>___________________________</b>", styles['CustomSignatureText'])); story.append(Paragraph(f"<b>Signed by:</b> {sig_author_v}", styles['CustomSignatureText'])); story.append(Paragraph(f"<b>Position:</b> {sig_position_v}", styles['CustomSignatureText'])); story.append(Spacer(1, final_config["signature_space_between_vertical"]))
            
            doc.build(story)
            buffer.seek(0)
            return buffer, None
        except Exception as e:
            logger.error(f"Error exporting structured submission to PDF: {submission_id} - {str(e)}", exc_info=True)
            return None, f"An error occurred during PDF generation: {str(e)}"

    @staticmethod
    def export_submission_to_pdf(
        submission_id: int, upload_path: str, include_signatures: bool = True,
        header_image: Optional[FileStorage] = None, header_opacity: float = 1.0,
        header_size: Optional[float] = None, header_width: Optional[float] = None, header_height: Optional[float] = None,
        header_alignment: str = "center", signatures_size: float = 100, signatures_alignment: str = "vertical",
        pdf_style_options: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[BytesIO], Optional[str]]:
        logger.info(f"Calling export_structured_submission_to_pdf for submission_id: {submission_id} with custom styles.")
        return ExportSubmissionService.export_structured_submission_to_pdf(
            submission_id=submission_id, upload_path=upload_path,
            pdf_style_options=pdf_style_options, 
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
