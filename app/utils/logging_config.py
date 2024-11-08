# app/utils/logging_config.py

import logging
import os
from datetime import datetime
from pathlib import Path

def setup_logging():
    """Configure logging for the application"""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f'app_{datetime.now():%Y%m%d}.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Set SQLAlchemy logging level
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)