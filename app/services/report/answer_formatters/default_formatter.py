# app/services/report/answer_formatters/default_formatter.py
# Simplify to ensure it always works

from typing import List, Dict
import logging
from reportlab.platypus import Flowable, Paragraph

logger = logging.getLogger(__name__)

class DefaultAnswerFormatter:
    """Default formatter for question types without specific formatters"""
    
    def format(self, answer_text: str, styles: Dict) -> List[Flowable]:
        """Format answer as simple paragraph"""
        try:
            if answer_text is None or answer_text.strip() == "":
                return [Paragraph("No answer provided", styles['Answer'])]
            return [Paragraph(answer_text, styles['Answer'])]
        except Exception as e:
            logger.error(f"Error in default formatter: {str(e)}")
            # Ultra-safe fallback
            return [Paragraph("Error displaying answer", styles['Normal'])]