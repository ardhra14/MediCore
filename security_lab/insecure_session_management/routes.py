"""Isolated intentionally vulnerable session-management lab."""

from datetime import datetime, timedelta

from flask import Blueprint, abort, flash, jsonify, make_response, redirect, render_template, request, url_for
from werkzeug.security import check_password_hash

from app.models.db import get_db

vuln_session_bp = Blueprint("vuln_session", __name__, url_prefix="/lab/session-demo")


@vuln_session_bp.before_request
def restrict_to_localhost():
    host = (request.host or "").split(":", 1)[0]
    if host not in {"127.0.0.1", "localhost"}:
        abort(403)


def create_vuln_session(user_id):
    db = get_db()
    cur = db.execute(
        "INSERT INTO vuln_sessions (user_id, expires_at) VALUES (?, ?)",
        (user_id, (datetime.utcnow() + timedelta(hours=8)).isoformat()),
    )
    db.commit()
    return str(cur.lastrowid)


@vuln_session_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            token = create_vuln_session(user["id"])
            response = make_response(redirect(url_for("vuln_session.whoami")))
            response.set_cookie("lab_session", token)
            flash("Signed in through the intentionally vulnerable lab flow.", "info")
            return response
        flash("Invalid email or password.", "danger")
    return render_template("lab_session_login.html", vulnerable=True)


@vuln_session_bp.route("/whoami")
def whoami():
    token = request.cookies.get("lab_session")
    if not token:
        return jsonify({"authenticated": False})
    user = get_db().execute(
        "SELECT u.full_name, u.email, u.role FROM vuln_sessions s "
        "JOIN users u ON u.id = s.user_id WHERE s.id = ? AND s.expires_at > ?",
        (token, datetime.utcnow().isoformat()),
    ).fetchone()
    if not user:
        return jsonify({"authenticated": False})
    return jsonify(
        {
            "authenticated": True,
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
        }
    )