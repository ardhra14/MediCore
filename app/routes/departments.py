from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.auth.utils import login_required, roles_required
from app.models.db import get_db

departments_bp = Blueprint("departments", __name__, url_prefix="/departments")


@departments_bp.route("/")
@login_required
def list_departments():
    db = get_db()
    rows = db.execute(
        """
        SELECT dep.*,
            (SELECT COUNT(*) FROM doctors WHERE department_id = dep.id) AS doctor_count,
            (SELECT COUNT(*) FROM staff WHERE department_id = dep.id) AS staff_count,
            (SELECT COUNT(*) FROM appointments WHERE department_id = dep.id) AS appointment_count
        FROM departments dep
        ORDER BY dep.name ASC
        """
    ).fetchall()
    return render_template("departments/list.html", departments=rows)


@departments_bp.route("/<int:dep_id>")
@login_required
def view_department(dep_id):
    db = get_db()
    department = db.execute("SELECT * FROM departments WHERE id = ?", (dep_id,)).fetchone()
    if not department:
        flash("Department not found.", "danger")
        return redirect(url_for("departments.list_departments"))

    doctors = db.execute(
        """
        SELECT d.*, u.full_name, u.email
        FROM doctors d
        JOIN users u ON u.id = d.user_id
        WHERE d.department_id = ?
        ORDER BY u.full_name
        """,
        (dep_id,),
    ).fetchall()

    staff = db.execute(
        """
        SELECT s.*, u.full_name, u.email
        FROM staff s
        JOIN users u ON u.id = s.user_id
        WHERE s.department_id = ?
        ORDER BY u.full_name
        """,
        (dep_id,),
    ).fetchall()

    return render_template("departments/view.html", department=department, doctors=doctors, staff=staff)


@departments_bp.route("/new", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def new_department():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash("Department name is required.", "danger")
            return render_template("departments/form.html", department=None)

        db = get_db()
        existing = db.execute("SELECT id FROM departments WHERE name = ?", (name,)).fetchone()
        if existing:
            flash(f"A department named '{name}' already exists.", "danger")
            return render_template("departments/form.html", department=None)

        db.execute(
            "INSERT INTO departments (name, description) VALUES (?, ?)",
            (name, description or None),
        )
        db.commit()
        flash(f"Department '{name}' created successfully.", "success")
        return redirect(url_for("departments.list_departments"))

    return render_template("departments/form.html", department=None)


@departments_bp.route("/<int:dep_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def edit_department(dep_id):
    db = get_db()
    department = db.execute("SELECT * FROM departments WHERE id = ?", (dep_id,)).fetchone()
    if not department:
        flash("Department not found.", "danger")
        return redirect(url_for("departments.list_departments"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash("Department name cannot be empty.", "danger")
            return render_template("departments/form.html", department=department)

        existing = db.execute("SELECT id FROM departments WHERE name = ? AND id != ?", (name, dep_id)).fetchone()
        if existing:
            flash(f"Another department named '{name}' already exists.", "danger")
            return render_template("departments/form.html", department=department)

        db.execute(
            "UPDATE departments SET name = ?, description = ? WHERE id = ?",
            (name, description or None, dep_id),
        )
        db.commit()
        flash(f"Department '{name}' updated successfully.", "success")
        return redirect(url_for("departments.list_departments"))

    return render_template("departments/form.html", department=department)


@departments_bp.route("/<int:dep_id>/delete", methods=["POST"])
@login_required
@roles_required("admin")
def delete_department(dep_id):
    db = get_db()
    department = db.execute("SELECT * FROM departments WHERE id = ?", (dep_id,)).fetchone()
    if not department:
        flash("Department not found.", "danger")
        return redirect(url_for("departments.list_departments"))

    # Check unlinked items: Doctors and staff will have their department_id SET NULL via FK schema
    name = department["name"]
    db.execute("DELETE FROM departments WHERE id = ?", (dep_id,))
    db.commit()
    flash(f"Department '{name}' has been deleted.", "success")
    return redirect(url_for("departments.list_departments"))
