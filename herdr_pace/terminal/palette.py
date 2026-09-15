import re
from dataclasses import dataclass

from prompt_toolkit.input.ansi_escape_sequences import ANSI_SEQUENCES

COLOR_QUERY = "\033]10;?\033\\\033]4;1;?\033\\"
COLOR_REPORT = re.compile(
    r"(10|4;1);rgb:([0-9a-fA-F]{1,4})/([0-9a-fA-F]{1,4})/([0-9a-fA-F]{1,4})"
)


@dataclass(frozen=True)
class TerminalPalette:
    foreground: tuple[int, int, int]
    focus: tuple[int, int, int]


class PaletteParser:
    def __init__(self, keyboard_parser, changed=lambda palette: None):
        self.keyboard_parser = keyboard_parser
        self.changed = changed
        self.colors = {}
        self.pending = ""
        self.in_report = ""
        self.truncated = False
        self.previous = ""

    @property
    def palette(self):
        if "10" in self.colors and "4;1" in self.colors:
            return TerminalPalette(self.colors["10"], self.colors["4;1"])
        return None

    def report(self):
        match = COLOR_REPORT.fullmatch(self.pending[2:].rstrip("\x07\x1b\\"))
        if match and not self.truncated:
            self.colors[match[1]] = tuple(
                round(int(part, 16) * 255 / (16 ** len(part) - 1))
                for part in match.groups()[1:]
            )
            self.changed(self.palette)
        self.pending = ""
        self.in_report = ""
        self.truncated = False

    def feed(self, data: str) -> None:
        for character in data:
            if self.in_report:
                if len(self.pending) < 256:
                    self.pending += character
                else:
                    self.truncated = True
                if self.in_report == "csi":
                    if "@" <= character <= "~":
                        if self.pending in ANSI_SEQUENCES and not self.truncated:
                            self.keyboard_parser.feed(self.pending)
                        self.pending = ""
                        self.in_report = ""
                        self.truncated = False
                elif character == "\x07" or (
                    self.previous == "\x1b" and character == "\\"
                ):
                    self.report()
                self.previous = character
                continue
            if self.pending:
                if character in ("]", "["):
                    self.pending += character
                    self.in_report = "osc" if character == "]" else "csi"
                    continue
                self.keyboard_parser.feed(self.pending)
                self.pending = ""
            if character == "\x1b":
                self.pending = character
            else:
                self.keyboard_parser.feed(character)

    def flush(self) -> None:
        if self.pending == "\x1b":
            self.keyboard_parser.feed(self.pending)
            self.pending = ""
        self.keyboard_parser.flush()
