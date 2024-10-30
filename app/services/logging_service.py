import logging
from flask import current_app

class LoggingService:
    @staticmethod
    def setup_logging():
        logging.basicConfig(level=logging.INFO)
        file_handler = logging.FileHandler('app.log')
        file_handler.setLevel(logging.INFO)
        current_app.logger.addHandler(file_handler)

    @staticmethod
    def log_info(message):
        current_app.logger.info(message)

    @staticmethod
    def log_error(message):
        current_app.logger.error(message)