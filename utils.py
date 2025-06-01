import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
from flask import current_app, flash, redirect, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename
from tasks import send_email_task
from dotenv import load_dotenv

load_dotenv()

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
    """
    Send email using SMTP
    """
    try:
        # Get email settings from environment variables
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        from_email = os.getenv('FROM_EMAIL', smtp_username)

        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject

        # Add body
        msg.attach(MIMEText(body, 'plain'))

        # Create SMTP session
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)

        # Send email
        server.send_message(msg)
        server.quit()

        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False