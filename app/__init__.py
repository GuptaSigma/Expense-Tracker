import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, storage_uri=os.getenv('RATELIMIT_STORAGE_URI', 'memory://'),default_limits=["1500 per hour"])
mail = Mail()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'

    # Register blueprints
    from app.routes import main
    from app.auth import auth, init_google_oauth

    app.register_blueprint(main)
    app.register_blueprint(auth)
    
    # Initialize Google OAuth
    init_google_oauth(app)

    # Create tables on startup only when explicitly requested via AUTO_CREATE_TABLES.
    # On Render/production, prefer running `flask db upgrade` instead.
    if Config.OTP_DEV_MODE and not Config.DEBUG:
        app.logger.warning(
            "OTP_DEV_MODE is enabled but the app is running in production mode "
            "(FLASK_DEBUG=0). OTP will NOT be displayed in HTML responses. "
            "Disable OTP_DEV_MODE in production to suppress this warning."
        )

    if app.config.get('AUTO_CREATE_TABLES', False):
        with app.app_context():
            db.create_all()

    return app


# Backward-compatible WSGI entrypoint so `gunicorn app:app` also works.
app = create_app()
