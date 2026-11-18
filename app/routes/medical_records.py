from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.auth.utils import login_required, roles_required, current_user
from app.models.db import get_db

records_bp = Blueprint("records", __name__, url_prefix="/records")


@records_bp.route("/")
@login_required
@roles_required("admin", "doctor")
def list_records():
    db = get_db()
    q = request.args.get("q", "").strip()

    sql = """
        SELECT mr.*, p.full_name AS patient_name, u.full_name AS doctor_name, dep.name AS department_name
        FROM medical_records mr
        JOIN patients p ON p.id = mr.patient_id
        LEFT JOIN doctors d ON d.id = mr.doctor_id
        LEFT JOIN users u ON u.id = d.user_id
        LEFT JOIN departments dep ON dep.id = d.department_id
        WHERE 1=1
    """
    params = []

    if q:
        sql += " AND (p.full_name LIKE ? OR mr.diagnosis LIKE ? OR mr.prescription LIKE ?)"
        pattern = f"%{q}%"
        params.extend([pattern, pattern, pattern])

    sql += " ORDER BY mr.visit_date DESC"
    rows = db.execute(sql, params).fetchall()

    return render_template("records/list.html", records=rows, q=q)


@records_bp.route("/<int:record_id>")
@login_required
@roles_required("admin", "doctor")
def view_record(record_id):
    db = get_db()
    record = db.execute(
        """
        SELECT mr.*, p.full_name AS patient_name, p.date_of_birth, p.gender, p.blood_group, p.phone AS patient_phone,
               u.full_name AS doctor_name, d.specialty AS doctor_specialty, dep.name AS department_name
        FROM medical_records mr
        JOIN patients p ON p.id = mr.patient_id
        LEFT JOIN doctors d ON d.id = mr.doctor_id
        LEFT JOIN users u ON u.id = d.user_id
        LEFT JOIN departments dep ON dep.id = d.department_id
        WHERE mr.id = ?
        """,
        (record_id,),
    ).fetchone()
    if not record:
        flash("Medical record not found.", "danger")
        return redirect(url_for("records.list_records"))

    return render_template("records/view.html", record=record)


@records_bp.route("/new", methods=["GET", "POST"])
@login_required
@roles_required("admin", "doctor")
def new_record():
    db = get_db()
    patients = db.execute("SELECT * FROM patients ORDER BY full_name").fetchall()
    doctors = db.execute(
        "SELECT d.id, u.full_name FROM doctors d JOIN users u ON u.id = d.user_id ORDER BY u.full_name"
    ).fetchall()

    pre_patient_id = request.args.get("patient_id", type=int)
    pre_doctor_id = request.args.get("doctor_id", type=int)

    # Auto-detect if current logged-in user is a doctor
    curr = current_user()
    if curr and curr["role"] == "doctor" and not pre_doctor_id:
        doc_match = db.execute("SELECT id FROM doctors WHERE user_id = ?", (curr["id"],)).fetchone()
        if doc_match:
            pre_doctor_id = doc_match["id"]

    if request.method == "POST":
        patient_id = request.form.get("patient_id")
        doctor_id = request.form.get("doctor_id") or None
        diagnosis = request.form.get("diagnosis", "").strip()
        notes = request.form.get("notes", "").strip()
        prescription = request.form.get("prescription", "").strip()

        if not patient_id:
            flash("Please select a patient.", "danger")
            return render_template(
                "records/form.html",
                patients=patients,
                doctors=doctors,
                record=None,
                pre_patient_id=pre_patient_id,
                pre_doctor_id=pre_doctor_id,
            )

        cur = db.execute(
            """
            INSERT INTO medical_records (patient_id, doctor_id, diagnosis, notes, prescription)
            VALUES (?, ?, ?, ?, ?)
            """,
            (patient_id, doctor_id, diagnosis, notes, prescription),
        )
        db.commit()
        flash("Medical record documented successfully.", "success")
        return redirect(url_for("records.view_record", record_id=cur.lastrowid))

    return render_template(
        "records/form.html",
        patients=patients,
        doctors=doctors,
        record=None,
        pre_patient_id=pre_patient_id,
        pre_doctor_id=pre_doctor_id,
    )


@records_bp.route("/<int:record_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("admin", "doctor")
def edit_record(record_id):
    db = get_db()
    record = db.execute("SELECT * FROM medical_records WHERE id = ?", (record_id,)).fetchone()
    if not record:
        flash("Medical record not found.", "danger")
        return redirect(url_for("records.list_records"))

    patients = db.execute("SELECT * FROM patients ORDER BY full_name").fetchall()
    doctors = db.execute(
        "SELECT d.id, u.full_name FROM doctors d JOIN users u ON u.id = d.user_id ORDER BY u.full_name"
    ).fetchall()

    if request.method == "POST":
        patient_id = request.form.get("patient_id")
        doctor_id = request.form.get("doctor_id") or None
        diagnosis = request.form.get("diagnosis", "").strip()
        notes = request.form.get("notes", "").strip()
        prescription = request.form.get("prescription", "").strip()

        db.execute(
            """
            UPDATE medical_records
            SET patient_id = ?, doctor_id = ?, diagnosis = ?, notes = ?, prescription = ?
            WHERE id = ?
            """,
            (patient_id, doctor_id, diagnosis, notes, prescription, record_id),
        )
        db.commit()
        flash("Medical record updated successfully.", "success")
        return redirect(url_for("records.view_record", record_id=record_id))

    return render_template(
        "records/form.html",
        patients=patients,
        doctors=doctors,
        record=record,
        pre_patient_id=record["patient_id"],
        pre_doctor_id=record["doctor_id"],
    )


@records_bp.route("/<int:record_id>/delete", methods=["POST"])
@login_required
@roles_required("admin", "doctor")
def delete_record(record_id):
    db = get_db()
    record = db.execute("SELECT id FROM medical_records WHERE id = ?", (record_id,)).fetchone()
    if not record:
        flash("Medical record not found.", "danger")
        return redirect(url_for("records.list_records"))

    db.execute("DELETE FROM medical_records WHERE id = ?", (record_id,))
    db.commit()
    flash("Medical record has been deleted.", "success")
    return redirect(url_for("records.list_records"))
