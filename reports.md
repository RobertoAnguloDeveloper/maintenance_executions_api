# Report Generation API Documentation

## Overview

The Report Generation API allows users to generate custom reports in various formats (XLSX, CSV, PDF, DOCX, PPTX) for different entities in the system. This documentation provides all possible request bodies organized by individual entities and entity combinations.

## Base Endpoint

```
POST /reports/generate
```

## Authentication

All endpoints require JWT authentication. Include a valid JWT token in the Authorization header:

```
Authorization: Bearer <your_token>
```

## Common Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| report_type | string or array | Yes | Entity or entities to include in the report |
| output_format | string | No | Output format: "xlsx", "csv", "pdf", "docx", "pptx" (default: "xlsx") |
| columns | array | No | Specific columns to include (defaults to predefined columns) |
| filters | array | No | Filters to apply to the data |
| sort_by | array | No | Sorting options for the data |
| filename | string | No | Custom filename (without extension) |
| report_title | string | No | Custom report title |
| template_id | integer | No | ID of a saved report template to use |
| include_data_table_in_ppt | boolean | No | Include data table in PPTX (default: false) |
| charts | array | No | Custom chart configurations |

## 1. USERS

### Available Columns
id, username, first_name, last_name, email, contact_number, role_id, environment_id, role.name, role.description, role.is_super_user, environment.name, environment.description, created_at, updated_at, is_deleted, deleted_at

### Default Columns
id, username, first_name, last_name, email, contact_number, role.name, environment.name, created_at

### Request Bodies

#### Basic Excel Report
```json
{
 "report_type": "users",
 "output_format": "xlsx"
}
```

#### CSV Report
```json
{
 "report_type": "users",
 "output_format": "csv"
}
```

#### PDF Report
```json
{
 "report_type": "users",
 "output_format": "pdf"
}
```

#### DOCX Report
```json
{
 "report_type": "users",
 "output_format": "docx"
}
```

#### PPTX Report
```json
{
 "report_type": "users",
 "output_format": "pptx",
 "include_data_table_in_ppt": true
}
```

#### Filtered Report
```json
{
 "report_type": "users",
 "filters": [
   {"field": "environment.name", "operator": "eq", "value": "Production"},
   {"field": "role.name", "operator": "neq", "value": "admin"}
 ],
 "sort_by": [
   {"field": "username", "direction": "asc"}
 ]
}
```

#### Custom Columns Report
```json
{
 "report_type": "users",
 "columns": [
   "id", "username", "email", "role.name", "environment.name"
 ]
}
```

#### Users with Charts
```json
{
 "report_type": "users",
 "output_format": "pdf",
 "report_title": "User Distribution Analysis",
 "charts": [
   {
     "type": "bar",
     "column": "role.name",
     "title": "Users by Role"
   },
   {
     "type": "pie",
     "column": "environment.name",
     "title": "Users by Environment"
   },
   {
     "type": "line",
     "column": "created_at",
     "title": "User Creation Timeline"
   }
 ]
}
```

#### Users with Custom Filename
```json
{
 "report_type": "users",
 "filename": "active_users_export",
 "report_title": "Active Users Report"
}
```

## 2. ROLES

### Available Columns
id, name, description, is_super_user, created_at, updated_at, is_deleted, deleted_at

### Default Columns
id, name, description, is_super_user, created_at

### Request Bodies

#### Basic Excel Report
```json
{
 "report_type": "roles",
 "output_format": "xlsx"
}
```

#### CSV Report
```json
{
 "report_type": "roles",
 "output_format": "csv"
}
```

#### PDF Report
```json
{
 "report_type": "roles",
 "output_format": "pdf"
}
```

#### DOCX Report
```json
{
 "report_type": "roles",
 "output_format": "docx"
}
```

#### PPTX Report
```json
{
 "report_type": "roles",
 "output_format": "pptx",
 "include_data_table_in_ppt": true
}
```

#### Filtered Report
```json
{
 "report_type": "roles",
 "filters": [
   {"field": "is_super_user", "operator": "eq", "value": false}
 ],
 "sort_by": [
   {"field": "name", "direction": "asc"}
 ]
}
```

