from datetime import datetime
from typing import Optional, Union
from app import db
from app.models.answer_submitted import AnswerSubmitted
from app.models.form_answer import FormAnswer
from app.models.form_question import FormQuestion
from app.models.question import Question
from app.models.question_type import QuestionType
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
import re
import logging

logger = logging.getLogger(__name__)

class QuestionTypeService:
    CORE_TYPES = {'checkbox', 'multiple_choice', 'single_choice', 'date'}
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
    def get_all_question_types(include_deleted: bool = False) -> list[QuestionType]:
        """Get all question types"""
        query = QuestionType.query
        
        if not include_deleted:
            query = query.filter(QuestionType.is_deleted == False)
            
        return query.order_by(QuestionType.id).all()

    @staticmethod
    def get_question_type(type_id: int) -> Optional[QuestionType]:
        """Get non-deleted question type by ID"""
        return QuestionType.query.filter_by(
            id=type_id,
            is_deleted=False
        ).first()
        
    @staticmethod
    def get_question_type_by_name(type_name: str) -> Optional[QuestionType]:
        """Get non-deleted question type by name"""
        return QuestionType.query.filter_by(
            type=type_name,
            is_deleted=False
        ).first()

    @staticmethod
    def update_question_type(
        type_id: int, 
        new_type_name: str
    ) -> tuple[Optional[QuestionType], Optional[str]]:
        """Update a question type with validation"""
        try:
            question_type = QuestionType.query.filter_by(
                id=type_id,
                is_deleted=False
            ).first()
            
            if not question_type:
                return None, "Question type not found"

            # Prevent modification of core types
            if question_type.type in QuestionTypeService.CORE_TYPES:
                return None, "Cannot modify core question types"

            # Check name format
            if not new_type_name or ' ' in new_type_name:
                return None, "Type name must be a non-empty string without spaces"

            # Check for existing type with new name
            existing = QuestionType.query.filter_by(
                type=new_type_name,
                is_deleted=False
            ).first()
            
            if existing and existing.id != type_id:
                return None, "A question type with this name already exists"

            question_type.type = new_type_name
            question_type.updated_at = datetime.utcnow()
            db.session.commit()

            return question_type, None

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error updating question type: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    def delete_question_type(type_id: int) -> tuple[bool, Union[dict, str]]:
        """
        Delete a question type with cascade validation
        
        Args:
            type_id (int): ID of the question type to delete
            
        Returns:
            tuple: (success: bool, result: Union[dict, str])
                  result contains either deletion statistics or error message
        """
        try:
            question_type = QuestionType.query.filter_by(
                id=type_id,
                is_deleted=False
            ).first()
            
            if not question_type:
                return False, "Question type not found"

            # Prevent deletion of core types
            if question_type.type in QuestionTypeService.CORE_TYPES:
                return False, "Cannot delete core question types"

            # Check for active questions
            active_questions = Question.query.filter_by(
                question_type_id=type_id,
                is_deleted=False
            ).count()
            
            if active_questions > 0:
                return False, f"Question type has {active_questions} active questions"

            # Start transaction
            db.session.begin_nested()

            deletion_stats = {
                'questions': 0,
                'form_questions': 0,
                'form_answers': 0,
                'answers_submitted': 0
            }

            # Find all questions of this type (including already deleted ones)
            questions = Question.query.filter_by(question_type_id=type_id).all()

            for question in questions:
                if not question.is_deleted:
                    question.soft_delete()
                    deletion_stats['questions'] += 1

                # Get form questions for this question
                form_questions = FormQuestion.query.filter_by(
                    question_id=question.id,
                    is_deleted=False
                ).all()

                for fq in form_questions:
                    fq.soft_delete()
                    deletion_stats['form_questions'] += 1

                    # Get form answers for this form question
                    form_answers = FormAnswer.query.filter_by(
                        form_question_id=fq.id,
                        is_deleted=False
                    ).all()

                    for fa in form_answers:
                        fa.soft_delete()
                        deletion_stats['form_answers'] += 1

                        # Get submitted answers for this form answer
                        answers_submitted = AnswerSubmitted.query.filter_by(
                            form_answers_id=fa.id,
                            is_deleted=False
                        ).all()

                        for ans in answers_submitted:
                            ans.soft_delete()
                            deletion_stats['answers_submitted'] += 1

            # Finally soft delete the question type
            question_type.soft_delete()

            # Commit all changes
            db.session.commit()
            
            logger.info(f"Question type {type_id} and associated data soft deleted. Stats: {deletion_stats}")
            return True, deletion_stats

        except Exception as e:
            db.session.rollback()
            error_msg = f"Error deleting question type: {str(e)}"
            logger.error(error_msg)
            return False, error_msg