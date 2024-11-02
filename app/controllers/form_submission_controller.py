from app.services.form_submission_service import FormSubmissionService
from datetime import datetime

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
    def get_form_submission(submission_id):
        """Get a specific form submission"""
        return FormSubmissionService.get_submission(submission_id)

    @staticmethod
    def get_submissions_by_form(form_id):
        """Get all submissions for a form"""
        return FormSubmissionService.get_submissions_by_form(form_id)

    @staticmethod
    def get_submissions_by_user(username):
        """Get all submissions by a user"""
        return FormSubmissionService.get_submissions_by_user(username)

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