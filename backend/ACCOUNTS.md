# Individual accounts in the shared workspace

Accounts use SQLite and work through the purple Next.js interface and backend
auth APIs. The older `/app/` fallback retains its shared-token access form.
Each operator has a separate email,
password and revocable session; all operators see the same leads, tasks and
automations. Company tenants, roles, email verification and password recovery
are not implemented.

No external API key is needed for accounts. In production set a strong
`APP_API_TOKEN` as instructed by the deployment guide. Registration requires
the operator to enter that workspace invitation code. Development without a
token permits registration only through a loopback backend connection. Hosted
operation must use production mode, HTTPS and the invitation code.

Passwords must contain 12–128 characters. The server stores independent random
salts and PBKDF2-SHA256 hashes with 600,000 iterations. Raw passwords and session
tokens are not saved. Sessions last 12 hours, survive process restarts, rotate
on sign-in, and are revoked on logout. Restoring a backup retains accounts but
revokes restored sessions so operators sign in again.

The browser receives an HttpOnly, SameSite=Strict account cookie (`aia_session`
in development, `__Host-aia_session` with Secure in production). Changes made
with that cookie also need the server-issued `X-Workspace-CSRF` value and a
permitted origin. Persistent login/registration throttles limit repeated
attempts. The app validates sign-in data without echoing passwords or codes.

## Purple interface bridge

`BACKEND_URL` must be the backend's HTTP(S) origin, without credentials, paths,
queries or fragments. Next.js checks the browser's origin before forwarding
auth requests. It relays the backend's account cookie and verifies the actual
session with `/auth/me`. For workspace changes it forwards that cookie and a
freshly fetched CSRF token, rather than replacing the operator with a shared
bearer token. Account sessions remain active after a reload.

The old access-code pilot remains optional when `DEMO_ACCESS_CODE`,
`FRONTEND_SESSION_SECRET` and `APP_API_TOKEN` are configured. It uses a separate
`preview_session` cookie and continues locking on a document reload. Only this
explicit legacy session uses the server's shared bearer. Its access code is
distinct from individual sign-in and does not create an account.

Backend APIs: `GET /auth/status`, `POST /auth/register`, `POST /auth/login`,
`GET /auth/me`, `POST /auth/logout`. Next.js exposes the matching controlled
`/api/auth/{action}` paths. Registration also requires literal
`confirm_shared_workspace: true`; successful registration/login return `user`,
`csrf_token` and `workspace: "shared"`.

SQLite is required for individual accounts. Supabase account requests explicitly
report unsupported storage and do not silently switch databases.

## Verification

`backend/tests/test_auth.py` checks password/token hashing, invitation and
confirmation guards, session persistence/expiry/rotation/revocation, CSRF and
origin rejection, durable throttling, backup recovery, protected newer routes,
and SQLite-only behavior using disposable fictional data.

`frontend/scripts/auth-bridge-smoke.mjs` is an HTTP integration check for isolated
servers. It requires `AUTH_BRIDGE_FIXTURE=true`. With
`AUTH_TEST_HEADER_PROOF=true`, run the backend test-only
`backend/tests/auth_bridge_fixture.py` app. That fixture records header presence
only, so the check can establish that account writes forward a cookie and CSRF
without the owner bearer. Never start this fixture against a user's database.
