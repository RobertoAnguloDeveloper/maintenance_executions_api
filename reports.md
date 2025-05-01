# API Report Generation Request Bodies for POST /api/reports/generate

This file contains various JSON request body examples for testing the `/api/reports/generate` endpoint based on the provided API documentation and database schema.

## 1. Basic Reports (Default XLSX Format)

* **Users Report:**
    ```json
    {
      "report_type": "users"
    }
    ```
* **Forms Report:**
    ```json
    {
      "report_type": "forms"
    }
    ```
* **Form Submissions Report:**
    ```json
    {
      "report_type": "form_submissions"
    }
    ```
* **Environments Report:**
    ```json
    {
      "report_type": "environments"
    }
    ```
* **Roles Report:**
    ```json
    {
      "report_type": "roles"
    }
    ```

## 2. Reports with Column Selection

* **Specific User Columns:**
    ```json
    {
      "report_type": "users",
      "columns": [
        "id",
        "username",
        "email",
        "first_name",
        "last_name",
        "role.name",
        "environment.name",
        "created_at"
      ]
    }
    ```
* **Specific Form Submission Columns**:
    ```json
    {
      "report_type": "form_submissions",
      "columns": [
        "id",
        "form.title",
        "submitted_by",
        "submitted_at",
        "form.creator.username",
        "created_at"
      ]
    }
    ```

## 3. Reports with Filtering

* **Filter Users by Role ID:**
    ```json
    {
      "report_type": "users",
      "filters": [
        {
          "field": "role_id",
          "operator": "eq",
          "value": 4 // Example: Technician role ID from backup
        }
      ]
    }
    ```
* **Filter Environments by Name Like 'Production' (if applicable) and Date**:
    ```json
    {
      "report_type": "environments",
      "filters": [
        {
          "field": "name",
          "operator": "like",
          "value": "Production"
        },
        {
          "field": "created_at",
          "operator": "gte",
          "value": "2025-01-01T00:00:00Z"
        }
      ]
    }
    ```
* **Filter Form Submissions by Date Range:**
    ```json
    {
      "report_type": "form_submissions",
      "filters": [
        {
          "field": "submitted_at",
          "operator": "between",
          "value": ["2025-04-01T00:00:00Z", "2025-04-30T23:59:59Z"] // Example date range
        }
      ]
    }
    ```
* **Filter Form Submissions by Specific Form ID and Answer Value**:
    ```json
    {
      "report_type": "form_submissions",
      "filters": [
        {
          "field": "form.id",
          "operator": "eq",
          "value": 1 // Example form ID from backup
        },
        {
          "field": "answers_submitted.question",
          "operator": "eq",
          "value": "Select your department" // Example question text from backup
        },
        {
          "field": "answers_submitted.answer",
          "operator": "eq",
          "value": "Maintenance Department" // Example answer text from backup
        }
      ]
    }
    ```

## 4. Reports with Sorting

* **Sort Users by Username Descending:**
    ```json
    {
      "report_type": "users",
      "sort_by": [
        {
          "field": "username",
          "direction": "desc"
        }
      ]
    }
    ```
* **Sort Role Permissions by Role Name and Permission Entity**:
    ```json
    {
      "report_type": "role_permissions",
      "sort_by": [
        {
          "field": "role.name",
          "direction": "asc"
        },
        {
          "field": "permission.entity",
          "direction": "asc"
        }
      ]
    }
    ```

## 5. Reports with Different Output Formats

* **Forms Report as CSV**:
    ```json
    {
      "report_type": "forms",
      "output_format": "csv",
      "columns": [
        "id",
        "title",
        "description",
        "creator.username",
        "is_public",
        "created_at"
      ]
    }
    ```
* **Form Submissions Report as PDF with Title**:
    ```json
    {
      "report_type": "form_submissions",
      "output_format": "pdf",
      "report_title": "Form Submissions Summary Report",
      "filters": [
        {
          "field": "submitted_at",
          "operator": "between",
          "value": ["2025-04-01T00:00:00Z", "2025-04-30T23:59:59Z"]
        }
      ]
    }
    ```
