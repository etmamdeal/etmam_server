from flask import Blueprint, jsonify, render_template, redirect, url_for, request, flash, current_app, abort # Added current_app, abort
from flask_login import login_required, current_user, login_user, logout_user
from flask_babel import gettext as _ # Import gettext
import os
from functools import wraps
from models import User, db, Product, Subscription, UserScript, ProductType # Import necessary models
from datetime import datetime # Import datetime
from flask import send_from_directory # Import send_from_directory

# إنشاء Blueprint
bp = Blueprint('main', __name__)

# تعريف decorator للتحقق من صلاحيات المشرف (API specific)
def api_super_admin_required(f): # Renamed
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_super_admin:
            return jsonify({'error': _('غير مصرح لك بالوصول')}), 403 # Wrapped string
        return f(*args, **kwargs)
    return decorated_function

from auth import super_admin_required as ui_super_admin_required # Import UI version

# الصفحة الرئيسية
@bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_super_admin:
            return redirect(url_for('main.super_admin_control'))
        elif current_user.is_admin:
            return redirect(url_for('main.admin_dashboard'))
        else:
            return redirect(url_for('main.client_dashboard'))
    return render_template('index.html')

# صفحة تسجيل الدخول
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(_('Login successful'), 'success') # Example: Added a success message
            return redirect(url_for('main.index'))
        else:
            flash(_('خطأ في اسم المستخدم أو كلمة المرور'), 'error') # Wrapped string
    
    return render_template('login.html')

# تسجيل الخروج
@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

# لوحة تحكم السوبر أدمن
@bp.route('/super-admin-control')
@login_required
@ui_super_admin_required # Use the UI version from auth.py
def super_admin_control():
    return render_template('admin.html')

# لوحة تحكم المشرف
@bp.route('/admin-dashboard')
@login_required
@ui_super_admin_required # Changed to use the decorator
def admin_dashboard():
    # The decorator now handles the role check and redirect
    # Rendering admin.html as admin_dashboard.html is missing and roles are currently aliased
    return render_template('admin.html')

# لوحة تحكم العميل
@bp.route('/client-dashboard')
@login_required
def client_dashboard():
    return render_template('client_dashboard.html')

