import re
from contextlib import nullcontext

import pytest

from herdr_speed_read import reader_popup
from herdr_speed_read.markdown_text import reading_words
from herdr_speed_read.reader_playback import ReaderPlayback
from herdr_speed_read.reader_terminal import TerminalGeometry
from herdr_speed_read.terminal_colors import TerminalPalette


@pytest.mark.parametrize(
    "palette", [None, TerminalPalette((247, 246, 245), (193, 112, 19))]
)
def test_surrounding_text_stays_fixed_through_playback_and_replay(palette):
    playback = ReaderPlayback(reading_words("First\n\nSecond  \nThird."), 800)
    surroundings = []

    def capture():
        frame = reader_popup.render_frame(
            playback, TerminalGeometry(61, 9), palette, True
        )
        surroundings.append(
            [
                (row, text)
                for row, text in re.findall(r"\x1b\[(\d+);1H([^\x1b]*)", frame)
                if row in ("2", "6", "9")
            ]
        )

    capture()
    playback.handle_key(" ")
    while not playback.finished:
        capture()
        playback.advance_frame()
    capture()
    for key in (" ", " ", "r"):
        playback.handle_key(key)
        capture()
    assert all(frame == surroundings[0] for frame in surroundings)


def test_setting_labels_do_not_shift_when_numeric_width_changes():
    headings = []
    for speed, countdown in ((50, 0), (950, 9), (1000, 10), (2000, 3)):
        playback = ReaderPlayback(
            reading_words("Hello"), speed, countdown_duration_seconds=countdown
        )
        frame = reader_popup.render_frame(playback, TerminalGeometry(61, 9), None, True)
        heading = re.search(r"\x1b\[2;1H([^\x1b]*)", frame)[1]
        headings.append((heading.index("WPM"), heading.index("countdown")))
    assert len(set(headings)) == 1


def test_automatic_playback_only_redraws_the_reading_area(monkeypatch):
    now = 0.0
    inputs = [(0.4, " "), (2.4, "+"), (2.5, "]"), (2.6, "r"), (4.0, "q")]
    frames = []
    original_render = reader_popup.render_frame

    def wait_for_input(readers, writers, errors, timeout):
        nonlocal now
        if inputs[0][0] <= now + timeout:
            now = inputs[0][0]
            return readers, [], []
        now += timeout
        return [], [], []

    def render(*arguments):
        frame = original_render(*arguments)
        frames.append((now, frame))
        return frame

    monkeypatch.setattr(reader_popup, "open_keyboard_terminal", lambda: nullcontext(3))
    monkeypatch.setattr(reader_popup.time, "monotonic", lambda: now)
    monkeypatch.setattr(
        reader_popup.TerminalGeometry,
        "read",
        lambda descriptor: TerminalGeometry(61, 9),
    )
    monkeypatch.setattr(
        reader_popup.os, "read", lambda *args: inputs.pop(0)[1].encode()
    )
    monkeypatch.setattr(reader_popup.select, "select", wait_for_input)
    monkeypatch.setattr(reader_popup, "render_frame", render)
    reader_popup.display_popup(
        ReaderPlayback(
            reading_words("First\n\nSecond  \nThird."),
            800,
            countdown_duration_seconds=0,
        )
    )
    full_frames = [timestamp for timestamp, frame in frames if "\033[2J" in frame]
    assert full_frames == [0, 2.4, 2.5]
    for timestamp, frame in frames:
        if timestamp in full_frames:
            continue
        rows = set(re.findall(r"\x1b\[(\d+);1H", frame))
        assert rows <= {"3", "4", "5"}
        assert "WPM" not in frame
        assert "Space" not in frame
