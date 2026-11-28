-- MediCore database schema (SQLite)
-- Fictional data only. Never load real patient information into this schema.

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS billing;
DROP TABLE IF EXISTS medical_records;
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS staff;
DROP TABLE IF EXISTS doctors;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS departments;
DROP TABLE IF EXISTS password_resets;
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name       TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('admin', 'doctor', 'receptionist', 'patient')),
    is_active       INTEGER NOT NULL DEFAULT 1,
    two_factor_enabled INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE departments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    description     TEXT
);

CREATE TABLE doctors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    department_id   INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    specialty       TEXT,
    phone           TEXT,
    availability    TEXT  -- free-text weekly availability summary
);

CREATE TABLE patients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    full_name       TEXT NOT NULL,
    date_of_birth   TEXT,
    gender          TEXT,
    phone           TEXT,
    address         TEXT,
    blood_group     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE staff (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    department_id   INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    job_title       TEXT,
    phone           TEXT
);

CREATE TABLE appointments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id       INTEGER NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    department_id   INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    scheduled_at    TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed')),
    reason          TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE medical_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id       INTEGER REFERENCES doctors(id) ON DELETE SET NULL,
    visit_date      TEXT NOT NULL DEFAULT (datetime('now')),
    diagnosis       TEXT,
    notes           TEXT,
    prescription    TEXT
);

CREATE TABLE billing (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    appointment_id  INTEGER REFERENCES appointments(id) ON DELETE SET NULL,
    amount          REAL NOT NULL,
    status          TEXT NOT NULL DEFAULT 'unpaid' CHECK (status IN ('unpaid', 'paid', 'overdue')),
    issued_at       TEXT NOT NULL DEFAULT (datetime('now')),
    paid_at         TEXT
);

-- ---------------------------------------------------------------------------
-- The two tables below back the SECURE authentication path. The vulnerable
-- lab mechanisms (security_lab/) use their OWN separate tables
-- (vuln_reset_tokens, vuln_sessions) created in security_lab/schema.sql so
-- that the intentionally-broken logic never touches real auth data.
-- ---------------------------------------------------------------------------

CREATE TABLE sessions (
    id              TEXT PRIMARY KEY,          -- cryptographically random token (secure path)
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at      TEXT NOT NULL,
    revoked         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE password_resets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      TEXT NOT NULL,             -- secure path stores only a hash of a random token
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at      TEXT NOT NULL,
    used            INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE otp_codes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    otp_code        TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at      TEXT NOT NULL,
    used            INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_appointments_patient ON appointments(patient_id);
CREATE INDEX idx_appointments_doctor ON appointments(doctor_id);
CREATE INDEX idx_medical_records_patient ON medical_records(patient_id);
CREATE INDEX idx_billing_patient ON billing(patient_id);
