from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash

from app.auth.utils import login_required, roles_required
from app.models.db import get_db

doctors_bp = Blueprint("doctors", __name__, url_prefix="/doctors")


@doctors_bp.route("/")
@login_required
@roles_required("admin", "doctor", "receptionist", "patient")
def list_doctors():
    db = get_db()
    q = request.args.get("q", "").strip()
    dep_id = request.args.get("department_id", "").strip()

    sql = """
        SELECT d.*, u.full_name, u.email, dep.name AS department_name,
               (SELECT COUNT(*) FROM appointments WHERE doctor_id = d.id AND status != 'cancelled') AS active_appointments
        FROM doctors d
        JOIN users u ON u.id = d.user_id
        LEFT JOIN departments dep ON dep.id = d.department_id
        WHERE 1=1
    """
    params = []

    if q:
        sql += " AND (u.full_name LIKE ? OR d.specialty LIKE ?)"
        pattern = f"%{q}%"
        params.extend([pattern, pattern])

    if dep_id and dep_id.isdigit():
        sql += " AND d.department_id = ?"
        params.append(int(dep_id))

    sql += " ORDER BY u.full_name ASC"
    rows = db.execute(sql, params).fetchall()
    departments = db.execute("SELECT * FROM departments ORDER BY name").fetchall()

    return render_template(
        "doctors/list.html",
        doctors=rows,
        departments=departments,
        q=q,
        selected_department=int(dep_id) if dep_id.isdigit() else None,
    )


@doctors_bp.route("/<int:doctor_id>")
@login_required
@roles_required("admin", "doctor", "receptionist", "patient")
def view_doctor(doctor_id):
    db = get_db()
    doctor = db.execute(
        """
        SELECT d.*, u.full_name, u.email, dep.name AS department_name
        FROM doctors d
        JOIN users u ON u.id = d.user_id
        LEFT JOIN departments dep ON dep.id = d.department_id
        WHERE d.id = ?
        """,
        (doctor_id,),
    ).fetchone()
    if not doctor:
        flash("Doctor not found.", "danger")
        return redirect(url_for("doctors.list_doctors"))

    # Load appointments for this doctor
    appointments = db.execute(
        """
        SELECT a.*, p.full_name AS patient_name
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        WHERE a.doctor_id = ?
        ORDER BY a.scheduled_at DESC LIMIT 15
        """,
        (doctor_id,),
    ).fetchall()

    return render_template("doctors/view.html", doctor=doctor, appointments=appointments)


@doctors_bp.route("/new", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def new_doctor():
    db = get_db()
    departments = db.execute("SELECT * FROM departments ORDER BY name").fetchall()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not full_name or not email or len(password) < 8:
            flash("Full name, valid email, and temporary password (min 8 characters) are required.", "danger")
            return render_template("doctors/form.html", doctor=None, departments=departments)

        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            flash("A user account with that email already exists.", "danger")
            return render_template("doctors/form.html", doctor=None, departments=departments)

        cur = db.execute(
            "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, 'doctor')",
            (full_name, email, generate_password_hash(password)),
        )
        user_id = cur.lastrowid
        cur_doc = db.execute(
            """
            INSERT INTO doctors (user_id, department_id, specialty, phone, availability)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                request.form.get("department_id") or None,
                request.form.get("specialty", "").strip() or None,
                request.form.get("phone", "").strip() or None,
                request.form.get("availability", "").strip() or None,
            ),
        )
        db.commit()
        flash(f"Doctor '{full_name}' successfully added.", "success")
        return redirect(url_for("doctors.view_doctor", doctor_id=cur_doc.lastrowid))

    return render_template("doctors/form.html", doctor=None, departments=departments)


@doctors_bp.route("/<int:doctor_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def edit_doctor(doctor_id):
    db = get_db()
    departments = db.execute("SELECT * FROM departments ORDER BY name").fetchall()
    doctor = db.execute(
        """
        SELECT d.*, u.full_name, u.email
        FROM doctors d
        JOIN users u ON u.id = d.user_id
        WHERE d.id = ?
        """,
        (doctor_id,),
    ).fetchone()
    if not doctor:
        flash("Doctor not found.", "danger")
        return redirect(url_for("doctors.list_doctors"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        if not full_name:
            flash("Doctor name cannot be empty.", "danger")
            return render_template("doctors/form.html", doctor=doctor, departments=departments)

        db.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, doctor["user_id"]))
        db.execute(
            """
            UPDATE doctors
            SET department_id = ?, specialty = ?, phone = ?, availability = ?
            WHERE id = ?
            """,
            (
                request.form.get("department_id") or None,
                request.form.get("specialty", "").strip() or None,
                request.form.get("phone", "").strip() or None,
                request.form.get("availability", "").strip() or None,
                doctor_id,
            ),
        )
        db.commit()
        flash("Doctor profile updated successfully.", "success")
        return redirect(url_for("doctors.view_doctor", doctor_id=doctor_id))

    return render_template("doctors/form.html", doctor=doctor, departments=departments)


@doctors_bp.route("/<int:doctor_id>/delete", methods=["POST"])
@login_required
@roles_required("admin")
def delete_doctor(doctor_id):
    db = get_db()
    doctor = db.execute(
        "SELECT d.*, u.full_name, d.user_id FROM doctors d JOIN users u ON u.id = d.user_id WHERE d.id = ?",
        (doctor_id,),
    ).fetchone()
    if not doctor:
        flash("Doctor not found.", "danger")
        return redirect(url_for("doctors.list_doctors"))

    name = doctor["full_name"]
    user_id = doctor["user_id"]
    db.execute("DELETE FROM doctors WHERE id = ?", (doctor_id,))
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()

    flash(f"Doctor '{name}' was removed from the system.", "success")
    return redirect(url_for("doctors.list_doctors"))
