import os
import re
import struct
import termios

import pytest
from wcwidth import wcswidth

from herdr_speed_read import reader_terminal, word_graphics
from herdr_speed_read.markdown_text import reading_words
from herdr_speed_read.reader_playback import ReaderPlayback
from herdr_speed_read.reader_popup import render_frame
from herdr_speed_read.reader_terminal import TerminalGeometry


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
    empty = render_frame(ReaderPlayback([], 400), TerminalGeometry(62, 9))
    assert "No completed reply in this pane yet." in empty
    finished = render_frame(
        ReaderPlayback(["Done."], 400, position=1), TerminalGeometry(62, 9)
    )
    assert "Finished. Press R to read again." in finished
    assert "Q/Esc close" in finished


@pytest.mark.parametrize("remaining", [3, 2, 1])
def test_countdown_replaces_the_word_until_reading_starts(remaining, monkeypatch):
    rendered_words = []

    def render_word(word, *args):
        rendered_words.append(word)
        return ""

    monkeypatch.setattr(word_graphics, "render_word_graphics", render_word)
    playback = ReaderPlayback(["One"], 400, paused=False, countdown_seconds=remaining)
    frame = render_frame(playback, TerminalGeometry(64, 11))
    assert "Starting in" in frame
    assert rendered_words == [str(remaining)]


def test_long_identifiers_are_read_in_full_across_frames():
    identifier = "https://example.test/" + "identifier" * 15
    frames = reading_words(identifier)
    assert "".join(frames) == identifier
    assert all(wcswidth(frame) <= 24 for frame in frames)


def test_only_reading_content_uses_graphics():
    frame = render_frame(ReaderPlayback(["Reading"], 400), TerminalGeometry(64, 11))
    assert "Paused  ·  400 WPM" in frame
    assert "Space play" in frame
    assert "1 / 1" in frame
    assert "r=3" in frame
    assert len(re.findall(r"a=T", frame)) == 1


def test_small_pane_asks_for_space_without_overflowing_graphics():
    frame = render_frame(ReaderPlayback(["Reading"], 400), TerminalGeometry(12, 5))
    assert "Enlarge pane" in frame
    assert "a=T" not in frame


@pytest.mark.parametrize(
    "pixel_size,cell_size", [((704, 253), (11, 23)), ((0, 0), (8, 16))]
)
def test_terminal_geometry_uses_native_pixel_size(
    keyboard_terminal, pixel_size, cell_size
):
    descriptor, _ = keyboard_terminal
    reader_terminal.fcntl.ioctl(
        descriptor, termios.TIOCSWINSZ, struct.pack("HHHH", 11, 64, *pixel_size)
    )
    geometry = TerminalGeometry.read(descriptor)
    assert geometry == TerminalGeometry(64, 11, *cell_size)
