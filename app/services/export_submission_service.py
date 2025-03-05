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
            
            # Get all answers excluding signature type questions
            answers = AnswerSubmitted.query.filter_by(
                form_submission_id=submission_id,
                is_deleted=False
            ).all()
            
            sorted_answers = sorted(
                [a for a in answers if a.question_type.lower() != 'signature'], 
                key=lambda a: a.question
            )
            
            # Add questions and answers
            for answer in sorted_answers:
                q_text = f"{answer.question}"
                story.append(Paragraph(q_text, styles['Question']))
                
                a_text = answer.answer if answer.answer else "No answer provided"
                story.append(Paragraph(a_text, styles['Answer']))
            
            # Add signatures if requested
            if include_signatures:
                # Get all signature attachments
                attachments = Attachment.query.filter_by(
                    form_submission_id=submission_id,
                    is_signature=True,
                    is_deleted=False
                ).all()
                
                if attachments:
                    story.append(Spacer(1, 24))
                    story.append(Paragraph("Signatures:", styles['Heading2']))
                    story.append(Spacer(1, 6))
                    
                    for attachment in attachments:
                        file_path = os.path.join(upload_path, attachment.file_path)
                        exists = os.path.exists(file_path)
                        
                        # Extract signature metadata
                        signature_position = attachment.signature_position
                        signature_author = attachment.signature_author
                        
                        # Try to extract from filename if not in attachment record
                        if not signature_position or not signature_author:
                            try:
                                filename = os.path.basename(attachment.file_path)
                                parts = filename.split('+')
                                
                                if len(parts) >= 4:
                                    # Format: {form_submission_id}+{signature_position}+{signature_author}+{timestamp}
                                    if not signature_position:
                                        signature_position = parts[1].replace('_', ' ')
                                    if not signature_author:
                                        signature_author = parts[2].replace('_', ' ')
                            except Exception as e:
                                logger.warning(f"Could not parse signature metadata from filename: {str(e)}")
                        
                        if exists:
                            try:
                                # 1. First, add the signature image
                                img = Image(file_path, width=3.5*inch, height=1.4*inch)
                                
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
                                story.append(Spacer(1, 5))
                                
                                # 2. Next, add signature author below the image
                                if signature_author:
                                    story.append(Paragraph(f"<b>Signed by:</b> {signature_author}", styles['Normal']))
                                    story.append(Spacer(1, 3))
                                
                                # 3. Finally, add signature position below the author
                                if signature_position:
                                    story.append(Paragraph(f"<b>Position:</b> {signature_position}", styles['Normal']))
                                
                                story.append(Spacer(1, 16))
                                
                            except Exception as img_error:
                                logger.warning(f"Error adding signature image: {str(img_error)}")
                                story.append(Paragraph("Image could not be loaded", styles['Normal']))
                                story.append(Spacer(1, 12))
                        else:
                            # Add signature information even if image can't be found
                            if signature_author:
                                story.append(Paragraph(f"<b>Signed by:</b> {signature_author}", styles['Normal']))
                                story.append(Spacer(1, 3))
                            if signature_position:
                                story.append(Paragraph(f"<b>Position:</b> {signature_position}", styles['Normal']))
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
        Get all signature images for a submission with proper metadata extraction
        
        Args:
            submission_id: ID of the form submission
            upload_path: Path to uploads folder
            
        Returns:
            List of signature image details including paths, authors, and positions
        """
        signatures = []
        
        # Get all signature attachments
        attachments = Attachment.query.filter_by(
            form_submission_id=submission_id,
            is_signature=True,
            is_deleted=False
        ).all()
        
        # Process each attachment
        for attachment in attachments:
            # Get the file path
            file_path = os.path.join(upload_path, attachment.file_path)
            exists = os.path.exists(file_path)
            
            # Try to extract author and position from filename or use model fields
            signature_position = attachment.signature_position
            signature_author = attachment.signature_author
            
            # If not available in model, try to extract from filename
            if not signature_position or not signature_author:
                try:
                    # Parse the filename which should have format: {id}+{position}+{author}+{timestamp}.ext
                    filename = os.path.basename(attachment.file_path)
                    parts = filename.split('+')
                    
                    if len(parts) >= 4:
                        # First part is submission ID
                        # Second part is position
                        if not signature_position:
                            signature_position = parts[1].replace('_', ' ')
                        
                        # Third part is author
                        if not signature_author:
                            signature_author = parts[2].replace('_', ' ')
                except Exception as e:
                    logger.warning(f"Could not parse signature metadata from filename: {str(e)}")
            
            signatures.append({
                "path": file_path,
                "position": signature_position or "Signature",
                "author": signature_author or "Signer",
                "exists": exists
            })
        
        return signatures