# app/services/report/answer_formatter_factory.py
from typing import Dict

from app.services.report.answer_formatters.base_answer_formatter import BaseAnswerFormatter
from app.services.report.answer_formatters.default_formatter import DefaultAnswerFormatter
from app.services.report.answer_formatters.dropdown_formatter import DropdownAnswerFormatter
from app.services.report.answer_formatters.table_formatter import TableAnswerFormatter


class AnswerFormatterFactory:
    """Factory for creating answer formatters based on question type"""
    
    _formatters: Dict[str, BaseAnswerFormatter] = {
        "table": TableAnswerFormatter(),
        "dropdown": DropdownAnswerFormatter(),
        "select": DropdownAnswerFormatter(),  # Treat select same as dropdown
        # Add more formatters here as needed
    }
    
    @classmethod
    def get_formatter(cls, question_type: str) -> BaseAnswerFormatter:
        """Get the appropriate formatter for a question type"""
        if question_type is None:
            return DefaultAnswerFormatter()
            
        question_type = question_type.lower()
        return cls._formatters.get(question_type, DefaultAnswerFormatter())