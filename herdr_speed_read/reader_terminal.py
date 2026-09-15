import fcntl
import struct
import sys
import termios
import tty
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass(frozen=True)
class TerminalGeometry:
    columns: int
    rows: int
    cell_width: int = 8
    cell_height: int = 16

    @classmethod
    def read(cls, descriptor: int) -> "TerminalGeometry":
        rows, columns, pixel_width, pixel_height = struct.unpack(
            "HHHH", fcntl.ioctl(descriptor, termios.TIOCGWINSZ, b"\0" * 8)
        )
        return cls(
            max(1, columns),
            max(1, rows),
            min(64, max(1, pixel_width // max(1, columns))) if pixel_width else 8,
            min(128, max(1, pixel_height // max(1, rows))) if pixel_height else 16,
        )


def clear_current_line() -> None:
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()


@contextmanager
def open_keyboard_terminal() -> Iterator[int]:
    try:
        keyboard_terminal = open("/dev/tty", "rb", buffering=0)
    except OSError:
        print("Error: speed-read requires an interactive terminal.", file=sys.stderr)
        raise SystemExit(1) from None

    with keyboard_terminal:
        keyboard_descriptor = keyboard_terminal.fileno()
        original_settings = termios.tcgetattr(keyboard_descriptor)
        try:
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()
            tty.setraw(keyboard_descriptor)
            yield keyboard_descriptor
        finally:
            try:
                termios.tcsetattr(
                    keyboard_descriptor, termios.TCSADRAIN, original_settings
                )
            finally:
                sys.stdout.write("\033[?25h")
                sys.stdout.flush()
