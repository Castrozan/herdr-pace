from contextlib import nullcontext

import pytest

from herdr_speed_read import reader_popup
from herdr_speed_read.reader_playback import ReaderPlayback


def test_popup_waits_for_start_and_counts_three_seconds(monkeypatch, capsys):
    now = 0.0
    keys = [(4.0, " "), (5.5, "+"), (7.4, "q")]
    frames = []
    original_render = reader_popup.render_frame

    def wait_for_input(readers, writers, errors, timeout):
        nonlocal now
        if keys[0][0] <= now + timeout:
            now = keys[0][0]
            return readers, [], []
        now += timeout
        return [], [], []

    def render(playback, width, height):
        frames.append(
            (now, playback.position, playback.paused, playback.countdown_seconds)
        )
        return original_render(playback, width, height)

    monkeypatch.setattr(reader_popup, "open_keyboard_terminal", lambda: nullcontext(3))
    monkeypatch.setattr(reader_popup.time, "monotonic", lambda: now)
    monkeypatch.setattr(
        reader_popup.os, "get_terminal_size", lambda descriptor: (64, 11)
    )
    monkeypatch.setattr(reader_popup.os, "read", lambda *args: keys.pop(0)[1].encode())
    monkeypatch.setattr(reader_popup.select, "select", wait_for_input)
    monkeypatch.setattr(reader_popup, "render_frame", render)
    reader_popup.display_popup(ReaderPlayback(["One", "two."], 400))

    assert frames[0] == (0, 0, True, 0)
    assert frames[1:4] == [(4, 0, False, 3), (5, 0, False, 2), (5.5, 0, False, 2)]
    assert (6, 0, False, 1) in frames
    assert (7, 0, False, 0) in frames
    first_word_advance = next(frame[0] for frame in frames if frame[1] == 1)
    assert first_word_advance == pytest.approx(7 + 60 / 450)
    assert "Space play" in capsys.readouterr().out
