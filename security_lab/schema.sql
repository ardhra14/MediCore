-- Isolated lab tables. These are only created for the intentional security lab.
DROP TABLE IF EXISTS vuln_reset_tokens;
DROP TABLE IF EXISTS vuln_sessions;

CREATE TABLE vuln_reset_tokens (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    used       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE vuln_sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL
);

CREATE TABLE vuln_2fa_codes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    otp_code   TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL
);