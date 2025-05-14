from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.answer_submitted_controller import AnswerSubmittedController
from app.controllers.form_submission_controller import FormSubmissionController
from app.models.user import User
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging

logger = logging.getLogger(__name__)

answer_submitted_bp = Blueprint('answers-submitted', __name__)

@answer_submitted_bp.route('', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.SUBMISSIONS)
def create_answer_submitted():
    try:
        current_user = get_jwt_identity()
        
        data = request.form.to_dict() if request.form else request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ['form_submission_id', 'question_text', 'question_type_text', 'answer_text']
        if not all(field in data for field in required_fields):
            return jsonify({
                "error": "Missing required fields",
                "required_fields": required_fields
            }), 400

        # Extract question_order if provided
        question_order = None
        if 'question_order' in data:
            try:
                question_order = int(data['question_order'])
            except (ValueError, TypeError):
                return jsonify({"error": "question_order must be an integer"}), 400

        # Extract table-specific fields if necessary
        column = None
        row = None
        cell_content = None
        
        if data['question_type_text'] == 'table':
            # Additional validation for table-type questions
            if 'column' not in data or 'row' not in data:
                return jsonify({"error": "Column and row are required for table-type questions"}), 400
                
            column = int(data['column'])
            row = int(data['row'])
            cell_content = data.get('cell_content')

        answer_submitted, error = AnswerSubmittedController.create_answer_submitted(
            form_submission_id=int(data['form_submission_id']),
            question_text=data['question_text'],
            question_type_text=data['question_type_text'],
            answer_text=data['answer_text'],
            question_order=question_order,  # Added question_order
            current_user=current_user,
            column=column,
            row=row,
            cell_content=cell_content
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify({
            "message": "Answer submitted successfully",
            "answer_submitted": answer_submitted
        }), 201

    except Exception as e:
        logger.error(f"Error creating answer submission: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_submitted_bp.route('/bulk', methods=['POST'])
@jwt_required()
@PermissionManager.require_permission(action="create", entity_type=EntityType.SUBMISSIONS)
def bulk_create_answers_submitted():
    """Bulk create submitted answers"""
    try:
        current_user = get_jwt_identity()
        
        data = request.get_json()
        if not data or 'form_submission_id' not in data or 'submissions' not in data:
            return jsonify({
                "error": "Missing required fields: form_submission_id and submissions"
            }), 400

        # Validate each submission data
        for submission in data['submissions']:
            if not all(key in submission for key in ['question_text', 'question_type_text', 'answer_text']):
                return jsonify({
                    "error": "Each submission must contain question_text, question_type_text, and answer_text"
                }), 400
                
            # Additional validation for table-type questions
            if submission['question_type_text'] == 'table':
                if 'column' not in submission or 'row' not in submission:
                    return jsonify({"error": "Column and row are required for table-type questions"}), 400
            
            # Validate question_order if present
            if 'question_order' in submission:
                try:
                    submission['question_order'] = int(submission['question_order'])
                except (ValueError, TypeError):
                    return jsonify({"error": "question_order must be an integer"}), 400

        submissions, error = AnswerSubmittedController.bulk_create_answers_submitted(
            form_submission_id=int(data['form_submission_id']),
            submissions_data=data['submissions'],
            current_user=current_user
        )
        
        if error:
            return jsonify({"error": error}), 400
            
        # Convert AnswerSubmitted objects to dictionaries
        submissions_data = []
        if submissions:
            for submission in submissions:
                if hasattr(submission, 'to_dict'):
                    submissions_data.append(submission.to_dict())
                else:
                    submission_dict = {
                        'id': submission.id,
                        'question': submission.question,
                        'question_type': submission.question_type,
                        'answer': submission.answer,
                        'form_submission_id': submission.form_submission_id,
                        'created_at': submission.created_at.isoformat() if submission.created_at else None,
                        'updated_at': submission.updated_at.isoformat() if submission.updated_at else None
                    }
                    
                    # Add question_order if available
                    if hasattr(submission, 'question_order'):
                        submission_dict['question_order'] = submission.question_order
                    
                    # Add table-specific fields if applicable
                    if submission.question_type == 'table':
                        submission_dict['column'] = submission.column
                        submission_dict['row'] = submission.row
                        submission_dict['cell_content'] = submission.cell_content
                        
                    submissions_data.append(submission_dict)
            
        return jsonify({
            "message": "Answers submitted successfully",
            "submissions": submissions_data
        }), 201
        
    except Exception as e:
        logger.error(f"Error in bulk create answers submitted: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_submitted_bp.route('', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_all_answers_submitted():
    """Get all answers submitted with filters"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # Build filters from query parameters
        filters = {}
        
        # Form submission filter
        form_submission_id = request.args.get('form_submission_id', type=int)
        if form_submission_id:
            filters['form_submission_id'] = form_submission_id

        # Question type filter
        question_type = request.args.get('question_type')
        if question_type:
            filters['question_type'] = question_type
            
        # Question order filter
        question_order = request.args.get('question_order', type=int)
        if question_order is not None:
            filters['question_order'] = question_order
            
        # Table-specific filters
        column = request.args.get('column', type=int)
        if column is not None:
            filters['column'] = column
            
        row = request.args.get('row', type=int)
        if row is not None:
            filters['row'] = row

        # Date range filters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if start_date and end_date:
            filters['date_range'] = {
                'start': start_date,
                'end': end_date
            }

        answers = AnswerSubmittedController.get_all_answers_submitted(user, filters)

        return jsonify({
            'total_count': len(answers),
            'filters_applied': filters,
            'answers': answers
        }), 200

    except Exception as e:
        logger.error(f"Error getting answers submitted: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@answer_submitted_bp.route('/batch', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_batch_answers_submitted():
    """Get batch of submitted answers with pagination"""
    try:
        # Get pagination parameters
        page = request.args.get('page', type=int, default=1)
        per_page = request.args.get('per_page', type=int, default=50)
        
        # Get filter parameters
        include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        form_submission_id = request.args.get('form_submission_id', type=int)
        question_type = request.args.get('question_type')
        question_order = request.args.get('question_order', type=int)
        
        # Table-specific filters
        column = request.args.get('column', type=int)
        row = request.args.get('row', type=int)
        
        # Apply role-based access control
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Call controller method with pagination
        total_count, answers_submitted = AnswerSubmittedController.get_batch(
            page=page,
            per_page=per_page,
            include_deleted=include_deleted,
            form_submission_id=form_submission_id,
            question_type=question_type,
            question_order=question_order,
            column=column,
            row=row,
            current_user=user
        )
        
        # Calculate total pages
        total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 0
        
        return jsonify({
            "metadata": {
                "total_items": total_count,
                "total_pages": total_pages,
                "current_page": page,
                "per_page": per_page,
                "filters_applied": {
                    "form_submission_id": form_submission_id,
                    "question_type": question_type,
                    "question_order": question_order,
                    "column": column,
                    "row": row
                }
            },
            "items": answers_submitted
        }), 200

    except Exception as e:
        logger.error(f"Error getting batch of submitted answers: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

@answer_submitted_bp.route('/<int:answer_submitted_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_answer_submitted(answer_submitted_id):
    """Get a specific submitted answer"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        answer_submitted, error = AnswerSubmittedController.get_answer_submitted(
            answer_submitted_id=answer_submitted_id,
            current_user=current_user,
            user_role=user.role.name
        )

        if error:
            return jsonify({"error": error}), 404

        return jsonify(answer_submitted), 200

    except Exception as e:
        logger.error(f"Error getting answer submitted {answer_submitted_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_submitted_bp.route('/submission/<int:submission_id>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_answers_by_submission(submission_id):
    """Get all submitted answers for a form submission"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        # First verify submission exists and check access
        submission = FormSubmissionController.get_submission(submission_id)
        if not submission:
            return jsonify({"error": "Form submission not found"}), 404

        # Access control
        if not user.role.is_super_user:
            if user.role.name in [RoleType.SITE_MANAGER, RoleType.SUPERVISOR]:
                # Verify submitter is in the same environment
                submitter = User.query.filter_by(username=submission.submitted_by).first()
                if not submitter or submitter.environment_id != user.environment_id:
                    return jsonify({"error": "Unauthorized access"}), 403
            elif submission.submitted_by != current_user:
                # Regular users can only see their own submissions
                return jsonify({"error": "Unauthorized access"}), 403

        answers, error = AnswerSubmittedController.get_answers_by_submission(
            submission_id=submission_id,
            current_user=current_user,
            user_role=user.role.name
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify({
            'submission_id': submission_id,
            'total_answers': len(answers),
            'answers': answers
        }), 200

    except Exception as e:
        logger.error(f"Error getting answers for submission {submission_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_submitted_bp.route('/table/<int:submission_id>/<path:question_text>', methods=['GET'])
@jwt_required()
@PermissionManager.require_permission(action="view", entity_type=EntityType.SUBMISSIONS)
def get_table_structure(submission_id, question_text):
    """Get the structure of a table question's answers"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        table_structure, error = AnswerSubmittedController.get_table_structure(
            submission_id=submission_id,
            question_text=question_text,
            current_user=current_user,
            user_role=user.role.name
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify({
            'submission_id': submission_id,
            'question_text': question_text,
            'table_structure': table_structure
        }), 200

    except Exception as e:
        logger.error(f"Error getting table structure for submission {submission_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_submitted_bp.route('/<int:answer_submitted_id>', methods=['PUT'])
@jwt_required()
@PermissionManager.require_permission(action="update", entity_type=EntityType.SUBMISSIONS)
def update_answer_submitted(answer_submitted_id):
    """Update a submitted answer"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        data = request.get_json()
        if not data:
            return jsonify({"error": "No update data provided"}), 400

        # Get the existing answer to check its type
        existing_answer, error = AnswerSubmittedController.get_answer_submitted(
            answer_submitted_id=answer_submitted_id,
            current_user=current_user,
            user_role=user.role.name
        )
        
        if error:
            return jsonify({"error": error}), 404

        # Extract question_order if provided
        question_order = None
        if 'question_order' in data:
            try:
                question_order = int(data['question_order'])
            except (ValueError, TypeError):
                return jsonify({"error": "question_order must be an integer"}), 400

        # Extract table-specific fields if necessary
        column = None
        row = None
        cell_content = None
        
        if existing_answer.get('question_type') == 'table':
            # For table-type questions, validate and extract table fields
            if 'column' in data:
                column = int(data['column'])
            if 'row' in data:
                row = int(data['row'])
            if 'cell_content' in data:
                cell_content = data.get('cell_content')

        updated_answer, error = AnswerSubmittedController.update_answer_submitted(
            answer_submitted_id=answer_submitted_id,
            answer_text=data.get('answer_text'),
            question_order=question_order,
            column=column,
            row=row,
            cell_content=cell_content,
            current_user=current_user,
            user_role=user.role.name
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify({
            "message": "Answer submission updated successfully",
            "answer_submitted": updated_answer
        }), 200

    except Exception as e:
        logger.error(f"Error updating answer submitted {answer_submitted_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@answer_submitted_bp.route('/<int:answer_submitted_id>', methods=['DELETE'])
@jwt_required()
@PermissionManager.require_permission(action="delete", entity_type=EntityType.SUBMISSIONS)
def delete_answer_submitted(answer_submitted_id):
    """Delete a submitted answer"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)

        success, message = AnswerSubmittedController.delete_answer_submitted(
            answer_submitted_id=answer_submitted_id,
            current_user=current_user,
            user_role=user.role.name
        )

        if not success:
            return jsonify({"error": message}), 400

        return jsonify({
            "message": message,
            "deleted_id": answer_submitted_id
        }), 200

    except Exception as e:
        logger.error(f"Error deleting answer submitted {answer_submitted_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500