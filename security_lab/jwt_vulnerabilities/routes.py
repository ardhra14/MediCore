"""
Isolated JWT Token Validation & Privilege Escalation Lab.

Demonstrates CWE-347 (Improper Verification of Cryptographic Signature) and
CWE-345 (Insufficient Verification of Data Authenticity):
- Algorithm 'none' acceptance flaw
- Client-side claim manipulation: modifying {"isAdmin": false} -> {"isAdmin": true}
  to escalate privileges from patient/doctor to clinical administrator.
"""

import base64
import hmac
import hashlib
import json
import time

from flask import Blueprint, abort, flash, jsonify, make_response, redirect, render_template, request, url_for
from werkzeug.security import check_password_hash

from app.models.db import get_db

vuln_jwt_bp = Blueprint("vuln_jwt", __name__, url_prefix="/lab/jwt")

JWT_SECRET = "medicore-security-lab-jwt-secret-key-2026"


@vuln_jwt_bp.before_request
def restrict_to_localhost():
    host = (request.host or "").split(":", 1)[0]
    if host not in {"127.0.0.1", "localhost"}:
        abort(403)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    padding = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s + padding)


def create_lab_jwt(payload: dict, alg: str = "HS256") -> str:
    header = {"typ": "JWT", "alg": alg}
    header_json = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    h_b64 = _b64url_encode(header_json)
    p_b64 = _b64url_encode(payload_json)

    if alg.lower() == "none":
        return f"{h_b64}.{p_b64}."

    signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
    sig = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    s_b64 = _b64url_encode(sig)
    return f"{h_b64}.{p_b64}.{s_b64}"


def verify_lab_jwt(token: str):
    """
    Deliberately flawed JWT verification.
    If header 'alg' is 'none' (or missing signature), signature validation is skipped!
    """
    if not token or "." not in token:
        return None, "Malformed JWT structure"

    parts = token.strip().split(".")
    if len(parts) < 2:
        return None, "Invalid token parts"

    try:
        header_raw = _b64url_decode(parts[0])
        header = json.loads(header_raw.decode("utf-8"))
        payload_raw = _b64url_decode(parts[1])
        payload = json.loads(payload_raw.decode("utf-8"))
    except Exception as e:
        return None, f"Decoding error: {str(e)}"

    alg = header.get("alg", "").lower()

    # VULNERABILITY: If 'none' algorithm is specified, signature check is completely bypassed!
    if alg == "none":
        return payload, "Verified (none algorithm bypass)"

    if len(parts) != 3 or not parts[2]:
        return None, "Signature required for HS256"

    signing_input = f"{parts[0]}.{parts[1]}".encode("utf-8")
    expected_sig = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    expected_b64 = _b64url_encode(expected_sig)

    if not hmac.compare_digest(parts[2], expected_b64):
        return None, "Invalid HMAC-SHA256 cryptographic signature"

    return payload, "Verified (cryptographic HS256 signature valid)"


def _get_request_jwt():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return request.cookies.get("lab_jwt") or request.args.get("token") or ""


@vuln_jwt_bp.route("/")
def index():
    token = _get_request_jwt()
    claims = None
    verification_status = None
    if token:
        claims, verification_status = verify_lab_jwt(token)

    return render_template(
        "lab_jwt.html",
        vulnerable=True,
        current_token=token,
        claims=claims,
        verification_status=verification_status,
    )


@vuln_jwt_bp.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "eldho.paulose@medicore.test").strip().lower()
    password = request.form.get("password", "Passw0rd!")

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user or not check_password_hash(user["password_hash"], password):
        flash("Invalid email or password for JWT lab.", "danger")
        return redirect(url_for("vuln_jwt.index"))

    # Issue token with genuine user roles
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "name": user["full_name"],
        "role": user["role"],
        "isAdmin": True if user["role"] == "admin" else False,
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400,
    }

    token = create_lab_jwt(payload, alg="HS256")
    resp = make_response(redirect(url_for("vuln_jwt.index")))
    resp.set_cookie("lab_jwt", token)
    flash(f"JWT issued for {user['full_name']} (role: {user['role']}, isAdmin: {payload['isAdmin']})", "info")
    return resp


@vuln_jwt_bp.route("/admin")
def admin_portal():
    wants_json = (
        request.is_json
        or request.args.get("format") == "json"
        or "application/json" in request.headers.get("Accept", "")
    )
    token = _get_request_jwt()
    if not token:
        if wants_json:
            return jsonify({"error": "Authorization token required"}), 401
        flash("Authorization token required. Please sign in or supply a token.", "warning")
        return redirect(url_for("vuln_jwt.index"))

    payload, status = verify_lab_jwt(token)
    if not payload:
        if wants_json:
            return jsonify({"error": f"Token verification failed: {status}"}), 401
        flash(f"Token rejected: {status}", "danger")
        return redirect(url_for("vuln_jwt.index"))

    # Check privilege claim
    is_admin = payload.get("isAdmin") is True or payload.get("role") == "admin"

    if not is_admin:
        if wants_json:
            return jsonify({
                "error": "HTTP 403 Forbidden: Privilege Escalation Required",
                "message": "Token claim 'isAdmin' is false. Modify claims and use alg 'none' to escalate.",
                "claims": payload
            }), 403
        flash("Access Denied (HTTP 403): Your JWT claim 'isAdmin' is false. Privilege escalation needed.", "danger")
        return redirect(url_for("vuln_jwt.index"))

    # Privileged Admin Clinical Governance Data
    admin_data = {
        "access": "GRANTED - Full Clinical Governance Console",
        "authenticated_claims": payload,
        "verification_mode": status,
        "facility_secret_metadata": {
            "hipaa_audit_id": "MEDICORE-KL-0914-AUDIT",
            "db_encryption_key_id": "KMS-KEY-92841-KOCHI",
            "executive_overrides": ["STAFF_BYPASS", "SYSTEM_DEBUG", "FINANCIAL_EXPORT"],
        },
    }

    if wants_json:
        return jsonify(admin_data)

    return render_template(
        "lab_jwt_admin.html",
        vulnerable=True,
        admin_data=admin_data,
        payload=payload,
        status=status,
    )


@vuln_jwt_bp.route("/forge", methods=["POST"])
def forge():
    """Helper tool for lab testers to generate an alg: none privilege-escalated token."""
    raw_sub = request.form.get("sub", "8")
    name = request.form.get("name", "Eldho Paulose")
    email = request.form.get("email", "eldho.paulose@medicore.test")
    is_admin = request.form.get("isAdmin", "true").lower() in {"true", "1"}

    payload = {
        "sub": int(raw_sub) if raw_sub.isdigit() else raw_sub,
        "email": email,
        "name": name,
        "role": "admin" if is_admin else "patient",
        "isAdmin": is_admin,
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400,
    }

    forged_token = create_lab_jwt(payload, alg="none")
    resp = make_response(redirect(url_for("vuln_jwt.index")))
    resp.set_cookie("lab_jwt", forged_token)
    flash(f"Forged 'alg: none' token generated with isAdmin={is_admin}!", "danger")
    return resp


@vuln_jwt_bp.route("/logout")
def logout():
    resp = make_response(redirect(url_for("vuln_jwt.index")))
    resp.delete_cookie("lab_jwt")
    flash("JWT token cleared.", "info")
    return resp
