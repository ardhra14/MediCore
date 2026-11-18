"""
Comprehensive test suite for MediCore Healthcare Systems.
Compatible with both:
    python -m unittest tests/test_basic.py
and
    pytest tests/
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from config import Config


class TestConfig(Config):
    TESTING = True
    SECURITY_LAB_ENABLED = True
    WTF_CSRF_ENABLED = False
    DEBUG = False


class MediCoreTestCase(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        TestConfig.DATABASE_PATH = self.db_path
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "schema.sql"
        )
        with self.app.app_context():
            from app.models.db import get_db
            db = get_db()
            with open(schema_path, encoding="utf-8") as f:
                db.executescript(f.read())
            lab_schema_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "security_lab",
                "schema.sql",
            )
            if os.path.exists(lab_schema_path):
                with open(lab_schema_path, encoding="utf-8") as f:
                    db.executescript(f.read())
            db.commit()

            # Seed a default admin and department for tests
            from werkzeug.security import generate_password_hash
            pw = generate_password_hash("Passw0rd!")
            db.execute(
                "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                ("Ardhra", "admin@medicore.test", pw, "admin"),
            )
            db.execute(
                "INSERT INTO departments (name, description) VALUES (?, ?)",
                ("Cardiology", "Heart and vascular clinical care"),
            )
            db.commit()

    def tearDown(self):
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def login_as_admin(self):
        return self.client.post(
            "/login",
            data={"email": "admin@medicore.test", "password": "Passw0rd!"},
            follow_redirects=True,
        )

    # --- Public Pages & Contact ---------------------------------------------
    def test_landing_page_loads(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"MediCore", resp.data)

    def test_about_page_loads(self):
        resp = self.client.get("/about")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"MediCore", resp.data)

    def test_contact_form_submission(self):
        # Empty submission fails
        resp = self.client.post("/contact", data={"name": "", "email": "", "message": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"All fields are required", resp.data)

        # Valid submission succeeds
        resp = self.client.post(
            "/contact",
            data={
                "name": "Eldho Paulose",
                "email": "eldho@example.com",
                "message": "Inquiring about pediatric cardiology consultation hours.",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Thank you, Eldho Paulose!", resp.data)

    # --- Authentication Flow ------------------------------------------------
    def test_login_page_loads(self):
        resp = self.client.get("/login")
        self.assertEqual(resp.status_code, 200)

    def test_register_and_login_flow(self):
        # Register new patient
        resp = self.client.post(
            "/register",
            data={
                "full_name": "Amina Shereen",
                "email": "amina.shereen@medicore.test",
                "password": "Passw0rd!",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Account created", resp.data)

        # Login with newly registered patient
        resp = self.client.post(
            "/login",
            data={"email": "amina.shereen@medicore.test", "password": "Passw0rd!"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Overview", resp.data)

    def test_dashboard_requires_login(self):
        resp = self.client.get("/dashboard", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(b"sign in" in resp.data.lower() or b"login" in resp.data.lower())

    def test_logout(self):
        self.login_as_admin()
        resp = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"signed out", resp.data)

    # --- Patients CRUD ------------------------------------------------------
    def test_patient_crud_operations(self):
        self.login_as_admin()

        # Create Patient
        resp = self.client.post(
            "/patients/new",
            data={
                "full_name": "Karthik Namboodiri",
                "date_of_birth": "1974-07-23",
                "gender": "Male",
                "phone": "+91 94460 92341",
                "address": "Nadakkavu, Kozhikode, Kerala",
                "blood_group": "B+",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Karthik Namboodiri", resp.data)

        # View Patient
        resp = self.client.get("/patients/1")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Karthik Namboodiri", resp.data)
        self.assertIn(b"Nadakkavu", resp.data)

        # Edit Patient
        resp = self.client.post(
            "/patients/1/edit",
            data={
                "full_name": "Karthik Namboodiri Varma",
                "date_of_birth": "1974-07-23",
                "gender": "Male",
                "phone": "+91 94460 99999",
                "address": "Silver Crest, Kozhikode, Kerala",
                "blood_group": "B+",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Karthik Namboodiri Varma", resp.data)

        # Delete Patient
        resp = self.client.post("/patients/1/delete", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"deleted successfully", resp.data)

    # --- Doctors & Appointments CRUD ----------------------------------------
    def test_doctor_and_appointment_workflow(self):
        self.login_as_admin()

        # Add Doctor
        resp = self.client.post(
            "/doctors/new",
            data={
                "full_name": "Dr. Harikrishnan Nair",
                "email": "dr.harikrishnan@medicore.test",
                "password": "Passw0rd!",
                "department_id": 1,
                "specialty": "Interventional Cardiology",
                "phone": "+91 94470 12041",
                "availability": "Mon-Fri 09:00 - 16:00",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Dr. Harikrishnan Nair", resp.data)

        # Add Patient for appointment
        self.client.post(
            "/patients/new",
            data={"full_name": "Eldho Paulose", "phone": "+91 98950 41230", "blood_group": "O+"},
            follow_redirects=True,
        )

        # Book Appointment
        resp = self.client.post(
            "/appointments/new",
            data={
                "patient_id": 1,
                "doctor_id": 1,
                "department_id": 1,
                "scheduled_at": "2026-12-01T10:30",
                "reason": "Routine ECG consultation",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Appointment scheduled", resp.data)

        # Confirm Appointment
        resp = self.client.post("/appointments/1/status/confirmed", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"confirmed", resp.data)

        # Mark Completed
        resp = self.client.post("/appointments/1/status/completed", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"completed", resp.data)

    # --- Medical Records CRUD -----------------------------------------------
    def test_medical_records_crud(self):
        self.login_as_admin()

        # Setup Patient
        self.client.post(
            "/patients/new",
            data={"full_name": "Reshma Susan Cherian", "blood_group": "AB+"},
            follow_redirects=True,
        )

        # Add Medical Record
        resp = self.client.post(
            "/records/new",
            data={
                "patient_id": 1,
                "diagnosis": "Allergic Rhinitis",
                "notes": "Patient presented with sneezing and nasal blockage.",
                "prescription": "Tab Levocetirizine 5mg 0-0-1 x 5 days",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Allergic Rhinitis", resp.data)
        self.assertIn(b"Levocetirizine", resp.data)

        # View Record
        resp = self.client.get("/records/1")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Allergic Rhinitis", resp.data)

        # Edit Record
        resp = self.client.post(
            "/records/1/edit",
            data={
                "patient_id": 1,
                "diagnosis": "Acute Allergic Rhinosinusitis",
                "notes": "Symptoms improving on antihistamines.",
                "prescription": "Tab Levocetirizine 5mg 0-0-1, Fluticasone Nasal Spray",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Acute Allergic Rhinosinusitis", resp.data)

    # --- Departments CRUD ---------------------------------------------------
    def test_departments_crud(self):
        self.login_as_admin()

        # Create
        resp = self.client.post(
            "/departments/new",
            data={"name": "Pediatrics & Neonatology", "description": "Child care and newborn ICU"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Pediatrics &amp; Neonatology", resp.data)

        # View
        resp = self.client.get("/departments/2")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Pediatrics &amp; Neonatology", resp.data)

        # Edit
        resp = self.client.post(
            "/departments/2/edit",
            data={"name": "Advanced Pediatrics", "description": "Comprehensive child wellness"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Advanced Pediatrics", resp.data)

        # Delete
        resp = self.client.post("/departments/2/delete", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"deleted", resp.data)

    # --- Staff CRUD ---------------------------------------------------------
    def test_staff_crud(self):
        self.login_as_admin()

        # Add Staff
        resp = self.client.post(
            "/staff/new",
            data={
                "full_name": "Sneha Menachery",
                "email": "sneha.menachery@medicore.test",
                "password": "Passw0rd!",
                "department_id": 1,
                "job_title": "Senior Front Desk Coordinator",
                "phone": "+91 94471 20455",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Sneha Menachery", resp.data)

        # Edit Staff
        resp = self.client.post(
            "/staff/1/edit",
            data={
                "full_name": "Sneha Menachery Pillai",
                "department_id": 1,
                "job_title": "Chief Patient Intake Officer",
                "phone": "+91 94471 99999",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Sneha Menachery Pillai", resp.data)

        # Delete Staff
        resp = self.client.post("/staff/1/delete", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"removed", resp.data)

    # --- Security Lab Blueprints (Vulnerabilities Preserved) -----------------
    def test_vulnerable_recovery_blueprint_mounted(self):
        resp = self.client.get("/lab/password-recovery/forgot-password")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Vulnerable", resp.data)

        # Execute Vulnerability 1 full flow:
        # Request reset code for admin@medicore.test (user id 1)
        resp = self.client.post(
            "/lab/password-recovery/forgot-password",
            data={"email": "admin@medicore.test"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(b"Generated Token:" in resp.data or b"Demo token:" in resp.data)

        # Extract token or compute it
        from datetime import datetime
        now = datetime.utcnow()
        computed_token = f"{1 % 100:02d}{now.hour * 60 + now.minute:04d}"

        # Reset password via predictable token without email access
        resp = self.client.post(
            f"/lab/password-recovery/reset/{computed_token}",
            data={"password": "HackedPassword123!"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Password reset via the vulnerable lab flow", resp.data)

        # Verify login with the overwritten password
        resp = self.client.post(
            "/login",
            data={"email": "admin@medicore.test", "password": "HackedPassword123!"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Overview", resp.data)

    def test_vulnerable_session_blueprint_mounted(self):
        resp = self.client.get("/lab/session-demo/login")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Vulnerable", resp.data)

        # Execute Vulnerability 2 full flow:
        # Sign in via lab session login
        resp = self.client.post(
            "/lab/session-demo/login",
            data={"email": "admin@medicore.test", "password": "Passw0rd!"},
            follow_redirects=False,
        )
        # Verify 302 redirect to whoami and cookie is set
        self.assertEqual(resp.status_code, 302)
        cookie_header = resp.headers.get("Set-Cookie", "")
        self.assertIn("lab_session=", cookie_header)

        # Test whoami with guessable session id = 1
        self.client.set_cookie("lab_session", "1")
        resp = self.client.get("/lab/session-demo/whoami")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("authenticated"))
        self.assertEqual(data.get("full_name"), "Ardhra")


if __name__ == "__main__":
    unittest.main()
