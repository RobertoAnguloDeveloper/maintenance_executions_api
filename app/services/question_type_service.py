from app import db
from app.models.question_type import QuestionType
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
import re
import logging

logger = logging.getLogger(__name__)

class QuestionTypeService:
    @staticmethod
    def validate_type_name(type_name):
        """Validate question type name."""
        if type_name is None:
            return "Type name is required"
        if not type_name.strip():
            return "Type name cannot be empty"
        if len(type_name) > 255:
            return "Type name cannot exceed 255 characters"
        if re.search(r'[<>{}()\[\]]', type_name):
            return "Type name contains invalid characters"
        return None

    @staticmethod
    def create_question_type(type_name):
        """Create a new question type."""
        # Validate input
        error = QuestionTypeService.validate_type_name(type_name)
        if error:
            return None, error

        try:
            # Check if type already exists
            existing = db.session.scalar(
                select(QuestionType).filter_by(type=type_name)
            )
            if existing:
                return None, "A question type with this name already exists"

            question_type = QuestionType(type=type_name)
            db.session.add(question_type)
            db.session.commit()
            return question_type, None
        except IntegrityError:
            db.session.rollback()
            return None, "A question type with this name already exists"
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def get_all_question_types(include_deleted=False):
        """Get all question types"""
        try:
            query = QuestionType.query
            if not include_deleted:
                query = query.filter(QuestionType.is_deleted == False)
            return query.all()
        except Exception as e:
            logger.error(f"Error getting question types: {str(e)}")
            raise

    @staticmethod
    def get_question_type(type_id):
        """Get a question type by ID."""
        try:
            if not isinstance(type_id, int) or type_id < 1:
                return None
            return db.session.get(QuestionType, type_id)
        except Exception:
            return None

    @staticmethod
    def update_question_type(type_id, new_type_name):
        """Update a question type."""
        # Validate input
        error = QuestionTypeService.validate_type_name(new_type_name)
        if error:
            return None, error

        try:
            question_type = db.session.get(QuestionType, type_id)
            if not question_type:
                return None, "Question type not found"

            # If the name hasn't changed, don't proceed with the update
            if question_type.type == new_type_name:
                return None, "A question type with this name already exists"

            # Check if new name already exists in other records
            existing = db.session.scalar(
                select(QuestionType)
                .filter(QuestionType.type == new_type_name)
                .filter(QuestionType.id != type_id)
            )
            if existing:
                return None, "A question type with this name already exists"

            question_type.type = new_type_name
            db.session.commit()
            return question_type, None
        except IntegrityError:
            db.session.rollback()
            return None, "A question type with this name already exists"
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def delete_question_type(type_id):
        """Soft delete a question type"""
        try:
            question_type = QuestionType.query.get(type_id)
            if not question_type:
                return False, "Question type not found"

            if question_type.questions.count() > 0:
                return False, "Cannot delete question type with existing questions"

            question_type.soft_delete()
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, str(e)