# تشغيل السكربت
@bp.route('/run-script', methods=['POST'])
@login_required
@api_super_admin_required # Use the API version (original one in this file)
def run_script():
    try:
        # تأكد من وجود السكربت في مجلد uploads
        script_path = os.path.join('uploads', 'real_estate_scraper.py')  # عدّل الاسم حسب الحاجة

        import subprocess
        result = subprocess.run(
            ['python', script_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout or _("⚠️ لا توجد مخرجات") # Wrapped string
        errors = result.stderr

        return jsonify({
            'success': True,
            'output': output,
            'errors': errors # Errors from subprocess might be harder to translate or might not be user-facing directly
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'output': "",
            'errors': _("❌ حدث خطأ أثناء تشغيل السكربت: {}").format(str(e)) # Wrapped string & formatted
        })

# المنتجات الرقمية
@bp.route('/products')
def products():
    return render_template('products.html')

# تواصل معنا
@bp.route('/contact-us')
def contact_us():
    return render_template('contact_us.html')

# تسجيل العملاء
@bp.route('/register')
def register():
    return render_template('client_register.html')

# لوحة التحكم
@bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('client_dashboard.html')

# سكربتاتي
@bp.route('/my-scripts')
@login_required
def my_scripts():
    return render_template('my_scripts.html')

# سجل السكربتات
@bp.route('/script-logs')
@login_required
def script_logs():
    return render_template('script_logs.html')

# الملف الشخصي
@bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

# === Webhooks ===
@bp.route('/webhook/payment_confirmed', methods=['POST'])
def webhook_payment_confirmed():
    # IMPORTANT: Secure this webhook!
    # - Verify sender (e.g., IP whitelist, signature verification using a shared secret)
    # - Use HTTPS

    data = request.json # Assuming payment gateway sends JSON data
    current_app.logger.info(f"Received payment confirmation webhook: {data}")

    # Placeholder: Extract necessary data (actual keys will depend on the payment gateway)
    user_id = data.get('user_id')
    product_id = data.get('product_id')
    transaction_id = data.get('transaction_id')
    # payment_status = data.get('status') # e.g., 'completed', 'success'

    if not all([user_id, product_id, transaction_id]):
        current_app.logger.error(f"Webhook missing required data: user_id, product_id, or transaction_id. Data: {data}")
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400

    # Fetch User and Product from DB
    user = User.query.get(user_id)
    product = Product.query.get(product_id)

    if not user:
        current_app.logger.error(f"Webhook: User not found for user_id: {user_id}. Data: {data}")
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    if not product:
        current_app.logger.error(f"Webhook: Product not found for product_id: {product_id}. Data: {data}")
        return jsonify({'status': 'error', 'message': 'Product not found'}), 404
    if not product.is_active:
        current_app.logger.error(f"Webhook: Product {product_id} is inactive. Data: {data}")
        return jsonify({'status': 'error', 'message': 'Product is inactive'}), 400

    # Grant Access (Create Subscription)
    # Determine subscription period
    subscription_period_months = 12 # Default for new script subscriptions
    if product.type == ProductType.EBOOK or product.type == ProductType.DATABASE:
        subscription_period_months = 1200 # ~100 years for "lifetime" access
    elif hasattr(product, 'default_subscription_period_months') and product.default_subscription_period_months:
        subscription_period_months = product.default_subscription_period_months

    new_subscription = Subscription(
        user_id=user.id,
        product_id=product.id,
        period_months=subscription_period_months,
        start_date=datetime.utcnow(),
        is_active=True
    )
    db.session.add(new_subscription)

    delivery_info = ""
    product_type_for_email = product.type # Will be translated by _() in email template if key matches

    if product.type == ProductType.SCRIPT:
        product_type_for_email = _('سكربت') # More specific for email if needed
        delivery_info = url_for('main.my_scripts', _external=True)
        if product.script_id:
            existing_user_script = UserScript.query.filter_by(user_id=user.id, script_id=product.script_id).first()
            if not existing_user_script:
                user_script = UserScript(user_id=user.id, script_id=product.script_id, assigned_by=user.id) # Self-assigned
                db.session.add(user_script)
    elif product.type == ProductType.EBOOK or product.type == ProductType.DATABASE:
        product_type_for_email = _('كتاب إلكتروني') if product.type == ProductType.EBOOK else _('قاعدة بيانات')
        # Assuming product.id is sufficient for product_access route for these types for now
        delivery_info = url_for('main.product_access', product_id=product.id, _external=True)
    else:
        product_type_for_email = _('منتج رقمي')
        delivery_info = url_for('main.dashboard', _external=True) # Fallback to dashboard

    try:
        db.session.commit()
        current_app.logger.info(f"Webhook: Subscription and UserScript (if applicable) created for user {user_id}, product {product_id}.")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Webhook: Database error for user {user_id}, product {product_id}: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Database processing error'}), 500

    # Call Celery tasks
    from tasks import task_send_delivery_email, task_send_whatsapp_notification

    user_name_for_email = user.full_name or user.username

    task_send_delivery_email.delay(
        user.email,
        user_name_for_email,
        product.name,
        product_type_for_email,
        delivery_info
    )

    if user.phone:
       whatsapp_message = _("مرحباً %(user_name)s، تم تأكيد طلبك للمنتج '%(product_name)s'. شكراً لك!",
                            user_name=user_name_for_email, product_name=product.name)
       task_send_whatsapp_notification.delay(user.phone, whatsapp_message)

    current_app.logger.info(f"Successfully processed webhook and queued notification tasks for transaction {transaction_id} for user {user_id}.")
    return jsonify({'status': 'success', 'message': 'Product delivery processing initiated.'}), 200

# === Secure Product Access ===
@bp.route('/product_access/<int:product_id>') # Renamed parameter
@login_required
def product_access(product_id): # Renamed parameter
    # Verify Access: Check for an active subscription
    subscription = Subscription.query.filter_by(
        user_id=current_user.id,
        product_id=product_id,
        is_active=True
    ).filter(Subscription.end_date > datetime.utcnow()).first()

    if not subscription:
        current_app.logger.warning(f"User {current_user.id} failed access attempt for product {product_id} - no active subscription.")
        abort(403) # Forbidden

    product = Product.query.get_or_404(product_id)

    if not product.is_active: # Check if product itself is still active
        current_app.logger.warning(f"User {current_user.id} trying to access inactive product {product_id}.")
        abort(404) # Not found, or treat as forbidden

    # Serve file if EBOOK or DATABASE and file_path exists
    if product.type in [ProductType.EBOOK, ProductType.DATABASE] and product.file_path:
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads') # Default to 'uploads'
        if not os.path.isabs(upload_folder): # Ensure UPLOAD_FOLDER is absolute or correctly relative to app root
            upload_folder = os.path.join(current_app.root_path, upload_folder)

        directory = os.path.join(upload_folder, os.path.dirname(product.file_path))
        filename = os.path.basename(product.file_path)

        current_app.logger.info(f"User {current_user.id} granted access to {product.type} '{product.name}'. Serving file: {filename} from {directory}")
        try:
            return send_from_directory(directory, filename, as_attachment=True)
        except Exception as e:
            current_app.logger.error(f"Error serving file {filename} from {directory}: {e}", exc_info=True)
            abort(500)

    elif product.type == ProductType.SCRIPT:
        # Scripts are not downloaded directly, user gets access via their 'my_scripts' page
        return redirect(url_for('main.my_scripts'))
    else:
        current_app.logger.warning(f"Product {product_id} type '{product.type}' not configured for direct download.")
        abort(404) # Or a more specific error page