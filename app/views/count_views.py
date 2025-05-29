# app/views/count_views.py

from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import inspect, text
from sqlalchemy.orm import class_mapper
from app import db
from app.models.user import User
from app.services.auth_service import AuthService
from app.utils.permission_manager import PermissionManager, EntityType, RoleType
import logging
import importlib
import os
from pathlib import Path

logger = logging.getLogger(__name__)

count_bp = Blueprint('counts', __name__)

class DynamicModelLoader:
    """Dynamically load all models from the models directory"""
    
    _models_cache = None
    
    @classmethod
    def get_all_models(cls):
        """Get all SQLAlchemy models dynamically with caching"""
        if cls._models_cache is not None:
            return cls._models_cache
            
        models = {}
        models_dir = Path(__file__).parent.parent / 'models'
        
        # Get all Python files in the models directory
        for file in models_dir.glob('*.py'):
            if file.name.startswith('__'):
                continue
                
            module_name = f"app.models.{file.stem}"
            try:
                module = importlib.import_module(module_name)
                
                # Find all classes that are SQLAlchemy models
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (hasattr(attr, '__class__') and 
                        hasattr(attr, '__tablename__') and 
                        hasattr(attr, 'query')):
                        # Use the table name as the key
                        table_name = attr.__tablename__
                        models[table_name] = attr
            except Exception as e:
                logger.warning(f"Could not load module {module_name}: {str(e)}")
        
        cls._models_cache = models
        return models

    @staticmethod
    def get_model_by_table_name(table_name):
        """Get a model class by its table name"""
        models = DynamicModelLoader.get_all_models()
        return models.get(table_name)

class DynamicPermissionChecker:
    """Dynamically determine permissions based on model relationships"""
    
    @staticmethod
    def can_view_entity(user, model, table_name):
        """Determine if user can view this entity based on relationships and fields"""
        # Admin users can see everything
        if user.role.is_super_user:
            return True
        
        # Check if model has relationships that indicate permission requirements
        mapper = class_mapper(model)
        
        # Analyze the model's relationships and columns
        has_user_relationship = False
        has_form_relationship = False
        has_role_relationship = False
        has_environment_relationship = False
        
        # Check columns
        for column in mapper.columns:
            column_name = column.name
            if column_name in ['user_id', 'created_by', 'submitted_by']:
                has_user_relationship = True
            elif column_name == 'form_id':
                has_form_relationship = True
            elif column_name == 'role_id':
                has_role_relationship = True
            elif column_name == 'environment_id':
                has_environment_relationship = True
        
        # Check relationships
        for rel in mapper.relationships:
            if rel.target.name in ['users', 'user', 'creator', 'submitted_by']:
                has_user_relationship = True
            elif rel.target.name in ['forms', 'form']:
                has_form_relationship = True
            elif rel.target.name in ['roles', 'role']:
                has_role_relationship = True
            elif rel.target.name in ['environments', 'environment']:
                has_environment_relationship = True
        
        # For now, allow viewing if user has any role
        # You can make this more restrictive based on your needs
        return True

