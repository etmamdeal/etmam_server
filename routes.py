from flask import Blueprint, jsonify, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user, login_user, logout_user
import os
from functools import wraps
from models import User, db

# إنشاء Blueprint
bp = Blueprint('main', __name__)

# تعريف decorator للتحقق من صلاحيات المشرف
def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_super_admin:
            return jsonify({'error': 'غير مصرح لك بالوصول'}), 403
        return f(*args, **kwargs)
    return decorated_function

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
            return redirect(url_for('main.index'))
        else:
            flash('خطأ في اسم المستخدم أو كلمة المرور', 'error')
    
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
@super_admin_required
def super_admin_control():
    return render_template('admin.html')

# لوحة تحكم المشرف
@bp.route('/admin-dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin and not current_user.is_super_admin:
        return redirect(url_for('main.index'))
    return render_template('admin_dashboard.html')

# لوحة تحكم العميل
@bp.route('/client-dashboard')
@login_required
def client_dashboard():
    return render_template('client_dashboard.html')

# تشغيل السكربت
@bp.route('/run-script', methods=['POST'])
@login_required
@super_admin_required
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

        output = result.stdout or "⚠️ لا توجد مخرجات"
        errors = result.stderr

        return jsonify({
            'success': True,
            'output': output,
            'errors': errors
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'output': "",
            'errors': f"❌ حدث خطأ أثناء تشغيل السكربت: {str(e)}"
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