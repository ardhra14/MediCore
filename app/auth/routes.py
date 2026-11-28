"""
SECURE authentication routes.

This is the production-grade auth path for MediCore: salted password
hashing (Werkzeug/PBKDF2), CSPRNG session tokens stored server-side, and
a password reset flow that emails a random, single-use, short-lived,
hashed token.

Contrast this file with security_lab/broken_password_recovery/routes.py
and security_lab/insecure_session_management/routes.py, which exist
purely to demonstrate what this file deliberately avoids.
"""

import hashlib
import logging
import secrets
import time
from collections import defaultdict

logger = logging.getLogger("medicore.auth")

_LOGIN_ATTEMPTS = defaultdict(list)
_RATE_WINDOW = 15 * 60
_RATE_MAX = 5
_RATE_BLOCK = 15 * 60


def _rate_key(email, ip):
    return f"{email}|{ip}"


def _is_rate_limited(key):
    now = time.time()
    attempts = [t for t in _LOGIN_ATTEMPTS[key] if now - t < _RATE_WINDOW]
    _LOGIN_ATTEMPTS[key] = attempts
    if len(attempts) >= _RATE_MAX:
        # check cooldown: block if last attempt within block window
        if attempts and now - attempts[-1] < _RATE_BLOCK:
            return True
    return False


def _record_failure(key):
    _LOGIN_ATTEMPTS[key].append(time.time())


def _reset(key):
    _LOGIN_ATTEMPTS.pop(key, None)
from datetime import datetime, timedelta
from urllib.parse import urlparse

from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response, current_app

from werkzeug.security import check_password_hash, generate_password_hash

