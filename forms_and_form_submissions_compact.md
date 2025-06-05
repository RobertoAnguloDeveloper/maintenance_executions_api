# API Endpoints Documentation

## Forms Endpoints

### Endpoint: `/api/forms/compact`

* **Method:** `GET`
* **Description:** Get compact information for all forms accessible to the current user, with optional filtering and sorting. Returns only forms editable by the user if 'only_editable' is true (for non-admins).
* **Authentication Required:** True
* **Base URL Example:** `GET /api/forms/compact`
* **Query Parameters:**
    ```json
    [
      {
        "name": "date_filter_field",
        "type": "string",
        "optional": true,
        "description": "Specifies which date field to filter on.",
        "accepted_values": ["created_at", "updated_at"],
        "notes": "If provided, 'start_date' and 'end_date' are also required.",
        "example_url": "/api/forms/compact?date_filter_field=created_at&start_date=2024-01-01&end_date=2024-01-31"
      },
      {
        "name": "start_date",
        "type": "string",
        "optional": true,
        "description": "The start date for the date range filter. Required if 'date_filter_field' is specified.",
        "format": "ISO 8601 (e.g., 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SSZ')"
      },
      {
        "name": "end_date",
        "type": "string",
        "optional": true,
        "description": "The end date for the date range filter. Required if 'date_filter_field' is specified.",
        "format": "ISO 8601 (e.g., 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SSZ')"
      },
      {
        "name": "sort_by",
        "type": "string",
        "optional": true,
        "default": "updated_at",
        "description": "Field to sort the results by.",
        "accepted_values": ["updated_at", "title", "created_at"],
        "example_urls": [
          "/api/forms/compact?sort_by=title",
          "/api/forms/compact?sort_by=created_at&sort_order=asc"
        ]
      },
      {
        "name": "sort_order",
        "type": "string",
        "optional": true,
        "default": "desc",
        "description": "Order of sorting.",
        "accepted_values": ["asc", "desc"],
        "example_url": "/api/forms/compact?sort_order=asc"
      },
      {
        "name": "only_editable",
        "type": "string",
        "optional": true,
        "default": "false",
        "description": "If 'true', returns only forms that are editable by the current user (i.e., created by them, unless they are an admin).",
        "accepted_values": ["true", "false"],
        "example_url": "/api/forms/compact?only_editable=true"
      }
    ]
    ```
* **Combined Example URLs:**
    ```json
    [
      {
        "description": "Get forms created in January 2024, sorted by title ascending.",
        "url": "/api/forms/compact?date_filter_field=created_at&start_date=2024-01-01&end_date=2024-01-31&sort_by=title&sort_order=asc"
      },
      {
        "description": "Get only forms editable by the current user, sorted by update date descending.",
        "url": "/api/forms/compact?only_editable=true&sort_by=updated_at&sort_order=desc"
      },
      {
        "description": "Get forms updated in March 2024 that are editable by the current user, sorted by title.",
        "url": "/api/forms/compact?date_filter_field=updated_at&start_date=2024-03-01T00:00:00Z&end_date=2024-03-31T23:59:59Z&only_editable=true&sort_by=title"
      }
    ]
    ```
* **Response Fields Per Item:**
    ```json
    [
      {"name": "id", "type": "integer", "description": "The unique identifier for the form."},
      {"name": "title", "type": "string", "description": "The title of the form."},
      {"name": "description", "type": "string", "nullable": true, "description": "A brief description of the form."},
      {"name": "questions_count", "type": "integer", "description": "The number of active questions in the form."},
      {"name": "created_at", "type": "string", "format": "ISO 8601 datetime", "nullable": true, "description": "Timestamp of when the form was created."},
      {"name": "updated_at", "type": "string", "format": "ISO 8601 datetime", "nullable": true, "description": "Timestamp of when the form was last updated."},
      {"name": "created_by_fullname", "type": "string", "nullable": true, "description": "Full name of the user who created the form."}
    ]
    ```

