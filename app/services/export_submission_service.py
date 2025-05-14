# app/services/export_submission_service.py

import io
import itertools
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime
import os
import logging
from io import BytesIO
from sqlalchemy.orm import joinedload
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle as ReportLabParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph as ReportLabParagraph, Spacer,
    Table as ReportLabTable, TableStyle as ReportLabTableStyle,
    Image as ReportLabImage, Flowable
)
from PIL import Image as PILImage # type: ignore
# import io # already imported via from io import BytesIO
import json
import re
from collections import defaultdict

from werkzeug.datastructures import FileStorage # type: ignore

# Assuming your models are correctly imported from your app structure
from app.models.form_question import FormQuestion
from app.models.form_submission import FormSubmission
from app.models.attachment import Attachment
from app.models.answer_submitted import AnswerSubmitted
from app.models.form import Form
from app.models.question import Question
from app.models.question_type import QuestionType

# Imports for DOCX generation
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml


logger = logging.getLogger(__name__)

# --- Default Style Configuration (for PDF and adapted for DOCX) ---
DEFAULT_STYLE_CONFIG: Dict[str, Any] = {
    # Page Layout
    "page_margin_top": 0.75, # Inches for DOCX, ReportLab uses * inch
    "page_margin_bottom": 0.75,
    "page_margin_left": 0.75,
    "page_margin_right": 0.75,
    "default_font_family": "Helvetica", # For PDF
    "default_font_family_docx": "Calibri", # For DOCX
    "default_font_color": colors.black, # ReportLab color object
    "default_font_color_docx": "000000", # Hex string for DOCX
    "default_font_size_docx": 11, # Points for DOCX

    # Title
    "title_font_family": "Helvetica-Bold",
    "title_font_family_docx": "Calibri",
    "title_font_size": 18, # Points
    "title_font_size_docx": 22, # Points
    "title_leading": 22, # Points for ReportLab
    "title_font_color": colors.black,
    "title_font_color_docx": "000000",
    "title_alignment": TA_CENTER, # ReportLab alignment constant
    "title_alignment_docx": "center", # String for DOCX
    "title_space_after": 0.25, # Inches for ReportLab, converted to Pt for DOCX
    "title_space_after_docx": 12, # Points for DOCX

    # Description
    "description_font_family": "Helvetica",
    "description_font_family_docx": "Calibri",
    "description_font_size": 10,
    "description_font_size_docx": 10,
    "description_leading": 12,
    "description_font_color": colors.darkslategray,
    "description_font_color_docx": "2F4F4F",
    "description_alignment": TA_LEFT,
    "description_alignment_docx": "left",
    "description_space_after": 0.15, # Inches
    "description_space_after_docx": 6, # Points


    # Submission Info (Submitted by, Date)
    "info_font_family": "Helvetica",
    "info_font_family_docx": "Calibri",
    "info_font_size": 10,
    "info_font_size_docx": 9,
    "info_leading": 12,
    "info_font_color": colors.darkslategray,
    "info_font_color_docx": "2F4F4F",
    "info_label_font_family": "Helvetica-Bold", # For PDF, DOCX will just use bold
    "info_label_font_family_docx": "Calibri",
    "info_alignment": TA_LEFT,
    "info_alignment_docx": "left",
    "info_space_after": 0.2, # Inches
    "info_space_after_docx": 12, # Points

    # Question
    "question_font_family": "Helvetica-Bold",
    "question_font_family_docx": "Calibri",
    "question_font_size": 11, # Points
    "question_font_size_docx": 12, # Points
    "question_font_color": colors.black,
    "question_font_color_docx": "000000",
    "question_left_indent": 0, # Inches for ReportLab
    "question_left_indent_docx": 0, # Inches for DOCX
    "question_space_before": 0.15, # Inches
    "question_space_before_docx": 8, # Points
    "question_space_after": 4/72.0, # Inches (4 points)
    "question_space_after_docx": 3, # Points
    "question_leading": 14, # Points

    # Answer
    "answer_font_family": "Helvetica",
    "answer_font_family_docx": "Calibri",
    "answer_font_size": 10, # Points
    "answer_font_size_docx": 10, # Points
    "answer_font_color": colors.darkslategray,
    "answer_font_color_docx": "2F4F4F", # Dark Slate Gray
    "answer_left_indent": 15/72.0, # Inches (15 points)
    "answer_left_indent_docx": 0.25, # Inches
    "answer_space_before": 2/72.0, # Inches (2 points)
    "answer_space_before_docx": 2, # Points
    "answer_space_after": 0.15, # Inches
    "answer_space_after_docx": 6, # Points
    "answer_leading": 12, # Points
    "qa_layout": "answer_below", # "answer_below" or "answer_same_line"
    "answer_same_line_max_length": 70,

    # Table Header
    "table_header_font_family": "Helvetica-Bold",
    "table_header_font_family_docx": "Calibri",
    "table_header_font_size": 9, # Points
    "table_header_font_size_docx": 10, # Points
    "table_header_font_color": colors.black, # ReportLab
    "table_header_font_color_docx": "000000", # DOCX
    "table_header_bg_color": colors.lightgrey, # ReportLab color object
    "table_header_bg_color_docx": "D3D3D3", # Hex string for lightgrey
    "table_header_leading": 11, # Points
    "table_header_alignment": "CENTER", # ReportLab ParagraphStyle string
    "table_header_alignment_docx": "center", # DOCX alignment string
    "table_cell_padding_left": 3, # Points for ReportLab TableStyle
    "table_cell_padding_right": 3,
    "table_cell_padding_top": 3,
    "table_cell_padding_bottom": 3,
    "table_space_after": 0.15, # Inches
    "table_space_after_docx": 12, # Points

    # Table Cell
    "table_cell_font_family": "Helvetica",
    "table_cell_font_family_docx": "Calibri",
    "table_cell_font_size": 8, # Points
    "table_cell_font_size_docx": 9, # Points
    "table_cell_font_color": colors.black,
    "table_cell_font_color_docx": "000000",
    "table_cell_leading": 10, # Points
    "table_cell_alignment": "LEFT", # ReportLab ParagraphStyle string
    "table_cell_alignment_docx": "left", # DOCX alignment string
    "table_grid_color": colors.grey, # ReportLab
    "table_grid_color_docx": "BEBEBE", # Hex for grey
    "table_grid_thickness": 0.5, # Points

    # Signatures
    "signature_label_font_family": "Helvetica-Bold",
    "signature_label_font_family_docx": "Calibri",
    "signature_label_font_size": 12, # Points
    "signature_label_font_size_docx": 11, # Points
    "signature_label_font_color": colors.black,
    "signature_label_font_color_docx": "000000",
    "signature_text_font_family": "Helvetica",
    "signature_text_font_family_docx": "Calibri",
    "signature_text_font_size": 9, # Points
    "signature_text_font_size_docx": 9, # Points
    "signature_text_font_color": colors.black,
    "signature_text_font_color_docx": "000000",
    "signature_image_width": 2.0, # Inches
    "signature_image_width_docx": 2.0, # Inches
    "signature_image_height": 0.8, # Inches
    "signature_image_height_docx": 0.8, # Inches
    "signature_section_space_before": 0.3, # Inches
    "signature_section_space_before_docx": 18, # Points
    "signature_space_between_vertical": 0.2, # Inches
    "signature_space_between_vertical_docx_pt": 10, # Points for DOCX
}

# --- Global Helper Functions ---
def _get_color_rl(color_input: Any, default_color: colors.Color = colors.black) -> colors.Color:
    if isinstance(color_input, colors.Color):
        return color_input
    if isinstance(color_input, str):
        try:
            if color_input.startswith("#"):
                return colors.HexColor(color_input)
            color_name_lower = color_input.lower()
            if hasattr(colors, color_name_lower):
                return getattr(colors, color_name_lower)
            if len(color_input) == 6 and all(c in "0123456789abcdefABCDEF" for c in color_input):
                 return colors.HexColor(f"#{color_input}")
            logger.warning(f"Unknown ReportLab color string '{color_input}'. Using default.")
            return default_color
        except (ValueError, AttributeError):
            logger.warning(f"Invalid ReportLab color string '{color_input}'. Using default.")
            return default_color
    elif isinstance(color_input, (list, tuple)) and len(color_input) == 3:
        try:
            return colors.Color(float(color_input[0]), float(color_input[1]), float(color_input[2]))
        except ValueError:
            logger.warning(f"Invalid RGB list/tuple for color: {color_input}. Using default.")
            return default_color
    logger.warning(f"Invalid ReportLab color type '{type(color_input)}'. Using default.")
    return default_color

