# app/services/report/answer_formatters/dropdown_formatter.py
from typing import List, Dict
from reportlab.platypus import Flowable, Paragraph
from .base_answer_formatter import BaseAnswerFormatter
import json
import logging

logger = logging.getLogger(__name__)

class DropdownAnswerFormatter(BaseAnswerFormatter):
    """Formatter for dropdown question types"""
    
    def format(self, answer_text: str, styles: Dict) -> List[Flowable]:
        """Format dropdown answer text into ReportLab flowables"""
        if not answer_text or answer_text.strip() == "":
            return [Paragraph("No selection made", styles['Answer'])]
            
        try:
            # Check if it's a multi-select dropdown (might be JSON array)
            try:
                data = json.loads(answer_text)
                if isinstance(data, list):
                    # Format as a bulleted list
                    bullets = ""
                    for item in data:
                        bullets += f"• {item}<br/>"
                    return [Paragraph(bullets, styles['Answer'])]
                else:
                    # Single value as JSON
                    return [Paragraph(str(data), styles['Answer'])]
            except json.JSONDecodeError:
                # Not JSON, just return the text
                return [Paragraph(answer_text, styles['Answer'])]
        except Exception as e:
            logger.error(f"Error formatting dropdown answer: {str(e)}")
            return [Paragraph(answer_text, styles['Answer'])]