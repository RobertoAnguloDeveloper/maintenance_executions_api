# app/controllers/health_controller.py

from app.services.health_service import HealthService
import logging

logger = logging.getLogger(__name__)

class HealthController:
    @staticmethod
    def ping():
        """
        Simple ping endpoint to check if the server is running.
        
        Returns:
            dict: Contains status "pong" if server is running
        """
        return {"status": "pong", "message": "Server is running"}
    
    @staticmethod
    def get_health_status():
        """
        Get detailed health status of the server.
        
        Returns:
            dict: Health status information
        """
        try:
            return HealthService.get_health_status()
        except Exception as e:
            logger.error(f"Error getting health status: {str(e)}")
            return {
                "status": "error",
                "message": "Error retrieving health status",
                "timestamp": HealthService.get_system_health()["timestamp"]
            }