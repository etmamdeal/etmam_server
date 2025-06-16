"""
تطبيق Flask الرئيسي
---------------
"""

from flask import Blueprint, Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, get_flashed_messages, abort, current_app
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from .forms import ResetPasswordForm, ProfileForm, ChangePasswordForm, EditProductForm, PropertyForm # Added PropertyForm
from werkzeug.security import generate_password_hash, check_password_hash
import werkzeug.routing.exceptions # Added for specific exception handling
from datetime import datetime, timedelta, date # Added date
from dotenv import load_dotenv
import io
# Removed duplicate dotenv and io imports
import contextlib
import json # json is already imported, ensure it's here
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.utils import secure_filename
from functools import wraps

# تحميل متغيرات البيئة من ملف .env
load_dotenv()

# إنشاء Blueprint
bp = Blueprint('main', __name__)

# Context processor to inject 'now' for templates
@bp.app_context_processor
def inject_now():
    return {'now': datetime.utcnow()}

# تهيئة قاعدة البيانات
from models import db, User, Script, UserScript, RunLog, Role, Permission, Product, ProductType, Subscription, SubscriptionPeriod, Ebook, Database, Ticket, TicketMessage, TicketAttachment

# تهيئة نظام تسجيل الدخول
login_manager = LoginManager()
login_manager.login_view = 'main.client_login'

def create_super_admin():
    """إنشاء حساب السوبر أدمن إذا لم يكن موجوداً"""
    try:
        # التحقق من وجود حساب سوبر أدمن
        super_admin = User.query.filter_by(role=Role.SUPER_ADMIN).first()
        if not super_admin:
            # إنشاء حساب السوبر أدمن
            super_admin = User(
                username='super_admin',
                password=generate_password_hash('super_admin123'),
                email='super_admin@etmamdeal.com',
                full_name='السوبر أدمن',
                phone='0500000000',
                role=Role.SUPER_ADMIN,
                is_active=True,
                permissions=json.dumps(Permission.get_all_permissions())
            )
            db.session.add(super_admin)
            db.session.commit()
            print("✅ تم إنشاء حساب السوبر أدمن بنجاح!")
            print("Username: super_admin")
            print("Password: super_admin123")
        else:
            print("✅ حساب السوبر أدمن موجود مسبقاً")
    except Exception as e:
        print(f"❌ خطأ في إنشاء حساب السوبر أدمن: {str(e)}")
        db.session.rollback()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# استيراد دوال المصادقة
from auth import super_admin_required, admin_required, client_required, check_permission, check_role_and_redirect

# إعدادات البريد الإلكتروني من متغيرات البيئة
SMTP_SERVER = 'smtppro.zoho.sa'
SMTP_PORT = 465
SMTP_USERNAME = 'ai_agents@etmamdeal.com'
SMTP_PASSWORD = 'TKxLhzQ2zRtp'
ADMIN_EMAIL = 'ai_agents@etmamdeal.com'

