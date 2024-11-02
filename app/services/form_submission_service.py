from app import db
from app.models.form_submission import FormSubmission
from app.models.form_answer import FormAnswer
from app.models.answers_submitted import AnswerSubmitted
from app.models.form_question import FormQuestion
from app.models.attachment import Attachment
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

class FormSubmissionService:
    @staticmethod
    def create_submission(form_id, username, answers_data, attachments_data=None):
        """
        Create a new form submission with answers and attachments
        
        Args:
            form_id (int): ID of the form being submitted
            username (str): Username of the submitter
            answers_data (list): List of dicts with question_id, answer_id, and remarks
            attachments_data (list): Optional list of attachment information
            
        Returns:
            tuple: (FormSubmission, error_message)
        """
        try:
            # Create the submission record
            submission = FormSubmission(
                form_submitted=str(form_id),  # Store form ID as string as per schema
                submitted_by=username,
                submitted_at=datetime.utcnow()
            )
            db.session.add(submission)
            
            # Process each answer
            for answer_data in answers_data:
                # Get the form question
                form_question = FormQuestion.query.filter_by(
                    form_id=form_id,
                    question_id=answer_data['question_id']
                ).first()
                
                if not form_question:
                    raise ValueError(f"Invalid question_id: {answer_data['question_id']}")
                
                # Create form answer
                form_answer = FormAnswer(
                    form_question=form_question,
                    answer_id=answer_data['answer_id'],
                    remarks=answer_data.get('remarks')
                )
                db.session.add(form_answer)
                
                # Link answer to submission
                answer_submitted = AnswerSubmitted(
                    form_answer=form_answer,
                    form_submission=submission
                )
                db.session.add(answer_submitted)
            
            # Process attachments if any
            if attachments_data:
                for attachment_data in attachments_data:
                    attachment = Attachment(
                        form_submission=submission,
                        file_type=attachment_data['file_type'],
                        file_path=attachment_data['file_path'],
                        is_signature=attachment_data.get('is_signature', False)
                    )
                    db.session.add(attachment)
            
            db.session.commit()
            return submission, None
            
        except ValueError as e:
            db.session.rollback()
            return None, str(e)
        except IntegrityError:
            db.session.rollback()
            return None, "Database integrity error"
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def get_submission(submission_id):
        """Get a submission with all its relationships loaded"""
        return FormSubmission.query.options(
            joinedload(FormSubmission.answers).joinedload(AnswerSubmitted.form_answer),
            joinedload(FormSubmission.attachments)
        ).get(submission_id)

    @staticmethod
    def get_submissions_by_form(form_id):
        """Get all submissions for a specific form"""
        return FormSubmission.query.filter_by(
            form_submitted=str(form_id)
        ).order_by(FormSubmission.submitted_at.desc()).all()

    @staticmethod
    def get_submissions_by_user(username):
        """Get all submissions by a specific user"""
        return FormSubmission.query.filter_by(
            submitted_by=username
        ).order_by(FormSubmission.submitted_at.desc()).all()

    @staticmethod
    def delete_submission(submission_id):
        """Delete a submission and all related data"""
        submission = FormSubmission.query.get(submission_id)
        if submission:
            try:
                db.session.delete(submission)
                db.session.commit()
                return True, None
            except Exception as e:
                db.session.rollback()
                return False, str(e)
        return False, "Submission not found"