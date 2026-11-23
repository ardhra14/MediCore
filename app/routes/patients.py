from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.auth.utils import login_required, roles_required
from app.models.db import get_db

patients_bp = Blueprint("patients", __name__, url_prefix="/patients")


@patients_bp.route("/")
@login_required
@roles_required("admin", "doctor", "receptionist", "patient")
def list_patients():
    db = get_db()
    from app.auth.utils import current_user
    user = current_user()
    if user and user["role"] == "patient":
        my_patient = db.execute("SELECT id FROM patients WHERE user_id = ?", (user["id"],)).fetchone()
        if my_patient:
            return redirect(url_for("patients.view_patient", patient_id=my_patient["id"]))
        flash("No patient profile found for your account.", "warning")
        return redirect(url_for("dashboard.overview"))

    q = request.args.get("q", "").strip()
    blood = request.args.get("blood", "").strip()
    gender = request.args.get("gender", "").strip()

    sql = "SELECT * FROM patients WHERE 1=1"
    params = []

    if q:
        sql += " AND (full_name LIKE ? OR phone LIKE ? OR address LIKE ?)"
        pattern = f"%{q}%"
        params.extend([pattern, pattern, pattern])

    if blood:
        sql += " AND blood_group = ?"
        params.append(blood)

    if gender:
        sql += " AND gender = ?"
        params.append(gender)

    sql += " ORDER BY full_name ASC"
    rows = db.execute(sql, params).fetchall()

    return render_template(
        "patients/list.html",
        patients=rows,
        q=q,
        blood=blood,
        gender=gender,
    )


@patients_bp.route("/<int:patient_id>")
@login_required
@roles_required("admin", "doctor", "receptionist", "patient")
def view_patient(patient_id):
    db = get_db()
    from app.auth.utils import current_user
    user = current_user()
    patient = db.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if not patient:
        flash("Patient not found.", "danger")
        return redirect(url_for("patients.list_patients"))

    if user and user["role"] == "patient" and patient["user_id"] != user["id"]:
        flash("Access denied. You can only view your own patient profile.", "danger")
        return redirect(url_for("dashboard.overview"))

    records = db.execute(
        """
        SELECT mr.*, u.full_name AS doctor_name, dep.name AS department_name
        FROM medical_records mr
        LEFT JOIN doctors d ON d.id = mr.doctor_id
        LEFT JOIN users u ON u.id = d.user_id
        LEFT JOIN departments dep ON dep.id = d.department_id
        WHERE mr.patient_id = ?
        ORDER BY mr.visit_date DESC
        """,
        (patient_id,),
    ).fetchall()

    appointments = db.execute(
        """
        SELECT a.*, u.full_name AS doctor_name, dep.name AS department_name
        FROM appointments a
        JOIN doctors d ON d.id = a.doctor_id
        JOIN users u ON u.id = d.user_id
        LEFT JOIN departments dep ON dep.id = a.department_id
        WHERE a.patient_id = ?
        ORDER BY a.scheduled_at DESC
        """,
        (patient_id,),
    ).fetchall()

    bills = db.execute(
        "SELECT * FROM billing WHERE patient_id = ? ORDER BY issued_at DESC", (patient_id,)
    ).fetchall()

    return render_template(
        "patients/view.html",
        patient=patient,
        records=records,
        appointments=appointments,
        bills=bills,
    )


@patients_bp.route("/new", methods=["GET", "POST"])
@login_required
@roles_required("admin", "receptionist")
def new_patient():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        if not full_name:
            flash("Patient full name is required.", "danger")
            return render_template("patients/form.html", patient=None)

        db = get_db()
        cur = db.execute(
            """
            INSERT INTO patients (full_name, date_of_birth, gender, phone, address, blood_group)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                full_name,
                request.form.get("date_of_birth") or None,
                request.form.get("gender") or None,
                request.form.get("phone", "").strip() or None,
                request.form.get("address", "").strip() or None,
                request.form.get("blood_group", "").strip() or None,
            ),
        )
        db.commit()
        flash(f"Patient '{full_name}' registered successfully.", "success")
        return redirect(url_for("patients.view_patient", patient_id=cur.lastrowid))

    return render_template("patients/form.html", patient=None)


@patients_bp.route("/<int:patient_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("admin", "receptionist")
def edit_patient(patient_id):
    db = get_db()
    patient = db.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if not patient:
        flash("Patient not found.", "danger")
        return redirect(url_for("patients.list_patients"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        if not full_name:
            flash("Full name cannot be empty.", "danger")
            return render_template("patients/form.html", patient=patient)

        db.execute(
            """
            UPDATE patients
            SET full_name = ?, date_of_birth = ?, gender = ?, phone = ?, address = ?, blood_group = ?
            WHERE id = ?
            """,
            (
                full_name,
                request.form.get("date_of_birth") or None,
                request.form.get("gender") or None,
                request.form.get("phone", "").strip() or None,
                request.form.get("address", "").strip() or None,
                request.form.get("blood_group", "").strip() or None,
                patient_id,
            ),
        )
        if patient["user_id"]:
            db.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, patient["user_id"]))

        db.commit()
        flash("Patient profile updated successfully.", "success")
        return redirect(url_for("patients.view_patient", patient_id=patient_id))

    return render_template("patients/form.html", patient=patient)


@patients_bp.route("/<int:patient_id>/delete", methods=["POST"])
@login_required
@roles_required("admin")
def delete_patient(patient_id):
    db = get_db()
    patient = db.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if not patient:
        flash("Patient not found.", "danger")
        return redirect(url_for("patients.list_patients"))

    # Deleting patient (cascades to appointments, medical_records, billing via FK schema)
    name = patient["full_name"]
    user_id = patient["user_id"]
    db.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
    if user_id:
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()

    flash(f"Patient record for '{name}' was deleted successfully.", "success")
    return redirect(url_for("patients.list_patients"))
