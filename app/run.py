"""
تشغيل التطبيق مع دعم WebSocket
----------------------------
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import db, User, Script, UserScript, RunLog, Role, Permission # db is imported here
from celery_app import make_celery
from app import bp, login_manager # app blueprint
from extensions import migrate # Import migrate from extensions
from werkzeug.security import generate_password_hash

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # تهيئة الإضافات
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db) # Initialize Flask-Migrate
    
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
    
    return app

app = create_app()
celery = make_celery(app)

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    ) 