# تحسين التحقق من الصلاحيات
def check_admin_permission(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("يجب تسجيل الدخول أولاً.", "danger")
                return redirect(url_for('main.admin_login'))
                
            if current_user.is_super_admin:
                if request.endpoint.startswith('admin_'):
                    return redirect(url_for('main.super_admin_dashboard'))
            elif current_user.is_admin:
                if not current_user.has_permission(permission):
                    flash("ليس لديك الصلاحية الكافية.", "danger")
                    return redirect(url_for('main.admin_dashboard'))
            else:
                flash("غير مصرح لك بالدخول هنا.", "danger")
                return redirect(url_for('main.homepage'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def send_email(subject, body, to_email):
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = SMTP_USERNAME
        msg['To'] = to_email

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
            print("✅ تم الإرسال بنجاح")
            return True
    except Exception as e:
        error_msg = f"❌ فشل الإرسال: {str(e)}"
        print(error_msg)
        current_app.logger.error(error_msg)
        return False

# المسارات
@bp.route('/')
def homepage():
    try:
        return render_template('index.html', now=datetime.now())
    except Exception as e:
        current_app.logger.error(f'خطأ في الصفحة الرئيسية: {str(e)}')
        return f'<h1>خطأ في عرض الصفحة</h1><pre>{str(e)}</pre>', 500

@bp.route('/service-description')
def service_description():
    return render_template('service_description.html')

@bp.route('/scripts')
def scripts():
    try:
        # Renamed 'scripts' to 'script_products' for clarity as items are Product objects
        script_products = Product.query.filter_by(type=ProductType.SCRIPT, is_active=True).all()
        return render_template('scripts.html', scripts=script_products, ProductType=ProductType)
    except Exception as e:
        current_app.logger.error(f"Error in /scripts route: {str(e)}")
        flash("حدث خطأ أثناء تحميل السكربتات", "danger")
        return redirect(url_for('main.products'))

@bp.route('/products')
def products():
    try:
        all_products = Product.query.filter_by(is_active=True).all()
        return render_template('products.html', products=all_products, ProductType=ProductType)
    except Exception as e:
        current_app.logger.error(f"Error in /products route: {str(e)}")
        flash("حدث خطأ أثناء تحميل المنتجات", "danger")
        return redirect(url_for('main.homepage'))

@bp.route('/request-script/<int:script_id>')
@bp.route('/request-script/<int:script_id>/<int:period>')
@login_required
def request_script(script_id, period=None):
    script = Product.query.get_or_404(script_id)
    if script.type != 'script':
        abort(404)
    
    # حساب السعر بناءً على فترة الاشتراك
    price = script.price
    if period:
        if period == 3:
            price = script.price * 2.5
        elif period == 6:
            price = script.price * 4.5
        elif period == 12:
            price = script.price * 8

    # إرسال طلب السكربت عبر البريد الإلكتروني
    send_script_request_email(current_user, script, period, price)
    
    flash('تم إرسال طلبك بنجاح. سيتم التواصل معك قريباً.', 'success')
    return redirect(url_for('main.scripts'))

@bp.route('/contact-us', methods=['GET', 'POST'])
def contact_us():
    if request.method == 'POST':
        # ... existing code ...
        return redirect(url_for('main.contact_us'))
    
    return render_template('contact_us.html', now=datetime.now())

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            full_name = request.form['full_name']
            phone = request.form['phone']

            if password != confirm_password:
                flash("كلمتا المرور غير متطابقتين", "danger")
                return redirect(url_for('main.register'))

            if len(password) < 6:
                flash("كلمة المرور يجب أن تكون 6 أحرف على الأقل", "danger")
                return redirect(url_for('main.register'))

            if User.query.filter_by(username=username).first():
                flash("اسم المستخدم مسجل مسبقًا", "danger")
                return redirect(url_for('main.register'))

            if User.query.filter_by(email=email).first():
                flash("البريد الإلكتروني مسجل مسبقًا", "danger")
                return redirect(url_for('main.register'))

            # إنشاء حساب جديد
            user = User(
                username=username,
                email=email,
                password=generate_password_hash(password),
                full_name=full_name,
                phone=phone,
                is_active=True
            )
            
            db.session.add(user)
            db.session.commit()
            
            login_user(user)
            flash("تم تسجيل حسابك بنجاح! مرحباً بك في منصة إتمام", "success")
            return redirect(url_for('main.client_dashboard'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"خطأ في عملية التسجيل: {str(e)}")
            flash("حدث خطأ أثناء التسجيل. الرجاء المحاولة مرة أخرى.", "danger")
            return redirect(url_for('main.register'))

    return render_template('client_register.html', now=datetime.now())

@bp.route('/client-login', methods=['GET', 'POST'])
def client_login():
    if current_user.is_authenticated:
        dashboard = check_role_and_redirect()
        if dashboard:
            return redirect(url_for(f'main.{dashboard}'))
        return redirect(url_for('main.homepage'))

    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            
            user = User.query.filter_by(username=username).first()
            
            if not user or not check_password_hash(user.password, password):
                flash("خطأ في اسم المستخدم أو كلمة المرور.", "danger")
                return redirect(url_for('main.client_login'))
            
            if user.is_admin or user.is_super_admin:
                flash("هذا الحساب مخصص للإدارة فقط.", "danger")
                return redirect(url_for('main.client_login'))
            
            if not user.is_active:
                flash("حسابك غير مفعل. الرجاء التواصل مع الإدارة.", "warning")
                return redirect(url_for('main.client_login'))
                
            login_user(user)
            flash("تم تسجيل دخولك بنجاح!", "success")
            return redirect(url_for('main.client_dashboard'))
            
        except Exception as e:
            current_app.logger.error(f"خطأ في تسجيل دخول العميل: {str(e)}")
            flash("حدث خطأ أثناء تسجيل الدخول. الرجاء المحاولة مرة أخرى.", "danger")
            return redirect(url_for('main.client_login'))
            
    return render_template('client_login.html', now=datetime.now())

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("تم تسجيل خروجك بنجاح.", "success")
    return redirect(url_for('main.homepage'))

@bp.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        if current_user.is_super_admin:
            return redirect(url_for('main.super_admin_dashboard'))
        elif current_user.is_admin:
            return redirect(url_for('main.admin_dashboard'))
        else:
            flash("غير مصرح لك بالدخول هنا.", "danger")
            return redirect(url_for('main.homepage'))

    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            
            user = User.query.filter_by(username=username).first()
            
            if not user:
                flash("اسم المستخدم غير موجود.", "danger")
                return redirect(url_for('main.admin_login'))
            
            if not check_password_hash(user.password, password):
                flash("كلمة المرور غير صحيحة.", "danger")
                return redirect(url_for('main.admin_login'))
            
            if not (user.is_admin or user.is_super_admin):
                flash("هذا الحساب ليس لديه صلاحيات إدارية.", "danger")
                return redirect(url_for('main.admin_login'))
            
            if not user.is_active:
                flash("الحساب غير مفعل.", "danger")
                return redirect(url_for('main.admin_login'))
            
            login_user(user)
            user.update_last_login()
            flash("تم تسجيل دخولك بنجاح!", "success")
            
            if user.is_super_admin:
                return redirect(url_for('main.super_admin_dashboard'))
            else:
                return redirect(url_for('main.admin_dashboard'))
            
        except Exception as e:
            current_app.logger.error(f"خطأ في تسجيل دخول المشرف: {str(e)}")
            flash("حدث خطأ أثناء تسجيل الدخول. الرجاء المحاولة مرة أخرى.", "danger")
            return redirect(url_for('main.admin_login'))
            
    return render_template('admin_login.html', now=datetime.now())

@bp.route('/reset-password-request', methods=['POST'])
def reset_password_request():
    try:
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash("البريد الإلكتروني غير مسجل في النظام.", "danger")
            return redirect(url_for('main.admin_login'))
            
        # إنشاء رابط إعادة تعيين كلمة المرور
        reset_token = user.get_reset_password_token()
        reset_url = url_for('main.reset_password', token=reset_token, _external=True)
        
        # إرسال البريد الإلكتروني
        subject = "طلب إعادة تعيين كلمة المرور"
        body = f"""
        مرحباً {user.username},
        
        لقد تلقينا طلباً لإعادة تعيين كلمة المرور الخاصة بك.
        لإعادة تعيين كلمة المرور، يرجى النقر على الرابط التالي:
        
        {reset_url}
        
        إذا لم تقم بطلب إعادة تعيين كلمة المرور، يرجى تجاهل هذا البريد.
        
        مع تحيات،
        فريق إتمام
        """
        
        if send_email(subject, body, user.email):
            flash("تم إرسال رابط إعادة تعيين كلمة المرور إلى بريدك الإلكتروني.", "success")
        else:
            flash("حدث خطأ أثناء إرسال البريد الإلكتروني. الرجاء المحاولة مرة أخرى.", "danger")
            
    except Exception as e:
        current_app.logger.error(f"خطأ في طلب إعادة تعيين كلمة المرور: {str(e)}")
        flash("حدث خطأ أثناء معالجة الطلب. الرجاء المحاولة مرة أخرى.", "danger")
        
    return redirect(url_for('main.admin_login')) # Keep this, as it's for the modal on admin_login page. The new usage will also redirect.

# This existing route is used by a modal on the admin_login page.
# We will now also use it from the super_admin_dashboard.
# Adding @super_admin_required would break its use for non-logged-in users trying to register an admin account (if that's a flow).
# However, the task implies this route should *now* be for super_admin use.
# This means the modal on admin_login.html for admin_register will become super_admin only.
# Or, we need a new route for super_admin adding admins.
# Given the instruction "Refactor admin_register for Super Admin Use", I will add the decorator and change redirect.
# This implies the previous usage from admin_login.html's modal might become non-functional or also require super_admin.
# For now, I will follow the refactoring instruction strictly.

@bp.route('/admin-register', methods=['POST'])
@login_required # Required for current_user context
@super_admin_required # Add super_admin_required decorator
def admin_register():
    try:
        # التحقق من البيانات
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        full_name = request.form['full_name']
        phone = request.form['phone']
        
        if password != confirm_password:
            flash("كلمتا المرور غير متطابقتين", "danger")
            return redirect(url_for('main.admin_login'))
            
        if User.query.filter_by(username=username).first():
            flash("اسم المستخدم مسجل مسبقاً", "danger")
            return redirect(url_for('main.admin_login'))
            
        if User.query.filter_by(email=email).first():
            flash("البريد الإلكتروني مسجل مسبقاً", "danger")
            return redirect(url_for('main.admin_login'))
            
        # إنشاء حساب المشرف
        admin = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            full_name=full_name,
            phone=phone,
            role=Role.ADMIN, # Changed from is_admin=True
            is_active=False  # يحتاج لتفعيل من السوبر أدمن
        )
        
        db.session.add(admin)
        db.session.commit()
        
        # Adjusted flash message for super_admin context
        flash(f"تم إنشاء حساب المشرف {admin.username} بنجاح. يحتاج الحساب إلى تفعيل.", "success")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"خطأ في تسجيل المشرف: {str(e)}")
        flash("حدث خطأ أثناء إنشاء الحساب. الرجاء المحاولة مرة أخرى.", "danger")
        
    return redirect(url_for('main.super_admin_dashboard')) # Change redirect to super_admin_dashboard

@bp.route('/super-admin')
@login_required
@super_admin_required
def super_admin_dashboard():
    try:
        admins = User.query.filter_by(role=Role.ADMIN).all()
        users = User.query.filter_by(role=Role.USER).all()

        # Fetch all products, details will be accessed via relationships in the template
        all_products = Product.query.all()

        # For stats, we still need to query by type
        active_scripts_count = Product.query.filter_by(type=ProductType.SCRIPT, is_active=True).count()
        total_scripts_count = Product.query.filter_by(type=ProductType.SCRIPT).count()

        # The template will iterate all_products and use product.type
        # to differentiate and access product.script_definition,
        # product.ebook_details, or product.database_details

        all_scripts = Script.query.all() # Fetch all actual scripts for assignment

        permissions = Permission.get_all_permissions()
        stats = {
            'admins_count': len(admins),
            'users_count': len(users),
            'active_scripts': active_scripts_count,
            'total_scripts': total_scripts_count,
            # Add counts for other product types if needed for stats
            'total_ebooks': Product.query.filter_by(type=ProductType.EBOOK).count(),
            'total_databases': Product.query.filter_by(type=ProductType.DATABASE).count(),
        }
        return render_template(
            'super_admin_dashboard.html',
            admins=admins,
            users=users,
            all_products=all_products, # Pass all products
            scripts=all_scripts, # Pass all scripts for assignment modal
            permissions=permissions,
            stats=stats,
            ProductType=ProductType # Pass ProductType class for template usage
        )
    except Exception as e:
        current_app.logger.error(f"Error in super_admin_dashboard: {str(e)}")
        flash("حدث خطأ أثناء تحميل لوحة التحكم", "danger")
        return redirect(url_for('main.homepage'))

@bp.route('/admin')
@admin_required
def admin_dashboard():
    try:
        # The @admin_required decorator (now updated) handles:
        # 1. Authentication check (redirects to admin_login if not authenticated)
        # 2. Role check (allows admin or super_admin)
        #    - If a super_admin accesses this, they are allowed by the decorator.
        #      It's conventional for super_admins to see admin dashboards.
        #      If specific redirection for super_admins away from this page is still desired,
        #      an explicit check can be maintained:
        if current_user.is_super_admin:
            return redirect(url_for('main.super_admin_dashboard'))
            
        # Fetch data for admin dashboard
        users = User.query.filter_by(role=Role.USER).all()
        all_products = Product.query.all() # Fetch all products

        # The template will iterate all_products and use product.type
        # to differentiate and access product.script_definition,
        # product.ebook_details, or product.database_details

        try:
            return render_template(
                'admin_dashboard.html',
                users=users,
                all_products=all_products, # Pass all products
                ProductType=ProductType, # Pass ProductType class for template usage
                Permission=Permission # Pass Permission class for template usage
            )
        except werkzeug.routing.exceptions.BuildError as e:
            if 'toggle_user_status' in str(e):
                current_app.logger.error(f"BuildError for 'toggle_user_status' in admin_dashboard: {str(e)} - Rendering minimal or redirecting.")
                flash("لوحة التحكم للمشرف واجهت خطأ في عرض جزء من الصفحة، ولكن الوظيفة الرئيسية تمت.", "warning")
                # Option 1: Redirect to a safe page
                return redirect(url_for('main.homepage'))
                # Option 2: Render a minimal template (if one exists or create simple one)
                # return render_template('admin/admin_dashboard_minimal_error.html', users=users, ProductType=ProductType)
            else:
                raise e # Re-raise other BuildErrors
        
    except Exception as e:
        current_app.logger.error(f"Error in admin_dashboard: {str(e)}")
        flash("حدث خطأ أثناء تحميل لوحة التحكم", "danger")
        return redirect(url_for('main.homepage'))

@bp.route('/client', endpoint='client_dashboard') # Assuming this is being repurposed
@login_required
@client_required # Ensure this decorator is appropriate for brokers, or a new one is needed.
def client_dashboard():
    # Stats for Real Estate Broker
    total_properties = Property.query.filter_by(user_id=current_user.id).count()

    # Placeholder stats for deals until deal management is implemented
    # Corrected querying for deals (assuming Deal model is available and user_id links to the broker)
    deals_in_progress_count = Deal.query.filter(Deal.user_id == current_user.id, Deal.stage.notin_(['Closed - Won', 'Closed - Lost'])).count() if db.inspect(Deal).has_table() else 0
    completed_deals_count = Deal.query.filter(Deal.user_id == current_user.id, Deal.stage == 'Closed - Won').count() if db.inspect(Deal).has_table() else 0

    # Placeholder for revenue estimation - this requires a field like 'deal_value' or 'commission_amount' on the Deal model
    # For now, let's assume it's based on property price of 'Closed - Won' deals if no specific value field.
    # This is highly speculative and needs a proper field in Deal model.
    revenue_estimation = db.session.query(db.func.sum(Property.price)).join(Deal, Deal.property_id == Property.id).filter(Deal.user_id == current_user.id, Deal.stage == 'Closed - Won').scalar() or 0.0 if db.inspect(Deal).has_table() else 0.0


    # Placeholder for recent activity - for now, just fetch last 5 properties added by user
    recent_activities = Property.query.filter_by(user_id=current_user.id)\
                                  .order_by(Property.created_at.desc())\
                                  .limit(5).all()

    return render_template('client/dashboard.html', # Changed template path
                                   total_properties=total_properties,
                                   deals_in_progress_count=deals_in_progress_count,
                                   completed_deals_count=completed_deals_count,
                                   revenue_estimation=revenue_estimation,
                                   recent_activities=recent_activities,
                                   now=datetime.utcnow() # Added now
                                  )

@bp.route('/client/my-scripts', endpoint='client_my_scripts')
@login_required
@client_required
def client_my_scripts():
    user_scripts_data = db.session.query(UserScript, Script, Product)\
        .join(Script, UserScript.script_id == Script.id)\
        .join(Product, Script.id == Product.script_id)\
        .filter(UserScript.user_id == current_user.id)\
        .filter(Product.type == ProductType.SCRIPT)\
        .all()

    # user_scripts_data will be a list of tuples (user_script_obj, script_obj, product_obj)
    # It's better to pass it as is, or structure it into a list of dicts if preferred by template complexity.

    return render_template('client/my_scripts.html', user_scripts_data=user_scripts_data, now=datetime.utcnow())

@bp.route('/client/my-logs', endpoint='client_my_logs')
@login_required
@client_required
def client_my_logs():
    page = request.args.get('page', 1, type=int)
    # Querying RunLog and labeling Script.name as 'script_name'
    logs_pagination = db.session.query(RunLog, Script.name.label('script_name'))\
        .join(Script, RunLog.script_id == Script.id)\
        .filter(RunLog.user_id == current_user.id)\
        .order_by(RunLog.executed_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)

    # logs_pagination.items will be a list of tuples (run_log_obj, script_name_str)
    return render_template('client/my_logs.html', logs_pagination=logs_pagination, now=datetime.utcnow())

@bp.route('/client/profile', methods=['GET', 'POST'], endpoint='client_profile')
@login_required
@client_required
def client_profile():
    profile_form = ProfileForm(obj=current_user) # Pre-populate with current_user data
    password_form = ChangePasswordForm()

    # Check which form was submitted using the submit button's name
    if 'submit_profile' in request.form and profile_form.validate_on_submit():
        current_user.full_name = profile_form.full_name.data
        current_user.email = profile_form.email.data
        current_user.phone = profile_form.phone.data
        try:
            db.session.commit()
            flash('تم تحديث بيانات ملفك الشخصي بنجاح!', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating profile for {current_user.username}: {str(e)}")
            flash('حدث خطأ أثناء تحديث الملف الشخصي. قد يكون البريد الإلكتروني مستخدماً.', 'danger')
        return redirect(url_for('main.client_profile'))

    if 'submit_password' in request.form and password_form.validate_on_submit():
        # The form already validates current_password and that new_password matches confirm_new_password
        current_user.password = generate_password_hash(password_form.new_password.data)
        try:
            db.session.commit()
            flash('تم تغيير كلمة المرور بنجاح!', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error changing password for {current_user.username}: {str(e)}")
            flash('حدث خطأ أثناء تغيير كلمة المرور.', 'danger')
        return redirect(url_for('main.client_profile'))

    return render_template('client/profile.html', profile_form=profile_form, password_form=password_form, now=datetime.utcnow())

@bp.route('/client/properties/map', methods=['GET'], endpoint='client_add_property_map')
@login_required
@client_required
def client_add_property_map():
    user_properties = Property.query.filter_by(user_id=current_user.id).all()
    # Convert properties to a JSON string to be easily embedded in the template for JavaScript
    properties_data = []
    for prop in user_properties:
        properties_data.append({
            "title": prop.title,
            "lat": prop.latitude,
            "lng": prop.longitude,
            "type": prop.type,
            "price": prop.price,
            "url": "#" # Placeholder for url_for('main.client_edit_property', property_id=prop.id)
        })
    properties_json = json.dumps(properties_data)
    form = PropertyForm() # Instantiate the form for the modal
    return render_template('client/property_map.html', properties_json=properties_json, form=form, now=datetime.utcnow())

@bp.route('/client/properties/add', methods=['POST'], endpoint='client_add_property')
@login_required
@client_required
def client_add_property():
    form = PropertyForm(request.form) # Pass request.form explicitly for non-AJAX POST with separate hidden fields
    latitude = request.form.get('latitude', type=float)
    longitude = request.form.get('longitude', type=float)

    if not latitude or not longitude:
        flash('الموقع (خط العرض وخط الطول) مطلوب. يرجى تحديد نقطة على الخريطة.', 'danger')
        return redirect(url_for('main.client_add_property_map'))

    if form.validate(): # validate_on_submit() might not work as expected if lat/lng are not part of the WTForm class
        try:
            new_property = Property(
                user_id=current_user.id,
                title=form.title.data,
                type=form.type.data,
                price=form.price.data,
                area=form.area.data,
                rooms=form.rooms.data,
                description=form.description.data,
                latitude=latitude,
                longitude=longitude
                # created_at and updated_at have defaults
            )
            db.session.add(new_property)
            db.session.commit()
            flash(f'تمت إضافة العقار "{new_property.title}" بنجاح!', 'success')
            return redirect(url_for('main.client_add_property_map')) # Redirect back to map, new property will show
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding property: {str(e)}")
            flash('حدث خطأ أثناء إضافة العقار. يرجى المحاولة مرة أخرى.', 'danger')
    else:
        # Collect WTForm errors and flash them
        error_messages = []
        for field, errors in form.errors.items():
            for error in errors:
                error_messages.append(f"{getattr(form, field).label.text}: {error}")
        if error_messages: # Flash only if there are actual form validation errors
             flash("فشل التحقق من النموذج: " + "؛ ".join(error_messages), 'danger')

    # If validation fails or other issues, redirect back to the map page.
    # User will lose modal state and data in hidden fields if not handled by JS to repopulate,
    # but form data submitted would be lost anyway on a simple redirect.
    # Flashed messages will be displayed on the map page.
    return redirect(url_for('main.client_add_property_map'))

@bp.route('/client/properties', methods=['GET'], endpoint='client_manage_properties')
@login_required
@client_required
def client_manage_properties():
    page = request.args.get('page', 1, type=int)
    property_type_filter = request.args.get('type_filter', None)

    query = Property.query.filter_by(user_id=current_user.id)
    if property_type_filter and property_type_filter != 'all' and property_type_filter != '':
        query = query.filter(Property.type == property_type_filter)

    properties_pagination = query.order_by(Property.created_at.desc()).paginate(page=page, per_page=10, error_out=False)

    # Get distinct property types for filter dropdown, ensuring they are not None or empty
    distinct_types_query = db.session.query(Property.type)\
        .filter(Property.user_id == current_user.id, Property.type.isnot(None), Property.type != '')\
        .distinct().all()
    available_types = [ptype[0] for ptype in distinct_types_query]

    return render_template('client/property_list.html',
                           properties_pagination=properties_pagination,
                           available_types=available_types,
                           current_type_filter=property_type_filter if property_type_filter else 'all', # ensure 'all' is default if None
                           now=datetime.utcnow())

@bp.route('/client/properties/<int:property_id>/edit', methods=['GET', 'POST'], endpoint='client_edit_property')
@login_required
@client_required
def client_edit_property(property_id):
    property_to_edit = Property.query.filter_by(id=property_id, user_id=current_user.id).first_or_404()
    form = PropertyForm(obj=property_to_edit) # Pre-populate form with existing data

    original_lat = property_to_edit.latitude
    original_lng = property_to_edit.longitude

    if form.validate_on_submit(): # This will be true for POST requests if form data is valid
        try:
            property_to_edit.title = form.title.data
            property_to_edit.type = form.type.data
            property_to_edit.price = form.price.data
            property_to_edit.area = form.area.data
            property_to_edit.rooms = form.rooms.data
            property_to_edit.description = form.description.data

            # Get lat/lng from hidden fields in the form for potential re-positioning
            new_latitude = request.form.get('latitude', type=float)
            new_longitude = request.form.get('longitude', type=float)

            if new_latitude and new_longitude:
                property_to_edit.latitude = new_latitude
                property_to_edit.longitude = new_longitude

            property_to_edit.updated_at = datetime.utcnow() # Manually set updated_at
            db.session.commit()
            flash(f'تم تحديث العقار "{property_to_edit.title}" بنجاح!', 'success')
            return redirect(url_for('main.client_manage_properties'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error editing property {property_id}: {str(e)}")
            flash('حدث خطأ أثناء تحديث العقار. يرجى المحاولة مرة أخرى.', 'danger')

    # For GET requests, or if form validation failed on POST:
    # Pass original coordinates for map centering.
    # The form object (form) will contain submitted values and errors if validation failed.
    # Ensure hidden fields in template are populated with these values for JS to pick up on load.
    if request.method == 'POST' and not form.validate(): # If POST failed validation
        # Keep submitted values for hidden fields if they exist, else use original
        current_lat_for_map = request.form.get('latitude', original_lat, type=float)
        current_lng_for_map = request.form.get('longitude', original_lng, type=float)
        flash('الرجاء تصحيح الأخطاء في النموذج.', 'danger')
    else: # For GET requests
        current_lat_for_map = original_lat
        current_lng_for_map = original_lng


    return render_template('client/edit_property.html',
                           form=form,
                           property_id=property_id,
                           property_title=property_to_edit.title,
                           current_lat=current_lat_for_map,
                           current_lng=current_lng_for_map,
                           now=datetime.utcnow())

@bp.route('/client/properties/<int:property_id>/delete', methods=['POST'], endpoint='client_delete_property')
@login_required
@client_required
def client_delete_property(property_id):
    property_to_delete = Property.query.filter_by(id=property_id, user_id=current_user.id).first_or_404()

    try:
        # Note: If Deal model has property_id as ForeignKey without ondelete='CASCADE',
        # and related deals exist, this will fail.
        # For now, proceeding with direct delete as per subtask instructions.
        # Example: Deal.query.filter_by(property_id=property_to_delete.id, user_id=current_user.id).delete()

        # Check for related deals and prevent deletion if they exist, or handle them.
        # This check assumes Deal model is imported and has a 'property_id' field.
        if hasattr(Deal, 'query') and Deal.query.filter_by(property_id=property_to_delete.id).first():
            flash(f'لا يمكن حذف العقار "{property_to_delete.title}" لأنه مرتبط بصفقات حالية. يرجى التعامل مع الصفقات أولاً.', 'danger')
            return redirect(url_for('main.client_manage_properties'))

        db.session.delete(property_to_delete)
        db.session.commit()
        flash(f'تم حذف العقار "{property_to_delete.title}" بنجاح.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting property {property_id}: {str(e)}")
        flash('حدث خطأ أثناء حذف العقار. يرجى المحاولة مرة أخرى.', 'danger')

    return redirect(url_for('main.client_manage_properties'))

@bp.route('/client/marketing-tools', methods=['GET'], endpoint='client_marketing_tools')
@login_required
@client_required
def client_marketing_tools():
    # This page might have dynamic elements in the future, but for now, it's static content.
    return render_template('client/marketing_tools.html', now=datetime.utcnow())

@bp.route('/client/resources', methods=['GET'], endpoint='client_resources')
@login_required
@client_required
def client_resources():
    # Similar to marketing tools, this page is initially static.
    return render_template('client/resources.html', now=datetime.utcnow())

@bp.route('/manage_users')
@login_required
def manage_users():
    if not current_user.is_admin:
        flash("غير مصرح لك بالدخول هنا.", "danger")
        return redirect(url_for('main.homepage'))
        
    users = User.query.all()
    return render_template('manage_users.html', users=users)

@bp.route('/manage_users/<int:user_id>/<action>')
@login_required
def manage_user_action(user_id, action):
    if not current_user.is_admin:
        flash("غير مصرح لك بالدخول هنا.", "danger")
        return redirect(url_for('main.homepage'))
    
    try:
        target_user = User.query.get_or_404(user_id)

        # Permission check: Allow if super_admin, or if admin and has MANAGE_USERS permission
        if not current_user.is_super_admin:
            if not (current_user.is_admin and current_user.has_permission(Permission.MANAGE_USERS)):
                flash("ليس لديك الصلاحية الكافية للقيام بهذا الإجراء.", "danger")
                # Redirect to where the admin usually manages users or a general dashboard
                return redirect(url_for('main.admin_dashboard'))

        if action == 'toggle_status':
            if request.method == 'POST':
                # Regular admins can only manage regular users. Super admins can manage anyone not themselves (super_admin).
                if not current_user.is_super_admin and target_user.role != Role.USER:
                    flash("لا يمكنك تعديل حالة هذا المستخدم.", "warning")
                    return redirect(url_for('main.admin_dashboard'))

                # Super admins cannot deactivate other super admins through this route (should use specific super_admin tools if any)
                # and cannot deactivate themselves. Regular admins cannot deactivate admins/super_admins.
                if target_user.role == Role.SUPER_ADMIN:
                    flash("لا يمكن تعديل حالة حساب سوبر أدمن آخر من هنا.", "danger")
                    return redirect(url_for('main.admin_dashboard'))

                if target_user.id == current_user.id:
                    flash("لا يمكنك تغيير حالتك الخاصة.", "warning")
                    return redirect(url_for('main.admin_dashboard'))

                target_user.is_active = not target_user.is_active
                db.session.commit()
                flash(f"تم {'تفعيل' if target_user.is_active else 'تعطيل'} حساب المستخدم {target_user.username} بنجاح.", "success")
            else: # GET request for toggle_status
                flash("الإجراء غير صالح. يجب أن يتم عبر POST.", "warning")

            # Determine redirect based on who is performing action
            if current_user.is_super_admin:
                # Super admin might be managing users from their main dashboard or a dedicated user list
                # For now, assume they go back to their main dashboard.
                # If there's a specific user list page they use, redirect there.
                return redirect(url_for('main.super_admin_dashboard'))
            else: # Regular admin
                 # Regular admins manage users from their admin_dashboard (which lists users)
                return redirect(url_for('main.admin_dashboard'))

        # Fallback for other actions or if action is not 'toggle_status'
        # flash(f"Action '{action}' not fully implemented for user {target_user.username}.", "info")
        if current_user.is_super_admin:
            return redirect(url_for('main.super_admin_dashboard'))
        return redirect(url_for('main.admin_dashboard'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"خطأ في تحديث حالة المستخدم: {str(e)}")
        flash("حدث خطأ أثناء تحديث حالة المستخدم", "danger")
        return redirect(url_for('main.manage_users'))

# --- End of Admin User Management (for regular admins, if any) ---


# Admin route to add a new script
@bp.route('/admin/add-script', methods=['GET', 'POST'])
@admin_required
def add_script_route(): # Renamed to avoid conflict if 'add_script' is used elsewhere
    if request.method == 'POST':
        try:
            script_name = request.form.get('name')
            description = request.form.get('description')
            parameters_str = request.form.get('parameters', '{}') # Default to empty JSON object
            price = request.form.get('price', 0.0)
            is_active = request.form.get('is_active') == 'true'

            if 'script_file' not in request.files:
                flash('لم يتم اختيار ملف للسكربت!', 'danger')
                return redirect(request.url)

            file = request.files['script_file']

            if file.filename == '':
                flash('لم يتم اختيار ملف للسكربت!', 'danger')
                return redirect(request.url)

            if not file.filename.endswith('.py'):
                flash('الملف المسموح به هو .py فقط', 'danger')
                return redirect(request.url)

            # Validate parameters as JSON
            try:
                parameters_json = json.loads(parameters_str) if parameters_str.strip() else {}
            except json.JSONDecodeError:
                flash('صيغة معلمات السكربت (JSON) غير صحيحة.', 'danger')
                return redirect(request.url)

            # Securely save the file
            filename = secure_filename(file.filename)
            # Construct path relative to the app's instance folder or a configured UPLOAD_FOLDER
            # For consistency, ensure UPLOAD_FOLDER and its subdirectories are handled correctly.
            # Assuming current_app.config['UPLOAD_FOLDER'] = 'uploads' (relative to instance or app root)
            # and we want scripts in a 'scripts' subfolder of that.

            # Path should be relative to the application root or instance path for portability
            # If UPLOAD_FOLDER is 'uploads', this will be 'uploads/scripts'
            scripts_upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'scripts')

            # Create the directory if it doesn't exist (it should be created by config.init_app)
            # For absolute path, one might use current_app.root_path or current_app.instance_path
            # Here, we assume UPLOAD_FOLDER is relative from where app runs or an absolute path itself.
            # If UPLOAD_FOLDER is relative, let's make it relative to app.root_path for clarity
            if not os.path.isabs(scripts_upload_folder):
                 scripts_upload_path = os.path.join(current_app.root_path, scripts_upload_folder)
            else:
                 scripts_upload_path = scripts_upload_folder

            os.makedirs(scripts_upload_path, exist_ok=True)

            file_path_for_db = os.path.join(scripts_upload_folder, filename) # Path to store in DB (relative)
            absolute_file_path = os.path.join(scripts_upload_path, filename) # Absolute path to save file

            # Check for filename collision (optional, but good practice)
            if os.path.exists(absolute_file_path):
                # Add a unique prefix/suffix or reject
                base, ext = os.path.splitext(filename)
                new_filename = f"{base}_{int(datetime.now().timestamp())}{ext}"
                absolute_file_path = os.path.join(scripts_upload_path, new_filename)
                file_path_for_db = os.path.join(scripts_upload_folder, new_filename)

            file.save(absolute_file_path)

            # Create Script object (actual script details)
            new_script_obj = Script(
                name=script_name, # Or a more internal name if Product.name is primary display name
                description=description, # Or perhaps Script model has its own detailed/technical description
                file_path=file_path_for_db, # Store relative path in DB
                parameters=parameters_json,
                created_by=current_user.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(new_script_obj)
            db.session.flush() # Flush to get new_script_obj.id for the Product

            # Create Product object (store/shop listing)
            new_product = Product(
                name=script_name,
                description=description,
                type=ProductType.SCRIPT,
                price=float(price),
                is_active=is_active,
                created_by=current_user.id,
                script_id=new_script_obj.id, # Link to the Script object
                created_at=datetime.utcnow(),
                last_modified=datetime.utcnow()
            )
            db.session.add(new_product)
            db.session.commit()

            flash(f'تمت إضافة السكربت "{script_name}" بنجاح!', 'success')
            return redirect(url_for('main.admin_dashboard')) # Or a script management page

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding new script: {str(e)}")
            flash('حدث خطأ أثناء إضافة السكربت. الرجاء المحاولة مرة أخرى.', 'danger')
            return redirect(request.url)

    return render_template('admin/add_script.html')

# Client Ticket System Routes
@bp.route('/client/tickets/new', methods=['GET', 'POST'], endpoint='client_new_ticket')
@login_required
@client_required
def client_new_ticket():
    if request.method == 'POST':
        ticket_type = request.form.get('ticket_type')
        subject = request.form.get('subject')
        description = request.form.get('description')

        if not all([ticket_type, subject, description]):
            flash('جميع الحقول مطلوبة لإنشاء التذكرة.', 'danger')
            return redirect(url_for('main.client_new_ticket'))

        new_ticket = Ticket(
            user_id=current_user.id,
            ticket_type=ticket_type,
            subject=subject,
            description=description,
            status='open', # Default status
            priority='medium' # Default priority
            # created_at and updated_at have defaults in model
        )
        db.session.add(new_ticket)
        db.session.commit() # Commit to get new_ticket.id

        # Notify admin about the new ticket
        email_subject = f"تذكرة دعم جديدة #{new_ticket.id}: {new_ticket.subject}"
        email_body = f"""
        مرحباً أيها المشرف,

        تم فتح تذكرة دعم جديدة بواسطة المستخدم {current_user.username} (Email: {current_user.email}).

        بيانات التذكرة:
        - المعرف: {new_ticket.id}
        - النوع: {new_ticket.ticket_type}
        - الموضوع: {new_ticket.subject}
        - الوصف: {new_ticket.description}
        - الأولوية: {new_ticket.priority}

        يمكنك عرض التذكرة والرد عليها عبر الرابط التالي:
        {url_for('main.admin_view_ticket', ticket_id=new_ticket.id, _external=True)}
        """
        send_email(email_subject, email_body, ADMIN_EMAIL)

        flash('تم إنشاء تذكرة الدعم بنجاح!', 'success')
        return redirect(url_for('main.client_list_tickets'))

    return render_template('client/new_ticket.html')

@bp.route('/client/tickets', methods=['GET'], endpoint='client_list_tickets')
@login_required
@client_required
def client_list_tickets():
    tickets = Ticket.query.filter_by(user_id=current_user.id).order_by(Ticket.updated_at.desc()).all()
    return render_template('client/list_tickets.html', tickets=tickets)

# Admin Ticket System Routes
@bp.route('/admin/tickets', methods=['GET'], endpoint='admin_list_tickets')
@login_required
@admin_required
def admin_list_tickets():
    tickets = Ticket.query.order_by(Ticket.updated_at.desc()).all()
    # For displaying user email/name, the Ticket model has ticket.user relationship
    return render_template('admin/list_tickets.html', tickets=tickets)

@bp.route('/client/tickets/<int:ticket_id>', methods=['GET', 'POST'], endpoint='client_view_ticket')
@login_required
@client_required
def client_view_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if ticket.user_id != current_user.id:
        abort(403) # Not authorized to view this ticket

    if request.method == 'POST':
        message_body = request.form.get('message_body')
        if not message_body:
            flash('لا يمكن إرسال رسالة فارغة.', 'warning')
        else:
            new_message = TicketMessage(
                ticket_id=ticket.id,
                user_id=current_user.id,
                message_body=message_body
                # created_at has default
            )
            ticket.updated_at = datetime.utcnow() # Update ticket's last update time
            db.session.add(new_message)
            db.session.add(ticket) # Add ticket to session due to updated_at change
            db.session.commit()

            # Notify admin about the client's new message
            email_subject = f"رد من العميل على تذكرة الدعم #{ticket.id}: {ticket.subject}"
            email_body = f"""
            مرحباً أيها المشرف,

            قام العميل {current_user.username} (Email: {current_user.email}) بالرد على التذكرة "{ticket.subject}" (ID: {ticket.id}).

            الرسالة:
            {message_body}

            يمكنك عرض التذكرة والرد عليها عبر الرابط التالي:
            {url_for('main.admin_view_ticket', ticket_id=ticket.id, _external=True)}
            """
            send_email(email_subject, email_body, ADMIN_EMAIL)

            flash('تم إرسال رسالتك بنجاح.', 'success')
            return redirect(url_for('main.client_view_ticket', ticket_id=ticket.id))

    messages = TicketMessage.query.filter_by(ticket_id=ticket.id).order_by(TicketMessage.created_at.asc()).all()
    return render_template('client/view_ticket.html', ticket=ticket, messages=messages)

@bp.route('/admin/tickets/<int:ticket_id>', methods=['GET', 'POST'], endpoint='admin_view_ticket')
@login_required
@admin_required
def admin_view_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    # No user_id check here, as admin should be able to see all tickets

    if request.method == 'POST':
        message_body = request.form.get('message_body')
        new_status = request.form.get('new_status')
        new_priority = request.form.get('new_priority')

        action_taken = False # Flag to check if any action was performed

        if message_body:
            # Admin posts a message
            admin_message = TicketMessage(
                ticket_id=ticket.id,
                user_id=current_user.id, # Admin is the sender
                message_body=message_body
            )
            db.session.add(admin_message)
            action_taken = True

            # Notify client of admin's reply
            email_subject = f"تحديث على تذكرة الدعم #{ticket.id}: {ticket.subject}"
            email_body = f"""
            مرحباً {ticket.user.username},

            قام أحد المشرفين بالرد على تذكرتك "{ticket.subject}" (ID: {ticket.id}).

            الرسالة:
            {message_body}

            يمكنك عرض التذكرة والرد عليها عبر الرابط التالي:
            {url_for('main.client_view_ticket', ticket_id=ticket.id, _external=True)}

            مع تحيات فريق دعم إتمام,
            """
            send_email(email_subject, email_body, ticket.user.email)

        if new_status and new_status != ticket.status:
            ticket.status = new_status
            action_taken = True
            # TODO: Potentially send email notification about status change

        if new_priority and new_priority != ticket.priority:
            ticket.priority = new_priority
            action_taken = True
            # TODO: Potentially send email notification about priority change

        if action_taken:
            ticket.updated_at = datetime.utcnow()
            db.session.add(ticket) # Add ticket to session due to updated_at or status/priority change
            db.session.commit()
            flash('تم تحديث التذكرة بنجاح!', 'success')
        else:
            flash('لم يتم إجراء أي تغييرات على التذكرة.', 'info')

        return redirect(url_for('main.admin_view_ticket', ticket_id=ticket.id))

    messages = TicketMessage.query.filter_by(ticket_id=ticket.id).order_by(TicketMessage.created_at.asc()).all()
    available_statuses = ['open', 'in_progress', 'closed', 'resolved']
    available_priorities = ['low', 'medium', 'high', 'urgent']

    return render_template('admin/view_ticket.html',
                           ticket=ticket,
                           messages=messages,
                           available_statuses=available_statuses,
                           available_priorities=available_priorities)

@bp.route('/super-admin/user/<int:user_id>/toggle-status', methods=['POST'], endpoint='toggle_user_status')
@login_required
@super_admin_required
def toggle_user_status(user_id):
    user_to_toggle = User.query.get_or_404(user_id)

    if user_to_toggle.is_super_admin: # Cannot deactivate a super_admin
        flash('لا يمكن تغيير حالة حساب السوبر أدمن.', 'danger')
        return redirect(url_for('main.super_admin_dashboard'))

    if user_to_toggle.role == Role.ADMIN: # Admins should be handled by toggle_admin_status
        flash('لتغيير حالة حساب المشرف، يرجى استخدام المسار المخصص للمشرفين.', 'warning')
        return redirect(url_for('main.super_admin_dashboard'))

    user_to_toggle.is_active = not user_to_toggle.is_active
    db.session.commit()

    status_message = "مفعل" if user_to_toggle.is_active else "معطل"
    flash(f'تم تغيير حالة المستخدم {user_to_toggle.username} إلى {status_message} بنجاح.', 'success')
    return redirect(url_for('main.super_admin_dashboard'))

@bp.route('/super-admin/admin/<int:admin_id>/toggle-status', methods=['POST'], endpoint='toggle_admin_status')
@login_required
@super_admin_required
def toggle_admin_status(admin_id):
    admin_to_toggle = User.query.get_or_404(admin_id)

    if admin_to_toggle.role != Role.ADMIN:
        flash('هذا المستخدم ليس مشرفاً.', 'danger')
        return redirect(url_for('main.super_admin_dashboard'))

    if admin_to_toggle.id == current_user.id:
        flash('لا يمكن للسوبر أدمن تعطيل حسابه الخاص بهذه الطريقة.', 'danger')
        return redirect(url_for('main.super_admin_dashboard'))

    admin_to_toggle.is_active = not admin_to_toggle.is_active
    db.session.commit()

    status_message = "مفعل" if admin_to_toggle.is_active else "معطل"
    flash(f'تم تغيير حالة المشرف {admin_to_toggle.username} إلى {status_message} بنجاح.', 'success')
    return redirect(url_for('main.super_admin_dashboard'))

@bp.route('/admin/product/<int:product_id>/edit', methods=['GET', 'POST'], endpoint='edit_product')
@login_required
@admin_required # Using general admin_required, specific permission check inside
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    # Permission check: Super_admin can edit any. Admin needs MANAGE_SCRIPTS for script products.
    if not current_user.is_super_admin:
        if product.type == ProductType.SCRIPT and not current_user.has_permission(Permission.MANAGE_SCRIPTS):
            flash("ليس لديك الصلاحية لتعديل هذا المنتج (السكربت).", "danger")
            return redirect(url_for('main.admin_dashboard'))
        # Add elif for other product types and their specific permissions if needed
        # elif product.type == ProductType.EBOOK and not current_user.has_permission(Permission.MANAGE_EBOOKS):
        #     flash("You do not have permission to edit this ebook product.", "danger")
        #     return redirect(url_for('main.admin_dashboard'))
        elif product.type != ProductType.SCRIPT: # For now, only allow script editing by non-super-admins if they have MANAGE_SCRIPTS
             flash(f"ليس لديك صلاحية تعديل هذا النوع من المنتجات ('{product.type}').", "warning")
             return redirect(url_for('main.admin_dashboard'))


    form = EditProductForm(obj=product)
    # Populate script_parameters for script products on GET request
    if request.method == 'GET' and product.type == ProductType.SCRIPT:
        if product.script_definition and product.script_definition.parameters:
            try:
                form.script_parameters.data = json.dumps(product.script_definition.parameters, indent=2, ensure_ascii=False)
            except TypeError: # handle cases where parameters might not be serializable directly
                 form.script_parameters.data = "{}" # Default to empty JSON string
                 flash("لم يتمكن من تحميل معلمات السكربت بشكل صحيح، قد تكون غير مهيأة.", "warning")


    if form.validate_on_submit():
        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        product.is_active = form.is_active.data
        product.last_modified_by = current_user.id
        product.last_modified = datetime.utcnow()

        if product.type == ProductType.SCRIPT and product.script_definition:
            if form.script_parameters.data and form.script_parameters.data.strip():
                try:
                    product.script_definition.parameters = json.loads(form.script_parameters.data)
                except json.JSONDecodeError:
                    # Error is handled by form validator, but we can flash again or log
                    flash("صيغة JSON لمعلمات السكربت غير صحيحة. لم يتم تحديث المعلمات.", "danger")
            else:
                product.script_definition.parameters = {} # Store empty JSON object

        try:
            db.session.commit()
            flash(f'تم تحديث المنتج "{product.name}" بنجاح!', 'success')
            if current_user.is_super_admin:
                return redirect(url_for('main.super_admin_dashboard'))
            return redirect(url_for('main.admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating product {product.name}: {str(e)}")
            flash(f'خطأ أثناء تحديث المنتج: {str(e)}', 'danger')

    # If form validation failed, errors will be in form.errors and displayed in template
    return render_template('admin/edit_product.html', form=form, product=product, ProductType=ProductType, now=datetime.utcnow())

@bp.route('/admin/product/<int:product_id>/delete', methods=['POST'], endpoint='delete_product')
@login_required
@admin_required # Base protection, more specific checks inside
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    # Permission check: Super_admin can "delete" any.
    # Admin needs MANAGE_SCRIPTS for script products.
    can_delete = False
    if current_user.is_super_admin:
        can_delete = True
    elif product.type == ProductType.SCRIPT and current_user.has_permission(Permission.MANAGE_SCRIPTS):
        can_delete = True
    # Add elif for other product types and their specific "manage" permissions if they exist/are added
    # Example:
    # elif product.type == ProductType.EBOOK and current_user.has_permission(Permission.MANAGE_EBOOKS):
    #    can_delete = True

    if not can_delete:
        flash("ليس لديك الصلاحية لحذف هذا المنتج.", "danger")
        if current_user.is_super_admin:
             return redirect(url_for('main.super_admin_dashboard'))
        return redirect(url_for('main.admin_dashboard'))

    if not product.is_active:
        flash(f'المنتج "{product.name}" هو بالفعل غير نشط.', 'info')
    else:
        product.is_active = False
        product.last_modified_by = current_user.id
        product.last_modified = datetime.utcnow()
        try:
            db.session.commit()
            flash(f'تم تحديد المنتج "{product.name}" كـغير نشط وتم إخفاؤه من القوائم العامة.', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deactivating product {product.name}: {str(e)}")
            flash(f'خطأ في إلغاء تنشيط المنتج: {str(e)}', 'danger')

    if current_user.is_super_admin:
        return redirect(url_for('main.super_admin_dashboard'))
    return redirect(url_for('main.admin_dashboard'))

# User Management by Super Admin

@bp.route('/super-admin/user/add', methods=['POST'], endpoint='add_user_by_superadmin')
@login_required
@super_admin_required
def add_user_by_superadmin():
    full_name = request.form.get('full_name')
    username = request.form.get('username')
    email = request.form.get('email')
    phone = request.form.get('phone')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if not all([full_name, username, email, password, confirm_password]):
        flash('جميع الحقول (الاسم الكامل، اسم المستخدم، البريد، كلمة المرور، تأكيد كلمة المرور) مطلوبة.', 'danger')
        return redirect(url_for('main.super_admin_dashboard'))

    if password != confirm_password:
        flash('كلمتا المرور غير متطابقتين.', 'danger')
        return redirect(url_for('main.super_admin_dashboard'))

    if len(password) < 6:
        flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل.', 'danger')
        return redirect(url_for('main.super_admin_dashboard'))

    if User.query.filter_by(username=username).first():
        flash(f'اسم المستخدم "{username}" مسجل مسبقاً.', 'danger')
        return redirect(url_for('main.super_admin_dashboard'))

    if User.query.filter_by(email=email).first():
        flash(f'البريد الإلكتروني "{email}" مسجل مسبقاً.', 'danger')
        return redirect(url_for('main.super_admin_dashboard'))

    new_user = User(
        full_name=full_name,
        username=username,
        email=email,
        phone=phone,
        password=generate_password_hash(password),
        role=Role.USER,
        is_active=True # Or False, if manual activation is preferred
    )
    db.session.add(new_user)
    try:
        db.session.commit()
        flash(f'تم إضافة المستخدم {new_user.username} بنجاح.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding user by superadmin: {str(e)}")
        flash('حدث خطأ أثناء إضافة المستخدم.', 'danger')

    return redirect(url_for('main.super_admin_dashboard'))


@bp.route('/super-admin/user/<int:user_id>/edit', methods=['POST'], endpoint='edit_user_by_superadmin')
@login_required
@super_admin_required
def edit_user_by_superadmin(user_id):
    user_to_edit = User.query.get_or_404(user_id)

    if user_to_edit.role != Role.USER:
        flash('يمكن تعديل حسابات المستخدمين العاديين فقط من هنا.', 'danger')
        return redirect(url_for('main.super_admin_dashboard'))

    new_full_name = request.form.get('full_name')
    new_email = request.form.get('email')
    new_phone = request.form.get('phone')

    if not new_full_name or len(new_full_name) < 3:
        flash('الاسم الكامل مطلوب ويجب أن يكون 3 أحرف على الأقل.', 'danger')
        return redirect(url_for('main.super_admin_dashboard'))

    if not new_email:
        flash('البريد الإلكتروني مطلوب.', 'danger')
        return redirect(url_for('main.super_admin_dashboard'))

    existing_user_with_email = User.query.filter(User.email == new_email, User.id != user_id).first()
    if existing_user_with_email:
        flash(f'البريد الإلكتروني "{new_email}" مستخدم بالفعل.', 'danger')
        return redirect(url_for('main.super_admin_dashboard'))

    user_to_edit.full_name = new_full_name
    user_to_edit.email = new_email
    user_to_edit.phone = new_phone

    try:
        db.session.commit()
        flash(f'تم تحديث بيانات المستخدم {user_to_edit.username} بنجاح.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error editing user {user_to_edit.username}: {str(e)}")
        flash('حدث خطأ أثناء تحديث بيانات المستخدم.', 'danger')

    return redirect(url_for('main.super_admin_dashboard'))

@bp.route('/super-admin/user/<int:user_id>/reset-password', methods=['POST'], endpoint='reset_user_password_by_superadmin')
@login_required
@super_admin_required
def reset_user_password_by_superadmin(user_id):
    user_to_reset = User.query.get_or_404(user_id)

    if user_to_reset.role != Role.USER:
        flash('يمكن إعادة تعيين كلمة مرور المستخدمين العاديين فقط.', 'danger')
        return redirect(url_for('main.super_admin_dashboard'))

    new_password = request.form.get('password')
    if not new_password or len(new_password) < 6:
        flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل.', 'danger')
        return redirect(url_for('main.super_admin_dashboard'))

    user_to_reset.password = generate_password_hash(new_password)
    try:
        db.session.commit()
        flash(f'تم إعادة تعيين كلمة مرور المستخدم {user_to_reset.username} بنجاح.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error resetting user password for {user_to_reset.username}: {str(e)}")
        flash('حدث خطأ أثناء إعادة تعيين كلمة المرور.', 'danger')

    return redirect(url_for('main.super_admin_dashboard'))

@bp.route('/super-admin/user/<int:user_id>/assign-scripts', methods=['POST'], endpoint='assign_scripts_to_user_by_superadmin')
@login_required
@super_admin_required
def assign_scripts_to_user_by_superadmin(user_id):
    user_to_assign = User.query.get_or_404(user_id)

    if user_to_assign.role != Role.USER:
        flash('يمكن تخصيص السكربتات للمستخدمين العاديين فقط.', 'danger')
        return redirect(url_for('main.super_admin_dashboard'))

    script_ids = request.form.getlist('scripts[]')

    # Clear existing script associations for this user
    UserScript.query.filter_by(user_id=user_id).delete()

    for script_id_str in script_ids:
        try:
            script_id = int(script_id_str)
            script = Script.query.get(script_id)
            if script:
                user_script = UserScript(
                    user_id=user_id,
                    script_id=script.id,
                    assigned_by=current_user.id,
                    assigned_at=datetime.utcnow()
                    # config_data can be set here if there's a way to input it, otherwise defaults to {}
                )
                db.session.add(user_script)
            else:
                flash(f'لم يتم العثور على السكربت بالمعرف {script_id_str}.', 'warning')
        except ValueError:
            flash(f'معرف السكربت غير صالح: {script_id_str}.', 'warning')

    try:
        db.session.commit()
        flash(f'تم تحديث السكربتات المخصصة للمستخدم {user_to_assign.username} بنجاح.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error assigning scripts to user {user_to_assign.username}: {str(e)}")
        flash('حدث خطأ أثناء تخصيص السكربتات.', 'danger')

    return redirect(url_for('main.super_admin_dashboard'))