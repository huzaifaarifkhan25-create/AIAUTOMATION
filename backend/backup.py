"""SQLite and scraper-artifact backup/recovery; restoration never overwrites data."""
import argparse
import hashlib
import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path, PurePosixPath
from uuid import uuid4


def checksum(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def database(path):
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def manifest_path(name):
    # Older Windows backups used backslashes; new manifests use portable names.
    if not isinstance(name, str) or not name or "\x00" in name:
        raise ValueError("Backup file name is invalid")
    relative = PurePosixPath(name.replace("\\", "/"))
    if (relative.is_absolute() or not relative.parts or ".." in relative.parts
            or ":" in relative.parts[0]):
        raise ValueError("Backup file name is outside the backup")
    return Path(*relative.parts)


def verify(folder):
    manifest = json.loads((folder / "manifest.json").read_text())
    if manifest.get("format") != "aiautomation-backup-v1":
        raise ValueError("Unsupported backup format")
    for name, digest in manifest["files"].items():
        relative = manifest_path(name)
        path = folder / relative
        if path.is_symlink() or not path.resolve().is_relative_to(folder.resolve()) or checksum(path) != digest:
            raise ValueError("Backup file is missing, changed, or outside the backup")
    if "backend.sqlite3" not in manifest["files"]:
        raise ValueError("Backup database is missing")
    with closing(database(folder / "backend.sqlite3")) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise ValueError("Backup database integrity check failed")
    return manifest


def backup(db_path, scrape_root, output_root):
    scrape_root = scrape_root.resolve()
    if output_root.resolve().is_relative_to(scrape_root):
        raise ValueError("Store backups outside the scraper artifact directory")
    output_root.mkdir(parents=True, exist_ok=True)
    folder = output_root / ("backup-" + uuid4().hex[:12])
    folder.mkdir(mode=0o700)
    try:
        with closing(database(db_path)) as source, closing(sqlite3.connect(folder / "backend.sqlite3")) as target:
            # The SQLite backup API includes committed WAL data consistently.
            source.backup(target)
            jobs = [json.loads(row[0]) for row in target.execute("SELECT payload FROM backend_records WHERE kind='discovery_jobs'")]
            if any(job["status"] in {"queued", "running"} for job in jobs):
                raise ValueError("Wait for the active collection to finish before backing up")
            for job in jobs:
                if job["status"] == "succeeded":
                    path = Path(job["result_path"]).resolve()
                    if not path.is_relative_to(scrape_root) or checksum(path) != job["sha256"]:
                        raise ValueError("A successful job's original CSV is missing or changed")
                    # Store a canonical path in the backup copy. Windows may have
                    # saved the original path with an 8.3 parent directory name.
                    if job["result_path"] != str(path):
                        job["result_path"] = str(path)
                        target.execute("UPDATE backend_records SET payload=? WHERE kind='discovery_jobs' AND id=?",
                                       (json.dumps(job), job["id"]))
            target.commit()
        if scrape_root.exists():
            for path in scrape_root.rglob("*"):
                if path.is_symlink():
                    raise ValueError("Scraper artifacts must not contain symbolic links")
                if path.is_file():
                    destination = folder / "scrapes" / path.relative_to(scrape_root)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, destination)
        files = {path.relative_to(folder).as_posix(): checksum(path) for path in folder.rglob("*") if path.is_file()}
        (folder / "manifest.json").write_text(json.dumps({"format": "aiautomation-backup-v1", "source_scrape_root": str(scrape_root), "files": files}, indent=2) + "\n")
        verify(folder)
        return folder
    except Exception:
        shutil.rmtree(folder)
        raise


def restore(folder, destination):
    manifest = verify(folder)
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    try:
        shutil.copyfile(folder / "backend.sqlite3", destination / "backend.sqlite3")
        (destination / "scrapes").mkdir()
        for name in manifest["files"]:
            relative = manifest_path(name)
            if relative.parts[0] == "scrapes":
                path = destination / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(folder / relative, path)
        original = Path(manifest["source_scrape_root"]).resolve()
        if not original.is_absolute():
            raise ValueError("Original artifact root must be absolute")
        with closing(sqlite3.connect(destination / "backend.sqlite3")) as connection, connection:
            for record_id, payload in connection.execute("SELECT id,payload FROM backend_records WHERE kind='discovery_jobs'").fetchall():
                job = json.loads(payload)
                if "result_path" in job:
                    old = Path(job["result_path"]).resolve()
                    if not old.is_relative_to(original):
                        raise ValueError("Discovery result lies outside the original artifact root")
                    job["result_path"] = str((destination / "scrapes" / old.relative_to(original)).resolve())
                    connection.execute("UPDATE backend_records SET payload=? WHERE kind='discovery_jobs' AND id=?", (json.dumps(job), record_id))
        return destination
    except Exception:
        shutil.rmtree(destination)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("--output-dir", type=Path, required=True)
    recover = commands.add_parser("restore")
    recover.add_argument("backup", type=Path)
    recover.add_argument("--destination", type=Path, required=True)
    check = commands.add_parser("verify")
    check.add_argument("backup", type=Path)
    args = parser.parse_args()
    if args.command == "create":
        from app.settings import Settings
        settings = Settings.from_env()
        if settings.persistence_backend != "sqlite":
            parser.error("This helper backs up SQLite only; use your provider's backup tools for Supabase")
        print(backup(Path(settings.database_path), Path(settings.scrape_output_path), args.output_dir))
    elif args.command == "restore":
        print(restore(args.backup, args.destination))
    else:
        verify(args.backup)
        print("Backup file checksums and SQLite integrity passed")
