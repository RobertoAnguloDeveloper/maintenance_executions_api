from app.controllers.question_type_controller import QuestionTypeController
from app.models.question_type import QuestionType

def test_create_question_type(app_context, session):
    """Test QuestionTypeController create method."""
    question_type, error = QuestionTypeController.create_question_type('Date')
    
    assert error is None
    assert question_type is not None
    assert question_type.type == 'Date'

def test_get_all_question_types(app_context, session, sample_question_type):
    """Test retrieving all question types."""
    # Store the sample_question_type id
    sample_id = sample_question_type.id
    sample_type = sample_question_type.type

    # Clear existing data
    session.query(QuestionType).delete()
    session.commit()

    # Re-add our test data
    question_type = QuestionType(type=sample_type)
    session.add(question_type)
    session.commit()
    session.refresh(question_type)

    # Get all types
    types = QuestionTypeController.get_all_question_types()
    
    assert len(types) == 1
    assert types[0].type == sample_type

def test_get_question_type(app_context, session, sample_question_type):
    """Test retrieving a specific question type."""
    session.refresh(sample_question_type)
    type_id = sample_question_type.id
    
    question_type = QuestionTypeController.get_question_type(type_id)
    
    assert question_type is not None
    assert question_type.id == type_id
    assert question_type.type == sample_question_type.type

def test_update_question_type(app_context, session, sample_question_type):
    """Test updating a question type."""
    session.refresh(sample_question_type)
    type_id = sample_question_type.id
    
    updated_type, error = QuestionTypeController.update_question_type(
        type_id,
        'Updated Type'
    )
    
    assert error is None
    assert updated_type is not None
    assert updated_type.type == 'Updated Type'

def test_delete_question_type(app_context, session, sample_question_type):
    """Test deleting a question type."""
    session.refresh(sample_question_type)
    type_id = sample_question_type.id
    
    success, error = QuestionTypeController.delete_question_type(type_id)
    
    assert error is None
    assert success is True
    
    # Verify deletion
    deleted_type = QuestionTypeController.get_question_type(type_id)
    assert deleted_type is None