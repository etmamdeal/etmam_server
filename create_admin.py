from app import app, db, User, Role
from werkzeug.security import generate_password_hash
import json
from models import Permission

# إنشاء حساب السوبر أدمن
with app.app_context():
    # التحقق من عدم وجود السوبر أدمن مسبقاً
    super_admin = User.query.filter_by(role=Role.SUPER_ADMIN).first()
    if not super_admin:
        super_admin_user = User(
            username='super_admin',
            password=generate_password_hash('super_admin123'),
            full_name='السوبر أدمن',
            email='super_admin@etmamdeal.com',
            phone='0500000000',
            role=Role.SUPER_ADMIN,
            permissions=json.dumps(Permission.get_all_permissions()),
            is_active=True
        )
        db.session.add(super_admin_user)
        db.session.commit()
        print("✅ تم إنشاء حساب السوبر أدمن بنجاح!")
        print("Username: super_admin")
        print("Password: super_admin123")
    else:
        print("⚠️ حساب السوبر أدمن موجود مسبقاً!")
        print("Username: super_admin") 