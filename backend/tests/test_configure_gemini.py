"""Disposable local settings only; no actual credential or provider call."""
import contextlib
import getpass
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

from dotenv import dotenv_values

from configure_gemini import main, save_config


FAKE_KEY = "fictional-gemini-key-for-local-setup"


class ConfigureGeminiTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.target = self.root / ".env"

    def test_saved_key_loads_after_two_fresh_process_starts(self):
        save_config(self.root, FAKE_KEY)
        environment = {k: v for k, v in os.environ.items() if not k.startswith(("GEMINI_", "LLM_"))}
        code = """import sys, json, hashlib
from dotenv import load_dotenv
from app.settings import Settings
load_dotenv(sys.argv[1])
s = Settings.from_env()
s.validate_runtime()
assert s.gemini_api_key == s.llm_api_key
print(json.dumps({'provider': s.llm_provider, 'model': s.llm_model,
    'key_hash': hashlib.sha256(s.gemini_api_key.encode()).hexdigest()}))
"""
        for _ in range(2):
            result = subprocess.run([sys.executable, "-c", code, str(self.target)],
                                    cwd=Path(__file__).resolve().parents[1], env=environment,
                                    capture_output=True, text=True, check=True)
            saved = json.loads(result.stdout)
            self.assertEqual(saved["provider"], "gemini")
            self.assertEqual(saved["model"], "gemini-3.5-flash-lite")
            self.assertEqual(saved["key_hash"], hashlib.sha256(FAKE_KEY.encode()).hexdigest())
            self.assertNotIn(FAKE_KEY, result.stdout + result.stderr)
        if os.name != "nt":
            self.assertEqual(self.target.stat().st_mode & 0o777, 0o600)

    def test_existing_duplicates_bom_comments_and_multiline_values_preserved(self):
        unrelated = '# Keep my records\r\nAPP_DB_PATH="D:/My CRM/.local/data.sqlite3"\r\nNOTES="first\r\nGEMINI_API_KEY=example-inside-notes\r\nlast"\r\n'
        self.target.write_bytes(("\ufeff" + unrelated + "export LLM_PROVIDER=openai\r\n"
                                 "GEMINI_MODEL=gemini-custom\r\nLLM_MODEL=old-model\r\n"
                                 "GEMINI_API_KEY=old-one\r\nGEMINI_API_KEY=old-two\r\n").encode())
        save_config(self.root, FAKE_KEY)
        text = self.target.read_bytes().decode()
        self.assertTrue(text.startswith(unrelated))
        values = dotenv_values(self.target, interpolate=False)
        self.assertEqual(values["NOTES"], "first\nGEMINI_API_KEY=example-inside-notes\nlast")
        self.assertEqual(values["APP_DB_PATH"], "D:/My CRM/.local/data.sqlite3")
        self.assertEqual(values["LLM_PROVIDER"], "gemini")
        self.assertEqual(values["LLM_MODEL"], "gemini-custom")
        self.assertEqual(values["GEMINI_API_KEY"], FAKE_KEY)
        self.assertNotIn("old-one", text)
        self.assertNotIn("old-two", text)

    def test_invalid_keys_cannot_inject_settings_or_modify_existing_file(self):
        self.target.write_bytes(b"APP_DB_PATH=keep.sqlite3\n")
        for key in ["", "too-short", FAKE_KEY + "\nAPP_ENV=production", "${GEMINI_API_KEY}", FAKE_KEY + " "]:
            with self.subTest(key_type="invalid"):
                with self.assertRaises(ValueError):
                    save_config(self.root, key)
                self.assertEqual(self.target.read_bytes(), b"APP_DB_PATH=keep.sqlite3\n")

    def test_invalid_existing_dotenv_is_preserved(self):
        original = b'APP_API_TOKEN="unclosed\n'
        self.target.write_bytes(original)
        with self.assertRaises(ValueError):
            save_config(self.root, FAKE_KEY)
        self.assertEqual(self.target.read_bytes(), original)

    def test_failed_atomic_replace_preserves_original_and_removes_private_temp(self):
        original = b"APP_DB_PATH=keep.sqlite3\n"
        self.target.write_bytes(original)
        with patch("configure_gemini.os.replace", side_effect=PermissionError("locked fixture")):
            with self.assertRaises(PermissionError):
                save_config(self.root, FAKE_KEY)
        self.assertEqual(self.target.read_bytes(), original)
        self.assertEqual(list(self.root.iterdir()), [self.target])

    def test_echoing_prompt_is_refused_without_saving(self):
        def insecure_prompt(*args, **kwargs):
            warnings.warn("no private terminal", getpass.GetPassWarning)
            return FAKE_KEY
        with patch("configure_gemini.getpass.getpass", side_effect=insecure_prompt), \
             patch("configure_gemini.save_config") as save, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(), 1)
        save.assert_not_called()
        self.assertNotIn(FAKE_KEY, output.getvalue())

    @unittest.skipIf(os.name == "nt", "Unprivileged Windows symlink creation is not assumed")
    def test_existing_symlink_target_is_not_modified(self):
        external = self.root / "other.env"
        external.write_bytes(b"APP_API_TOKEN=keep-this\n")
        self.target.symlink_to(external)
        with self.assertRaises(ValueError):
            save_config(self.root, FAKE_KEY)
        self.assertEqual(external.read_bytes(), b"APP_API_TOKEN=keep-this\n")


if __name__ == "__main__":
    unittest.main()
