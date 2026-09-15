import asyncio

import pytest
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from herdr_pace.terminal.palette import PaletteParser, TerminalPalette
from herdr_pace.terminal.startup import prepare_terminal


@pytest.mark.parametrize("response", [True, False])
async def test_startup_negotiates_colors_once_and_preserves_early_keys(response):
    with create_pipe_input() as keyboard:
        parser = PaletteParser(keyboard.vt100_parser)
        keyboard.vt100_parser = parser
        keyboard.send_text(" ")
        if response:
            keyboard.send_text("\x1b]10;rgb:fff/fff/fff\x07\x1b]4;1;rgb:f/0/0\x07")
        started = asyncio.get_running_loop().time()
        keys = await prepare_terminal(keyboard, DummyOutput(), parser)
        elapsed = asyncio.get_running_loop().time() - started
        assert [key.data for key in keys] == [" "]
        assert parser.palette == (
            TerminalPalette((255, 255, 255), (255, 0, 0)) if response else None
        )
        assert elapsed < 0.35
        if not response:
            assert elapsed >= 0.25
