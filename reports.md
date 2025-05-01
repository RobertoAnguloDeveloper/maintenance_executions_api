# API Report Generation Request Bodies for POST /api/reports/generate

This file contains various JSON request body examples for testing the `/api/reports/generate` endpoint based on the provided API documentation and database schema.

## How to Create a Report using Postman

To generate a report using this API endpoint via Postman, you need to configure the following parts of your request:

1.  **Method:** `POST`
    * Select `POST` from the dropdown list next to the URL field in Postman.

2.  **URL:** `YOUR_API_BASE_URL/api/reports/generate`
    * Replace `YOUR_API_BASE_URL` with the actual base URL where the API is hosted (e.g., `http://localhost:5000`, `https://api.example.com`).

3.  **Headers:** You need to set two essential headers:
    * `Authorization`:
        * **Key:** `Authorization`
        * **Value:** `Bearer <YOUR_JWT_TOKEN>`
        * **Purpose:** This authenticates your request. Replace `<YOUR_JWT_TOKEN>` with the valid JSON Web Token you obtained after logging in (e.g., via the `/api/users/login` endpoint).
    * `Content-Type`:
        * **Key:** `Content-Type`
        * **Value:** `application/json`
        * **Purpose:** This tells the server that the data you are sending in the request body is in JSON format.

