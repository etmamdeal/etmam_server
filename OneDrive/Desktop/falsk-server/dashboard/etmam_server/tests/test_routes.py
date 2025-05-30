"""
اختبارات المسارات في نظام إتمام
-------------------------------

يحتوي هذا الملف على اختبارات شاملة لجميع مسارات التطبيق:
- اختبارات المصادقة
- اختبارات لوحة التحكم
- اختبارات إدارة السكربتات
- اختبارات إدارة المستخدمين
"""

import unittest
from flask import url_for
from app import app, db
from models import User, Script, RunLog, Role, Permission
from werkzeug.security import generate_password_hash
import json

class TestRoutes(unittest.TestCase):
    """اختبارات المسارات الرئيسية في التطبيق"""
    
    def setUp(self):
        """إعداد بيئة الاختبار قبل كل اختبار"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
        
        # إنشاء مستخدم اختبار
        self.test_user = User(
            username='test_user',
            password=generate_password_hash('test123'),
            email='test@test.com',
            full_name='مستخدم اختبار',
            role=Role.USER,
            is_active=True
        )
        
        # إنشاء مشرف اختبار
        self.test_admin = User(
            username='test_admin',
            password=generate_password_hash('admin123'),
            email='admin@test.com',
            full_name='مشرف اختبار',
            role=Role.ADMIN,
            is_active=True
        )
        
        db.session.add(self.test_user)
        db.session.add(self.test_admin)
        db.session.commit()
    
    def tearDown(self):
        """تنظيف بيئة الاختبار بعد كل اختبار"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def login(self, username, password):
        """تسجيل دخول مستخدم"""
        return self.client.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)
    
    def logout(self):
        """تسجيل خروج المستخدم"""
        return self.client.get('/logout', follow_redirects=True)
    
    def test_home_page(self):
        """اختبار الصفحة الرئيسية"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('نظام إتمام', response.data.decode())
    
    def test_login_page(self):
        """اختبار صفحة تسجيل الدخول"""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn('تسجيل الدخول', response.data.decode())
    
    def test_valid_login(self):
        """اختبار تسجيل دخول صحيح"""
        response = self.login('test_user', 'test123')
        self.assertEqual(response.status_code, 200)
        self.assertIn('تم تسجيل الدخول بنجاح', response.data.decode())
    
    def test_invalid_login(self):
        """اختبار تسجيل دخول خاطئ"""
        response = self.login('wrong_user', 'wrong_pass')
        self.assertIn('خطأ في اسم المستخدم أو كلمة المرور', response.data.decode())
    
    def test_logout(self):
        """اختبار تسجيل الخروج"""
        self.login('test_user', 'test123')
        response = self.logout()
        self.assertEqual(response.status_code, 200)
        self.assertIn('تم تسجيل الخروج بنجاح', response.data.decode())
    
    def test_admin_dashboard_access(self):
        """اختبار الوصول للوحة تحكم المشرف"""
        # محاولة الوصول بدون تسجيل دخول
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 302)  # إعادة توجيه لصفحة تسجيل الدخول
        
        # تسجيل دخول كمستخدم عادي
        self.login('test_user', 'test123')
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 403)  # غير مصرح
        
        # تسجيل دخول كمشرف
        self.logout()
        self.login('test_admin', 'admin123')
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 200)
        self.assertIn('لوحة تحكم المشرف', response.data.decode())
    
    def test_script_management(self):
        """اختبار إدارة السكربتات"""
        self.login('test_admin', 'admin123')
        
        # إنشاء سكربت جديد
        response = self.client.post('/admin/scripts/add', data=dict(
            name='test_script',
            description='سكربت اختبار',
            code='print("Hello, World!")',
            is_active=True
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('تم إضافة السكربت بنجاح', response.data.decode())
        
        # التحقق من وجود السكربت
        script = Script.query.filter_by(name='test_script').first()
        self.assertIsNotNone(script)
        self.assertEqual(script.description, 'سكربت اختبار')
        
        # تعديل السكربت
        response = self.client.post(f'/admin/scripts/edit/{script.id}', data=dict(
            name='test_script_updated',
            description='سكربت اختبار معدل',
            code='print("Updated!")',
            is_active=True
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('تم تحديث السكربت بنجاح', response.data.decode())
        
        # حذف السكربت
        response = self.client.post(f'/admin/scripts/delete/{script.id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('تم حذف السكربت بنجاح', response.data.decode())
    
    def test_user_management(self):
        """اختبار إدارة المستخدمين"""
        self.login('test_admin', 'admin123')
        
        # إنشاء مستخدم جديد
        response = self.client.post('/admin/users/add', data=dict(
            username='new_user',
            password='user123',
            email='new@test.com',
            full_name='مستخدم جديد',
            role=Role.USER,
            is_active=True
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('تم إضافة المستخدم بنجاح', response.data.decode())
        
        # التحقق من وجود المستخدم
        user = User.query.filter_by(username='new_user').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'new@test.com')
        
        # تعديل المستخدم
        response = self.client.post(f'/admin/users/edit/{user.id}', data=dict(
            username='new_user_updated',
            email='updated@test.com',
            full_name='مستخدم معدل',
            role=Role.USER,
            is_active=True
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('تم تحديث المستخدم بنجاح', response.data.decode())
        
        # تعطيل المستخدم
        response = self.client.post(f'/admin/users/toggle/{user.id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('تم تحديث حالة المستخدم بنجاح', response.data.decode())
    
    def test_error_pages(self):
        """اختبار صفحات الخطأ"""
        # صفحة 404
        response = self.client.get('/page_not_exists')
        self.assertEqual(response.status_code, 404)
        self.assertIn('الصفحة غير موجودة', response.data.decode())
        
        # صفحة 403
        self.login('test_user', 'test123')
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 403)
        self.assertIn('غير مصرح لك', response.data.decode())

if __name__ == '__main__':
    unittest.main() 