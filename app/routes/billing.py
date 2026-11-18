from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.auth.utils import login_required, roles_required
from app.models.db import get_db

billing_bp = Blueprint("billing", __name__, url_prefix="/billing")


@billing_bp.route("/")
@login_required
@roles_required("admin", "receptionist")
def list_invoices():
    db = get_db()
    rows = db.execute(
        """
        SELECT b.*, p.full_name AS patient_name
        FROM billing b
        JOIN patients p ON p.id = b.patient_id
        ORDER BY b.issued_at DESC
        """
    ).fetchall()
    return render_template("billing/list.html", invoices=rows)


@billing_bp.route("/new", methods=["GET", "POST"])
@login_required
@roles_required("admin", "receptionist")
def new_invoice():
    db = get_db()
    patients = db.execute("SELECT * FROM patients ORDER BY full_name").fetchall()

    if request.method == "POST":
        patient_id = request.form.get("patient_id")
        amount = request.form.get("amount")
        appointment_id = request.form.get("appointment_id") or None
        status = request.form.get("status", "unpaid")

        if not patient_id or not amount or status not in ("unpaid", "paid", "overdue"):
            flash("Patient, amount, and a valid status are required.", "danger")
            return render_template("billing/form.html", patients=patients)

        try:
            amount_value = float(amount)
        except ValueError:
            flash("Amount must be a valid number.", "danger")
            return render_template("billing/form.html", patients=patients)

        now = datetime.utcnow().isoformat(timespec="minutes")
        cur = db.execute(
            """
            INSERT INTO billing (patient_id, appointment_id, amount, status, issued_at, paid_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (patient_id, appointment_id, amount_value, status, now, now if status == "paid" else None),
        )
        db.commit()
        flash(f"Invoice #{cur.lastrowid} generated successfully.", "success")
        return redirect(url_for("billing.view_invoice", invoice_id=cur.lastrowid))

    return render_template("billing/form.html", patients=patients)


@billing_bp.route("/<int:invoice_id>")
@login_required
@roles_required("admin", "receptionist")
def view_invoice(invoice_id):
    db = get_db()
    invoice = db.execute(
        """
        SELECT b.*, p.full_name AS patient_name, p.phone AS patient_phone
        FROM billing b
        JOIN patients p ON p.id = b.patient_id
        WHERE b.id = ?
        """,
        (invoice_id,),
    ).fetchone()
    if not invoice:
        flash("Invoice not found.", "danger")
        return redirect(url_for("billing.list_invoices"))
    return render_template("billing/view.html", invoice=invoice)


@billing_bp.route("/<int:invoice_id>/mark-paid", methods=["POST"])
@login_required
@roles_required("admin", "receptionist")
def mark_paid(invoice_id):
    db = get_db()
    invoice = db.execute("SELECT id FROM billing WHERE id = ?", (invoice_id,)).fetchone()
    if not invoice:
        flash("Invoice not found.", "danger")
        return redirect(url_for("billing.list_invoices"))

    db.execute(
        "UPDATE billing SET status = 'paid', paid_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(timespec="minutes"), invoice_id),
    )
    db.commit()
    flash("Invoice marked as paid.", "success")
    return redirect(url_for("billing.view_invoice", invoice_id=invoice_id))