# app/models/__init__.py

from .user import User
from .role import Role
from .permission import Permission
from .role_permission import RolePermission
from .environment import Environment
from .question_type import QuestionType
from .question import Question
from .answer import Answer
from .form import Form
from .form_question import FormQuestion
from .form_answer import FormAnswer
from .form_submission import FormSubmission
from .answer_submitted import AnswerSubmitted
from .attachment import Attachment
from .token_blocklist import TokenBlocklist
from .report_template import ReportTemplate
from .form_assignment import FormAssignment # New import

__all__ = [
    'User',
    'Role',
    'Permission',
    'RolePermission',
    'Environment',
    'QuestionType',
    'Question',
    'Answer',
    'Form',
    'FormQuestion',
    'FormAnswer',
    'FormSubmission',
    'AnswerSubmitted',
    'Attachment',
    'TokenBlocklist',
    'ReportTemplate',
    'FormAssignment' # New model added
]