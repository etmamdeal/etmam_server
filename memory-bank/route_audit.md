# مراجعة المسارات والقوالب

## المسارات المفقودة
المسارات التالية مستخدمة في القوالب ولكنها غير معرفة في `app.py`:

1. `main.super_admin_dashboard` - مستخدم في:
   - templates/base.html (السطر 48)
   - يحتاج إلى إضافة المسار والقالب

2. `main.admin_dashboard` - مستخدم في:
   - templates/base.html (السطر 54)
   - يحتاج إلى إضافة المسار والقالب

3. `main.client_dashboard` - مستخدم في:
   - templates/base.html (السطر 60)
   - يحتاج إلى إضافة المسار والقالب

4. `main.my_scripts` - مستخدم في:
   - templates/base.html (السطر 65)
   - يحتاج إلى إضافة المسار والقالب

5. `main.script_logs` - مستخدم في:
   - templates/base.html (السطر 70)
   - يحتاج إلى إضافة المسار والقالب

6. `main.profile` - مستخدم في:
   - templates/base.html (السطر 76)
   - يحتاج إلى إضافة المسار والقالب

## المسارات المطلوب إضافتها
```python
@bp.route('/super-admin')
@super_admin_required
def super_admin_dashboard():
    return render_template('super_admin_dashboard.html')

@bp.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@bp.route('/dashboard')
@client_required
def client_dashboard():
    return render_template('client_dashboard.html')

@bp.route('/my-scripts')
@client_required
def my_scripts():
    return render_template('my_scripts.html')

@bp.route('/script-logs')
@client_required
def script_logs():
    return render_template('script_logs.html')

@bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html')
```

## القوالب المطلوبة
يجب إنشاء القوالب التالية في مجلد `templates`:
1. `super_admin_dashboard.html`
2. `admin_dashboard.html`
3. `client_dashboard.html`
4. `my_scripts.html`
5. `script_logs.html`
6. `profile.html`

## ملاحظات إضافية
- تم تعطيل تسجيل المشرفين الجدد
- تم تقييد الوصول إلى لوحة التحكم للسوبر أدمن فقط
- يجب التأكد من وجود الديكوريتورز المناسبة (@super_admin_required, @admin_required, @client_required)
- يجب التأكد من وجود جميع القوالب قبل تشغيل التطبيق 