def _color_to_hex_string_rl(color_obj: Any) -> str:
    if isinstance(color_obj, str):
        try:
            temp_color = _get_color_rl(color_obj)
            if hasattr(temp_color, 'hexval') and callable(getattr(temp_color, 'hexval')):
                return temp_color.hexval()
            r_float, g_float, b_float = temp_color.red, temp_color.green, temp_color.blue
            return f"#{int(r_float*255):02x}{int(g_float*255):02x}{int(b_float*255):02x}"
        except:
            return "#000000"
    elif hasattr(color_obj, 'red') and hasattr(color_obj, 'green') and hasattr(color_obj, 'blue'):
        r_float = max(0.0, min(1.0, color_obj.red))
        g_float = max(0.0, min(1.0, color_obj.green))
        b_float = max(0.0, min(1.0, color_obj.blue))
        return f"#{int(r_float*255):02x}{int(g_float*255):02x}{int(b_float*255):02x}"
    return "#000000"

def _parse_numeric_value(value: Any, default_value: float = 0.0) -> float:
    if value is None: return default_value
    try: return float(value)
    except (ValueError, TypeError):
        logger.warning(f"Invalid numeric value '{value}'. Using default {default_value}.")
        return default_value

def _get_alignment_code_rl(align_input: Optional[Union[str, int]], default_align: int = TA_LEFT) -> int:
    code_map = {"LEFT": TA_LEFT, "CENTER": TA_CENTER, "RIGHT": TA_RIGHT, "JUSTIFY": TA_JUSTIFY}
    if isinstance(align_input, int) and align_input in code_map.values():
        return align_input
    if isinstance(align_input, str):
        effective_align_str = align_input.upper()
        if effective_align_str in code_map:
            return code_map[effective_align_str]
    return default_align # Default is TA_LEFT

def _get_docx_alignment(align_input: Optional[Union[str, int]], default_align: WD_ALIGN_PARAGRAPH = WD_ALIGN_PARAGRAPH.LEFT) -> WD_ALIGN_PARAGRAPH:
    align_map_str = {
        "LEFT": WD_ALIGN_PARAGRAPH.LEFT, "CENTER": WD_ALIGN_PARAGRAPH.CENTER,
        "RIGHT": WD_ALIGN_PARAGRAPH.RIGHT, "JUSTIFY": WD_ALIGN_PARAGRAPH.JUSTIFY,
    }
    align_map_int = {
        TA_LEFT: WD_ALIGN_PARAGRAPH.LEFT, 0: WD_ALIGN_PARAGRAPH.LEFT,
        TA_CENTER: WD_ALIGN_PARAGRAPH.CENTER, 1: WD_ALIGN_PARAGRAPH.CENTER,
        TA_RIGHT: WD_ALIGN_PARAGRAPH.RIGHT, 2: WD_ALIGN_PARAGRAPH.RIGHT,
        TA_JUSTIFY: WD_ALIGN_PARAGRAPH.JUSTIFY, 4: WD_ALIGN_PARAGRAPH.JUSTIFY,
    }
    if isinstance(align_input, str): return align_map_str.get(align_input.upper(), default_align)
    if isinstance(align_input, int): return align_map_int.get(align_input, default_align)
    return default_align

