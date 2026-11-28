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
from app.auth.routes import _LOGIN_ATTEMPTS


class TestConfig(Config):
    TESTING = True
    SECURITY_LAB_ENABLED = True
    WTF_CSRF_ENABLED = False
    DEBUG = False


class MediCoreTestCase(unittest.TestCase):
    def setUp(self):
        _LOGIN_ATTEMPTS.clear()
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

    # --- Extended Security & RBAC Tests -------------------------------------
    def test_login_rate_limiting(self):
        # 5 consecutive failed login attempts
        for i in range(5):
            resp = self.client.post(
                "/login",
                data={"email": "admin@medicore.test", "password": "WrongPassword!"},
                follow_redirects=True,
            )
            self.assertEqual(resp.status_code, 200)
            self.assertIn(b"Invalid email or password", resp.data)

        # 6th attempt should be blocked by rate limiting
        resp = self.client.post(
            "/login",
            data={"email": "admin@medicore.test", "password": "Passw0rd!"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Too many failed login attempts", resp.data)

    def test_secure_password_reset_flow(self):
        # Request password reset for admin
        resp = self.client.post(
            "/forgot-password",
            data={"email": "admin@medicore.test"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"reset link has been generated", resp.data)

        # Fetch token from database
        with self.app.app_context():
            from app.models.db import get_db
            db = get_db()
            reset_row = db.execute(
                "SELECT * FROM password_resets WHERE user_id = 1 AND used = 0 ORDER BY id DESC"
            ).fetchone()
            self.assertIsNotNone(reset_row)

        # Token was hashed in DB; find the token generated in the flash text or generate one for testing
        # We can test the reset endpoint directly using a known raw token
        import secrets
        import hashlib
        from datetime import datetime, timedelta

        raw_test_token = secrets.token_urlsafe(32)
        test_hash = hashlib.sha256(raw_test_token.encode()).hexdigest()
        expires = datetime.utcnow() + timedelta(minutes=15)

        with self.app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO password_resets (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
                (1, test_hash, expires.isoformat()),
            )
            db.commit()

        # Perform password reset
        resp = self.client.post(
            f"/reset-password/{raw_test_token}",
            data={"password": "NewSecurePassword123!"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Password updated", resp.data)

        # Confirm old password no longer works
        resp = self.client.post(
            "/login",
            data={"email": "admin@medicore.test", "password": "Passw0rd!"},
            follow_redirects=True,
        )
        self.assertIn(b"Invalid email or password", resp.data)

        # Confirm new password logs in successfully
        resp = self.client.post(
            "/login",
            data={"email": "admin@medicore.test", "password": "NewSecurePassword123!"},
            follow_redirects=True,
        )
        self.assertIn(b"Overview", resp.data)

    def test_patient_rbac_access_restrictions(self):
        from werkzeug.security import generate_password_hash
        with self.app.app_context():
            from app.models.db import get_db
            db = get_db()
            pw = generate_password_hash("Passw0rd!")
            db.execute(
                "INSERT INTO users (id, full_name, email, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                (10, "Patient One", "patient1@medicore.test", pw, "patient"),
            )
            db.execute(
                "INSERT INTO patients (id, user_id, full_name) VALUES (?, ?, ?)",
                (10, 10, "Patient One"),
            )
            db.execute(
                "INSERT INTO users (id, full_name, email, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                (11, "Patient Two", "patient2@medicore.test", pw, "patient"),
            )
            db.execute(
                "INSERT INTO patients (id, user_id, full_name) VALUES (?, ?, ?)",
                (11, 11, "Patient Two"),
            )
            db.commit()

        # Login as Patient One
        self.client.post(
            "/login",
            data={"email": "patient1@medicore.test", "password": "Passw0rd!"},
            follow_redirects=True,
        )

        # Patient visiting /patients/ is redirected to their own profile (/patients/10)
        resp = self.client.get("/patients/", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/patients/10", resp.headers.get("Location", ""))

        # Patient One attempting to view Patient Two's profile (/patients/11) is blocked
        resp = self.client.get("/patients/11", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Access denied", resp.data)

    def test_doctor_role_restrictions(self):
        from werkzeug.security import generate_password_hash
        with self.app.app_context():
            from app.models.db import get_db
            db = get_db()
            pw = generate_password_hash("Passw0rd!")
            db.execute(
                "INSERT INTO users (id, full_name, email, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                (20, "Dr. Test Doctor", "dr.test@medicore.test", pw, "doctor"),
            )
            db.execute(
                "INSERT INTO doctors (id, user_id, department_id, specialty) VALUES (?, ?, ?, ?)",
                (20, 20, 1, "General"),
            )
            db.commit()

        # Login as Doctor
        self.client.post(
            "/login",
            data={"email": "dr.test@medicore.test", "password": "Passw0rd!"},
            follow_redirects=True,
        )

        # Doctor cannot access admin-only staff management
        resp = self.client.get("/staff/new", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"do not have permission", resp.data)

        # Doctor cannot create departments
        resp = self.client.get("/departments/new", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"do not have permission", resp.data)

    def test_login_credential_verification_and_rejection(self):
        # 1. Empty email or password
        resp = self.client.post("/login", data={"email": "", "password": ""}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Please enter both email and password", resp.data)

        # 2. Random nonexistent credentials rejected
        resp = self.client.post(
            "/login",
            data={"email": "attacker@unknown-domain.com", "password": "RandomPassword123!"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Invalid email or password", resp.data)

        # 3. Existing user with wrong password rejected
        resp = self.client.post(
            "/login",
            data={"email": "admin@medicore.test", "password": "WrongPassword999!"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Invalid email or password", resp.data)

        # 4. Random credentials when session cookie is present must NOT authenticate
        # First sign in as admin
        self.login_as_admin()
        # Verify authenticated
        resp = self.client.get("/dashboard", follow_redirects=True)
        self.assertIn(b"Overview", resp.data)

        # Attempt to post random credentials while session exists
        resp = self.client.post(
            "/login",
            data={"email": "random.user@external.com", "password": "badpassword123"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Invalid email or password", resp.data)
        self.assertNotIn(b"Welcome back, Ardhra", resp.data)

        # Confirm the session was revoked and visiting protected dashboard is denied
        resp = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers.get("Location", ""))

        # 5. Legitimate credentials authenticate properly
        resp = self.client.post(
            "/login",
            data={"email": "admin@medicore.test", "password": "Passw0rd!"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Overview", resp.data)
        self.assertIn(b"Welcome back, Ardhra", resp.data)

    # --- Two-Factor Authentication & Rate Limiting Tests --------------------
    def test_two_factor_auth_flow_and_rate_limiting(self):
        # Enable 2FA on admin user
        with self.app.app_context():
            from app.models.db import get_db
            db = get_db()
            db.execute("UPDATE users SET two_factor_enabled = 1 WHERE email = 'admin@medicore.test'")
            db.commit()

        # Login step 1: Valid password triggers 2FA challenge redirect
        resp = self.client.post(
            "/login",
            data={"email": "admin@medicore.test", "password": "Passw0rd!"},
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/verify-2fa", resp.headers.get("Location", ""))

        # Verify 2FA challenge page loads
        resp = self.client.get("/verify-2fa")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Two-Factor Verification", resp.data)

        # Invalid OTP rejected
        resp = self.client.post("/verify-2fa", data={"otp_code": "999999"}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Invalid or expired 2FA code", resp.data)

        # Fetch generated OTP from database
        with self.app.app_context():
            db = get_db()
            otp_row = db.execute(
                "SELECT * FROM otp_codes WHERE user_id = 1 AND used = 0 ORDER BY id DESC LIMIT 1"
            ).fetchone()
            self.assertIsNotNone(otp_row)
            valid_otp = otp_row["otp_code"]

        # Valid OTP succeeds and logs in
        resp = self.client.post("/verify-2fa", data={"otp_code": valid_otp}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Overview", resp.data)
        self.assertIn(b"Welcome back, Ardhra", resp.data)

    # --- Vulnerable 2FA Security Lab Tests -----------------------------------
    def test_vulnerable_2fa_lab_bypasses(self):
        # Initiate lab 2FA
        resp = self.client.post(
            "/lab/2fa/login",
            data={"email": "admin@medicore.test", "password": "Passw0rd!"},
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/lab/2fa/verify", resp.headers.get("Location", ""))

        # Bypass 1: Header-based bypass (X-Bypass-2FA: true)
        resp = self.client.post(
            "/lab/2fa/verify",
            data={"otp_code": "wrong1"},
            headers={"X-Bypass-2FA": "true"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"EXPLOIT SUCCESSFUL", resp.data)
        self.assertIn(b"Header-based bypass", resp.data)

        # Re-login for Bypass 2
        self.client.post(
            "/lab/2fa/login",
            data={"email": "admin@medicore.test", "password": "Passw0rd!"},
            follow_redirects=False,
        )

        # Bypass 2: Universal master code (000000)
        resp = self.client.post(
            "/lab/2fa/verify",
            data={"otp_code": "000000"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"EXPLOIT SUCCESSFUL", resp.data)
        self.assertIn(b"Master code bypass", resp.data)

    # --- Rate Limiting Lab Tests --------------------------------------------
    def test_rate_limit_lab_scenarios(self):
        from security_lab.rate_limit_bypass.routes import _PROTECTED_ATTEMPTS
        _PROTECTED_ATTEMPTS.clear()

        # Protected endpoint enforces 429 after 5 failed attempts
        for i in range(5):
            resp = self.client.post("/lab/rate-limit/verify-otp-protected", json={"pin": "0000"})
            self.assertEqual(resp.status_code, 400)

        # 6th attempt is blocked with HTTP 429
        resp = self.client.post("/lab/rate-limit/verify-otp-protected", json={"pin": "0000"})
        self.assertEqual(resp.status_code, 429)

        # Vulnerable endpoint allows unlimited requests with no 429 lockout
        for i in range(12):
            resp = self.client.post("/lab/rate-limit/verify-otp-vulnerable", json={"pin": f"100{i}"})
            self.assertEqual(resp.status_code, 400)

        # Correct PIN 4281 succeeds immediately on vulnerable endpoint
        resp = self.client.post("/lab/rate-limit/verify-otp-vulnerable", json={"pin": "4281"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json().get("success"))

    # --- JWT Vulnerability & Privilege Escalation Lab Tests -----------------
    def test_jwt_lab_privilege_escalation(self):
        # Login and obtain standard non-admin JWT
        resp = self.client.post(
            "/lab/jwt/login",
            data={"email": "admin@medicore.test", "password": "Passw0rd!"},
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)

        # Access with non-admin token fails (using helper to forge patient token)
        from security_lab.jwt_vulnerabilities.routes import create_lab_jwt
        patient_payload = {
            "sub": 8,
            "email": "eldho.paulose@medicore.test",
            "name": "Eldho Paulose",
            "role": "patient",
            "isAdmin": False,
        }
        legit_token = create_lab_jwt(patient_payload, alg="HS256")
        resp = self.client.get(
            "/lab/jwt/admin",
            headers={"Authorization": f"Bearer {legit_token}", "Accept": "application/json"},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Privilege Escalation Required", resp.get_json().get("error", ""))

        # Exploit: forge token with alg: "none" and isAdmin: true
        escalated_payload = {
            "sub": 8,
            "email": "eldho.paulose@medicore.test",
            "name": "Eldho Paulose",
            "role": "admin",
            "isAdmin": True,
        }
        forged_token = create_lab_jwt(escalated_payload, alg="none")
        resp = self.client.get(
            "/lab/jwt/admin",
            headers={"Authorization": f"Bearer {forged_token}", "Accept": "application/json"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("GRANTED", data.get("access", ""))
        self.assertEqual(data.get("authenticated_claims", {}).get("isAdmin"), True)

    # --- Information Disclosure Lab Tests ------------------------------------
    def test_information_disclosure_lab(self):
        resp = self.client.get("/lab/info-disclosure/diagnostics?format=json")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("server_environment", data)
        self.assertIn("application_configuration", data)
        self.assertIn("database_internals", data)
        self.assertIn("python_executable", data["server_environment"])
        self.assertIn("users", data["database_internals"]["active_tables"])


if __name__ == "__main__":
    unittest.main()
