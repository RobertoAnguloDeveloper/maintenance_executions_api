# services/export_service.py

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from weasyprint import HTML, CSS
import pandas as pd
import json
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from werkzeug.exceptions import BadRequest

logger = logging.getLogger(__name__)

class ExportService:
    def __init__(self):
        self.supported_formats = ['PNG', 'JPG', 'PDF', 'CSV', 'XLSX']
        self.font_path = os.path.join(os.path.dirname(__file__), '../static/fonts/Arial.ttf')
        self.form_width = 1200
        self.form_height = 1600
        self.margin = 40
        
    def export_as_image(self, form_data: Dict[str, Any], format: str = 'PNG') -> bytes:
        """
        Export form as image
        
        Args:
            form_data: Dictionary containing form data including:
                - title: Form title
                - questions: List of questions
                - answers: List of answers (optional)
                - signature: Base64 encoded signature image (optional)
            format: Output format ('PNG' or 'JPG')
            
        Returns:
            bytes: Image data in specified format
        """
        try:
            if format not in ['PNG', 'JPG']:
                raise ValueError(f"Unsupported image format: {format}")

            # Create blank image with white background
            img = Image.new('RGB', (self.form_width, self.form_height), 'white')
            draw = ImageDraw.Draw(img)

            # Load font
            title_font = ImageFont.truetype(self.font_path, 36)
            normal_font = ImageFont.truetype(self.font_path, 24)

            # Draw form title
            title = form_data.get('title', 'Untitled Form')
            draw.text((self.margin, self.margin), title, font=title_font, fill='black')

            y_position = self.margin + 80
            questions = form_data.get('questions', [])
            answers = form_data.get('answers', {})

            # Draw questions and answers
            for i, question in enumerate(questions, 1):
                # Draw question
                question_text = f"{i}. {question['text']}"
                draw.text((self.margin, y_position), question_text, font=normal_font, fill='black')
                y_position += 40

                # Draw answer if available
                answer = answers.get(str(question['id']), '')
                if answer:
                    draw.text((self.margin + 20, y_position), f"Answer: {answer}", 
                            font=normal_font, fill='darkblue')
                    y_position += 40

                y_position += 20

            # Add signature if present
            signature = form_data.get('signature')
            if signature:
                try:
                    # Convert base64 signature to image and paste
                    sig_img = Image.open(BytesIO(signature))
                    sig_img = sig_img.resize((300, 100), Image.Resampling.LANCZOS)
                    img.paste(sig_img, (self.margin, y_position))
                    y_position += 120
                except Exception as e:
                    logger.error(f"Error processing signature: {str(e)}")

            # Add timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            draw.text((self.margin, y_position), f"Generated: {timestamp}", 
                     font=normal_font, fill='gray')

            # Convert to output format
            output = BytesIO()
            img.save(output, format=format.upper())
            return output.getvalue()

        except Exception as e:
            logger.error(f"Error generating {format} image: {str(e)}")
            raise BadRequest(f"Error generating {format} image: {str(e)}")

    def _draw_question_answer(self, draw, question: Dict, answer: str, 
                            y_pos: int, font) -> int:
        """Helper method to draw question and answer on image"""
        question_text = f"Q: {question['text']}"
        draw.text((self.margin, y_pos), question_text, font=font, fill='black')
        y_pos += 30
        
        if answer:
            answer_text = f"A: {answer}"
            draw.text((self.margin + 20, y_pos), answer_text, font=font, fill='blue')
            y_pos += 30
            
        return y_pos + 10

    @staticmethod
    def get_supported_formats() -> List[str]:
        """Get list of supported export formats"""
        return ['PNG', 'JPG', 'PDF', 'CSV', 'XLSX']

    def validate_format(self, format: str) -> None:
        """Validate export format"""
        if format.upper() not in self.supported_formats:
            raise ValueError(f"Unsupported format: {format}. Supported formats: {', '.join(self.supported_formats)}")