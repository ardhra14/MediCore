import csv
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response

from app.auth.utils import login_required, roles_required
from app.models.db import get_db

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
@login_required
@roles_required("admin")
def index():
    db = get_db()
    summary = {
        "patients": db.execute("SELECT COUNT(*) c FROM patients").fetchone()["c"],
        "doctors": db.execute("SELECT COUNT(*) c FROM doctors").fetchone()["c"],
        "appointments": db.execute("SELECT COUNT(*) c FROM appointments").fetchone()["c"],
    }
    doctor_workload = db.execute(
        """
        SELECT u.full_name,
               COUNT(a.id) AS total_appointments,
               SUM(CASE WHEN a.status = 'completed' THEN 1 ELSE 0 END) AS completed_appointments
        FROM doctors d
        JOIN users u ON u.id = d.user_id
        LEFT JOIN appointments a ON a.doctor_id = d.id
        GROUP BY d.id
        ORDER BY total_appointments DESC
        """
    ).fetchall()
    return render_template("reports/index.html", summary=summary, doctor_workload=doctor_workload)


@reports_bp.route("/export/<dataset>")
@login_required
@roles_required("admin")
def export_csv(dataset):
    db = get_db()
    queries = {
        "appointments": (
            "SELECT a.id, p.full_name AS patient_name, u.full_name AS doctor_name, "
            "a.scheduled_at, a.status, a.reason FROM appointments a "
            "JOIN patients p ON p.id = a.patient_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "JOIN users u ON u.id = d.user_id ORDER BY a.scheduled_at DESC"
        ),
        "billing": (
            "SELECT b.id, p.full_name AS patient_name, b.amount, b.status, b.issued_at, b.paid_at "
            "FROM billing b JOIN patients p ON p.id = b.patient_id ORDER BY b.issued_at DESC"
        ),
        "patients": (
            "SELECT id, full_name, date_of_birth, gender, phone, address, blood_group "
            "FROM patients ORDER BY full_name"
        ),
    }
    if dataset not in queries:
        flash("Unknown report dataset.", "danger")
        return redirect(url_for("reports.index"))

    rows = db.execute(queries[dataset]).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(rows[0].keys() if rows else ["result"])
    for row in rows:
        writer.writerow([row[key] for key in row.keys()])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={dataset}.csv"},
    )