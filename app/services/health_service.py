# app/services/health_service.py

from sqlalchemy import text

import time
import logging
from datetime import datetime
import psutil  # You might need to install this package: pip install psutil

logger = logging.getLogger(__name__)

class HealthService:
    @staticmethod
    def get_system_health():
        """
        Get basic system health metrics.
        
        Returns:
            dict: Dictionary containing health metrics
        """
        try:
            return {
                "status": "online",
                "timestamp": datetime.utcnow().isoformat(),
                "server_time": time.time(),
                "cpu_usage": psutil.cpu_percent(interval=0.1),
                "memory_usage": psutil.virtual_memory().percent,
                "uptime": time.time() - psutil.boot_time()
            }
        except Exception as e:
            logger.error(f"Error getting system health: {str(e)}")
            return {
                "status": "degraded",
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Could not retrieve full system health"
            }
    
    @staticmethod
    def check_database_connection():
        """
        Check if the database connection is working.
        
        Returns:
            bool: True if database connection is working, False otherwise
        """
        from app import db
        
        try:
            # Use the text() function from sqlalchemy to create a textual SQL expression
            result = db.session.execute(text("SELECT 1")).scalar()
            return result == 1
        except Exception as e:
            logger.error(f"Database connection check failed: {str(e)}")
            return False
    
    @staticmethod
    def get_health_status():
        """
        Get overall health status combining different health checks.
        
        Returns:
            dict: Health status with various metrics
        """
        system_health = HealthService.get_system_health()
        db_status = HealthService.check_database_connection()
        
        return {
            **system_health,
            "database_connection": "healthy" if db_status else "unhealthy",
            "health_status": "healthy" if db_status and system_health["status"] == "online" else "degraded"
        }