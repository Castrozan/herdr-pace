import io
import json
import subprocess
from types import SimpleNamespace

import pytest

from herdr_speed_read import application
from herdr_speed_read.reader_settings import ReaderSettings
from herdr_speed_read.reply_storage import load_reader_settings, load_reply, reply_key


def test_plugin_action_opens_popup_for_source_pane(monkeypatch):
    monkeypatch.setenv("HERDR_PANE_ID", "w1:p2")
    monkeypatch.setenv("HERDR_SOCKET_PATH", "/tmp/test.sock")
    monkeypatch.setenv("HERDR_BIN_PATH", "/example/herdr")
    calls = []
    monkeypatch.setattr(
        application.subprocess,
        "run",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    application.open_reader()
    arguments, options = calls[0]
    assert arguments[0][:6] == [
        "/example/herdr",
        "plugin",
        "pane",
        "open",
        "--plugin",
        "castrozan.speed-read",
    ]
    assert "--target-pane" not in arguments[0]
    assert arguments[0][-2:] == [
        "--env",
        f"SPEED_READ_REPLY_KEY={reply_key('w1:p2', '/tmp/test.sock')}",
    ]
    assert options["timeout"] == 3


@pytest.mark.parametrize("raw", [b"{", b"null", b"[]", b'{"reply_text": 3}'])
def test_malformed_capture_never_blocks_completion(monkeypatch, raw):
    monkeypatch.setattr(application.sys, "argv", ["herdr-speed-read", "capture"])
    monkeypatch.setattr(
        application.sys, "stdin", SimpleNamespace(buffer=io.BytesIO(raw))
    )
    application.main()


def test_capture_cli_handles_native_stop_payload(tmp_path, monkeypatch):
    monkeypatch.setenv("HERDR_PLUGIN_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("HERDR_PANE_ID", "pane")
    monkeypatch.setenv("HERDR_SOCKET_PATH", "socket")
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setattr(application.sys, "argv", ["herdr-speed-read", "capture"])
    payload = {"hook_event_name": "Stop", "last_assistant_message": "Saved."}
    monkeypatch.setattr(
        application.sys,
        "stdin",
        SimpleNamespace(buffer=io.BytesIO(json.dumps(payload).encode())),
    )
    application.main()
    assert load_reply(reply_key("pane", "socket")) == "Saved."


def test_failed_open_reports_failure(monkeypatch):
    monkeypatch.setattr(application.sys, "argv", ["herdr-speed-read", "open"])
    monkeypatch.setenv("HERDR_PANE_ID", "pane")
    monkeypatch.setenv("HERDR_SOCKET_PATH", "socket")
    monkeypatch.setenv("HERDR_BIN_PATH", "herdr")

    def failed_command(*args, **kwargs):
        raise subprocess.TimeoutExpired("herdr", 3)

    monkeypatch.setattr(application.subprocess, "run", failed_command)
    with pytest.raises(SystemExit) as error:
        application.main()
    assert error.value.code == 1


def test_reader_restores_and_saves_countdown_with_speed(tmp_path, monkeypatch):
    from herdr_speed_read import reader_popup

    monkeypatch.setenv("HERDR_PLUGIN_STATE_DIR", str(tmp_path))
    (tmp_path / "settings.json").write_text(
        '{"words_per_minute":650,"countdown_duration_seconds":5}'
    )
    observed = []

    def adjust_settings(playback):
        observed.append(
            (playback.words_per_minute, playback.countdown_duration_seconds)
        )
        assert playback.paused
        playback.handle_key("+")
        playback.handle_key("[")

    monkeypatch.setattr(reader_popup, "display_popup", adjust_settings)
    application.read_reply()
    assert load_reader_settings() == ReaderSettings(700, 4)
    application.read_reply()
    assert observed == [(650, 5), (700, 4)]
    assert load_reader_settings() == ReaderSettings(750, 3)
