"""Disposable HTTP fixture for frontend/scripts/auth-bridge-smoke.mjs.

Never run against user data. Records only header presence, never credentials.
"""
import os

if os.getenv("AUTH_BRIDGE_FIXTURE") != "true":
    raise RuntimeError("This module is only for an isolated auth bridge fixture")

from app.main import app

events = []


@app.middleware("http")
async def header_proof(request, call_next):
    if request.url.path == "/tasks" or request.url.path.endswith("/tasks"):
        events.append({
            "method": request.method,
            "path": request.url.path,
            "authorization_present": bool(request.headers.get("authorization")),
            "account_cookie_present": bool(request.cookies.get(app.state.accounts.cookie)),
            "csrf_present": bool(request.headers.get("x-workspace-csrf")),
        })
    return await call_next(request)


@app.get("/fixture/auth-header-proof")
async def proof():
    return events
