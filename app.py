from flask import Blueprint, jsonify
from flask_login import login_required, current_user
import os
from functools import wraps
from flask import Flask
from flask_login import LoginManager
from models import User

# إنشاء Blueprint
bp = Blueprint('main', __name__)

# إنشاء login manager
login_manager = LoginManager()
login_manager.login_view = 'main.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# تعريف decorator للتحقق من صلاحيات المشرف
def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_super_admin:
            return jsonify({'error': 'غير مصرح لك بالوصول'}), 403
        return f(*args, **kwargs)
    return decorated_function

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

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # تهيئة login manager
    login_manager.init_app(app)
    
    # استيراد وتسجيل Blueprint
    from routes import bp
    app.register_blueprint(bp)
    
    return app