---

## Form Submissions Endpoints

### Endpoint: `/api/form_submissions/compact`

* **Method:** `GET`
* **Description:** Get a compact list of form submissions with optional filtering and sorting.
* **Authentication Required:** True
* **Base URL Example:** `GET /api/form_submissions/compact`
* **Query Parameters:**
    ```json
    [
      {
        "name": "form_id",
        "type": "integer",
        "optional": true,
        "description": "Filter submissions by a specific form ID.",
        "example_url": "/api/form_submissions/compact?form_id=101"
      },
      {
        "name": "start_date",
        "type": "string",
        "optional": true,
        "description": "Filter submissions where 'submitted_at' is on or after this date. Required if 'end_date' is provided.",
        "format": "ISO 8601 (e.g., 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SSZ')",
        "example_url": "/api/form_submissions/compact?start_date=2024-03-01&end_date=2024-03-31"
      },
      {
        "name": "end_date",
        "type": "string",
        "optional": true,
        "description": "Filter submissions where 'submitted_at' is on or before this date. Required if 'start_date' is provided.",
        "format": "ISO 8601 (e.g., 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SSZ')"
      },
      {
        "name": "sort_by",
        "type": "string",
        "optional": true,
        "default": "submitted_at",
        "description": "Field to sort the results by.",
        "accepted_values": ["submitted_at", "submitted_by", "form_title"],
        "example_urls": [
          "/api/form_submissions/compact?sort_by=submitted_by",
          "/api/form_submissions/compact?sort_by=form_title&sort_order=asc"
        ]
      },
      {
        "name": "sort_order",
        "type": "string",
        "optional": true,
        "default": "desc",
        "description": "Order of sorting.",
        "accepted_values": ["asc", "desc"],
        "example_url": "/api/form_submissions/compact?sort_order=asc"
      }
    ]
    ```
* **Combined Example URLs:**
    ```json
    [
      {
        "description": "Get submissions for form_id 75, submitted in Q1 2024, sorted by submitter's username ascending.",
        "url": "/api/form_submissions/compact?form_id=75&start_date=2024-01-01T00:00:00Z&end_date=2024-03-31T23:59:59Z&sort_by=submitted_by&sort_order=asc"
      },
      {
        "description": "Get all accessible submissions, sorted by form title descending.",
        "url": "/api/form_submissions/compact?sort_by=form_title&sort_order=desc"
      },
      {
        "description": "Get submissions submitted in May 2025, sorted by submission date ascending.",
        "url": "/api/form_submissions/compact?start_date=2025-05-01&end_date=2025-05-31&sort_by=submitted_at&sort_order=asc"
      }
    ]
    ```
* **Response Structure (Outer):**
    ```json
    {
      "total_count": "integer (total number of items matching filters)",
      "filters_applied": {
          "form_id": "integer (value of form_id filter, or null)",
          "start_date": "string (value of start_date filter, or null)",
          "end_date": "string (value of end_date filter, or null)",
          "sort_by": "string (value of sort_by filter)",
          "sort_order": "string (value of sort_order filter)"
      },
      "submissions": "array (list of submission objects, see 'response_fields_per_item_format')"
    }
    ```
* **Response Fields Per Item:**
    ```json
    [
      {"name": "id", "type": "integer", "description": "The unique identifier for the submission."},
      {"name": "form_id", "type": "integer", "description": "The ID of the form that was submitted."},
      {"name": "form_title", "type": "string", "nullable": true, "description": "The title of the submitted form."},
      {"name": "submitted_at", "type": "string", "format": "ISO 8601 datetime", "nullable": true, "description": "Timestamp of when the form was submitted."},
      {"name": "submitted_by", "type": "string", "description": "Username of the user who submitted the form."},
      {"name": "answers_count", "type": "integer", "description": "The number of non-deleted answers in this submission."},
      {"name": "signatures_count", "type": "integer", "description": "The number of attachments in this submission that are marked as signatures."},
      {"name": "attachments_count", "type": "integer", "description": "The number of attachments in this submission that are NOT marked as signatures."}
    ]
    ```

