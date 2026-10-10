import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from app.database.store import SQLiteStore
from app.models.workflow import now
from app.services.discovery import Discovery
from backup import backup, restore, verify


class BackupTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "source.sqlite3"
        self.scrapes = self.root / "source-scrapes"
        self.store = SQLiteStore(str(self.db))
        await self.store.put("businesses", "synthetic", {"id": "synthetic", "source": "csv"})
        self.csv = self.scrapes / "fixture/results.csv"
        self.csv.parent.mkdir(parents=True)
        self.csv.write_bytes(b"name,address\nSynthetic backup fixture,Fixture address\n")
        self.job = {"id": "synthetic-job", "status": "succeeded", "created_at": now().isoformat(),
                    "result_path": str(self.csv), "sha256": hashlib.sha256(self.csv.read_bytes()).hexdigest()}
        await self.store.put("discovery_jobs", "synthetic-job", self.job)

    async def test_restored_database_and_artifacts_work_after_original_artifacts_are_removed(self):
        folder = backup(self.db, self.scrapes, self.root / "backups")
        shutil.rmtree(self.scrapes)
        recovered = restore(folder, self.root / "recovered")
        store = SQLiteStore(str(recovered / "backend.sqlite3"))
        self.assertEqual(await store.get("businesses", "synthetic"), {"id": "synthetic", "source": "csv"})
        job = await store.get("discovery_jobs", "synthetic-job")
        self.assertEqual(Discovery(store, recovered / "scrapes").result(job), b"name,address\nSynthetic backup fixture,Fixture address\n")
        self.assertEqual(await self.store.get("discovery_jobs", "synthetic-job"), self.job)

    async def test_portable_manifest_and_legacy_windows_names_restore(self):
        folder = backup(self.db, self.scrapes, self.root / "backups")
        manifest_path = folder / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        self.assertIn("scrapes/fixture/results.csv", manifest["files"])
        manifest["files"] = {name.replace("/", "\\"): digest for name, digest in manifest["files"].items()}
        manifest_path.write_text(json.dumps(manifest))
        shutil.rmtree(self.scrapes)
        recovered = restore(folder, self.root / "recovered")
        self.assertEqual((recovered / "scrapes/fixture/results.csv").read_bytes(),
                         b"name,address\nSynthetic backup fixture,Fixture address\n")

    async def test_changed_backup_is_rejected_before_creating_destination(self):
        folder = backup(self.db, self.scrapes, self.root / "backups")
        (folder / "scrapes/fixture/results.csv").write_bytes(b"changed")
        with self.assertRaises(ValueError):
            restore(folder, self.root / "recovered")
        self.assertFalse((self.root / "recovered").exists())

    async def test_restore_never_overwrites_existing_data(self):
        folder = backup(self.db, self.scrapes, self.root / "backups")
        protected = self.root / "existing"
        protected.mkdir()
        (protected / "keep.txt").write_text("Keep this existing file")
        with self.assertRaises(FileExistsError):
            restore(folder, protected)
        self.assertEqual((protected / "keep.txt").read_text(), "Keep this existing file")

    async def test_active_collection_and_recursive_backup_destination_are_rejected(self):
        await self.store.put("discovery_jobs", "active", {"id": "active", "status": "running"})
        with self.assertRaises(ValueError):
            backup(self.db, self.scrapes, self.root / "backups")
        self.assertEqual(list((self.root / "backups").iterdir()), [])
        with self.assertRaises(ValueError):
            backup(self.db, self.scrapes, self.scrapes / "backups")

    async def test_manifest_path_traversal_is_rejected_without_touching_existing_files(self):
        folder = backup(self.db, self.scrapes, self.root / "backups")
        manifest_path = folder / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        name = f"scrapes/../../{folder.name}/backend.sqlite3"
        manifest["files"][name] = manifest["files"]["backend.sqlite3"]
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            restore(folder, self.root / "recovered")
        self.assertFalse((self.root / "recovered").exists())


if __name__ == "__main__":
    unittest.main()
