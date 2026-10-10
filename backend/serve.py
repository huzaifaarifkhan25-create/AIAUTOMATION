"""Portable single-worker container entrypoint; hosting TLS lives at the ingress."""
import os
import sys
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == "__main__":
    if os.getenv("APP_ENV") != "production":
        raise SystemExit("Container entrypoint requires APP_ENV=production; use the loopback launcher for development")
    value = os.getenv("PORT", "8000")
    if not value.isascii() or not value.isdigit() or not 1 <= int(value) <= 65535:
        raise SystemExit("PORT must be an integer from 1 to 65535")
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(value), workers=1, proxy_headers=False)
