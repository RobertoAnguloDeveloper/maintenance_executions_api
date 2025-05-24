# app/services/report/report_config.py
from typing import Dict, List, Any, Type
from datetime import datetime, date
from app.models import (
    User, FormSubmission, AnswerSubmitted, Form, Role, Environment,
    Question, Answer, QuestionType, Permission, RolePermission,
    FormQuestion, FormAnswer, Attachment, TokenBlocklist,
    FormAssignment # Ensure FormAssignment is imported
)
import logging

# Configure logger
logger = logging.getLogger(__name__)
# Ensure EntityType and RoleType are correctly imported or defined
# from app.utils.permission_manager import EntityType, RoleType
# For standalone execution, we'll define placeholders if not available
try:
    from app.utils.permission_manager import EntityType, RoleType
except ImportError:
    logger.warning("EntityType or RoleType not found from app.utils.permission_manager. Using placeholder enums.")
    from enum import Enum
    class EntityType(Enum): # Placeholder
        USERS = "users"
        ROLES = "roles"
        FORMS = "forms"
        SUBMISSIONS = "submissions"
        ENVIRONMENTS = "environments"
        QUESTION_TYPES = "question_types"
        QUESTIONS = "questions"
        ANSWERS = "answers"
        ATTACHMENTS = "attachments"
        # Add other entity types as needed
    class RoleType(Enum): # Placeholder
        ADMIN = "admin"
        # Add other role types
        SITE_MANAGER = "site_manager"
        SUPERVISOR = "supervisor"
        TECHNICIAN = "technician"


import logging

logger = logging.getLogger(__name__)

# Constants
SUPPORTED_FORMATS = ["xlsx", "csv", "pdf", "docx", "pptx"]
MULTI_ENTITY_FORMATS = ["xlsx", "csv", "pdf", "docx"]
VISUAL_FORMATS = ["pdf", "docx", "pptx"]
DEFAULT_REPORT_TITLE = "Data Analysis Report"
MAX_XLSX_SHEET_NAME_LEN = 31
ANSWERS_PREFIX = "answers."
GENERIC_CATEGORICAL_COLS = [
    'type', 'name', 'status', 'action', 'role', 'environment', 'is_public',
    'is_deleted', 'is_super_user', 'is_signature', 'file_type', 'question_type',
    'entity_name' # Added
]
MAX_UNIQUE_GENERIC_CHART = 15
DEFAULT_CHART_TYPES = ["bar", "pie", "line", "scatter", "area", "histogram"]

# Model to entity mapping
MODEL_TO_ENTITY = {
    User: 'users',
    Role: 'roles',
    Permission: 'permissions',
    RolePermission: 'role_permissions',
    Environment: 'environments',
    QuestionType: 'question_types',
    Question: 'questions',
    Answer: 'answers',
    Form: 'forms',
    FormQuestion: 'form_questions',
    FormAnswer: 'form_answers',
    FormAssignment: 'form_assignments', # Added
    FormSubmission: 'form_submissions',
    AnswerSubmitted: 'answers_submitted',
    Attachment: 'attachments',
    TokenBlocklist: 'token_blocklist'
}

# Entity to model mapping (reverse of MODEL_TO_ENTITY)
ENTITY_TO_MODEL = {v: k for k, v in MODEL_TO_ENTITY.items()}

