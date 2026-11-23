from datetime import datetime

from flask import Blueprint, render_template

from app.auth.utils import login_required, current_user
from app.models.db import get_db

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def overview():
    db = get_db()
    user = current_user()

    # Patient-specific dashboard data
    if user["role"] == "patient":
        patient = db.execute("SELECT * FROM patients WHERE user_id = ?", (user["id"],)).fetchone()
        patient_appts = []
        patient_records = []
        if patient:
            patient_appts = db.execute(
                """
                SELECT a.*, u.full_name AS doctor_name, d.specialty, dep.name AS department_name
                FROM appointments a
                JOIN doctors d ON d.id = a.doctor_id
                JOIN users u ON u.id = d.user_id
                LEFT JOIN departments dep ON dep.id = a.department_id
                WHERE a.patient_id = ?
                ORDER BY a.scheduled_at DESC
                """,
                (patient["id"],),
            ).fetchall()

            patient_records = db.execute(
                """
                SELECT mr.*, u.full_name AS doctor_name, dep.name AS department_name
                FROM medical_records mr
                LEFT JOIN doctors d ON d.id = mr.doctor_id
                LEFT JOIN users u ON u.id = d.user_id
                LEFT JOIN departments dep ON dep.id = d.department_id
                WHERE mr.patient_id = ?
                ORDER BY mr.visit_date DESC
                """,
                (patient["id"],),
            ).fetchall()

        stats = {
            "total_appointments": len(patient_appts),
            "upcoming_visits": len([a for a in patient_appts if a["status"] in ("pending", "confirmed")]),
            "completed_visits": len([a for a in patient_appts if a["status"] == "completed"]),
            "medical_records": len(patient_records),
        }

        return render_template(
            "dashboard/overview.html",
            user=user,
            stats=stats,
            patient=patient,
            patient_appts=patient_appts,
            patient_records=patient_records,
        )

    # Doctor-specific dashboard
    doctor = None
    if user["role"] == "doctor":
        doctor = db.execute("SELECT * FROM doctors WHERE user_id = ?", (user["id"],)).fetchone()

    stats = {
        "total_patients": db.execute("SELECT COUNT(*) c FROM patients").fetchone()["c"],
        "active_doctors": db.execute("SELECT COUNT(*) c FROM doctors").fetchone()["c"],
        "today_appointments": db.execute(
            "SELECT COUNT(*) c FROM appointments WHERE date(scheduled_at) = date('now')"
        ).fetchone()["c"],
        "pending_appointments": db.execute(
            "SELECT COUNT(*) c FROM appointments WHERE status = 'pending'"
        ).fetchone()["c"],
    }

    if doctor:
        stats["my_patients"] = db.execute(
            "SELECT COUNT(DISTINCT patient_id) c FROM appointments WHERE doctor_id = ?",
            (doctor["id"],),
        ).fetchone()["c"]
        stats["my_today"] = db.execute(
            "SELECT COUNT(*) c FROM appointments WHERE doctor_id = ? AND date(scheduled_at) = date('now')",
            (doctor["id"],),
        ).fetchone()["c"]

    status_counts = db.execute(
        "SELECT status, COUNT(*) c FROM appointments GROUP BY status ORDER BY status"
    ).fetchall()

    recent_appointments = db.execute(
        "SELECT a.*, p.full_name AS patient_name, u.full_name AS doctor_name "
        "FROM appointments a "
        "JOIN patients p ON p.id = a.patient_id "
        "JOIN doctors d ON d.id = a.doctor_id "
        "JOIN users u ON u.id = d.user_id "
        + ("WHERE a.doctor_id = ? " if doctor else "")
        + "ORDER BY a.scheduled_at DESC LIMIT 6",
        ((doctor["id"],) if doctor else ()),
    ).fetchall()

    upcoming = db.execute(
        "SELECT a.*, p.full_name AS patient_name, u.full_name AS doctor_name "
        "FROM appointments a "
        "JOIN patients p ON p.id = a.patient_id "
        "JOIN doctors d ON d.id = a.doctor_id "
        "JOIN users u ON u.id = d.user_id "
        "WHERE a.scheduled_at >= ? AND a.status != 'cancelled' "
        + ("AND a.doctor_id = ? " if doctor else "")
        + "ORDER BY a.scheduled_at ASC LIMIT 6",
        ((datetime.now().isoformat(timespec="minutes"), doctor["id"]) if doctor else (datetime.now().isoformat(timespec="minutes"),)),
    ).fetchall()

    return render_template(
        "dashboard/overview.html",
        user=user,
        doctor=doctor,
        stats=stats,
        status_counts=status_counts,
        recent_appointments=recent_appointments,
        upcoming=upcoming,
    )


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from app import create_app

    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from app import create_app

    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
