from flask import Flask

from config import Config


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    from app.models.db import init_app as init_db
    init_db(app)

    # --- Application blueprints -----------------------------------
    from app.auth.routes import auth_bp
    from app.routes.public import public_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.patients import patients_bp
    from app.routes.doctors import doctors_bp
    from app.routes.appointments import appointments_bp
    from app.routes.departments import departments_bp
    from app.routes.staff import staff_bp
    from app.routes.medical_records import records_bp
    from app.routes.settings import settings_bp
    from app.routes.billing import billing_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(doctors_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(departments_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(reports_bp)

    if app.config.get("SECURITY_LAB_ENABLED", False):
        from security_lab.broken_password_recovery.routes import vuln_recovery_bp
        from security_lab.insecure_session_management.routes import vuln_session_bp

        app.register_blueprint(vuln_recovery_bp)
        app.register_blueprint(vuln_session_bp)

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; connect-src 'self'",
        )
        return response

    @app.context_processor
    def inject_globals():
        import secrets
        from flask import session
        from app.auth.utils import current_user

        def get_csrf_token():
            if "_csrf_token" not in session:
                session["_csrf_token"] = secrets.token_hex(16)
            return session["_csrf_token"]

        return {"current_user": current_user(), "csrf_token": get_csrf_token}

    return app