4.  **Body:** This is where you define the specifics of the report you want.
    * Select the `Body` tab in Postman.
    * Choose the `raw` option.
    * Select `JSON` from the dropdown list (usually appears to the right of the `raw` option).
    * Enter the JSON payload defining your report.

    **Detailed Body Parameters:**

    * `report_type` (string | array of strings) - **Required**
        * **Purpose:** Specifies the data entity (or entities) to report on.
        * **Type:** String for a single entity, or an array of strings for a multi-entity report.
        * **Valid Values (based on docs/schema):** `"users"`, `"forms"`, `"form_submissions"`, `"environments"`, `"roles"`, `"permissions"`, `"role_permissions"`, `"questions"`, `"answers"`, `"form_questions"`, `"form_answers"`, `"answers_submitted"`, `"attachments"`, `"all"` (for all entities), or an array like `["users", "forms"]`.
        * **Example (Single):** `"report_type": "users"`
        * **Example (Multi):** `"report_type": ["users", "forms", "form_submissions"]`
        * **Example (All):** `"report_type": "all"`

    * `output_format` (string) - *Optional*
        * **Purpose:** Specifies the desired file format for the report.
        * **Type:** String.
        * **Valid Values (from docs):** `"xlsx"`, `"csv"`, `"pdf"`, `"docx"`, `"pptx"`.
        * **Default:** `"xlsx"` (if omitted).
        * **Example:** `"output_format": "pdf"`

    * `columns` (array of strings) - *Optional*
        * **Purpose:** Selects specific columns (fields) to include in the report. If omitted, a default set of columns for the `report_type` is used.
        * **Type:** Array of strings.
        * **Valid Values:** Field names from the primary entity table or related tables using dot notation (e.g., `role.name`, `form.title`, `creator.username`, `answers.Your Question Text`). The exact available fields depend on the `report_type` and the backend implementation (refer to schema or `/api/reports/schema` endpoint if admin).
        * **Example (Users):** `"columns": ["id", "username", "email", "role.name"]`
        * **Example (Submissions):** `"columns": ["id", "form.title", "submitted_by", "submitted_at", "answers.Safety Check Completed"]`

    * `filters` (array of objects) - *Optional*
        * **Purpose:** Filters the data included in the report based on specified criteria.
        * **Type:** Array, where each element is a filter object.
        * **Filter Object Structure:**
            * `field` (string): The field to filter on (can use dot notation for related fields, e.g., `role.id`, `form.title`, `answers_submitted.answer`).
            * `operator` (string): The comparison operator to use. Common values include:
                * `eq`: Equals (=)
                * `neq`: Not Equals (!=)
                * `gt`: Greater Than (>)
                * `gte`: Greater Than or Equal To (>=)
                * `lt`: Less Than (<)
                * `lte`: Less Than or Equal To (<=)
                * `like`: Pattern matching (case-insensitive, use `%` as wildcard).
                * `ilike`: Case-insensitive pattern matching (often same as `like` in PostgreSQL).
                * `in`: Value is within a list.
                * `notin`: Value is not within a list.
                * `between`: Value is between two specified values (inclusive).
                * `is`: Checks for `NULL` or `NOT NULL`.
            * `value`: The value to compare against. The type depends on the field and operator:
                * String for `eq`, `neq`, `like`, `ilike`.
                * Number (integer/float) for `eq`, `neq`, `gt`, `gte`, `lt`, `lte`.
                * Boolean (`true`/`false`) for `eq`, `neq`.
                * Array for `in`, `notin`, `between` (e.g., `["value1", "value2"]` for `in`, `[startDate, endDate]` for `between`).
                * `null` or `"null"` for `is` (e.g., `{"field": "contact_number", "operator": "is", "value": null}`).
        * **Example (Filter by Role ID):** `"filters": [{"field": "role_id", "operator": "eq", "value": 4}]`
        * **Example (Filter by Date Range):** `"filters": [{"field": "submitted_at", "operator": "between", "value": ["2025-04-01T00:00:00Z", "2025-04-30T23:59:59Z"]}]`
        * **Example (Filter by Name Like):** `"filters": [{"field": "name", "operator": "like", "value": "%Production%"}]`
        * **Example (Filter by Multiple Values):** `"filters": [{"field": "form.id", "operator": "in", "value": [1, 5, 10]}]`

    * `sort_by` (array of objects) - *Optional*
        * **Purpose:** Defines the sorting order for the report data.
        * **Type:** Array, where each element is a sort object.
        * **Sort Object Structure:**
            * `field` (string): The field to sort by (can use dot notation, e.g., `role.name`, `submitted_at`).
            * `direction` (string): The sort direction. Valid values: `"asc"` (ascending) or `"desc"` (descending).
        * **Example (Sort by Date Desc):** `"sort_by": [{"field": "submitted_at", "direction": "desc"}]`
        * **Example (Multi-Sort):** `"sort_by": [{"field": "role.name", "direction": "asc"}, {"field": "username", "direction": "asc"}]`

    * `filename` (string) - *Optional*
        * **Purpose:** Suggests a base filename for the generated report file. The server might add extensions or timestamps.
        * **Type:** String.
        * **Example:** `"filename": "active_users_report"`

    * `report_title` (string) - *Optional*
        * **Purpose:** Sets a custom title within the report content (primarily for PDF and PPTX formats).
        * **Type:** String.
        * **Example:** `"report_title": "Q1 User Activity Summary"`

    * `include_data_table_in_ppt` (boolean) - *Optional (PPTX only)*
        * **Purpose:** Whether to include a data table slide in the PowerPoint output.
        * **Type:** Boolean (`true` or `false`).
        * **Default:** Not specified, likely `false`.
        * **Example:** `"include_data_table_in_ppt": true`

    * `max_ppt_table_rows` (integer) - *Optional (PPTX only)*
        * **Purpose:** Limits the number of rows shown in the data table if `include_data_table_in_ppt` is true.
        * **Type:** Integer.
        * **Default:** Not specified.
        * **Example:** `"max_ppt_table_rows": 20`

    * `[entity]_sheet_name` (string) - *Optional (Multi-entity XLSX only)*
        * **Purpose:** Customizes the sheet name for a specific entity in a multi-entity XLSX report. Replace `[entity]` with the plural entity name (e.g., `users`, `forms`).
        * **Type:** String.
        * **Example:** `"users_sheet_name": "System Users List"`

    * `table_options` (object) - *Optional (XLSX only)*
        * **Purpose:** Applies specific styling options to tables within the XLSX report.
        * **Type:** Object.
        * **Object Structure (Example):**
            * `style` (string): Name of a predefined Excel table style (e.g., "Table Style Medium 2", "Table Style Light 9").
            * `banded_rows` (boolean): Whether to apply banded row styling.
        * **Example:** `"table_options": {"style": "Table Style Medium 9", "banded_rows": true}`

---

## Report Examples

*(The rest of the examples from the previous version follow here...)*

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
