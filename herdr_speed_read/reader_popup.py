import os
import select
import sys
import time

from wcwidth import wcswidth

from .reader_playback import ReaderPlayback
from .reader_terminal import open_keyboard_terminal
from .word_rendering import format_word_with_orp_highlight


def centered_line(text: str, width: int) -> str:
    text = text[:width]
    return " " * max(0, (width - wcswidth(text)) // 2) + text


def render_frame(playback: ReaderPlayback, width: int, height: int) -> str:
    middle = max(2, height // 2)
    status = "Done" if playback.finished else "Paused" if playback.paused else "Reading"
    progress = min(playback.position + 1, len(playback.words))
    heading = f"{status}  ·  {playback.words_per_minute} WPM"
    if not playback.words:
        word = centered_line("No completed reply in this pane yet.", width)
        heading = "Speed reader"
    elif playback.finished:
        word = centered_line("Finished. Press R to read again.", width)
    else:
        word = format_word_with_orp_highlight(playback.word, 1, width)
    lines = (
        (max(1, middle - 2), centered_line(heading, width)),
        (middle, word),
        (
            min(height - 1, middle + 2),
            centered_line(f"{progress} / {len(playback.words)}", width),
        ),
        (
            height,
            centered_line("Space pause  +/- speed  R restart  Q/Esc close", width),
        ),
    )
    return "\033[2J" + "".join(f"\033[{row};1H{text}" for row, text in lines)


def display_popup(playback: ReaderPlayback) -> None:
    with open_keyboard_terminal() as keyboard_descriptor:
        deadline = time.monotonic() + playback.word_delay
        previous_frame_state = None
        while True:
            width, height = os.get_terminal_size(keyboard_descriptor)
            frame_state = (
                playback.position,
                playback.words_per_minute,
                playback.paused,
                width,
                height,
            )
            if frame_state != previous_frame_state:
                sys.stdout.write(render_frame(playback, width, height))
                sys.stdout.flush()
                previous_frame_state = frame_state
            advancing = not playback.paused and not playback.finished
            timeout = (
                max(0, min(0.25, deadline - time.monotonic())) if advancing else 0.25
            )
            ready, _, _ = select.select([keyboard_descriptor], [], [], timeout)
            if ready:
                key = os.read(keyboard_descriptor, 1).decode("utf-8", errors="ignore")
                if not key or not playback.handle_key(key):
                    return
                deadline = time.monotonic() + playback.word_delay
            elif advancing and time.monotonic() >= deadline:
                playback.position += 1
                deadline = time.monotonic() + playback.word_delay