class DynamicQueryFilter:
    """Apply dynamic filters based on model structure and user permissions"""
    
    @staticmethod
    def apply_filters(query, model, table_name, user, current_user_id, include_deleted=False):
        """Apply appropriate filters based on model structure"""
        
        # Get model mapper to inspect columns and relationships
        mapper = class_mapper(model)
        column_names = [col.name for col in mapper.columns]
        
        # Apply soft delete filter if applicable
        if 'is_deleted' in column_names and not include_deleted:
            query = query.filter(model.is_deleted == False)
        
        # If admin, no further filtering needed
        if user.role.is_super_user:
            return query
        
        # Apply filters based on model structure
        query = DynamicQueryFilter._apply_relationship_filters(
            query, model, mapper, column_names, user, current_user_id
        )
        
        return query
    
    @staticmethod
    def _apply_relationship_filters(query, model, mapper, column_names, user, current_user_id):
        """Apply filters based on relationships and columns"""
        
        # Check for direct user relationship
        if 'submitted_by' in column_names:
            # For technician role, filter by their submissions
            if hasattr(user.role, 'name') and user.role.name == RoleType.TECHNICIAN:
                query = query.filter(model.submitted_by == current_user_id)
        
        # Check for environment-based filtering
        if 'environment_id' in column_names:
            query = query.filter(model.environment_id == user.environment_id)
        
        # Check for role-based filtering
        if 'is_super_user' in column_names:
            query = query.filter(model.is_super_user == False)
        
        # Check for public/private filtering
        if 'is_public' in column_names:
            # For forms, allow public or same environment
            if 'user_id' in column_names or 'created_by' in column_names:
                creator_field = 'user_id' if 'user_id' in column_names else 'created_by'
                User_model = DynamicModelLoader.get_model_by_table_name('users')
                query = query.filter(
                    (model.is_public == True) | 
                    (getattr(model, creator_field).has(User_model.environment_id == user.environment_id))
                )
        
        # Handle related tables through foreign keys
        for rel in mapper.relationships:
            rel_mapper = rel.mapper
            rel_column_names = [col.name for col in rel_mapper.columns]
            
            # If related to forms, apply form filtering
            if rel.target.name == 'forms' and 'form_id' in column_names:
                Form_model = DynamicModelLoader.get_model_by_table_name('forms')
                User_model = DynamicModelLoader.get_model_by_table_name('users')
                if Form_model and User_model:
                    query = query.join(Form_model).filter(
                        (Form_model.is_public == True) | 
                        (Form_model.user_id.has(User_model.environment_id == user.environment_id))
                    )
            
            # If related to form_submissions, apply submission filtering
            elif rel.target.name == 'form_submissions' and 'form_submission_id' in column_names:
                FormSubmission_model = DynamicModelLoader.get_model_by_table_name('form_submissions')
                if FormSubmission_model:
                    if hasattr(user.role, 'name') and user.role.name == RoleType.TECHNICIAN:
                        query = query.join(FormSubmission_model).filter(
                            FormSubmission_model.submitted_by == current_user_id
                        )
                    else:
                        # For other roles, filter by environment through forms
                        Form_model = DynamicModelLoader.get_model_by_table_name('forms')
                        User_model = DynamicModelLoader.get_model_by_table_name('users')
                        if Form_model and User_model:
                            query = query.join(FormSubmission_model).join(Form_model).join(
                                User_model, Form_model.user_id == User_model.id
                            ).filter(User_model.environment_id == user.environment_id)
            
            # If related to roles, filter super user roles
            elif rel.target.name == 'roles' and 'role_id' in column_names:
                Role_model = DynamicModelLoader.get_model_by_table_name('roles')
                if Role_model:
                    query = query.join(Role_model).filter(Role_model.is_super_user == False)
        
        return query

