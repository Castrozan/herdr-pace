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
    redraw_controls: bool,
) -> str:
    from .word_graphics import clear_word_image, render_word_graphics

    width, height = geometry.columns, geometry.rows
    middle = max(2, height // 2)
    heading = (
        f"{playback.words_per_minute:4} WPM  "
        f"{playback.countdown_duration_seconds:2}s countdown"
    )
    graphics = clear_word_image()
    if not playback.words:
        word = centered_line("No completed reply in this pane yet.", width)
    elif width < 12 or height < 7:
        word = centered_line("Enlarge pane to read.", width)
    else:
        reading_text = playback.reading_text
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
    controls = (
        (max(1, middle - 2), centered_line(heading, width)),
        (
            min(height - 1, middle + 2),
            centered_line(
                f"{len(playback.words)} word"
                + ("" if len(playback.words) == 1 else "s"),
                width,
            ),
        ),
        (
            height,
            centered_line(
                "Space play/pause  +/- WPM  [/] countdown  R restart  Esc quit",
                width,
            ),
        ),
    )
    surrounding_text = (
        "\033[2J" + "".join(f"\033[{row};1H{text}" for row, text in controls)
        if redraw_controls or width < 12 or height < 7
        else "".join(f"\033[{row};1H\033[2K" for row in range(middle - 1, middle + 2))
    )
    return (
        "\033[?2026h"
        + surrounding_text
        + f"\033[{middle};1H{word}"
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
            startup_deadline = time.monotonic() + 0.25
            graphics_enabled = None if playback.words else False
            previous_frame_state = None
            previous_controls_state = None
            while True:
                if (
                    graphics_enabled is not False
                    and time.monotonic() >= next_color_query
                ):
                    sys.stdout.write(COLOR_QUERY)
                    sys.stdout.flush()
                    next_color_query = time.monotonic() + 1.0
                geometry = TerminalGeometry.read(keyboard_descriptor)
                if graphics_enabled is None and (
                    terminal_input.palette is not None
                    or time.monotonic() >= startup_deadline
                ):
                    graphics_enabled = terminal_input.palette is not None
                palette = terminal_input.palette if graphics_enabled else None
                controls_state = (
                    playback.words_per_minute,
                    playback.countdown_duration_seconds,
                    geometry,
                )
                frame_state = (
                    playback.position,
                    playback.words_per_minute,
                    playback.paused,
                    playback.countdown_seconds,
                    playback.countdown_duration_seconds,
                    playback.showing_break,
                    geometry,
                    palette,
                )
                if graphics_enabled is not None and frame_state != previous_frame_state:
                    sys.stdout.write(
                        render_frame(
                            playback,
                            geometry,
                            palette,
                            controls_state != previous_controls_state,
                        )
                    )
                    sys.stdout.flush()
                    if previous_frame_state is None:
                        deadline = time.monotonic() + playback.frame_delay
                    previous_frame_state = frame_state
                    previous_controls_state = controls_state
                advancing = (
                    previous_frame_state is not None
                    and not playback.paused
                    and not playback.finished
                )
                timeout = (
                    max(0, min(0.25, deadline - time.monotonic()))
                    if advancing
                    else 0.25
                )
                if graphics_enabled is None:
                    timeout = min(timeout, max(0, startup_deadline - time.monotonic()))
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
                            and not playback.showing_break
                        )
                        or (previous_countdown and not playback.countdown_seconds)
                    ):
                        deadline = time.monotonic() + playback.frame_delay
                if (
                    previous_frame_state is not None
                    and not playback.paused
                    and not playback.finished
                    and time.monotonic() >= deadline
                ):
                    playback.advance_frame()
                    deadline = time.monotonic() + playback.frame_delay
        finally:
            sys.stdout.write(clear_word_image())
            sys.stdout.flush()
