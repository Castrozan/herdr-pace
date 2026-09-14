import sys
import termios
import tty
from collections.abc import Iterator
from contextlib import contextmanager


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
