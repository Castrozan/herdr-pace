import re
from dataclasses import dataclass, field

COLOR_QUERY = "\033]10;?\033\\\033]4;1;?\033\\"
COLOR_REPORT = re.compile(
    rb"(10|4;1);rgb:([0-9a-fA-F]{1,4})/([0-9a-fA-F]{1,4})/([0-9a-fA-F]{1,4})"
)
READER_KEYS = b" qQpPrR+-=_[]\x03"


@dataclass(frozen=True)
class TerminalPalette:
    foreground: tuple[int, int, int]
    focus: tuple[int, int, int]


@dataclass
class TerminalInput:
    foreground: tuple[int, int, int] | None = None
    focus: tuple[int, int, int] | None = None
    pending: bytearray = field(default_factory=bytearray)
    sequence_kind: str = ""
    previous_byte: int = 0
    truncated: bool = False

    @property
    def palette(self) -> TerminalPalette | None:
        if self.foreground is None or self.focus is None:
            return None
        return TerminalPalette(self.foreground, self.focus)

    def read_color(self, report: bytes) -> None:
        match = COLOR_REPORT.fullmatch(report)
        if match is None:
            return
        color = tuple(
            round(int(part, 16) * 255 / (16 ** len(part) - 1))
            for part in match.groups()[1:]
        )
        if match[1] == b"10":
            self.foreground = color
        else:
            self.focus = color

    def finish_escape(self) -> list[str]:
        if self.sequence_kind != "escape":
            return []
        self.sequence_kind = ""
        self.pending.clear()
        return ["\x1b"]

    def feed(self, data: bytes) -> list[str]:
        keys = []
        for byte in data:
            if self.sequence_kind in ("osc", "csi"):
                complete = (
                    byte == 7 or (self.previous_byte == 27 and byte == 92)
                    if self.sequence_kind == "osc"
                    else 64 <= byte <= 126
                )
                if len(self.pending) < 256:
                    self.pending.append(byte)
                else:
                    self.truncated = True
                self.previous_byte = byte
                if complete:
                    if self.sequence_kind == "osc" and not self.truncated:
                        ending_length = 1 if byte == 7 else 2
                        self.read_color(bytes(self.pending[2:-ending_length]))
                    self.pending.clear()
                    self.sequence_kind = ""
                    self.truncated = False
                continue
            if self.sequence_kind == "escape":
                if byte in (91, 93):
                    self.sequence_kind = "osc" if byte == 93 else "csi"
                    self.pending.append(byte)
                    self.previous_byte = byte
                    continue
                keys.extend(self.finish_escape())
            if byte == 27:
                self.sequence_kind = "escape"
                self.pending.append(byte)
            elif byte in READER_KEYS:
                keys.append(chr(byte))
        return keys
