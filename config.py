import os
import datetime
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'ku_voting_super_secret_key_2026_kampala_university')
    
    # Session Security
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(
        minutes=int(os.getenv('PERMANENT_SESSION_LIFETIME_MINUTES', '30'))
    )
    SESSION_COOKIE_HTTPONLY = os.getenv('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    
    # File Uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', str(5 * 1024 * 1024))) # 5MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'svg'}

    # Database Configuration
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
    DB_PORT = os.getenv('DB_PORT', '3306')
    DB_NAME = os.getenv('DB_NAME', 'ku_voting')
    
    _mysql_uri = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    _sqlite_uri = f"sqlite:///{os.path.join(BASE_DIR, 'ku_voting.db')}"
    
    direct_url = os.getenv('DATABASE_URL')
    if direct_url:
        SQLALCHEMY_DATABASE_URI = direct_url
    else:
        # Check if MySQL is accessible
        import pymysql
        try:
            conn = pymysql.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                port=int(DB_PORT),
                connect_timeout=2
            )
            # Check or create database if necessary
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.close()
            SQLALCHEMY_DATABASE_URI = _mysql_uri
            DB_ENGINE_NAME = "MySQL"
        except Exception as e:
            # Graceful fallback to SQLite for local development
            SQLALCHEMY_DATABASE_URI = _sqlite_uri
            DB_ENGINE_NAME = "SQLite (Local Fallback)"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    } if 'mysql' in SQLALCHEMY_DATABASE_URI else {}

    # University specific details
    UNIVERSITY_NAME = "Kampala University"
    UNIVERSITY_ABBR = "KU"
    CAMPUSES = [
        "Ggaba (Main Campus)",
        "Mutundwe Campus",
        "Luweero Campus",
        "Jinja Campus",
        "Masaka Campus"
    ]
    FACULTIES = [
        "Faculty of Computer Science and Information Technology",
        "Faculty of Business Administration & Management",
        "Faculty of Education",
        "Faculty of Arts & Social Sciences",
        "Faculty of Natural Sciences",
        "Faculty of Health Sciences"
    ]

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
