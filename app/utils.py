import os
import smtplib
from email.mime.text import MIMEText
from functools import wraps
from flask import current_app, flash, redirect, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename
from .tasks import send_email_task

def send_email(subject, body, to_email=None):
    """إرسال بريد إلكتروني باستخدام نظام المهام غير المتزامنة"""
    try:
        # إرسال المهمة إلى Celery
        send_email_task.delay(
            subject=subject,
            body=body,
            to_email=to_email or current_app.config['ADMIN_EMAIL'],
            config={
                'SMTP_SERVER': current_app.config['SMTP_SERVER'],
                'SMTP_PORT': current_app.config['SMTP_PORT'],
                'SMTP_USERNAME': current_app.config['SMTP_USERNAME'],
                'SMTP_PASSWORD': current_app.config['SMTP_PASSWORD']
            }
        )
        return True
    except Exception as e:
        print(f"خطأ في جدولة مهمة البريد: {str(e)}")
        return False

def admin_required(f):
    """مصمم للتحقق من صلاحيات المشرف"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("غير مصرح لك بالوصول إلى هذه الصفحة")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename, type_key):
    '''
    Checks if a filename has an allowed extension for a given type.
    Args:
        filename (str): The name of the file.
        type_key (str): The key corresponding to the upload type in
                        current_app.config['ALLOWED_EXTENSIONS_BY_TYPE'].
    Returns:
        bool: True if the file is allowed, False otherwise.
    '''
    if not filename:
        return False
    allowed_extensions_map = current_app.config.get('ALLOWED_EXTENSIONS_BY_TYPE', {})
    allowed_set = allowed_extensions_map.get(type_key, set())
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_set

def get_secure_path(filename, type_key, base_folder=None):
    '''
    Generates a secure filename and constructs a path within the UPLOAD_FOLDER.
    Args:
        filename (str): The original filename.
        type_key (str): The key for allowed extensions, also used as subfolder.
        base_folder (str, optional): Base upload folder. Defaults to UPLOAD_FOLDER from config.
    Returns:
        str: Full path to save the file or None if type_key is invalid or file not allowed.
    '''
    if not allowed_file(filename, type_key):
        return None

    s_filename = secure_filename(filename)

    if base_folder is None:
        base_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads') # 'app/uploads'

    # Create a subfolder based on type_key for organization
    target_folder = os.path.join(base_folder, type_key)
    if not os.path.exists(target_folder):
        os.makedirs(target_folder, exist_ok=True) # exist_ok=True for safety

    return os.path.join(target_folder, s_filename)

def create_script_folder(user_id):
    """إنشاء مجلد للمستخدم لتخزين السكربتات"""
    folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], str(user_id))
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
    """تنسيق التاريخ والوقت"""
    if value is None:
        return ""
    return value.strftime(format)

def get_script_path(user_id, script_name):
    """الحصول على المسار الكامل للسكربت"""
    return os.path.join(create_script_folder(user_id), script_name)

def validate_script_content(content):
    """التحقق من محتوى السكربت والتأكد من أنه آمن"""
    # قائمة الكلمات المحظورة التي قد تشكل خطراً
    forbidden_words = [
        'os.system', 'subprocess', 'eval', 'exec',
        'import os', 'import subprocess', '__import__',
        'open(', 'file.', 'socket.', 'sys.'
    ]

    content_lower = content.lower()
    for word in forbidden_words:
        if word.lower() in content_lower:
            return False, f"الكلمة المحظورة: {word}"

    return True, "السكربت آمن"

def send_email_direct(subject, body, to_email):
    """Sends an email directly using smtplib. (Moved from app.py)"""
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        # Use MAIL_DEFAULT_SENDER from config, or fallback to MAIL_USERNAME if not set
        msg['From'] = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config['MAIL_USERNAME']
        msg['To'] = to_email

        # Ensure MAIL_PORT is an integer
        mail_port = int(current_app.config.get('MAIL_PORT', 587)) # Default to 587 if not set

        # Determine SMTP class based on whether TLS or SSL is preferred.
        if current_app.config.get('MAIL_USE_TLS'): # Assuming this implies SSL for port 465 or STARTTLS for 587
            if mail_port == 465: # Typically SSL
                with smtplib.SMTP_SSL(current_app.config['MAIL_SERVER'], mail_port) as server:
                    server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
                    server.send_message(msg)
            else: # Typically STARTTLS for other ports like 587
                with smtplib.SMTP(current_app.config['MAIL_SERVER'], mail_port) as server:
                    server.starttls()
                    server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
                    server.send_message(msg)
        else: # Plain SMTP (usually port 25, less common for new setups)
            with smtplib.SMTP(current_app.config['MAIL_SERVER'], mail_port) as server:
                server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
                server.send_message(msg)

        current_app.logger.info(f"Email (direct) sent successfully to {to_email} with subject: {subject}")
        return True
    except Exception as e:
        current_app.logger.error(f"Direct email sending failed to {to_email}: {e}", exc_info=True)
        return False