#### Roles with Charts
```json
{
 "report_type": "roles",
 "output_format": "pdf",
 "report_title": "Roles Analysis",
 "charts": [
   {
     "type": "pie",
     "column": "is_super_user",
     "title": "Roles by Superuser Status"
   },
   {
     "type": "bar",
     "column": "name",
     "title": "Role Distribution"
   }
 ]
}
```

## 3. PERMISSIONS

### Available Columns
id, name, action, entity, description, created_at, updated_at, is_deleted, deleted_at

### Default Columns
id, name, action, entity, description

### Request Bodies

#### Basic Excel Report
```json
{
 "report_type": "permissions",
 "output_format": "xlsx"
}
```

#### CSV Report
```json
{
 "report_type": "permissions",
 "output_format": "csv"
}
```

#### PDF Report
```json
{
 "report_type": "permissions",
 "output_format": "pdf"
}
```

#### DOCX Report
```json
{
 "report_type": "permissions",
 "output_format": "docx"
}
```

#### PPTX Report
```json
{
 "report_type": "permissions",
 "output_format": "pptx",
 "include_data_table_in_ppt": true
}
```

#### Filtered Report
```json
{
 "report_type": "permissions",
 "filters": [
   {"field": "action", "operator": "eq", "value": "create"}
 ],
 "sort_by": [
   {"field": "entity", "direction": "asc"}
 ]
}
```

#### Permissions with Charts
```json
{
 "report_type": "permissions",
 "output_format": "pdf",
 "charts": [
   {
     "type": "pie",
     "column": "action",
     "title": "Permissions by Action Type"
   },
   {
     "type": "bar",
     "column": "entity",
     "title": "Permissions by Entity"
   }
 ]
}
```

## 4. ROLE_PERMISSIONS

### Available Columns
id, role_id, permission_id, role.name, role.description, role.is_super_user, permission.name, permission.action, permission.entity, permission.description, created_at, updated_at, is_deleted, deleted_at

### Default Columns
id, role_id, permission_id, role.name, permission.name, permission.action, permission.entity

### Request Bodies

#### Basic Excel Report
```json
{
 "report_type": "role_permissions",
 "output_format": "xlsx"
}
```

#### CSV Report
```json
{
 "report_type": "role_permissions",
 "output_format": "csv"
}
```

#### PDF Report
```json
{
 "report_type": "role_permissions",
 "output_format": "pdf"
}
```

#### DOCX Report
```json
{
 "report_type": "role_permissions",
 "output_format": "docx"
}
```

#### PPTX Report
```json
{
 "report_type": "role_permissions",
 "output_format": "pptx",
 "include_data_table_in_ppt": true
}
```

#### Filtered Report
```json
{
 "report_type": "role_permissions",
 "filters": [
   {"field": "role.name", "operator": "eq", "value": "site_manager"}
 ],
 "sort_by": [
   {"field": "permission.action", "direction": "asc"}
 ]
}
```

#### Role Permissions with Charts
```json
{
 "report_type": "role_permissions",
 "output_format": "pdf",
 "charts": [
   {
     "type": "bar",
     "column": "role.name",
     "title": "Permissions Count by Role"
   },
   {
     "type": "pie",
     "column": "permission.action",
     "title": "Permission Actions Distribution"
   }
 ]
}
```

## 5. ENVIRONMENTS

### Available Columns
id, name, description, created_at, updated_at, is_deleted, deleted_at

### Default Columns
id, name, description, created_at

### Request Bodies

#### Basic Excel Report
```json
{
 "report_type": "environments",
 "output_format": "xlsx"
}
```

#### CSV Report
```json
{
 "report_type": "environments",
 "output_format": "csv"
}
```

#### PDF Report
```json
{
 "report_type": "environments",
 "output_format": "pdf"
}
```

#### DOCX Report
```json
{
 "report_type": "environments",
 "output_format": "docx"
}
```

#### PPTX Report
```json
{
 "report_type": "environments",
 "output_format": "pptx",
 "include_data_table_in_ppt": true
}
```

#### Sorted Report
```json
{
 "report_type": "environments",
 "sort_by": [
   {"field": "created_at", "direction": "desc"}
 ]
}
```

#### Environments with Charts
```json
{
 "report_type": "environments",
 "output_format": "pdf",
 "charts": [
   {
     "type": "bar",
     "column": "name",
     "title": "Environment Overview"
   }
 ]
}
```

