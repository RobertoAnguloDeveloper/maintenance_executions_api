from app.services.form_submission_service import FormSubmissionService
from datetime import datetime

class FormSubmissionController:
    @staticmethod
    def create_form_submission(question_answer, username):
        """
        Create a new form submission
        """
        return FormSubmissionService.create_form_submission(
            question_answer=question_answer,
            username=username,
            submitted_at=datetime.utcnow()
        )

    @staticmethod
    def get_form_submission(submission_id):
        """
        Get a form submission by ID
        """
        return FormSubmissionService.get_form_submission(submission_id)

    @staticmethod
    def get_submissions_by_username(username):
        """
        Get all submissions by username
        """
        return FormSubmissionService.get_submissions_by_username(username)

    @staticmethod
    def get_submissions_by_form(form_id):
        """
        Get all submissions for a form
        """
        return FormSubmissionService.get_submissions_by_form(form_id)

    @staticmethod
    def get_all_submissions():
        """
        Get all submissions
        """
        return FormSubmissionService.get_all_submissions()

    @staticmethod
    def update_form_submission(submission_id, **kwargs):
        """
        Update a form submission
        """
        return FormSubmissionService.update_form_submission(submission_id, **kwargs)

    @staticmethod
    def delete_form_submission(submission_id):
        """
        Delete a form submission
        """
        return FormSubmissionService.delete_form_submission(submission_id)

    @staticmethod
    def get_submission_statistics():
        """
        Get submission statistics
        """
        return FormSubmissionService.get_submission_statistics()