# MediCore Security Lab — Testing Guide

> **Scope.** This lab is for authorized, educational penetration-testing
> practice against your own local instance only. Both vulnerabilities are
> confined to isolated Flask blueprints under `security_lab/`, are gated
> behind `SECURITY_LAB_ENABLED` in `config.py`, and additionally refuse any
> request whose `Host` header is not `localhost` / `127.0.0.1`. Never deploy
> this lab to a shared or public network, and never point it at real
> accounts or real patient data.

## Setup

```bash
python database/seed.py     # fictional test accounts, password: Passw0rd!
python run.py                # serves on http://127.0.0.1:5000
```

Test accounts created by `seed.py` (all share the password `Passw0rd!`):

| Role         | Email                          | Name                  |
|--------------|--------------------------------|-----------------------|
| admin        | admin@medicore.test            | Ardhra                |
| doctor       | dr.harikrishnan@medicore.test  | Dr. Harikrishnan Nair |
| receptionist | sneha.menachery@medicore.test  | Sneha Menachery       |
| patient      | eldho.paulose@medicore.test    | Eldho Paulose         |

---

## Vulnerability 1 — Weak Password Recovery (CWE-640, CWE-330)

**Location:** `security_lab/broken_password_recovery/`

### What's broken
The reset "token" is `generate_predictable_token(user_id, now)` in
`routes.py`: a 2-digit zero-padded user ID concatenated with a 4-digit
minute-of-day (UTC). There is no random secret component, so anyone who
knows (or enumerates) a target's user ID can compute every valid token for
the current minute without ever seeing an email. The lookup also never
checks expiry or the `used` flag, so a computed token keeps working.

### Reproduction steps
1. Go to `http://127.0.0.1:5000/lab/password-recovery/forgot-password`.
2. Submit `eldho.paulose@medicore.test` (patient test account, user id `8`
   in the seeded database — visible in the demo banner for teaching
   purposes).
3. Instead of using the token shown in the demo banner, compute it
   independently: `f"{8 % 100:02d}{hour*60+minute:04d}"` using the current
   UTC time, e.g. `081083`.
4. Browse to `/lab/password-recovery/reset/081083` and set a new password.

### Expected outcome
The password is reset using only the victim's user ID and the current
time — no access to the victim's inbox or credentials was required.

### Impact
Full account takeover for any user whose ID is known or guessable, with no
interaction from the victim.

### Recommended fix
Use the pattern already in `app/auth/routes.py`: `secrets.token_urlsafe(32)`
tokens, store only a SHA-256 hash, 15-minute expiry, single-use enforcement,
rate limiting, and a response that doesn't reveal whether the email exists.

---

## Vulnerability 2 — Insecure Session Management (CWE-384, CWE-330)

**Location:** `security_lab/insecure_session_management/`

### What's broken
`create_vuln_session()` issues the session's own `AUTOINCREMENT` primary
key as the session token — a small, sequential, guessable integer — and
sets it in a cookie with no `HttpOnly`, `Secure`, or `SameSite` attributes.
Sessions never expire, aren't rotated on login, and logout only revokes the
one session row, leaving any other captured session tokens for that user
valid.

### Reproduction steps
1. In Browser A, go to `/lab/session-demo/login` and sign in as
   `eldho.paulose@medicore.test` / `Passw0rd!`. Note the `lab_session`
   cookie value shown in the flash message, e.g. `lab_session=3`.
2. In Browser B (a separate/incognito session, or `curl --cookie`), set the
   cookie `lab_session=3` manually and request
   `/lab/session-demo/whoami`.
3. Observe Browser B is now treated as the authenticated user, with no
   credentials entered.
4. Try adjacent integers (`1`, `2`, `4`, `5`, …) against `/whoami` to show
   other live sessions can be found by guessing alone.

### Expected outcome
An attacker who observes or guesses a small integer gains the session of
another authenticated user.

### Impact
Session hijacking / unauthorized access to any active account without
credentials.

### Recommended fix
Use the pattern already in `app/auth/utils.py`: `secrets.token_urlsafe(32)`
session tokens, `HttpOnly` + `SameSite` + `Secure` cookies, a checked
expiry column, session rotation on every login, and revocation of **all**
sessions for a user on logout or password change.

---

## Vulnerability 3 — Two-Factor Authentication (2FA) Bypass (CWE-304, CWE-287)

