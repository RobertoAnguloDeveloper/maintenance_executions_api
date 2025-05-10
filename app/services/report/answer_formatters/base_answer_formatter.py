# app/services/report/answer_formatters/base_answer_formatter.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Flowable
import logging

logger = logging.getLogger(__name__)

class BaseAnswerFormatter(ABC):
    """Base class for answer formatters"""
    
    @abstractmethod
    def format(self, answer_text: str, styles: Dict) -> List[Flowable]:
        """Format an answer into ReportLab flowables"""
        pass