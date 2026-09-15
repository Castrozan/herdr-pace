from contextlib import nullcontext

import pytest

from herdr_speed_read import reader_popup
from herdr_speed_read.markdown_text import reading_words
from herdr_speed_read.reader_playback import ReaderPlayback
from herdr_speed_read.reader_terminal import TerminalGeometry

FOREGROUND = b"\033]10;rgb:f7f7/f6f6/f5f5\033\\"
FOCUS = b"\033]4;1;rgb:c1c1/7070/1313\033\\"


def startup_frames(
    monkeypatch, events, text="Opening smoothly.", countdown=3, initial_render_delay=0.0
):
    now = 0.0
    frames = []

    def wait_for_input(readers, writers, errors, timeout):
        nonlocal now
        if events[0][0] <= now + timeout:
            now = events[0][0]
            return readers, [], []
        now += timeout
        return [], [], []

    def render(playback, geometry, palette, redraw_controls):
        nonlocal now
        frames.append((now, palette, playback.reading_text, playback.paused))
        if len(frames) == 1:
            now += initial_render_delay
        return ""

    monkeypatch.setattr(reader_popup, "open_keyboard_terminal", lambda: nullcontext(3))
    monkeypatch.setattr(reader_popup.time, "monotonic", lambda: now)
    monkeypatch.setattr(reader_popup.select, "select", wait_for_input)
    monkeypatch.setattr(reader_popup.os, "read", lambda *args: events.pop(0)[1])
    monkeypatch.setattr(
        reader_popup.TerminalGeometry, "read", lambda _: TerminalGeometry(61, 9)
    )
    monkeypatch.setattr(reader_popup, "render_frame", render)
    reader_popup.display_popup(
        ReaderPlayback(reading_words(text), 400, countdown_duration_seconds=countdown)
    )
    return frames


def test_first_frame_waits_for_both_terminal_colors(monkeypatch):
    frames = startup_frames(
        monkeypatch, [(0.05, FOREGROUND), (0.1, FOCUS), (0.8, b"q")]
    )
    assert len(frames) == 1
    assert frames[0][0] == pytest.approx(0.1)
    assert frames[0][1] is not None
    assert frames[0][2:] == ("Opening", True)


@pytest.mark.parametrize("late_reports", [b"", FOREGROUND + FOCUS])
def test_missing_colors_fall_back_once_without_a_later_zoom(monkeypatch, late_reports):
    frames = startup_frames(monkeypatch, [(0.6, late_reports), (0.8, b"q")])
    assert frames == [(0.25, None, "Opening", True)]


@pytest.mark.parametrize("key", [b"q", b"\x1b", b""])
def test_close_during_startup_does_not_flash_a_frame(monkeypatch, key):
    frames = startup_frames(monkeypatch, [(0.05, key), (0.8, b"q")])
    assert frames == []


def test_play_pressed_during_startup_is_preserved(monkeypatch):
    frames = startup_frames(
        monkeypatch, [(0.05, b" " + FOREGROUND + FOCUS), (0.8, b"q")]
    )
    assert frames[0][0] == pytest.approx(0.05)
    assert frames[0][1] is not None
    assert frames[0][2:] == ("3", False)


def test_empty_reply_does_not_wait_for_font_colors(monkeypatch):
    frames = startup_frames(monkeypatch, [(0.8, b"q")], text="")
    assert frames == [(0.0, None, "", True)]


@pytest.mark.parametrize("reports_at", [0.2, 0.4])
def test_early_play_gives_the_first_word_its_full_interval(monkeypatch, reports_at):
    frames = startup_frames(
        monkeypatch,
        [(0.01, b" "), (reports_at, FOREGROUND + FOCUS), (0.9, b"q")],
        countdown=0,
        initial_render_delay=0.2,
    )
    assert frames[0][2] == "Opening"
    assert frames[1][2] == "smoothly."
    assert frames[1][0] - frames[0][0] == pytest.approx(0.35)
