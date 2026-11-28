"""
Isolated intentionally vulnerable Two-Factor Authentication (2FA) verification lab.

Demonstrates CWE-304 (Missing Required Cryptographic Step) and CWE-287 (Improper Authentication):
- Header-based bypass (e.g. X-Bypass-2FA: true)
- Universal master code bypass (e.g. 000000)
- Request parameter / forced-browsing tampering (e.g. ?skip_2fa=1 or form bypass=1)
"""

from datetime import datetime, timedelta
import secrets

from flask import Blueprint, abort, flash, make_response, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from app.models.db import get_db

vuln_2fa_bp = Blueprint("vuln_2fa", __name__, url_prefix="/lab/2fa")


@vuln_2fa_bp.before_request
def restrict_to_localhost():
    host = (request.host or "").split(":", 1)[0]
    if host not in {"127.0.0.1", "localhost"}:
        abort(403)


@vuln_2fa_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            otp = f"{secrets.randbelow(900000) + 100000:06d}"
            expires_at = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
            db.execute(
                "INSERT INTO vuln_2fa_codes (user_id, otp_code, expires_at) VALUES (?, ?, ?)",
                (user["id"], otp, expires_at),
            )
            db.commit()

            session["vuln_2fa_user_id"] = user["id"]
            flash(f"Valid Demo OTP: {otp} (Notice: vulnerable bypass conditions also exist).", "info")
            return redirect(url_for("vuln_2fa.verify"))

        flash("Invalid email or password for lab login.", "danger")

    return render_template("lab_2fa.html", vulnerable=True)


@vuln_2fa_bp.route("/verify", methods=["GET", "POST"])
def verify():
    user_id = session.get("vuln_2fa_user_id")
    if not user_id:
        flash("No 2FA challenge pending. Please sign in through the lab first.", "warning")
        return redirect(url_for("vuln_2fa.login"))

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return redirect(url_for("vuln_2fa.login"))

    bypass_detected = None

    # Vulnerability Condition 1: Header-based 2FA bypass
    if request.headers.get("X-Bypass-2FA", "").lower() in {"1", "true", "yes"} or \
       request.headers.get("X-2FA-Bypass", "").lower() in {"1", "true", "yes"}:
        bypass_detected = "Header-based bypass (X-Bypass-2FA: true)"

    # Vulnerability Condition 2: Query parameter or form field step-skipping
    elif request.args.get("skip_2fa") in {"1", "true"} or request.form.get("bypass") in {"1", "true"}:
        bypass_detected = "Parameter tampering bypass (skip_2fa=1)"

    if request.method == "POST" or bypass_detected:
        code = request.form.get("otp_code", "").strip()

        # Vulnerability Condition 3: Universal magic master code
        if code in {"000000", "888888"} and not bypass_detected:
            bypass_detected = f"Master code bypass (Submitted code: {code})"

        # Check genuine code in database if no bypass was triggered
        valid_otp = False
        if not bypass_detected:
            now_str = datetime.utcnow().isoformat()
            row = db.execute(
                "SELECT * FROM vuln_2fa_codes WHERE user_id = ? AND otp_code = ? AND expires_at > ? ORDER BY id DESC LIMIT 1",
                (user["id"], code, now_str),
            ).fetchone()
            if row:
                valid_otp = True

        if bypass_detected or valid_otp:
            session.pop("vuln_2fa_user_id", None)
            resp = make_response(redirect(url_for("vuln_2fa.portal")))
            resp.set_cookie("lab_2fa_session", str(user["id"]))
            if bypass_detected:
                flash(f"EXPLOIT SUCCESSFUL: 2FA bypassed via {bypass_detected}!", "danger")
            else:
                flash("2FA verification successful via legitimate OTP code.", "success")
            return resp

        flash("Invalid OTP code. Try entering the correct code or exploit one of the bypass flaws.", "danger")

    return render_template("lab_2fa_verify.html", user=user, vulnerable=True)


@vuln_2fa_bp.route("/portal")
def portal():
    cookie_user_id = request.cookies.get("lab_2fa_session")
    if not cookie_user_id:
        flash("You are not authenticated in the 2FA lab.", "warning")
        return redirect(url_for("vuln_2fa.login"))

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (cookie_user_id,)).fetchone()
    if not user:
        return redirect(url_for("vuln_2fa.login"))

    return render_template("lab_2fa_portal.html", user=user, vulnerable=True)


@vuln_2fa_bp.route("/logout")
def logout():
    resp = make_response(redirect(url_for("vuln_2fa.login")))
    resp.delete_cookie("lab_2fa_session")
    session.pop("vuln_2fa_user_id", None)
    flash("Signed out of 2FA lab.", "info")
    return resp
