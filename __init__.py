"""
حزمة etmam_server
---------------
""" 

from flask import Flask, current_app, g, request # Added current_app, g, request
from flask_babel import Babel # Added Babel import
from .extensions import db, migrate, socketio, login_manager, mail # Import mail
from celery_app import make_celery # Import make_celery
import os

# تهيئة قاعدة البيانات والإضافات - Removed, instances are in extensions.py
# Initialize Babel here, but it will be configured in create_app
babel = Babel()
celery = None # Placeholder for celery instance

def create_app():
    app = Flask(__name__, instance_path=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance'))
    os.makedirs(app.instance_path, exist_ok=True) # Ensure instance folder exists

    # تكوين التطبيق
    # Load config from config.py based on FLASK_ENV or default to Config
    if os.environ.get('FLASK_ENV') == 'production':
        app.config.from_object('config.ProductionConfig')
    elif os.environ.get('FLASK_ENV') == 'testing':
        app.config.from_object('config.TestingConfig')
    else: # Default to development
        app.config.from_object('config.DevelopmentConfig')
        # Fallback for essential keys if not in DevelopmentConfig explicitly for some reason
        app.config.setdefault('SECRET_KEY', os.environ.get('SECRET_KEY', 'dev'))
        app.config.setdefault('SQLALCHEMY_DATABASE_URI', os.environ.get('DATABASE_URL', 'sqlite:////app/instance/development.db'))
        app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='gevent')
    login_manager.init_app(app)
    babel.init_app(app) # Initialize Babel with the app
    mail.init_app(app) # Initialize Mail with the app

    # Initialize Celery
    global celery
    celery = make_celery(app)

    # login_manager.login_view = 'main.client_login' # This is already set in extensions.py
    
    # استيراد النماذج
    from .models import User, Script, UserScript, RunLog, Role, Permission # This should be fine now
    
    # استيراد وتسجيل المسارات
    from .app import bp # Assuming bp is defined in app.py
    # from app import create_super_admin # create_super_admin might need to be moved or re-evaluated
    app.register_blueprint(bp)
    
    # إنشاء قاعدة البيانات
    # with app.app_context():
    #     db.create_all() # Commenting out to let Flask-Migrate handle it
        
        # إنشاء حساب السوبر أدمن إذا لم يكن موجوداً
        # create_super_admin() # Commenting out for now, to be addressed separately if needed
    
    return app

@babel.localeselector
def get_locale():
    # For now, use a simple logic: session, then default.
    # Later, can add user preference from DB or Accept-Language header.
    if 'locale' in g: # Check if set by a before_request handler perhaps
        return g.locale
    # For testing, one might allow forcing via query parameter:
    # if request.args.get('lang'):
    #     session['locale'] = request.args.get('lang')
    # return session.get('locale', current_app.config['BABEL_DEFAULT_LOCALE'])
    return current_app.config['BABEL_DEFAULT_LOCALE'] # Default to Arabic for now

# Optional: Store chosen locale in g for easy access during the request
# @current_app.before_request
# def before_request():
# g.locale = get_locale()
# This might be redundant if get_locale() is simple and called once per request by Babel.
# If get_locale() becomes complex (e.g. DB lookup), caching it in `g` is good.
# For now, the direct return in get_locale is fine.