def _get_docx_color(color_input: Any, default_hex: str = "000000") -> Optional[RGBColor]:
    hex_val = default_hex
    if isinstance(color_input, str):
        color_str_lower = color_input.lower().strip()
        if color_str_lower.startswith("#"): hex_val = color_str_lower[1:]
        else:
            color_name_map = {
                "black": "000000", "white": "FFFFFF", "red": "FF0000", "green": "00FF00", "blue": "0000FF",
                "yellow": "FFFF00", "cyan": "00FFFF", "magenta": "FF00FF", "silver": "C0C0C0",
                "gray": "808080", "grey": "808080", "maroon": "800000", "olive": "808000",
                "purple": "800080", "teal": "008080", "navy": "000080", "darkblue": "00008B",
                "darkgrey": "A9A9A9", "darkgray": "A9A9A9", "lightgrey": "D3D3D3", "lightgray": "D3D3D3",
                "darkslategray":"2F4F4F",
            }
            if color_str_lower in color_name_map: hex_val = color_name_map[color_str_lower]
            elif len(color_str_lower) == 6 and all(c in "0123456789abcdefABCDEF" for c in color_str_lower):
                hex_val = color_str_lower
            else: logger.warning(f"DOCX: Unknown color string '{color_input}'. Using default hex '{default_hex}'.")
    elif isinstance(color_input, RGBColor): return color_input
    elif hasattr(color_input, 'red') and hasattr(color_input, 'green') and hasattr(color_input, 'blue'):
        try:
            r = int(color_input.red * 255); g = int(color_input.green * 255); b = int(color_input.blue * 255)
            return RGBColor(r, g, b)
        except Exception as e:
            logger.warning(f"Could not convert ReportLab color to DOCX RGBColor: {e}. Using default.")
            hex_val = default_hex

    if len(hex_val) == 3: hex_val = "".join([c*2 for c in hex_val])
    if len(hex_val) != 6:
        logger.warning(f"DOCX: Invalid hex color value '{hex_val}' derived from '{color_input}'. Using default.")
        hex_val = default_hex
    try:
        return RGBColor(int(hex_val[0:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16))
    except ValueError:
        logger.warning(f"DOCX: Error converting hex '{hex_val}' to RGBColor. Using default.")
        if default_hex and len(default_hex) == 6:
             return RGBColor(int(default_hex[0:2], 16), int(default_hex[2:4], 16), int(default_hex[4:6], 16))
        return RGBColor(0,0,0)

def _set_cell_background_docx(cell, hex_color_string_input: str):
    rgb_color = _get_docx_color(hex_color_string_input)
    if rgb_color is None:
        logger.warning(f"DOCX: Could not determine valid color for background from '{hex_color_string_input}'. Skipping background.")
        return
    hex_color_string = f"{rgb_color.r:02X}{rgb_color.g:02X}{rgb_color.b:02X}"
    shading_elm_str = f'<w:shd {nsdecls("w")} w:fill="{hex_color_string}" w:val="clear" />'
    try:
        shading_elm = parse_xml(shading_elm_str)
        cell._tc.get_or_add_tcPr().append(shading_elm)
    except Exception as e:
        logger.error(f"Error setting DOCX cell background with color {hex_color_string}: {e}")


class ExportSubmissionService:
    @staticmethod
    def _process_header_image(
        image_file: Union[FileStorage, str],
        upload_path_base: Optional[str] = None,
        size_percent: Optional[float] = None,
        width_px: Optional[float] = None,
        height_px: Optional[float] = None
    ) -> Optional[Tuple[BytesIO, float, float]]:
        try:
            img_data = None
            if isinstance(image_file, FileStorage):
                img_data = image_file.read()
                image_file.seek(0)
            elif isinstance(image_file, str):
                full_path = os.path.join(upload_path_base, image_file) if upload_path_base and not os.path.isabs(image_file) else image_file
                if os.path.exists(full_path):
                    with open(full_path, 'rb') as f: img_data = f.read()
                else:
                    logger.error(f"Header image file not found at path: {full_path}"); return None
            else:
                logger.error(f"Invalid header_image type: {type(image_file)}"); return None

            if not img_data: return None
            img = PILImage.open(io.BytesIO(img_data))
            if img.format == 'GIF' and getattr(img, 'is_animated', False): img.seek(0)

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
            elif size_percent is not None:
                scale_factor = float(size_percent) / 100.0
                new_width_px *= scale_factor; new_height_px *= scale_factor

            if new_width_px <= 0 or new_height_px <= 0:
                new_width_px, new_height_px = float(orig_width_px), float(orig_height_px)

            if img.mode in ('P', 'LA') or (img.mode == 'RGBA' and img.info.get('transparency') is not None):
                 img = img.convert('RGBA')
            elif img.mode != 'RGB': img = img.convert('RGB')

            img_resized = img.resize((int(new_width_px), int(new_height_px)), PILImage.LANCZOS)
            img_format = img.format if img.format else 'PNG'
            if img_format.upper() in ['SVG', 'WEBP']: img_format = 'PNG'

            result_io = io.BytesIO()
            if img_format.upper() == 'JPEG' and img_resized.mode == 'RGBA':
                img_resized = img_resized.convert('RGB')
            img_resized.save(result_io, format=img_format)
            result_io.seek(0)
            return result_io, new_width_px, new_height_px
        except Exception as e:
            logger.error(f"Error processing header image: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def _add_header_image_to_reportlab_story( # CORRECTED DEFINITION SIGNATURE
        story: List[Flowable],
        header_image_input: Union[FileStorage, str],
        upload_path_base: str,
        opacity: float,
        size_percent: Optional[float],
        width_px: Optional[float],
        height_px: Optional[float],
        alignment_str: str, # Changed from 'alignment' to 'alignment_str' for clarity
        page_margin_left: float, # Added
        page_margin_right: float, # Added
        doc_width: float
    ):
        processed_image_data = ExportSubmissionService._process_header_image(
            header_image_input, upload_path_base, size_percent, width_px, height_px
        )
        if processed_image_data:
            image_io, img_w_px, img_h_px = processed_image_data
            img_w_pt = img_w_px * (72.0 / 96.0)
            img_h_pt = img_h_px * (72.0 / 96.0)

            # doc_width is the available width for content (page_width - margins_total)
            # No need to subtract margins again here if doc_width is already correctly calculated.
            available_width_for_image = doc_width
            if img_w_pt > available_width_for_image:
                scale_ratio = available_width_for_image / img_w_pt
                img_w_pt *= scale_ratio
                img_h_pt *= scale_ratio

            if opacity < 1.0:
                 logger.warning("ReportLab Image opacity < 1.0 not directly supported.")

            img_obj = ReportLabImage(image_io, width=img_w_pt, height=img_h_pt)
            align_code = _get_alignment_code_rl(alignment_str.upper(), TA_CENTER)
            table_style_align_map = {TA_LEFT: 'LEFT', TA_CENTER: 'CENTER', TA_RIGHT: 'RIGHT'}
            img_align_for_table_style = table_style_align_map.get(align_code, 'CENTER')

            img_table = ReportLabTable([[img_obj]], colWidths=[doc_width]) # Cell uses full available width
            img_table.setStyle(ReportLabTableStyle([
                ('ALIGN', (0, 0), (0, 0), img_align_for_table_style),
                ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (0,0), 0), ('RIGHTPADDING', (0,0), (0,0), 0),
                ('TOPPADDING', (0,0), (0,0), 0), ('BOTTOMPADDING', (0,0), (0,0), 0),
            ]))
            story.append(img_table)
            story.append(Spacer(1, 0.1 * inch))

    @staticmethod
    def _add_signatures_to_reportlab_story(
        story: List[Flowable],
        attachments: List[Attachment],
        upload_path: str,
        scale_factor: float,
        alignment_str: str, # Changed from 'alignment'
        styles: Any,
        config: Dict[str, Any]
    ):
        sig_attachments = [att for att in attachments if att.is_signature and not att.is_deleted]
        if not sig_attachments: return

        if 'CustomSignatureLabel' not in styles:
            styles.add(ReportLabParagraphStyle(name='CustomSignatureLabel',
                fontName=str(config.get("signature_label_font_family", "Helvetica-Bold")),
                fontSize=_parse_numeric_value(config.get("signature_label_font_size", 12)),
                textColor=_get_color_rl(config.get("signature_label_font_color", colors.black)),
                spaceBefore=_parse_numeric_value(config.get("signature_section_space_before", 0.3)) * inch,
                spaceAfter=4))
        if 'CustomSignatureText' not in styles:
            styles.add(ReportLabParagraphStyle(name='CustomSignatureText',
                fontName=str(config.get("signature_text_font_family", "Helvetica")),
                fontSize=_parse_numeric_value(config.get("signature_text_font_size", 9)),
                textColor=_get_color_rl(config.get("signature_text_font_color", colors.black)),
                leading=_parse_numeric_value(config.get("signature_text_font_size", 9)) * 1.2))

        story.append(ReportLabParagraph("Signatures:", styles['CustomSignatureLabel']))
        story.append(Spacer(1, 0.05 * inch))

        sig_img_w_conf = _parse_numeric_value(config.get("signature_image_width", 2.0)) * inch * scale_factor
        sig_img_h_conf = _parse_numeric_value(config.get("signature_image_height", 0.8)) * inch * scale_factor
        sig_space_between_vertical = _parse_numeric_value(config.get("signature_space_between_vertical", 0.2)) * inch
        page_content_width = styles.PAGE_WIDTH - styles.LEFT_MARGIN - styles.RIGHT_MARGIN

        if alignment_str.lower() == "horizontal" and len(sig_attachments) > 1:
            effective_sig_width = sig_img_w_conf + (0.2 * inch)
            max_sigs_per_row = int(page_content_width / effective_sig_width) if effective_sig_width > 0 else 1
            max_sigs_per_row = max(1, min(max_sigs_per_row, len(sig_attachments), 3))

            sig_rows_data = []; current_sig_row_items = []
            for idx, att in enumerate(sig_attachments):
                sig_block_elements: List[Flowable] = []
                full_file_path = os.path.join(upload_path, att.file_path)
                sig_author = att.signature_author or "N/A"; sig_position = att.signature_position or "N/A"
                if os.path.exists(full_file_path):
                    try: sig_block_elements.append(ReportLabImage(full_file_path, width=sig_img_w_conf, height=sig_img_h_conf))
                    except Exception as e_img: sig_block_elements.append(ReportLabParagraph(f"<i>[Image Error: {e_img}]</i>", styles['CustomSignatureText']))
                else: sig_block_elements.append(ReportLabParagraph(f"<i>[Image Missing: {att.file_path}]</i>", styles['CustomSignatureText']))
                sig_block_elements.extend([Spacer(1, 2), ReportLabParagraph("___________________________", styles['CustomSignatureText']),
                                          ReportLabParagraph(f"<b>Signed by:</b> {sig_author}", styles['CustomSignatureText']),
                                          ReportLabParagraph(f"<b>Position:</b> {sig_position}", styles['CustomSignatureText'])])
                current_sig_row_items.append(sig_block_elements)
                if len(current_sig_row_items) == max_sigs_per_row or idx == len(sig_attachments) - 1:
                    sig_rows_data.append(current_sig_row_items); current_sig_row_items = []
            for sig_row_group in sig_rows_data:
                if not sig_row_group: continue
                col_width_sig = page_content_width / len(sig_row_group) if len(sig_row_group) > 0 else page_content_width
                sig_table = ReportLabTable([sig_row_group], colWidths=[col_width_sig] * len(sig_row_group))
                sig_table.setStyle(ReportLabTableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 2),
                                                       ('RIGHTPADDING', (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 5)]))
                story.append(sig_table); story.append(Spacer(1, 0.1 * inch))
        else: # Vertical
            for att in sig_attachments:
                full_file_path = os.path.join(upload_path, att.file_path)
                sig_author = att.signature_author or "N/A"; sig_position = att.signature_position or "N/A"
                if os.path.exists(full_file_path):
                    try: story.append(ReportLabImage(full_file_path, width=sig_img_w_conf, height=sig_img_h_conf))
                    except Exception as e_img: story.append(ReportLabParagraph(f"<i>[Sig Image Error: {e_img}]</i>", styles['CustomSignatureText']))
                else: story.append(ReportLabParagraph(f"<i>[Sig Image Missing: {att.file_path}]</i>", styles['CustomSignatureText']))
                story.extend([Spacer(1, 2), ReportLabParagraph("___________________________", styles['CustomSignatureText']),
                              ReportLabParagraph(f"<b>Signed by:</b> {sig_author}", styles['CustomSignatureText']),
                              ReportLabParagraph(f"<b>Position:</b> {sig_position}", styles['CustomSignatureText']),
                              Spacer(1, sig_space_between_vertical)])

    @staticmethod
    def _add_header_image_to_docx_header(
        doc: Document, header_image_input: Union[FileStorage, str], upload_path_base: str,
        size_percent: Optional[float], width_px: Optional[float], height_px: Optional[float],
        alignment_str: str
    ):
        processed_image_data = ExportSubmissionService._process_header_image(
            header_image_input, upload_path_base, size_percent, width_px, height_px
        )
        if processed_image_data:
            image_io, img_w_px, _ = processed_image_data
            img_width_inches = img_w_px / 96.0
            header = doc.sections[0].header
            p_header_img = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
            for run in p_header_img.runs: run.clear() # Clear existing content if reusing paragraph
            run_header_img = p_header_img.add_run()
            try: run_header_img.add_picture(image_io, width=Inches(img_width_inches))
            except Exception as e: logger.error(f"DOCX: Error adding header picture: {e}"); run_header_img.add_text("[Header Image Error]")
            p_header_img.alignment = _get_docx_alignment(alignment_str, WD_ALIGN_PARAGRAPH.CENTER)

    @staticmethod
    def _add_signatures_to_docx(
        doc: Document, attachments: List[Attachment], upload_path: str,
        size_percent: float, alignment_str: str, config: Dict[str, Any]
    ):
        sig_attachments_info = [{'path': os.path.join(upload_path, att.file_path),
                                 'author': att.signature_author or "N/A",
                                 'position': att.signature_position or "N/A",
                                 'exists': os.path.exists(os.path.join(upload_path, att.file_path))}
                                for att in attachments if att.is_signature and not att.is_deleted]
        if not sig_attachments_info: return

        sig_heading_p = doc.add_paragraph()
        sig_heading_run = sig_heading_p.add_run("Signatures")
        sig_heading_run.bold = True
        sig_heading_run.font.size = Pt(_parse_numeric_value(config.get("signature_label_font_size_docx", 11)))
        sig_heading_p.paragraph_format.space_before = Pt(_parse_numeric_value(config.get("signature_section_space_before_docx", 18)))
        sig_heading_p.paragraph_format.space_after = Pt(6)

        sig_img_width_default_inches = _parse_numeric_value(config.get("signature_image_width_docx", 2.0))
        sig_img_width_final_inches = sig_img_width_default_inches * (size_percent / 100.0)
        sig_text_font_fam = str(config.get("signature_text_font_family_docx", "Calibri"))
        sig_text_font_sz = Pt(_parse_numeric_value(config.get("signature_text_font_size_docx", 9)))
        sig_text_font_color = _get_docx_color(config.get("signature_text_font_color_docx", "000000"))
        sig_space_after_pt = Pt(_parse_numeric_value(config.get("signature_space_between_vertical_docx_pt", 10)))

        if alignment_str.lower() == "horizontal" and len(sig_attachments_info) > 1:
            page_width_inches = (doc.sections[0].page_width - doc.sections[0].left_margin - doc.sections[0].right_margin) / Inches(1)
            max_cols = int(page_width_inches / (sig_img_width_final_inches + 0.5)) if sig_img_width_final_inches > 0 else 1
            max_cols = max(1, min(max_cols, len(sig_attachments_info), 3))
            num_rows = (len(sig_attachments_info) + max_cols - 1) // max_cols
            sig_table = doc.add_table(rows=num_rows, cols=max_cols)
            sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER

            for idx, sig_info in enumerate(sig_attachments_info):
                cell = sig_table.cell(idx // max_cols, idx % max_cols)
                if cell.paragraphs: cell.paragraphs[0]._p.getparent().remove(cell.paragraphs[0]._p) # Clear default para

                p_img = cell.add_paragraph(); p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                if sig_info["exists"]:
                    try: p_img.add_run().add_picture(sig_info["path"], width=Inches(sig_img_width_final_inches))
                    except Exception as e: p_img.add_run(f"[Img Err: {e}]")
                else: p_img.add_run(f"[Img Miss: {os.path.basename(sig_info['path'])}]")
                
                for text_line in ["___________________________", f"Signed by: {sig_info['author']}", f"Position: {sig_info['position']}"]:
                    p_text = cell.add_paragraph(text_line); p_text.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for run in p_text.runs:
                        run.font.name = sig_text_font_fam; run.font.size = sig_text_font_sz
                        if sig_text_font_color: run.font.color.rgb = sig_text_font_color
                p_text.paragraph_format.space_after = sig_space_after_pt # Space after the block
        else: # Vertical
            for sig_info in sig_attachments_info:
                p_img = doc.add_paragraph(); p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                if sig_info["exists"]:
                    try: p_img.add_run().add_picture(sig_info["path"], width=Inches(sig_img_width_final_inches))
                    except Exception as e: p_img.add_run(f"[Img Err: {e}]")
                else: p_img.add_run(f"[Img Miss: {os.path.basename(sig_info['path'])}]")
                
                for text_line in ["___________________________", f"Signed by: {sig_info['author']}", f"Position: {sig_info['position']}"]:
                    p_text = doc.add_paragraph(text_line); p_text.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for run in p_text.runs:
                        run.font.name = sig_text_font_fam; run.font.size = sig_text_font_sz
                        if sig_text_font_color: run.font.color.rgb = sig_text_font_color
                p_text.paragraph_format.space_after = sig_space_after_pt


    # ============================================================================
    # == REFACTORED EXPORT METHODS START HERE
    # ============================================================================
    @staticmethod
    def export_structured_submission_to_pdf(
        submission_id: int,
        upload_path: str,
        include_signatures: bool = True,
        header_image: Optional[Any] = None,
        header_opacity: float = 1.0,
        header_size: Optional[float] = None,
        header_width: Optional[float] = None,
        header_height: Optional[float] = None,
        header_alignment: str = "center",
        signatures_size: float = 100,
        signatures_alignment: str = "vertical",
        pdf_style_options: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[BytesIO], Optional[str]]:
        final_config = DEFAULT_STYLE_CONFIG.copy()
        if pdf_style_options:
            for key, value in pdf_style_options.items():
                if key in final_config: final_config[key] = value
                else: logger.warning(f"PDF Export: Unknown style option '{key}' provided.")

        buffer = BytesIO()
        try:
            submission = FormSubmission.query.options(
                joinedload(FormSubmission.form)
                    .joinedload(Form.form_questions)
                    .joinedload(FormQuestion.question)
                    .joinedload(Question.question_type),
                joinedload(FormSubmission.answers_submitted),
                joinedload(FormSubmission.attachments)
            ).filter_by(id=submission_id, is_deleted=False).first()

            if not submission: return None, "Submission not found"
            form = submission.form
            if not form: return None, "Form not found for submission"

            page_margin_top_val = _parse_numeric_value(final_config.get("page_margin_top"), 0.75) * inch
            page_margin_bottom_val = _parse_numeric_value(final_config.get("page_margin_bottom"), 0.75) * inch
            page_margin_left_val = _parse_numeric_value(final_config.get("page_margin_left"), 0.75) * inch
            page_margin_right_val = _parse_numeric_value(final_config.get("page_margin_right"), 0.75) * inch

            doc_pdf = SimpleDocTemplate(buffer, pagesize=letter,
                                        leftMargin=page_margin_left_val, rightMargin=page_margin_right_val,
                                        topMargin=page_margin_top_val, bottomMargin=page_margin_bottom_val)
            story: List[Flowable] = []
            styles_pdf = getSampleStyleSheet()

            # --- Define Custom Styles ---
            styles_pdf.add(ReportLabParagraphStyle(name='CustomTitle',
                                          fontName=str(final_config["title_font_family"]),
                                          fontSize=_parse_numeric_value(final_config["title_font_size"]),
                                          # CORRECTED: Parse title_font_size before multiplying
                                          leading=_parse_numeric_value(final_config.get("title_leading", _parse_numeric_value(final_config["title_font_size"]) * 1.2)),
                                          textColor=_get_color_rl(final_config["title_font_color"]),
                                          alignment=_get_alignment_code_rl(final_config["title_alignment"]),
                                          spaceAfter=_parse_numeric_value(final_config["title_space_after"]) * inch)) # Assuming title_space_after is in inches

            styles_pdf.add(ReportLabParagraphStyle(name='CustomDescription',
                                          fontName=str(final_config.get("description_font_family","Helvetica")),
                                          fontSize=_parse_numeric_value(final_config.get("description_font_size",10)),
                                          leading=_parse_numeric_value(final_config.get("description_leading",12)), # Assuming leading is points
                                          textColor=_get_color_rl(final_config.get("description_font_color",colors.darkslategray)),
                                          alignment=_get_alignment_code_rl(final_config.get("description_alignment",TA_LEFT)),
                                          spaceAfter=_parse_numeric_value(final_config.get("description_space_after",0.15))*inch)) # Assuming space_after is inches

            styles_pdf.add(ReportLabParagraphStyle(name='CustomSubmissionInfo',
                                          fontName=str(final_config["info_font_family"]),
                                          fontSize=_parse_numeric_value(final_config["info_font_size"]),
                                          # CORRECTED: Parse info_font_size before multiplying
                                          leading=_parse_numeric_value(final_config.get("info_leading", _parse_numeric_value(final_config["info_font_size"]) * 1.2)),
                                          textColor=_get_color_rl(final_config["info_font_color"]),
                                          alignment=_get_alignment_code_rl(final_config.get("info_alignment", TA_LEFT)),
                                          spaceAfter=_parse_numeric_value(final_config["info_space_after"]) * inch)) # Assuming info_space_after is inches

            styles_pdf.add(ReportLabParagraphStyle(name='CustomQuestion',
                                          fontName=str(final_config["question_font_family"]),
                                          fontSize=_parse_numeric_value(final_config["question_font_size"]),
                                          leading=_parse_numeric_value(final_config["question_leading"]),
                                          textColor=_get_color_rl(final_config["question_font_color"]),
                                          leftIndent=_parse_numeric_value(final_config.get("question_left_indent",0)) * inch, # Assuming question_left_indent is inches
                                          spaceBefore=_parse_numeric_value(final_config["question_space_before"]) * inch, # Assuming question_space_before is inches
                                          spaceAfter=_parse_numeric_value(final_config["question_space_after"]))) # Assuming question_space_after is points

            styles_pdf.add(ReportLabParagraphStyle(name='CustomAnswer',
                                          fontName=str(final_config["answer_font_family"]),
                                          fontSize=_parse_numeric_value(final_config["answer_font_size"]),
                                          leading=_parse_numeric_value(final_config["answer_leading"]),
                                          textColor=_get_color_rl(final_config["answer_font_color"]),
                                          leftIndent=_parse_numeric_value(final_config["answer_left_indent"]), # Assuming answer_left_indent is points
                                          spaceBefore=_parse_numeric_value(final_config["answer_space_before"]), # Assuming answer_space_before is points
                                          spaceAfter=_parse_numeric_value(final_config["answer_space_after"]) * inch)) # Assuming answer_space_after is inches

            styles_pdf.add(ReportLabParagraphStyle(name='CustomQACombined',
                                          fontName=str(final_config["question_font_family"]),
                                          fontSize=_parse_numeric_value(final_config["question_font_size"]),
                                          leading=_parse_numeric_value(final_config["question_leading"]),
                                          textColor=_get_color_rl(final_config["question_font_color"]),
                                          leftIndent=_parse_numeric_value(final_config.get("question_left_indent",0)) * inch,
                                          spaceBefore=_parse_numeric_value(final_config["question_space_before"]) * inch,
                                          spaceAfter=_parse_numeric_value(final_config["answer_space_after"]) * inch)) # Uses answer's space_after

            styles_pdf.add(ReportLabParagraphStyle(name='CustomTableHeader',
                                        fontName=str(final_config["table_header_font_family"]),
                                        fontSize=_parse_numeric_value(final_config["table_header_font_size"]),
                                        textColor=_get_color_rl(final_config["table_header_font_color"]),
                                        alignment=_get_alignment_code_rl(final_config["table_header_alignment"]),
                                        # CORRECTED: Parse table_header_font_size before multiplying
                                        leading=_parse_numeric_value(final_config.get("table_header_leading", _parse_numeric_value(final_config["table_header_font_size"])*1.2))))

            styles_pdf.add(ReportLabParagraphStyle(name='CustomTableCell',
                                        fontName=str(final_config["table_cell_font_family"]),
                                        fontSize=_parse_numeric_value(final_config["table_cell_font_size"]),
                                        textColor=_get_color_rl(final_config["table_cell_font_color"]),
                                        alignment=_get_alignment_code_rl(final_config["table_cell_alignment"]),
                                        # CORRECTED: Parse table_cell_font_size before multiplying
                                        leading=_parse_numeric_value(final_config.get("table_cell_leading",_parse_numeric_value(final_config["table_cell_font_size"])*1.2))))

            styles_pdf.add(ReportLabParagraphStyle(name='CustomTableError',
                                        fontName=str(final_config["table_cell_font_family"]),
                                        # CORRECTED: Parse table_cell_font_size before arithmetic
                                        fontSize=_parse_numeric_value(final_config["table_cell_font_size"])-1,
                                        textColor=colors.red,
                                        alignment=TA_LEFT,
                                        # CORRECTED: Parse table_cell_font_size for default leading calc
                                        leading=_parse_numeric_value(final_config.get("table_cell_leading",_parse_numeric_value(final_config["table_cell_font_size"])*1.2)),
                                        spaceBefore=2, spaceAfter=2))

            styles_pdf.add(ReportLabParagraphStyle(name='CustomSignatureLabel',
                                      fontName=str(final_config.get("signature_label_font_family", "Helvetica-Bold")),
                                      fontSize=_parse_numeric_value(final_config.get("signature_label_font_size", 12)),
                                      textColor=_get_color_rl(final_config.get("signature_label_font_color", colors.black)),
                                      spaceBefore=_parse_numeric_value(final_config.get("signature_section_space_before", 0.3)) * inch, # Assuming inches
                                      spaceAfter=4)) # Points

            styles_pdf.add(ReportLabParagraphStyle(name='CustomSignatureText',
                                      fontName=str(final_config.get("signature_text_font_family", "Helvetica")),
                                      fontSize=_parse_numeric_value(final_config.get("signature_text_font_size", 9)),
                                      textColor=_get_color_rl(final_config.get("signature_text_font_color", colors.black)),
                                      # CORRECTED: Parse signature_text_font_size before multiplying
                                      leading=_parse_numeric_value(final_config.get("signature_text_font_size", 9)) * 1.2))
            styles_pdf.PAGE_WIDTH = letter[0]; styles_pdf.LEFT_MARGIN = page_margin_left_val; styles_pdf.RIGHT_MARGIN = page_margin_right_val # For helpers

            if header_image:
                ExportSubmissionService._add_header_image_to_reportlab_story(
                    story, header_image, upload_path, header_opacity, header_size,
                    header_width, header_height, header_alignment,
                    doc_pdf.leftMargin, doc_pdf.rightMargin, doc_pdf.width # Corrected call
                )

            if form.title: story.append(ReportLabParagraph(form.title, styles_pdf['CustomTitle']))
            if form.description: story.append(ReportLabParagraph(form.description.replace('\n', '<br/>\n') if form.description else "", styles_pdf['CustomDescription']))
            info_text = f"<b>Submitted by:</b> {submission.submitted_by or 'N/A'}<br/><b>Date:</b> {submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if submission.submitted_at else 'N/A'}"
            story.append(ReportLabParagraph(info_text, styles_pdf['CustomSubmissionInfo']))

            all_submitted_answers_map = {
                (str(ans.question).strip(), str(ans.question_type).lower().strip()): ans
                for ans in submission.answers_submitted
                if ans.question and ans.question_type and ans.question_type.lower() not in ['table', 'signature']
            }
            choice_submitted_answers_grouped = defaultdict(list)
            for ans in submission.answers_submitted:
                if ans.question and ans.question_type and \
                   ans.question_type.lower() in ['dropdown', 'select', 'multiselect', 'checkbox', 'multiple_choices', 'single_choice']:
                    choice_submitted_answers_grouped[str(ans.question).strip()].append(ans)

            ordered_form_questions = form.form_questions
            qa_layout = str(final_config.get("qa_layout", "answer_below"))
            answer_same_line_max_len = int(_parse_numeric_value(final_config.get("answer_same_line_max_length"), 70))
            answer_color_for_html = _color_to_hex_string_rl(final_config["answer_font_color"])
            processed_questions_text_for_pdf = set()

            for form_question_assoc in ordered_form_questions:
                if form_question_assoc.is_deleted or not form_question_assoc.question or form_question_assoc.question.is_deleted: continue
                question_model = form_question_assoc.question
                q_text_p = str(question_model.text or "Untitled Question").strip()
                q_type_p = str(question_model.question_type.type.lower() if question_model.question_type and hasattr(question_model.question_type, 'type') else "").strip()

                if q_text_p in processed_questions_text_for_pdf and q_type_p not in ['table', 'signature']: continue
                if q_type_p not in ['table', 'signature']: processed_questions_text_for_pdf.add(q_text_p)
                if q_type_p == 'table' or q_type_p == 'signature': continue

                ans_val_p = "No answer provided"
                choice_based_types = ['dropdown', 'select', 'multiselect', 'checkbox', 'multiple_choices', 'single_choice']
                if q_type_p in choice_based_types:
                    submitted_choices = choice_submitted_answers_grouped.get(q_text_p, [])
                    combined_options = []
                    for choice_ans_submitted in submitted_choices:
                        if choice_ans_submitted.answer is not None and str(choice_ans_submitted.answer).strip() != "":
                            try:
                                parsed_json_options = json.loads(choice_ans_submitted.answer)
                                if isinstance(parsed_json_options, list): combined_options.extend([str(item).strip() for item in parsed_json_options if str(item).strip()])
                                elif str(parsed_json_options).strip(): combined_options.append(str(parsed_json_options).strip())
                            except json.JSONDecodeError:
                                if str(choice_ans_submitted.answer).strip(): combined_options.append(str(choice_ans_submitted.answer).strip())
                    unique_options = list(dict.fromkeys(opt for opt in combined_options if opt))
                    ans_val_p = ", ".join(unique_options) if unique_options else "No selection"
                else:
                    ans_submitted_obj = all_submitted_answers_map.get((q_text_p, q_type_p))
                    if ans_submitted_obj and ans_submitted_obj.answer is not None: ans_val_p = str(ans_submitted_obj.answer)
                
                ans_val_p_display = ans_val_p.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>\n')
                q_text_p_display = q_text_p.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>\n')

                if qa_layout == "answer_same_line" and len(ans_val_p) <= answer_same_line_max_len and '\n' not in ans_val_p:
                    combined_text = f"<b>{q_text_p_display}:</b> <font color='{answer_color_for_html}'>{ans_val_p_display}</font>"
                    story.append(ReportLabParagraph(combined_text, styles_pdf['CustomQACombined']))
                else: # answer_below
                    story.append(ReportLabParagraph(q_text_p_display, styles_pdf['CustomQuestion']))
                    story.append(ReportLabParagraph(ans_val_p_display, styles_pdf['CustomAnswer']))

            table_answers_submitted = [ans for ans in submission.answers_submitted if ans.question_type and ans.question_type.lower() == 'table']
            cell_based_tables_data = defaultdict(lambda: {'name': '', 'headers': {}, 'cells': {}, 'row_indices': set(), 'col_indices': set(), 'header_row_present': False})
            for ans_cell in table_answers_submitted:
                table_id = str(ans_cell.question or "Unnamed Table").strip()
                cell_based_tables_data[table_id]['name'] = table_id
                cell_content_str = str(ans_cell.cell_content if ans_cell.cell_content is not None else ans_cell.answer or "").strip()
                try:
                    row_idx, col_idx = int(ans_cell.row), int(ans_cell.column)
                    if row_idx == 0:
                        cell_based_tables_data[table_id]['headers'][col_idx] = cell_content_str
                        cell_based_tables_data[table_id]['col_indices'].add(col_idx)
                        cell_based_tables_data[table_id]['header_row_present'] = True
                    elif row_idx > 0:
                        cell_based_tables_data[table_id]['cells'][(row_idx, col_idx)] = cell_content_str
                        cell_based_tables_data[table_id]['row_indices'].add(row_idx)
                        cell_based_tables_data[table_id]['col_indices'].add(col_idx)
                except (ValueError, TypeError): logger.warning(f"PDF: Invalid table cell index for table '{table_id}'. Skipping."); continue

            for fq_assoc_table in ordered_form_questions:
                if fq_assoc_table.is_deleted or not fq_assoc_table.question or fq_assoc_table.question.is_deleted: continue
                q_model_table = fq_assoc_table.question
                q_text_table = str(q_model_table.text or "Unnamed Table").strip()
                q_type_table = str(q_model_table.question_type.type.lower() if q_model_table.question_type and hasattr(q_model_table.question_type, 'type') else "").strip()

                if q_type_table == 'table':
                    story.append(ReportLabParagraph(q_text_table.replace('\n', '<br/>\n'), styles_pdf['CustomQuestion']))
                    table_data_render = cell_based_tables_data.get(q_text_table)
                    if table_data_render and (table_data_render['headers'] or table_data_render['cells']):
                        all_cols = sorted(list(table_data_render['col_indices']))
                        if not all_cols:
                            story.append(ReportLabParagraph("Table has no columns.", styles_pdf['CustomTableError'])); continue
                        table_rows_styled = []
                        if table_data_render['header_row_present']:
                            header_styled_row = [ReportLabParagraph(str(table_data_render['headers'].get(c, '')).replace('\n', '<br/>\n'), styles_pdf['CustomTableHeader']) for c in all_cols]
                            table_rows_styled.append(header_styled_row)
                        data_row_indices = sorted(list(r for r in table_data_render['row_indices'] if r > 0))
                        for r_idx in data_row_indices:
                            row_styled = [ReportLabParagraph(str(table_data_render['cells'].get((r_idx, c), '')).replace('\n', '<br/>\n'), styles_pdf['CustomTableCell']) for c in all_cols]
                            table_rows_styled.append(row_styled)
                        if not table_rows_styled: story.append(ReportLabParagraph("No data for this table.", styles_pdf['CustomAnswer']))
                        else:
                            rl_table = ReportLabTable(table_rows_styled, repeatRows=(1 if table_data_render['header_row_present'] else 0))
                            ts = ReportLabTableStyle([
                                ('GRID', (0,0), (-1,-1), _parse_numeric_value(final_config["table_grid_thickness"]), _get_color_rl(final_config["table_grid_color"])),
                                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                                ('LEFTPADDING', (0,0), (-1,-1), _parse_numeric_value(final_config["table_cell_padding_left"])),
                                ('RIGHTPADDING', (0,0), (-1,-1), _parse_numeric_value(final_config["table_cell_padding_right"])),
                                ('TOPPADDING', (0,0), (-1,-1), _parse_numeric_value(final_config["table_cell_padding_top"])),
                                ('BOTTOMPADDING', (0,0), (-1,-1), _parse_numeric_value(final_config["table_cell_padding_bottom"])),
                            ])
                            if table_data_render['header_row_present']: ts.add('BACKGROUND', (0,0), (-1,0), _get_color_rl(final_config["table_header_bg_color"]))
                            rl_table.setStyle(ts)
                            story.append(rl_table)
                            story.append(Spacer(1, _parse_numeric_value(final_config.get("table_space_after", 0.15)) * inch))
                    else: story.append(ReportLabParagraph("No data submitted for this table.", styles_pdf['CustomAnswer']))

            if include_signatures:
                ExportSubmissionService._add_signatures_to_reportlab_story(story, submission.attachments, upload_path, signatures_size / 100.0, signatures_alignment, styles_pdf, final_config)

            doc_pdf.build(story)
            buffer.seek(0)
            return buffer, None
        except Exception as e:
            logger.error(f"Error exporting structured submission to PDF: {submission_id} - {str(e)}", exc_info=True)
            return None, f"An error occurred during PDF generation: {str(e)}"

    @staticmethod
    def export_submission_to_pdf(*args, **kwargs): # Wrapper remains same
        return ExportSubmissionService.export_structured_submission_to_pdf(*args, **kwargs)

    @staticmethod
    def _get_signature_images(submission_id: int, upload_path: str) -> List[Dict]: # Remains same
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
                "path": file_path_item, "position": sig_pos_item or "Signature",
                "author": sig_auth_item or "Signer", "exists": exists_bool
            })
        return signatures_list

    @staticmethod
    def export_submission_to_docx(
        submission_id: int, upload_path: str, include_signatures: bool = True,
        style_options: Optional[Dict[str, Any]] = None, header_image_file: Optional[Any] = None,
        header_size_percent: Optional[float] = None, header_width_px: Optional[float] = None,
        header_height_px: Optional[float] = None, header_alignment_str: str = "center",
        signatures_size_percent: float = 100, signatures_alignment_str: str = "vertical"
    ) -> Tuple[Optional[BytesIO], Optional[str]]:
        final_config_docx = DEFAULT_STYLE_CONFIG.copy()
        if style_options:
            for key, value in style_options.items():
                final_config_docx[key] = value # Allow overriding or adding new keys for DOCX

        try:
            submission = FormSubmission.query.options(
                joinedload(FormSubmission.form).joinedload(Form.form_questions).joinedload(FormQuestion.question).joinedload(Question.question_type),
                joinedload(FormSubmission.answers_submitted), joinedload(FormSubmission.attachments)
            ).filter_by(id=submission_id, is_deleted=False).first()

            if not submission: return None, "Submission not found"
            form = submission.form
            if not form: return None, "Form not found for submission"

            doc = Document()
            style = doc.styles['Normal']; font = style.font # Base font style
            font.name = str(final_config_docx.get("default_font_family_docx", "Calibri"))
            font.size = Pt(_parse_numeric_value(final_config_docx.get("default_font_size_docx", 11)))
            font.color.rgb = _get_docx_color(final_config_docx.get("default_font_color_docx", "000000"))
            for section in doc.sections:
                section.top_margin = Inches(_parse_numeric_value(final_config_docx.get("page_margin_top"), 0.75))
                section.bottom_margin = Inches(_parse_numeric_value(final_config_docx.get("page_margin_bottom"), 0.75))
                section.left_margin = Inches(_parse_numeric_value(final_config_docx.get("page_margin_left"), 0.75))
                section.right_margin = Inches(_parse_numeric_value(final_config_docx.get("page_margin_right"), 0.75))

            if header_image_file:
                ExportSubmissionService._add_header_image_to_docx_header(doc, header_image_file, upload_path, header_size_percent, header_width_px, header_height_px, header_alignment_str)

            if form.title:
                title_p = doc.add_paragraph(); title_run = title_p.add_run(form.title)
                title_run.font.name = str(final_config_docx.get("title_font_family_docx", font.name)); title_run.font.size = Pt(_parse_numeric_value(final_config_docx.get("title_font_size_docx", 22))); title_run.bold = True
                title_run.font.color.rgb = _get_docx_color(final_config_docx.get("title_font_color_docx", "000000")); title_p.alignment = _get_docx_alignment(final_config_docx.get("title_alignment_docx", "center"))
                title_p.paragraph_format.space_after = Pt(_parse_numeric_value(final_config_docx.get("title_space_after_docx", 12)))
            if form.description:
                desc_p = doc.add_paragraph()
                for line in (form.description or "").split('\n'): desc_p.add_run(line).add_break()
                if desc_p.runs: desc_p.runs[-1].clear()
                for run in desc_p.runs:
                    run.font.name = str(final_config_docx.get("description_font_family_docx", font.name)); run.font.size = Pt(_parse_numeric_value(final_config_docx.get("description_font_size_docx", 10)))
                    run.font.color.rgb = _get_docx_color(final_config_docx.get("description_font_color_docx", "2F4F4F"))
                desc_p.alignment = _get_docx_alignment(final_config_docx.get("description_alignment_docx", "left")); desc_p.paragraph_format.space_after = Pt(_parse_numeric_value(final_config_docx.get("description_space_after_docx", 6)))

            info_p = doc.add_paragraph(); info_p.add_run("Submitted by: ").bold = True; info_p.add_run(f"{submission.submitted_by or 'N/A'}\n"); info_p.add_run("Date: ").bold = True
            info_p.add_run(submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if submission.submitted_at else 'N/A')
            for run in info_p.runs:
                run.font.name = str(final_config_docx.get("info_font_family_docx", font.name)); run.font.size = Pt(_parse_numeric_value(final_config_docx.get("info_font_size_docx", 9)))
                run.font.color.rgb = _get_docx_color(final_config_docx.get("info_font_color_docx", "2F4F4F"))
            info_p.alignment = _get_docx_alignment(final_config_docx.get("info_alignment_docx", "left")); info_p.paragraph_format.space_after = Pt(_parse_numeric_value(final_config_docx.get("info_space_after_docx", 12)))

            all_submitted_answers_map_docx = { (str(ans.question).strip(), str(ans.question_type).lower().strip()): ans for ans in submission.answers_submitted if ans.question and ans.question_type and ans.question_type.lower() not in ['table', 'signature']}
            choice_submitted_answers_grouped_docx = defaultdict(list)
            for ans in submission.answers_submitted:
                if ans.question and ans.question_type and ans.question_type.lower() in ['dropdown', 'select', 'multiselect', 'checkbox', 'multiple_choices', 'single_choice']:
                    choice_submitted_answers_grouped_docx[str(ans.question).strip()].append(ans)
            ordered_form_questions_docx = form.form_questions
            qa_layout_pref_docx = str(final_config_docx.get("qa_layout", "answer_below"))
            ans_same_line_max_len_docx = int(_parse_numeric_value(final_config_docx.get("answer_same_line_max_length"), 70))
            processed_questions_text_for_docx = set()

            for form_question_assoc_docx in ordered_form_questions_docx:
                if form_question_assoc_docx.is_deleted or not form_question_assoc_docx.question or form_question_assoc_docx.question.is_deleted: continue
                question_model_docx = form_question_assoc_docx.question
                q_text_val_docx = str(question_model_docx.text or "Untitled Question").strip()
                q_type_val_docx = str(question_model_docx.question_type.type.lower() if question_model_docx.question_type and hasattr(question_model_docx.question_type, 'type') else "").strip()
                if q_text_val_docx in processed_questions_text_for_docx and q_type_val_docx not in ['table', 'signature']: continue
                if q_type_val_docx not in ['table', 'signature']: processed_questions_text_for_docx.add(q_text_val_docx)
                if q_type_val_docx == 'table' or q_type_val_docx == 'signature': continue

                ans_text_val_docx = "No answer provided"
                choice_based_types_docx = ['dropdown', 'select', 'multiselect', 'checkbox', 'multiple_choices', 'single_choice']
                if q_type_val_docx in choice_based_types_docx:
                    submitted_choices_docx = choice_submitted_answers_grouped_docx.get(q_text_val_docx, [])
                    combined_options_docx = []
                    for choice_ans_submitted_docx in submitted_choices_docx:
                        if choice_ans_submitted_docx.answer is not None and str(choice_ans_submitted_docx.answer).strip() != "":
                            try:
                                parsed_json_options_docx = json.loads(choice_ans_submitted_docx.answer)
                                if isinstance(parsed_json_options_docx, list): combined_options_docx.extend([str(item).strip() for item in parsed_json_options_docx if str(item).strip()])
                                elif str(parsed_json_options_docx).strip(): combined_options_docx.append(str(parsed_json_options_docx).strip())
                            except json.JSONDecodeError:
                                if str(choice_ans_submitted_docx.answer).strip(): combined_options_docx.append(str(choice_ans_submitted_docx.answer).strip())
                    unique_options_docx = list(dict.fromkeys(opt for opt in combined_options_docx if opt))
                    ans_text_val_docx = ", ".join(unique_options_docx) if unique_options_docx else "No selection"
                else:
                    ans_submitted_obj_docx = all_submitted_answers_map_docx.get((q_text_val_docx, q_type_val_docx))
                    if ans_submitted_obj_docx and ans_submitted_obj_docx.answer is not None: ans_text_val_docx = str(ans_submitted_obj_docx.answer)

                if qa_layout_pref_docx == "answer_same_line" and len(ans_text_val_docx) <= ans_same_line_max_len_docx and '\n' not in ans_text_val_docx:
                    p_qa = doc.add_paragraph(); q_run = p_qa.add_run(f"{q_text_val_docx}: ")
                    q_run.font.name = str(final_config_docx.get("question_font_family_docx", font.name)); q_run.font.size = Pt(_parse_numeric_value(final_config_docx.get("question_font_size_docx", 12))); q_run.bold = True
                    q_run.font.color.rgb = _get_docx_color(final_config_docx.get("question_font_color_docx", "000000"))
                    a_run = p_qa.add_run(ans_text_val_docx)
                    a_run.font.name = str(final_config_docx.get("answer_font_family_docx", font.name)); a_run.font.size = Pt(_parse_numeric_value(final_config_docx.get("answer_font_size_docx", 10)))
                    a_run.font.color.rgb = _get_docx_color(final_config_docx.get("answer_font_color_docx", "2F4F4F"))
                    p_qa.paragraph_format.space_before = Pt(_parse_numeric_value(final_config_docx.get("question_space_before_docx", 8))); p_qa.paragraph_format.space_after = Pt(_parse_numeric_value(final_config_docx.get("answer_space_after_docx", 6)))
                else:
                    q_p = doc.add_paragraph()
                    for line in q_text_val_docx.split('\n'): q_p.add_run(line).add_break()
                    if q_p.runs: q_p.runs[-1].clear()
                    for run in q_p.runs: run.font.name = str(final_config_docx.get("question_font_family_docx", font.name)); run.font.size = Pt(_parse_numeric_value(final_config_docx.get("question_font_size_docx", 12))); run.bold = True; run.font.color.rgb = _get_docx_color(final_config_docx.get("question_font_color_docx", "000000"))
                    q_p.paragraph_format.space_before = Pt(_parse_numeric_value(final_config_docx.get("question_space_before_docx", 8))); q_p.paragraph_format.space_after = Pt(_parse_numeric_value(final_config_docx.get("question_space_after_docx", 3)))
                    a_p = doc.add_paragraph()
                    for line in ans_text_val_docx.split('\n'): a_p.add_run(line).add_break()
                    if a_p.runs: a_p.runs[-1].clear()
                    for run in a_p.runs: run.font.name = str(final_config_docx.get("answer_font_family_docx", font.name)); run.font.size = Pt(_parse_numeric_value(final_config_docx.get("answer_font_size_docx", 10))); run.font.color.rgb = _get_docx_color(final_config_docx.get("answer_font_color_docx", "2F4F4F"))
                    a_p.paragraph_format.left_indent = Inches(_parse_numeric_value(final_config_docx.get("answer_left_indent_docx", 0.25))); a_p.paragraph_format.space_after = Pt(_parse_numeric_value(final_config_docx.get("answer_space_after_docx", 6)))

            table_answers_submitted_docx = [ans for ans in submission.answers_submitted if ans.question_type and ans.question_type.lower() == 'table']
            cell_based_tables_data_docx = defaultdict(lambda: {'name': '', 'headers': {}, 'cells': {}, 'row_indices': set(), 'col_indices': set(), 'header_row_present': False})
            for ans_cell_docx in table_answers_submitted_docx:
                table_id_docx = str(ans_cell_docx.question or "Unnamed Table").strip()
                cell_based_tables_data_docx[table_id_docx]['name'] = table_id_docx
                cell_content_str_docx = str(ans_cell_docx.cell_content if ans_cell_docx.cell_content is not None else ans_cell_docx.answer or "").strip()
                try:
                    row_idx_docx, col_idx_docx = int(ans_cell_docx.row), int(ans_cell_docx.column) # Error if row/col is None
                    if row_idx_docx == 0:
                        cell_based_tables_data_docx[table_id_docx]['headers'][col_idx_docx] = cell_content_str_docx
                    elif row_idx_docx > 0:
                        cell_based_tables_data_docx[table_id_docx]['cells'][(row_idx_docx, col_idx_docx)] = cell_content_str_docx
                except (ValueError, TypeError):
                    logger.warning(f"DOCX: Invalid table cell index for table '{table_id_docx}' (row='{ans_cell_docx.row}', col='{ans_cell_docx.column}'). Skipping cell.")
                    continue

            for fq_assoc_table_docx in ordered_form_questions_docx:
                if fq_assoc_table_docx.is_deleted or not fq_assoc_table_docx.question or fq_assoc_table_docx.question.is_deleted: continue
                q_model_table_docx = fq_assoc_table_docx.question
                q_text_table_docx = str(q_model_table_docx.text or "Unnamed Table").strip()
                q_type_table_docx = str(q_model_table_docx.question_type.type.lower() if q_model_table_docx.question_type and hasattr(q_model_table_docx.question_type, 'type') else "").strip()

                if q_type_table_docx == 'table':
                    tbl_title_p_docx = doc.add_paragraph(); tbl_title_run_docx = tbl_title_p_docx.add_run(q_text_table_docx.split('\n')[0])
                    tbl_title_run_docx.font.name = str(final_config_docx.get("question_font_family_docx", font.name)); tbl_title_run_docx.font.size = Pt(_parse_numeric_value(final_config_docx.get("question_font_size_docx", 12))); tbl_title_run_docx.bold = True
                    tbl_title_run_docx.font.color.rgb = _get_docx_color(final_config_docx.get("question_font_color_docx", "000000")); tbl_title_p_docx.paragraph_format.space_before = Pt(_parse_numeric_value(final_config_docx.get("question_space_before_docx", 8))); tbl_title_p_docx.paragraph_format.space_after = Pt(_parse_numeric_value(final_config_docx.get("question_space_after_docx", 3)))
                    table_data_render_docx = cell_based_tables_data_docx.get(q_text_table_docx)
                    if table_data_render_docx and (table_data_render_docx['headers'] or table_data_render_docx['cells']):
                        all_cols_docx = sorted(list(table_data_render_docx['col_indices']))
                        if not all_cols_docx: doc.add_paragraph("Table has no columns.").paragraph_format.space_after = Pt(_parse_numeric_value(final_config_docx.get("table_space_after_docx", 12))); continue
                        num_data_rows = len(set(r for r in table_data_render_docx['row_indices'] if r > 0))
                        total_docx_rows = (1 if table_data_render_docx['header_row_present'] else 0) + num_data_rows
                        if total_docx_rows == 0: doc.add_paragraph("No data for this table.").paragraph_format.space_after = Pt(_parse_numeric_value(final_config_docx.get("table_space_after_docx", 12))); continue
                        docx_table_obj = doc.add_table(rows=total_docx_rows, cols=len(all_cols_docx)); docx_table_obj.style = str(final_config_docx.get('table_style_docx', 'TableGrid')); docx_table_obj.alignment = _get_docx_alignment(final_config_docx.get("table_alignment_docx", "center"), WD_ALIGN_PARAGRAPH.CENTER)
                        if table_data_render_docx['header_row_present']:
                            header_cells_docx = docx_table_obj.rows[0].cells
                            for c_idx, actual_col_idx in enumerate(all_cols_docx):
                                cell_p = header_cells_docx[c_idx].paragraphs[0]; cell_p.text = str(table_data_render_docx['headers'].get(actual_col_idx, '')); cell_p.alignment = _get_docx_alignment(final_config_docx.get("table_header_alignment_docx", "center"))
                                for run in cell_p.runs: run.font.name = str(final_config_docx.get("table_header_font_family_docx", font.name)); run.font.size = Pt(_parse_numeric_value(final_config_docx.get("table_header_font_size_docx", 10))); run.bold = True; run.font.color.rgb = _get_docx_color(final_config_docx.get("table_header_font_color_docx", "000000"))
                                _set_cell_background_docx(header_cells_docx[c_idx], str(final_config_docx.get("table_header_bg_color_docx", "D3D3D3")))
                        current_docx_data_row = 1 if table_data_render_docx['header_row_present'] else 0
                        data_row_indices_docx = sorted(list(r for r in table_data_render_docx['row_indices'] if r > 0))
                        for r_form_idx in data_row_indices_docx:
                            if current_docx_data_row >= total_docx_rows: break
                            row_cells_docx = docx_table_obj.rows[current_docx_data_row].cells
                            for c_idx, actual_col_idx in enumerate(all_cols_docx):
                                cell_p_data = row_cells_docx[c_idx].paragraphs[0]; cell_p_data.text = str(table_data_render_docx['cells'].get((r_form_idx, actual_col_idx), '')); cell_p_data.alignment = _get_docx_alignment(final_config_docx.get("table_cell_alignment_docx", "left"))
                                for run in cell_p_data.runs: run.font.name = str(final_config_docx.get("table_cell_font_family_docx", font.name)); run.font.size = Pt(_parse_numeric_value(final_config_docx.get("table_cell_font_size_docx", 9))); run.font.color.rgb = _get_docx_color(final_config_docx.get("table_cell_font_color_docx", "000000"))
                            current_docx_data_row += 1
                        doc.add_paragraph().paragraph_format.space_after = Pt(_parse_numeric_value(final_config_docx.get("table_space_after_docx", 12)))
                    else: doc.add_paragraph("No data submitted for this table.").paragraph_format.space_after = Pt(_parse_numeric_value(final_config_docx.get("table_space_after_docx", 12)))

            if include_signatures:
                ExportSubmissionService._add_signatures_to_docx(doc, submission.attachments, upload_path, signatures_size_percent, signatures_alignment_str, final_config_docx)

            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            return buffer, None
        except Exception as e:
            logger.error(f"Error exporting submission {submission_id} to DOCX: {str(e)}", exc_info=True)
            return None, f"An error occurred during DOCX generation: {str(e)}"