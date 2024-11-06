"""add soft delete columns

Revision ID: add_soft_delete_columns
Create Date: 2024-11-05 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# List of tables that need soft delete columns
TABLES = [
    'users', 'roles', 'permissions', 'environments', 'questions',
    'question_types', 'answers', 'forms', 'form_questions',
    'form_answers', 'form_submissions', 'answers_submitted',
    'attachments', 'role_permissions'
]

def upgrade():
    for table in TABLES:
        op.add_column(table, sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'))
        op.add_column(table, sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))

def downgrade():
    for table in TABLES:
        op.drop_column(table, 'deleted_at')
        op.drop_column(table, 'is_deleted')