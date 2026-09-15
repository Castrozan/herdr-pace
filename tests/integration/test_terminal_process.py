import json
import os
import re
import signal
import sys

import pexpect
import pyte
import pytest

from herdr_pace.terminal.palette import COLOR_QUERY

REPORTS = "\x1b]10;rgb:f7f7/f6f6/f5f5\x1b\\\x1b]4;1;rgb:c1c1/7070/1313\x1b\\"


@pytest.fixture
def terminal(tmp_path):
    key = "a" * 64
    (tmp_path / "replies").mkdir()
    (tmp_path / "replies" / f"{key}.json").write_text(
        json.dumps({"text": "First\n\nSecond  \nThird."})
    )
    (tmp_path / "settings.json").write_text(
        '{"words_per_minute":400,"countdown_duration_seconds":0}'
    )
    environment = dict(
        os.environ,
        HERDR_PLUGIN_STATE_DIR=str(tmp_path),
        HERDR_PACE_REPLY_KEY=key,
        TERM="xterm-256color",
    )
    with pexpect.spawn(
        sys.executable,
        ["-m", "herdr_pace", "read"],
        env=environment,
        dimensions=(9, 61),
        encoding="utf-8",
        timeout=4,
    ) as child:
        child.delaybeforesend = None
        child.expect_exact(COLOR_QUERY)
        yield child


@pytest.mark.parametrize("palette", [False, True])
def test_first_frame_is_complete_and_late_reports_never_zoom(terminal, palette):
    if palette:
        terminal.send(REPORTS)
    terminal.expect_exact("\x1b[?2026l")
    opening = terminal.before
    assert opening.count("\x1b[?2026h") == 1
    assert "Space play/pause" in opening
    assert "400 WPM" in opening
    assert ("a=T" in opening) == palette
    terminal.send(REPORTS)
    terminal.expect(pexpect.TIMEOUT, timeout=0.15)
    assert "a=T" not in terminal.before
    terminal.send("\x1b")
    terminal.expect(pexpect.EOF)
    assert "\x1b[?25h" in terminal.before
    assert "a=d,d=I" in terminal.before
    terminal.close()
    assert terminal.exitstatus == 0


@pytest.mark.parametrize("key", ["q", "\x1b", "\x03"])
def test_quitting_before_first_frame_does_not_flash(terminal, key):
    terminal.send(key)
    terminal.expect(pexpect.EOF)
    assert "\x1b[?2026h" not in terminal.before
    terminal.close()
    assert terminal.exitstatus == 0


def test_early_play_shows_first_word_before_advancing(terminal):
    terminal.send(" ")
    screen = pyte.Screen(61, 9)
    stream = pyte.Stream(screen)
    for word in ("First", "¶"):
        while True:
            terminal.expect_exact("\x1b[?2026l")
            stream.feed(re.sub(r"\x1b_G.*?\x1b\\", "", terminal.before))
            if screen.display[3].strip() == word:
                break
    terminal.send("q")
    terminal.expect(pexpect.EOF)


def test_same_size_resize_restores_the_large_word(terminal):
    terminal.send(REPORTS)
    terminal.expect_exact("\x1b[?2026l")
    os.kill(terminal.pid, signal.SIGWINCH)
    terminal.expect_exact("\x1b[?2026l")
    assert "a=T" in terminal.before
    assert "Space play/pause" in terminal.before
    terminal.send("q")
    terminal.expect(pexpect.EOF)


@pytest.mark.parametrize(
    "report", ["\x1b[?2026;1$y", "\x1b[?1;2c", "\x1b[>1;4000;0c", "\x1b[0n"]
)
def test_terminal_status_reports_do_not_quit_or_change_settings(terminal, report):
    terminal.send(REPORTS)
    terminal.expect_exact("\x1b[?2026l")
    terminal.send(report)
    terminal.expect(pexpect.TIMEOUT, timeout=0.1)
    assert "WPM" not in terminal.before
    assert "countdown" not in terminal.before
    assert terminal.isalive()
    terminal.send("q")
    terminal.expect(pexpect.EOF)
