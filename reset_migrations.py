import os
import shutil
from run import app
from models import db
from flask_migrate import init, migrate, upgrade

def reset_database():
    # حذف قاعدة البيانات القديمة
    if os.path.exists('database.db'):
        os.remove('database.db')
        print("✅ تم حذف قاعدة البيانات القديمة")

    # حذف مجلد migrations إذا كان موجوداً
    if os.path.exists('migrations'):
        shutil.rmtree('migrations')
        print("✅ تم حذف مجلد migrations")

    with app.app_context():
        # إنشاء قاعدة بيانات جديدة
        db.create_all()
        print("✅ تم إنشاء قاعدة البيانات الجديدة")

        # تهيئة وترقية قاعدة البيانات
        init()
        print("✅ تم تهيئة migrations")
        migrate()
        print("✅ تم إنشاء ملف الترحيل")
        upgrade()
        print("✅ تم ترقية قاعدة البيانات")

if __name__ == '__main__':
    reset_database() 