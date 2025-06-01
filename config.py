import logging
from logging.handlers import RotatingFileHandler

"""
ملف التكوين الرئيسي للتطبيق
---------------------------

يحتوي على جميع إعدادات التطبيق مثل:
- إعدادات قاعدة البيانات
- مفاتيح الأمان
- إعدادات التسجيل
- خيارات التحسين
"""

import os
from datetime import timedelta

class Config:
    # إعدادات Celery
    # IMPORTANT: For production, set CELERY_BROKER_URL and CELERY_RESULT_BACKEND via environment variables.
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0' # Default for dev
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/0' # Default for dev
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TIMEZONE = 'Asia/Riyadh'
    CELERY_ENABLE_UTC = True
    
    # إعدادات أساسية
    # IMPORTANT: SECRET_KEY must be set in the environment for production to ensure security.
    # Generate a strong, unique key and set it as an environment variable.
    SECRET_KEY = os.environ.get('SECRET_KEY')
    FLASK_APP = 'app.py'
    
    # إعدادات قاعدة البيانات
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True  # تمكين تسجيل الاستعلامات للتحسين
    SQLALCHEMY_ECHO = False  # تعطيل طباعة الاستعلامات في وضع الإنتاج
    
    # تحسين الأداء
    DATABASE_QUERY_TIMEOUT = 0.5  # الحد الأقصى لوقت الاستعلام (بالثواني)
    SLOW_DB_QUERY_TIME = 0.5  # وقت الاستعلام البطيء (للتسجيل)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # الحد الأقصى لحجم الملف (16 ميجابايت)
    
    # إعدادات الجلسة
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # إعدادات التسجيل
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s [%(levelname)s] %(message)s'
    LOG_FILE = 'logs/etmam.log'
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 ميجابايت
    LOG_BACKUP_COUNT = 10
    
    # إعدادات البريد الإلكتروني
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # إعدادات التخزين المؤقت
    CACHE_TYPE = 'redis'
    # IMPORTANT: For production, set REDIS_URL via environment variable.
    CACHE_REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0' # Default for dev
    CACHE_DEFAULT_TIMEOUT = 300
    
    # إعدادات الأمان
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    # IMPORTANT: SECURITY_PASSWORD_SALT must be set in the environment for production.
    # Generate a strong, unique salt and set it as an environment variable.
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT')
    
    # إعدادات تحميل الملفات
    # IMPORTANT: UPLOAD_FOLDER (e.g., 'app/uploads/') must NOT be publicly served by the webserver.
    # Files should be served via a controlled endpoint that checks permissions.
    UPLOAD_FOLDER = 'uploads' # Relative to app instance path, so 'app/uploads/'

    # Define allowed extensions by type of upload for more granular control.
    # IMPORTANT:
    # 1. Always use werkzeug.utils.secure_filename() on any user-provided filename before saving.
    # 2. Validate MIME types in addition to extensions in your upload handling logic.
    # 3. For sensitive files like executable scripts ('scripts'), ensure they are stored securely,
    #    with appropriate permissions, and ideally not directly executable from their stored location.
    #    Consider storing them outside the web root or in a database if appropriate.
    ALLOWED_EXTENSIONS_BY_TYPE = {
        'scripts': {'py', 'sh', 'js'},  # Example: Python, shell scripts, JavaScript
        'ebooks': {'pdf', 'epub', 'mobi'},       # Example: PDF, ePub, Mobi
        'databases': {'db', 'sqlite', 'sqlite3', 'csv', 'json', 'sql'}, # Example
        'general_text': {'txt', 'json', 'yaml', 'yml', 'md'} # For general text files, markdown
    }
    
    # إعدادات التحسين
    OPTIMIZE_DB_QUERIES = True
    USE_DB_INDEXES = True
    ENABLE_QUERY_CACHING = True
    
    # تعطيل حسابات المشرف العادي
    DISABLE_ADMIN = True  # سيتم استخدام هذا المتغير للتحكم في تفعيل/تعطيل حسابات المشرف
    
    @staticmethod
    def init_app(app):
        """تهيئة إضافية للتطبيق
        
        المعلمات:
            app: تطبيق Flask
        """
        # إنشاء مجلدات مطلوبة
        if not os.path.exists('logs'):
            os.mkdir('logs')
        if not os.path.exists('uploads'):
            os.mkdir('uploads')
            
        # إعداد التسجيل
        if not app.debug and not app.testing:
            log_level = getattr(logging, app.config['LOG_LEVEL'].upper(), logging.INFO)

            if app.config['LOG_TO_STDOUT']:
                stream_handler = logging.StreamHandler()
                stream_handler.setLevel(log_level)
                stream_handler.setFormatter(logging.Formatter(app.config['LOG_FORMAT']))
                app.logger.addHandler(stream_handler)
            else:
                if not os.path.exists('logs'): # This will be app/logs
                    os.mkdir('logs')
                file_handler = RotatingFileHandler(
                    app.config['LOG_FILE'], # This will be app/logs/etmam.log
                    maxBytes=app.config['LOG_MAX_SIZE'],
                    backupCount=app.config['LOG_BACKUP_COUNT']
                )
                file_handler.setFormatter(logging.Formatter(app.config['LOG_FORMAT']))
                file_handler.setLevel(log_level)
                app.logger.addHandler(file_handler)
                
            app.logger.setLevel(log_level)
            app.logger.info('بدء تشغيل نظام إتمام')

class DevelopmentConfig(Config):
    """إعدادات بيئة التطوير"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    TEMPLATES_AUTO_RELOAD = True

class ProductionConfig(Config):
    """إعدادات بيئة الإنتاج"""
    DEBUG = False
    TESTING = False
    SQLALCHEMY_ECHO = False
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT', 'True') # Default to True for prod if not set
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO') # Default to INFO for prod if not set
    
    # تحسينات الأمان
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    
    # تحسينات الأداء
    SQLALCHEMY_POOL_RECYCLE = 299
    SQLALCHEMY_POOL_TIMEOUT = 20
    SQLALCHEMY_POOL_SIZE = 30
    SQLALCHEMY_MAX_OVERFLOW = 10

class TestingConfig(Config):
    """إعدادات بيئة الاختبار"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False