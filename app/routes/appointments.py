from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.auth.utils import login_required, roles_required
from app.models.db import get_db

appointments_bp = Blueprint("appointments", __name__, url_prefix="/appointments")


@appointments_bp.route("/")
@login_required
def list_appointments():
    db = get_db()
    from app.auth.utils import current_user
    user = current_user()
    status = request.args.get("status", "").strip()
    q = request.args.get("q", "").strip()
    doctor_id = request.args.get("doctor_id", "").strip()

    query = """
        SELECT a.*, p.full_name AS patient_name, u.full_name AS doctor_name, dep.name AS department_name
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        JOIN doctors d ON d.id = a.doctor_id
        JOIN users u ON u.id = d.user_id
        LEFT JOIN departments dep ON dep.id = a.department_id
        WHERE 1=1
    """
    params = []

    if user and user["role"] == "patient":
        patient = db.execute("SELECT id FROM patients WHERE user_id = ?", (user["id"],)).fetchone()
        if patient:
            query += " AND a.patient_id = ?"
            params.append(patient["id"])
        else:
            query += " AND 1=0"

    if status:
        query += " AND a.status = ?"
        params.append(status)

    if doctor_id and doctor_id.isdigit():
        query += " AND a.doctor_id = ?"
        params.append(int(doctor_id))

    if q:
        query += " AND (p.full_name LIKE ? OR u.full_name LIKE ? OR a.reason LIKE ?)"
        pattern = f"%{q}%"
        params.extend([pattern, pattern, pattern])

    query += " ORDER BY a.scheduled_at DESC"
    rows = db.execute(query, params).fetchall()
    doctors = db.execute(
        "SELECT d.id, u.full_name FROM doctors d JOIN users u ON u.id = d.user_id ORDER BY u.full_name"
    ).fetchall()

    return render_template(
        "appointments/list.html",
        appointments=rows,
        status=status,
        q=q,
        doctors=doctors,
        selected_doctor=int(doctor_id) if doctor_id.isdigit() else None,
    )


@appointments_bp.route("/new", methods=["GET", "POST"])
@login_required
@roles_required("admin", "doctor", "receptionist", "patient")
def new_appointment():
    db = get_db()
    from app.auth.utils import current_user
    user = current_user()
    patients = db.execute("SELECT * FROM patients ORDER BY full_name").fetchall()
    doctors = db.execute(
        """
        SELECT d.id, u.full_name, d.department_id, dep.name AS department_name
        FROM doctors d
        JOIN users u ON u.id = d.user_id
        LEFT JOIN departments dep ON dep.id = d.department_id
        ORDER BY u.full_name
        """
    ).fetchall()
    departments = db.execute("SELECT * FROM departments ORDER BY name").fetchall()

    # Pre-select from query params if navigated from patient or doctor view
    pre_patient_id = request.args.get("patient_id", type=int)
    pre_doctor_id = request.args.get("doctor_id", type=int)

    if user and user["role"] == "patient":
        my_patient = db.execute("SELECT id FROM patients WHERE user_id = ?", (user["id"],)).fetchone()
        if my_patient:
            pre_patient_id = my_patient["id"]

    if request.method == "POST":
        if user and user["role"] == "patient":
            my_patient = db.execute("SELECT id FROM patients WHERE user_id = ?", (user["id"],)).fetchone()
            patient_id = my_patient["id"] if my_patient else None
        else:
            patient_id = request.form.get("patient_id")

        doctor_id = request.form.get("doctor_id")
        scheduled_at = request.form.get("scheduled_at")
        reason = request.form.get("reason", "").strip()
        department_id = request.form.get("department_id") or None

        if not patient_id or not doctor_id or not scheduled_at:
            flash("Patient, doctor, and date/time are required.", "danger")
            return render_template(
                "appointments/form.html",
                patients=patients,
                doctors=doctors,
                departments=departments,
                pre_patient_id=pre_patient_id,
                pre_doctor_id=pre_doctor_id,
            )

        # If department was not explicitly provided, look up doctor's department
        if not department_id:
            doc_row = db.execute("SELECT department_id FROM doctors WHERE id = ?", (doctor_id,)).fetchone()
            if doc_row and doc_row["department_id"]:
                department_id = doc_row["department_id"]

        db.execute(
            """
            INSERT INTO appointments (patient_id, doctor_id, department_id, scheduled_at, reason, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
            """,
            (patient_id, doctor_id, department_id, scheduled_at, reason),
        )
        db.commit()
        flash("Appointment scheduled successfully.", "success")
        return redirect(url_for("appointments.list_appointments"))

    return render_template(
        "appointments/form.html",
        patients=patients,
        doctors=doctors,
        departments=departments,
        pre_patient_id=pre_patient_id,
        pre_doctor_id=pre_doctor_id,
    )


