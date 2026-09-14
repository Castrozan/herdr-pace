import os
import re
import termios

import pytest
from wcwidth import wcswidth

from herdr_speed_read import reader_terminal
from herdr_speed_read.markdown_text import reading_words
from herdr_speed_read.reader_playback import ReaderPlayback
from herdr_speed_read.reader_popup import render_frame
from herdr_speed_read.word_rendering import format_word_with_orp_highlight


@pytest.fixture
def keyboard_terminal(monkeypatch):
    master, slave = os.openpty()
    original = termios.tcgetattr(slave)
    monkeypatch.setattr(
        reader_terminal,
        "open",
        lambda *args, **kwargs: os.fdopen(os.dup(slave), "rb", buffering=0),
        raising=False,
    )
    try:
        yield slave, original
    finally:
        os.close(slave)
        os.close(master)


@pytest.mark.parametrize("failure", [False, True])
def test_terminal_modes_and_cursor_are_restored(keyboard_terminal, capsys, failure):
    slave, original = keyboard_terminal
    try:
        with reader_terminal.open_keyboard_terminal() as descriptor:
            assert os.isatty(descriptor)
            assert not termios.tcgetattr(descriptor)[3] & termios.ICANON
            if failure:
                raise RuntimeError("playback failed")
    except RuntimeError:
        pass
    restored = termios.tcgetattr(slave)
    interactive_modes = termios.ECHO | termios.ICANON | termios.ISIG | termios.IEXTEN
    assert restored[3] & interactive_modes == original[3] & interactive_modes
    assert restored[:3] == original[:3]
    assert capsys.readouterr().out == "\033[?25l\033[?25h"


def test_missing_terminal_does_not_hide_cursor(monkeypatch, capsys):
    def missing_terminal(*args, **kwargs):
        raise OSError("No terminal")

    monkeypatch.setattr(reader_terminal, "open", missing_terminal, raising=False)
    with pytest.raises(SystemExit):
        with reader_terminal.open_keyboard_terminal():
            pytest.fail("Missing terminal cannot enter playback")
    assert "\033[?25l" not in capsys.readouterr().out


def test_empty_and_completed_views_are_actionable():
    empty = render_frame(ReaderPlayback([], 400), 62, 9)
    assert "No completed reply in this pane yet." in empty
    finished = render_frame(ReaderPlayback(["Done."], 400, position=1), 62, 9)
    assert "Finished. Press R to read again." in finished
    assert "Q/Esc close" in finished


def test_long_identifiers_are_read_in_full_across_frames():
    identifier = "https://example.test/" + "identifier" * 15
    frames = reading_words(identifier)
    assert "".join(frames) == identifier
    assert all(wcswidth(frame) <= 24 for frame in frames)


def test_unicode_focus_uses_terminal_cell_width():
    highlighted = format_word_with_orp_highlight("世界你好", 1, 62)
    before_focus = highlighted.split("\033[38;5;1m")[0]
    plain = re.sub(r"\033\[[0-9;]*m", "", before_focus)
    assert wcswidth(plain) == 31