* **Active Users Report as DOCX with Custom Filename**:
    ```json
    {
      "report_type": "users",
      "output_format": "docx",
      "filename": "active_users_report",
      "filters": [
        {
          "field": "is_deleted",
          "operator": "eq",
          "value": false
        }
      ]
    }
    ```
* **Form Submissions Report as PPTX**:
    ```json
    {
      "report_type": "form_submissions",
      "output_format": "pptx",
      "report_title": "Monthly Submission Trends",
      "include_data_table_in_ppt": true,
      "max_ppt_table_rows": 15
    }
    ```

## 6. Multi-Entity Reports

* **Report on All Entities (XLSX)**:
    ```json
    {
      "report_type": "all",
      "output_format": "xlsx",
      "filename": "full_system_data_report"
    }
    ```
* **Report on Specific Entities (CSV in ZIP)**:
    ```json
    {
      "report_type": ["users", "forms", "form_submissions"],
      "output_format": "csv",
      "filename": "user_form_activity"
    }
    ```
* **Report on Specific Entities (XLSX with Custom Sheet Names & Styling)**:
    ```json
    {
      "report_type": ["users", "environments"],
      "output_format": "xlsx",
      "users_sheet_name": "System Users",
      "environments_sheet_name": "Available Environments",
      "filename": "system_configuration",
      "table_options": {
        "style": "Table Style Medium 2",
        "banded_rows": true
      }
    }
    ```

## 7. Complex Combined Request

* **Filtered, Sorted, Specific Columns, Custom Filename:**
    ```json
    {
      "report_type": "form_submissions",
      "columns": [
        "id",
        "form.title",
        "submitted_by",
        "submitted_at",
        "answers.What is your full name?", // Using specific answer text; needs careful mapping
        "answers.Select your department"
      ],
      "filters": [
        {
          "field": "form.id",
          "operator": "eq",
          "value": 1 // Example form ID from backup
        },
        {
          "field": "submitted_at",
          "operator": "between",
          "value": ["2025-01-01T00:00:00Z", "2025-03-31T23:59:59Z"]
        }
      ],
      "sort_by": [
        {
          "field": "submitted_at",
          "direction": "desc"
        }
      ],
      "output_format": "xlsx",
      "filename": "q1_form1_submissions"
    }
    ```

## 8. Additional Examples

* **Questions Report (Filtered, CSV)**: Report on questions that are marked as required.
    ```json
    {
      "report_type": "questions",
      "output_format": "csv",
      "filters": [
        {
          "field": "is_required",
          "operator": "eq",
          "value": true
        }
      ],
      "columns": [
        "id",
        "text",
        "type.name",
        "remarks",
        "is_required"
      ]
    }
    ```
* **Answers Submitted Report (Filtered, Sorted, PDF)**: Report on answers submitted for a specific form submission, sorted by question text.
    ```json
    {
      "report_type": "answers_submitted",
      "output_format": "pdf",
      "report_title": "Submission Details - ID 5",
      "filters": [
        {
          "field": "form_submission_id",
          "operator": "eq",
          "value": 5 // Example submission ID
        }
      ],
      "sort_by": [
        {
          "field": "question_text",
          "direction": "asc"
        }
      ],
      "columns": [
        "id",
        "question_text",
        "question_type_text",
        "answer_text",
        "column",
        "row",
        "cell_content"
      ]
    }
    ```
* **Attachments Report (Filtered, XLSX)**: Report on attachments that are signatures.
    ```json
    {
      "report_type": "attachments",
      "output_format": "xlsx",
      "filters": [
        {
          "field": "is_signature",
          "operator": "eq",
          "value": true
        }
      ],
      "columns": [
        "id",
        "form_submission_id",
        "filename",
        "file_type",
        "signature_position",
        "signature_author",
        "created_at"
      ]
    }
    ```
* **Roles and Permissions Multi-Entity Report (XLSX)**: Report combining roles and permissions with custom sheet names.
    ```json
    {
      "report_type": ["roles", "permissions"],
      "output_format": "xlsx",
      "roles_sheet_name": "System Roles",
      "permissions_sheet_name": "Available Permissions",
      "filename": "roles_and_permissions_overview"
    }
    ```
