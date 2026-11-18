from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.models.db import get_db

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def landing():
    db = get_db()
    # Live stats from database
    total_patients = db.execute("SELECT COUNT(*) AS c FROM patients").fetchone()["c"]
    total_doctors = db.execute("SELECT COUNT(*) AS c FROM doctors").fetchone()["c"]
    total_depts = db.execute("SELECT COUNT(*) AS c FROM departments").fetchone()["c"]
    departments = db.execute("SELECT * FROM departments ORDER BY name LIMIT 5").fetchall()

    return render_template(
        "public/landing.html",
        total_patients=total_patients,
        total_doctors=total_doctors,
        total_depts=total_depts,
        departments=departments,
    )


@public_bp.route("/about")
def about():
    db = get_db()
    departments = db.execute("SELECT * FROM departments ORDER BY name").fetchall()
    return render_template("public/about.html", departments=departments)


@public_bp.route("/contact", methods=["GET", "POST"])
def contact():
    name = ""
    email = ""
    message = ""

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not message:
            flash("All fields are required. Please provide your name, valid email, and message.", "danger")
            return render_template("public/contact.html", name=name, email=email, message=message)

        flash(
            f"Thank you, {name}! Your message has been forwarded to our clinical administration team in Kochi, Kerala. We will be in touch at {email} shortly.",
            "success",
        )
        return render_template("public/contact.html", name="", email="", message="")

    return render_template("public/contact.html", name="", email="", message="")