## 6. QUESTION_TYPES

### Available Columns
id, type, created_at, updated_at, is_deleted, deleted_at

### Default Columns
id, type, created_at

### Request Bodies

#### Basic Excel Report
```json
{
 "report_type": "question_types",
 "output_format": "xlsx"
}
```

#### CSV Report
```json
{
 "report_type": "question_types",
 "output_format": "csv"
}
```

#### PDF Report
```json
{
 "report_type": "question_types",
 "output_format": "pdf"
}
```

#### DOCX Report
```json
{
 "report_type": "question_types",
 "output_format": "docx"
}
```

#### PPTX Report
```json
{
 "report_type": "question_types",
 "output_format": "pptx",
 "include_data_table_in_ppt": true
}
```

#### Question Types with Charts
```json
{
 "report_type": "question_types",
 "output_format": "pdf",
 "charts": [
   {
     "type": "pie",
     "column": "type",
     "title": "Question Type Distribution"
   }
 ]
}
```

## 7. QUESTIONS

### Available Columns
id, text, question_type_id, is_signature, remarks, question_type.type, created_at, updated_at, is_deleted, deleted_at

### Default Columns
id, text, question_type.type, is_signature, remarks, created_at

### Request Bodies

#### Basic Excel Report
```json
{
 "report_type": "questions",
 "output_format": "xlsx"
}
```

#### CSV Report
```json
{
 "report_type": "questions",
 "output_format": "csv"
}
```

#### PDF Report
```json
{
 "report_type": "questions",
 "output_format": "pdf"
}
```

#### DOCX Report
```json
{
 "report_type": "questions",
 "output_format": "docx"
}
```

#### PPTX Report
```json
{
 "report_type": "questions",
 "output_format": "pptx",
 "include_data_table_in_ppt": true
}
```

#### Filtered Report
```json
{
 "report_type": "questions",
 "filters": [
   {"field": "question_type.type", "operator": "eq", "value": "text"},
   {"field": "is_signature", "operator": "eq", "value": false}
 ],
 "sort_by": [
   {"field": "text", "direction": "asc"}
 ]
}
```

#### Questions with Charts
```json
{
 "report_type": "questions",
 "output_format": "pdf",
 "charts": [
   {
     "type": "pie",
     "column": "question_type.type",
     "title": "Questions by Type"
   },
   {
     "type": "bar",
     "column": "is_signature",
     "title": "Signature vs Non-Signature Questions"
   }
 ]
}
```

## 8. ANSWERS

### Available Columns
id, value, remarks, created_at, updated_at, is_deleted, deleted_at

### Default Columns
id, value, remarks, created_at

### Request Bodies

#### Basic Excel Report
```json
{
 "report_type": "answers",
 "output_format": "xlsx"
}
```

#### CSV Report
```json
{
 "report_type": "answers",
 "output_format": "csv"
}
```

#### PDF Report
```json
{
 "report_type": "answers",
 "output_format": "pdf"
}
```

#### DOCX Report
```json
{
 "report_type": "answers",
 "output_format": "docx"
}
```

#### PPTX Report
```json
{
 "report_type": "answers",
 "output_format": "pptx",
 "include_data_table_in_ppt": true
}
```

#### Sorted Report
```json
{
 "report_type": "answers",
 "sort_by": [
   {"field": "value", "direction": "asc"}
 ]
}
```

#### Answers with Charts
```json
{
 "report_type": "answers",
 "output_format": "pdf",
 "charts": [
   {
     "type": "bar",
     "column": "created_at",
     "title": "Answers Creation Timeline"
   }
 ]
}
```

## 9. FORMS

### Available Columns
id, title, description, user_id, is_public, creator.username, creator.email, creator.first_name, creator.last_name, creator.environment.name, creator.environment.description, created_at, updated_at, is_deleted, deleted_at

### Default Columns
id, title, description, creator.username, creator.environment.name, is_public, created_at

### Request Bodies

#### Basic Excel Report
```json
{
 "report_type": "forms",
 "output_format": "xlsx"
}
```

#### CSV Report
```json
{
 "report_type": "forms",
 "output_format": "csv"
}
```

#### PDF Report
```json
{
 "report_type": "forms",
 "output_format": "pdf"
}
```

