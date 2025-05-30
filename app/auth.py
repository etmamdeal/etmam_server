from functools import wraps
from flask import redirect, url_for, flash, request
from flask_login import current_user

def check_role_and_redirect():
    """التحقق من دور المستخدم وتوجيهه للصفحة المناسبة"""
    if not current_user.is_authenticated:
        return None
        
    if current_user.is_super_admin:
        return 'main.super_admin_dashboard'
    elif current_user.is_admin:
        return 'main.admin_dashboard'
    else:
        return 'main.client_dashboard'

def super_admin_required(f):
    """للتحقق من صلاحيات السوبر أدمن"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("يجب تسجيل الدخول أولاً.", "danger")
            return redirect(url_for('main.admin_login'))
            
        if not current_user.is_super_admin:
            flash("غير مصرح لك بالدخول هنا.", "danger")
            dashboard = check_role_and_redirect()
            return redirect(url_for(dashboard)) if dashboard else redirect(url_for('main.homepage'))
            
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """للتحقق من صلاحيات المشرف"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("يجب تسجيل الدخول أولاً.", "danger")
            return redirect(url_for('main.admin_login'))
            
        if not current_user.is_admin:
            flash("غير مصرح لك بالدخول هنا.", "danger")
            dashboard = check_role_and_redirect()
            return redirect(url_for(dashboard)) if dashboard else redirect(url_for('main.homepage'))
            
        return f(*args, **kwargs)
    return decorated_function

def client_required(f):
    """للتحقق من صلاحيات العميل"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("يجب تسجيل الدخول أولاً.", "danger")
            return redirect(url_for('main.client_login'))
            
        if current_user.is_admin or current_user.is_super_admin:
            flash("هذه الصفحة مخصصة للعملاء فقط.", "danger")
            dashboard = check_role_and_redirect()
            return redirect(url_for(dashboard))
            
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
                return redirect(url_for(dashboard)) if dashboard else redirect(url_for('main.homepage'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator 

# Moved from app.py and renamed for clarity
def require_admin_with_permission(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("يجب تسجيل الدخول أولاً.", "danger")
                return redirect(url_for('main.admin_login'))
                
            if current_user.is_super_admin:
                # Super admin might be accessing a regular admin page,
                # redirect them to super admin dashboard if the endpoint implies it's an admin area.
                if request.endpoint.startswith('admin_') and not request.endpoint.startswith('admin_super_'): # Avoid redirect loops if on super admin
                    # This logic might need refinement based on actual admin view function names
                    # to prevent unwanted redirects from super_admin_dashboard itself if it's also 'admin_...'
                    pass # Super admin has all permissions, so proceed. Or redirect if it's not a super_admin page.
                     # For now, let's assume super_admin can access all admin pages.
            elif current_user.is_admin:
                if not current_user.has_permission(permission):
                    flash("ليس لديك الصلاحية الكافية.", "danger")
                    return redirect(url_for('main.admin_dashboard')) # Redirect to their own dashboard
            else: # Not super_admin and not admin
                flash("غير مصرح لك بالدخول هنا.", "danger")
                # Redirect to homepage or client login, as admin_login might not be appropriate
                return redirect(url_for('main.homepage')) 
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator