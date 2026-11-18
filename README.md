<p align="center">
  <img src="app/static/images/logo.svg" alt="MediCore Healthcare Systems" width="260">
</p>

<h3 align="center">Enterprise Healthcare Operating System &amp; Clinical Administration Platform</h3>

<p align="center">
  A full-stack hospital and clinical practice administration suite built for modern healthcare facilities — featuring role-based operations, electronic health records, automated billing, analytics telemetry, and an isolated cybersecurity penetration-testing lab.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/Framework-Flask%203.0-teal?logo=flask&logoColor=white" alt="Flask 3.0">
  <img src="https://img.shields.io/badge/Database-SQLite%203-003B57?logo=sqlite&logoColor=white" alt="SQLite 3">
  <img src="https://img.shields.io/badge/UI-Bootstrap%205.3%20%7C%20Chart.js-purple" alt="Bootstrap 5.3">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License">
</p>

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Architecture & Design](#architecture--design)
- [Installation & Quickstart](#installation--quickstart)
- [Pre-Configured Test Accounts](#pre-configured-test-accounts)
- [Screenshots](#screenshots)
- [Security Lab (Educational Testing)](#security-lab-educational-testing)
- [Running Automated Tests](#running-automated-tests)
- [Project Structure](#project-structure)
- [License](#license)

---

## Overview

**MediCore** is an enterprise-grade clinic and hospital administration platform developed to streamline outpatient and inpatient clinical workflows. From patient intake and demographic tracking to specialist scheduling, electronic medical records (EMR), prescription authoring, and GST-ready billing receipts, MediCore unifies all hospital operations into a coherent, responsive SaaS interface.

In addition to production-style secure authentication (salted PBKDF2 hashing, CSPRNG 256-bit server-side session tokens, and short-lived hashed reset tokens), MediCore houses an **isolated cybersecurity lab** containing two intentionally vulnerable authentication mechanisms for authorized penetration testing, CTF training, and educational evaluation.

---

## Key Features

### 1. Clinical Operations
- **Patient Registry & EMR**: Complete demographic profiles, blood group tracking, contact information, and longitudinal medical visit history.
- **Multi-Field Patient Search**: Instant lookup by name, phone number, address locality, blood group, or gender.
- **Doctor & Specialist Roster**: Profiles detailing specialties (Cardiology, Pediatrics, Orthopedics, Dermatology, General Medicine), OPD availability hours, and active caseloads.
- **OPD Appointment Scheduling**: Book visits, reschedule slots, and transition states (`pending` &rarr; `confirmed` &rarr; `completed` or `cancelled`).
- **Electronic Medical Records (EMR)**: Structured diagnosis records, physician clinical progress notes, and Rx prescriptions with printable clinical charts.

### 2. Practice Administration & Billing
- **Hospital Department Hierarchy**: Configure clinical divisions with automated doctor, staff, and appointment counts.
- **Staff Credentialing**: Onboard receptionists, intake specialists, and clinical coordinators with department assignments.
- **Patient Invoicing & Ledger**: Generate tax invoices with itemized OPD rates, track payment statuses (`unpaid`, `paid`, `overdue`), and print formal medical receipts.

### 3. Analytics & Reporting
- **Interactive Telemetry**: Real-time Chart.js doughnut charts visualizing appointment caseloads by status.
- **Doctor Workload Matrix**: Breakdown of total patient consultations and completion metrics.
- **One-Click CSV Exports**: Download complete datasets for Appointments, Invoices, and Patients directly from the Reports portal.

### 4. Account Settings & Security
- **Personal Profile Management**: Update contact phone numbers and residential addresses.
- **Self-Service Password Change**: Verified current password check, PBKDF2 salting, and automatic invalidation of all other active sessions.
- **Active Session Monitor**: View live cryptographic session tokens and revoke foreign sessions with a single click.

---

## Technology Stack

| Layer | Component | Notes |
|---|---|---|
| **Frontend** | HTML5, CSS3, JavaScript (ES6+) | Modern clinical SaaS design system, zero bloated heavy frameworks |
| **Styling** | Custom CSS + Bootstrap 5.3 | Responsive flexbox/grid layout, CSS custom properties |
| **Icons** | Bootstrap Icons 1.11 | Crisp clinical and administrative iconography |
| **Visualizations** | Chart.js 4.4 | Doughnut and analytics metrics |
| **Backend** | Python 3.9+, Flask 3.0+ | Modular Flask Blueprint architecture |
| **Security** | Werkzeug 3.0+ | PBKDF2-HMAC-SHA256 password hashing, CSPRNG token generation |
| **Database** | SQLite 3 | Full relational schema with cascading foreign keys (`PRAGMA foreign_keys = ON`) |
| **Testing** | Python `unittest` & `pytest` | 17-point automated verification suite |

---

## Installation & Quickstart

### Prerequisites
- Python 3.9, 3.10, 3.11, or 3.12
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/MediCore.git
cd MediCore
```

### 2. Set Up Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate on Windows:
.venv\Scripts\activate

# Activate on macOS/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
# Copy template configuration
cp .env.example .env
```
*(On Windows PowerShell, use `Copy-Item .env.example .env`)*. The default `.env` is pre-configured for immediate local evaluation.

### 5. Seed the Database
```bash
python database/seed.py
```
This initializes `database/medicore.db` from `database/schema.sql` and loads realistic Indian (Malayali) profiles, departments, clinical records, appointments, and billing invoices.

### 6. Run the Application
```bash
python run.py
```
Open your browser and navigate to **http://127.0.0.1:5000**.

---

## Pre-Configured Test Accounts

All pre-seeded test accounts share the password: **`Passw0rd!`**

| Role | Name | Email Address | Department / Title |
|---|---|---|---|
| **Administrator** | Ardhra | `admin@medicore.test` | System Administration &amp; Hospital Management |
| **Doctor** | Dr. Harikrishnan Nair | `dr.harikrishnan@medicore.test` | Interventional Cardiology |
| **Doctor** | Dr. Ananya Kurian | `dr.ananya@medicore.test` | Pediatric &amp; Neonatal Care |
| **Doctor** | Dr. Mathew Varghese | `dr.mathew@medicore.test` | Orthopedic Surgery &amp; Arthroscopy |
| **Doctor** | Dr. Fathima Beevi | `dr.fathima@medicore.test` | Clinical &amp; Aesthetic Dermatology |
| **Receptionist** | Sneha Menachery | `sneha.menachery@medicore.test` | Senior Front Desk Coordinator |
| **Receptionist** | Rahul Pillai | `rahul.pillai@medicore.test` | Clinical Pharmacist &amp; Intake Specialist |
| **Patient** | Eldho Paulose | `eldho.paulose@medicore.test` | Outpatient (#PT-0001) |
| **Patient** | Amina Shereen | `amina.shereen@medicore.test` | Outpatient (#PT-0002) |
| **Patient** | Karthik Namboodiri | `karthik.namboodiri@medicore.test` | Outpatient (#PT-0003) |
| **Patient** | Reshma Susan Cherian | `reshma.cherian@medicore.test` | Outpatient (#PT-0004) |
| **Patient** | Vinu Balakrishnan | `vinu.balakrishnan@medicore.test` | Outpatient (#PT-0005) |

*(The sign-in page also features one-click quick-fill buttons for instant evaluation of each role).*

---

## Screenshots

<p align="center">
  <em>(Replace the anchors below with real UI screenshots when preparing marketing releases)</em>
</p>

| View | Description |
|---|---|
| **Clinical Overview** | Live KPI metric cards, Chart.js caseload status, and upcoming appointments |
| **Patient Directory** | Filterable registry with blood group badges, contact info, and longitudinal history |
| **Medical Records (EMR)** | Clinical diagnoses, physical observations, and official electronic prescriptions |
| **Tax Invoice & Receipt** | GSTIN-ready medical invoices with line-item breakdown and printable layout |
| **Department Workloads** | Caseload distribution across Cardiology, Pediatrics, Orthopedics, and Dermatology |

---

## Security Lab (Educational Testing)

MediCore includes an isolated security lab containing **two intentionally vulnerable authentication mechanisms** designed specifically for authorized penetration-testing training and CTF practice:

1. **Weak Password Recovery (CWE-640, CWE-330)**:
   - *Location*: `security_lab/broken_password_recovery/` (`/lab/password-recovery`)
   - *Vulnerability*: Reset token is computed using a deterministic concatenation of the numeric user ID and UTC timestamp minute, with no secret randomness or server-side expiry enforcement.
2. **Insecure Session Management (CWE-384, CWE-330)**:
   - *Location*: `security_lab/insecure_session_management/` (`/lab/session-demo`)
   - *Vulnerability*: Session token is issued directly as the auto-increment integer primary key in a plain cookie lacking `HttpOnly` and `Secure` attributes, allowing session enumeration and fixation.

### Lab Guardrails
- **Host Restriction**: The vulnerable blueprints enforce a strict `before_request` hook rejecting any request whose `Host` header is not `localhost` or `127.0.0.1`.
- **Toggle Flag**: The lab is disabled by default. Set `SECURITY_LAB_ENABLED=1` in `.env` (or the environment) to register the blueprints.
- **Data Isolation**: The lab maintains its own separate tables (`vuln_reset_tokens`, `vuln_sessions`) and never shares state with the production authentication system.
- **CSRF**: Production forms use Flask-WTF CSRF protection by default; set `WTF_CSRF_ENABLED=0` only for local demos or isolated tests.

For step-by-step reproduction walkthroughs and remediation strategies, refer to [`docs/security_testing.md`](docs/security_testing.md).

---

## Running Automated Tests

MediCore includes an automated 17-point test suite covering public pages, contact form submissions, authentication flows, CRUD operations, CSV exports, account settings, and both security lab vulnerabilities.

Run with Python's standard library test runner:
```bash
python -m unittest tests/test_basic.py
```

Or with `pytest`:
```bash
pytest tests/
```

---

## Project Structure

```
MediCore/
├── app/
│   ├── auth/              # Production authentication routes & session helpers
│   ├── models/            # Database schema models & user queries
│   ├── routes/            # Feature modules (patients, doctors, appointments, ...)
│   ├── static/            # Brand SVG logos, CSS SaaS theme, client JS
│   └── templates/         # Modular Jinja2 template hierarchy
├── database/
│   ├── schema.sql         # 10 relational tables with foreign key cascades
│   └── seed.py            # Sample data generator (Indian/Malayali profiles)
├── docs/
│   ├── architecture.md    # Technical architecture & security specifications
│   └── security_testing.md# Security lab reproduction guide & mitigations
├── security_lab/          # Isolated intentionally vulnerable educational modules
├── tests/
│   └── test_basic.py      # Automated unittest & pytest suite
├── .env.example           # Environment template
├── .gitignore             # Comprehensive Git exclusion rules
├── LICENSE                # MIT License
├── README.md              # Project documentation
├── requirements.txt       # Dependencies
└── run.py                 # Local server entry point
```

---

## License

This project is licensed under the [MIT License](LICENSE).

---

*Disclaimer: All patient data, names, clinical diagnoses, and financial records in this repository are entirely fictional and generated for educational and portfolio demonstration purposes.*
