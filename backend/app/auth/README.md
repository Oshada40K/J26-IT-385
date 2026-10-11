# CareerNova account authentication

The React dashboard requires a verified `/api/auth/me` session. Registration
redirects to login. Login creates a signed JWT in an HttpOnly cookie; it is never
returned to JavaScript or stored in localStorage. Passwords use Argon2id through
argon2-cffi. JWT signatures, issuer, audience and expiration are verified with
PyJWT, and every request also checks a revocable database session. Logout deletes
that session and cookie. Remember me extends expiration from 8 hours to 30 days
and makes the cookie persistent. The browser checks sessions on focus, at expiry
and every minute, and synchronizes account changes across tabs.

## Setup

Install `backend/requirements.txt`. Copy the authentication variables from
`backend/.env.example` into your ignored `backend/.env`. Generate a unique secret:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set `AUTH_SECRET_KEY` to that value (at least 32 bytes). Missing configuration
returns 503 for auth operations; research APIs can still start. Keep the secret
stable across restarts/replicas. Changing it signs everyone out.

For development, set `AUTH_COOKIE_SECURE=false`, use frontend
`http://localhost:5173`, backend `http://localhost:8000`, and set frontend
`VITE_API_BASE_URL=http://localhost:8000`. Restart Vite after changing its env.
Use the same hostname on both services (both localhost or both 127.0.0.1).

Production requires HTTPS, `AUTH_COOKIE_SECURE=true`, explicit frontend origins
in `AUTH_ALLOWED_ORIGINS` (comma-separated, no wildcard), and a persistent
`AUTH_DATABASE_PATH` such as `/data/auth.sqlite3` on a Railway volume. This SQLite
implementation is intended for a single backend deployment/replica; use a shared
database before scaling horizontally. Back up the volume. If frontend and API
are cross-site, use `AUTH_COOKIE_SAMESITE=none`; browsers may still block third-party
cookies. Same-site custom domains or a same-origin reverse proxy are preferred.
Never deploy with development cookie settings. The frontend does not bypass login
if cookies are rejected.

All mutation requests require an `Origin` matching `AUTH_ALLOWED_ORIGINS`, including
non-browser API clients. Auth responses cannot be cached. CORS allows credentials
only from that origin list; include every legitimate dashboard origin when
deploying. Request throttling is stored in SQLite (30 attempts per action/IP and,
where relevant, 10 per action/email, per 15 minutes). Proxy client-address handling
must trust only your own reverse proxy; do not expose Uvicorn with arbitrary
forwarded headers trusted.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/auth/register` | `{full_name,email,password}`; create account (201) |
| POST | `/api/auth/login` | `{email,password,remember_me}`; set session cookie |
| GET | `/api/auth/me` | Validate cookie and return `{user,expires_at}` |
| POST | `/api/auth/logout` | Revoke session and clear cookie (204) |
| POST | `/api/auth/forgot-password` | `{email}`; request reset email |
| POST | `/api/auth/reset-password` | `{token,password}`; single-use reset |

Configure `AUTH_SMTP_HOST`, `AUTH_SMTP_PORT` (default 587), `AUTH_SMTP_FROM`,
`AUTH_SMTP_USERNAME`, `AUTH_SMTP_PASSWORD`, and `AUTH_FRONTEND_URL` to enable password
reset email. SMTP uses STARTTLS. Without mail configuration, the UI explains that
reset email is unavailable. Reset requests otherwise return a generic response
for both existing and unknown emails. Tokens are random, stored only as SHA-256
hashes, expire after 30 minutes, and invalidate all sessions on successful use.
The email URL carries the token in its fragment so it is not sent in page requests.

Existing Component 01–04 API contracts and authorization stay as they are; the
new account cookie does not replace Component 1's candidate bearer token. Dashboard
navigation is protected by the new account session. Its account identity and the
prototype CV candidate identity are separate; logout/account changes clear the
current tab's candidate credential to prevent showing a prior user's CV. Linking
saved candidate histories to accounts is outside this change.

## Verification

```powershell
cd backend
python -m unittest discover -s tests -v
cd ../frontend
npm run build
```

Optional browser verification uses the existing Python Playwright installation:

```powershell
cd frontend
python tests/auth_browser.py http://127.0.0.1:5175
```

Point this at a frontend connected to a disposable local authentication database;
it creates randomized test accounts and expects SMTP to be unconfigured. It checks
desktop/mobile forms, registration, login, persistent cookies, protected routes,
reloads, logout across tabs, and CV-credential cleanup. Screenshots are written to
the ignored `backend/.data/auth-qa/` directory.

Implementation references: [FastAPI security](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/),
[PyJWT validation](https://pyjwt.readthedocs.io/en/latest/usage.html),
[argon2-cffi password hashing](https://argon2-cffi.readthedocs.io/en/stable/api.html).
