This guide outlines how to make requests to the Form Assignments API endpoints using Postman.

**Common Headers for all requests (unless specified):**
* `Authorization`: `Bearer {{jwt_token}}`
* `Content-Type`: `application/json` (for POST requests)

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
            "deleted_at": null
        }
    }
    ```
* **Error Responses:**
    * `400 Bad Request`: Missing fields, invalid data types.
        ```json
        { "error": "Missing required fields: form_id, entity_name, entity_id" }
        ```json
        { "error": "Invalid data types for form_id, entity_name, or entity_id" }
        ```
    * `401 Unauthorized`: Authentication error (e.g., user not found for token).
        ```json
        { "error": "Authentication error: User not found." }
        ```
    * `403 Forbidden`: User not authorized to assign the form.
        ```json
        { "error": "Unauthorized to assign this form. You must be the form owner or an administrator." }
        ```
    * `404 Not Found`: Form not found.
        ```json
        { "error": "Form with ID 1 not found." }
        ```
    * `409 Conflict`: Form already assigned to this entity.
        ```json
        { "error": "This form is already actively assigned to user ID 101." }
        ```
    * `500 Internal Server Error`:
        ```json
        { "error": "Internal server error: <specific error message>" }
        ```

---

### 2. Create Bulk Form Assignments

* **Request Type:** `POST`
* **URL:** `{{base_url}}/form-assignments/bulk`
* **Body (Raw JSON):**
    ```json
    [
        {
            "form_id": 1,
            "entity_name": "user",
            "entity_id": 102
        },
        {
            "form_id": 2,
            "entity_name": "role",
            "entity_id": 5
        },
        {
            "form_id": 1, // This might fail if form 1 is already assigned to user 101
            "entity_name": "user",
            "entity_id": 101
        },
        {
            "form_id": 999, // This will fail if form 999 doesn't exist
            "entity_name": "user",
            "entity_id": 103
        }
    ]
    ```
* **Success Response (201 Created - if all successful):**
    ```json
    {
        "message": "All assignments created successfully.",
        "details": {
            "successful_assignments": [
                {
                    "form_id": 1,
                    "entity_name": "user",
                    "entity_id": 102,
                    "assignment_id": 2
                },
                {
                    "form_id": 2,
                    "entity_name": "role",
                    "entity_id": 5,
                    "assignment_id": 3
                }
            ],
            "failed_assignments": []
        }
    }
    ```
* **Partial Success Response (207 Multi-Status - if some succeed and some fail):**
    ```json
    {
        "message": "Bulk assignment processing complete.",
        "details": {
            "successful_assignments": [
                {
                    "form_id": 1,
                    "entity_name": "user",
                    "entity_id": 102,
                    "assignment_id": 2
                }
            ],
            "failed_assignments": [
                {
                    "input": {
                        "form_id": 1,
                        "entity_name": "user",
                        "entity_id": 101
                    },
                    "error": "This form is already actively assigned to user ID 101."
                },
                {
                    "input": {
                        "form_id": 999,
                        "entity_name": "user",
                        "entity_id": 103
                    },
                    "error": "Form with ID 999 not found or is deleted."
                }
            ]
        }
    }
    ```
