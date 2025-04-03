# API Documentation

## Table of Contents
- [User Management](#user-management)
- [Roles & Permissions](#roles--permissions)
- [Environments](#environments)
- [Forms](#forms)
- [Form Questions](#form-questions)
- [Form Answers](#form-answers)
- [Form Submissions](#form-submissions)
- [Questions & Answers](#questions--answers)
- [Answers Submitted](#answers-submitted)
- [Attachments](#attachments)
- [Export](#export)
- [CMMS Configuration](#cmms-configuration)
- [Health & Status](#health--status)

## User Management

### Register User
- **URL:** `/api/users/register`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Create users, Admin role
- **Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "contact_number": "1234567890",
  "username": "johndoe",
  "password": "password123",
  "role_id": 2,
  "environment_id": 1
}
```

### Login
- **URL:** `/api/users/login`
- **Method:** `POST`
- **Auth:** None
- **Request Body:**
```json
{
  "username": "johndoe",
  "password": "password123"
}
```

### Get All Users
- **URL:** `/api/users`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View users

### Get Batch Users
- **URL:** `/api/users/batch`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View users
- **Query Parameters:**
  - `page`: Page number (default: 1)
  - `per_page`: Items per page (default: 50)
  - `include_deleted`: Include deleted users (true/false)
  - `role_id`: Filter by role ID
  - `environment_id`: Filter by environment ID

### Get Users Compact List
- **URL:** `/api/users/compact-list`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View users

### Get Users By Role
- **URL:** `/api/users/byRole/{role_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View users

### Get Users By Environment
- **URL:** `/api/users/byEnvironment/{environment_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View users

### Search Users
- **URL:** `/api/users/search`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View users
- **Query Parameters:**
  - `id`: User ID
  - `username`: Username
  - `role_id`: Role ID
  - `environment_id`: Environment ID

### Get User
- **URL:** `/api/users/{user_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View users

### Update User
- **URL:** `/api/users/{user_id}`
- **Method:** `PUT`
- **Auth:** JWT required
- **Permissions:** Update users
- **Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "contact_number": "1234567890",
  "password": "newpassword123",
  "role_id": 2,
  "environment_id": 1
}
```

### Delete User
- **URL:** `/api/users/{user_id}`
- **Method:** `DELETE`
- **Auth:** JWT required
- **Permissions:** Delete users

### Get Current User
- **URL:** `/api/users/current`
- **Method:** `GET`
- **Auth:** JWT required

## Roles & Permissions

### Create Role
- **URL:** `/api/roles`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Admin role
- **Request Body:**
```json
{
  "name": "Supervisor",
  "description": "Supervises technicians",
  "is_super_user": false
}
```

### Get All Roles
- **URL:** `/api/roles`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View roles

### Get Batch Roles
- **URL:** `/api/roles/batch`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View roles
- **Query Parameters:**
  - `page`: Page number (default: 1)
  - `per_page`: Items per page (default: 50)
  - `include_deleted`: Include deleted roles (true/false)
  - `is_super_user`: Filter by super user status (true/false)

### Get Role
- **URL:** `/api/roles/{role_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View roles

### Update Role
- **URL:** `/api/roles/{role_id}`
- **Method:** `PUT`
- **Auth:** JWT required
- **Permissions:** Admin role
- **Request Body:**
```json
{
  "name": "Senior Supervisor",
  "description": "Supervises other supervisors",
  "is_super_user": false
}
```

### Delete Role
- **URL:** `/api/roles/{role_id}`
- **Method:** `DELETE`
- **Auth:** JWT required
- **Permissions:** Admin role

### Remove Permission From Role
- **URL:** `/api/roles/{role_id}/permissions/{permission_id}`
- **Method:** `DELETE`
- **Auth:** JWT required
- **Permissions:** Admin role

### Create Permission
- **URL:** `/api/permissions`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Admin role
- **Request Body:**
```json
{
  "name": "create_forms",
  "action": "create",
  "entity": "forms",
  "description": "Can create new forms"
}
```

### Get All Permissions
- **URL:** `/api/permissions`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View roles

### Get Batch Permissions
- **URL:** `/api/permissions/batch`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View roles
- **Query Parameters:**
  - `page`: Page number (default: 1)
  - `per_page`: Items per page (default: 50)
  - `include_deleted`: Include deleted permissions (true/false)
  - `action`: Filter by action
  - `entity`: Filter by entity

### Get Permission
- **URL:** `/api/permissions/{permission_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View roles

### Check User Permission
- **URL:** `/api/permissions/check/{user_id}/{permission_name}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** Admin role

### Update Permission
- **URL:** `/api/permissions/{permission_id}`
- **Method:** `PUT`
- **Auth:** JWT required
- **Permissions:** Admin role
- **Request Body:**
```json
{
  "name": "create_forms",
  "action": "create",
  "entity": "forms",
  "description": "Can create and edit forms"
}
```

### Delete Permission
- **URL:** `/api/permissions/{permission_id}`
- **Method:** `DELETE`
- **Auth:** JWT required
- **Permissions:** Admin role

### Get All Role-Permissions
- **URL:** `/api/role-permissions`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** Admin role

### Get Batch Role-Permissions
- **URL:** `/api/role-permissions/batch`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** Admin role
- **Query Parameters:**
  - `page`: Page number (default: 1)
  - `per_page`: Items per page (default: 50)
  - `include_deleted`: Include deleted mappings (true/false)
  - `role_id`: Filter by role ID
  - `permission_id`: Filter by permission ID

### Get Roles With Permissions
- **URL:** `/api/role-permissions/roles_with_permissions`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View roles

### Assign Permission To Role
- **URL:** `/api/role-permissions`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Admin role
- **Request Body:**
```json
{
  "role_id": 2,
  "permission_id": 5
}
```

### Bulk Assign Permissions
- **URL:** `/api/role-permissions/bulk-assign`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Admin role
- **Request Body:**
```json
{
  "role_id": 2,
  "permission_ids": [1, 2, 3, 4, 5]
}
```

### Update Role-Permission
- **URL:** `/api/role-permissions/{role_permission_id}`
- **Method:** `PUT`
- **Auth:** JWT required
- **Permissions:** Admin role
- **Request Body:**
```json
{
  "role_id": 3,
  "permission_id": 5,
  "is_deleted": false
}
```

### Remove Permission From Role
- **URL:** `/api/role-permissions/{role_permission_id}`
- **Method:** `DELETE`
- **Auth:** JWT required
- **Permissions:** Admin role

### Get Permissions By Role
- **URL:** `/api/role-permissions/role/{role_id}/permissions`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View roles

### Get Roles By Permission
- **URL:** `/api/role-permissions/permission/{permission_id}/roles`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View roles

## Environments

### Create Environment
- **URL:** `/api/environments`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Admin role
- **Request Body:**
```json
{
  "name": "Factory A",
  "description": "Main production facility"
}
```

### Get All Environments
- **URL:** `/api/environments`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View environments

### Get Batch Environments
- **URL:** `/api/environments/batch`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View environments
- **Query Parameters:**
  - `page`: Page number (default: 1)
  - `per_page`: Items per page (default: 50)
  - `include_deleted`: Include deleted environments (true/false)

### Get Environment
- **URL:** `/api/environments/{environment_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View environments

### Get Environment By Name
- **URL:** `/api/environments/name/{name}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View environments

### Update Environment
- **URL:** `/api/environments/{environment_id}`
- **Method:** `PUT`
- **Auth:** JWT required
- **Permissions:** Admin role
- **Request Body:**
```json
{
  "name": "Factory A-1",
  "description": "Updated production facility"
}
```

### Delete Environment
- **URL:** `/api/environments/{environment_id}`
- **Method:** `DELETE`
- **Auth:** JWT required
- **Permissions:** Admin role

### Get Users In Environment
- **URL:** `/api/environments/{environment_id}/users`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View users

### Get Forms In Environment
- **URL:** `/api/environments/{environment_id}/forms`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View forms

## Forms

### Get All Forms
- **URL:** `/api/forms`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View forms

### Get Batch Forms
- **URL:** `/api/forms/batch`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View forms
- **Query Parameters:**
  - `page`: Page number (default: 1)
  - `per_page`: Items per page (default: 50)
  - `include_deleted`: Include deleted forms (true/false)
  - `is_public`: Filter by public status (true/false)
  - `user_id`: Filter by creator user ID
  - `environment_id`: Filter by environment ID
  - `only_editable`: Return only forms that the user can edit (true/false)

### Get Form
- **URL:** `/api/forms/{form_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View forms

### Get Forms By Environment
- **URL:** `/api/forms/environment/{environment_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View forms

### Get Public Forms
- **URL:** `/api/forms/public`
- **Method:** `GET`
- **Auth:** JWT required

### Get Forms By Creator
- **URL:** `/api/forms/creator/{username}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View forms

### Create Form
- **URL:** `/api/forms`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Create forms
- **Request Body:**
```json
{
  "title": "Equipment Inspection",
  "description": "Monthly inspection checklist",
  "user_id": 5,
  "is_public": false
}
```

### Add Questions To Form
- **URL:** `/api/forms/{form_id}/questions`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Update forms
- **Request Body:**
```json
{
  "questions": [
    {
      "question_id": 1,
      "order_number": 1
    },
    {
      "question_id": 2,
      "order_number": 2
    }
  ]
}
```

### Get Form Submissions
- **URL:** `/api/forms/{form_id}/submissions`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View submissions

### Get Form Statistics
- **URL:** `/api/forms/{form_id}/statistics`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View forms

### Update Form
- **URL:** `/api/forms/{form_id}`
- **Method:** `PUT`
- **Auth:** JWT required
- **Permissions:** Update forms
- **Request Body:**
```json
{
  "title": "Equipment Inspection - Updated",
  "description": "Updated monthly inspection checklist",
  "is_public": true
}
```

### Delete Form
- **URL:** `/api/forms/{form_id}`
- **Method:** `DELETE`
- **Auth:** JWT required
- **Permissions:** Delete forms

## Form Questions

### Create Form Question
- **URL:** `/api/form-questions`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Create forms
- **Request Body:**
```json
{
  "form_id": 1,
  "question_id": 5,
  "order_number": 3
}
```

### Get All Form Questions
- **URL:** `/api/form-questions`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View forms

### Get Batch Form Questions
- **URL:** `/api/form-questions/batch`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View forms
- **Query Parameters:**
  - `page`: Page number (default: 1)
  - `per_page`: Items per page (default: 50)
  - `include_deleted`: Include deleted form questions (true/false)
  - `form_id`: Filter by form ID
  - `question_id`: Filter by question ID

### Get Form Questions
- **URL:** `/api/form-questions/form/{form_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View forms

### Get Form Question
- **URL:** `/api/form-questions/{form_question_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View forms

### Update Form Question
- **URL:** `/api/form-questions/{form_question_id}`
- **Method:** `PUT`
- **Auth:** JWT required
- **Permissions:** Update forms
- **Request Body:**
```json
{
  "question_id": 6,
  "order_number": 4
}
```

### Delete Form Question
- **URL:** `/api/form-questions/{form_question_id}`
- **Method:** `DELETE`
- **Auth:** JWT required
- **Permissions:** Delete forms

### Bulk Create Form Questions
- **URL:** `/api/form-questions/bulk`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Create forms
- **Request Body:**
```json
{
  "form_id": 1,
  "questions": [
    {
      "question_id": 1,
      "order_number": 1
    },
    {
      "question_id": 2,
      "order_number": 2
    },
    {
      "question_id": 3,
      "order_number": 3
    }
  ]
}
```

## Form Answers

### Create Form Answer
- **URL:** `/api/form-answers`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Create forms
- **Request Body:**
```json
{
  "form_question_id": 1,
  "answer_id": 5
}
```

### Bulk Create Form Answers
- **URL:** `/api/form-answers/bulk`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Create forms
- **Request Body:**
```json
{
  "form_answers": [
    {
      "form_question_id": 1,
      "answer_id": 5
    },
    {
      "form_question_id": 2,
      "answer_id": 8
    }
  ]
}
```

### Get All Form Answers
- **URL:** `/api/form-answers`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View forms

### Get Batch Form Answers
- **URL:** `/api/form-answers/batch`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View forms
- **Query Parameters:**
  - `page`: Page number (default: 1)
  - `per_page`: Items per page (default: 50)
  - `include_deleted`: Include deleted form answers (true/false)
  - `form_question_id`: Filter by form question ID
  - `answer_id`: Filter by answer ID

### Get Answers By Question
- **URL:** `/api/form-answers/question/{form_question_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View forms

### Get Form Answer
- **URL:** `/api/form-answers/{form_answer_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View forms

### Update Form Answer
- **URL:** `/api/form-answers/{form_answer_id}`
- **Method:** `PUT`
- **Auth:** JWT required
- **Permissions:** Update forms
- **Request Body:**
```json
{
  "answer_id": 6,
  "form_question_id": 2
}
```

### Delete Form Answer
- **URL:** `/api/form-answers/{form_answer_id}`
- **Method:** `DELETE`
- **Auth:** JWT required
- **Permissions:** Delete forms

## Form Submissions

### Create Submission
- **URL:** `/api/form-submissions`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Create submissions
- **Request Body:**
```json
{
  "form_id": 1,
  "answers": [
    {
      "question_id": 1,
      "answer_text": "Yes",
      "is_signature": false
    },
    {
      "question_id": 2,
      "answer_text": "Completed",
      "is_signature": false
    }
  ]
}
```

### Get All Submissions
- **URL:** `/api/form-submissions`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View submissions
- **Query Parameters:**
  - `form_id`: Filter by form ID
  - `start_date`: Filter by start date
  - `end_date`: Filter by end date

### Get Submissions Compact List
- **URL:** `/api/form-submissions/compact-list`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View submissions
- **Query Parameters:**
  - `form_id`: Filter by form ID
  - `start_date`: Filter by start date
  - `end_date`: Filter by end date

### Get Batch Form Submissions
- **URL:** `/api/form-submissions/batch`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View submissions
- **Query Parameters:**
  - `page`: Page number (default: 1)
  - `per_page`: Items per page (default: 50)
  - `include_deleted`: Include deleted submissions (true/false)
  - `form_id`: Filter by form ID
  - `submitted_by`: Filter by submitter username
  - `start_date`: Filter by start date
  - `end_date`: Filter by end date

### Get Submission
- **URL:** `/api/form-submissions/{submission_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View submissions

### Get My Submissions
- **URL:** `/api/form-submissions/my-submissions`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View own submissions
- **Query Parameters:**
  - `start_date`: Filter by start date
  - `end_date`: Filter by end date
  - `form_id`: Filter by form ID

### Update Submission
- **URL:** `/api/form-submissions/{submission_id}`
- **Method:** `PUT`
- **Auth:** JWT required
- **Permissions:** Update submissions
- **Request Body:**
```json
{
  "answers": [
    {
      "question_id": 1,
      "answer_text": "No",
      "is_signature": false
    },
    {
      "question_id": 2,
      "answer_text": "Pending",
      "is_signature": false
    }
  ]
}
```

### Delete Submission
- **URL:** `/api/form-submissions/{submission_id}`
- **Method:** `DELETE`
- **Auth:** JWT required
- **Permissions:** Delete submissions

### Get Submission Answers
- **URL:** `/api/form-submissions/{submission_id}/answers`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View submissions

## Questions & Answers

### Create Question
- **URL:** `/api/questions`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Create questions
- **Request Body:**
```json
{
  "text": "Is the equipment clean?",
  "question_type_id": 2,
  "remarks": "Check for oil residue"
}
```

### Bulk Create Questions
- **URL:** `/api/questions/bulk`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Create questions
- **Request Body:**
```json
{
  "questions": [
    {
      "text": "Is the equipment clean?",
      "question_type_id": 2,
      "remarks": "Check for oil residue"
    },
    {
      "text": "Are safety guards in place?",
      "question_type_id": 2,
      "remarks": "All guards must be secured"
    }
  ]
}
```

### Get All Questions
- **URL:** `/api/questions`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View questions

### Get Batch Questions
- **URL:** `/api/questions/batch`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View questions
- **Query Parameters:**
  - `page`: Page number (default: 1)
  - `per_page`: Items per page (default: 50)
  - `include_deleted`: Include deleted questions (true/false)
  - `question_type_id`: Filter by question type ID
  - `is_signature`: Filter signature questions (true/false)
  - `search_text`: Search by text

### Get Questions By Type
- **URL:** `/api/questions/by-type/{type_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View questions

### Get Question
- **URL:** `/api/questions/{question_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View questions

### Search Questions
- **URL:** `/api/questions/search`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View questions
- **Query Parameters:**
  - `text`: Search by question text
  - `remarks`: Search by remarks
  - `type_id`: Filter by question type ID

### Update Question
- **URL:** `/api/questions/{question_id}`
- **Method:** `PUT`
- **Auth:** JWT required
- **Permissions:** Update questions
- **Request Body:**
```json
{
  "text": "Is the equipment thoroughly cleaned?",
  "question_type_id": 2,
  "remarks": "Check for oil and grease residue"
}
```

### Delete Question
- **URL:** `/api/questions/{question_id}`
- **Method:** `DELETE`
- **Auth:** JWT required
- **Permissions:** Delete questions

### Create Question Type
- **URL:** `/api/question-types`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Create question types
- **Request Body:**
```json
{
  "type": "dropdown"
}
```

### Get All Question Types
- **URL:** `/api/question-types`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View question types

### Get Batch Question Types
- **URL:** `/api/question-types/batch`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View question types
- **Query Parameters:**
  - `page`: Page number (default: 1)
  - `per_page`: Items per page (default: 50)
  - `include_deleted`: Include deleted question types (true/false)

### Get Question Type
- **URL:** `/api/question-types/{type_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View question types

### Update Question Type
- **URL:** `/api/question-types/{type_id}`
- **Method:** `PUT`
- **Auth:** JWT required
- **Permissions:** Update question types
- **Request Body:**
```json
{
  "type": "dropdown_select"
}
```

### Delete Question Type
- **URL:** `/api/question-types/{type_id}`
- **Method:** `DELETE`
- **Auth:** JWT required
- **Permissions:** Delete question types

### Create Answer
- **URL:** `/api/answers`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Create answers
- **Request Body:**
```json
{
  "value": "Yes",
  "remarks": "Affirmative response"
}
```

### Bulk Create Answers
- **URL:** `/api/answers/bulk`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Create answers
- **Request Body:**
```json
{
  "answers": [
    {
      "value": "Yes",
      "remarks": "Affirmative response"
    },
    {
      "value": "No",
      "remarks": "Negative response"
    },
    {
      "value": "N/A",
      "remarks": "Not applicable"
    }
  ]
}
```

### Get All Answers
- **URL:** `/api/answers`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View answers

### Get Batch Answers
- **URL:** `/api/answers/batch`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View answers
- **Query Parameters:**
  - `page`: Page number (default: 1)
  - `per_page`: Items per page (default: 50)
  - `include_deleted`: Include deleted answers (true/false)

### Get Answer
- **URL:** `/api/answers/{answer_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View answers

### Get Answers By Form
- **URL:** `/api/answers/form/{form_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View answers

### Update Answer
- **URL:** `/api/answers/{answer_id}`
- **Method:** `PUT`
- **Auth:** JWT required
- **Permissions:** Update answers
- **Request Body:**
```json
{
  "value": "Yes - Confirmed",
  "remarks": "Verified positive response"
}
```

### Delete Answer
- **URL:** `/api/answers/{answer_id}`
- **Method:** `DELETE`
- **Auth:** JWT required
- **Permissions:** Delete answers

## Answers Submitted

### Create Answer Submitted
- **URL:** `/api/answers-submitted`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Create submissions
- **Request Body:**
```json
{
  "form_submission_id": 1,
  "question_text": "Is the equipment clean?",
  "question_type_text": "multiple_choice",
  "answer_text": "Yes"
}
```

### Bulk Create Answers Submitted
- **URL:** `/api/answers-submitted/bulk`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Create submissions
- **Request Body:**
```json
{
  "form_submission_id": 1,
  "submissions": [
    {
      "question_text": "Is the equipment clean?",
      "question_type_text": "multiple_choice",
      "answer_text": "Yes"
    },
    {
      "question_text": "Are safety guards in place?",
      "question_type_text": "multiple_choice",
      "answer_text": "No"
    }
  ]
}
```

### Get All Answers Submitted
- **URL:** `/api/answers-submitted`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View submissions
- **Query Parameters:**
  - `form_submission_id`: Filter by form submission ID
  - `start_date`: Filter by start date
  - `end_date`: Filter by end date

### Get Batch Answers Submitted
- **URL:** `/api/answers-submitted/batch`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View submissions
- **Query Parameters:**
  - `page`: Page number (default: 1)
  - `per_page`: Items per page (default: 50)
  - `include_deleted`: Include deleted submissions (true/false)
  - `form_submission_id`: Filter by form submission ID
  - `question_type`: Filter by question type

### Get Answer Submitted
- **URL:** `/api/answers-submitted/{answer_submitted_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View submissions

### Get Answers By Submission
- **URL:** `/api/answers-submitted/submission/{submission_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View submissions

### Update Answer Submitted
- **URL:** `/api/answers-submitted/{answer_submitted_id}`
- **Method:** `PUT`
- **Auth:** JWT required
- **Permissions:** Update submissions
- **Request Body:**
```json
{
  "answer_text": "Updated answer"
}
```

### Delete Answer Submitted
- **URL:** `/api/answers-submitted/{answer_submitted_id}`
- **Method:** `DELETE`
- **Auth:** JWT required
- **Permissions:** Delete submissions

## Attachments

### Create Attachment
- **URL:** `/api/attachments`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Create attachments
- **Request Body (multipart/form-data):**
  - `form_submission_id`: ID of the form submission
  - `file`: File to upload
  - `is_signature` (optional): Whether this is a signature (true/false)
  - `answer_submitted_id` (optional): ID of the answer submitted (for signatures)
  - `signature_position` (optional): Position of signature
  - `signature_author` (optional): Author of signature

### Bulk Create Attachments
- **URL:** `/api/attachments/bulk`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Create attachments
- **Request Body (multipart/form-data):**
  - `form_submission_id`: ID of the form submission
  - `file1`, `file2`, etc.: Files to upload
  - `is_signature1`, `is_signature2`, etc. (optional): Whether each file is a signature
  - `answer_submitted_id1`, `answer_submitted_id2`, etc. (optional): IDs of the answers submitted
  - `signature_position1`, `signature_position2`, etc. (optional): Positions of signatures
  - `signature_author1`, `signature_author2`, etc. (optional): Authors of signatures

### Get All Attachments
- **URL:** `/api/attachments`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View attachments
- **Query Parameters:**
  - `form_submission_id`: Filter by form submission ID
  - `is_signature`: Filter by signature status (true/false)
  - `file_type`: Filter by file type
  - `signature_author`: Filter by signature author
  - `signature_position`: Filter by signature position

### Get Batch Attachments
- **URL:** `/api/attachments/batch`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View attachments
- **Query Parameters:**
  - `page`: Page number (default: 1)
  - `per_page`: Items per page (default: 50)
  - `include_deleted`: Include deleted attachments (true/false)
  - `form_submission_id`: Filter by form submission ID
  - `is_signature`: Filter by signature status (true/false)
  - `file_type`: Filter by file type

### Get Attachment
- **URL:** `/api/attachments/{attachment_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View attachments

### Get Submission Attachments
- **URL:** `/api/attachments/submission/{submission_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View attachments

### Update Attachment
- **URL:** `/api/attachments/{attachment_id}`
- **Method:** `PUT`
- **Auth:** JWT required
- **Permissions:** Update attachments
- **Request Body:**
```json
{
  "signature_position": "Bottom right",
  "signature_author": "John Doe",
  "is_signature": true
}
```

### Delete Attachment
- **URL:** `/api/attachments/{attachment_id}`
- **Method:** `DELETE`
- **Auth:** JWT required
- **Permissions:** Delete attachments

## Export

### Export Form Data
- **URL:** `/api/export/form/{form_id}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View forms
- **Query Parameters:**
  - `format`: Export format (PDF, DOCX)
  - `page_size`: Page size (A4, LETTER, LEGAL)
  - `margin_top`, `margin_bottom`, `margin_left`, `margin_right`: Margins in inches
  - `line_spacing`: Line spacing multiplier
  - `font_size`: Font size in points
  - `logo_path`: Path to logo image
  - Various signature parameters

### Get Supported Formats
- **URL:** `/api/export/formats`
- **Method:** `GET`
- **Auth:** JWT required

### Get Format Parameters
- **URL:** `/api/export/parameters`
- **Method:** `GET`
- **Auth:** JWT required

### Preview Export Parameters
- **URL:** `/api/export/form/{form_id}/preview-params`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View forms

### Export Submission to PDF
- **URL:** `/api/export_submissions/{submission_id}/pdf`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View submissions

### Export Submission to PDF with Logo
- **URL:** `/api/export_submissions/{submission_id}/pdf/logo`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** View submissions
- **Request Body (multipart/form-data):**
  - `header_image`: Image file for header
  - `header_opacity`: Opacity value (0-100)
  - `header_size`: Size percentage (1-500)
  - `header_width`: Width in pixels
  - `header_height`: Height in pixels
  - `header_alignment`: Alignment (left, center, right)
  - `signatures_size`: Size percentage for signatures
  - `signatures_alignment`: Layout for signatures (vertical, horizontal)

## CMMS Configuration

### Create Config
- **URL:** `/api/cmms-configs`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Admin role
- **Request Body:**
```json
{
  "filename": "machine_config.json",
  "content": {
    "machine_id": "M001",
    "maintenance_interval": 30,
    "critical_parts": ["belt", "motor", "filter"]
  }
}
```

### Upload Config
- **URL:** `/api/cmms-configs/upload`
- **Method:** `POST`
- **Auth:** JWT required
- **Permissions:** Admin role
- **Request Body (multipart/form-data):**
  - `file`: Configuration file to upload

### List Files
- **URL:** `/api/cmms-configs/files`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View forms

### Get File
- **URL:** `/api/cmms-configs/file/{filename}`
- **Method:** `GET`
- **Auth:** JWT required
- **Permissions:** View forms

### Update Config File
- **URL:** `/api/cmms-configs/configs/{filename}`
- **Method:** `PUT`
- **Auth:** JWT required
- **Permissions:** Admin role
- **Request Body:**
```json
{
  "content": {
    "machine_id": "M001",
    "maintenance_interval": 60,
    "critical_parts": ["belt", "motor", "filter", "coolant"]
  }
}
```

### Rename Config
- **URL:** `/api/cmms-configs/{filename}/rename`
- **Method:** `PUT`
- **Auth:** JWT required
- **Permissions:** Admin role
- **Request Body:**
```json
{
  "new_filename": "updated_machine_config.json"
}
```

### Load Config
- **URL:** `/api/cmms-configs/{filename}`
- **Method:** `GET`
- **Auth:** JWT required

### Delete Config
- **URL:** `/api/cmms-configs/{filename}`
- **Method:** `DELETE`
- **Auth:** JWT required
- **Permissions:** Admin role

### Check Config File
- **URL:** `/api/cmms-configs/check`
- **Method:** `GET`
- **Auth:** JWT required

## Health & Status

### API Ping
- **URL:** `/api/ping`
- **Method:** `GET`
- **Auth:** None

### Health Ping
- **URL:** `/api/health/ping`
- **Method:** `GET`
- **Auth:** None

### Health Status
- **URL:** `/api/health/status`
- **Method:** `GET`
- **Auth:** None
