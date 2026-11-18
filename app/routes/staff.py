from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash

from app.auth.utils import login_required, roles_required
from app.models.db import get_db

staff_bp = Blueprint("staff", __name__, url_prefix="/staff")


@staff_bp.route("/")
@login_required
@roles_required("admin")
def list_staff():
    db = get_db()
    q = request.args.get("q", "").strip()
    dep_id = request.args.get("department_id", "").strip()

    sql = """
        SELECT s.*, u.full_name, u.email, dep.name AS department_name
        FROM staff s
        JOIN users u ON u.id = s.user_id
        LEFT JOIN departments dep ON dep.id = s.department_id
        WHERE 1=1
    """
    params = []

    if q:
        sql += " AND (u.full_name LIKE ? OR s.job_title LIKE ? OR u.email LIKE ?)"
        pattern = f"%{q}%"
        params.extend([pattern, pattern, pattern])

    if dep_id and dep_id.isdigit():
        sql += " AND s.department_id = ?"
        params.append(int(dep_id))

    sql += " ORDER BY u.full_name ASC"
    rows = db.execute(sql, params).fetchall()
    departments = db.execute("SELECT * FROM departments ORDER BY name").fetchall()

    return render_template(
        "staff/list.html",
        staff=rows,
        departments=departments,
        q=q,
        selected_department=int(dep_id) if dep_id.isdigit() else None,
    )


@staff_bp.route("/new", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def new_staff():
    db = get_db()
    departments = db.execute("SELECT * FROM departments ORDER BY name").fetchall()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not full_name or not email or len(password) < 8:
            flash("Full name, valid email, and temporary password (min 8 chars) are required.", "danger")
            return render_template("staff/form.html", staff=None, departments=departments)

        if db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            flash("A user account with that email already exists.", "danger")
            return render_template("staff/form.html", staff=None, departments=departments)

        cur = db.execute(
            "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, 'receptionist')",
            (full_name, email, generate_password_hash(password)),
        )
        user_id = cur.lastrowid
        db.execute(
            """
            INSERT INTO staff (user_id, department_id, job_title, phone)
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                request.form.get("department_id") or None,
                request.form.get("job_title", "").strip() or None,
                request.form.get("phone", "").strip() or None,
            ),
        )
        db.commit()
        flash(f"Staff member '{full_name}' added successfully.", "success")
        return redirect(url_for("staff.list_staff"))

    return render_template("staff/form.html", staff=None, departments=departments)


@staff_bp.route("/<int:staff_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def edit_staff(staff_id):
    db = get_db()
    departments = db.execute("SELECT * FROM departments ORDER BY name").fetchall()
    staff_member = db.execute(
        """
        SELECT s.*, u.full_name, u.email
        FROM staff s
        JOIN users u ON u.id = s.user_id
        WHERE s.id = ?
        """,
        (staff_id,),
    ).fetchone()
    if not staff_member:
        flash("Staff member not found.", "danger")
        return redirect(url_for("staff.list_staff"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        if not full_name:
            flash("Full name cannot be empty.", "danger")
            return render_template("staff/form.html", staff=staff_member, departments=departments)

        db.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, staff_member["user_id"]))
        db.execute(
            """
            UPDATE staff
            SET department_id = ?, job_title = ?, phone = ?
            WHERE id = ?
            """,
            (
                request.form.get("department_id") or None,
                request.form.get("job_title", "").strip() or None,
                request.form.get("phone", "").strip() or None,
                staff_id,
            ),
        )
        db.commit()
        flash("Staff member profile updated successfully.", "success")
        return redirect(url_for("staff.list_staff"))

    return render_template("staff/form.html", staff=staff_member, departments=departments)


@staff_bp.route("/<int:staff_id>/delete", methods=["POST"])
@login_required
@roles_required("admin")
def delete_staff(staff_id):
    db = get_db()
    staff_member = db.execute(
        "SELECT s.*, u.full_name FROM staff s JOIN users u ON u.id = s.user_id WHERE s.id = ?",
        (staff_id,),
    ).fetchone()
    if not staff_member:
        flash("Staff member not found.", "danger")
        return redirect(url_for("staff.list_staff"))

    name = staff_member["full_name"]
    user_id = staff_member["user_id"]
    db.execute("DELETE FROM staff WHERE id = ?", (staff_id,))
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()

    flash(f"Staff member '{name}' has been removed.", "success")
    return redirect(url_for("staff.list_staff"))
