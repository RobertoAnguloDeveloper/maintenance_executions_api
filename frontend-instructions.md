# 🛠️ Maintenance Executions API
## Functional Requirements & API Documentation

## 📋 Table of Contents
1. [User Management](#user-management)
2. [Form Management](#form-management)
3. [Question Management](#question-management)
4. [Submission Management](#submission-management)
5. [API Endpoints Reference](#api-endpoints)
6. [Frontend Implementation Guidelines](#frontend-guidelines)

## 👥 User Management <a name="user-management"></a>

### Authentication & Authorization
- Users must log in using username/password
- JWT token is provided upon successful authentication
- Token must be included in all subsequent requests
- Role-based access control (Admin, Site Manager, Supervisor, Technician)

### User Roles & Permissions
#### 👑 Admin
- Full system access
- User management
- Role management
- Environment management

#### 🏢 Site Manager
- Environment-specific access
- User management within environment
- Form management within environment

#### 👨‍💼 Supervisor
- Form creation and management
- Review submissions
- Generate reports

#### 👨‍🔧 Technician
- View assigned forms
- Submit form responses
- Upload attachments

## 📝 Form Management <a name="form-management"></a>

### Form Creation
- Title and description required
- Public/private visibility setting
- Multiple question types supported
- Question ordering capability
- Optional remarks for questions

### Question Types
- Single Text (`single_text`)
- Multiple Choice (`multiple_choice`)
- Single Choice (`single_choice`)
- Date (`date`)

### Form Submissions
- Answer validation based on question type
- File attachment support
- Signature capture support
- Remarks for specific answers

## ❓ Question Management <a name="question-management"></a>

### Question Configuration
- Question text
- Question type
- Order number
- Remarks flag

### Answer Management
- Answer values
- Optional remarks
- Multiple answers for choice questions

## 📨 Submission Management <a name="submission-management"></a>

### Submission Process
- Form data validation
- File upload support
- Signature capture
- Submission timestamp
- User tracking

### File Attachments
- Multiple file support
- Type validation
- Size limits
- Storage management

## 🔌 API Endpoints Reference <a name="api-endpoints"></a>

### Authentication
```http
POST /api/users/login
{
    "username": string,
    "password": string
}

Response: {
    "access_token": string
}
```

### User Management
```http
# User Registration (Admin only)
POST /api/users/register
{
    "first_name": string,
    "last_name": string,
    "email": string,
    "username": string,
    "password": string,
    "role_id": integer,
    "environment_id": integer
}

# Get Users
GET /api/users
GET /api/users/{user_id}
GET /api/users/current
GET /api/users/byRole/{role_id}
GET /api/users/byEnvironment/{environment_id}

# Update User
PUT /api/users/{user_id}

# Delete User
DELETE /api/users/{user_id}
```

### Form Management
```http
# Create Form
POST /api/forms
{
    "title": string,
    "description": string,
    "is_public": boolean,
    "questions": array
}

# Get Forms
GET /api/forms
GET /api/forms/{form_id}
GET /api/forms/public

# Update Form
PUT /api/forms/{form_id}

# Delete Form
DELETE /api/forms/{form_id}

# Form Questions
POST /api/forms/{form_id}/questions
PUT /api/forms/{form_id}/questions/reorder
```

### Question Management
```http
# Create Question
POST /api/questions
{
    "text": string,
    "question_type_id": integer,
    "order_number": integer,
    "has_remarks": boolean
}

# Get Questions
GET /api/questions
GET /api/questions/{question_id}
GET /api/questions/type/{type_id}

# Update Question
PUT /api/questions/{question_id}

# Delete Question
DELETE /api/questions/{question_id}
```

### Form Submissions
```http
# Submit Form
POST /api/form_submissions
{
    "form_id": integer,
    "answers": array,
    "attachments": array
}

# Get Submissions
GET /api/form_submissions
GET /api/form_submissions/{submission_id}
GET /api/form_submissions/user/{username}
GET /api/form_submissions/form/{form_id}

# Get Filled Form
GET /api/form_submissions/filled/{submission_id}

# Delete Submission
DELETE /api/form_submissions/{submission_id}
```

### Attachments
```http
# Upload Attachment
POST /api/attachments
{
    "form_submission_id": integer,
    "file_type": string,
    "file_path": string,
    "file_name": string,
    "file_size": integer,
    "is_signature": boolean
}

# Get Attachments
GET /api/attachments/{attachment_id}
GET /api/attachments/submission/{form_submission_id}

# Delete Attachment
DELETE /api/attachments/{attachment_id}
```

### Data Export
```http
GET /api/export/{form_id}?format=csv
Supported formats: csv, excel, pdf
```

## 🎨 Frontend Implementation Guidelines <a name="frontend-guidelines"></a>

### Required Templates
1. **Authentication**
   - `login.html`
   - `register.html` (admin only)

2. **Dashboard**
   - `dashboard/index.html`
   - `dashboard/stats.html`

3. **User Management**
   - `users/index.html`
   - `users/create.html`
   - `users/edit.html`

4. **Forms**
   - `forms/index.html`
   - `forms/create.html`
   - `forms/edit.html`
   - `forms/view.html`

5. **Submissions**
   - `submissions/index.html`
   - `submissions/view.html`
   - `submissions/my_submissions.html`

### Implementation Notes

#### Authentication
- Store JWT token in localStorage
- Include token in Authorization header
- Implement token refresh mechanism
- Handle expired tokens

#### Form Building
- Implement dynamic form builder
- Support all question types
- Handle question ordering
- Implement file upload preview

#### Form Submission
- Client-side validation
- File upload progress
- Signature pad integration
- Autosave functionality

#### Data Display
- Implement pagination
- Sorting capabilities
- Filtering options
- Export functionality

### Security Considerations
- CSRF protection
- XSS prevention
- Input sanitization
- File upload validation