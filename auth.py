from functools import wraps
from flask import redirect, url_for, flash, request
from flask_login import current_user

def check_role_and_redirect():
    """التحقق من دور المستخدم وتوجيهه للصفحة المناسبة"""
    if not current_user.is_authenticated:
        return None
        
    if current_user.is_super_admin:
        return 'main.super_admin_dashboard'
    else:
        return 'main.dashboard'

def super_admin_required(f):
    """للتحقق من صلاحيات السوبر أدمن"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("يجب تسجيل الدخول أولاً.", "danger")
            return redirect(url_for('main.admin_login'))
            
        if not current_user.is_super_admin:
            flash("غير مصرح لك بالدخول هنا.", "danger")
            return redirect(url_for('main.index'))
            
        return f(*args, **kwargs)
    return decorated_function

def client_required(f):
    """للتحقق من صلاحيات العميل"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("يجب تسجيل الدخول أولاً.", "danger")
            return redirect(url_for('main.client_login'))
            
        if current_user.is_super_admin:
            flash("هذه الصفحة مخصصة للعملاء فقط.", "danger")
            dashboard = check_role_and_redirect()
            return redirect(url_for(dashboard)) if dashboard else redirect(url_for('main.index'))
            
        return f(*args, **kwargs)
    return decorated_function

def check_permission(permission):
    """للتحقق من صلاحيات محددة"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("يجب تسجيل الدخول أولاً.", "danger")
                return redirect(url_for('main.admin_login'))
                
            if not current_user.has_permission(permission):
                flash("ليس لديك الصلاحية الكافية.", "danger")
                dashboard = check_role_and_redirect()
                return redirect(url_for(dashboard)) if dashboard else redirect(url_for('main.index'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# The require_admin_with_permission decorator (previously check_admin_permission)
# has been removed as it was found to be unused in app/app.py.
# The combination of @admin_required and @check_permission(Permission.NAME)
# is used instead for routes requiring admin role and specific permissions.