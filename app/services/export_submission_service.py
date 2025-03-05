# app/services/export_submission_service.py

from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
import os
import logging
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Flowable
from werkzeug.exceptions import BadRequest
from app.models.form_submission import FormSubmission
from app.models.attachment import Attachment
from app.models.answer_submitted import AnswerSubmitted
from app.models.form import Form
from app.models.form_question import FormQuestion

logger = logging.getLogger(__name__)

class ExportSubmissionService:
    """Service for exporting form submissions to PDF"""
    
    @staticmethod
    def export_submission_to_pdf(
        submission_id: int,
        upload_path: str,
        include_signatures: bool = True
    ) -> Tuple[Optional[BytesIO], Optional[str]]:
        """
        Export a form submission to PDF with all answers and optional signatures
        
        Args:
            submission_id: ID of the form submission
            upload_path: Path to uploads folder for retrieving signatures
            include_signatures: Whether to include signature images or not
            
        Returns:
            Tuple containing BytesIO PDF buffer or None, and error message or None
        """
        try:
            # Get the submission with all needed relationships
            submission = FormSubmission.query.filter_by(
                id=submission_id,
                is_deleted=False
            ).first()
            
            if not submission:
                return None, "Submission not found"
                
            # Get form details
            form = Form.query.filter_by(
                id=submission.form_id,
                is_deleted=False
            ).first()
            
            if not form:
                return None, "Form not found"
                
            # Create a buffer for the PDF
            buffer = BytesIO()
            
            # Create document
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=0.75*inch,
                leftMargin=0.5*inch,  # Reduced left margin to push everything more to the left
                topMargin=0.75*inch,
                bottomMargin=0.75*inch,
                title=f"Form Submission - {form.title}"
            )
            
            # Prepare styles
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                name='FormTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=12,
                alignment=1  # Center alignment for title
            ))
            styles.add(ParagraphStyle(
                name='Question',
                parent=styles['Heading2'],
                fontSize=12,
                spaceAfter=6,
                leftIndent=0  # Ensure questions start at left margin
            ))
            styles.add(ParagraphStyle(
                name='Answer',
                parent=styles['Normal'],
                fontSize=11,
                leftIndent=20,
                spaceAfter=12
            ))
            styles.add(ParagraphStyle(
                name='SignatureLabel',
                parent=styles['Heading3'],
                fontSize=11,
                spaceAfter=3,
                alignment=0,  # Left alignment for signature labels
                leftIndent=0  # No indent for signature labels
            ))
            
            # Create the content
            story = []
            
            # Add title and submission info
            story.append(Paragraph(form.title, styles['FormTitle']))
            if form.description:
                story.append(Paragraph(form.description, styles['Normal']))
            story.append(Spacer(1, 12))
            
            # Add submission info in a more organized way
            info_data = [
                ['Submitted by:', submission.submitted_by],
                ['Date:', submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S')]
            ]
            
            # Create a table for submission info with proper styling
            info_table = Table(info_data, colWidths=[1.5*inch, 4*inch])
            info_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (0, -1), 0),  # No left padding for first column
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 24))
            
            # Get all form questions with order
            form_questions = FormQuestion.query.filter_by(
                form_id=form.id,
                is_deleted=False
            ).order_by(FormQuestion.order_number).all()
            
            question_order = {fq.question_id: fq.order_number for fq in form_questions}
            
            # Get all answers in order of questions
            answers = AnswerSubmitted.query.filter_by(
                form_submission_id=submission_id,
                is_deleted=False
            ).all()
            
            # Sort answers to match form question order if possible
            sorted_answers = sorted(
                answers, 
                key=lambda a: a.question
            )
            
            # Add questions and answers, excluding signature type questions
            for answer in sorted_answers:
                # Skip questions with question_type = 'signature'
                if answer.question_type.lower() == 'signature':
                    continue
                    
                q_text = f"{answer.question}"
                story.append(Paragraph(q_text, styles['Question']))
                
                a_text = answer.answer if answer.answer else "No answer provided"
                story.append(Paragraph(a_text, styles['Answer']))
            
            # Add signatures if requested
            if include_signatures:
                signatures = ExportSubmissionService._get_signature_images(submission_id, upload_path)
                
                if signatures:
                    story.append(Spacer(1, 24))
                    story.append(Paragraph("Signatures:", styles['Heading2']))
                    story.append(Spacer(1, 6))
                    
                    # Process each signature individually for maximum left alignment
                    for sig in signatures:
                        if sig["exists"]:
                            try:
                                # Add the label with no indent
                                story.append(Paragraph(sig["label"], styles["SignatureLabel"]))
                                
                                # Create image with no left padding
                                img = Image(sig["path"], width=3.5*inch, height=1.4*inch)
                                
                                # Create a table with zero left padding to push image to the left
                                sig_table = Table(
                                    [[img]],
                                    colWidths=[7*inch]
                                )
                                sig_table.setStyle(TableStyle([
                                    ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                                    ('VALIGN', (0, 0), (0, 0), 'TOP'),
                                    ('LEFTPADDING', (0, 0), (0, 0), 0),
                                    ('RIGHTPADDING', (0, 0), (0, 0), 0),
                                    ('TOPPADDING', (0, 0), (0, 0), 0),
                                    ('BOTTOMPADDING', (0, 0), (0, 0), 0),
                                ]))
                                
                                story.append(sig_table)
                                story.append(Spacer(1, 16))
                            except Exception as img_error:
                                logger.warning(f"Error adding signature image: {str(img_error)}")
                                story.append(Paragraph("Image could not be loaded", styles['Normal']))
                                story.append(Spacer(1, 12))
                        else:
                            story.append(Paragraph(sig['label'], styles["SignatureLabel"]))
                            story.append(Paragraph("Image not found", styles['Normal']))
                            story.append(Spacer(1, 12))
            
            # Build the PDF
            doc.build(story)
            buffer.seek(0)
            return buffer, None
            
        except Exception as e:
            logger.error(f"Error exporting submission to PDF: {str(e)}")
            return None, str(e)
    
    @staticmethod
    def _get_signature_images(submission_id: int, upload_path: str) -> List[Dict]:
        """
        Get all signature images for a submission
        
        Args:
            submission_id: ID of the form submission
            upload_path: Path to uploads folder
            
        Returns:
            List of signature image details including paths and labels
        """
        signatures = []
        
        # Get all signature attachments
        attachments = Attachment.query.filter_by(
            form_submission_id=submission_id,
            is_signature=True,
            is_deleted=False
        ).all()
        
        # Get all answer submitted records for this submission
        answers = AnswerSubmitted.query.filter_by(
            form_submission_id=submission_id,
            is_deleted=False
        ).all()
        
        # Get signature type answers
        signature_answers = [a for a in answers if a.question_type.lower() == 'signature']
        
        # Map signature attachments to questions when possible
        labeled_signatures = []
        
        for attachment in attachments:
            # Try to find a matching answer by looking at the file path pattern
            # The pattern should be: {id}_{question}_{form_id}_{timestamp}
            path_parts = os.path.basename(attachment.file_path).split('_')
            
            if len(path_parts) >= 3:
                # Try to extract the answer ID from the filename
                try:
                    answer_id = int(path_parts[0])
                    # Find the corresponding answer
                    answer = next((a for a in answers if a.id == answer_id), None)
                    
                    if answer:
                        labeled_signatures.append({
                            "path": os.path.join(upload_path, attachment.file_path),
                            "label": answer.question,
                            "exists": os.path.exists(os.path.join(upload_path, attachment.file_path))
                        })
                        continue
                except (ValueError, IndexError):
                    # If we can't parse the answer ID, fall through to default handling
                    pass
            
            # Default handling for signatures without clear mapping
            labeled_signatures.append({
                "path": os.path.join(upload_path, attachment.file_path),
                "label": "Signature",
                "exists": os.path.exists(os.path.join(upload_path, attachment.file_path))
            })
        
        return labeled_signatures