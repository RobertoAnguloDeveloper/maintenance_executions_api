from app.models.answers_submitted import AnswerSubmitted
from app.models.form_answer import FormAnswer
from app.models.form_question import FormQuestion
from app.models.form_submission import FormSubmission
from app.models.question import Question
from app.services.form_submission_service import FormSubmissionService
from datetime import datetime
from sqlalchemy.orm import joinedload

class FormSubmissionController:
    @staticmethod
    def create_form_submission(form_id, username, answers, attachments=None):
        """
        Create a new form submission
        
        Args:
            form_id (int): ID of the form being submitted
            username (str): Username of the submitter
            answers (list): List of answer data including question_id and answer_id
            attachments (list): Optional list of attachment information
            
        Returns:
            tuple: (FormSubmission, error_message)
        """
        return FormSubmissionService.create_submission(
            form_id=form_id,
            username=username,
            answers_data=answers,
            attachments_data=attachments
        )
        
    @staticmethod
    def get_all_submissions(form_id=None, start_date=None, end_date=None):
        """
        Get all submissions with optional filters
        
        Args:
            form_id (int, optional): Filter by specific form
            start_date (datetime, optional): Filter by submissions after this date
            end_date (datetime, optional): Filter by submissions before this date
            
        Returns:
            list: List of FormSubmission objects
        """
        # Start with base query with all needed relationships
        query = FormSubmission.query.options(
            joinedload(FormSubmission.form),
            joinedload(FormSubmission.answers_submitted)
                .joinedload(AnswerSubmitted.form_answer)
                .joinedload(FormAnswer.form_question)
                .joinedload(FormQuestion.question)
                .joinedload(Question.question_type),
            joinedload(FormSubmission.answers_submitted)
                .joinedload(AnswerSubmitted.form_answer)
                .joinedload(FormAnswer.answer),
            joinedload(FormSubmission.attachments)
        )

        # Apply filters if provided
        if form_id:
            query = query.filter(FormSubmission.form_id == form_id)
        
        if start_date:
            query = query.filter(FormSubmission.submitted_at >= start_date)
            
        if end_date:
            query = query.filter(FormSubmission.submitted_at <= end_date)

        # Order by submission date (newest first)
        return query.order_by(FormSubmission.submitted_at.desc()).all()

    @staticmethod
    def get_form_submission(submission_id):
        """Get a specific submission with all its relationships"""
        return FormSubmission.query.options(
            joinedload(FormSubmission.form),
            joinedload(FormSubmission.answers_submitted)
                .joinedload(AnswerSubmitted.form_answer)
                .joinedload(FormAnswer.form_question)
                .joinedload(FormQuestion.question),
            joinedload(FormSubmission.attachments)
        ).get(submission_id)

    @staticmethod
    def get_submissions_by_form(form_id):
        """Get all submissions for a form"""
        return FormSubmissionService.get_submissions_by_form(form_id)

    @staticmethod
    def get_submissions_by_user(username, form_id=None, start_date=None, end_date=None):
        """Get all submissions by a specific user"""
        query = FormSubmission.query.filter_by(submitted_by=username)
        
        if form_id:
            query = query.filter_by(form_id=form_id)
            
        if start_date:
            query = query.filter(FormSubmission.submitted_at >= start_date)
            
        if end_date:
            query = query.filter(FormSubmission.submitted_at <= end_date)
            
        return query.order_by(FormSubmission.submitted_at.desc()).all()

    @staticmethod
    def delete_form_submission(submission_id):
        """Delete a form submission"""
        return FormSubmissionService.delete_submission(submission_id)

    @staticmethod
    def get_submission_statistics(form_id=None):
        """
        Get submission statistics
        Optional form_id parameter to get statistics for a specific form
        """
        submissions = (FormSubmissionService.get_submissions_by_form(form_id) 
                     if form_id else FormSubmissionService.get_all_submissions())
        
        stats = {
            'total_submissions': len(submissions),
            'submissions_by_user': {},
            'submission_timeline': {}
        }
        
        for submission in submissions:
            # Count submissions by user
            stats['submissions_by_user'][submission.submitted_by] = (
                stats['submissions_by_user'].get(submission.submitted_by, 0) + 1
            )
            
            # Group by date for timeline
            date_key = submission.submitted_at.strftime('%Y-%m-%d')
            stats['submission_timeline'][date_key] = (
                stats['submission_timeline'].get(date_key, 0) + 1
            )
        
        return stats, None