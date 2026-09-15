from contextlib import nullcontext

import pytest

from herdr_speed_read import reader_popup
from herdr_speed_read.reader_playback import ReaderPlayback
from herdr_speed_read.reader_terminal import TerminalGeometry
from herdr_speed_read.reading_word import ReadingWord
from herdr_speed_read.terminal_colors import TerminalInput


@pytest.mark.parametrize("color_reports", [False, True])
def test_popup_waits_for_start_and_counts_three_seconds(
    monkeypatch, capsys, color_reports
):
    now = 0.0
    keys = [(4.0, " "), (5.5, "+"), (7.4, "q")]
    if color_reports:
        keys.extend(
            [
                (0.1, "\033]10;rgb:f7f7/f6f6/f5f5\033\\"),
                (0.2, "\033]4;1;rgb:c1c1/7070/1313\033\\"),
                (4.9, "\033]10;rgb:eeee/ffff/aaaa\033\\"),
                (5.8, "\033]4;1;rgb:"),
                (6.1, "ffff/aaaa/2222\033\\"),
            ]
        )
        keys.sort()
    frames = []
    original_render = reader_popup.render_frame

    def wait_for_input(readers, writers, errors, timeout):
        nonlocal now
        if keys[0][0] <= now + timeout:
            now = keys[0][0]
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
        lambda descriptor: TerminalGeometry(64, 11),
    )
    monkeypatch.setattr(reader_popup.os, "read", lambda *args: keys.pop(0)[1].encode())
    monkeypatch.setattr(reader_popup.select, "select", wait_for_input)
    monkeypatch.setattr(reader_popup, "render_frame", render)
    reader_popup.display_popup(
        ReaderPlayback([ReadingWord("One"), ReadingWord("two.")], 400)
    )

    assert frames[0] == (0.2 if color_reports else 0.25, 0, True, 0)
    for frame in [(4, 0, False, 3), (5, 0, False, 2), (5.5, 0, False, 2)]:
        assert frame in frames
    assert (6, 0, False, 1) in frames
    assert (7, 0, False, 0) in frames
    first_word_advance = next(frame[0] for frame in frames if frame[1] == 1)
    assert first_word_advance == pytest.approx(7 + 60 / 450)
    assert "Space play" in capsys.readouterr().out


def test_graphics_are_cleared_if_drawing_fails(monkeypatch, capsys):
    monkeypatch.setattr(reader_popup, "open_keyboard_terminal", lambda: nullcontext(3))
    monkeypatch.setattr(
        reader_popup,
        "TerminalInput",
        lambda: TerminalInput(foreground=(247, 246, 245), focus=(193, 112, 19)),
    )
    monkeypatch.setattr(
        reader_popup.TerminalGeometry,
        "read",
        lambda descriptor: TerminalGeometry(64, 11),
    )

    def fail_render(*args):
        raise RuntimeError("drawing failed")

    monkeypatch.setattr(reader_popup, "render_frame", fail_render)
    with pytest.raises(RuntimeError, match="drawing failed"):
        reader_popup.display_popup(ReaderPlayback([ReadingWord("One")], 400))
    assert capsys.readouterr().out.endswith("\033_Ga=d,d=I,i=1,q=2\033\\")
