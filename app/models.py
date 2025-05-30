from datetime import datetime, timedelta
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import json

db = SQLAlchemy()

class Permission:
    # تعريف الصلاحيات المتاحة
    VIEW_DASHBOARD = 'view_dashboard'  # عرض لوحة التحكم
    MANAGE_SCRIPTS = 'manage_scripts'  # إدارة السكربتات
    ASSIGN_SCRIPTS = 'assign_scripts'  # تخصيص السكربتات للمستخدمين
    MANAGE_USERS = 'manage_users'  # إدارة المستخدمين
    MANAGE_ADMINS = 'manage_admins'  # إدارة المشرفين (خاص بالسوبر أدمن)
    VIEW_LOGS = 'view_logs'  # عرض السجلات
    MANAGE_SETTINGS = 'manage_settings'  # إدارة إعدادات النظام

    @staticmethod
    def get_all_permissions():
        return [
            Permission.VIEW_DASHBOARD,
            Permission.MANAGE_SCRIPTS,
            Permission.ASSIGN_SCRIPTS,
            Permission.MANAGE_USERS,
            Permission.MANAGE_ADMINS,
            Permission.VIEW_LOGS,
            Permission.MANAGE_SETTINGS
        ]

class Role:
    # تعريف الأدوار المتاحة
    SUPER_ADMIN = 'super_admin'
    ADMIN = 'admin'
    USER = 'user'

    @staticmethod
    def get_default_permissions(role):
        if role == Role.SUPER_ADMIN:
            return Permission.get_all_permissions()
        elif role == Role.ADMIN:
            return [
                Permission.VIEW_DASHBOARD,
                Permission.MANAGE_SCRIPTS,
                Permission.ASSIGN_SCRIPTS,
                Permission.MANAGE_USERS,
                Permission.VIEW_LOGS
            ]
        else:
            return []

class Script(db.Model):
    """نموذج لتخزين معلومات السكربتات"""
    __tablename__ = 'scripts'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    parameters = db.Column(db.JSON)  # لتخزين معلومات المتغيرات المطلوبة
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # العلاقات
    users = db.relationship('UserScript', back_populates='script')
    
    def __repr__(self):
        return f'<Script {self.name}>'

class UserScript(db.Model):
    __tablename__ = 'user_script'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id', ondelete='CASCADE'), primary_key=True)
    config_data = db.Column(db.Text, default='{}')
    assigned_at = db.Column(db.DateTime, default=datetime.now)
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    
    # العلاقات
    user = db.relationship('User', foreign_keys=[user_id], overlaps="scripts,users")
    script = db.relationship('Script', foreign_keys=[script_id], overlaps="scripts,users")
    assigner = db.relationship('User', foreign_keys=[assigned_by])

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default=Role.USER)
    permissions = db.Column(db.Text, default='[]')  # JSON string of permissions
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime, nullable=True)

    @property
    def is_admin(self):
        """التحقق من كون المستخدم مشرفاً"""
        return self.role in [Role.ADMIN, Role.SUPER_ADMIN]

    @property
    def is_super_admin(self):
        """التحقق من كون المستخدم سوبر أدمن"""
        return self.role == Role.SUPER_ADMIN

    def get_permissions(self):
        """الحصول على قائمة الصلاحيات"""
        try:
            return json.loads(self.permissions)
        except:
            return []

    def set_permissions(self, permissions):
        """تعيين قائمة الصلاحيات"""
        self.permissions = json.dumps(list(set(permissions)))  # إزالة التكرار

    def has_permission(self, permission):
        """التحقق من وجود صلاحية معينة"""
        if self.is_super_admin:
            return True
        return permission in self.get_permissions()

    def update_last_login(self):
        """تحديث وقت آخر تسجيل دخول"""
        self.last_login = datetime.now()
        db.session.commit()

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        # تعيين الصلاحيات الافتراضية حسب الدور
        if not self.permissions or self.permissions == '[]':
            self.set_permissions(Role.get_default_permissions(self.role))

class RunLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id', name='fk_runlog_script'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', name='fk_runlog_user'), nullable=False)
    user_script_id = db.Column(db.Integer, db.ForeignKey('user_script.user_id', name='fk_runlog_user_script'), nullable=True)
    status = db.Column(db.String(20), nullable=False)  # success, error
    output = db.Column(db.Text)
    error = db.Column(db.Text)
    executed_at = db.Column(db.DateTime, default=datetime.now)
    
    # العلاقات
    user = db.relationship('User', backref='run_logs')
    script = db.relationship('Script', backref='run_logs')
    user_script = db.relationship('UserScript', backref='run_logs', primaryjoin="and_(RunLog.user_script_id==UserScript.user_id, RunLog.script_id==UserScript.script_id)")

class ProductType:
    SCRIPT = 'script'
    EBOOK = 'ebook'
    DATABASE = 'database'

    @staticmethod
    def get_all_types():
        return [
            ProductType.SCRIPT,
            ProductType.EBOOK,
            ProductType.DATABASE
        ]

class SubscriptionPeriod:
    ONE_MONTH = 1
    THREE_MONTHS = 3
    SIX_MONTHS = 6
    TWELVE_MONTHS = 12

    @staticmethod
    def get_all_periods():
        return [
            SubscriptionPeriod.ONE_MONTH,
            SubscriptionPeriod.THREE_MONTHS,
            SubscriptionPeriod.SIX_MONTHS,
            SubscriptionPeriod.TWELVE_MONTHS
        ]

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # script, ebook, database
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    last_modified = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    last_modified_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # للسكربتات فقط
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id'), nullable=True)
    
    # العلاقات
    creator = db.relationship('User', foreign_keys=[created_by], backref='products_created')
    modifier = db.relationship('User', foreign_keys=[last_modified_by], backref='products_modified')
    # script relationship is now handled by the backref 'associated_script' from Script model
    subscriptions = db.relationship('Subscription', backref='product', lazy='dynamic')

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    period_months = db.Column(db.Integer, nullable=False)  # 1, 3, 6, 12
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # العلاقات
    user = db.relationship('User', backref='subscriptions')

    def __init__(self, **kwargs):
        super(Subscription, self).__init__(**kwargs)
        if not self.end_date:
            self.end_date = self.start_date + timedelta(days=30 * self.period_months)

    @property
    def is_expired(self):
        return datetime.now() > self.end_date

class Ebook(db.Model):
    __tablename__ = 'ebooks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50))
    file_path = db.Column(db.String(200), nullable=False)
    cover_path = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<Ebook {self.title}>'

class Database(db.Model):
    __tablename__ = 'databases'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(50))
    size = db.Column(db.String(50))
    file_path = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<Database {self.name}>'