#### DOCX Report
```json
{
 "report_type": "forms",
 "output_format": "docx"
}
```

#### PPTX Report
```json
{
 "report_type": "forms",
 "output_format": "pptx",
 "include_data_table_in_ppt": true
}
```

#### Filtered Report
```json
{
 "report_type": "forms",
 "filters": [
   {"field": "is_public", "operator": "eq", "value": true}
 ],
 "sort_by": [
   {"field": "created_at", "direction": "desc"}
 ]
}
```

#### Forms with Charts
```json
{
 "report_type": "forms",
 "output_format": "pdf",
 "charts": [
   {
     "type": "pie",
     "column": "is_public",
     "title": "Public vs Private Forms"
   },
   {
     "type": "bar",
     "column": "creator.username",
     "title": "Forms per Creator"
   },
   {
     "type": "line",
     "column": "created_at",
     "title": "Form Creation Timeline"
   }
 ]
}
```

## 10. FORM_QUESTIONS

### Available Columns
id, form_id, question_id, order_number, form.title, form.description, form.is_public, question.text, question.is_signature, question.question_type.type, created_at, updated_at, is_deleted, deleted_at

### Default Columns
id, form_id, question_id, order_number, form.title, question.text, question.question_type.type

### Request Bodies

#### Basic Excel Report
```json
{
 "report_type": "form_questions",
 "output_format": "xlsx"
}
```

#### CSV Report
```json
{
 "report_type": "form_questions",
 "output_format": "csv"
}
```

#### PDF Report
```json
{
 "report_type": "form_questions",
 "output_format": "pdf"
}
```

#### DOCX Report
```json
{
 "report_type": "form_questions",
 "output_format": "docx"
}
```

#### PPTX Report
```json
{
 "report_type": "form_questions",
 "output_format": "pptx",
 "include_data_table_in_ppt": true
}
```

#### Filtered Report
```json
{
 "report_type": "form_questions",
 "filters": [
   {"field": "form.title", "operator": "like", "value": "Inspection"}
 ],
 "sort_by": [
   {"field": "form_id", "direction": "asc"},
   {"field": "order_number", "direction": "asc"}
 ]
}
```

#### Form Questions with Charts
```json
{
 "report_type": "form_questions",
 "output_format": "pdf",
 "charts": [
   {
     "type": "bar",
     "column": "form.title",
     "title": "Questions by Form"
   },
   {
     "type": "pie",
     "column": "question.question_type.type",
     "title": "Question Types Distribution"
   }
 ]
}
```

## 11. FORM_ANSWERS

### Available Columns
id, form_question_id, answer_id, remarks, form_question.form.title, form_question.form.description, form_question.question.text, form_question.question.question_type.type, form_question.order_number, answer.value, answer.remarks, created_at, updated_at, is_deleted, deleted_at

### Default Columns
id, form_question_id, answer_id, form_question.question.text, answer.value, remarks

### Request Bodies

#### Basic Excel Report
```json
{
 "report_type": "form_answers",
 "output_format": "xlsx"
}
```

#### CSV Report
```json
{
 "report_type": "form_answers",
 "output_format": "csv"
}
```

#### PDF Report
```json
{
 "report_type": "form_answers",
 "output_format": "pdf"
}
```

#### DOCX Report
```json
{
 "report_type": "form_answers",
 "output_format": "docx"
}
```

#### PPTX Report
```json
{
 "report_type": "form_answers",
 "output_format": "pptx",
 "include_data_table_in_ppt": true
}
```

#### Filtered Report
```json
{
 "report_type": "form_answers",
 "filters": [
   {"field": "form_question.form.title", "operator": "eq", "value": "Safety Checklist"}
 ],
 "sort_by": [
   {"field": "form_question_id", "direction": "asc"}
 ]
}
```

#### Form Answers with Charts
```json
{
 "report_type": "form_answers",
 "output_format": "pdf",
 "charts": [
   {
     "type": "bar",
     "column": "form_question.form.title",
     "title": "Answers by Form"
   },
   {
     "type": "pie",
     "column": "form_question.question.question_type.type",
     "title": "Answers by Question Type"
   }
 ]
}
```

## 12. FORM_SUBMISSIONS

