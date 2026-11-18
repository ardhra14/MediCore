"""
MediCore configuration.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    # --- Core Flask settings -------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"

    # --- Database --------------------------------------------------------------
    DATABASE_PATH = os.environ.get(
        "DATABASE_PATH", str(BASE_DIR / "database" / "medicore.db")
    )

    # --- CSRF / form protection ---------------------------------------------
    WTF_CSRF_ENABLED = os.environ.get("WTF_CSRF_ENABLED", "1") == "1"
    WTF_CSRF_TIME_LIMIT = 60 * 60 * 8

    # --- Secure session cookie settings (used by the REAL login system) --------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8  # 8 hours

    # --- Security lab ---------------------------------------------------------
    SECURITY_LAB_ENABLED = os.environ.get("SECURITY_LAB_ENABLED", "0") == "1"