"""Individual operator accounts for one shared SQLite workspace."""
import asyncio
import hashlib
import hmac
import ipaddress
import secrets
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from app.database.store import SQLiteStore
from app.errors import AppError

ITERATIONS = 600_000
SESSION_SECONDS = 12 * 60 * 60


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS).hex()


class Accounts:
    def __init__(self, settings, store):
        self.settings = settings
        self.supported = isinstance(store, SQLiteStore)
        self.path = store.path if self.supported else None
        self.cookie = "__Host-aia_session" if settings.app_env == "production" else "aia_session"
        self.lock = asyncio.Lock()

    def _db(self, action):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS auth_users (id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, name TEXT NOT NULL, salt TEXT NOT NULL, password_hash TEXT NOT NULL, created_at INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS auth_sessions (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS auth_limits (identity TEXT PRIMARY KEY, attempts INTEGER NOT NULL, window_start INTEGER NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS auth_session_expiry ON auth_sessions(expires_at)")
            db.execute("BEGIN IMMEDIATE")
            return action(db)

    async def run(self, action):
        if not self.supported:
            raise AppError(503, "accounts_storage_unsupported", "Individual accounts currently require SQLite")
        try:
            return await asyncio.to_thread(self._db, action)
        except (sqlite3.Error, OSError):
            raise AppError(503, "accounts_storage_unavailable", "Account storage is unavailable") from None

    def registration_allowed(self, request):
        if self.settings.app_api_token:
            return True
        try:
            return self.settings.app_env == "development" and ipaddress.ip_address(request.client.host).is_loopback
        except (AttributeError, ValueError):
            return False

    async def status(self, request):
        count = await self.run(lambda db: db.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0]) if self.supported else 0
        return {"supported": self.supported, "has_accounts": count > 0,
                "registration_available": self.supported and self.registration_allowed(request),
                "access_code_required": bool(self.settings.app_api_token),
                "workspace": "shared", "session_hours": SESSION_SECONDS // 3600}

    async def has_accounts(self):
        return self.supported and await self.run(lambda db: bool(db.execute("SELECT 1 FROM auth_users LIMIT 1").fetchone()))

    async def throttle(self, request, email):
        host = request.client.host if request.client else "unknown"
        now = int(time.time())
        def reserve(db):
            db.execute("DELETE FROM auth_limits WHERE window_start <= ?", (now - 900,))
            for value, maximum in [("ip:" + host, 30), ("email:" + email, 10)]:
                identity = digest(value)
                row = db.execute("SELECT attempts FROM auth_limits WHERE identity=?", (identity,)).fetchone()
                if row and row[0] >= maximum:
                    return False
            for value in ("ip:" + host, "email:" + email):
                db.execute("INSERT INTO auth_limits VALUES(?,1,?) ON CONFLICT(identity) DO UPDATE SET attempts=attempts+1", (digest(value), now))
            return True
        if not await self.run(reserve):
            raise AppError(429, "auth_rate_limited", "Too many attempts. Try again in 15 minutes")

    @staticmethod
    def user(row):
        return {"id": row[0], "email": row[1], "name": row[2]}

    async def register(self, request, body):
        if not self.registration_allowed(request):
            raise AppError(403, "registration_closed", "Local registration requires a loopback connection; configure a workspace access code for remote access")
        async with self.lock:
            await self.throttle(request, body.email)
            expected = self.settings.app_api_token
            if expected and not hmac.compare_digest(body.access_code.encode(), expected.encode()):
                raise AppError(403, "invalid_access_code", "A valid workspace access code is required to register")
            salt = secrets.token_hex(16)
            hashed = await asyncio.to_thread(password_hash, body.password, salt)
            identifier, now = str(uuid4()), int(time.time())
            def insert(db):
                if db.execute("SELECT 1 FROM auth_users WHERE email=?", (body.email,)).fetchone():
                    raise AppError(409, "account_exists", "An account already uses this email. Sign in instead")
                db.execute("INSERT INTO auth_users VALUES(?,?,?,?,?,?)", (identifier, body.email, body.name, salt, hashed, now))
                return {"id": identifier, "email": body.email, "name": body.name}
            user = await self.run(insert)
            return await self.issue(user, request.cookies.get(self.cookie))

    async def login(self, request, body):
        async with self.lock:
            await self.throttle(request, body.email)
            row = await self.run(lambda db: db.execute("SELECT id,email,name,salt,password_hash FROM auth_users WHERE email=?", (body.email,)).fetchone())
            # Missing users still perform the same work; responses disclose no account existence.
            hashed = await asyncio.to_thread(password_hash, body.password, row[3] if row else "00" * 16)
            if not row or not hmac.compare_digest(hashed, row[4]):
                raise AppError(401, "invalid_credentials", "Email or password is incorrect")
            return await self.issue(self.user(row), request.cookies.get(self.cookie))

    async def issue(self, user, old_token=None):
        token, now = secrets.token_urlsafe(32), int(time.time())
        def insert(db):
            db.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (now,))
            if old_token:
                db.execute("DELETE FROM auth_sessions WHERE token_hash=?", (digest(old_token),))
            db.execute("INSERT INTO auth_sessions VALUES(?,?,?)", (digest(token), user["id"], now + SESSION_SECONDS))
            # Bound active sessions per operator without removing the new one.
            db.execute("DELETE FROM auth_sessions WHERE user_id=? AND token_hash NOT IN (SELECT token_hash FROM auth_sessions WHERE user_id=? ORDER BY expires_at DESC, rowid DESC LIMIT 10)", (user["id"], user["id"]))
        await self.run(insert)
        return user, token

    async def session(self, request, required=True):
        token = request.cookies.get(self.cookie)
        row = None
        if token and len(token) <= 128 and self.supported:
            row = await self.run(lambda db: db.execute("SELECT u.id,u.email,u.name FROM auth_sessions s JOIN auth_users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?", (digest(token), int(time.time()))).fetchone())
        if not row:
            if required:
                raise AppError(401, "sign_in_required", "Sign in to access the workspace")
            return None
        request.state.user = self.user(row)
        return {"user": request.state.user, "csrf_token": digest(token + ":csrf")}

    async def authorize_cookie(self, request):
        session = await self.session(request)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            expected = session["csrf_token"]
            if not hmac.compare_digest(request.headers.get("x-workspace-csrf", "").encode(), expected.encode()):
                raise AppError(403, "csrf_required", "Refresh the page before changing workspace data")
        return session

    async def logout(self, request):
        token = request.cookies.get(self.cookie)
        if token:
            session = await self.session(request, required=False)
            if session:
                await self.authorize_cookie(request)
            await self.run(lambda db: db.execute("DELETE FROM auth_sessions WHERE token_hash=?", (digest(token),)))
