import json
import os
import subprocess
import sys

from .hook_capture import capture_hook
from .hook_installation import install_hooks
from .reply_storage import (
    MAX_REPLY_BYTES,
    PLUGIN_ID,
    load_reading_speed,
    load_reply,
    reply_key,
    save_reading_speed,
)


def capture_reply() -> None:
    payload = json.loads(sys.stdin.buffer.read(MAX_REPLY_BYTES * 2 + 4096))
    if isinstance(payload, dict):
        capture_hook(payload)


def open_reader() -> None:
    pane_id = os.environ.get("HERDR_PANE_ID", "")
    socket_path = os.environ.get("HERDR_SOCKET_PATH", "")
    herdr_command = os.environ.get("HERDR_BIN_PATH", "")
    if not pane_id or not socket_path or not herdr_command:
        raise ValueError("Open the speed reader from a Herdr pane")
    subprocess.run(
        [
            herdr_command,
            "plugin",
            "pane",
            "open",
            "--plugin",
            PLUGIN_ID,
            "--entrypoint",
            "reader",
            "--env",
            f"SPEED_READ_REPLY_KEY={reply_key(pane_id, socket_path)}",
        ],
        check=True,
        timeout=3,
    )


def read_reply() -> None:
    from .markdown_text import reading_words
    from .reader_playback import ReaderPlayback
    from .reader_popup import display_popup

    text = load_reply(os.environ.get("SPEED_READ_REPLY_KEY", ""))
    original_speed = load_reading_speed()
    playback = ReaderPlayback(reading_words(text), original_speed)
    try:
        display_popup(playback)
    finally:
        if playback.words_per_minute != original_speed:
            save_reading_speed(playback.words_per_minute)


def main() -> None:
    actions = {
        "capture": capture_reply,
        "open": open_reader,
        "read": read_reply,
        "install-hooks": install_hooks,
    }
    if len(sys.argv) != 2 or sys.argv[1] not in actions:
        print(
            "Usage: herdr-speed-read capture|open|read|install-hooks", file=sys.stderr
        )
        raise SystemExit(2)
    try:
        actions[sys.argv[1]]()
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as failure:
        print(f"Speed reader: {failure}", file=sys.stderr)
        if sys.argv[1] == "capture":
            return
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
