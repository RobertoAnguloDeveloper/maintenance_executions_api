import pytest
from app.services.question_type_service import QuestionTypeService

def test_create_question_type(app_context, session):
    """Test QuestionTypeService create method."""
    question_type, error = QuestionTypeService.create_question_type('Checkbox')
    
    assert error is None
    assert question_type is not None
    assert question_type.type == 'Checkbox'

@pytest.mark.parametrize("type_name,expected_error", [
    ('', "Type name cannot be empty"),
    (None, "Type name is required"),
    ('A' * 256, "Type name cannot exceed 255 characters"),
    ('<script>alert("xss")</script>', "Type name contains invalid characters"),
])
def test_create_question_type_validation(app_context, session, type_name, expected_error):
    """Test question type creation with invalid inputs."""
    question_type, error = QuestionTypeService.create_question_type(type_name)
    
    assert question_type is None
    assert error == expected_error

def test_create_duplicate_question_type(app_context, session, sample_question_type):
    """Test creating a question type with duplicate name."""
    session.refresh(sample_question_type)
    new_question_type, error = QuestionTypeService.create_question_type(sample_question_type.type)
    
    assert new_question_type is None
    assert error == "A question type with this name already exists"

@pytest.mark.parametrize("existing_name,update_name,expected_error", [
    ('Text', 'Multiple Choice', None),
    ('Text', 'Text', "A question type with this name already exists"),
    ('Text', '', "Type name cannot be empty"),
    ('Text', 'A' * 256, "Type name cannot exceed 255 characters"),
])
def test_update_question_type_validation(app_context, session, existing_name, update_name, expected_error):
    """Test question type updates with various scenarios."""
    # Create initial question type
    question_type = QuestionTypeService.create_question_type(existing_name)[0]
    session.refresh(question_type)
    
    # Attempt update
    updated_type, error = QuestionTypeService.update_question_type(question_type.id, update_name)
    
    if expected_error:
        assert updated_type is None
        assert error == expected_error
    else:
        assert error is None
        assert updated_type is not None
        assert updated_type.type == update_name

def test_get_question_type_not_found(app_context, session):
    """Test retrieving a non-existent question type."""
    question_type = QuestionTypeService.get_question_type(999)
    assert question_type is None

@pytest.mark.parametrize("invalid_id", [
    None,
    0,
    -1,
    'invalid',
])
def test_get_question_type_invalid_id(app_context, session, invalid_id):
    """Test retrieving question type with invalid IDs."""
    question_type = QuestionTypeService.get_question_type(invalid_id)
    assert question_type is None

def test_delete_question_type_with_relations(app_context, session, sample_question_type, sample_question):
    """Test deleting a question type that has related questions."""
    session.refresh(sample_question_type)
    success, error = QuestionTypeService.delete_question_type(sample_question_type.id)
    
    assert not success
    assert "Cannot delete question type with existing questions" in error

def test_concurrent_creation(app_context, session):
    """Test handling concurrent creation of question types."""
    # Simulate concurrent creation of the same question type
    type_name = "Concurrent Type"
    
    # First creation should succeed
    first_type, error1 = QuestionTypeService.create_question_type(type_name)
    assert error1 is None
    assert first_type is not None
    
    # Second creation should fail
    second_type, error2 = QuestionTypeService.create_question_type(type_name)
    assert second_type is None
    assert "already exists" in error2

def test_update_nonexistent_type(app_context, session):
    """Test updating a non-existent question type."""
    updated_type, error = QuestionTypeService.update_question_type(999, "New Name")
    assert updated_type is None
    assert "Question type not found" in error

def test_delete_nonexistent_type(app_context, session):
    """Test deleting a non-existent question type."""
    success, error = QuestionTypeService.delete_question_type(999)
    assert not success
    assert "Question type not found" in error