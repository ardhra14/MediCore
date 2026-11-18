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

    status_counts = db.execute(
        "SELECT status, COUNT(*) c FROM appointments GROUP BY status ORDER BY status"
    ).fetchall()

    recent_appointments = db.execute(
        "SELECT a.*, p.full_name AS patient_name, u.full_name AS doctor_name "
        "FROM appointments a "
        "JOIN patients p ON p.id = a.patient_id "
        "JOIN doctors d ON d.id = a.doctor_id "
        "JOIN users u ON u.id = d.user_id "
        "ORDER BY a.scheduled_at DESC LIMIT 6"
    ).fetchall()

    upcoming = db.execute(
        "SELECT a.*, p.full_name AS patient_name, u.full_name AS doctor_name "
        "FROM appointments a "
        "JOIN patients p ON p.id = a.patient_id "
        "JOIN doctors d ON d.id = a.doctor_id "
        "JOIN users u ON u.id = d.user_id "
        "WHERE a.scheduled_at >= ? AND a.status != 'cancelled' "
        "ORDER BY a.scheduled_at ASC LIMIT 6",
        (datetime.now().isoformat(timespec="minutes"),),
    ).fetchall()

    return render_template(
        "dashboard/overview.html",
        user=user,
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
