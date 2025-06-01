"""
تنفيذ المهام غير المتزامنة في النظام
------------------------------------

يحتوي هذا الملف على تعريفات المهام التي تنفذ في الخلفية باستخدام Celery
"""

from celery import Celery
import smtplib
from email.mime.text import MIMEText
from flask import current_app

# Import the Celery app instance from __init__.py
# This assumes __init__.py makes 'celery' available for import,
# or tasks are defined after app creation and celery initialization.
# A common pattern is to have a celery_worker.py that imports the app and celery instance.
# For now, we assume 'celery' from __init__ can be imported.
from __init__ import celery # Import the celery instance from the main app package
from utils.notifications import send_product_delivery_email, send_whatsapp_notification
import logging

logger = logging.getLogger(__name__)

# The existing send_email_task might need to be refactored or removed
# if it's replaced by the Flask-Mail based one.
# For now, I will comment it out to avoid conflict and focus on new tasks.
# @celery.task(bind=True, max_retries=3)
# def send_email_task(self, subject, body, to_email, config=None):
#     """
#     مهمة إرسال البريد الإلكتروني بشكل غير متزامن
#     ... (original implementation) ...
#     """
#     try:
#         # ... (original implementation) ...
#         pass # Original implementation commented out
#     except Exception as e:
#         retry_in = 60 * (self.request.retries + 1)
#         self.retry(exc=e, countdown=retry_in)


@celery.task(bind=True, max_retries=3, default_retry_delay=60) # Added default_retry_delay
def task_send_delivery_email(self, user_email, user_name, product_name, product_type, delivery_info):
    """
    Celery task to send a product delivery email using Flask-Mail.
    """
    try:
        logger.info(f"Task: Sending delivery email to {user_email} for {product_name}")
        success = send_product_delivery_email(user_email, user_name, product_name, product_type, delivery_info)
        if not success:
            logger.warning(f"send_product_delivery_email reported failure for {user_email}, product {product_name}. Retrying if applicable.")
            # You might want to raise an exception to trigger Celery retry based on 'success'
            # For example: if not success: raise Exception("Failed to send email via utility")
        return success
    except Exception as e:
        logger.error(f"Exception in task_send_delivery_email for {user_email}: {e}", exc_info=True)
        self.retry(exc=e)


@celery.task(bind=True, max_retries=3, default_retry_delay=60) # Added default_retry_delay
def task_send_whatsapp_notification(self, user_phone, message_body):
    """
    Celery task to send a WhatsApp notification (placeholder).
    """
    try:
        logger.info(f"Task: Sending WhatsApp notification to {user_phone}")
        success = send_whatsapp_notification(user_phone, message_body)
        # Similar to email, handle 'success' for retry logic if needed
        return success
    except Exception as e:
        logger.error(f"Exception in task_send_whatsapp_notification for {user_phone}: {e}", exc_info=True)
        self.retry(exc=e)