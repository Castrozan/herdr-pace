import os
import select
import sys
import time

from wcwidth import wcswidth

from .reader_playback import ReaderPlayback
from .reader_terminal import TerminalGeometry, open_keyboard_terminal


def centered_line(text: str, width: int) -> str:
    text = text[:width]
    return " " * max(0, (width - wcswidth(text)) // 2) + text


def render_frame(playback: ReaderPlayback, geometry: TerminalGeometry) -> str:
    from .word_graphics import clear_word_image, render_word_graphics

    width, height = geometry.columns, geometry.rows
    middle = max(2, height // 2)
    status = "Done" if playback.finished else "Paused" if playback.paused else "Reading"
    if playback.countdown_seconds:
        status = "Starting in"
    progress = min(playback.position + 1, len(playback.words))
    heading = f"{status}  ·  {playback.words_per_minute} WPM"
    graphics = clear_word_image()
    if not playback.words:
        word = centered_line("No completed reply in this pane yet.", width)
        heading = "Speed reader"
    elif width < 12 or height < 7:
        word = centered_line("Enlarge pane to read.", width)
    elif playback.finished:
        word = centered_line("Finished. Press R to read again.", width)
    else:
        word = ""
        reading_text = (
            str(playback.countdown_seconds)
            if playback.countdown_seconds
            else playback.word
        )
        graphics = render_word_graphics(
            reading_text,
            width,
            max(1, middle - 1),
            geometry.cell_width,
            geometry.cell_height,
        )
    playback_control = "play" if playback.paused or playback.finished else "pause"
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
                f"Space {playback_control}  +/- speed  R restart  Q/Esc close", width
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
            previous_frame_state = None
            while True:
                geometry = TerminalGeometry.read(keyboard_descriptor)
                frame_state = (
                    playback.position,
                    playback.words_per_minute,
                    playback.paused,
                    playback.countdown_seconds,
                    geometry,
                )
                if frame_state != previous_frame_state:
                    sys.stdout.write(render_frame(playback, geometry))
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
                    key = os.read(keyboard_descriptor, 1).decode(
                        "utf-8", errors="ignore"
                    )
                    if not key or not playback.handle_key(key):
                        return
                    if not playback.countdown_seconds or key in (
                        " ",
                        "p",
                        "P",
                        "r",
                        "R",
                    ):
                        deadline = time.monotonic() + playback.frame_delay
                elif advancing and time.monotonic() >= deadline:
                    playback.advance_frame()
                    deadline = time.monotonic() + playback.frame_delay
        finally:
            sys.stdout.write(clear_word_image())
            sys.stdout.flush()
