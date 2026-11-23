# Contributing to MediCore Healthcare Systems

Thank you for your interest in contributing to MediCore! This guide outlines how to contribute safely and effectively to this clinical hospital operating system and educational cybersecurity lab.

---

## 1. Code of Conduct & Ethics

- **No Real Patient Data:** MediCore is configured strictly with fictional evaluation records. Never commit real patient health information (PHI), real credentials, API keys, or private database files.
- **Security Lab Integrity:** MediCore includes an isolated security lab (`security_lab/`) containing intentionally vulnerable authentication blueprints for local educational and penetration-testing training. **Do not remove or modify these vulnerable mechanisms in the lab**, as they are deliberate educational contrast exercises.
- **Local Scope:** The security lab is strictly restricted to `localhost` / `127.0.0.1` and disabled by default (`SECURITY_LAB_ENABLED=0`).

---

## 2. Getting Started

### Prerequisites
- Python 3.9+ (Python 3.10 or 3.11 recommended)
- Git
- SQLite 3

### Clone & Setup

```bash
# Clone the repository
git clone https://github.com/ardhra14/MediCore.git
cd MediCore

# Create and activate virtual environment
# Windows:
python -m venv .venv
.\.venv\Scripts\activate

# Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Initialize and seed the database with realistic sample data
python database/seed.py

# Run the development server
python run.py
```

The application will be accessible at: `http://127.0.0.1:5000`

---

## 3. Development Guidelines

1. **Coding Style:**
   - Adhere to PEP 8 standards.
   - Use clear, descriptive variable and function names.
   - Keep views modular within blueprints under `app/routes/`.
2. **Database Changes:**
   - Modify `database/schema.sql` for schema changes.
   - Update `database/seed.py` to maintain consistent sample data.
3. **Role-Based Access Control (RBAC):**
   - Every protected route must use `@login_required` and `@roles_required(...)`.
   - Never rely exclusively on client-side UI hides; enforce permissions server-side.
4. **Testing:**
   - Run the automated test suite before opening a pull request:
     ```bash
     python -m unittest tests/test_basic.py
     ```
   - Ensure all tests pass (`OK`).

---

## 4. Submitting a Pull Request

1. Fork the repository and create your feature branch from `main`:
   ```bash
   git checkout -b feature/my-new-feature
   ```
2. Commit your changes with clear, imperative commit messages:
   ```bash
   git commit -m "Add: support for multi-specialty triage filters"
   ```
3. Push to your branch and open a Pull Request against `main`.
4. Describe your changes, testing steps, and relevant issue numbers.

---

## 5. Security Vulnerability Reporting

If you discover an unintentional security vulnerability in the production application paths (`app/auth/`, `app/routes/`, `app/models/`), please report it privately to the maintainers rather than opening a public issue.
