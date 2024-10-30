import pytest
from flask import Flask
import os
import sys
from datetime import timedelta
from flask_jwt_extended import create_access_token

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.question_type import QuestionType
from app.models.question import Question
from app.views.question_type_views import question_type_bp

class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://rangulot:plg-cmms-2024@localhost/cmms_test'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'Angulo73202647'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    PRESERVE_CONTEXT_ON_EXCEPTION = False

@pytest.fixture(scope='session')
def app():
    """Create and configure a Flask test application."""
    _app = create_app(TestConfig)
    
    # Register test blueprints
    _app.register_blueprint(question_type_bp, url_prefix='/api/question_types')
    
    # Create all tables once for the test session
    with _app.app_context():
        db.create_all()
    
    yield _app
    
    # Clean up database after all tests
    with _app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def app_context(app):
    """Provide app context for each test."""
    with app.app_context() as ctx:
        yield ctx

@pytest.fixture(scope='function')
def db_session(app_context):
    """Provide clean database session for each test."""
    # Start a transaction
    connection = db.engine.connect()
    transaction = connection.begin()

    # Configure session for the connection
    session = db.create_scoped_session(
        options={"bind": connection, "binds": {}}
    )
    
    # Make this session the current one
    db.session = session

    yield session

    # Rollback transaction and clean up
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope='function')
def client(app):
    """Create a test client."""
    return app.test_client()

@pytest.fixture(scope='function')
def auth_headers(app):
    """Create valid JWT auth headers for testing."""
    with app.app_context():
        # Create a real JWT token
        access_token = create_access_token(
            identity='test-user',
            additional_claims={'role': 'admin'}
        )
        return {'Authorization': f'Bearer {access_token}'}

@pytest.fixture(scope='function')
def sample_question_type(db_session):
    """Create a sample question type."""
    try:
        question_type = QuestionType(type='Text')
        db_session.add(question_type)
        db_session.commit()
        db_session.refresh(question_type)
        return question_type
    except Exception as e:
        db_session.rollback()
        raise e

@pytest.fixture(scope='function')
def sample_question(db_session, sample_question_type):
    """Create a sample question."""
    try:
        question = Question(
            text='Test Question',
            question_type_id=sample_question_type.id,
            order_number=1,
            has_remarks=True
        )
        db_session.add(question)
        db_session.commit()
        db_session.refresh(question)
        return question
    except Exception as e:
        db_session.rollback()
        raise e

@pytest.fixture(autouse=True)
def clean_db(db_session):
    """Clean database after each test."""
    yield
    for table in reversed(db.metadata.sorted_tables):
        db_session.execute(table.delete())
    db_session.commit()