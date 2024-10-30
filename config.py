import os
from dotenv import load_dotenv

load_dotenv()
    
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'Angulo73202647'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://rangulot:plg-cmms-2024@localhost/maintenance_executions'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'Angulo73202647'
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour