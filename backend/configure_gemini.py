"""One-time local Gemini setup. Never accepts a secret on the command line."""
import getpass
import io
import os
import re
import sys
import tempfile
import warnings
from pathlib import Path

from dotenv import dotenv_values
from dotenv.parser import parse_stream


DEFAULT_MODEL = "gemini-3.5-flash-lite"


def save_config(root: Path, key: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9._-]{16,512}", key):
        raise ValueError("Enter a nonempty API key without spaces or line breaks.")
    target = root / ".env"
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise ValueError("The existing .env is not a regular file; it was left unchanged.")
    original_bytes = target.read_bytes() if target.exists() else None
    original = original_bytes.decode("utf-8-sig") if original_bytes is not None else ""
    bindings = list(parse_stream(io.StringIO(original)))
    if any(binding.error for binding in bindings):
        raise ValueError("The existing .env has invalid syntax; it was left unchanged.")
    current = dotenv_values(stream=io.StringIO(original), interpolate=False)
    model = current.get("GEMINI_MODEL") or (
        current.get("LLM_MODEL") if current.get("LLM_PROVIDER") == "gemini" else None
    ) or DEFAULT_MODEL
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", model):
        raise ValueError("The existing Gemini model setting is invalid; .env was left unchanged.")
    updates = {"LLM_PROVIDER": "gemini", "LLM_MODEL": model,
               "GEMINI_MODEL": model, "GEMINI_API_KEY": key}
    newline = "\r\n" if "\r\n" in original else "\n"
    remaining = set(updates)
    output = []
    for binding in bindings:
        if binding.key in updates:
            # Replace every duplicate so a later old value cannot override it.
            output.append(f"{binding.key}='{updates[binding.key]}'{newline}")
            remaining.discard(binding.key)
        else:
            output.append(binding.original.string)
    text = "".join(output)
    if text and not text.endswith(("\n", "\r")):
        text += newline
    text += "".join(f"{name}='{value}'{newline}" for name, value in updates.items() if name in remaining)
    temporary = None
    try:
        # The temporary filename is also covered by the repository's .env.* ignore.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="",
                                         prefix=".env.", dir=root, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        # Avoid overwriting settings changed while the operator was configuring.
        if target.is_symlink() or (target.read_bytes() if target.exists() else None) != original_bytes:
            raise ValueError("The .env changed during setup; no settings were replaced. Run setup again.")
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return target


def main() -> int:
    print("One-time Gemini setup for this project.")
    print("Paste the key at the hidden prompt; it will not appear as you type.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            key = getpass.getpass("Gemini API key (hidden): ")
        save_config(Path(__file__).resolve().parents[1], key)
    except (KeyboardInterrupt, EOFError, getpass.GetPassWarning):
        print("Setup cancelled: a private interactive prompt is required. No key was printed.")
        return 1
    except (OSError, UnicodeError, ValueError):
        # Exceptions may carry configuration content. Never print their raw text.
        print("Could not save Gemini settings. Check that .env is valid and writable, then run setup again.")
        return 1
    print("Saved privately in this project's .env. Existing non-AI settings were preserved.")
    print("Restart the backend once. Future starts load the saved key automatically.")
    print("In AI Agent, click Verify live AI. Saving a key does not verify provider access.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
