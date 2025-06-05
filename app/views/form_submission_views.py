# app/views/form_submission_views.py
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.form_submission_controller import FormSubmissionController
from app.models.user import User as UserModel # Renamed to avoid conflict if User is used as var name
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging

logger = logging.getLogger(__name__)

form_submission_bp = Blueprint('form_submissions', __name__)

@form_submission_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.SUBMISSIONS)
def create_submission():
    """Create a new form submission"""
    try:
        current_user_jwt_identity = get_jwt_identity() # username string

        data = request.form.to_dict() if request.form else request.get_json()
        files = request.files.to_dict()

        if not data or 'form_id' not in data:
            return jsonify({"error": "form_id is required"}), 400

        answers_data = data.get('answers', [])
        # Ensure answers_data is a list
        if not isinstance(answers_data, list):
            try:
                # Attempt to parse if it's a JSON string representation of a list
                import json
                answers_data = json.loads(answers_data)
                if not isinstance(answers_data, list):
                    raise ValueError
            except (json.JSONDecodeError, ValueError, TypeError):
                logger.warning(f"Answers data is not a valid list or JSON list string: {answers_data}")
                answers_data = [] # Default to empty list if parsing fails or not a list

        for answer in answers_data:
            if answer.get('is_signature'):
                # Ensure question_id is a simple key, not nested if it's directly from form key
                question_id_for_file = answer.get('question_id', answer.get('id')) # Try common keys
                file_key = f"signature_{question_id_for_file}"
                if file_key in files:
                    answer['signature_file'] = files[file_key]
                elif str(question_id_for_file) in files: # Fallback if file key is just question_id
                    answer['signature_file'] = files[str(question_id_for_file)]


        submitted_at_str = data.get('submitted_at')
        submitted_at_dt = None
        if submitted_at_str:
            try:
                submitted_at_dt = datetime.fromisoformat(submitted_at_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid submitted_at format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"}), 400

        submission, error = FormSubmissionController.create_submission(
            form_id=int(data['form_id']),
            username=current_user_jwt_identity, # Pass username string
            answers_data=answers_data,
            submitted_at=submitted_at_dt
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify({
            "message": "Form submitted successfully",
            "submission": submission.to_dict()
        }), 201

    except Exception as e:
        logger.exception(f"Error creating submission: {str(e)}") # Use logger.exception for full traceback
        return jsonify({"error": "Internal server error"}), 500

@form_submission_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_all_submissions():
    """Get all submissions with filtering"""
    try:
        current_user_jwt_identity = get_jwt_identity()
        user_obj = AuthService.get_current_user(current_user_jwt_identity) # User object
        if not user_obj:
            return jsonify({"error": "Authenticated user not found"}), 401


        filters = {}
        form_id = request.args.get('form_id', type=int)
        if form_id:
            filters['form_id'] = form_id

        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        if start_date_str and end_date_str:
            try:
                filters['date_range'] = {
                    'start': datetime.fromisoformat(start_date_str.replace('Z', '+00:00')),
                    'end': datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                }
            except ValueError:
                return jsonify({"error": "Invalid date format for start_date or end_date. Use ISO format."}), 400
        
        # Pass the User OBJECT to the controller
        submissions = FormSubmissionController.get_all_submissions(user_obj, filters)

        return jsonify({
            'total_count': len(submissions),
            'filters_applied': filters,
            'submissions': [sub.to_dict() for sub in submissions]
        }), 200

    except Exception as e:
        logger.exception(f"Error getting submissions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@form_submission_bp.route('/compact', methods=['GET']) # This is your existing compact route
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_all_submissions_compact_list():
    """
    Get a compact list of submissions with filtering and sorting.
    Response attributes: id, form_id, form_title, submitted_at, submitted_by, 
                         answers_count, signatures_count, attachments_count (non-signatures).
    Query Parameters:
        - form_id (int, optional): Filter by form ID.
        - start_date (str, optional): Filter by submission start date (ISO format, e.g., YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ).
        - end_date (str, optional): Filter by submission end date (ISO format).
        - sort_by (str, optional): Field to sort by ('submitted_at', 'submitted_by', 'form_title'). Default: 'submitted_at'.
        - sort_order (str, optional): Sort order ('asc' or 'desc'). Default: 'desc'.
    """
    try:
        current_user_jwt_identity = get_jwt_identity()
        user_obj = AuthService.get_current_user(current_user_jwt_identity) 
        if not user_obj:
            return jsonify({"error": "Authenticated user not found"}), 401

        # Get filters from request.args
        form_id_filter = request.args.get('form_id', type=int) # Keep existing filter
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        sort_by = request.args.get('sort_by', default='submitted_at')
        sort_order = request.args.get('sort_order', default='desc').lower()

        # Validate sort_order
        if sort_order not in ['asc', 'desc']:
            return jsonify({"error": "Invalid sort_order. Must be 'asc' or 'desc'."}), 400
        
        # Validate sort_by
        valid_sort_fields = ['submitted_at', 'submitted_by', 'form_title']
        if sort_by not in valid_sort_fields:
            return jsonify({"error": f"Invalid sort_by field. Must be one of: {', '.join(valid_sort_fields)}"}), 400
        
        # Basic validation for date presence if one is provided
        if (start_date_str and not end_date_str) or (not start_date_str and end_date_str):
            return jsonify({"error": "Both start_date and end_date are required if one is provided for date filtering."}), 400

        # Call the updated controller method
        compact_submissions_data = FormSubmissionController.get_all_submissions_compact(
            user=user_obj, # Pass the User object
            start_date_str=start_date_str,
            end_date_str=end_date_str,
            sort_by=sort_by,
            sort_order=sort_order,
            form_id_filter=form_id_filter # Pass existing filter
        )
        # The controller now directly returns the list of dictionaries.

        # The original response structure had 'total_count', 'filters_applied', 'submissions'
        # We can maintain that if desired, or just return the list.
        # For consistency with the previous /forms/compact:
        return jsonify({
            'total_count': len(compact_submissions_data),
            'filters_applied': {
                'form_id': form_id_filter,
                'start_date': start_date_str,
                'end_date': end_date_str,
                'sort_by': sort_by,
                'sort_order': sort_order
            },
            'submissions': compact_submissions_data
        }), 200

    except Exception as e:
        logger.exception(f"Error getting compact submissions list: {str(e)}") # Use logger.exception for traceback
        return jsonify({"error": "Internal server error"}), 500
    
@form_submission_bp.route('/search', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS) # Adjust permission if needed
def search_form_submissions_view():
    """
    Search form submissions based on criteria related to their answers.
    Returns a compact list of matching submissions.
    
    Query Parameters:
        - form_id (int, optional): Filter by a specific form ID in conjunction with other search terms.
        - answer (str, optional): Search for text within the answer content (case-insensitive).
        - cell_content (str, optional): Search for text within table cell content (case-insensitive).
        - question (str, optional): Search for text within the question text of an answer (case-insensitive).
        - question_type (str, optional): Filter by the type of question associated with an answer (case-insensitive partial match).
    """
    try:
        current_user_jwt_identity = get_jwt_identity()
        user_obj = AuthService.get_current_user(current_user_jwt_identity)
        if not user_obj:
            return jsonify({"error": "Authenticated user not found"}), 401

        search_criteria = {}
        answer_query = request.args.get('answer')
        cell_content_query = request.args.get('cell_content')
        question_query = request.args.get('question')
        question_type_query = request.args.get('question_type')
        
        form_id_filter = request.args.get('form_id', type=int)

        if answer_query:
            search_criteria['answer'] = answer_query
        if cell_content_query:
            search_criteria['cell_content'] = cell_content_query
        if question_query:
            search_criteria['question'] = question_query
        if question_type_query:
            search_criteria['question_type'] = question_type_query
        
        # A search endpoint typically requires at least one search criterion for the "search" part.
        # The form_id_filter can be used in conjunction but shouldn't be the sole basis for this specific endpoint.
        if not search_criteria:
            return jsonify({"message": "Please provide at least one search criterion from: answer, cell_content, question, question_type."}), 400

        results = FormSubmissionController.search_submissions(
            user=user_obj,
            search_criteria=search_criteria,
            form_id_filter=form_id_filter
        )

        # The controller returns a list of dictionaries already.
        return jsonify({
            "search_criteria_applied": search_criteria,
            "form_id_filter_applied": form_id_filter,
            "total_results": len(results),
            "submissions": results # This is the list of compact submission dicts
        }), 200

    except Exception as e:
        logger.exception(f"Error in search_form_submissions_view: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@form_submission_bp.route('/batch', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_batch_form_submissions():
    """Get batch of form submissions with pagination"""
    try:
        page = request.args.get('page', type=int, default=1)
        per_page = request.args.get('per_page', type=int, default=50)
        
        include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        form_id = request.args.get('form_id', type=int)
        submitted_by = request.args.get('submitted_by') # username string
        
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        date_range = None
        if start_date_str and end_date_str:
            try:
                date_range = {
                    'start': datetime.fromisoformat(start_date_str.replace('Z', '+00:00')),
                    'end': datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                }
            except ValueError:
                return jsonify({"error": "Invalid date format for start_date or end_date. Use ISO format."}), 400
        
        current_user_jwt_identity = get_jwt_identity()
        user_obj = AuthService.get_current_user(current_user_jwt_identity) # User object
        if not user_obj:
             return jsonify({"error": "Authenticated user not found"}), 401
        
        total_count, form_submissions_data = FormSubmissionController.get_batch(
            page=page,
            per_page=per_page,
            include_deleted=include_deleted,
            form_id=form_id,
            submitted_by=submitted_by,
            date_range=date_range,
            current_user=user_obj # Pass User OBJECT
        )
        
        total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 0
        
        return jsonify({
            "metadata": {
                "total_items": total_count,
                "total_pages": total_pages,
                "current_page": page,
                "per_page": per_page,
                "filters_applied": { # Store original string dates for filters_applied if needed
                    "form_id": form_id,
                    "submitted_by": submitted_by,
                    "start_date": start_date_str,
                    "end_date": end_date_str
                }
            },
            "items": form_submissions_data # Controller now returns list of dicts
        }), 200
    except Exception as e:
        logger.exception(f"Error getting batch of form submissions: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

@form_submission_bp.route('/<int:submission_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_submission(submission_id):
    """Get a specific submission with its answers"""
    try:
        current_user_jwt_identity = get_jwt_identity() # username string

        # Corrected: Call FormSubmissionController.get_submission with current_user_identity
        submission_model = FormSubmissionController.get_submission(
            submission_id=submission_id,
            current_user_identity=current_user_jwt_identity
        )
        
        if not submission_model:
            return jsonify({"error": "Submission not found or access denied"}), 404

        user_obj = AuthService.get_current_user(current_user_jwt_identity) # User object for role name
        if not user_obj: # Defensive check
             return jsonify({"error": "Authenticated user not found for role check"}), 401

        # The RBAC for viewing the submission is now handled by FormSubmissionController.get_submission
        # If more granular checks were needed specific to this view, they could be here.
        # The existing access control block in the user's provided code might be redundant now
        # or needs to be re-evaluated against what FormSubmissionController.get_submission enforces.
        # For safety, one might re-verify, but it means duplicating logic.
        # Assuming FormSubmissionController.get_submission is the source of truth for access:

        # Get answers with access control
        answers, error = FormSubmissionController.get_submission_answers(
            submission_id=submission_id,
            current_user_identity=current_user_jwt_identity, # Pass username string
            user_role_name=user_obj.role.name if user_obj.role else None # Pass role name string
        )

        if error:
            return jsonify({"error": error}), 403 # Or appropriate code

        submission_data = submission_model.to_dict()
        submission_data['answers'] = answers

        return jsonify(submission_data), 200

    except Exception as e:
        logger.exception(f"Error getting submission {submission_id}: {str(e)}") # Use logger.exception
        return jsonify({"error": "Internal server error"}), 500
    
@form_submission_bp.route('/my-submissions', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view_own_submissions", entity_type=EntityType.SUBMISSIONS)
def get_my_submissions():
    """Get all submissions for the current user with filtering"""
    try:
        current_user_jwt_identity = get_jwt_identity() # username string
        
        filters = {}
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        if start_date_str:
            try:
                filters['start_date'] = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Invalid start_date format. Use ISO format."}), 400
        if end_date_str:
            try:
                filters['end_date'] = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Invalid end_date format. Use ISO format."}), 400
            
        form_id = request.args.get('form_id', type=int)
        if form_id:
            filters['form_id'] = form_id

        submissions_list, error = FormSubmissionController.get_user_submissions(
            username=current_user_jwt_identity, # username string
            filters=filters
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify({
            "total_count": len(submissions_list),
            "filters_applied": {
                "start_date": start_date_str, # Return original strings for applied filters
                "end_date": end_date_str,
                "form_id": form_id
            },
            "submissions": [sub.to_dict() for sub in submissions_list]
        }), 200

    except Exception as e:
        logger.exception(f"Error getting user submissions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_submission_bp.route('/<int:submission_id>/answers', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_submission_answers_route_view(submission_id): # Renamed function to avoid conflict
    """Get all answers for a specific submission"""
    try:
        current_user_jwt_identity = get_jwt_identity() # username string
        user_obj = AuthService.get_current_user(current_user_jwt_identity) # User object
        if not user_obj:
            return jsonify({"error": "Authenticated user not found"}), 401

        # First verify submission exists and check access by calling FormSubmissionController.get_submission
        submission_model_check = FormSubmissionController.get_submission(
            submission_id=submission_id,
            current_user_identity=current_user_jwt_identity # Pass username string
        )
        if not submission_model_check:
            return jsonify({"error": "Submission not found or access denied"}), 404
            
        # If submission is accessible, then call the controller method for getting answers
        answers, error = FormSubmissionController.get_submission_answers(
            submission_id=submission_id,
            current_user_identity=current_user_jwt_identity, # Pass username string
            user_role_name=user_obj.role.name if user_obj.role else None # Pass role name string
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify({
            'submission_id': submission_id,
            'total_answers': len(answers),
            'answers': answers
        }), 200

    except Exception as e:
        logger.exception(f"Error getting submission answers for {submission_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@form_submission_bp.route('/<int:submission_id>', methods=['PUT'])
@jwt_required()
@PermissionManager.require_permission(action="update", entity_type=EntityType.SUBMISSIONS)
def update_submission(submission_id):
    """Update an existing form submission"""
    try:
        current_user_jwt_identity = get_jwt_identity() # username string
        user_obj = AuthService.get_current_user(current_user_jwt_identity) # User object
        if not user_obj:
             return jsonify({"error": "Authenticated user not found"}), 401

        data = request.form.to_dict() if request.form else request.get_json()
        files = request.files.to_dict()

        if not data:
            return jsonify({"error": "No update data provided"}), 400

        answers_data = data.get('answers', [])
        if not isinstance(answers_data, list):
            try:
                import json
                answers_data = json.loads(answers_data)
                if not isinstance(answers_data, list):
                    raise ValueError
            except (json.JSONDecodeError, ValueError, TypeError):
                logger.warning(f"Answers data for update is not a valid list or JSON list string: {answers_data}")
                answers_data = []


        for answer in answers_data:
            if answer.get('is_signature'):
                question_id_for_file = answer.get('question_id', answer.get('id'))
                file_key = f"signature_{question_id_for_file}"
                if file_key in files:
                    answer['signature_file'] = files[file_key]
                elif str(question_id_for_file) in files:
                     answer['signature_file'] = files[str(question_id_for_file)]


        # Pass identity string and role name string to controller
        submission, error = FormSubmissionController.update_submission(
            submission_id=submission_id,
            current_user_identity=current_user_jwt_identity, # Pass username string
            user_role_name=user_obj.role.name if user_obj.role else None, # Pass role name string
            update_data=data,
            answers_data=answers_data
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify({
            "message": "Form submission updated successfully",
            "submission": submission.to_dict()
        }), 200

    except Exception as e:
        logger.exception(f"Error updating submission {submission_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@form_submission_bp.route('/<int:submission_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.SUBMISSIONS)
def delete_submission(submission_id):
    """Delete a submission with cascade soft delete"""
    try:
        current_user_jwt_identity = get_jwt_identity() # username string
        user_obj = AuthService.get_current_user(current_user_jwt_identity) # User object
        if not user_obj:
             return jsonify({"error": "Authenticated user not found"}), 401

        # Pass identity string and role name string to controller
        success, message = FormSubmissionController.delete_submission(
            submission_id=submission_id,
            current_user_identity=current_user_jwt_identity, # Pass username string
            user_role_name=user_obj.role.name if user_obj.role else None # Pass role name string
        )

        if not success:
            return jsonify({"error": message}), 400

        return jsonify({
            "message": message or "Submission deleted successfully", # Ensure message is not None
            "submission_id": submission_id
        }), 200

    except Exception as e:
        logger.exception(f"Error deleting submission {submission_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500