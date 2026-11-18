# MediCore — Architecture & Technical Specifications

## Technical Stack

| Layer      | Technologies & Frameworks |
|------------|---------------------------|
| **Frontend** | HTML5, CSS3 Custom Properties, JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons 1.11, Chart.js 4.4 |
| **Backend**  | Python 3.9+, Flask 3.0+ (Blueprint architecture), Werkzeug 3.0+ |
| **Database** | SQLite 3 (`database/medicore.db`) with Foreign Key enforcement (`PRAGMA foreign_keys = ON`) |
| **Security** | PBKDF2-SHA256 password hashing, CSPRNG 256-bit server-side session tokens, HttpOnly/SameSite cookies |
| **Testing**  | Python `unittest` test suite & `pytest` runner |

---

## Repository Structure

```
MediCore/
├── app/
│   ├── auth/                       # Production-grade authentication & session management
│   │   ├── routes.py               # Login, register, logout, secure password reset
│   │   ├── utils.py                # CSPRNG session generator, auth decorators, RBAC checks
│   │   └── __init__.py
│   ├── models/                     # Database access layer
│   │   ├── db.py                   # SQLite connection provider & teardown context
│   │   ├── user.py                 # User CRUD & password updates
│   │   └── __init__.py
│   ├── routes/                     # Application feature modules (Blueprints)
│   │   ├── appointments.py         # Scheduling, status workflows (pending, confirmed, completed, cancelled)
│   │   ├── billing.py              # Invoicing, GST tax receipts, payment status, ledger
│   │   ├── dashboard.py            # Clinical overview & Chart.js caseload telemetry
│   │   ├── departments.py          # Hospital clinical division management
│   │   ├── doctors.py              # Specialist profiles, credentials, availability schedules
│   │   ├── medical_records.py      # EMR consultations, clinical progress notes, prescriptions
│   │   ├── patients.py             # Patient registry, search, demographic profiles
│   │   ├── public.py               # Landing page, about, interactive contact desk
│   │   ├── reports.py              # Department performance, revenue metrics, CSV exports
│   │   ├── settings.py             # Profile management, password change, active sessions
│   │   └── staff.py                # Administrative & front-desk staff roster
│   ├── static/
│   │   ├── css/styles.css          # Commercial Healthcare SaaS visual design system
│   │   ├── images/
│   │   │   ├── favicon.svg         # Crisp 48x48 healthcare vector mark
│   │   │   ├── logo.svg            # Dual-helix clinical vector logo (light theme)
│   │   │   └── logo-white.svg      # Vector logo optimized for dark sidebar
│   │   └── js/app.js               # Responsive sidebar drawer, alert management
│   └── templates/                  # Jinja2 template hierarchy
├── config.py                       # Environment configuration, cookie flags, security lab toggles
├── database/
│   ├── schema.sql                  # Complete relational schema (10 tables + indexes)
│   └── seed.py                     # Realistic Indian / Malayali sample data generator
├── docs/
│   ├── architecture.md             # This document
│   └── security_testing.md         # Vulnerability reproduction guide & remediation
├── security_lab/                   # Isolated educational penetration-testing modules
│   ├── broken_password_recovery/   # CWE-640 / CWE-330 predictable reset token lab
│   └── insecure_session_management/# CWE-384 / CWE-330 guessable sequential session lab
├── tests/
│   └── test_basic.py               # Comprehensive 17-point test suite
├── .env.example                    # Environment variable template
├── .gitignore                      # Git exclusion rules
├── LICENSE                         # MIT License
├── README.md                       # Professional GitHub documentation
├── requirements.txt                # Production & test dependencies
└── run.py                          # Application entry point (127.0.0.1:5000)
```

---

## Security Architecture

### Production Security Path
- **Password Protection**: Passwords are never stored in plaintext. They are salted and hashed using PBKDF2-HMAC-SHA256 with 600,000+ iterations via Werkzeug.
- **Session Tokens**: Generated with `secrets.token_urlsafe(32)` providing 256 bits of CSPRNG entropy. Tokens are stored server-side in the `sessions` table.
- **Cookie Security**: Set with `HttpOnly=True`, `SameSite="Lax"`, and optional `Secure=True` behind TLS.
- **Password Reset**: Cryptographically random CSPRNG tokens. Only the SHA-256 hash is persisted in the database; tokens expire after 15 minutes and are strictly single-use.
- **Role-Based Access Control**:
  - `admin`: Full platform control, doctor & staff onboarding, department deletion, system settings.
  - `doctor`: Clinical documentation, medical records, patient history, consultations.
  - `receptionist`: Patient intake, appointment scheduling, billing and invoice generation.
  - `patient`: Personal health profile, appointment bookings, medical visit history.

### Isolated Security Lab (Vulnerabilities 1 & 2)
The application houses two intentionally vulnerable blueprints under `security_lab/`:
1. `vuln_recovery_bp` (`/lab/password-recovery`): Weak password recovery relying on numeric user ID and UTC minute without secret randomness (CWE-640, CWE-330).
2. `vuln_session_bp` (`/lab/session-demo`): Insecure session management returning sequential integer primary keys in non-HttpOnly cookies (CWE-384, CWE-330).

Both blueprints are:
- Strictly isolated in their own directory (`security_lab/`).
- Disabled by default; set `SECURITY_LAB_ENABLED=1` in `config.py` / `.env` to mount them.
- Guarded by a `before_request` hook that aborts with HTTP 403 unless the `Host` header is `127.0.0.1` or `localhost`.
- Stored in separate tables (`vuln_reset_tokens`, `vuln_sessions`) defined in `security_lab/schema.sql`, so production authentication state remains unaffected.
