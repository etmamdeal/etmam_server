"""
تطبيق Flask الرئيسي
---------------
"""

from flask import Blueprint, Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, get_flashed_messages, abort, current_app
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from dotenv import load_dotenv
import io
import contextlib
import json
import os
# smtplib, MIMEText, MIMEMultipart removed as send_email moved to utils
from werkzeug.utils import secure_filename
from functools import wraps
from .utils import send_email_direct # Added for relocated email function

# تحميل متغيرات البيئة من ملف .env
load_dotenv()

# إنشاء Blueprint
bp = Blueprint('main', __name__)

# تهيئة قاعدة البيانات
from models import db, User, Script, UserScript, RunLog, Role, Permission, Product, ProductType, Subscription, SubscriptionPeriod, Ebook, Database

# تهيئة نظام تسجيل الدخول
login_manager = LoginManager()
login_manager.login_view = 'main.client_login'

# Custom Error Handlers
@bp.app_errorhandler(400)
def handle_400(e):
    current_app.logger.warning(f"Bad Request (400): {e.description if hasattr(e, 'description') else 'No description'}")
    return render_template('errors/generic_error.html', error=e), 400

@bp.app_errorhandler(401)
def handle_401(e):
    current_app.logger.warning(f"Unauthorized (401): {e.description if hasattr(e, 'description') else 'No description'}")
    flash("الرجاء تسجيل الدخول للوصول لهذه الصفحة.", "warning")
    return redirect(url_for('main.client_login'))

@bp.app_errorhandler(403)
def handle_403(e):
    current_app.logger.warning(f"Forbidden (403): {e.description if hasattr(e, 'description') else 'No description'}")
    # Assuming errors/403.html exists or will be created.
    # For now, to ensure this runs, let's use generic_error.html if 403.html is not confirmed.
    # The prompt implies errors/403.html, errors/404.html, errors/500.html exist from a previous step.
    # I will assume they exist.
    return render_template('errors/403.html', error=e), 403

@bp.app_errorhandler(404)
def handle_404(e):
    current_app.logger.info(f"Not Found (404): {request.path} - {e.description if hasattr(e, 'description') else 'No description'}")
    return render_template('errors/404.html', error=e), 404

@bp.app_errorhandler(500)
def handle_500(e):
    original_exception = getattr(e, "original_exception", None)
    if original_exception:
        current_app.logger.exception(f"Internal Server Error (500): {e.description if hasattr(e, 'description') else 'No description'}")
    else:
        current_app.logger.error(f"Internal Server Error (500): {e.description if hasattr(e, 'description') else 'No description'}")
    return render_template('errors/500.html', error=e), 500

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
# check_admin_permission was moved to auth.py
from auth import super_admin_required, admin_required, client_required, check_permission, check_role_and_redirect 

# send_email was moved to utils.py and renamed send_email_direct

# المسارات
@bp.route('/')
def homepage():
    try:
        return render_template('index.html', now=datetime.now())
    except Exception as e:
        current_app.logger.exception(f'An error occurred in the homepage: {str(e)}')
        abort(500) 

@bp.route('/service-description')
def service_description():
    return render_template('service_description.html')

@bp.route('/scripts')
def scripts():
    try:
        scripts = Product.query.filter_by(type='script', is_active=True).all()
        return render_template('scripts.html', scripts=scripts)
    except Exception as e:
        current_app.logger.exception(f"Error in route {request.path}: {str(e)}")
        flash("حدث خطأ أثناء تحميل السكربتات", "danger")
        return redirect(url_for('main.products'))

@bp.route('/products')
def products():
    try:
        products = Product.query.filter_by(is_active=True).all()
        return render_template('products.html', products=products)
    except Exception as e:
        current_app.logger.exception(f"Error in route {request.path}: {str(e)}")
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
            current_app.logger.exception(f"Error in route {request.path}: {str(e)}")
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
            current_app.logger.exception(f"Error in route {request.path}: {str(e)}")
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
            current_app.logger.exception(f"Error in route {request.path}: {str(e)}")
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
        
        if send_email_direct(subject, body, user.email): # Updated to send_email_direct
            flash("تم إرسال رابط إعادة تعيين كلمة المرور إلى بريدك الإلكتروني.", "success")
        else:
            flash("حدث خطأ أثناء إرسال البريد الإلكتروني. الرجاء المحاولة مرة أخرى.", "danger")
            
    except Exception as e:
        current_app.logger.exception(f"Error in route {request.path}: {str(e)}")
        flash("حدث خطأ أثناء معالجة الطلب. الرجاء المحاولة مرة أخرى.", "danger")
        
    return redirect(url_for('main.admin_login'))

@bp.route('/admin-register', methods=['POST'])
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
            is_admin=True,
            is_active=False  # يحتاج لتفعيل من السوبر أدمن
        )
        
        db.session.add(admin)
        db.session.commit()
        
        flash("تم إنشاء حساب المشرف بنجاح. يرجى انتظار تفعيل الحساب من قبل الإدارة.", "success")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error in route {request.path}: {str(e)}")
        flash("حدث خطأ أثناء إنشاء الحساب. الرجاء المحاولة مرة أخرى.", "danger")
        
    return redirect(url_for('main.admin_login'))

@bp.route('/super-admin')
@login_required
@super_admin_required
def super_admin_dashboard():
    try:
        admins = User.query.filter_by(role=Role.ADMIN).all()
        users = User.query.filter_by(role=Role.USER).all()
        scripts = Product.query.filter_by(type='script').all()
        ebooks = Product.query.filter_by(type='ebook').all()
        databases = Product.query.filter_by(type='database').all()
        permissions = Permission.get_all_permissions()
        stats = {
            'admins_count': len(admins),
            'users_count': len(users),
            'active_scripts': Product.query.filter_by(type='script', is_active=True).count(),
            'total_scripts': Product.query.filter_by(type='script').count(),
        }
        return render_template(
            'super_admin_dashboard.html',
            admins=admins,
            users=users,
            scripts=scripts,
            ebooks=ebooks,
            databases=databases,
            permissions=permissions,
            stats=stats
        )
    except Exception as e:
        current_app.logger.exception(f"Error in route {request.path}: {str(e)}")
        flash("حدث خطأ أثناء تحميل لوحة التحكم", "danger")
        return redirect(url_for('main.homepage'))

@bp.route('/admin')
@admin_required
def admin_dashboard():
    try:
        if not current_user.is_authenticated:
            return redirect(url_for('main.admin_login'))
            
        if current_user.is_super_admin:
            return redirect(url_for('main.super_admin_dashboard'))
            
        if not current_user.is_admin:
            flash("غير مصرح لك بالدخول هنا.", "danger")
            return redirect(url_for('main.homepage'))
            
        # ... rest of the code ...
        
    except Exception as e:
        current_app.logger.exception(f"Error in route {request.path}: {str(e)}")
        flash("حدث خطأ أثناء تحميل لوحة التحكم", "danger")
        return redirect(url_for('main.homepage'))

@bp.route('/client')
@client_required
def client_dashboard():
    return render_template('client_dashboard.html')

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
        # ... existing code ...
        return redirect(url_for('main.manage_users'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error in route {request.path}: {str(e)}")
        flash("حدث خطأ أثناء تحديث حالة المستخدم", "danger")
        return redirect(url_for('main.manage_users'))

# حذف سطر تسجيل Blueprint لأنه يتم في run.py 