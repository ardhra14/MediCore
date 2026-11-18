"""Isolated intentionally vulnerable password recovery lab."""

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from werkzeug.security import generate_password_hash

from app.models.db import get_db

vuln_recovery_bp = Blueprint("vuln_recovery", __name__, url_prefix="/lab/password-recovery")


@vuln_recovery_bp.before_request
def restrict_to_localhost():
    host = (request.host or "").split(":", 1)[0]
    if host not in {"127.0.0.1", "localhost"}:
        abort(403)


def generate_predictable_token(user_id, now=None):
    now = now or datetime.utcnow()
    return f"{user_id % 100:02d}{now.hour * 60 + now.minute:04d}"


@vuln_recovery_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user:
            token = generate_predictable_token(user["id"])
            db = get_db()
            db.execute("DELETE FROM vuln_reset_tokens WHERE user_id = ?", (user["id"],))
            db.execute(
                "INSERT INTO vuln_reset_tokens (user_id, token, used) VALUES (?, ?, 0)",
                (user["id"], token),
            )
            db.commit()
            flash(f"Demo token: {token} (intentionally predictable)", "info")
        else:
            flash("If that email exists, a demo token was generated.", "info")
        return redirect(url_for("vuln_recovery.forgot_password"))

    return render_template("lab_recovery.html", vulnerable=True)


@vuln_recovery_bp.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token):
    db = get_db()
    record = db.execute(
        "SELECT * FROM vuln_reset_tokens WHERE token = ? AND used = 0",
        (token,),
    ).fetchone()
    if not record:
        flash("Invalid or already-used lab token.", "danger")
        return redirect(url_for("vuln_recovery.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("lab_recovery_reset.html", token=token, vulnerable=True)

        db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(password), record["user_id"]),
        )
        db.execute("UPDATE vuln_reset_tokens SET used = 1 WHERE id = ?", (record["id"],))
        db.commit()
        flash("Password reset via the vulnerable lab flow.", "success")
        return redirect(url_for("auth.login"))

    return render_template("lab_recovery_reset.html", token=token, vulnerable=True)