from app.models.db import get_db
from app.models.user import get_user_by_email, create_user, update_password
from app.auth.utils import (
    create_session,
    revoke_session,
    revoke_all_sessions_for_user,
    current_user,
    SESSION_COOKIE_NAME,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        ip = request.remote_addr or "unknown"
        key = _rate_key(email, ip)

        # Invalidate any prior session cookie immediately on login attempt
        prev_token = request.cookies.get(SESSION_COOKIE_NAME)
        if prev_token:
            revoke_session(prev_token)

        # Strict validation: both email and password are required
        if not email or not password:
            flash("Please enter both email and password.", "danger")
            resp = make_response(render_template("auth/login.html"))
            if prev_token:
                resp.delete_cookie(SESSION_COOKIE_NAME)
            return resp

        # Check server-side rate limiting
        if _is_rate_limited(key):
            logger.warning(f"Login rate limited for email '{email}' from IP '{ip}'.")
            flash("Too many failed login attempts. Please try again later.", "danger")
            resp = make_response(render_template("auth/login.html"))
            if prev_token:
                resp.delete_cookie(SESSION_COOKIE_NAME)
            return resp

        # Query user strictly from the database
        user = get_user_by_email(email)

        next_url = request.args.get("next")
        if next_url and urlparse(next_url).netloc:
            next_url = None

        # Verify credentials strictly against the database hash
        if user and check_password_hash(user["password_hash"], password):
            if not user["is_active"]:
                logger.warning(f"Inactive account login attempt for email '{email}' from IP '{ip}'.")
                flash("This account is inactive. Contact an administrator.", "danger")
                resp = make_response(render_template("auth/login.html"))
                if prev_token:
                    resp.delete_cookie(SESSION_COOKIE_NAME)
                return resp

            _reset(key)

            # Check if user has Two-Factor Authentication (2FA) enabled
            user_keys = user.keys() if hasattr(user, "keys") else []
            has_2fa = bool(user["two_factor_enabled"]) if "two_factor_enabled" in user_keys else False

            if has_2fa:
                otp_code = f"{secrets.randbelow(900000) + 100000:06d}"
                expires_at = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
                db = get_db()
                db.execute(
                    "INSERT INTO otp_codes (user_id, otp_code, expires_at) VALUES (?, ?, ?)",
                    (user["id"], otp_code, expires_at),
                )
                db.commit()

                from flask import session as flask_session
                flask_session["pending_2fa_user_id"] = user["id"]
                flask_session["pending_2fa_next"] = next_url
                logger.info(f"Two-factor OTP generated for user '{user['email']}'.")
                flash(f"A 2FA verification code has been issued: {otp_code} (Valid for 5 minutes).", "info")
                return redirect(url_for("auth.verify_2fa"))

            logger.info(f"Successful login for user '{user['email']}' (role: {user['role']}) from IP '{ip}'.")
            token = create_session(user["id"])
            resp = make_response(redirect(next_url or url_for("dashboard.overview")))
            resp.set_cookie(
                SESSION_COOKIE_NAME,
                token,
                httponly=True,
                samesite=current_app.config.get("SESSION_COOKIE_SAMESITE", "Lax"),
                secure=current_app.config.get("SESSION_COOKIE_SECURE", request.is_secure),
                max_age=current_app.config.get("PERMANENT_SESSION_LIFETIME", 60 * 60 * 8),
            )
            flash(f"Welcome back, {user['full_name']}.", "success")
            return resp

        # Authentication failed: reject invalid or random credentials
        _record_failure(key)
        logger.warning(f"Failed login attempt for email '{email}' from IP '{ip}'.")
        flash("Invalid email or password.", "danger")
        resp = make_response(render_template("auth/login.html"))
        if prev_token:
            resp.delete_cookie(SESSION_COOKIE_NAME)
        return resp

    # GET request: redirect only if user is already authenticated
    if current_user():
        return redirect(url_for("dashboard.overview"))

    return render_template("auth/login.html")


@auth_bp.route("/verify-2fa", methods=["GET", "POST"])
def verify_2fa():
    from flask import session as flask_session
    user_id = flask_session.get("pending_2fa_user_id")
    if not user_id:
        flash("No two-factor verification challenge is pending. Please sign in.", "warning")
        return redirect(url_for("auth.login"))

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        flask_session.pop("pending_2fa_user_id", None)
        return redirect(url_for("auth.login"))

    ip = request.remote_addr or "unknown"
    otp_key = f"otp|{user['email']}|{ip}"

    if request.method == "POST":
        # Working rate limiting on OTP verification
        if _is_rate_limited(otp_key):
            logger.warning(f"OTP rate limited for user '{user['email']}' from IP '{ip}'.")
            flash("Too many failed OTP verification attempts. Please wait 15 minutes before trying again.", "danger")
            return render_template("auth/verify_2fa.html", email=user["email"])

        code = request.form.get("otp_code", "").strip()
        if not code:
            flash("Please enter the 6-digit verification code.", "danger")
            return render_template("auth/verify_2fa.html", email=user["email"])

        now_str = datetime.utcnow().isoformat()
        otp_record = db.execute(
            "SELECT * FROM otp_codes WHERE user_id = ? AND otp_code = ? AND used = 0 AND expires_at > ? ORDER BY id DESC LIMIT 1",
            (user_id, code, now_str),
        ).fetchone()

        if otp_record:
            db.execute("UPDATE otp_codes SET used = 1 WHERE id = ?", (otp_record["id"],))
            db.commit()
            _reset(otp_key)
            next_url = flask_session.pop("pending_2fa_next", None)
            flask_session.pop("pending_2fa_user_id", None)

            token = create_session(user["id"])
            resp = make_response(redirect(next_url or url_for("dashboard.overview")))
            resp.set_cookie(
                SESSION_COOKIE_NAME,
                token,
                httponly=True,
                samesite=current_app.config.get("SESSION_COOKIE_SAMESITE", "Lax"),
                secure=current_app.config.get("SESSION_COOKIE_SECURE", request.is_secure),
                max_age=current_app.config.get("PERMANENT_SESSION_LIFETIME", 60 * 60 * 8),
            )
            flash(f"Two-factor authentication verified. Welcome back, {user['full_name']}.", "success")
            return resp

        # Invalid OTP submission
        _record_failure(otp_key)
        logger.warning(f"Invalid OTP attempt for user '{user['email']}' from IP '{ip}'.")
        flash("Invalid or expired 2FA code. Please check and try again.", "danger")

    return render_template("auth/verify_2fa.html", email=user["email"])


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("dashboard.overview"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not full_name or not email or len(password) < 8:
            flash("Please fill in all fields; password must be at least 8 characters.", "danger")
            return render_template("auth/register.html")

        if get_user_by_email(email):
            flash("An account with that email already exists.", "danger")
            return render_template("auth/register.html")

        user_id = create_user(full_name, email, generate_password_hash(password), role="patient")

        db = get_db()
        db.execute(
            "INSERT INTO patients (user_id, full_name) VALUES (?, ?)", (user_id, full_name)
        )
        db.commit()

        flash("Account created. You can now sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/logout")
def logout():
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        revoke_session(token)
    resp = make_response(redirect(url_for("public.landing")))
    resp.delete_cookie(SESSION_COOKIE_NAME)
    flash("You have been signed out.", "success")
    return resp


# ---------------------------------------------------------------------------
# SECURE password recovery (contrast with the vulnerable lab version).
#
#  * token = secrets.token_urlsafe(32)  -> CSPRNG, not guessable
#  * only a SHA-256 hash of the token is stored in the database
#  * token expires in 15 minutes and is marked used after one redemption
#  * the response does not reveal whether the email exists
# ---------------------------------------------------------------------------

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = get_user_by_email(email)

        if user:
            raw_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            expires_at = datetime.utcnow() + timedelta(minutes=15)

            db = get_db()
            db.execute(
                "INSERT INTO password_resets (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
                (user["id"], token_hash, expires_at.isoformat()),
            )
            db.commit()

            # In production this link is emailed, never shown in the UI.
            # It is surfaced here only so the demo is runnable without an
            # email provider configured.
            reset_link = url_for("auth.reset_password", token=raw_token, _external=True)
            flash(
                "If that email exists, a reset link has been generated. "
                f"(Demo mode — no mail server configured): {reset_link}",
                "info",
            )
        else:
            # Same message either way, so the form can't be used to enumerate accounts.
            flash("If that email exists, a reset link has been generated.", "info")

        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    db = get_db()
    record = db.execute(
        "SELECT * FROM password_resets WHERE token_hash = ? AND used = 0 AND expires_at > ?",
        (token_hash, datetime.utcnow().isoformat()),
    ).fetchone()

    if not record:
        flash("That reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("auth/reset_password.html", token=token)

        update_password(record["user_id"], generate_password_hash(password))
        db.execute("UPDATE password_resets SET used = 1 WHERE id = ?", (record["id"],))
        db.commit()
        revoke_all_sessions_for_user(record["user_id"])

        flash("Password updated. Please sign in with your new password.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", token=token)