### Available Columns
id, form_id, submitted_by, submitted_at, form.title, form.description, form.is_public, form.creator.username, form.creator.email, form.creator.environment.name, created_at, updated_at, is_deleted, deleted_at
plus dynamic columns for form answers in the format: answers.<question_text>

### Default Columns
id, form_id, form.title, submitted_by, submitted_at, created_at

### Request Bodies

#### Basic Excel Report
```json
{
 "report_type": "form_submissions",
 "output_format": "xlsx"
}
```

#### CSV Report
```json
{
 "report_type": "form_submissions",
 "output_format": "csv"
}
```

#### PDF Report
```json
{
 "report_type": "form_submissions",
 "output_format": "pdf"
}
```

#### DOCX Report
```json
{
 "report_type": "form_submissions",
 "output_format": "docx"
}
```

#### PPTX Report
```json
{
 "report_type": "form_submissions",
 "output_format": "pptx",
 "include_data_table_in_ppt": true
}
```

#### Filtered Report with Dynamic Columns
```json
{
 "report_type": "form_submissions",
 "columns": [
   "id", "form.title", "submitted_by", "submitted_at",
   "answers.What is your name?",
   "answers.What department do you work in?",
   "answers.Inspection date"
 ],
 "filters": [
   {"field": "form.title", "operator": "eq", "value": "Quality Inspection"},
   {"field": "submitted_at", "operator": "between", "value": ["2023-01-01", "2023-12-31"]}
 ],
 "sort_by": [
   {"field": "submitted_at", "direction": "desc"}
 ]
}
```

#### Form Submissions with Charts
```json
{
 "report_type": "form_submissions",
 "output_format": "pdf",
 "charts": [
   {
     "type": "bar",
     "column": "submitted_by",
     "title": "Submissions by User"
   },
   {
     "type": "pie",
     "column": "form.title",
     "title": "Submissions by Form"
   },
   {
     "type": "line",
     "column": "submitted_at",
     "title": "Submission Timeline"
   },
   {
     "type": "bar",
     "column": "answers.What department do you work in?",
     "title": "Submissions by Department"
   }
 ]
}
```

## 13. ANSWERS_SUBMITTED

### Available Columns
id, question, question_type, answer, form_submission_id, column, row, cell_content, form_submission.submitted_by, form_submission.submitted_at, form_submission.form.title, form_submission.form.description, created_at, updated_at, is_deleted, deleted_at

### Default Columns
id, form_submission_id, form_submission.form.title, question, question_type, answer, created_at

### Request Bodies

#### Basic Excel Report
```json
{
 "report_type": "answers_submitted",
 "output_format": "xlsx"
}
```

#### CSV Report
```json
{
 "report_type": "answers_submitted",
 "output_format": "csv"
}
```

#### PDF Report
```json
{
 "report_type": "answers_submitted",
 "output_format": "pdf"
}
```

#### DOCX Report
```json
{
 "report_type": "answers_submitted",
 "output_format": "docx"
}
```

#### PPTX Report
```json
{
 "report_type": "answers_submitted",
 "output_format": "pptx",
 "include_data_table_in_ppt": true
}
```

#### Filtered Report
```json
{
 "report_type": "answers_submitted",
 "filters": [
   {"field": "question_type", "operator": "eq", "value": "dropdown"},
   {"field": "form_submission.submitted_at", "operator": "between", "value": ["2023-06-01", "2023-06-30"]}
 ],
 "sort_by": [
   {"field": "form_submission.submitted_at", "direction": "desc"}
 ]
}
```

#### Answers Submitted with Charts
```json
{
 "report_type": "answers_submitted",
 "output_format": "pdf",
 "charts": [
   {
     "type": "pie",
     "column": "question_type",
     "title": "Answers by Question Type"
   },
   {
     "type": "bar",
     "column": "question",
     "title": "Answers by Question"
   },
   {
     "type": "bar",
     "column": "form_submission.form.title",
     "title": "Answers by Form"
   }
 ]
}
```

## 14. ATTACHMENTS

### Available Columns
id, form_submission_id, file_type, file_path, is_signature, signature_position, signature_author, form_submission.submitted_by, form_submission.submitted_at, form_submission.form.title, form_submission.form.description, created_at, updated_at, is_deleted, deleted_at

### Default Columns
id, form_submission_id, form_submission.form.title, file_path, file_type, is_signature, signature_author, created_at

