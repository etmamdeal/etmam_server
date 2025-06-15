"""
تشغيل التطبيق مع دعم WebSocket
----------------------------
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate # Import Migrate
from models import db, User, Script, UserScript, RunLog, Role, Permission
from celery_app import make_celery
from app import bp, login_manager
from werkzeug.security import generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix # Import ProxyFix
from flask_wtf.csrf import CSRFProtect # Import CSRFProtect

# Global CSRFProtect instance
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # تهيئة الإضافات
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app) # Initialize CSRF protection
    
    # تسجيل Blueprint
    app.register_blueprint(bp)
    
    # إنشاء قاعدة البيانات وحساب السوبر أدمن
    with app.app_context():
        db.create_all()
        
        # إنشاء حساب السوبر أدمن إذا لم يكن موجوداً
        if not User.query.filter_by(role=Role.SUPER_ADMIN).first():
            super_admin = User(
                username='super_admin',
                password=generate_password_hash('super_admin123'),
                email='super_admin@etmamdeal.com',
                full_name='السوبر أدمن',
                phone='0500000000',
                role=Role.SUPER_ADMIN,
                is_active=True
            )
            db.session.add(super_admin)
            db.session.commit()
            print("✅ تم إنشاء حساب السوبر أدمن بنجاح!")
            print("Username: super_admin")
            print("Password: super_admin123")
        else:
            print("✅ حساب السوبر أدمن موجود مسبقاً")
    

    # Apply ProxyFix middleware if not in debug mode
    if not app.config.get('DEBUG', False): # Check if DEBUG is explicitly False or not set
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    return app

app = create_app()
celery = make_celery(app)
migrate = Migrate(app, db) # Initialize Flask-Migrate

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    ) 