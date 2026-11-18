from app.models.db import get_db


def get_user_by_email(email):
    db = get_db()
    return db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def get_user_by_id(user_id):
    db = get_db()
    return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def create_user(full_name, email, password_hash, role="patient"):
    db = get_db()
    cur = db.execute(
        "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        (full_name, email, password_hash, role),
    )
    db.commit()
    return cur.lastrowid


def update_password(user_id, password_hash):
    db = get_db()
    db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
    db.commit()
