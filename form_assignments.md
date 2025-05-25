This guide outlines how to make requests to the Form Assignments API endpoints using Postman.

**Common Headers for all requests (unless specified):**
* `Authorization`: `Bearer {{jwt_token}}`
* `Content-Type`: `application/json` (for POST/PUT requests)

---

### 1. Create Single Form Assignment

* **Request Type:** `POST`
* **URL:** `{{base_url}}/form-assignments`
* **Body (Raw JSON):**
    ```json
    {
        "form_id": 1,
        "entity_name": "user", // or "role", "environment"
        "entity_id": 101
    }
    ```
* **Success Response (201 Created):**
    ```json
    {
        "message": "Form assigned successfully",
        "assignment": {
            "id": 1,
            "form_id": 1,
            "entity_name": "user",
            "entity_id": 101,
            "created_at": "2023-10-27T10:00:00Z",
            "updated_at": "2023-10-27T10:00:00Z",
            "is_deleted": false,
            "deleted_at": null,
            "form": { 
                "id": 1,
                "title": "Sample Form Title"
                // ... other basic form fields from form.to_dict_basic()
            }
        }
    }
    ```
* **Error Responses:**
    * `400 Bad Request`: Missing fields, invalid data types.
        ```json
        { "error": "Invalid data types or missing required fields: form_id (int), entity_name (non-empty str), entity_id (int)" }
        ```
    * `401 Unauthorized`: Authentication error.
    * `403 Forbidden`: User not authorized.
    * `404 Not Found`: Form or entity not found.
    * `409 Conflict`: Form already actively assigned.
    * `500 Internal Server Error`.

---

### 2. Create Bulk Form Assignments

* **Request Type:** `POST`
* **URL:** `{{base_url}}/form-assignments/bulk`
* **Body (Raw JSON):**
    ```json
    [
        { "form_id": 1, "entity_name": "user", "entity_id": 102 },
        { "form_id": 2, "entity_name": "role", "entity_id": 5 }
    ]
    ```
* **Success Response (201 Created - if all successful):**
    ```json
    {
        "message": "All assignments created successfully.",
        "details": {
            "successful_assignments": [
                { "form_id": 1, "entity_name": "user", "entity_id": 102, "assignment_id": 2 },
                { "form_id": 2, "entity_name": "role", "entity_id": 5, "assignment_id": 3 }
            ],
            "failed_assignments": []
        }
    }
    ```
* **Partial Success Response (207 Multi-Status):**
    ```json
    {
        "message": "Bulk assignment processing complete.",
        "details": {
            "successful_assignments": [ /* ... */ ],
            "failed_assignments": [ /* ... */ ]
        }
    }
    ```
* **Error Responses:** `400`, `401`, `403`, `500`.

---

### 3. Get Form Assignments Batch (Admin, Paginated)

* **Request Type:** `GET`
* **URL:** `{{base_url}}/form-assignments/batch`
* **Query Parameters (Optional):**
    * `page` (integer, default: 1): The page number to retrieve.
    * `per_page` (integer, default: 50): The number of items per page.
    * Example: `{{base_url}}/form-assignments/batch?page=2&per_page=10`
* **Body:** None
* **Success Response (200 OK):**
    ```json
    {
        "metadata": {
            "total_items": 150,
            "total_pages": 15,
            "current_page": 2,
            "per_page": 10
        },
        "assignments": [
            {
                "id": 11,
                "form_id": 5,
                "entity_name": "role",
                "entity_id": 2,
                // ... other assignment fields including 'form' object ...
            }
            // ... other assignments ...
        ]
    }
    ```
* **Error Responses:**
    * `401 Unauthorized`.
    * `403 Forbidden`: User is not an administrator.
        ```json
        { "error": "Unauthorized: Only administrators can view assignments batch." }
        ```
    * `500 Internal Server Error`.

---

### 4. Get All Form Assignments Unpaginated (Admin)

* **Request Type:** `GET`
* **URL:** `{{base_url}}/form-assignments/`
* **Body:** None
* **Success Response (200 OK):**
    ```json
    {
        "assignments": [
            {
                "id": 1,
                "form_id": 1,
                "entity_name": "user",
                "entity_id": 101,
                // ... other assignment fields including 'form' object ...
            },
            {
                "id": 2,
                "form_id": 1,
                "entity_name": "user",
                "entity_id": 102,
                // ... other assignment fields including 'form' object ...
            }
            // ... all other assignments ...
        ],
        "total_items": 2 // Total count of all assignments
    }
    ```
