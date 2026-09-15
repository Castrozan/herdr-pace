import os
from pathlib import Path

from .migration import migrate_saved_reading

PLUGIN_ID = "castrozan.pace"


def state_directory() -> Path:
    plugin_state = os.environ.get("HERDR_PLUGIN_STATE_DIR")
    state_home = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    destination = (
        Path(plugin_state)
        if plugin_state
        else state_home / "herdr" / "plugins" / PLUGIN_ID
    )
    migrate_saved_reading(destination)
    return destination
