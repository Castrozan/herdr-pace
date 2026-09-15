from contextlib import nullcontext

import pytest

from herdr_speed_read import reader_popup
from herdr_speed_read.reader_playback import ReaderPlayback
from herdr_speed_read.reader_terminal import TerminalGeometry
from herdr_speed_read.reading_word import ReadingWord


@pytest.mark.parametrize(
    "duration,adjustments,first_word_at",
    [
        (3, [(1.1, "]"), (2.2, "[")], 3.4),
        (3, [(0.9, "[[[")], 0.9),
        (0, [(0.45, "]")], 0.4),
        (1, [], 1.4),
    ],
)
def test_adjustment_preserves_ticks_and_full_word_intervals(
    monkeypatch, duration, adjustments, first_word_at
):
    now = 0.0
    inputs = sorted([(0.4, " "), *adjustments, (first_word_at + 0.6, "q")])
    frames = []
    original_render = reader_popup.render_frame

    def wait_for_input(readers, writers, errors, timeout):
        nonlocal now
        if inputs[0][0] <= now + timeout:
            now = inputs[0][0]
            return readers, [], []
        now += timeout
        return [], [], []

    def render(playback, geometry, palette, redraw_controls):
        frames.append(
            (now, playback.position, playback.paused, playback.countdown_seconds)
        )
        return original_render(playback, geometry, palette, redraw_controls)

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
            [ReadingWord("One"), ReadingWord("two"), ReadingWord("three")],
            400,
            countdown_duration_seconds=duration,
        )
    )

    first_word = next(frame for frame in frames if not frame[2] and not frame[3])
    assert first_word[0] == pytest.approx(first_word_at)
    second_word = next(frame for frame in frames if frame[1] == 1)
    assert second_word[0] == pytest.approx(first_word_at + 0.15)
