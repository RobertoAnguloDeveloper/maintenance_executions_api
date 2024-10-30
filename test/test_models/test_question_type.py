import pytest
from app.models.question_type import QuestionType
from app import db

def test_create_question_type(app_context, session):
    """Test creating a new question type."""
    question_type = QuestionType(type='Multiple Choice')
    session.add(question_type)
    session.commit()

    assert question_type.id is not None
    assert question_type.type == 'Multiple Choice'
    assert question_type.created_at is not None
    assert question_type.updated_at is not None

def test_question_type_to_dict(app_context, session, sample_question_type):
    """Test the to_dict method."""
    session.refresh(sample_question_type)
    data = sample_question_type.to_dict()
    
    assert data['id'] == sample_question_type.id
    assert data['type'] == sample_question_type.type
    assert 'created_at' in data
    assert 'updated_at' in data

def test_question_type_relationship(app_context, session, sample_question_type, sample_question):
    """Test the relationship between QuestionType and Question."""
    session.refresh(sample_question_type)
    questions = list(sample_question_type.questions)
    assert len(questions) == 1
    assert questions[0].id == sample_question.id