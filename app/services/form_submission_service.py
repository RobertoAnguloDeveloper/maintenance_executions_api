from app import db
from app.models.form_submission import FormSubmission
from app.models.answers_submitted import AnswerSubmitted
from app.models.form_answer import FormAnswer
from app.models.attachment import Attachment
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
import logging

logger = logging.getLogger(__name__)

class FormSubmissionService:
    @staticmethod
    def create_submission(form_id, username, answers_data, attachments_data=None):
        """
        Create a new form submission with answers and attachments
        
        Args:
            form_id (int): Form ID
            username (str): Username of submitter
            answers_data (list): List of answer data including form_question_id and answer_id
            attachments_data (list, optional): List of attachment information
            
        Returns:
            tuple: (FormSubmission, error_message)
        """
        try:
            # Create submission
            submission = FormSubmission(
                form_id=form_id,
                submitted_by=username,
                submitted_at=datetime.utcnow()
            )
            db.session.add(submission)
            db.session.flush()

            # Process answers
            for answer_data in answers_data:
                # Create form answer if it doesn't exist
                form_answer = FormAnswer.query.filter_by(
                    form_question_id=answer_data['form_question_id'],
                    answer_id=answer_data['answer_id']
                ).first()

                if not form_answer:
                    form_answer = FormAnswer(
                        form_question_id=answer_data['form_question_id'],
                        answer_id=answer_data['answer_id'],
                        remarks=answer_data.get('remarks')
                    )
                    db.session.add(form_answer)
                    db.session.flush()

                # Create answer submission
                answer_submitted = AnswerSubmitted(
                    form_answer_id=form_answer.id,
                    form_submission_id=submission.id
                )
                db.session.add(answer_submitted)

            # Process attachments if any
            if attachments_data:
                for attachment_data in attachments_data:
                    attachment = Attachment(
                        form_submission_id=submission.id,
                        file_type=attachment_data['file_type'],
                        file_path=attachment_data['file_path'],
                        is_signature=attachment_data.get('is_signature', False)
                    )
                    db.session.add(attachment)

            db.session.commit()
            return submission, None

        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Integrity error creating submission: {str(e)}")
            return None, "Database integrity error"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating submission: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_submission(submission_id):
        """
        Get a submission with all its relationships loaded
        """
        return FormSubmission.query.options(
            joinedload(FormSubmission.answers_submitted)
                .joinedload(AnswerSubmitted.form_answer),
            joinedload(FormSubmission.attachments)
        ).get(submission_id)

    @staticmethod
    def get_submissions_by_form(form_id, include_deleted=False):
        """Get all submissions for a form"""
        query = FormSubmission.query.filter_by(form_id=form_id)
        
        if not include_deleted:
            query = query.filter(FormSubmission.is_deleted == False)
            
        return query.order_by(FormSubmission.submitted_at.desc()).all()

    @staticmethod
    def get_submissions_by_user(username, form_id=None, start_date=None, end_date=None):
        """
        Get submissions by username with optional filters
        """
        query = FormSubmission.query.filter_by(submitted_by=username)
        
        if form_id:
            query = query.filter_by(form_id=form_id)
        if start_date:
            query = query.filter(FormSubmission.submitted_at >= start_date)
        if end_date:
            query = query.filter(FormSubmission.submitted_at <= end_date)
            
        return query.order_by(FormSubmission.submitted_at.desc()).all()

    @staticmethod
    def get_submissions_by_environment(environment_id, form_id=None):
        """Get submissions for a specific environment"""
        query = FormSubmission.query\
            .join(FormSubmission.form)\
            .filter_by(environment_id=environment_id)
            
        if form_id:
            query = query.filter(FormSubmission.form_id == form_id)
            
        return query.order_by(FormSubmission.submitted_at.desc()).all()

    @staticmethod
    def update_submission(submission_id, answers_data=None, attachments_data=None):
        """
        Update a submission's answers and attachments
        """
        try:
            submission = FormSubmission.query.get(submission_id)
            if not submission:
                return None, "Submission not found"

            if answers_data:
                # Remove existing answers
                AnswerSubmitted.query.filter_by(form_submission_id=submission_id).delete()
                
                # Add new answers
                for answer_data in answers_data:
                    form_answer = FormAnswer.query.filter_by(
                        form_question_id=answer_data['form_question_id'],
                        answer_id=answer_data['answer_id']
                    ).first()

                    if not form_answer:
                        form_answer = FormAnswer(
                            form_question_id=answer_data['form_question_id'],
                            answer_id=answer_data['answer_id'],
                            remarks=answer_data.get('remarks')
                        )
                        db.session.add(form_answer)
                        db.session.flush()

                    answer_submitted = AnswerSubmitted(
                        form_answer_id=form_answer.id,
                        form_submission_id=submission_id
                    )
                    db.session.add(answer_submitted)

            if attachments_data:
                # Handle attachments update
                Attachment.query.filter_by(form_submission_id=submission_id).delete()
                
                for attachment_data in attachments_data:
                    attachment = Attachment(
                        form_submission_id=submission_id,
                        file_type=attachment_data['file_type'],
                        file_path=attachment_data['file_path'],
                        is_signature=attachment_data.get('is_signature', False)
                    )
                    db.session.add(attachment)

            submission.updated_at = datetime.utcnow()
            db.session.commit()
            return submission, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating submission {submission_id}: {str(e)}")
            return None, str(e)

    @staticmethod
    def delete_submission(submission_id):
        """Soft delete a submission"""
        try:
            submission = FormSubmission.query.get(submission_id)
            if not submission:
                return False, "Submission not found"

            submission.soft_delete()
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def get_submission_statistics(form_id=None, environment_id=None, date_range=None):
        """Get submission statistics with optional filters"""
        try:
            query = FormSubmission.query

            if form_id:
                query = query.filter_by(form_id=form_id)
            if environment_id:
                query = query.join(FormSubmission.form)\
                    .filter_by(environment_id=environment_id)
            if date_range:
                query = query.filter(
                    FormSubmission.submitted_at.between(
                        date_range['start'],
                        date_range['end']
                    )
                )

            submissions = query.all()
            
            stats = {
                'total_submissions': len(submissions),
                'submissions_by_user': {},
                'submissions_by_date': {},
                'average_answers_per_submission': 0,
                'attachment_stats': {
                    'total_attachments': 0,
                    'submissions_with_attachments': 0
                }
            }

            if submissions:
                # Calculate user statistics
                for submission in submissions:
                    # User stats
                    stats['submissions_by_user'][submission.submitted_by] = \
                        stats['submissions_by_user'].get(submission.submitted_by, 0) + 1

                    # Date stats
                    date_key = submission.submitted_at.date().isoformat()
                    stats['submissions_by_date'][date_key] = \
                        stats['submissions_by_date'].get(date_key, 0) + 1

                    # Attachment stats
                    if submission.attachments:
                        stats['attachment_stats']['total_attachments'] += len(submission.attachments)
                        stats['attachment_stats']['submissions_with_attachments'] += 1

                # Calculate averages
                total_answers = sum(len(s.answers_submitted) for s in submissions)
                stats['average_answers_per_submission'] = total_answers / len(submissions)

            return stats

        except Exception as e:
            logger.error(f"Error calculating submission statistics: {str(e)}")
            return None