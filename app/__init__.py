import os
from flask import Flask
from .config import config_by_name
from .extensions import db, login_manager, csrf


def create_app(config_name=None):
    """Application factory for the FindIt app."""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Ensure upload folder exists
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Register blueprints
    from .blueprints.auth import auth_bp
    from .blueprints.main import main_bp
    from .blueprints.items import items_bp
    from .blueprints.claims import claims_bp
    from .blueprints.search import search_bp
    from .blueprints.messaging import messaging_bp
    from .blueprints.security import security_bp
    from .blueprints.admin import admin_bp
    from .blueprints.locations import locations_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(items_bp, url_prefix='/items')
    app.register_blueprint(claims_bp, url_prefix='/claims')
    app.register_blueprint(search_bp, url_prefix='/search')
    app.register_blueprint(messaging_bp, url_prefix='/messaging')
    app.register_blueprint(security_bp, url_prefix='/security')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(locations_bp, url_prefix='/locations')

    # User loader for Flask-Login
    from .models.auth import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Create tables
    with app.app_context():
        from . import models  # noqa: F401 — import to register all models
        db.create_all()

    return app
