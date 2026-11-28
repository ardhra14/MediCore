"""
Isolated Rate Limiting & Brute-Force Testing Lab.

Demonstrates CWE-307 (Improper Restriction of Excessive Authentication Attempts):
1. Protected Endpoint: Working strict rate limiting (max 5 attempts, blocks with HTTP 429).
2. Vulnerable Endpoint: Rate limiting completely absent, allowing automated brute-force attacks.
3. Header-Bypass Endpoint: Rate limiting enforced via client-controllable X-Forwarded-For header.
"""

from collections import defaultdict
import time
from flask import Blueprint, abort, flash, jsonify, render_template, request

vuln_rate_limit_bp = Blueprint("vuln_rate_limit", __name__, url_prefix="/lab/rate-limit")

CORRECT_LAB_PIN = "4281"

# In-memory attempt tracking for the lab
_PROTECTED_ATTEMPTS = defaultdict(list)
_HEADER_BYPASS_ATTEMPTS = defaultdict(list)
_VULNERABLE_COUNTER = 0

RATE_WINDOW = 15 * 60  # 15 minutes
MAX_ATTEMPTS = 5


@vuln_rate_limit_bp.before_request
def restrict_to_localhost():
    host = (request.host or "").split(":", 1)[0]
    if host not in {"127.0.0.1", "localhost"}:
        abort(403)


def _check_rate_limit(tracker, key):
    now = time.time()
    valid_attempts = [t for t in tracker[key] if now - t < RATE_WINDOW]
    tracker[key] = valid_attempts
    return len(valid_attempts) >= MAX_ATTEMPTS


def _record_attempt(tracker, key):
    tracker[key].append(time.time())


@vuln_rate_limit_bp.route("/")
def index():
    ip = request.remote_addr or "127.0.0.1"
    prot_count = len([t for t in _PROTECTED_ATTEMPTS[ip] if time.time() - t < RATE_WINDOW])
    return render_template(
        "lab_ratelimit.html",
        vulnerable=True,
        prot_count=prot_count,
        max_attempts=MAX_ATTEMPTS,
        vuln_counter=_VULNERABLE_COUNTER,
        target_pin="4281",
    )


@vuln_rate_limit_bp.route("/verify-otp-protected", methods=["POST"])
def verify_protected():
    ip = request.remote_addr or "127.0.0.1"
    pin = request.form.get("pin") or (request.get_json() or {}).get("pin", "")

    if _check_rate_limit(_PROTECTED_ATTEMPTS, ip):
        if request.is_json:
            return jsonify({"success": False, "error": "HTTP 429: Rate limit exceeded. 15-minute lockout enforced."}), 429
        flash("HTTP 429: Rate limit exceeded. Too many attempts from this IP address.", "danger")
        return index()

    _record_attempt(_PROTECTED_ATTEMPTS, ip)

    if pin == CORRECT_LAB_PIN:
        _PROTECTED_ATTEMPTS.pop(ip, None)
        if request.is_json:
            return jsonify({"success": True, "message": "Access granted! PIN verified under rate limiting."})
        flash("Success! Correct PIN verified under protected rate limiting.", "success")
        return index()

    remaining = MAX_ATTEMPTS - len(_PROTECTED_ATTEMPTS[ip])
    if request.is_json:
        return jsonify({"success": False, "error": f"Invalid PIN. Remaining attempts: {max(0, remaining)}"}), 400
    flash(f"Invalid PIN. Remaining attempts before lockout: {max(0, remaining)}", "danger")
    return index()


@vuln_rate_limit_bp.route("/verify-otp-vulnerable", methods=["POST"])
def verify_vulnerable():
    global _VULNERABLE_COUNTER
    _VULNERABLE_COUNTER += 1
    pin = request.form.get("pin") or (request.get_json() or {}).get("pin", "")

    # Deliberate vulnerability: NO RATE LIMITING ENFORCED!
    if pin == CORRECT_LAB_PIN:
        if request.is_json:
            return jsonify({
                "success": True,
                "message": f"EXPLOIT DEMO: PIN cracked after {_VULNERABLE_COUNTER} total requests with zero rate limiting!",
                "total_requests": _VULNERABLE_COUNTER
            })
        flash(f"EXPLOIT DEMO: PIN cracked after {_VULNERABLE_COUNTER} requests with zero lockout or delays!", "success")
        return index()

    if request.is_json:
        return jsonify({
            "success": False,
            "error": "Invalid PIN (No rate limiting enforced; unlimited attempts allowed)",
            "total_requests": _VULNERABLE_COUNTER
        }), 400

    flash(f"Invalid PIN submitted (Attempt #{_VULNERABLE_COUNTER}). Notice zero rate limiting or lockout occurred.", "warning")
    return index()


@vuln_rate_limit_bp.route("/verify-otp-header-bypass", methods=["POST"])
def verify_header_bypass():
    # Deliberate vulnerability: trust client-supplied X-Forwarded-For header
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1").split(",")[0].strip()
    pin = request.form.get("pin") or (request.get_json() or {}).get("pin", "")

    if _check_rate_limit(_HEADER_BYPASS_ATTEMPTS, client_ip):
        if request.is_json:
            return jsonify({
                "success": False,
                "error": f"HTTP 429: Rate limit hit for IP '{client_ip}'. (Tip: rotate X-Forwarded-For header to bypass)",
            }), 429
        flash(f"HTTP 429: Rate limit hit for IP '{client_ip}'. Rotate X-Forwarded-For to bypass.", "danger")
        return index()

    _record_attempt(_HEADER_BYPASS_ATTEMPTS, client_ip)

    if pin == CORRECT_LAB_PIN:
        if request.is_json:
            return jsonify({"success": True, "message": f"PIN verified using IP identity: {client_ip}"})
        flash(f"Success: Correct PIN verified using IP: {client_ip}", "success")
        return index()

    if request.is_json:
        return jsonify({
            "success": False,
            "error": f"Invalid PIN for IP '{client_ip}'",
            "ip_tracked": client_ip
        }), 400

    flash(f"Invalid PIN for tracked IP '{client_ip}'.", "danger")
    return index()


@vuln_rate_limit_bp.route("/reset", methods=["POST"])
def reset():
    global _VULNERABLE_COUNTER
    ip = request.remote_addr or "127.0.0.1"
    _PROTECTED_ATTEMPTS.pop(ip, None)
    _HEADER_BYPASS_ATTEMPTS.clear()
    _VULNERABLE_COUNTER = 0
    flash("Lab rate limit counters have been reset.", "info")
    return index()