**Location:** `security_lab/vulnerable_2fa/` (`/lab/2fa`)

### What's broken
The secondary OTP verification endpoint accepts multiple bypass mechanisms:
1. **Header-based bypass**: Sending `X-Bypass-2FA: true` skips the OTP verification step completely.
2. **Master magic code**: Submitting `000000` or `888888` is unconditionally treated as valid.
3. **Parameter tampering / Step-skipping**: Appending `?skip_2fa=1` bypasses the check.

### Reproduction steps
1. Sign in via `/lab/2fa/login` with any lab account (e.g. `eldho.paulose@medicore.test` / `Passw0rd!`).
2. On `/lab/2fa/verify`, enter OTP `000000` or send header `X-Bypass-2FA: true`.
3. Observe full access granted to `/lab/2fa/portal` without entering the target user's OTP.

### Recommended fix
Verify OTP cryptographically against server-side session state, bind single-use tokens to verified credentials, and reject all unrecognized bypass headers and magic codes.

---

## Vulnerability 4 — Rate Limit Bypass & Missing Rate Limiting (CWE-307)

**Location:** `security_lab/rate_limit_bypass/` (`/lab/rate-limit`)

### What's broken
1. `/lab/rate-limit/verify-otp-vulnerable`: Completely lacks rate limiting, allowing rapid automated brute-force attacks against the 4-digit PIN (`4281`).
2. `/lab/rate-limit/verify-otp-header-bypass`: Enforces rate limits using the untrusted, client-supplied `X-Forwarded-For` header. Rotating the IP bypasses lockout counters.

### Reproduction steps
1. Send rapid requests to `/lab/rate-limit/verify-otp-vulnerable` with a script or Burp Intruder. Observe no 429 lockout occurs.
2. Send 5 failed requests to `/lab/rate-limit/verify-otp-header-bypass` with `X-Forwarded-For: 10.0.0.1`, then change to `X-Forwarded-For: 10.0.0.2` to bypass the 429 lockout.

### Recommended fix
Enforce server-side rate limiting on all authentication and OTP endpoints using real remote socket addresses, progressive delays, and account lockouts.

---

## Vulnerability 5 — JWT Signature Bypass & Privilege Escalation (CWE-347, CWE-345)

**Location:** `security_lab/jwt_vulnerabilities/` (`/lab/jwt`)

### What's broken
The JWT validator accepts tokens signed with `alg: "none"` and skips cryptographic signature validation entirely. A regular patient can decode their token, alter `"isAdmin": false` to `"isAdmin": true`, set `"alg": "none"`, and submit the token to gain full administrative access to `/lab/jwt/admin`.

### Reproduction steps
1. Sign in via `/lab/jwt/login` as patient `eldho.paulose@medicore.test`.
2. Access `/lab/jwt/admin` and receive HTTP 403 Forbidden.
3. Use the Forge tool (or a script) to generate a token with header `{"typ": "JWT", "alg": "none"}` and payload `{"sub": 8, "name": "Eldho Paulose", "role": "admin", "isAdmin": true}`.
4. Submit the forged token to `/lab/jwt/admin` via `Authorization: Bearer <token>`.
5. Observe HTTP 200 OK and exposure of sensitive clinical administration telemetry.

### Recommended fix
Strictly whitelist allowed cryptographic algorithms (e.g. HS256 / RS256), reject tokens with `alg: "none"`, and verify cryptographic signatures before decoding or trusting claims.

---

## Vulnerability 6 — Technical Information Disclosure (CWE-200, CWE-209)

**Location:** `security_lab/information_disclosure/` (`/lab/info-disclosure`)

### What's broken
An exposed diagnostic route (`/lab/info-disclosure/diagnostics`) reveals internal filesystem paths, Python interpreter paths, session configuration attributes, database table schemas, record counts, and the internal Flask routing map.

### Reproduction steps
1. Navigate to `/lab/info-disclosure/diagnostics` (or fetch with `?format=json`).
2. Observe disclosure of server paths, operating system details, database internals, and routing maps.

### Recommended fix
Disable diagnostic endpoints in production, restrict administrative telemetry behind internal network boundaries, and ensure error handlers mask technical traces.

---

## Disabling the lab

Set `SECURITY_LAB_ENABLED=0` (the default) in `.env` or the environment to prevent all vulnerable blueprints from being registered at all — `create_app()` skips importing and mounting them entirely in that case.
