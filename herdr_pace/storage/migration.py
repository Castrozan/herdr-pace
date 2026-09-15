import os
from pathlib import Path

from .files import atomic_write

PREVIOUS_PLUGIN_ID = "castrozan.speed-read"
PREVIOUS_EXECUTABLE = "herdr-speed-read"


def migrate_saved_reading(destination: Path) -> None:
    if destination.name != "castrozan.pace":
        return
    previous = destination.with_name(PREVIOUS_PLUGIN_ID)
    marker = destination / "migration.json"
    if marker.exists() or not previous.is_dir():
        return
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    candidates = [previous / "settings.json"]
    replies = previous / "replies"
    if replies.is_dir():
        candidates.extend(list(replies.glob("*.json"))[:64])
    for source in candidates:
        target = destination / source.relative_to(previous)
        if source.is_file() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            try:
                os.link(source, target)
            except (FileExistsError, FileNotFoundError):
                pass
    atomic_write(marker, {"source": PREVIOUS_PLUGIN_ID})
