import json
import subprocess

import pytest
from click.testing import CliRunner

from herdr_pace.commands import cli
from herdr_pace.reading.actions import ReaderAction
from herdr_pace.reading.settings import ReaderSettings
from herdr_pace.storage.replies import load_reply, reply_key
from herdr_pace.storage.settings import load_reader_settings


@pytest.fixture
def runner(tmp_path, monkeypatch):
    monkeypatch.setenv("HERDR_PLUGIN_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("HERDR_PANE_ID", "pane")
    monkeypatch.setenv("HERDR_SOCKET_PATH", "socket")
    monkeypatch.setenv("HERDR_BIN_PATH", "herdr")
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    return CliRunner()


def test_action_opens_popup_for_source_pane(runner, monkeypatch):
    from herdr_pace.capture import herdr

    calls = []
    monkeypatch.setattr(
        herdr.subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs))
    )
    assert runner.invoke(cli, ["open"]).exit_code == 0
    arguments, options = calls[0]
    assert arguments[0] == [
        "herdr",
        "plugin",
        "pane",
        "open",
        "--plugin",
        "castrozan.pace",
        "--entrypoint",
        "reader",
        "--env",
        f"HERDR_PACE_REPLY_KEY={reply_key('pane', 'socket')}",
    ]
    assert options["timeout"] == 3


@pytest.mark.parametrize("raw", ["{", "null", "[]", '{"reply_text": 3}'])
def test_malformed_capture_never_blocks_completion(runner, raw):
    assert runner.invoke(cli, ["capture"], input=raw).exit_code == 0


def test_capture_command_saves_completed_reply(runner):
    result = runner.invoke(
        cli,
        ["capture"],
        input=json.dumps(
            {"hook_event_name": "Stop", "last_assistant_message": "Saved."}
        ),
    )
    assert result.exit_code == 0
    assert load_reply(reply_key("pane", "socket")) == "Saved."


def test_failed_open_reports_error(runner, monkeypatch):
    from herdr_pace.capture import herdr

    def failed(*args, **kwargs):
        raise subprocess.TimeoutExpired("herdr", 3)

    monkeypatch.setattr(herdr.subprocess, "run", failed)
    result = runner.invoke(cli, ["open"])
    assert result.exit_code == 1
    assert "timed out" in result.output


def test_reader_restores_and_saves_preferences(runner, tmp_path, monkeypatch):
    from herdr_pace.terminal import application

    (tmp_path / "settings.json").write_text(
        '{"words_per_minute":650,"countdown_duration_seconds":5}'
    )
    observed = []

    def adjust(playback):
        observed.append(
            (playback.words_per_minute, playback.countdown_duration_seconds)
        )
        assert playback.paused
        playback.apply(ReaderAction.FASTER)
        playback.apply(ReaderAction.SHORTER_COUNTDOWN)

    monkeypatch.setattr(application, "display_popup", adjust)
    assert runner.invoke(cli, ["read"]).exit_code == 0
    assert load_reader_settings() == ReaderSettings(700, 4)
    assert runner.invoke(cli, ["read"]).exit_code == 0
    assert observed == [(650, 5), (700, 4)]
    assert load_reader_settings() == ReaderSettings(750, 3)


@pytest.mark.parametrize("arguments,code", [(["--help"], 0), (["unknown"], 2)])
def test_cli_has_standard_help_and_usage_errors(runner, arguments, code):
    result = runner.invoke(cli, arguments)
    assert result.exit_code == code
    assert "Usage:" in result.output
