"""
SECURE authentication helpers used by the main MediCore application.

Session tokens here are generated with secrets.token_urlsafe (CSPRNG),
stored server-side in the `sessions` table, carried to the browser only
as an httponly/samesite cookie, and can be revoked individually. This is
the deliberate contrast to the broken session logic in
security_lab/insecure_session_management/.
"""

import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import current_app, g, redirect, request, session, url_for, flash

from app.models.db import get_db


SESSION_COOKIE_NAME = "medicore_session"


def generate_secure_session_id():
    # 256 bits of entropy from the OS CSPRNG - not predictable, not sequential.
    return secrets.token_urlsafe(32)


def create_session(user_id):
    db = get_db()
    token = generate_secure_session_id()
    expires_at = datetime.utcnow() + timedelta(
        seconds=current_app.config["PERMANENT_SESSION_LIFETIME"]
    )
    db.execute(
        "INSERT INTO sessions (id, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires_at.isoformat()),
    )
    db.commit()
    return token


def revoke_session(token):
    db = get_db()
    db.execute("UPDATE sessions SET revoked = 1 WHERE id = ?", (token,))
    db.commit()


def revoke_all_sessions_for_user(user_id):
    """Called on password change — secure systems invalidate every
    existing session so a stolen session cookie stops working."""
    db = get_db()
    db.execute("UPDATE sessions SET revoked = 1 WHERE user_id = ?", (user_id,))
    db.commit()


def get_session_user(token):
    if not token:
        return None
    db = get_db()
    row = db.execute(
        "SELECT u.*, s.id AS session_token, s.expires_at AS session_expires_at "
        "FROM sessions s JOIN users u ON u.id = s.user_id "
        "WHERE s.id = ? AND s.revoked = 0 AND s.expires_at > ? AND u.is_active = 1",
        (token, datetime.utcnow().isoformat()),
    ).fetchone()
    return row


def current_user():
    if "user" in g:
        return g.user
    token = request.cookies.get(SESSION_COOKIE_NAME)
    g.user = get_session_user(token) if token else None
    return g.user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                flash("Please sign in to continue.", "warning")
                return redirect(url_for("auth.login", next=request.path))
            if user["role"] not in roles:
                flash("You do not have permission to view that page.", "danger")
                return redirect(url_for("dashboard.overview"))
            return view(*args, **kwargs)

        return wrapped

    return decorator
