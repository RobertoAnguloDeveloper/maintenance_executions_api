from app import db
from app.models.form_submission import FormSubmission
from sqlalchemy.exc import IntegrityError
from datetime import datetime

class FormSubmissionService:
    @staticmethod
    def create_form_submission(question_answer, username, submitted_at=None):
        """
        Create a new form submission
        """
        try:
            if submitted_at is None:
                submitted_at = datetime.utcnow()
                
            new_submission = FormSubmission(
                question_answer=question_answer,
                username=username,
                submitted_at=submitted_at
            )
            db.session.add(new_submission)
            db.session.commit()
            return new_submission, None
        except IntegrityError:
            db.session.rollback()
            return None, "Username already exists or invalid question_answer reference"
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def get_form_submission(submission_id):
        """
        Get a form submission by ID
        """
        return FormSubmission.query.get(submission_id)

    @staticmethod
    def get_submissions_by_username(username):
        """
        Get all submissions by a specific username
        """
        return FormSubmission.query.filter_by(username=username).order_by(FormSubmission.submitted_at.desc()).all()

    @staticmethod
    def get_submissions_by_form(form_id):
        """
        Get all submissions for a specific form
        """
        return FormSubmission.query.filter_by(question_answer=form_id).order_by(FormSubmission.submitted_at.desc()).all()

    @staticmethod
    def get_all_submissions():
        """
        Get all form submissions
        """
        return FormSubmission.query.order_by(FormSubmission.submitted_at.desc()).all()

    @staticmethod
    def update_form_submission(submission_id, **kwargs):
        """
        Update a form submission
        """
        submission = FormSubmission.query.get(submission_id)
        if submission:
            try:
                for key, value in kwargs.items():
                    if hasattr(submission, key):
                        setattr(submission, key, value)
                db.session.commit()
                return submission, None
            except IntegrityError:
                db.session.rollback()
                return None, "Username already exists or invalid question_answer reference"
            except Exception as e:
                db.session.rollback()
                return None, str(e)
        return None, "Form submission not found"

    @staticmethod
    def delete_form_submission(submission_id):
        """
        Delete a form submission and its attachments
        """
        submission = FormSubmission.query.get(submission_id)
        if submission:
            try:
                db.session.delete(submission)
                db.session.commit()
                return True, None
            except Exception as e:
                db.session.rollback()
                return False, str(e)
        return False, "Form submission not found"

    @staticmethod
    def get_submission_statistics():
        """
        Get statistics about form submissions
        """
        try:
            total_submissions = FormSubmission.query.count()
            submissions_by_form = db.session.query(
                FormSubmission.question_answer,
                db.func.count(FormSubmission.id)
            ).group_by(FormSubmission.question_answer).all()
            
            return {
                'total_submissions': total_submissions,
                'submissions_by_form': dict(submissions_by_form)
            }
        except Exception as e:
            return None, str(e)