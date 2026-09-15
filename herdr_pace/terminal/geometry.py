import fcntl
import struct
import termios
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