### Request Bodies

#### Basic Excel Report
```json
{
 "report_type": "attachments",
 "output_format": "xlsx"
}
```

#### CSV Report
```json
{
 "report_type": "attachments",
 "output_format": "csv"
}
```

#### PDF Report
```json
{
 "report_type": "attachments",
 "output_format": "pdf"
}
```

#### DOCX Report
```json
{
 "report_type": "attachments",
 "output_format": "docx"
}
```

#### PPTX Report
```json
{
 "report_type": "attachments",
 "output_format": "pptx",
 "include_data_table_in_ppt": true
}
```

#### Filtered Report
```json
{
 "report_type": "attachments",
 "filters": [
   {"field": "is_signature", "operator": "eq", "value": true}
 ],
 "sort_by": [
   {"field": "created_at", "direction": "desc"}
 ]
}
```

#### Attachments with Charts
```json
{
 "report_type": "attachments",
 "output_format": "pdf",
 "charts": [
   {
     "type": "pie",
     "column": "file_type",
     "title": "Attachments by File Type"
   },
   {
     "type": "pie",
     "column": "is_signature",
     "title": "Signature vs Non-Signature Attachments"
   },
   {
     "type": "bar",
     "column": "signature_author",
     "title": "Signatures by Author"
   },
   {
     "type": "bar",
     "column": "form_submission.form.title",
     "title": "Attachments by Form"
   }
 ]
}
```

## 15. TOKEN_BLOCKLIST

### Available Columns
id, jti, created_at

### Default Columns
id, jti, created_at

### Request Bodies

#### Basic Excel Report
```json
{
 "report_type": "token_blocklist",
 "output_format": "xlsx"
}
```

#### CSV Report
```json
{
 "report_type": "token_blocklist",
 "output_format": "csv"
}
```

#### PDF Report
```json
{
 "report_type": "token_blocklist",
 "output_format": "pdf"
}
```

#### DOCX Report
```json
{
 "report_type": "token_blocklist",
 "output_format": "docx"
}
```

#### PPTX Report
```json
{
 "report_type": "token_blocklist",
 "output_format": "pptx",
 "include_data_table_in_ppt": true
}
```

#### Sorted Report
```json
{
 "report_type": "token_blocklist",
 "sort_by": [
   {"field": "created_at", "direction": "desc"}
 ]
}
```

#### Token Blocklist with Charts
```json
{
 "report_type": "token_blocklist",
 "output_format": "pdf",
 "charts": [
   {
     "type": "line",
     "column": "created_at",
     "title": "Token Blocklist Timeline"
   }
 ]
}
```

# MULTI-ENTITY REPORTS

## 1. All Entities Report

### PDF Format

```json
{
 "report_type": "all",
 "output_format": "pdf",
 "report_title": "Complete System Data Export"
}
```

### CSV Format

```json
{
 "report_type": "all",
 "output_format": "csv",
 "report_title": "Complete System Data Export"
}
```

### DOCX Format

```json
{
 "report_type": "all",
 "output_format": "docx",
 "report_title": "Complete System Data Export"
}
```

## 2. Users and Roles Report

### Excel Format

```json
{
 "report_type": ["users", "roles"],
 "output_format": "xlsx",
 "report_title": "Users and Roles Analysis"
}
```

### PDF Format

```json
{
 "report_type": ["users", "roles"],
 "output_format": "pdf",
 "report_title": "Users and Roles Analysis"
}
```

### CSV Format

```json
{
 "report_type": ["users", "roles"],
 "output_format": "csv",
 "report_title": "Users and Roles Analysis"
}
```

### DOCX Format

```json
{
 "report_type": ["users", "roles"],
 "output_format": "docx",
 "report_title": "Users and Roles Analysis"
}
```

### With Filters and Charts

```json
{
 "report_type": ["users", "roles"],
 "output_format": "pdf",
 "report_title": "Users and Roles Analysis",
 "filters": [
   {"field": "users.environment.name", "operator": "eq", "value": "Production"}
 ],
 "charts": [
   {
     "type": "pie",
     "column": "users.role.name",
     "title": "Users by Role"
   },
   {
     "type": "pie",
     "column": "roles.is_super_user",
     "title": "Roles by Superuser Status"
   }
 ]
}
```

