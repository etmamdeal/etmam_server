"""
اختبارات النماذج في نظام إتمام
-----------------------------

يحتوي هذا الملف على اختبارات شاملة لجميع نماذج قاعدة البيانات:
- اختبارات نموذج المستخدم
- اختبارات نموذج السكربت
- اختبارات نموذج سجل التشغيل
- اختبارات نموذج سجل الأنشطة
"""

import unittest
from datetime import datetime, timedelta
from app import app, db
from models import User, Script, RunLog, ActivityLog, Role, Permission
from werkzeug.security import generate_password_hash, check_password_hash

class TestModels(unittest.TestCase):
    """اختبارات نماذج قاعدة البيانات"""
    
    def setUp(self):
        """إعداد بيئة الاختبار قبل كل اختبار"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
    
    def tearDown(self):
        """تنظيف بيئة الاختبار بعد كل اختبار"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_user_creation(self):
        """اختبار إنشاء المستخدم"""
        user = User(
            username='test_user',
            password=generate_password_hash('test123'),
            email='test@test.com',
            full_name='مستخدم اختبار',
            role=Role.USER,
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        
        # التحقق من حفظ المستخدم
        saved_user = User.query.filter_by(username='test_user').first()
        self.assertIsNotNone(saved_user)
        self.assertEqual(saved_user.email, 'test@test.com')
        self.assertEqual(saved_user.role, Role.USER)
        self.assertTrue(saved_user.is_active)
        
        # التحقق من كلمة المرور
        self.assertTrue(check_password_hash(saved_user.password, 'test123'))
    
    def test_user_permissions(self):
        """اختبار صلاحيات المستخدم"""
        # إنشاء مستخدم عادي
        user = User(
            username='normal_user',
            role=Role.USER
        )
        self.assertFalse(user.has_permission(Permission.MANAGE_USERS))
        self.assertFalse(user.has_permission(Permission.MANAGE_SCRIPTS))
        
        # إنشاء مشرف
        admin = User(
            username='admin_user',
            role=Role.ADMIN
        )
        self.assertTrue(admin.has_permission(Permission.MANAGE_USERS))
        self.assertTrue(admin.has_permission(Permission.MANAGE_SCRIPTS))
        
        # إنشاء سوبر أدمن
        super_admin = User(
            username='super_admin',
            role=Role.SUPER_ADMIN
        )
        self.assertTrue(super_admin.has_permission(Permission.MANAGE_USERS))
        self.assertTrue(super_admin.has_permission(Permission.MANAGE_SCRIPTS))
        self.assertTrue(super_admin.has_permission(Permission.MANAGE_SYSTEM))
    
    def test_script_creation(self):
        """اختبار إنشاء السكربت"""
        script = Script(
            name='test_script',
            description='سكربت اختبار',
            code='print("Hello, World!")',
            created_by=1,
            is_active=True
        )
        db.session.add(script)
        db.session.commit()
        
        # التحقق من حفظ السكربت
        saved_script = Script.query.filter_by(name='test_script').first()
        self.assertIsNotNone(saved_script)
        self.assertEqual(saved_script.description, 'سكربت اختبار')
        self.assertTrue(saved_script.is_active)
        self.assertIsInstance(saved_script.created_at, datetime)
    
    def test_script_validation(self):
        """اختبار التحقق من صحة السكربت"""
        # محاولة إنشاء سكربت بدون اسم
        script = Script(description='test')
        with self.assertRaises(ValueError):
            db.session.add(script)
            db.session.commit()
        db.session.rollback()
        
        # محاولة إنشاء سكربت بنفس الاسم
        script1 = Script(name='duplicate', description='first')
        script2 = Script(name='duplicate', description='second')
        db.session.add(script1)
        db.session.commit()
        with self.assertRaises(Exception):
            db.session.add(script2)
            db.session.commit()
    
    def test_run_log_creation(self):
        """اختبار إنشاء سجل التشغيل"""
        log = RunLog(
            user_id=1,
            script_id=1,
            status='success',
            output='تم التنفيذ بنجاح',
            execution_time=1.5
        )
        db.session.add(log)
        db.session.commit()
        
        # التحقق من حفظ السجل
        saved_log = RunLog.query.first()
        self.assertIsNotNone(saved_log)
        self.assertEqual(saved_log.status, 'success')
        self.assertEqual(saved_log.output, 'تم التنفيذ بنجاح')
        self.assertEqual(saved_log.execution_time, 1.5)
        self.assertIsInstance(saved_log.executed_at, datetime)
    
    def test_activity_log_creation(self):
        """اختبار إنشاء سجل النشاط"""
        log = ActivityLog(
            user_id=1,
            action='login',
            entity_type='user',
            entity_id=1,
            details='تسجيل دخول ناجح',
            ip_address='127.0.0.1'
        )
        db.session.add(log)
        db.session.commit()
        
        # التحقق من حفظ السجل
        saved_log = ActivityLog.query.first()
        self.assertIsNotNone(saved_log)
        self.assertEqual(saved_log.action, 'login')
        self.assertEqual(saved_log.details, 'تسجيل دخول ناجح')
        self.assertEqual(saved_log.ip_address, '127.0.0.1')
        self.assertIsInstance(saved_log.created_at, datetime)
    
    def test_relationships(self):
        """اختبار العلاقات بين النماذج"""
        # إنشاء مستخدم
        user = User(
            username='test_user',
            password=generate_password_hash('test123'),
            email='test@test.com',
            role=Role.USER
        )
        db.session.add(user)
        db.session.commit()
        
        # إنشاء سكربت
        script = Script(
            name='test_script',
            description='سكربت اختبار',
            created_by=user.id
        )
        db.session.add(script)
        db.session.commit()
        
        # إنشاء سجل تشغيل
        run_log = RunLog(
            user_id=user.id,
            script_id=script.id,
            status='success'
        )
        db.session.add(run_log)
        db.session.commit()
        
        # التحقق من العلاقات
        self.assertEqual(run_log.user, user)
        self.assertEqual(run_log.script, script)
        self.assertIn(run_log, user.run_logs)
        self.assertIn(run_log, script.run_logs)
    
    def test_cascade_delete(self):
        """اختبار الحذف المتتابع"""
        # إنشاء مستخدم وسكربت وسجلات
        user = User(username='test_user', role=Role.USER)
        db.session.add(user)
        db.session.commit()
        
        script = Script(name='test_script', created_by=user.id)
        db.session.add(script)
        db.session.commit()
        
        run_log = RunLog(user_id=user.id, script_id=script.id)
        activity_log = ActivityLog(user_id=user.id, action='test')
        db.session.add(run_log)
        db.session.add(activity_log)
        db.session.commit()
        
        # حذف المستخدم
        db.session.delete(user)
        db.session.commit()
        
        # التحقق من حذف السجلات المرتبطة
        self.assertIsNone(RunLog.query.first())
        self.assertIsNone(ActivityLog.query.first())
        
        # التحقق من عدم حذف السكربت (علاقة غير متتابعة)
        self.assertIsNotNone(Script.query.first())

if __name__ == '__main__':
    unittest.main() 