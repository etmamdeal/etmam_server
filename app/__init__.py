"""
حزمة etmam_server
---------------
""" 

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_login import LoginManager
import os

# تهيئة قاعدة البيانات والإضافات
db = SQLAlchemy()
migrate = Migrate()
socketio = SocketIO()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # تكوين التطبيق
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # تهيئة الإضافات
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='gevent')
    login_manager.init_app(app)
    login_manager.login_view = 'main.client_login'
    
    # استيراد النماذج
    from models import User, Script, UserScript, RunLog, Role, Permission
    
    # استيراد وتسجيل المسارات
    from app import bp, create_super_admin
    app.register_blueprint(bp)
    
    # إنشاء قاعدة البيانات
    with app.app_context():
        db.create_all()
        
        # إنشاء حساب السوبر أدمن إذا لم يكن موجوداً
        create_super_admin()
    
    return app 