"""
MediCore entry point.

Usage:
    python run.py
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    # host=127.0.0.1 keeps this lab on localhost only, which matters
    # because this app intentionally ships two vulnerable auth mechanisms.
    app.run(host="127.0.0.1", port=5000, debug=app.config["DEBUG"])
