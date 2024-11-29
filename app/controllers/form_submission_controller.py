from datetime import datetime
from app.services.form_submission_service import FormSubmissionService
from app.utils.permission_manager import RoleType
import logging

logger = logging.getLogger(__name__)

class FormSubmissionController:
   @staticmethod
   def create_submission(form_id: int, username: str, answers: list) -> tuple:
       """
       Create a new form submission with answers
       
       Args:
           form_id (int): Form ID
           username (str): Username of submitter
           answers (list): List of answer data
           
       Returns:
           tuple: (FormSubmission, error_message)
       """
       return FormSubmissionService.create_submission(
           form_id=form_id,
           username=username, 
           answers=answers
       )

   @staticmethod
   def get_all_submissions(user, filters: dict = None) -> list:
       """
       Get all submissions with role-based filtering
       
       Args:
           user: Current user object
           filters (dict): Optional filters
           
       Returns:
           list: List of FormSubmission objects
       """
       # Initialize filters if None
       filters = filters or {}
       
       # Apply role-based filtering
       if not user.role.is_super_user:
           if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
               filters['environment_id'] = user.environment_id
           else:
               filters['submitted_by'] = user.username
                   
       return FormSubmissionService.get_all_submissions(filters)

   @staticmethod
   def get_submission(submission_id: int) -> tuple:
       """
       Get a specific submission
       
       Args:
           submission_id (int): Submission ID
           
       Returns:
           tuple: (FormSubmission, error_message)
       """
       return FormSubmissionService.get_submission(submission_id)

   @staticmethod
   def get_submissions_by_form(form_id: int) -> list:
       """
       Get all submissions for a form
       
       Args:
           form_id (int): Form ID
           
       Returns: 
           list: List of FormSubmission objects
       """
       return FormSubmissionService.get_submissions_by_form(form_id)

   @staticmethod
   def get_submissions_by_user(username: str, form_id: int = None, 
                             start_date: datetime = None, end_date: datetime = None) -> list:
       """
       Get submissions by username with optional filters
       
       Args:
           username (str): Username
           form_id (int, optional): Filter by form ID
           start_date (datetime, optional): Filter by start date
           end_date (datetime, optional): Filter by end date
           
       Returns:
           list: List of FormSubmission objects
       """
       return FormSubmissionService.get_submissions_by_user(
           username, form_id, start_date, end_date
       )

   @staticmethod
   def get_submissions_by_environment(environment_id: int, form_id: int = None) -> list:
       """
       Get submissions for an environment
       
       Args:
           environment_id (int): Environment ID
           form_id (int, optional): Filter by form ID
           
       Returns:
           list: List of FormSubmission objects
       """
       return FormSubmissionService.get_submissions_by_environment(
           environment_id, form_id
       )

   @staticmethod
   def update_submission(submission_id: int, user: str, answers_data: list = None) -> tuple:
       """
       Update a submission
       
       Args:
           submission_id (int): Submission ID
           user: Current user object for authorization
           answers_data (list, optional): Updated answer data
           
       Returns:
           tuple: (FormSubmission, error_message) 
       """
       return FormSubmissionService.update_submission(submission_id, user, answers_data)

   @staticmethod
   def delete_submission(submission_id: int, user) -> tuple:
       """
       Delete a submission
       
       Args:
           submission_id (int): Submission ID
           user: Current user object for authorization
           
       Returns:
           tuple: (success, error_message)
       """
       return FormSubmissionService.delete_submission(submission_id, user)

   @staticmethod
   def get_submission_statistics(form_id: int = None, environment_id: int = None, 
                               date_range: dict = None) -> dict:
       """
       Get submission statistics
       
       Args:
           form_id (int, optional): Filter by form ID
           environment_id (int, optional): Filter by environment ID
           date_range (dict, optional): Filter by date range
           
       Returns:
           dict: Statistics data
       """
       return FormSubmissionService.get_submission_statistics(
           form_id, environment_id, date_range
       )