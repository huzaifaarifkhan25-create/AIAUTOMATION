import asyncio
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from app.errors import AppError

KINDS = {"businesses", "analyses", "workflows", "contacts", "calls", "discovery_jobs", "workflow_runs", "workflow_outbox", "delivery_events", "workflow_permissions", "appointments", "activities", "tasks", "clients", "deployments", "deployment_events", "call_events", "ai_insights"}


class SQLiteStore:
    def __init__(self, path: str):
        self.path = path
        self.business_lock = asyncio.Lock()

    def _operation(self, action, kind, record_id=None, payload=None):
        if kind not in KINDS:
            raise ValueError("Unknown record kind")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=10)) as connection, connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS backend_records "
                "(kind TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(kind,id))"
            )
            if action == "put":
                connection.execute(
                    "INSERT INTO backend_records(kind,id,payload) VALUES(?,?,?) "
                    "ON CONFLICT(kind,id) DO UPDATE SET payload=excluded.payload",
                    (kind, record_id, json.dumps(payload)),
                )
                return payload
            if action == "reserve":
                cursor = connection.execute(
                    "INSERT OR IGNORE INTO backend_records(kind,id,payload) VALUES(?,?,?)",
                    (kind, record_id, json.dumps(payload)),
                )
                return cursor.rowcount == 1
            if action == "get":
                row = connection.execute(
                    "SELECT payload FROM backend_records WHERE kind=? AND id=?", (kind, record_id)
                ).fetchone()
                return json.loads(row[0]) if row else None
            rows = connection.execute(
                "SELECT payload FROM backend_records WHERE kind=? ORDER BY id", (kind,)
            ).fetchall()
            return [json.loads(row[0]) for row in rows]

    async def _run(self, *args):
        try:
            return await asyncio.to_thread(self._operation, *args)
        except (sqlite3.Error, OSError):
            raise AppError(503, "storage_unavailable", "Local database is unavailable") from None

    async def put(self, kind, record_id, payload):
        return await self._run("put", kind, record_id, payload)

    async def get(self, kind, record_id):
        return await self._run("get", kind, record_id)

    async def list(self, kind):
        return await self._run("list", kind)

    async def reserve(self, kind, record_id, payload):
        return await self._run("reserve", kind, record_id, payload)

    async def put_many(self, records):
        """Commit related local changes and their audit entries in one transaction."""
        def commit():
            if any(kind not in KINDS for kind, _, _ in records):
                raise ValueError("Unknown record kind")
            with closing(sqlite3.connect(self.path, timeout=10)) as connection, connection:
                connection.executemany(
                    "INSERT INTO backend_records(kind,id,payload) VALUES(?,?,?) "
                    "ON CONFLICT(kind,id) DO UPDATE SET payload=excluded.payload",
                    [(kind, key, json.dumps(payload)) for kind, key, payload in records],
                )
        try:
            await asyncio.to_thread(commit)
        except (sqlite3.Error, OSError):
            raise AppError(503, "storage_unavailable", "Local database is unavailable") from None


class SupabaseStore:
    def __init__(self, settings, gateway):
        self.settings = settings
        self.gateway = gateway
        self.business_lock = asyncio.Lock()

    @staticmethod
    def _records(result):
        if not isinstance(result, list) or any(
            not isinstance(item, dict) or not isinstance(item.get("payload"), dict)
            for item in result
        ):
            raise AppError(502, "storage_invalid_response", "Supabase returned an invalid response")
        return result

    async def _request(self, method, **kwargs):
        url = self.settings.supabase_url
        parsed = urlsplit(url)
        if not url or not self.settings.supabase_key:
            raise AppError(503, "supabase_not_configured", "Set SUPABASE_URL and SUPABASE_KEY in environment settings")
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise AppError(503, "supabase_invalid_url", "SUPABASE_URL must be a trusted HTTPS project URL")
        return await self.gateway.json_request(
            method, url.rstrip("/") + "/rest/v1/backend_records",
            headers={"apikey": self.settings.supabase_key,
                     "Authorization": f"Bearer {self.settings.supabase_key}",
                     "Prefer": "resolution=merge-duplicates,return=representation"},
            **kwargs,
        )

    async def put(self, kind, record_id, payload):
        result = await self._request("POST", params={"on_conflict": "kind,id"},
                                     json={"kind": kind, "id": record_id, "payload": payload})
        result = self._records(result)
        if not result:
            raise AppError(502, "storage_invalid_response", "Supabase returned an invalid response")
        return result[0]["payload"]

    async def get(self, kind, record_id):
        result = await self._request("GET", params={"kind": f"eq.{kind}", "id": f"eq.{record_id}", "select": "payload", "limit": "1"})
        result = self._records(result)
        return result[0]["payload"] if result else None

    async def list(self, kind):
        records = []
        offset = 0
        limit = 50
        while True:
            try:
                result = await self._request("GET", params={"kind": f"eq.{kind}", "select": "payload", "order": "id.asc", "offset": str(offset), "limit": str(limit)})
            except AppError as error:
                if error.code != "response_too_large" or limit == 1:
                    raise
                limit = max(1, limit // 2)
                continue
            result = self._records(result)
            records.extend(item["payload"] for item in result)
            if len(result) < limit:
                return records
            offset += len(result)

    async def reserve(self, kind, record_id, payload):
        # A conflicting primary key must never trigger a second external call.
        if not self.settings.supabase_url or not self.settings.supabase_key:
            raise AppError(503, "supabase_not_configured", "Configure Supabase before calling")
        parsed = urlsplit(self.settings.supabase_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise AppError(503, "supabase_invalid_url", "SUPABASE_URL must be a trusted HTTPS project URL")
        response = await self.gateway.request(
            "POST", self.settings.supabase_url.rstrip("/") + "/rest/v1/backend_records",
            accepted_statuses=(409,),
            headers={"apikey": self.settings.supabase_key,
                     "Authorization": f"Bearer {self.settings.supabase_key}"},
            json={"kind": kind, "id": record_id, "payload": payload},
        )
        return response.status_code != 409