* **Error Responses:**
    * `401 Unauthorized`.
    * `403 Forbidden`: User is not an administrator.
        ```json
        { "error": "Unauthorized: Only administrators can view all assignments." }
        ```
    * `500 Internal Server Error`.

---

### 5. Get Specific Form Assignment

* **Request Type:** `GET`
* **URL:** `{{base_url}}/form-assignments/<assignment_id>`
    * Example: `{{base_url}}/form-assignments/1`
* **Body:** None
* **Success Response (200 OK):**
    ```json
    {
        "id": 1,
        "form_id": 1,
        "entity_name": "user",
        "entity_id": 101,
        // ... other assignment fields including 'form' object ...
    }
    ```
* **Error Responses:** `401`, `403`, `404`, `500`.

---

### 6. Update Form Assignment

* **Request Type:** `PUT`
* **URL:** `{{base_url}}/form-assignments/<assignment_id>`
    * Example: `{{base_url}}/form-assignments/1`
* **Body (Raw JSON):**
    * Provide at least one field to update (`entity_name` or `entity_id`).
    ```json
    {
        "entity_name": "role", 
        "entity_id": 3
    }
    ```
* **Success Response (200 OK):**
    ```json
    {
        "message": "Form assignment updated successfully",
        "assignment": {
            "id": 1,
            "form_id": 1,
            "entity_name": "role", // Updated value
            "entity_id": 3,      // Updated value
            // ... other assignment fields including 'form' object ...
        }
    }
    ```
* **Error Responses:** `400`, `401`, `403`, `404`, `409`, `500`.

---

### 7. Get Assignments for a Specific Form

* **Request Type:** `GET`
* **URL:** `{{base_url}}/form-assignments/form/<form_id>`
    * Example: `{{base_url}}/form-assignments/form/1`
* **Body:** None
* **Success Response (200 OK):**
    ```json
    {
        "form_id": 1,
        "assignments": [ /* ... list of assignments ... */ ]
    }
    ```
* **Error Responses:** `401`, `403`, `404`, `500`.

---

### 8. Get Forms Assigned to a Specific Entity

* **Request Type:** `GET`
* **URL:** `{{base_url}}/form-assignments/entity/<entity_name>/<entity_id>`
    * Example (user): `{{base_url}}/form-assignments/entity/user/101`
* **Body:** None
* **Success Response (200 OK):**
    ```json
    {
        "entity_name": "user",
        "entity_id": 101,
        "assigned_forms": [ /* ... list of form basic dicts ... */ ]
    }
    ```
* **Error Responses:** `400`, `401`, `403`, `500`.

---

### 9. Get Accessible Forms for Current User

* **Request Type:** `GET`
* **URL:** `{{base_url}}/form-assignments/user/accessible-forms`
* **Body:** None
* **Success Response (200 OK):**
    ```json
    {
        "user_id": 101, 
        "accessible_forms": [ /* ... list of form basic dicts ... */ ]
    }
    ```
* **Error Responses:** `401`, `500`.

---

### 10. Get Accessible Forms for a Specific User (Admin)

* **Request Type:** `GET`
* **URL:** `{{base_url}}/form-assignments/user/<user_id>/accessible-forms`
    * Example: `{{base_url}}/form-assignments/user/105/accessible-forms`
* **Body:** None
* **Success Response (200 OK):**
    ```json
    {
        "user_id": 105, 
        "accessible_forms": [ /* ... list of form basic dicts ... */ ]
    }
    ```
* **Error Responses:** `401`, `403`, `500`.

---

### 11. Delete Form Assignment

* **Request Type:** `DELETE`
* **URL:** `{{base_url}}/form-assignments/<assignment_id>`
    * Example: `{{base_url}}/form-assignments/1`
* **Body:** None
* **Success Response (200 OK):**
    ```json
    {
        "message": "Form assignment deleted successfully.",
        "deleted_id": 1
    }
    ```
* **Error Responses:** `401`, `403`, `404`, `500`.

---
This guide should help you interact with the Form Assignments API using Postman.
