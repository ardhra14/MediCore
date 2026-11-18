"""Isolated intentionally vulnerable password recovery lab."""

from flask import Blueprint

vuln_recovery_bp = Blueprint("vuln_recovery", __name__, url_prefix="/lab/password-recovery")