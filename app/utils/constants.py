class Roles:
    ADMIN = 'Admin'
    SITE_MANAGER = 'Site Manager'
    SUPERVISOR = 'Supervisor'
    TECHNICIAN = 'Technician'

# Define endpoint access for each role
ROLE_ENDPOINTS = {
    Roles.ADMIN: {
        'can_access': '*',  # Admin can access everything
    },
    Roles.SITE_MANAGER: {
        'can_access': [
            # User management within environment
            'get_users_by_environment',
            # Form management within environment
            'get_forms_by_environment',
            'create_form',
            'update_form',
            'delete_form',
            # Question management
            'get_questions',
            'create_question',
            'update_question',
            'delete_question',
            # Other environment-specific endpoints...
        ]
    },
    Roles.SUPERVISOR: {
        'can_access': [
            # Form management within environment
            'get_forms_by_environment',
            'create_form',
            'update_form',
            'delete_form',
            # Question management
            'get_questions',
            'create_question',
            'update_question',
            'delete_question',
            # Other form-related endpoints...
        ]
    },
    Roles.TECHNICIAN: {
        'can_access': [
            # Form access
            'get_public_forms',
            'get_questions',
            # Form submission
            'create_form_submission',
            'update_own_submission',
            'delete_own_submission',
            'get_own_submissions',
            # Attachment management
            'create_attachment',
            'update_own_attachment',
            'delete_own_attachment',
            'get_own_attachments'
        ]
    }
}

# Additional constants for environment-specific access
ENVIRONMENT_RESTRICTED_ENDPOINTS = [
    'get_users_by_environment',
    'get_forms_by_environment',
    'get_questions_by_environment',
    # Add other environment-specific endpoints
]