* **Error Responses:**
    * `400 Bad Request`: Invalid payload structure, empty list, or all assignments failed.
        ```json
        { "error": "Invalid payload: Expected a list of assignment objects." }
        ```json
        { 
            "message": "All assignments failed to process.",
            "details": {
                "successful_assignments": [],
                "failed_assignments": [ /* ... list of all failures ... */ ]
            }
        }
        ```
    * `401 Unauthorized`: Authentication error.
    * `403 Forbidden`: User not authorized for bulk operations (e.g., not an admin).
        ```json
        { "error": "Unauthorized: Bulk assignment is restricted to administrators." }
        ```
    * `500 Internal Server Error`.

---

### 3. Get Assignments for a Specific Form

* **Request Type:** `GET`
* **URL:** `{{base_url}}/form-assignments/form/<form_id>`
    * Example: `{{base_url}}/form-assignments/form/1`
* **Body:** None
* **Success Response (200 OK):**
    ```json
    {
        "form_id": 1,
        "assignments": [
            {
                "id": 1,
                "form_id": 1,
                "entity_name": "user",
                "entity_id": 101,
                "created_at": "2023-10-27T10:00:00Z",
                "updated_at": "2023-10-27T10:00:00Z",
                "is_deleted": false,
                "deleted_at": null
            },
            {
                "id": 2,
                "form_id": 1,
                "entity_name": "user",
                "entity_id": 102,
                "created_at": "2023-10-27T10:05:00Z",
                "updated_at": "2023-10-27T10:05:00Z",
                "is_deleted": false,
                "deleted_at": null
            }
        ]
    }
    ```
    If no assignments:
    ```json
    {
        "form_id": 1,
        "assignments": []
    }
    ```
* **Error Responses:**
    * `401 Unauthorized`.
    * `403 Forbidden`: User not authorized to view assignments for this form.
    * `404 Not Found`: Form not found.
    * `500 Internal Server Error`.

---

### 4. Get Forms Assigned to a Specific Entity

* **Request Type:** `GET`
* **URL:** `{{base_url}}/form-assignments/entity/<entity_name>/<entity_id>`
    * Example (user): `{{base_url}}/form-assignments/entity/user/101`
    * Example (role): `{{base_url}}/form-assignments/entity/role/5`
* **Body:** None
* **Success Response (200 OK):**
    ```json
    {
        "entity_name": "user",
        "entity_id": 101,
        "assigned_forms": [ // These are Form objects, structure depends on Form.to_dict_basic()
            {
                "id": 1,
                "title": "User Onboarding Form",
                "user_id": 10, // Creator ID
                "is_public": false,
                // ... other basic form fields ...
                "created_at": "2023-10-26T09:00:00Z"
            },
            {
                "id": 3,
                "title": "Feedback Form",
                "user_id": 12,
                "is_public": true,
                // ... other basic form fields ...
                "created_at": "2023-10-25T11:00:00Z"
            }
        ]
    }
    ```
* **Error Responses:**
    * `400 Bad Request`: Invalid entity name.
        ```json
        { "error": "Invalid entity_name: <name>. Must be one of ['user', 'role', 'environment']." }
        ```
    * `401 Unauthorized`.
    * `403 Forbidden`: User not authorized to view forms for this entity.
    * `500 Internal Server Error`.

---

### 5. Get Accessible Forms for Current User

* **Request Type:** `GET`
* **URL:** `{{base_url}}/form-assignments/user/accessible-forms`
* **Body:** None
* **Success Response (200 OK):**
    ```json
    {
        "user_id": 101, // ID of the authenticated user
        "accessible_forms": [ // List of Form objects (basic dict)
            {
                "id": 1,
                "title": "User Onboarding Form",
                // ... other basic form fields ...
            },
            {
                "id": 5,
                "title": "General Survey",
                // ... other basic form fields ...
            }
        ]
    }
    ```
* **Error Responses:**
    * `401 Unauthorized`.
    * `500 Internal Server Error`.

---

### 6. Get Accessible Forms for a Specific User (Admin)

* **Request Type:** `GET`
* **URL:** `{{base_url}}/form-assignments/user/<user_id>/accessible-forms`
    * Example: `{{base_url}}/form-assignments/user/105/accessible-forms`
* **Body:** None
* **Success Response (200 OK):**
    ```json
    {
        "user_id": 105, // ID of the target user
        "accessible_forms": [ // List of Form objects (basic dict)
            {
                "id": 2,
                "title": "Department Specific Form",
                // ... other basic form fields ...
            }
        ]
    }
    ```
* **Error Responses:**
    * `401 Unauthorized`: Admin authentication error.
    * `403 Forbidden`: Authenticated user is not an admin or lacks `VIEW_ALL` permission.
    * `500 Internal Server Error`.

---

### 7. Delete Form Assignment

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
* **Error Responses:**
    * `401 Unauthorized`.
    * `403 Forbidden`: User not authorized to delete this assignment (not form owner or admin).
    * `404 Not Found`: Assignment ID not found or already deleted.
        ```json
        { "error": "Form assignment not found or already deleted." }
        ```
    * `500 Internal Server Error`.

---
This guide should help you interact with the Form Assignments API using Postman.
