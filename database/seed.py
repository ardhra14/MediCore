"""
Seeds database/medicore.db with realistic sample data for MediCore.
All person names are realistic Indian (Malayali) profiles.

Run from the project root:
    python database/seed.py

This destroys and recreates the database from schema.sql every time it runs,
so it is safe to re-run during development.
"""

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from werkzeug.security import generate_password_hash  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "medicore.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"


def build():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    cur = conn.cursor()

    # --- Departments ---------------------------------------------------
    departments = [
        ("Cardiology", "Advanced heart, vascular, and cardiac interventional care"),
        ("Pediatrics", "Comprehensive child health, neonatology, and adolescent wellness"),
        ("Orthopedics", "Bone, joint, spine, sports medicine, and reconstructive surgery"),
        ("Dermatology", "Clinical dermatology, trichology, and cutaneous laser therapies"),
        ("General Medicine", "Primary adult healthcare, diabetology, and preventive medicine"),
    ]
    cur.executemany("INSERT INTO departments (name, description) VALUES (?, ?)", departments)

    # --- Users: 1 admin, 4 doctors, 2 staff/receptionists, 5 patients ----
    # Password for every seeded account: Passw0rd!
    pw = generate_password_hash("Passw0rd!")

    users = [
        ("Ardhra", "admin@medicore.test", pw, "admin"),
        ("Dr. Harikrishnan Nair", "dr.harikrishnan@medicore.test", pw, "doctor"),
        ("Dr. Ananya Kurian", "dr.ananya@medicore.test", pw, "doctor"),
        ("Dr. Mathew Varghese", "dr.mathew@medicore.test", pw, "doctor"),
        ("Dr. Fathima Beevi", "dr.fathima@medicore.test", pw, "doctor"),
        ("Sneha Menachery", "sneha.menachery@medicore.test", pw, "receptionist"),
        ("Rahul Pillai", "rahul.pillai@medicore.test", pw, "receptionist"),
        ("Eldho Paulose", "eldho.paulose@medicore.test", pw, "patient"),
        ("Amina Shereen", "amina.shereen@medicore.test", pw, "patient"),
        ("Karthik Namboodiri", "karthik.namboodiri@medicore.test", pw, "patient"),
        ("Reshma Susan Cherian", "reshma.cherian@medicore.test", pw, "patient"),
        ("Vinu Balakrishnan", "vinu.balakrishnan@medicore.test", pw, "patient"),
    ]
    cur.executemany(
        "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        users,
    )

    # --- Doctors ----------------------------------------------------------
    doctor_rows = [
        (2, 1, "Interventional Cardiology", "+91 94470 12041", "Mon-Fri 09:00 - 16:00"),
        (3, 2, "Pediatric & Neonatal Care", "+91 98471 33022", "Mon-Thu 08:30 - 14:30"),
        (4, 3, "Orthopedic Surgery & Arthroscopy", "+91 94952 88103", "Tue-Sat 10:00 - 17:00"),
        (5, 4, "Clinical & Aesthetic Dermatology", "+91 98953 44094", "Wed-Fri 09:30 - 15:30"),
    ]
    cur.executemany(
        "INSERT INTO doctors (user_id, department_id, specialty, phone, availability) "
        "VALUES (?, ?, ?, ?, ?)",
        doctor_rows,
    )

    # --- Staff --------------------------------------------------------------
    staff_rows = [
        (6, 5, "Senior Front Desk Coordinator", "+91 94471 20455"),
        (7, 5, "Clinical Pharmacist & Intake Specialist", "+91 98470 33812"),
    ]
    cur.executemany(
        "INSERT INTO staff (user_id, department_id, job_title, phone) VALUES (?, ?, ?, ?)",
        staff_rows,
    )

    # --- Patients -------------------------------------------------------
    patient_rows = [
        (8, "Eldho Paulose", "1988-04-12", "Male", "+91 98950 41230", "14/280 Panampilly Nagar, Kochi, Kerala", "O+"),
        (9, "Amina Shereen", "1995-11-02", "Female", "+91 97451 88203", "C-42 Kowdiar Gardens, Thiruvananthapuram, Kerala", "A+"),
        (10, "Karthik Namboodiri", "1974-07-23", "Male", "+91 94460 92341", "7B Silver Crest, Nadakkavu, Kozhikode, Kerala", "B+"),
        (11, "Reshma Susan Cherian", "2001-01-30", "Female", "+91 98462 77019", "22 Valley View, Devalokam, Kottayam, Kerala", "AB+"),
        (12, "Vinu Balakrishnan", "1963-09-15", "Male", "+91 94955 61840", "56 Palace Road, Chembukkavu, Thrissur, Kerala", "O-"),
    ]
    cur.executemany(
        "INSERT INTO patients (user_id, full_name, date_of_birth, gender, phone, address, blood_group) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        patient_rows,
    )

    # --- Appointments -----------------------------------------------------
    now = datetime.now()
    appt_rows = [
        (1, 1, 1, (now + timedelta(days=1, hours=2)).isoformat(timespec="minutes"), "confirmed", "Follow-up ECG and Treadmill Test review"),
        (2, 2, 2, (now + timedelta(days=2, hours=1)).isoformat(timespec="minutes"), "pending", "Routine pediatric developmental checkup"),
        (3, 3, 3, (now + timedelta(hours=3)).isoformat(timespec="minutes"), "confirmed", "Post-operative knee rehabilitation assessment"),
        (4, 4, 4, (now + timedelta(days=3)).isoformat(timespec="minutes"), "pending", "Contact dermatitis evaluation"),
        (5, 1, 1, (now - timedelta(days=5)).isoformat(timespec="minutes"), "completed", "Annual cardiac screening and lipid check"),
        (1, 2, 2, (now + timedelta(days=5)).isoformat(timespec="minutes"), "pending", "Pediatric consultation for dependent"),
        (2, 1, 1, (now - timedelta(days=10)).isoformat(timespec="minutes"), "cancelled", "Atypical chest discomfort review"),
    ]
    cur.executemany(
        "INSERT INTO appointments (patient_id, doctor_id, department_id, scheduled_at, status, reason) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        appt_rows,
    )

    # --- Medical records --------------------------------------------------
    record_rows = [
        (1, 1, "Stable Coronary Artery Disease & Dyslipidemia", "Patient reports significant improvement in exercise tolerance. Resting BP 124/82 mmHg, HR 72 bpm. Normal S1/S2.", "Tab Atorvastatin 20mg 0-0-1 (post dinner), Tab Metoprolol Succinate 25mg 1-0-0"),
        (2, 2, "Allergic Rhinitis & Mild Pharyngitis", "Nasal congestion and throat irritation persisting for 3 days. Afebrile. Chest clear on auscultation.", "Syp Montelukast + Levocetirizine 5mg/5ml once daily at bedtime x 5 days, Warm saline gargle"),
        (3, 3, "Medial Meniscus Tear (Grade II) - Right Knee", "Joint line tenderness noted on medial aspect. McMurray test mildly positive. Range of motion 0-115 degrees. Conservative physiotherapy recommended.", "Tab Aceclofenac 100mg + Paracetamol 325mg 1-0-1 pc x 5 days, Quadriceps strengthening, Knee support while walking"),
        (5, 1, "Essential Hypertension (Stage 1) - Well Controlled", "Target blood pressure achieved (128/80 mmHg). No orthostatic dizziness. Serum creatinine and electrolytes within normal reference limits.", "Tab Telmisartan 40mg 1-0-0 (morning), Low dietary sodium, 30 min daily brisk walking"),
        (4, 4, "Eczematous Dermatitis", "Localized erythematous plaques over bilateral flexor surfaces. Moderate itching reported.", "Mometasone Furoate 0.1% cream apply thin film twice daily x 7 days, Liquid paraffin emollient qid"),
    ]
    cur.executemany(
        "INSERT INTO medical_records (patient_id, doctor_id, diagnosis, notes, prescription) "
        "VALUES (?, ?, ?, ?, ?)",
        record_rows,
    )

    # --- Billing -----------------------------------------------------------
    billing_rows = [
        (1, 1, 2400.00, "paid", (now - timedelta(days=1)).isoformat(timespec="minutes")),
        (2, 2, 1200.00, "unpaid", None),
        (3, 3, 3500.00, "unpaid", None),
        (4, 4, 1800.00, "overdue", None),
        (5, 5, 4200.00, "paid", (now - timedelta(days=5)).isoformat(timespec="minutes")),
    ]
    cur.executemany(
        "INSERT INTO billing (patient_id, appointment_id, amount, status, paid_at) VALUES (?, ?, ?, ?, ?)",
        billing_rows,
    )

    conn.commit()
    conn.close()
    print(f"Seeded database at {DB_PATH}")
    print("Test accounts (password for all: Passw0rd!):")
    for name, email, _, role in users:
        print(f"  [{role:13s}] {email} ({name})")


if __name__ == "__main__":
    build()