### Endpoint: `/api/form_submissions/search`

* **Method:** `GET`
* **Description:** Search form submissions based on criteria within their answers. Returns results in a compact format.
* **Authentication Required:** True
* **Base URL Example:** `GET /api/form_submissions/search`
* **Query Parameters:**
    ```json
    [
      {
        "name": "form_id",
        "type": "integer",
        "optional": true,
        "description": "Further restrict the search to submissions belonging to this specific form ID."
      },
      {
        "name": "answer",
        "type": "string",
        "optional": true,
        "description": "Search for submissions containing an answer with this text (case-insensitive, partial match)."
      },
      {
        "name": "cell_content",
        "type": "string",
        "optional": true,
        "description": "Search for submissions containing a table answer with this cell content (case-insensitive, partial match)."
      },
      {
        "name": "question",
        "type": "string",
        "optional": true,
        "description": "Search for submissions containing an answer to a question with this text (case-insensitive, partial match)."
      },
      {
        "name": "question_type",
        "type": "string",
        "optional": true,
        "description": "Search for submissions containing an answer to a question of this type (case-insensitive, partial match)."
      }
    ]
    ```
* **Notes:**
    * At least one of the following parameters must be provided for the search: 'answer', 'cell\_content', 'question', 'question\_type'.
    * All provided search criteria are combined with an AND logic.
* **Example URLs:**
    ```json
    [
      {
        "description": "Search for submissions where any answer contains 'safety hazard'.",
        "url": "/api/form_submissions/search?answer=safety%20hazard"
      },
      {
        "description": "Search for submissions for form_id 42 where a 'checkbox' type question was answered with 'Yes'.",
        "url": "/api/form_submissions/search?form_id=42&question_type=checkbox&answer=Yes"
      },
      {
        "description": "Search for submissions where the question 'Equipment ID' has an answer 'EX-101'.",
        "url": "/api/form_submissions/search?question=Equipment%20ID&answer=EX-101"
      },
      {
        "description": "Search for submissions containing table cell content 'Needs Repair'.",
        "url": "/api/form_submissions/search?cell_content=Needs%20Repair"
      }
    ]
    ```
* **Response Structure (Outer):**
    ```json
    {
      "search_criteria_applied": {
          "answer": "string (value of answer filter, or null)",
          "cell_content": "string (value of cell_content filter, or null)",
          "question": "string (value of question filter, or null)",
          "question_type": "string (value of question_type filter, or null)"
      },
      "form_id_filter_applied": "integer (value of form_id filter, or null)",
      "total_results": "integer (total number of submissions matching all criteria)",
      "submissions": "array (list of submission objects, see 'response_fields_per_item_format')"
    }
    ```
* **Response Fields Per Item (same as `/api/form_submissions/compact`):**
    ```json
    [
      {"name": "id", "type": "integer", "description": "The unique identifier for the submission."},
      {"name": "form_id", "type": "integer", "description": "The ID of the form that was submitted."},
      {"name": "form_title", "type": "string", "nullable": true, "description": "The title of the submitted form."},
      {"name": "submitted_at", "type": "string", "format": "ISO 8601 datetime", "nullable": true, "description": "Timestamp of when the form was submitted."},
      {"name": "submitted_by", "type": "string", "description": "Username of the user who submitted the form."},
      {"name": "answers_count", "type": "integer", "description": "The number of non-deleted answers in this submission."},
      {"name": "signatures_count", "type": "integer", "description": "The number of attachments in this submission that are marked as signatures."},
      {"name": "attachments_count", "type": "integer", "description": "The number of attachments in this submission that are NOT marked as signatures."}
    ]
    ```

---