# app/services/export_submission_service.py

import itertools
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
import os
import logging
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Flowable, ListFlowable, ListItem
from PIL import Image as PILImage # type: ignore
from reportlab.lib.utils import ImageReader
import io
import json
import re
from collections import defaultdict

from werkzeug.datastructures import FileStorage # type: ignore
# from werkzeug.exceptions import BadRequest # Not used in this final version

# Assuming your models are correctly imported from your app structure
from app.models.form_submission import FormSubmission
from app.models.attachment import Attachment
from app.models.answer_submitted import AnswerSubmitted
from app.models.form import Form
# from app.models.form_question import FormQuestion # Not directly used in this file after refactor

logger = logging.getLogger(__name__)

# Global variables for PDF formatting
PAGE_MARGINS = {
    'top': 0.75 * inch,
    'bottom': 0.75 * inch,
    'left': 0.80 * inch,
    'right': 0.75 * inch
}
TITLE_SPACING = {
    'before': 12,
    'after': 18
}
QUESTION_FORMATTING = {
    'font_size': 12,
    'space_before': 8,
    'space_after': 2, # Adjusted for spacing after question
    'left_indent': 0
}
ANSWER_FORMATTING = {
    'font_size': 10, # Slightly smaller for answers
    'space_before': 2,
    'space_after': 8, # Increased spacing after answer
    'left_indent': 15, # Indent answers slightly
    'leading': 12 # Line spacing for answers
}
SIGNATURE_FORMATTING = {
    'section_space_before': 12,
    'section_space_after': 6,
    'image_width': 2.5 * inch, # Adjusted for potentially multiple signatures
    'image_height': 1.0 * inch, # Adjusted
    'space_between': 10,
    'signature_space_after': 1
}
DEFAULT_IMAGE_SETTINGS = {
    'max_width': 7.0 * inch, # Max width for header image if not specified
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
        Process a header image file applying the specified opacity and sizing.
        Returns image as BytesIO with img_width and img_height attributes.
        """
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
            alpha_with_opacity = alpha_channel.point(lambda i: int(i * opacity)) # Ensure int for Pillow
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
        Export a form submission to PDF with structured organization of tables and choice-based answers.
        """
        try:
            submission = FormSubmission.query.filter_by(id=submission_id, is_deleted=False).first()
            if not submission:
                return None, "Submission not found"
            
            form = Form.query.filter_by(id=submission.form_id, is_deleted=False).first()
            if not form:
                return None, "Form not found"

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=PAGE_MARGINS['right'],
                leftMargin=PAGE_MARGINS['left'],
                topMargin=PAGE_MARGINS['top'],
                bottomMargin=PAGE_MARGINS['bottom'],
                title=f"Form Submission - {form.title}"
            )

            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(name='FormTitle', parent=styles['h1'], fontSize=18, alignment=1, spaceAfter=TITLE_SPACING['after'], leading=22))
            styles.add(ParagraphStyle(name='Question', parent=styles['h2'], fontSize=QUESTION_FORMATTING['font_size'], 
                                      spaceBefore=QUESTION_FORMATTING['space_before'], spaceAfter=QUESTION_FORMATTING['space_after'], 
                                      leftIndent=QUESTION_FORMATTING['left_indent'], leading=15))
            styles.add(ParagraphStyle(name='Answer', parent=styles['Normal'], fontSize=ANSWER_FORMATTING['font_size'], 
                                      spaceBefore=ANSWER_FORMATTING['space_before'], spaceAfter=ANSWER_FORMATTING['space_after'], 
                                      leftIndent=ANSWER_FORMATTING['left_indent'], leading=ANSWER_FORMATTING['leading']))
            styles.add(ParagraphStyle(name='SignatureLabel', parent=styles['h3'], fontSize=11, spaceAfter=2, alignment=0, leftIndent=0, leading=14))
            styles.add(ParagraphStyle(name='TableHeader', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', 
                                      alignment=1, spaceAfter=4, textColor=colors.black, backColor=colors.lightgrey, leading=11,
                                      leftPadding=3, rightPadding=3, topPadding=3, bottomPadding=3)) # Added padding
            styles.add(ParagraphStyle(name='TableCell', parent=styles['Normal'], fontSize=8, spaceAfter=0, leading=10, alignment=0, # Default left align cells
                                      leftPadding=3, rightPadding=3, topPadding=3, bottomPadding=3)) # Added padding
            styles.add(ParagraphStyle(name='SignatureText', parent=styles['Normal'], fontSize=9, leading=11, alignment=0))


            story: List[Flowable] = []

            page_content_width = letter[0] - PAGE_MARGINS['left'] - PAGE_MARGINS['right']

            if header_image:
                processed_image_io = ExportSubmissionService._process_header_image(
                    header_image, header_opacity, header_size, header_width, header_height
                )
                if processed_image_io and hasattr(processed_image_io, 'img_width') and hasattr(processed_image_io, 'img_height'):
                    img_w_attr = getattr(processed_image_io, 'img_width')
                    img_h_attr = getattr(processed_image_io, 'img_height')
                    
                    if not header_width and not header_height and not header_size:
                         if img_w_attr > page_content_width:
                            scale_ratio = page_content_width / img_w_attr
                            img_w_attr *= scale_ratio
                            img_h_attr *= scale_ratio
                    
                    img_obj = Image(processed_image_io, width=img_w_attr, height=img_h_attr)
                    
                    align_val = header_alignment.upper()
                    if align_val not in ['LEFT', 'CENTER', 'RIGHT']:
                        align_val = 'CENTER'
                    
                    header_table = Table([[img_obj]], colWidths=[page_content_width])
                    header_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (0, 0), align_val),
                        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                        ('LEFTPADDING', (0,0), (0,0), 0),
                        ('RIGHTPADDING', (0,0), (0,0), 0),
                        ('TOPPADDING', (0,0), (0,0), 0),
                        ('BOTTOMPADDING', (0,0), (0,0), 0),
                    ]))
                    story.append(header_table)
                    story.append(Spacer(1, 0.1 * inch))

            story.append(Paragraph(form.title, styles['FormTitle']))
            if form.description:
                story.append(Paragraph(form.description, styles['Normal']))
            story.append(Spacer(1, 0.2 * inch))

            info_data_paras = [
                [Paragraph('<b>Submitted by:</b>', styles['Normal']), Paragraph(str(submission.submitted_by or 'N/A'), styles['Normal'])],
                [Paragraph('<b>Date:</b>', styles['Normal']), Paragraph(submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if submission.submitted_at else 'N/A', styles['Normal'])]
            ]
            info_table = Table(info_data_paras, colWidths=[1.5 * inch, None])
            info_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 0.2 * inch))
            
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

            sorted_regular_answers = sorted(regular_answers, key=lambda a: a.question or "")
            for ans_item in sorted_regular_answers:
                story.append(Paragraph(str(ans_item.question or "Untitled Question"), styles['Question']))
                answer_val = str(ans_item.answer) if ans_item.answer is not None else "No answer provided"
                story.append(Paragraph(answer_val, styles['Answer']))

            for q_text_choice, ans_list_choice in choice_answer_groups.items():
                story.append(Paragraph(str(q_text_choice), styles['Question']))
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
                
                if unique_options:
                    answer_string = ", ".join(unique_options)
                    story.append(Paragraph(answer_string, styles['Answer']))
                else:
                    story.append(Paragraph("No selection", styles['Answer']))
            
            for table_id_cb, content_cb in cell_based_tables_data.items():
                story.append(Paragraph(str(content_cb['name']), styles['Question']))
                all_cols_indices = content_cb['col_indices']
                sorted_cols = sorted(list(all_cols_indices))
                data_row_indices = sorted([r for r in content_cb['row_indices'] if r > 0])
                header_styled_row: List[Paragraph] = []
                actual_col_count = len(sorted_cols)

                if content_cb['header_row_present']: 
                    for col_idx in sorted_cols:
                        header_text = str(content_cb['headers'].get(col_idx, f"Col {col_idx+1}"))
                        header_styled_row.append(Paragraph(header_text, styles['TableHeader']))
                elif actual_col_count > 0 and not content_cb['header_row_present'] and data_row_indices: 
                    header_styled_row = [Paragraph(f"Column {idx+1}", styles['TableHeader']) for idx in sorted_cols]
                
                table_rows_styled: List[List[Paragraph]] = []
                if header_styled_row: table_rows_styled.append(header_styled_row)

                for data_row_idx in data_row_indices: 
                    current_row_styled = [Paragraph(str(content_cb['cells'].get((data_row_idx, col_idx), "")), styles['TableCell']) for col_idx in sorted_cols]
                    table_rows_styled.append(current_row_styled)

                if table_rows_styled: 
                    col_widths_cb = [page_content_width / actual_col_count] * actual_col_count if actual_col_count > 0 else [page_content_width]
                    rl_table_cb = Table(table_rows_styled, colWidths=col_widths_cb, repeatRows=1 if header_styled_row else 0)
                    style_cmds_cb = [('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]
                    if header_styled_row: style_cmds_cb.extend([('BACKGROUND', (0,0), (-1,0), colors.lightgrey)])
                    rl_table_cb.setStyle(TableStyle(style_cmds_cb))
                    story.append(rl_table_cb)
                    story.append(Spacer(1, 0.15*inch))
                elif header_styled_row: 
                    col_widths_cb = [page_content_width / actual_col_count] * actual_col_count if actual_col_count > 0 else [page_content_width]
                    rl_table_cb = Table([header_styled_row], colWidths=col_widths_cb)
                    rl_table_cb.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BACKGROUND', (0,0), (-1,0), colors.lightgrey)]))
                    story.append(rl_table_cb)
                    story.append(Spacer(1, 0.15*inch))
                else:
                    story.append(Paragraph("No data for this table.", styles['Answer']))

            for table_name_pb, info_pb in pattern_based_tables_data.items():
                story.append(Paragraph(str(table_name_pb), styles['Question']))
                data_for_pb_table: List[List[Paragraph]] = []
                if info_pb['raw_json_csv_data']:
                    raw_str = info_pb['raw_json_csv_data']
                    try: 
                        parsed = json.loads(raw_str)
                        if isinstance(parsed, list) and parsed:
                            if isinstance(parsed[0], dict):
                                headers = list(parsed[0].keys())
                                data_for_pb_table.append([Paragraph(str(h), styles['TableHeader']) for h in headers])
                                for item_dict in parsed: data_for_pb_table.append([Paragraph(str(item_dict.get(h, "")), styles['TableCell']) for h in headers])
                            elif isinstance(parsed[0], list): 
                                data_for_pb_table.append([Paragraph(str(h_item), styles['TableHeader']) for h_item in parsed[0]])
                                for r_item_list in parsed[1:]: data_for_pb_table.append([Paragraph(str(c_item), styles['TableCell']) for c_item in r_item_list])
                    except json.JSONDecodeError: 
                        if '\n' in raw_str:
                            lines = [line.strip() for line in raw_str.strip().split('\n')]; sep = '~' if '~' in lines[0] else ','
                            if lines:
                                data_for_pb_table.append([Paragraph(str(h.strip()), styles['TableHeader']) for h in lines[0].split(sep)])
                                for data_line in lines[1:]: data_for_pb_table.append([Paragraph(str(c.strip()), styles['TableCell']) for c in data_line.split(sep)])
                if not data_for_pb_table: 
                    headers_from_pattern = sorted(info_pb['headers'], key=lambda x: x[0]); header_texts = [h_text for _, h_text in headers_from_pattern]
                    current_max_cols = len(header_texts); rows_from_pattern_dict = info_pb['rows']
                    if rows_from_pattern_dict: current_max_cols = max(current_max_cols, max(max(r.keys())+1 if r else 0 for r in rows_from_pattern_dict.values()))
                    if not header_texts and current_max_cols > 0: header_texts = [f"Column {i+1}" for i in range(current_max_cols)]
                    if header_texts: data_for_pb_table.append([Paragraph(str(h), styles['TableHeader']) for h in header_texts])
                    for r_idx_pat in sorted(info_pb['row_order']):
                        r_data_pat = rows_from_pattern_dict.get(r_idx_pat, {})
                        data_for_pb_table.append([Paragraph(str(r_data_pat.get(c_idx_pat, "")), styles['TableCell']) for c_idx_pat in range(current_max_cols)])
                if data_for_pb_table:
                    actual_cols_pb = len(data_for_pb_table[0]) if data_for_pb_table else 1
                    col_widths_pb = [page_content_width / actual_cols_pb] * actual_cols_pb if actual_cols_pb > 0 else [page_content_width]
                    rl_table_pb = Table(data_for_pb_table, colWidths=col_widths_pb, repeatRows=1)
                    rl_table_pb.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BACKGROUND', (0,0), (-1,0), colors.lightgrey)]))
                    story.append(rl_table_pb)
                    story.append(Spacer(1, 0.15*inch))
                else: story.append(Paragraph("No data available for this table.", styles['Answer']))

            if include_signatures:
                sig_attachments = Attachment.query.filter_by(form_submission_id=submission_id, is_signature=True, is_deleted=False).all()
                if sig_attachments:
                    story.append(Spacer(1, SIGNATURE_FORMATTING['section_space_before']))
                    story.append(Paragraph("Signatures:", styles['SignatureLabel'])) 
                    story.append(Spacer(1, 0.1 * inch))
                    sig_scale = signatures_size / 100.0; sig_img_w = SIGNATURE_FORMATTING['image_width'] * sig_scale; sig_img_h = SIGNATURE_FORMATTING['image_height'] * sig_scale
                    if signatures_alignment.lower() == "horizontal" and len(sig_attachments) > 1:
                        max_sigs_per_row = int(page_content_width / (sig_img_w + 0.2*inch)) if sig_img_w > 0 else 1; max_sigs_per_row = max(1, max_sigs_per_row) 
                        sig_rows_data = []; current_sig_row_items = []
                        for idx, att in enumerate(sig_attachments):
                            sig_block_elements: List[Flowable] = []; file_path = os.path.join(upload_path, att.file_path); sig_author = att.signature_author or "N/A"; sig_position = att.signature_position or "N/A"
                            if os.path.exists(file_path):
                                try: sig_block_elements.append(Image(file_path, width=sig_img_w, height=sig_img_h))
                                except Exception: sig_block_elements.append(Paragraph("<i>[Signature Image Error]</i>", styles['SignatureText']))
                            else: sig_block_elements.append(Paragraph("<i>[Signature Image Missing]</i>", styles['SignatureText']))
                            sig_block_elements.append(Paragraph("<b>___________________________</b>", styles['SignatureText'])); sig_block_elements.append(Paragraph(f"<b>Signed by:</b> {sig_author}", styles['SignatureText'])); sig_block_elements.append(Paragraph(f"<b>Position:</b> {sig_position}", styles['SignatureText']))
                            current_sig_row_items.append(sig_block_elements)
                            if len(current_sig_row_items) == max_sigs_per_row or idx == len(sig_attachments) - 1:
                                sig_rows_data.append(current_sig_row_items); current_sig_row_items = []
                        for sig_row_group in sig_rows_data:
                            col_w_sig = page_content_width / len(sig_row_group) if sig_row_group else page_content_width
                            sig_table_this_row = Table([sig_row_group], colWidths=[col_w_sig]*len(sig_row_group))
                            sig_table_this_row.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 5), ('RIGHTPADDING', (0,0), (-1,-1), 5)])) # Added right padding
                            story.append(sig_table_this_row)
                            story.append(Spacer(1, 0.1*inch))
                    else: 
                        for att in sig_attachments:
                            sig_block_vertical: List[Flowable] = []
                            file_path = os.path.join(upload_path, att.file_path); sig_author_v = att.signature_author or "N/A"; sig_position_v = att.signature_position or "N/A"
                            if os.path.exists(file_path):
                                try: sig_block_vertical.append(Image(file_path, width=sig_img_w, height=sig_img_h))
                                except Exception: sig_block_vertical.append(Paragraph("<i>[Signature Image Error]</i>", styles['SignatureText']))
                            else: sig_block_vertical.append(Paragraph("<i>[Signature Image Missing]</i>", styles['SignatureText']))
                            story.extend(sig_block_vertical); story.append(Paragraph("<b>___________________________</b>", styles['SignatureText'])); story.append(Paragraph(f"<b>Signed by:</b> {sig_author_v}", styles['SignatureText'])); story.append(Paragraph(f"<b>Position:</b> {sig_position_v}", styles['SignatureText'])); story.append(Spacer(1, SIGNATURE_FORMATTING['space_between']))
                    story.append(Spacer(1, SIGNATURE_FORMATTING['section_space_after']))

            doc.build(story)
            buffer.seek(0)
            return buffer, None
        except Exception as e:
            logger.error(f"Error exporting structured submission to PDF: {submission_id} - {str(e)}", exc_info=True)
            return None, f"An error occurred during PDF generation: {str(e)}"

    @staticmethod
    def export_submission_to_pdf(
        submission_id: int, upload_path: str, include_signatures: bool = True,
        header_image: Optional[FileStorage] = None, header_opacity: float = DEFAULT_IMAGE_SETTINGS['default_opacity'],
        header_size: Optional[float] = None, header_width: Optional[float] = None, header_height: Optional[float] = None,
        header_alignment: str = "center", signatures_size: float = 100, signatures_alignment: str = "vertical"
    ) -> Tuple[Optional[BytesIO], Optional[str]]:
        logger.info(f"Calling enhanced export_structured_submission_to_pdf for submission_id: {submission_id}")
        return ExportSubmissionService.export_structured_submission_to_pdf(
            submission_id=submission_id, upload_path=upload_path, include_signatures=include_signatures,
            header_image=header_image, header_opacity=header_opacity, header_size=header_size,
            header_width=header_width, header_height=header_height, header_alignment=header_alignment,
            signatures_size=signatures_size, signatures_alignment=signatures_alignment
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

    # The following methods (_consolidate_table_questions, _parse_table_structure, _format_answer_simple,
    # _format_answer, _format_answer_by_type, _format_table_answer, _format_dropdown_answer)
    # were part of the original file structure. They are not directly called by the refactored
    # export_structured_submission_to_pdf. They are included here for completeness if other parts
    # of the application might still use them, or for reference. If they are truly unused,
    # they could be removed.

    @staticmethod
    def _consolidate_table_questions(answers: List[AnswerSubmitted]) -> Tuple[List[AnswerSubmitted], Dict[str, Dict[str, List[Any]]]]:
        table_pattern = re.compile(r'^(Table\s+\d+)(?:\s+(.*))?$')
        table_data: Dict[str, Dict[str, List[Any]]] = defaultdict(lambda: {'headers': [], 'rows': []})
        non_table_answers: List[AnswerSubmitted] = []
        table_answers_orig: List[Tuple[str, str, AnswerSubmitted]] = []
        
        for answer in answers:
            question = answer.question
            match = table_pattern.match(question) if question else None
            
            if match and answer.question_type and answer.question_type.lower() == 'table':
                table_name = match.group(1)
                qualifier = match.group(2) or ""
                table_answers_orig.append((table_name, qualifier, answer))
            else:
                non_table_answers.append(answer)
        
        for table_name, table_questions_iterable in itertools.groupby(
            sorted(table_answers_orig, key=lambda x: x[0]), 
            key=lambda x: x[0]
        ):
            table_questions = list(table_questions_iterable)
            col_headers: List[Tuple[int, str]] = []
            rows_dict: Dict[int, Dict[int, str]] = defaultdict(dict)
            row_order_list: List[int] = []
            raw_data_found_for_table = False

            for _, qualifier, answer_obj in table_questions:
                if qualifier and qualifier.lower().startswith('column '):
                    try:
                        col_num = int(qualifier.lower().replace('column ', '').strip()) - 1
                        col_headers.append((col_num, answer_obj.answer or ""))
                    except ValueError:
                        col_headers.append((len(col_headers), answer_obj.answer or ""))
                elif qualifier and qualifier.lower().startswith('row '):
                    try:
                        row_parts = qualifier.lower().replace('row ', '').strip().split('.')
                        if len(row_parts) == 2:
                            row_num = int(row_parts[0]) - 1
                            col_num = int(row_parts[1]) - 1
                            if row_num not in row_order_list:
                                row_order_list.append(row_num)
                            rows_dict[row_num][col_num] = answer_obj.answer or ""
                    except ValueError:
                        logger.debug(f"Could not parse row/col for table {table_name}, qualifier {qualifier}")
                elif answer_obj.answer and not qualifier: # Potential raw JSON/CSV
                    try:
                        parsed_json = json.loads(answer_obj.answer)
                        if isinstance(parsed_json, list):
                            raw_data_found_for_table = True
                            if parsed_json and isinstance(parsed_json[0], dict): # List of dicts
                                temp_headers = list(parsed_json[0].keys())
                                col_headers = [(i, h) for i, h in enumerate(temp_headers)]
                                for i, row_item_dict in enumerate(parsed_json):
                                    if i not in row_order_list: row_order_list.append(i)
                                    for j, h_key in enumerate(temp_headers):
                                        rows_dict[i][j] = str(row_item_dict.get(h_key, ""))
                            elif parsed_json and isinstance(parsed_json[0], list): # List of lists
                                col_headers = [(i, str(h_val)) for i, h_val in enumerate(parsed_json[0])]
                                for i, row_item_list_data in enumerate(parsed_json[1:]):
                                    actual_row_idx = i 
                                    if actual_row_idx not in row_order_list: row_order_list.append(actual_row_idx)
                                    for j, cell_val in enumerate(row_item_list_data):
                                        rows_dict[actual_row_idx][j] = str(cell_val)
                    except json.JSONDecodeError:
                        if '\n' in answer_obj.answer and (',' in answer_obj.answer or '~' in answer_obj.answer):
                            raw_data_found_for_table = True
                            lines = answer_obj.answer.strip().split('\n')
                            separator = '~' if '~' in lines[0] else ','
                            if lines:
                                col_headers = [(i, h.strip()) for i, h in enumerate(lines[0].split(separator))]
                                for i, line_str in enumerate(lines[1:]):
                                    actual_row_idx = i
                                    if actual_row_idx not in row_order_list: row_order_list.append(actual_row_idx)
                                    cells = [cell.strip() for cell in line_str.split(separator)]
                                    for j, cell_data in enumerate(cells):
                                        rows_dict[actual_row_idx][j] = cell_data
                    if raw_data_found_for_table: # If raw data parsed, it defines the table structure
                        break # Move to next table_name

            if not raw_data_found_for_table: # Only sort and build if not parsed from raw data block
                col_headers.sort(key=lambda x: x[0])
            
            headers_list_final = [h for _, h in col_headers]
            
            current_max_cols = len(headers_list_final)
            if rows_dict:
                 current_max_cols = max(current_max_cols, max(max(r.keys()) + 1 if r else 0 for r in rows_dict.values()))


            table_rows_final = []
            for row_num_final in sorted(row_order_list):
                row_data_final = rows_dict.get(row_num_final, {})
                current_table_row_list = [row_data_final.get(col, "") for col in range(current_max_cols)]
                table_rows_final.append(current_table_row_list)
            
            if not headers_list_final and current_max_cols > 0: # Default headers if none found
                headers_list_final = [f"Column {i+1}" for i in range(current_max_cols)]

            table_data[table_name] = {
                'headers': headers_list_final,
                'rows': table_rows_final
            }
        return non_table_answers, dict(table_data)

    @staticmethod
    def _parse_table_structure(answers: List[AnswerSubmitted]) -> Tuple[List[AnswerSubmitted], Dict[str, List[List[str]]]]:
        table_pattern = re.compile(r'^(Table\s+\d+)(?:\s+(.*))?$')
        tables_dict: Dict[str, Dict[str, Any]] = defaultdict(lambda: {'headers': [], 'rows': defaultdict(dict), 'row_order': []})
        regular_answers_list: List[AnswerSubmitted] = []
        
        for answer_obj in answers:
            question_text = answer_obj.question
            if not question_text:
                regular_answers_list.append(answer_obj)
                continue
            match_obj = table_pattern.match(question_text)
            if match_obj:
                table_name = match_obj.group(1)
                qualifier = match_obj.group(2) or ""
                if qualifier.lower().startswith('column '):
                    try:
                        col_idx = int(qualifier.lower().replace('column ', '').strip()) - 1
                        tables_dict[table_name]['headers'].append((col_idx, answer_obj.answer or ""))
                    except ValueError:
                        tables_dict[table_name]['headers'].append(
                            (len(tables_dict[table_name]['headers']), answer_obj.answer or "")
                        )
                elif qualifier.lower().startswith('row '):
                    try:
                        row_parts = qualifier.lower().replace('row ', '').strip().split('.')
                        if len(row_parts) == 2:
                            row_idx = int(row_parts[0]) - 1
                            col_idx_row = int(row_parts[1]) - 1
                            if row_idx not in tables_dict[table_name]['row_order']:
                                tables_dict[table_name]['row_order'].append(row_idx)
                            tables_dict[table_name]['rows'][row_idx][col_idx_row] = answer_obj.answer or ""
                    except (ValueError, IndexError):
                        regular_answers_list.append(answer_obj)
                else: # No specific qualifier, but matched "Table X"
                    if answer_obj.answer: # If it has an answer, maybe it's a raw block
                         # This simplistic version doesn't try to parse raw JSON/CSV here
                         # It would be added to regular_answers if not qualifier matched
                        regular_answers_list.append(answer_obj)
            else:
                regular_answers_list.append(answer_obj)
        
        formatted_tables_output: Dict[str, List[List[str]]] = {}
        for table_name_fmt, table_data_fmt in tables_dict.items():
            sorted_headers_list = sorted(table_data_fmt['headers'], key=lambda x: x[0])
            header_row_list_str = [h for _, h in sorted_headers_list]
            
            max_cols_fmt = len(header_row_list_str)
            if table_data_fmt['rows']:
                max_cols_fmt = max(max_cols_fmt, max(max(row_d.keys()) + 1 if row_d else 0 for row_d in table_data_fmt['rows'].values()))
            
            if not header_row_list_str and max_cols_fmt > 0: # Default headers
                header_row_list_str = [f"Col {i+1}" for i in range(max_cols_fmt)]

            final_table_data_list: List[List[str]] = []
            if header_row_list_str: final_table_data_list.append(header_row_list_str)
            
            for row_idx_fmt in sorted(table_data_fmt['row_order']):
                row_data_item = table_data_fmt['rows'].get(row_idx_fmt, {})
                current_row_list_str = [row_data_item.get(col_idx_fmt, "") for col_idx_fmt in range(max_cols_fmt)]
                final_table_data_list.append(current_row_list_str)
            
            if final_table_data_list : # Only add if there's some data
                formatted_tables_output[table_name_fmt] = final_table_data_list
        
        return regular_answers_list, formatted_tables_output

    @staticmethod
    def _format_answer_simple(answer: AnswerSubmitted, styles: Dict[str, ParagraphStyle]) -> List[Flowable]:
        answer_text = answer.answer if answer.answer and hasattr(answer, 'answer') else "No answer provided"
        return [Paragraph(str(answer_text), styles['Answer'])]

    @staticmethod
    def _format_answer(answer: AnswerSubmitted, styles: Dict[str, ParagraphStyle]) -> List[Flowable]:
        # This is a placeholder if a more complex AnswerFormatterFactory is not used or for fallback.
        # The main export function now handles specific types directly.
        answer_text = str(answer.answer or "N/A")
        return [Paragraph(answer_text, styles['Answer'])]

    @staticmethod
    def _format_answer_by_type(answer: AnswerSubmitted, styles: Dict[str, ParagraphStyle]) -> List[Flowable]:
        # This method's specific type handling is largely integrated into the main export function.
        # It's kept for potential other uses or if it handles types not covered by the main function.
        question_type_fmt = (answer.question_type.lower() if hasattr(answer, 'question_type') and answer.question_type else "")
        answer_text_fmt = str(answer.answer or "No answer provided")

        if question_type_fmt == "table":
            return [Paragraph(f"[Table Data (Formatted by _format_answer_by_type)]: {answer_text_fmt}", styles['Answer'])]
        elif question_type_fmt in ["dropdown", "select", "multiselect", "checkbox", "multiple_choices"]:
            return [Paragraph(f"[Choice Data (Formatted by _format_answer_by_type)]: {answer_text_fmt}", styles['Answer'])]
        return [Paragraph(answer_text_fmt, styles['Answer'])]

    @staticmethod
    def _format_table_answer(answer_text: str, styles: Dict[str, ParagraphStyle]) -> List[Flowable]:
        # This method assumes answer_text is a pre-formatted string representing a table.
        # The main export function now builds tables from structured data directly.
        return [Paragraph(f"[Formatted Table (from _format_table_answer)]: {str(answer_text)}", styles['Answer'])]

    @staticmethod
    def _format_dropdown_answer(answer_text: str, styles: Dict[str, ParagraphStyle]) -> List[Flowable]:
        # Similar to _format_table_answer, assumes pre-formatted string.
        return [Paragraph(f"[Formatted Dropdown (from _format_dropdown_answer)]: {str(answer_text)}", styles['Answer'])]

