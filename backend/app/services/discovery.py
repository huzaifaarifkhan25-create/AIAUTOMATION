"""Single-worker pilot jobs. Never automatically import or retry a collection."""
import asyncio
import hashlib
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.errors import AppError
from app.models.workflow import now
from app.services.csv_import import import_csv
from collect_leads import collect


class Discovery:
    def __init__(self, store, root=None, collector=collect):
        self.store = store
        self.root = (root or Path(__file__).resolve().parents[3] / ".local/scrapes").resolve()
        self.collector = collector
        self.lock = asyncio.Lock()
        self.tasks = set()

    async def recover(self):
        for job in await self.store.list("discovery_jobs"):
            if job["status"] in {"queued", "running"}:
                job.update(status="interrupted", finished_at=now().isoformat(),
                           error="The service stopped during collection. Start a new pilot; partial output was not imported.")
                await self.store.put("discovery_jobs", job["id"], job)

    async def close(self):
        # The collector owns and cleans up its container, with a five-minute
        # browser timeout. Graceful shutdown waits instead of orphaning it.
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

    async def start(self, request):
        async with self.lock:
            if self.tasks:
                raise AppError(409, "discovery_busy", "A pilot is already running. Wait for its result before starting another.")
            job = {"id": str(uuid4()), "query": request.query, "limit": request.limit,
                   "status": "queued", "created_at": now().isoformat(),
                   "complete_directory": False}
            await self.store.put("discovery_jobs", job["id"], job)
            task = asyncio.create_task(self.run(job))
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
            return job

    async def require(self, job_id):
        job = await self.store.get("discovery_jobs", job_id)
        if not job:
            raise AppError(404, "not_found", "Discovery job was not found")
        return job

    def result(self, job):
        try:
            path = Path(job["result_path"]).resolve()
            if not path.is_relative_to(self.root) or path.name != "results.csv":
                raise ValueError()
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != job["sha256"]:
                raise ValueError()
            return data
        except (KeyError, OSError, ValueError):
            raise AppError(409, "discovery_output_unavailable", "The original CSV is missing or changed. Start a new pilot; this output cannot be imported.") from None

    async def run(self, job):
        try:
            job["status"] = "running"
            await self.store.put("discovery_jobs", job["id"], job)
            path = await asyncio.to_thread(self.collector, job["query"], self.root, job["limit"])
            manifest = json.loads(path.with_name("manifest.json").read_text())
            if (manifest.get("tls_verification") is not True or manifest.get("query") != job["query"]
                    or not isinstance(manifest.get("collected_count"), int)
                    or not 1 <= manifest["collected_count"] <= job["limit"]):
                raise ValueError("Invalid collection manifest")
            job.update(result_path=str(path), sha256=manifest["sha256"],
                       collected_count=manifest["collected_count"], collected_at=manifest["started_at"])
            self.result(job)
            # Validate before marking success, including the manifest date.
            preview = await import_csv(self.store, self.result(job), "csv", True,
                                       datetime.fromisoformat(manifest["started_at"]), "results.csv", {})
            if preview.total_rows != job["collected_count"] or not (preview.valid_rows or preview.duplicate_rows):
                raise ValueError("Invalid collection counts")
            job["status"] = "succeeded"
        except Exception:
            # Provider/process exception messages may contain credential values.
            job.update(status="failed", error="Live collection failed or produced invalid output. Check the collector prerequisites and network access, then start a new pilot. No leads were imported.")
        finally:
            job["finished_at"] = now().isoformat()
            await self.store.put("discovery_jobs", job["id"], job)

    async def preview_or_import(self, job_id, dry_run):
        job = await self.require(job_id)
        if job["status"] != "succeeded":
            raise AppError(409, "discovery_not_complete", "Only a successful pilot can be previewed or imported")
        return await import_csv(self.store, self.result(job), "csv", dry_run,
                                datetime.fromisoformat(job["collected_at"]), "results.csv", {})
