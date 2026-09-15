import os
import subprocess

from herdr_pace.storage.paths import PLUGIN_ID
from herdr_pace.storage.replies import reply_key


def open_reader_pane() -> None:
    pane_id = os.environ.get("HERDR_PANE_ID", "")
    socket_path = os.environ.get("HERDR_SOCKET_PATH", "")
    command = os.environ.get("HERDR_BIN_PATH", "")
    if not pane_id or not socket_path or not command:
        raise ValueError("Open Herdr Pace from a Herdr pane")
    subprocess.run(
        [
            command,
            "plugin",
            "pane",
            "open",
            "--plugin",
            PLUGIN_ID,
            "--entrypoint",
            "reader",
            "--env",
            f"HERDR_PACE_REPLY_KEY={reply_key(pane_id, socket_path)}",
        ],
        check=True,
        timeout=3,
    )
