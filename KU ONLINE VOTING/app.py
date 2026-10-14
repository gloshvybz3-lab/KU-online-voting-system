import os
from flask import Flask, render_template, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from config import Config, DevelopmentConfig
from models import db, Student, Admin, Notification, utc_now

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    csrf = CSRFProtect(app)
    limiter = Limiter(key_func=get_remote_address, default_limits=["300 per minute"], storage_uri=app.config.get("RATELIMIT_STORAGE_URI", "memory://"))
    limiter.init_app(app)

    # Ensure static and upload directories exist
    os.makedirs(app.config.get('UPLOAD_FOLDER', os.path.join(app.root_path, 'static', 'uploads')), exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.student_login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        """Dispatches user loading between Student and Admin models."""
        if not user_id:
            return None
        try:
            if user_id.startswith('student_'):
                student_pk = int(user_id.split('_')[1])
                return db.session.get(Student, student_pk)
            elif user_id.startswith('admin_'):
                admin_pk = int(user_id.split('_')[1])
                return db.session.get(Admin, admin_pk)
            # Legacy numeric fallback
            return db.session.get(Student, int(user_id))
        except Exception:
            return None

    # Context processors for global template availability
    @app.context_processor
    def inject_global_vars():
        pinned_notifs = []
        try:
            pinned_notifs = Notification.query.filter_by(is_pinned=True).order_by(Notification.created_at.desc()).limit(3).all()
        except Exception:
            pass
        return {
            'now': utc_now(),
            'university_name': app.config.get('UNIVERSITY_NAME', 'Kampala University'),
            'university_abbr': app.config.get('UNIVERSITY_ABBR', 'KU'),
            'campuses': app.config.get('CAMPUSES', []),
            'faculties': app.config.get('FACULTIES', []),
            'pinned_notifications': pinned_notifs
        }

    # Register Blueprints
    from blueprints.auth import auth_bp
    from blueprints.voting import voting_bp
    from blueprints.admin import admin_bp
    from blueprints.results import results_bp
    from blueprints.main import main_bp
    from blueprints.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(voting_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(results_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    # Read-only JSON assistant endpoint is authenticated by rate limiting and
    # does not mutate application state, so it is intentionally CSRF-exempt.
    csrf.exempt(api_bp)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(self), microphone=()")
        if not app.debug:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    # Error handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    # Development convenience only. Production databases must be migrated with
    # the migration tooling; workers should never race to mutate the schema.
    if app.config.get("AUTO_CREATE_TABLES", False):
        with app.app_context():
            db.create_all()

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
