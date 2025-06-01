"""
تشغيل التطبيق مع دعم WebSocket
----------------------------
"""

from flask_sqlalchemy import SQLAlchemy
from models import db, User, Script, UserScript, RunLog, Role, Permission
from celery_app import make_celery
from app import create_app
from extensions import migrate
from werkzeug.security import generate_password_hash

app = create_app()
app.config.from_object('config.Config')

# تهيئة الإضافات
db.init_app(app)
migrate.init_app(app, db)

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

celery = make_celery(app)

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    ) 