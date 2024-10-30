import pytest
import json
from app.models.question_type import QuestionType

def test_create_question_type_api(app_context, client, session, auth_headers):
    """Test question type creation via API."""
    response = client.post(
        '/api/question_types',
        json={'type': 'Multiple Choice'},
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['question_type']['type'] == 'Multiple Choice'
    assert 'id' in data['question_type']

def test_get_all_question_types_api(app_context, client, session, sample_question_type, auth_headers):
    """Test getting all question types via API."""
    response = client.get('/api/question_types', headers=auth_headers)
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['type'] == sample_question_type.type

@pytest.mark.parametrize("invalid_data,expected_error", [
    ({}, "Type is required"),
    ({'type': ''}, "Type name cannot be empty"),
    ({'type': 'A' * 256}, "Type name cannot exceed 255 characters"),
    ({'type': '<script>alert("xss")</script>'}, "Type name contains invalid characters"),
])
def test_create_question_type_validation_api(app_context, client, session, invalid_data, expected_error, auth_headers):
    """Test API validation for question type creation."""
    response = client.post(
        '/api/question_types',
        json=invalid_data,
        headers=auth_headers
    )
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['error'] == expected_error

def test_create_duplicate_question_type_api(app_context, client, session, sample_question_type, auth_headers):
    """Test creating duplicate question type via API."""
    response = client.post(
        '/api/question_types',
        json={'type': sample_question_type.type},
        headers=auth_headers
    )
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['error'] == "A question type with this name already exists"

def test_update_question_type_api(app_context, client, session, sample_question_type, auth_headers):
    """Test updating question type via API."""
    response = client.put(
        f'/api/question_types/{sample_question_type.id}',
        json={'type': 'Updated Type'},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['question_type']['type'] == 'Updated Type'

def test_delete_question_type_api(app_context, client, session, sample_question_type, auth_headers):
    """Test deleting question type via API."""
    response = client.delete(
        f'/api/question_types/{sample_question_type.id}',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    
    # Verify deletion
    assert session.get(QuestionType, sample_question_type.id) is None

def test_get_nonexistent_question_type_api(app_context, client, session, auth_headers):
    """Test getting non-existent question type via API."""
    response = client.get('/api/question_types/999', headers=auth_headers)
    
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['error'] == "Question type not found"

def test_update_nonexistent_question_type_api(app_context, client, session, auth_headers):
    """Test updating non-existent question type via API."""
    response = client.put(
        '/api/question_types/999',
        json={'type': 'Updated Type'},
        headers=auth_headers
    )
    
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['error'] == "Question type not found"

def test_delete_nonexistent_question_type_api(app_context, client, session, auth_headers):
    """Test deleting non-existent question type via API."""
    response = client.delete('/api/question_types/999', headers=auth_headers)
    
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['error'] == "Question type not found"