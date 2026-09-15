import os
import select
import sys
import time

from wcwidth import wcswidth

from .reader_playback import ReaderPlayback
from .reader_terminal import TerminalGeometry, open_keyboard_terminal
from .terminal_colors import COLOR_QUERY, TerminalInput, TerminalPalette
from .word_rendering import render_terminal_word


def centered_line(text: str, width: int) -> str:
    text = text[:width]
    return " " * max(0, (width - wcswidth(text)) // 2) + text


def render_frame(
    playback: ReaderPlayback,
    geometry: TerminalGeometry,
    palette: TerminalPalette | None,
) -> str:
    from .word_graphics import clear_word_image, render_word_graphics

    width, height = geometry.columns, geometry.rows
    middle = max(2, height // 2)
    progress = min(playback.position + 1, len(playback.words))
    heading = (
        f"{playback.words_per_minute} WPM  "
        f"{playback.countdown_duration_seconds}s countdown"
    )
    graphics = clear_word_image()
    if not playback.words:
        word = centered_line("No completed reply in this pane yet.", width)
        heading = "Speed reader"
    elif width < 12 or height < 7:
        word = centered_line("Enlarge pane to read.", width)
    else:
        reading_text = (
            str(playback.countdown_seconds)
            if playback.countdown_seconds
            else playback.word
        )
        word = "" if palette else render_terminal_word(reading_text, width)
        if palette:
            graphics = render_word_graphics(
                reading_text,
                width,
                max(1, middle - 1),
                geometry.cell_width,
                geometry.cell_height,
                palette,
            )
    playback_control = (
        "replay" if playback.finished else "play" if playback.paused else "pause"
    )
    lines = (
        (max(1, middle - 2), centered_line(heading, width)),
        (middle, word),
        (
            min(height - 1, middle + 2),
            centered_line(f"{progress} / {len(playback.words)}", width),
        ),
        (
            height,
            centered_line(
                f"Space {playback_control}  +/- WPM  [/] countdown  R restart  Q/Esc close",
                width,
            ),
        ),
    )
    return (
        "\033[?2026h\033[2J"
        + "".join(f"\033[{row};1H{text}" for row, text in lines)
        + graphics
        + "\033[?2026l"
    )


def display_popup(playback: ReaderPlayback) -> None:
    from .word_graphics import clear_word_image

    with open_keyboard_terminal() as keyboard_descriptor:
        try:
            deadline = time.monotonic() + playback.frame_delay
            next_color_query = 0.0
            terminal_input = TerminalInput()
            previous_frame_state = None
            while True:
                if time.monotonic() >= next_color_query:
                    sys.stdout.write(COLOR_QUERY)
                    sys.stdout.flush()
                    next_color_query = time.monotonic() + 1.0
                geometry = TerminalGeometry.read(keyboard_descriptor)
                frame_state = (
                    playback.position,
                    playback.words_per_minute,
                    playback.paused,
                    playback.countdown_seconds,
                    playback.countdown_duration_seconds,
                    geometry,
                    terminal_input.palette,
                )
                if frame_state != previous_frame_state:
                    sys.stdout.write(
                        render_frame(playback, geometry, terminal_input.palette)
                    )
                    sys.stdout.flush()
                    previous_frame_state = frame_state
                advancing = not playback.paused and not playback.finished
                timeout = (
                    max(0, min(0.25, deadline - time.monotonic()))
                    if advancing
                    else 0.25
                )
                ready, _, _ = select.select([keyboard_descriptor], [], [], timeout)
                if ready:
                    data = os.read(keyboard_descriptor, 4096)
                    if not data:
                        return
                    keys = terminal_input.feed(data)
                else:
                    keys = terminal_input.finish_escape()
                for key in keys:
                    previous_countdown = playback.countdown_seconds
                    if not playback.handle_key(key):
                        return
                    if (
                        key in (" ", "p", "P", "r", "R")
                        or (
                            key in ("+", "=", "-", "_")
                            and not playback.countdown_seconds
                        )
                        or (previous_countdown and not playback.countdown_seconds)
                    ):
                        deadline = time.monotonic() + playback.frame_delay
                if (
                    not playback.paused
                    and not playback.finished
                    and time.monotonic() >= deadline
                ):
                    playback.advance_frame()
                    deadline = time.monotonic() + playback.frame_delay
        finally:
            sys.stdout.write(clear_word_image())
            sys.stdout.flush()
