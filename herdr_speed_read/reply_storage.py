import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path

from .reader_settings import DEFAULT_WPM, MAX_WPM, MIN_WPM

PLUGIN_ID = "castrozan.speed-read"
MAX_REPLY_BYTES = 1024 * 1024
MAX_SAVED_REPLIES = 64


def state_directory() -> Path:
    plugin_state = os.environ.get("HERDR_PLUGIN_STATE_DIR")
    if plugin_state:
        return Path(plugin_state)
    state_home = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return state_home / "herdr" / "plugins" / PLUGIN_ID


def reply_key(pane_id: str, socket_path: str) -> str:
    return hashlib.sha256(f"{socket_path}\0{pane_id}".encode()).hexdigest()


def atomic_write(destination: Path, content: dict) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_path = tempfile.mkstemp(dir=destination.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(content, output, ensure_ascii=False)
        os.replace(temporary_path, destination)
    finally:
        Path(temporary_path).unlink(missing_ok=True)


def save_reply(pane_id: str, socket_path: str, session_id: str, text: str) -> None:
    if not pane_id or not socket_path or not text.strip():
        return
    if len(text.encode("utf-8")) > MAX_REPLY_BYTES:
        raise ValueError("Completed reply exceeds the 1 MiB reading limit")
    directory = state_directory() / "replies"
    atomic_write(
        directory / f"{reply_key(pane_id, socket_path)}.json",
        {"text": text, "session_id": session_id, "captured_at": time.time()},
    )
    snapshots = sorted(directory.glob("*.json"), key=lambda path: path.stat().st_mtime)
    for snapshot in snapshots[:-MAX_SAVED_REPLIES]:
        snapshot.unlink(missing_ok=True)


def load_reply(key: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", key):
        return ""
    try:
        with (state_directory() / "replies" / f"{key}.json").open("rb") as source:
            content = source.read(MAX_REPLY_BYTES * 2 + 4096)
        stored = json.loads(content)
    except (OSError, ValueError):
        return ""
    text = stored.get("text") if isinstance(stored, dict) else None
    return text if isinstance(text, str) else ""


def load_reading_speed() -> int:
    try:
        with (state_directory() / "settings.json").open("rb") as source:
            settings = json.loads(source.read(4096))
        speed = settings.get("words_per_minute")
        if type(speed) is int and MIN_WPM <= speed <= MAX_WPM:
            return speed
    except (OSError, ValueError, AttributeError):
        pass
    return DEFAULT_WPM


def save_reading_speed(words_per_minute: int) -> None:
    atomic_write(
        state_directory() / "settings.json", {"words_per_minute": words_per_minute}
    )