@appointments_bp.route("/<int:appt_id>/status/<new_status>", methods=["POST"])
@login_required
@roles_required("admin", "doctor", "receptionist", "patient")
def update_status(appt_id, new_status):
    if new_status not in ("pending", "confirmed", "cancelled", "completed"):
        flash("Invalid appointment status specified.", "danger")
        return redirect(url_for("appointments.list_appointments"))

    db = get_db()
    from app.auth.utils import current_user
    user = current_user()
    appt = db.execute("SELECT patient_id FROM appointments WHERE id = ?", (appt_id,)).fetchone()
    if not appt:
        flash("Appointment not found.", "danger")
        return redirect(url_for("appointments.list_appointments"))

    if user and user["role"] == "patient":
        my_patient = db.execute("SELECT id FROM patients WHERE user_id = ?", (user["id"],)).fetchone()
        if not my_patient or appt["patient_id"] != my_patient["id"] or new_status != "cancelled":
            flash("Access denied. Patients can only cancel their own appointments.", "danger")
            return redirect(url_for("appointments.list_appointments"))

    db.execute("UPDATE appointments SET status = ? WHERE id = ?", (new_status, appt_id))
    db.commit()
    flash(f"Appointment status updated to '{new_status}'.", "success")
    return redirect(request.referrer or url_for("appointments.list_appointments"))


@appointments_bp.route("/<int:appt_id>/reschedule", methods=["GET", "POST"])
@login_required
@roles_required("admin", "doctor", "receptionist", "patient")
def reschedule(appt_id):
    db = get_db()
    from app.auth.utils import current_user
    user = current_user()
    appt = db.execute(
        """
        SELECT a.*, p.full_name AS patient_name, u.full_name AS doctor_name
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        JOIN doctors d ON d.id = a.doctor_id
        JOIN users u ON u.id = d.user_id
        WHERE a.id = ?
        """,
        (appt_id,),
    ).fetchone()
    if not appt:
        flash("Appointment not found.", "danger")
        return redirect(url_for("appointments.list_appointments"))

    if user and user["role"] == "patient":
        my_patient = db.execute("SELECT id FROM patients WHERE user_id = ?", (user["id"],)).fetchone()
        if not my_patient or appt["patient_id"] != my_patient["id"]:
            flash("Access denied. You can only reschedule your own appointments.", "danger")
            return redirect(url_for("appointments.list_appointments"))

    if request.method == "POST":
        scheduled_at = request.form.get("scheduled_at")
        if not scheduled_at:
            flash("Please choose a valid date and time.", "danger")
            return render_template("appointments/reschedule.html", appt=appt)

        db.execute(
            "UPDATE appointments SET scheduled_at = ?, status = 'pending' WHERE id = ?",
            (scheduled_at, appt_id),
        )
        db.commit()
        flash("Appointment rescheduled and status marked as pending confirmation.", "success")
        return redirect(url_for("appointments.list_appointments"))

    return render_template("appointments/reschedule.html", appt=appt)


@appointments_bp.route("/<int:appt_id>/delete", methods=["POST"])
@login_required
@roles_required("admin")
def delete_appointment(appt_id):
    db = get_db()
    appt = db.execute("SELECT id FROM appointments WHERE id = ?", (appt_id,)).fetchone()
    if not appt:
        flash("Appointment not found.", "danger")
        return redirect(url_for("appointments.list_appointments"))

    db.execute("DELETE FROM appointments WHERE id = ?", (appt_id,))
    db.commit()
    flash("Appointment removed successfully.", "success")
    return redirect(url_for("appointments.list_appointments"))
