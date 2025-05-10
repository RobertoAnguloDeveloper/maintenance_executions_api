# app/services/report/answer_formatters/default_formatter.py
from typing import List, Dict
from reportlab.platypus import Flowable, Paragraph
from .base_answer_formatter import BaseAnswerFormatter

class DefaultAnswerFormatter(BaseAnswerFormatter):
    """Default formatter for question types without specific formatters"""
    
    def format(self, answer_text: str, styles: Dict) -> List[Flowable]:
        """Format answer as simple paragraph"""
        if answer_text is None:
            answer_text = "No answer provided"
        return [Paragraph(answer_text, styles['Answer'])]