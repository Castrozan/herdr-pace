from herdr_speed_read.terminal_colors import TerminalInput, TerminalPalette


def test_fragmented_color_reports_are_separate_from_keyboard_input():
    terminal = TerminalInput()
    assert terminal.feed(b" \x1b]10;rgb:f7f7/f6") == [" "]
    assert terminal.feed(b"f6/f5f5\x1b") == []
    assert terminal.feed(b"\\\x1b]4;1;rgb:c1/70/13\x07q") == ["q"]
    assert terminal.palette == TerminalPalette((247, 246, 245), (193, 112, 19))


def test_color_change_updates_palette_without_becoming_a_key():
    terminal = TerminalInput()
    terminal.feed(b"\x1b]10;rgb:fff/fff/fff\x07\x1b]4;1;rgb:f/0/0\x07")
    assert terminal.palette == TerminalPalette((255, 255, 255), (255, 0, 0))
    terminal.feed(b"\x1b]10;rgb:1111/2222/3333\x1b\\")
    assert terminal.palette.foreground == (17, 34, 51)


def test_unknown_or_malformed_reports_do_not_supply_colors_or_close_reader():
    terminal = TerminalInput()
    assert terminal.feed(b"\x1b]10;rgb:no/color/here\x07\x1b[6;16;8t+") == ["+"]
    assert terminal.palette is None


def test_escape_is_a_key_when_it_is_not_part_of_a_report():
    terminal = TerminalInput()
    assert terminal.feed(b"\x1b") == []
    assert terminal.finish_escape() == ["\x1b"]
    assert terminal.feed(b"r") == ["r"]


def test_unterminated_report_has_bounded_storage():
    terminal = TerminalInput()
    assert terminal.feed(b"\x1b]" + b"0" * 2048) == []
    assert len(terminal.pending) <= 256
    assert terminal.feed(b"\x07q") == ["q"]


def test_countdown_controls_are_not_confused_with_terminal_sequences():
    terminal = TerminalInput()
    assert terminal.feed(b"[\x1b[6;16;8t]\x1b]10;rgb:fff/fff/fff\x07") == ["[", "]"]
