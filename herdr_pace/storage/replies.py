import hashlib
import json
import re
import time

from .files import atomic_write
from .paths import state_directory

MAX_REPLY_BYTES = 1024 * 1024
MAX_SAVED_REPLIES = 64


def reply_key(pane_id: str, socket_path: str) -> str:
    return hashlib.sha256(f"{socket_path}\0{pane_id}".encode()).hexdigest()


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
