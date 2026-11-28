"""
Isolated Information Disclosure Security Lab.

Demonstrates CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor)
and CWE-209 (Generation of Error Message Containing Sensitive Information):
- Diagnostic / debug endpoint disclosing server file paths, internal environment,
  database schema names, routing maps, and configuration metadata.
"""

import os
import platform
import sys

from flask import Blueprint, abort, current_app, jsonify, render_template, request

from app.models.db import get_db

vuln_info_bp = Blueprint("vuln_info", __name__, url_prefix="/lab/info-disclosure")


@vuln_info_bp.before_request
def restrict_to_localhost():
    host = (request.host or "").split(":", 1)[0]
    if host not in {"127.0.0.1", "localhost"}:
        abort(403)


def _gather_diagnostic_metadata():
    db = get_db()
    # Query database internal tables
    tables = [row["name"] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    table_stats = {}
    for tbl in tables[:8]:
        try:
            cnt = db.execute(f"SELECT COUNT(*) AS c FROM {tbl}").fetchone()["c"]
            table_stats[tbl] = cnt
        except Exception:
            pass

    # Extract internal routing rules
    routes = []
    for rule in current_app.url_map.iter_rules():
        routes.append({
            "endpoint": rule.endpoint,
            "methods": sorted(list(rule.methods - {"HEAD", "OPTIONS"})),
            "rule": str(rule)
        })

    # Sensitive internal metadata
    metadata = {
        "server_environment": {
            "os_name": os.name,
            "platform": platform.platform(),
            "python_version": sys.version,
            "python_executable": sys.executable,
            "working_directory": os.getcwd(),
            "process_id": os.getpid(),
        },
        "application_configuration": {
            "database_path": str(current_app.config.get("DATABASE_PATH", "")),
            "session_cookie_name": current_app.config.get("SESSION_COOKIE_NAME", "medicore_session"),
            "permanent_session_lifetime_sec": current_app.config.get("PERMANENT_SESSION_LIFETIME", 28800),
            "session_cookie_samesite": current_app.config.get("SESSION_COOKIE_SAMESITE", "Lax"),
            "session_cookie_secure": current_app.config.get("SESSION_COOKIE_SECURE", False),
            "debug_mode": current_app.config.get("DEBUG", False),
            "security_lab_enabled": current_app.config.get("SECURITY_LAB_ENABLED", False),
        },
        "database_internals": {
            "engine": "SQLite 3",
            "active_tables": tables,
            "table_record_counts": table_stats,
        },
        "framework_routing_map": routes[:15],
    }
    return metadata


@vuln_info_bp.route("/")
@vuln_info_bp.route("/diagnostics")
def diagnostics():
    metadata = _gather_diagnostic_metadata()

    if request.args.get("format") == "json" or request.is_json or "application/json" in request.headers.get("Accept", ""):
        return jsonify(metadata)

    return render_template("lab_info_disclosure.html", vulnerable=True, metadata=metadata)
