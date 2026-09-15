import re

import pytest
from prompt_toolkit.formatted_text import to_formatted_text

from herdr_pace.reading.content import reading_words
from herdr_pace.reading.playback import ReaderPlayback
from herdr_pace.terminal.geometry import TerminalGeometry
from herdr_pace.terminal.palette import TerminalPalette


@pytest.mark.parametrize("key", ["q", "Q", "\x1b", "\x03"])
async def test_quit_keys_close_reader(reader, key):
    async with reader(ReaderPlayback(reading_words("Word"), 400)) as running:
        await running.press(key)
        assert running.application.is_done


@pytest.mark.parametrize("remaining", [3, 2, 1])
async def test_countdown_uses_only_the_central_word(reader, remaining):
    playback = ReaderPlayback(
        reading_words("First second"), 400, countdown_seconds=remaining
    )
    async with reader(playback) as running:
        text = "".join(
            fragment[1] for fragment in to_formatted_text(running.view.word())
        )
        assert text.strip() == str(remaining)
        assert "Starting in" not in running.output.getvalue()


async def test_empty_reply_explains_what_is_missing(reader):
    async with reader(ReaderPlayback([], 400)) as running:
        assert "No completed reply in this pane yet." in running.output.getvalue()
        await running.press(" r")
        assert running.view.playback.paused


async def test_small_pane_does_not_emit_graphics(reader):
    async with reader(
        ReaderPlayback(reading_words("Hello"), 400),
        TerminalPalette((255, 255, 255), (255, 0, 0)),
        TerminalGeometry(12, 5),
    ) as running:
        assert "Enlarge pan" in running.output.getvalue()
        assert "a=T" not in running.output.getvalue()


async def test_large_word_is_drawn_once_with_controls_in_first_sync_frame(reader):
    async with reader(
        ReaderPlayback(reading_words("Reading"), 400),
        TerminalPalette((255, 255, 255), (255, 0, 0)),
    ) as running:
        frames = re.findall(
            r"\x1b\[\?2026h(.*?)\x1b\[\?2026l", running.output.getvalue(), re.S
        )
        assert len(frames) == 1
        assert "Space play/pause" in frames[0]
        assert "a=T" in frames[0] and "r=3" in frames[0]
        assert frames[0].count("a=T") == 1