## 3. Form Submissions with Attachments Report

### Excel Format

```json
{
 "report_type": ["form_submissions", "attachments"],
 "output_format": "xlsx",
 "report_title": "Form Submissions with Attachments"
}
```

### PDF Format

```json
{
 "report_type": ["form_submissions", "attachments"],
 "output_format": "pdf",
 "report_title": "Form Submissions with Attachments"
}
```

### CSV Format

```json
{
 "report_type": ["form_submissions", "attachments"],
 "output_format": "csv",
 "report_title": "Form Submissions with Attachments"
}
```

### DOCX Format

```json
{
 "report_type": ["form_submissions", "attachments"],
 "output_format": "docx",
 "report_title": "Form Submissions with Attachments"
}
```

### With Filters and Charts

```json
{
 "report_type": ["form_submissions", "attachments"],
 "output_format": "pdf",
 "report_title": "Equipment Inspection Submissions with Attachments",
 "filters": [
   {"field": "form_submissions.form.title", "operator": "eq", "value": "Equipment Inspection"}
 ],
 "charts": [
   {
     "type": "bar",
     "column": "form_submissions.submitted_by",
     "title": "Submissions by User"
   },
   {
     "type": "pie",
     "column": "attachments.file_type",
     "title": "Attachments by File Type"
   },
   {
     "type": "line",
     "column": "form_submissions.submitted_at",
     "title": "Submission Timeline"
   }
 ]
}
```

## 4. Forms, Questions, and Submissions Report

### Excel Format

```json
{
 "report_type": ["forms", "form_questions", "form_submissions"],
 "output_format": "xlsx",
 "report_title": "Complete Form Analysis"
}
```

### PDF Format

```json
{
 "report_type": ["forms", "form_questions", "form_submissions"],
 "output_format": "pdf",
 "report_title": "Complete Form Analysis"
}
```

### CSV Format

```json
{
 "report_type": ["forms", "form_questions", "form_submissions"],
 "output_format": "csv",
 "report_title": "Complete Form Analysis"
}
```

### DOCX Format

```json
{
 "report_type": ["forms", "form_questions", "form_submissions"],
 "output_format": "docx",
 "report_title": "Complete Form Analysis"
}
```

### With Filters and Charts

```json
{
 "report_type": ["forms", "form_questions", "form_submissions"],
 "output_format": "pdf",
 "report_title": "Public Forms Analysis",
 "filters": [
   {"field": "forms.is_public", "operator": "eq", "value": true}
 ],
 "charts": [
   {
     "type": "bar",
     "column": "forms.creator.username",
     "title": "Forms per Creator"
   },
   {
     "type": "pie",
     "column": "form_questions.question.question_type.type",
     "title": "Question Type Distribution"
   },
   {
     "type": "line",
     "column": "form_submissions.submitted_at",
     "title": "Submission Timeline"
   }
 ]
}
```

## 5. Roles and Permissions Analysis

### Excel Format

```json
{
 "report_type": ["roles", "permissions", "role_permissions"],
 "output_format": "xlsx",
 "report_title": "Roles and Permissions Analysis"
}
```

### PDF Format

```json
{
 "report_type": ["roles", "permissions", "role_permissions"],
 "output_format": "pdf",
 "report_title": "Roles and Permissions Analysis"
}
```

### CSV Format

```json
{
 "report_type": ["roles", "permissions", "role_permissions"],
 "output_format": "csv",
 "report_title": "Roles and Permissions Analysis"
}
```

### DOCX Format

```json
{
 "report_type": ["roles", "permissions", "role_permissions"],
 "output_format": "docx",
 "report_title": "Roles and Permissions Analysis"
}
```

### With Charts

```json
{
 "report_type": ["roles", "permissions", "role_permissions"],
 "output_format": "pdf",
 "report_title": "Roles and Permissions Analysis",
 "charts": [
   {
     "type": "pie",
     "column": "roles.is_super_user",
     "title": "Regular vs. Superuser Roles"
   },
   {
     "type": "bar",
     "column": "permissions.action",
     "title": "Permissions by Action Type"
   },
   {
     "type": "bar",
     "column": "role_permissions.role.name",
     "title": "Permission Count by Role"
   }
 ]
}
```

## 6. User Activity Report

