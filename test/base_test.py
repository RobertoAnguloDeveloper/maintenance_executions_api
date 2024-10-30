from flask_testing import TestCase
from app import create_app, db
from conftest import TestConfig

class BaseTest(TestCase):
    """Base test class with common functionality."""
    
    def create_app(self):
        """Create and configure the test application."""
        app = create_app(TestConfig)
        return app

    def setUp(self):
        """Set up test database."""
        db.create_all()

    def tearDown(self):
        """Clean up test database."""
        db.session.remove()
        db.drop_all()

    def create_test_data(self):
        """Create common test data."""
        pass