# Entity configuration
ENTITY_CONFIG = {
    'users': {
        'model': User,
        'view_permission_entity': EntityType.USERS,
        'default_columns': [
            "id", "username", "first_name", "last_name", "email",
            "contact_number", "role.name", "environment.name", "created_at"
        ],
        'available_columns': [
            "id", "username", "first_name", "last_name", "email",
            "contact_number", "role_id", "environment_id",
            "role.name", "role.description", "role.is_super_user",
            "environment.name", "environment.description",
            "created_at", "updated_at", "is_deleted", "deleted_at"
        ],
        'sensitive_columns': ["password_hash"],
        'hidden_columns': ["password_hash"],
        'analysis_hints': {
            'date_columns': ['created_at', 'updated_at', 'deleted_at'],
            'categorical_columns': [
                'role.name', 'environment.name', 'is_deleted',
                'username', 'email', 'first_name', 'last_name'
            ],
            'numerical_columns': ['id', 'role_id', 'environment_id'],
        },
        'chart_hints': {
            'bar_charts': ['role.name', 'environment.name', 'is_deleted'],
            'pie_charts': ['role.name', 'environment.name', 'is_deleted'],
            'time_series': ['created_at', 'updated_at'],
        },
        'default_sort': [{"field": "username", "direction": "asc"}],
        'stats_generators': ['generate_user_stats', '_generate_generic_stats'],
        'chart_generators': ['generate_user_charts', '_generate_generic_charts'],
        'insight_generators': ['generate_user_insights', '_generate_generic_insights'],
        'format_generators': {'pptx': '_generate_user_pptx'}
    },
    'roles': {
        'model': Role,
        'view_permission_entity': EntityType.ROLES,
        'default_columns': ["id", "name", "description", "is_super_user", "created_at"],
        'available_columns': [
            "id", "name", "description", "is_super_user",
            "created_at", "updated_at", "is_deleted", "deleted_at"
        ],
        'analysis_hints': {
            'date_columns': ['created_at', 'updated_at', 'deleted_at'],
            'categorical_columns': ['is_super_user', 'name', 'description', 'is_deleted'],
            'numerical_columns': ['id'],
        },
        'chart_hints': {
            'bar_charts': ['is_super_user', 'name'],
            'pie_charts': ['is_super_user', 'name'],
        },
        'default_sort': [{"field": "name", "direction": "asc"}],
        'stats_generators': ['generate_role_stats', '_generate_generic_stats'],
        'chart_generators': ['generate_role_charts', '_generate_generic_charts'],
        'insight_generators': ['generate_role_insights', '_generate_generic_insights'],
        'format_generators': {}
    },
    'permissions': {
        'model': Permission,
        'view_permission_entity': EntityType.ROLES,
        'default_columns': ["id", "name", "action", "entity", "description"],
        'available_columns': [
            "id", "name", "action", "entity", "description",
            "created_at", "updated_at", "is_deleted", "deleted_at"
        ],
        'analysis_hints': {
            'date_columns': ['created_at', 'updated_at', 'deleted_at'],
            'categorical_columns': ['name', 'action', 'entity', 'description', 'is_deleted'],
            'numerical_columns': ['id'],
        },
        'chart_hints': {
            'bar_charts': ['action', 'entity'],
            'pie_charts': ['action', 'entity'],
        },
        'default_sort': [{"field": "name", "direction": "asc"}],
        'stats_generators': ['generate_permission_stats', '_generate_generic_stats'],
        'chart_generators': ['generate_permission_charts', '_generate_generic_charts'],
        'insight_generators': ['_generate_generic_insights'],
        'format_generators': {}
    },
    'role_permissions': {
        'model': RolePermission,
        'view_permission_entity': EntityType.ROLES,
        'default_columns': [
            "id", "role_id", "permission_id", "role.name",
            "permission.name", "permission.action", "permission.entity"
        ],
        'available_columns': [
            "id", "role_id", "permission_id",
            "role.name", "role.description", "role.is_super_user",
            "permission.name", "permission.action", "permission.entity", "permission.description",
            "created_at", "updated_at", "is_deleted", "deleted_at"
        ],
        'analysis_hints': {
            'date_columns': ['created_at', 'updated_at', 'deleted_at'],
            'categorical_columns': [
                'role.name', 'permission.name', 'permission.action',
                'permission.entity', 'is_deleted'
            ],
            'numerical_columns': ['id', 'role_id', 'permission_id'],
        },
        'chart_hints': {
            'bar_charts': ['role.name', 'permission.action', 'permission.entity'],
            'pie_charts': ['role.name', 'permission.action', 'permission.entity'],
        },
        'default_sort': [
            {"field": "role_id", "direction": "asc"},
            {"field": "permission_id", "direction": "asc"}
        ],
        'stats_generators': ['generate_role_permission_stats', '_generate_generic_stats'],
        'chart_generators': ['_generate_generic_charts'],
        'insight_generators': ['_generate_generic_insights'],
        'format_generators': {}
    },
    'environments': {
        'model': Environment,
        'view_permission_entity': EntityType.ENVIRONMENTS,
        'default_columns': ["id", "name", "description", "created_at"],
        'available_columns': [
            "id", "name", "description",
            "created_at", "updated_at", "is_deleted", "deleted_at"
        ],
        'analysis_hints': {
            'date_columns': ['created_at', 'updated_at', 'deleted_at'],
            'categorical_columns': ['name', 'description', 'is_deleted'],
            'numerical_columns': ['id'],
        },
        'chart_hints': {
            'bar_charts': ['name'],
            'pie_charts': ['name'],
        },
        'default_sort': [{"field": "name", "direction": "asc"}],
        'stats_generators': ['generate_environment_stats', '_generate_generic_stats'],
        'chart_generators': ['generate_environment_charts', '_generate_generic_charts'],
        'insight_generators': ['_generate_generic_insights'],
        'format_generators': {}
    },
    'question_types': {
        'model': QuestionType,
        'view_permission_entity': EntityType.QUESTION_TYPES,
        'default_columns': ["id", "type", "created_at"],
        'available_columns': [
            "id", "type",
            "created_at", "updated_at", "is_deleted", "deleted_at"
        ],
        'analysis_hints': {
            'date_columns': ['created_at', 'updated_at', 'deleted_at'],
            'categorical_columns': ['type', 'is_deleted'],
            'numerical_columns': ['id'],
        },
        'chart_hints': {
            'bar_charts': ['type'],
            'pie_charts': ['type'],
        },
        'default_sort': [{"field": "type", "direction": "asc"}],
        'stats_generators': ['generate_question_type_stats', '_generate_generic_stats'],
        'chart_generators': ['_generate_generic_charts'],
        'insight_generators': ['_generate_generic_insights'],
        'format_generators': {}
    },
    'questions': {
        'model': Question,
        'view_permission_entity': EntityType.QUESTIONS,
        'default_columns': [
            "id", "text", "question_type.type", "is_signature",
            "remarks", "created_at"
        ],
        'available_columns': [
            "id", "text", "question_type_id", "is_signature", "remarks",
            "question_type.type",
            "created_at", "updated_at", "is_deleted", "deleted_at"
        ],
        'analysis_hints': {
            'date_columns': ['created_at', 'updated_at', 'deleted_at'],
            'categorical_columns': [
                'question_type.type', 'is_signature', 'is_deleted'
            ],
            'numerical_columns': ['id', 'question_type_id'],
            'text_columns': ['text', 'remarks'],
        },
        'chart_hints': {
            'bar_charts': ['question_type.type', 'is_signature'],
            'pie_charts': ['question_type.type', 'is_signature'],
        },
        'default_sort': [{"field": "text", "direction": "asc"}],
        'stats_generators': ['generate_question_stats', '_generate_generic_stats'],
        'chart_generators': ['_generate_generic_charts'],
        'insight_generators': ['_generate_generic_insights'],
        'format_generators': {}
    },
    'answers': {
        'model': Answer,
        'view_permission_entity': EntityType.ANSWERS,
        'default_columns': ["id", "value", "remarks", "created_at"],
        'available_columns': [
            "id", "value", "remarks",
            "created_at", "updated_at", "is_deleted", "deleted_at"
        ],
        'analysis_hints': {
            'date_columns': ['created_at', 'updated_at', 'deleted_at'],
            'categorical_columns': ['is_deleted'],
            'numerical_columns': ['id'],
            'text_columns': ['value', 'remarks'],
        },
        'chart_hints': {},
        'default_sort': [{"field": "value", "direction": "asc"}],
        'stats_generators': ['_generate_generic_stats'],
        'chart_generators': ['_generate_generic_charts'],
        'insight_generators': ['_generate_generic_insights'],
        'format_generators': {}
    },
    'forms': {
        'model': Form,
        'view_permission_entity': EntityType.FORMS,
        'default_columns': [
            "id", "title", "description", "creator.username",
            "creator.environment.name", "is_public",
            "attachments_required", # Updated
            "created_at"
        ],
        'available_columns': [
            "id", "title", "description", "user_id", "is_public",
            "attachments_required", # Updated
            "creator.username", "creator.email", "creator.first_name", "creator.last_name",
            "creator.environment.name", "creator.environment.description",
            "created_at", "updated_at", "is_deleted", "deleted_at"
        ],
        'analysis_hints': {
            'date_columns': ['created_at', 'updated_at', 'deleted_at'],
            'categorical_columns': [
                'creator.username', 'creator.environment.name',
                'is_public', 'is_deleted', 'title',
                'attachments_required' # Updated
            ],
            'numerical_columns': ['id', 'user_id'],
            'text_columns': ['title', 'description'],
        },
        'chart_hints': {
            'bar_charts': ['creator.username', 'is_public', 'creator.environment.name', 'attachments_required'],
            'pie_charts': ['is_public', 'creator.environment.name', 'attachments_required'],
        },
        'default_sort': [{"field": "title", "direction": "asc"}],
        'stats_generators': ['generate_form_stats', '_generate_generic_stats'],
        'chart_generators': ['generate_form_charts', '_generate_generic_charts'],
        'insight_generators': ['generate_form_insights', '_generate_generic_insights'],
        'format_generators': {}
    },
    'form_questions': {
        'model': FormQuestion,
        'view_permission_entity': EntityType.FORMS,
        'default_columns': [
            "id", "form_id", "question_id", "order_number",
            "form.title", "question.text", "question.question_type.type"
        ],
        'available_columns': [
            "id", "form_id", "question_id", "order_number",
            "form.title", "form.description", "form.is_public",
            "question.text", "question.is_signature", "question.question_type.type",
            "created_at", "updated_at", "is_deleted", "deleted_at"
        ],
        'analysis_hints': {
            'date_columns': ['created_at', 'updated_at', 'deleted_at'],
            'categorical_columns': [
                'form.title', 'question.text', 'question.question_type.type',
                'question.is_signature', 'is_deleted'
            ],
            'numerical_columns': ['id', 'form_id', 'question_id', 'order_number'],
        },
        'chart_hints': {
            'bar_charts': ['form.title', 'question.question_type.type', 'order_number'],
            'pie_charts': ['question.question_type.type'],
        },
        'default_sort': [
            {"field": "form_id", "direction": "asc"},
            {"field": "order_number", "direction": "asc"}
        ],
        'stats_generators': ['generate_form_question_stats', '_generate_generic_stats'],
        'chart_generators': ['_generate_generic_charts'],
        'insight_generators': ['_generate_generic_insights'],
        'format_generators': {}
    },
    'form_answers': {
        'model': FormAnswer,
        'view_permission_entity': EntityType.FORMS,
        'default_columns': [
            "id", "form_question_id", "answer_id",
            "form_question.question.text", "answer.value", "remarks"
        ],
        'available_columns': [
            "id", "form_question_id", "answer_id", "remarks",
            "form_question.form.title", "form_question.form.description",
            "form_question.question.text", "form_question.question.question_type.type",
            "form_question.order_number", "answer.value", "answer.remarks",
            "created_at", "updated_at", "is_deleted", "deleted_at"
        ],
        'analysis_hints': {
            'date_columns': ['created_at', 'updated_at', 'deleted_at'],
            'categorical_columns': [
                'form_question.question.text',
                'form_question.question.question_type.type',
                'answer.value', 'is_deleted'
            ],
            'numerical_columns': ['id', 'form_question_id', 'answer_id'],
            'text_columns': ['remarks', 'answer.value', 'answer.remarks'],
        },
        'chart_hints': {
            'bar_charts': ['form_question.form.title', 'form_question.question.question_type.type'],
            'pie_charts': ['form_question.question.question_type.type'],
        },
        'default_sort': [{"field": "form_question_id", "direction": "asc"}],
        'stats_generators': ['_generate_generic_stats'],
        'chart_generators': ['_generate_generic_charts'],
        'insight_generators': ['_generate_generic_insights'],
        'format_generators': {}
    },
    'form_assignments': {
        'model': FormAssignment,
        'view_permission_entity': EntityType.FORMS,
        'default_columns': [
            "id",
            "form_id",
            "form.title",
            "entity_name",
            "entity_id",
            "assigned_entity_identifier", # Will hold username for users, name for roles/environments
            "created_at"
        ],
        'available_columns': [
            "id", "form_id", "entity_name", "entity_id",
            "form.title", "form.description", "form.is_public",
            "form.creator.username", # From related Form's creator
            "created_at", "updated_at", "is_deleted", "deleted_at",
            "assigned_entity_identifier", # Populated by ReportService with main identifier
            # Optional specific fields from assigned entities (ReportService would populate if requested)
            "assigned_user_username", "assigned_user_email", "assigned_user_fullname",
            "assigned_role_name", "assigned_role_description",
            "assigned_environment_name", "assigned_environment_description",
        ],
        'analysis_hints': {
            'date_columns': ['created_at', 'updated_at', 'deleted_at'],
            'categorical_columns': [
                'entity_name', 'form.title', 'is_deleted', 'assigned_entity_identifier'
            ],
            'numerical_columns': ['id', 'form_id', 'entity_id'],
        },
        'chart_hints': {
            'bar_charts': ['entity_name', 'form.title', 'assigned_entity_identifier'],
            'pie_charts': ['entity_name'],
        },
        'default_sort': [
            {"field": "form_id", "direction": "asc"},
            {"field": "entity_name", "direction": "asc"}
        ],
        'stats_generators': ['_generate_generic_stats'],
        'chart_generators': ['_generate_generic_charts'],
        'insight_generators': ['_generate_generic_insights'],
        'format_generators': {}
    },
    'form_submissions': {
        'model': FormSubmission,
        'view_permission_entity': EntityType.SUBMISSIONS,
        'default_columns': [
            "id", "form_id", "form.title", "submitted_by",
            "submitted_at", "created_at"
        ],
        'available_columns': [
            "id", "form_id", "submitted_by", "submitted_at",
            "form.title", "form.description", "form.is_public",
            "form.creator.username", "form.creator.email",
            "form.creator.environment.name",
            "created_at", "updated_at", "is_deleted", "deleted_at"
            # Dynamic answer columns (e.g., "answers.What is your name?") are added by ReportDataFetcher
        ],
        'analysis_hints': {
            'date_columns': ['submitted_at', 'created_at', 'updated_at', 'deleted_at'],
            'categorical_columns': [
                'submitted_by', 'form.title', 'form.creator.username',
                'form.creator.environment.name', 'is_deleted'
            ],
            'numerical_columns': ['id', 'form_id'],
            'dynamic_answer_prefix': ANSWERS_PREFIX,
        },
        'chart_hints': {
            'bar_charts': ['submitted_by', 'form.title', 'form.creator.environment.name'],
            'pie_charts': ['form.title', 'submitted_by', 'form.creator.environment.name'],
            'time_series': ['submitted_at', 'created_at'],
        },
        'default_sort': [{"field": "submitted_at", "direction": "desc"}],
        'stats_generators': ['generate_submission_stats', '_generate_generic_stats'],
        'chart_generators': ['generate_submission_charts', '_generate_generic_charts'],
        'insight_generators': ['generate_submission_insights', '_generate_generic_insights'],
        'format_generators': {'pptx': '_generate_submission_pptx'}
    },
    'answers_submitted': {
        'model': AnswerSubmitted,
        'view_permission_entity': EntityType.SUBMISSIONS,
        'default_columns': [
            "id", "form_submission_id", "form_submission.form.title",
            "question", "question_type", "answer", "created_at"
        ],
        'available_columns': [
            "id", "question", "question_type", "answer", "form_submission_id",
            "column", "row", "cell_content",
            "form_submission.submitted_by", "form_submission.submitted_at",
            "form_submission.form.title", "form_submission.form.description",
            "created_at", "updated_at", "is_deleted", "deleted_at"
        ],
        'analysis_hints': {
            'date_columns': ['created_at', 'updated_at', 'deleted_at', 'form_submission.submitted_at'],
            'categorical_columns': [
                'question', 'question_type', 'form_submission.form.title',
                'form_submission.submitted_by', 'is_deleted'
            ],
            'numerical_columns': ['id', 'form_submission_id', 'column', 'row'],
            'text_columns': ['answer', 'cell_content'],
        },
        'chart_hints': {
            'bar_charts': ['question_type', 'form_submission.form.title', 'form_submission.submitted_by'],
            'pie_charts': ['question_type', 'form_submission.form.title'],
        },
        'default_sort': [{"field": "created_at", "direction": "desc"}],
        'stats_generators': ['generate_answers_submitted_stats', '_generate_generic_stats'],
        'chart_generators': ['generate_answers_submitted_charts', '_generate_generic_charts'],
        'insight_generators': ['_generate_generic_insights'],
        'format_generators': {}
    },
    'attachments': {
        'model': Attachment,
        'view_permission_entity': EntityType.ATTACHMENTS,
        'default_columns': [
            "id", "form_submission_id", "form_submission.form.title",
            "file_path", "file_type", "is_signature",
            "signature_author", "created_at"
        ],
        'available_columns': [
            "id", "form_submission_id", "file_type", "file_path",
            "is_signature", "signature_position", "signature_author",
            "form_submission.submitted_by", "form_submission.submitted_at",
            "form_submission.form.title", "form_submission.form.description",
            "created_at", "updated_at", "is_deleted", "deleted_at"
        ],
        'analysis_hints': {
            'date_columns': ['created_at', 'updated_at', 'deleted_at', 'form_submission.submitted_at'],
            'categorical_columns': [
                'file_type', 'is_signature', 'signature_author',
                'form_submission.form.title', 'form_submission.submitted_by', 'is_deleted'
            ],
            'numerical_columns': ['id', 'form_submission_id'],
            'text_columns': ['file_path', 'signature_position'],
        },
        'chart_hints': {
            'bar_charts': ['file_type', 'is_signature', 'form_submission.form.title'],
            'pie_charts': ['file_type', 'is_signature', 'form_submission.form.title'],
            'time_series': ['created_at', 'form_submission.submitted_at'],
        },
        'default_sort': [{"field": "created_at", "direction": "desc"}],
        'stats_generators': ['generate_attachment_stats', '_generate_generic_stats'],
        'chart_generators': ['generate_attachment_charts', '_generate_generic_charts'],
        'insight_generators': ['_generate_generic_insights'],
        'format_generators': {}
    },
    'token_blocklist': {
        'model': TokenBlocklist,
        'view_permission_entity': EntityType.USERS, # Admin/security relevant
        'default_columns': ["id", "jti", "created_at"],
        'available_columns': ["id", "jti", "created_at"],
        'analysis_hints': {
            'date_columns': ['created_at'],
            'categorical_columns': [],
            'numerical_columns': ['id'],
            'text_columns': ['jti'],
        },
        'chart_hints': {
            'time_series': ['created_at'],
        },
        'default_sort': [{"field": "created_at", "direction": "desc"}],
        'stats_generators': ['_generate_generic_stats'],
        'chart_generators': ['_generate_generic_charts'],
        'insight_generators': ['_generate_generic_insights'],
        'format_generators': {}
    }
}

# PDF/Document constants
DEFAULT_CHART_WIDTH = 6.5  # in inches
DEFAULT_CHART_HEIGHT = 3.5 # in inches

# PPTX constants
DEFAULT_PPTX_CHART_WIDTH = 8    # in inches
DEFAULT_PPTX_CHART_HEIGHT = 4.5 # in inches
DEFAULT_PPTX_CHART_TOP = 1.5    # in inches from top of slide
DEFAULT_PPTX_CHART_LEFT = 1     # in inches from left of slide
DEFAULT_PPTX_TABLE_ROWS = 10    # Default max rows for tables in PPTX
