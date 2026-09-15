import pytest
from prompt_toolkit.input.vt100_parser import Vt100Parser
from prompt_toolkit.keys import Keys

from herdr_pace.terminal.palette import PaletteParser, TerminalPalette


@pytest.fixture
def parser():
    keys = []
    return PaletteParser(Vt100Parser(keys.append)), keys


def test_fragmented_reports_are_separate_from_keyboard_input(parser):
    terminal, keys = parser
    for fragment in (
        " \x1b]10;rgb:f7f7/f6",
        "f6/f5f5\x1b",
        "\\\x1b]4;1;rgb:c1/70/13\x07q",
    ):
        terminal.feed(fragment)
    assert [key.data for key in keys] == [" ", "q"]
    assert terminal.palette == TerminalPalette((247, 246, 245), (193, 112, 19))


def test_color_changes_update_palette_without_becoming_keys(parser):
    terminal, keys = parser
    terminal.feed("\x1b]10;rgb:fff/fff/fff\x07\x1b]4;1;rgb:f/0/0\x07")
    assert terminal.palette == TerminalPalette((255, 255, 255), (255, 0, 0))
    terminal.feed("\x1b]10;rgb:1111/2222/3333\x1b\\")
    assert terminal.palette.foreground == (17, 34, 51)
    assert keys == []


@pytest.mark.parametrize(
    "report",
    [
        "\x1b]10;rgb:no/color/here\x07",
        "\x1b[6;16;8t",
        "\x1b[?2026;1$y",
        "\x1b[?1;2c",
        "\x1b[>1;4000;0c",
        "\x1b[0n",
        "\x1b]" + "0" * 2048 + "\x07",
    ],
)
def test_terminal_reports_cannot_become_commands(parser, report):
    terminal, keys = parser
    terminal.feed("[" + report + "]")
    assert [key.data for key in keys] == ["[", "]"]
    assert terminal.palette is None
    assert len(terminal.pending) <= 256


def test_escape_flush_and_arrow_keys_use_framework_parser(parser):
    terminal, keys = parser
    terminal.feed("\x1b")
    assert keys == []
    terminal.flush()
    terminal.feed("\x1b[A")
    assert [key.key for key in keys] == [Keys.Escape, Keys.Up]


def test_unterminated_report_has_bounded_storage(parser):
    terminal, keys = parser
    terminal.feed("\x1b]" + "0" * 2048)
    assert len(terminal.pending) <= 256
    terminal.feed("\x07q")
    assert [key.data for key in keys] == ["q"]
