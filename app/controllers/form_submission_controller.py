from app.services.form_submission_service import FormSubmissionService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FormSubmissionController:
    @staticmethod
    def create_submission(form_id, username, answers_data, attachments_data=None):
        """
        Create a new form submission
        
        Args:
            form_id (int): ID of the form being submitted
            username (str): Username of the submitter
            answers_data (list): List of answer data
            attachments_data (list, optional): List of attachment information
            
        Returns:
            tuple: (FormSubmission, error_message)
        """
        return FormSubmissionService.create_submission(
            form_id=form_id,
            username=username,
            answers_data=answers_data,
            attachments_data=attachments_data
        )

    @staticmethod
    def get_submission(submission_id):
        """Get a specific submission with all related data"""
        return FormSubmissionService.get_submission(submission_id)

    @staticmethod
    def get_submissions_by_form(form_id):
        """Get all submissions for a specific form"""
        return FormSubmissionService.get_submissions_by_form(form_id)

    @staticmethod
    def get_submissions_by_user(username, form_id=None, start_date=None, end_date=None):
        """Get submissions by username with optional filters"""
        return FormSubmissionService.get_submissions_by_user(
            username, form_id, start_date, end_date
        )

    @staticmethod
    def get_submissions_by_environment(environment_id, form_id=None):
        """Get submissions for a specific environment"""
        return FormSubmissionService.get_submissions_by_environment(
            environment_id, form_id
        )

    @staticmethod
    def update_submission(submission_id, answers_data=None, attachments_data=None):
        """Update a submission"""
        return FormSubmissionService.update_submission(
            submission_id, answers_data, attachments_data
        )

    @staticmethod
    def delete_submission(submission_id):
        """Delete a submission"""
        return FormSubmissionService.delete_submission(submission_id)

    @staticmethod
    def get_submission_statistics(form_id=None, environment_id=None, date_range=None):
        """Get submission statistics"""
        return FormSubmissionService.get_submission_statistics(
            form_id, environment_id, date_range
        )