@count_bp.route('/<entity>', methods=['GET'])
@jwt_required()
def count_entity(entity):
    """Dynamically count any entity based on the table name"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Convert entity name to table name (e.g., 'form-submissions' -> 'form_submissions')
        table_name = entity.replace('-', '_')
        
        # Get the model
        model = DynamicModelLoader.get_model_by_table_name(table_name)
        if not model:
            return jsonify({"error": f"Entity '{entity}' not found"}), 404
        
        # Check if user can view this entity
        if not DynamicPermissionChecker.can_view_entity(user, model, table_name):
            return jsonify({"error": "Permission denied"}), 403
        
        # Check if user can see deleted records (admin only)
        include_deleted = False
        if user.role.is_super_user:
            include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        
        # Build and filter the query
        query = model.query
        query = DynamicQueryFilter.apply_filters(
            query, model, table_name, user, current_user, include_deleted
        )
        
        # Get the count
        count = query.count()
        
        return jsonify({
            "entity": entity,
            "count": count,
            "include_deleted": include_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting {entity} count: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@count_bp.route('', methods=['GET'])
@jwt_required()
def count_all_entities():
    """Dynamically get counts for all entities based on user permissions"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only admins can see counts with deleted records
        include_deleted = False
        if user.role.is_super_user:
            include_deleted = request.args.get('include_deleted', '').lower() == 'true'
        
        # Get all models
        models = DynamicModelLoader.get_all_models()
        
        # Initialize counts dictionary
        counts = {}
        
        # Process each model
        for table_name, model in models.items():
            # Skip special tables that don't follow standard patterns
            if table_name in ['token_blocklist', 'alembic_version']:
                continue
            
            # Check if user can view this entity
            if not DynamicPermissionChecker.can_view_entity(user, model, table_name):
                counts[table_name] = 0
                continue
            
            try:
                # Build and filter the query
                query = model.query
                query = DynamicQueryFilter.apply_filters(
                    query, model, table_name, user, current_user, include_deleted
                )
                
                # Get the count
                counts[table_name] = query.count()
                
            except Exception as e:
                logger.warning(f"Could not count {table_name}: {str(e)}")
                counts[table_name] = 0
        
        return jsonify(counts), 200
        
    except Exception as e:
        logger.error(f"Error getting aggregated counts: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@count_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_database_stats():
    """Get detailed database statistics including active and deleted rows"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Only admins can see detailed stats
        if not user.role.is_super_user:
            return jsonify({"error": "Permission denied"}), 403
        
        # Get all models
        models = DynamicModelLoader.get_all_models()
        
        stats = {
            "database_info": {
                "name": db.engine.url.database,
                "dialect": db.engine.dialect.name,
                "total_tables": len(models)
            },
            "tables": {}
        }
        
        for table_name, model in models.items():
            try:
                # Get column information
                mapper = class_mapper(model)
                columns = []
                for col in mapper.columns:
                    columns.append({
                        "name": col.name,
                        "type": str(col.type),
                        "nullable": col.nullable,
                        "primary_key": col.primary_key,
                        "default": str(col.default) if col.default else "None"
                    })
                
                # Get row counts
                total = model.query.count()
                
                # Active and deleted counts if applicable
                if hasattr(model, 'is_deleted'):
                    active = model.query.filter_by(is_deleted=False).count()
                    deleted = model.query.filter_by(is_deleted=True).count()
                else:
                    active = total
                    deleted = 0
                
                # Get foreign keys
                foreign_keys = []
                for fk in mapper.tables[0].foreign_keys:
                    foreign_keys.append({
                        "constrained_columns": [fk.parent.name],
                        "referred_table": fk.column.table.name,
                        "referred_columns": [fk.column.name]
                    })
                
                stats["tables"][table_name] = {
                    "columns": columns,
                    "total_rows": total,
                    "active_rows": active,
                    "deleted_rows": deleted,
                    "foreign_keys": foreign_keys,
                    "primary_keys": [col.name for col in mapper.columns if col.primary_key]
                }
                
            except Exception as e:
                logger.warning(f"Could not get stats for {table_name}: {str(e)}")
                stats["tables"][table_name] = {
                    "error": str(e)
                }
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting database stats: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@count_bp.route('/tables', methods=['GET'])
@jwt_required()
def list_available_tables():
    """List all available tables/entities"""
    try:
        current_user = get_jwt_identity()
        user = AuthService.get_current_user(current_user)
        
        # Get all models
        models = DynamicModelLoader.get_all_models()
        
        # Build list of tables with access info
        tables = []
        for table_name, model in models.items():
            if table_name in ['token_blocklist', 'alembic_version']:
                continue
                
            can_view = DynamicPermissionChecker.can_view_entity(user, model, table_name)
            
            # Convert table_name to API-friendly format
            api_name = table_name.replace('_', '-')
            
            tables.append({
                "table_name": table_name,
                "api_endpoint": f"/api/counts/{api_name}",
                "can_view": can_view,
                "has_soft_delete": hasattr(model, 'is_deleted')
            })
        
        return jsonify({
            "tables": sorted(tables, key=lambda x: x['table_name']),
            "total": len(tables)
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing tables: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500