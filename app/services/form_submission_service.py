from typing import Optional, List, Dict, Any
from app import db
from app.models.form import Form
from app.models.form_submission import FormSubmission
import logging

from app.models.user import User

from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class FormSubmissionService:
    @staticmethod
    def create_submission(form_id: int, username: str) -> Tuple[Optional[FormSubmission], Optional[str]]:
        """
        Create a new form submission
        
        Args:
            form_id: ID of the form
            username: Username of submitter
            
        Returns:
            tuple: (Created FormSubmission object or None, Error message or None)
        """
        try:
            submission = FormSubmission(
                form_id=form_id,
                submitted_by=username
            )
            db.session.add(submission)
            db.session.commit()
            return submission, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating submission: {str(e)}")
            return None, str(e)

    @staticmethod
    def get_all_submissions(filters: dict = None) -> List[FormSubmission]:
        """
        Get all submissions with optional filters
        
        Args:
            filters (dict): Optional filters
                - form_id (int): Filter by form ID
                - environment_id (int): Filter by environment
                - submitted_by (str): Filter by submitter
                
        Returns:
            List[FormSubmission]: List of submissions matching filters
        """
        query = FormSubmission.query.filter_by(is_deleted=False)
        
        if filters:
            if filters.get('form_id'):
                query = query.filter_by(form_id=filters['form_id'])
                
            if filters.get('submitted_by'):
                query = query.filter_by(submitted_by=filters['submitted_by'])
                
            if filters.get('environment_id'):
                query = query.join(Form).join(User).filter(
                    User.environment_id == filters['environment_id']
                )
                
        return query.order_by(FormSubmission.submitted_at.desc()).all()

    @staticmethod
    def get_submission(submission_id: int) -> Optional[FormSubmission]:
        """Get a specific submission"""
        return FormSubmission.query.filter_by(
            id=submission_id,
            is_deleted=False
        ).first()

    @staticmethod
    def delete_submission(submission_id: int) -> Tuple[bool, Optional[str]]:
        """Delete a submission with cascade soft delete"""
        try:
            submission = FormSubmission.query.filter_by(
                id=submission_id,
                is_deleted=False
            ).first()
            
            if not submission:
                return False, "Submission not found"

            submission.soft_delete()
            db.session.commit()
            return True, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting submission: {str(e)}")
            return False, str(e)