### Excel Format

```json
{
 "report_type": ["users", "form_submissions", "attachments"],
 "output_format": "xlsx",
 "report_title": "User Activity Report"
}
```

### PDF Format

```json
{
 "report_type": ["users", "form_submissions", "attachments"],
 "output_format": "pdf",
 "report_title": "User Activity Report"
}
```

### PPTX Format

```json
{
 "report_type": ["users", "form_submissions", "attachments"],
 "output_format": "pptx",
 "report_title": "User Activity Report",
 "include_data_table_in_ppt": true
}
```

### With Filters and Charts

```json
{
 "report_type": ["users", "form_submissions", "attachments"],
 "output_format": "pptx",
 "report_title": "User Activity Report 2023",
 "filters": [
   {"field": "form_submissions.submitted_at", "operator": "between", "value": ["2023-01-01", "2023-12-31"]}
 ],
 "charts": [
   {
     "type": "bar",
     "column": "users.role.name",
     "title": "Users by Role"
   },
   {
     "type": "line",
     "column": "form_submissions.submitted_at",
     "title": "Submission Timeline"
   },
   {
     "type": "pie",
     "column": "attachments.file_type",
     "title": "Attachment Types"
   }
 ],
 "include_data_table_in_ppt": true
}
```

## 7. CSV Export of Form Submissions with Answers

### CSV Format

```json
{
 "report_type": ["form_submissions", "answers_submitted"],
 "output_format": "csv",
 "report_title": "Form Submissions with Answers"
}
```

### With Filters

```json
{
 "report_type": ["form_submissions", "answers_submitted"],
 "output_format": "csv",
 "filters": [
   {"field": "form_submissions.form.title", "operator": "eq", "value": "Customer Feedback"}
 ],
 "report_title": "Customer Feedback Responses"
}
```

## 8. Environment and User Analysis

### Excel Format

```json
{
 "report_type": ["environments", "users"],
 "output_format": "xlsx",
 "report_title": "Environment User Distribution"
}
```

### PDF Format

```json
{
 "report_type": ["environments", "users"],
 "output_format": "pdf",
 "report_title": "Environment User Distribution"
}
```

### With Charts

```json
{
 "report_type": ["environments", "users"],
 "output_format": "pdf",
 "report_title": "Environment User Distribution",
 "charts": [
   {
     "type": "bar",
     "column": "environments.name",
     "title": "Environments Overview"
   },
   {
     "type": "pie",
     "column": "users.environment.name",
     "title": "User Distribution by Environment"
   }
 ]
}
```

## 9. Question Type Usage Analysis

### Excel Format

```json
{
 "report_type": ["question_types", "questions", "form_questions"],
 "output_format": "xlsx",
 "report_title": "Question Type Usage Analysis"
}
```

### PDF Format

```json
{
 "report_type": ["question_types", "questions", "form_questions"],
 "output_format": "pdf",
 "report_title": "Question Type Usage Analysis"
}
```

### With Charts

```json
{
 "report_type": ["question_types", "questions", "form_questions"],
 "output_format": "pdf",
 "report_title": "Question Type Usage Analysis",
 "charts": [
   {
     "type": "pie",
     "column": "question_types.type",
     "title": "Available Question Types"
   },
   {
     "type": "bar",
     "column": "questions.question_type.type",
     "title": "Questions by Type"
   },
   {
     "type": "bar",
     "column": "form_questions.form.title",
     "title": "Questions per Form"
   }
 ]
}
```

## 10. Forms with Answers Analysis

### Excel Format

```json
{
 "report_type": ["forms", "form_answers"],
 "output_format": "xlsx",
 "report_title": "Forms with Answers Analysis"
}
```

### PDF Format

```json
{
 "report_type": ["forms", "form_answers"],
 "output_format": "pdf",
 "report_title": "Forms with Answers Analysis"
}
```

### With Charts

```json
{
 "report_type": ["forms", "form_answers"],
 "output_format": "pdf",
 "report_title": "Forms with Answers Analysis",
 "charts": [
   {
     "type": "pie",
     "column": "forms.is_public",
     "title": "Public vs Private Forms"
   },
   {
     "type": "bar",
     "column": "form_answers.form_question.form.title",
     "title": "Answers per Form"
   }
 ]
}
```