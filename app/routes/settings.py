from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.security import check_password_hash, generate_password_hash

from app.auth.utils import login_required, current_user, revoke_all_sessions_for_user
from app.models.db import get_db

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    db = get_db()
    user = current_user()

    # Fetch role-specific profile data if any
    profile_extra = None
    if user["role"] == "patient":
        profile_extra = db.execute("SELECT * FROM patients WHERE user_id = ?", (user["id"],)).fetchone()
    elif user["role"] == "doctor":
        profile_extra = db.execute(
            """
            SELECT d.*, dep.name AS department_name
            FROM doctors d
            LEFT JOIN departments dep ON dep.id = d.department_id
            WHERE d.user_id = ?
            """,
            (user["id"],),
        ).fetchone()
    elif user["role"] == "receptionist":
        profile_extra = db.execute(
            """
            SELECT s.*, dep.name AS department_name
            FROM staff s
            LEFT JOIN departments dep ON dep.id = s.department_id
            WHERE s.user_id = ?
            """,
            (user["id"],),
        ).fetchone()

    # Fetch active sessions for current user
    active_sessions = db.execute(
        """
        SELECT id, created_at, expires_at, revoked
        FROM sessions
        WHERE user_id = ? AND revoked = 0 AND expires_at > ?
        ORDER BY created_at DESC
        """,
        (user["id"], datetime.utcnow().isoformat()),
    ).fetchall()

    return render_template(
        "settings/index.html",
        user=user,
        profile_extra=profile_extra,
        active_sessions=active_sessions,
        security_lab_enabled=current_app.config.get("SECURITY_LAB_ENABLED", False),
    )


@settings_bp.route("/profile", methods=["POST"])
@login_required
def update_profile():
    db = get_db()
    user = current_user()

    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()

    if not full_name:
        flash("Full name cannot be empty.", "danger")
        return redirect(url_for("settings.index"))

    # Update users table
    db.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, user["id"]))

    # Update corresponding profile table
    if user["role"] == "patient":
        db.execute(
            "UPDATE patients SET full_name = ?, phone = ?, address = ? WHERE user_id = ?",
            (full_name, phone, address, user["id"]),
        )
    elif user["role"] == "doctor":
        db.execute(
            "UPDATE doctors SET phone = ? WHERE user_id = ?",
            (phone, user["id"]),
        )
    elif user["role"] == "receptionist":
        db.execute(
            "UPDATE staff SET phone = ? WHERE user_id = ?",
            (phone, user["id"]),
        )

    db.commit()
    flash("Profile information updated successfully.", "success")
    return redirect(url_for("settings.index"))


@settings_bp.route("/security/password", methods=["POST"])
@login_required
def update_password():
    db = get_db()
    user = current_user()

    current_pwd = request.form.get("current_password", "")
    new_pwd = request.form.get("new_password", "")
    confirm_pwd = request.form.get("confirm_password", "")

    # Verification
    if not check_password_hash(user["password_hash"], current_pwd):
        flash("Incorrect current password. Please try again.", "danger")
        return redirect(url_for("settings.index"))

    if len(new_pwd) < 8:
        flash("New password must be at least 8 characters long.", "danger")
        return redirect(url_for("settings.index"))

    if new_pwd != confirm_pwd:
        flash("New passwords do not match.", "danger")
        return redirect(url_for("settings.index"))

    # Secure update
    new_hash = generate_password_hash(new_pwd)
    db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user["id"]))
    db.commit()

    # Revoke other sessions for security
    revoke_all_sessions_for_user(user["id"])
    flash("Password successfully changed. Other active sessions have been revoked.", "success")
    return redirect(url_for("settings.index"))


@settings_bp.route("/security/revoke-others", methods=["POST"])
@login_required
def revoke_others():
    from app.auth.utils import SESSION_COOKIE_NAME, get_db
    user = current_user()
    current_token = request.cookies.get(SESSION_COOKIE_NAME)

    db = get_db()
    if current_token:
        db.execute(
            "UPDATE sessions SET revoked = 1 WHERE user_id = ? AND id != ?",
            (user["id"], current_token),
        )
    else:
        db.execute("UPDATE sessions SET revoked = 1 WHERE user_id = ?", (user["id"],))
    db.commit()

    flash("All other active sessions have been signed out.", "success")
    return redirect(url_for("settings.index"))


@settings_bp.route("/security/2fa", methods=["POST"])
@login_required
def toggle_2fa():
    db = get_db()
    user = current_user()
    user_keys = user.keys() if hasattr(user, "keys") else []
    current_status = user["two_factor_enabled"] if "two_factor_enabled" in user_keys else 0
    new_status = 0 if current_status else 1

    db.execute("UPDATE users SET two_factor_enabled = ? WHERE id = ?", (new_status, user["id"]))
    db.commit()

    action = "enabled" if new_status else "disabled"
    flash(f"Two-factor authentication has been {action} for your account.", "success")
    return redirect(url_for("settings.index"))
