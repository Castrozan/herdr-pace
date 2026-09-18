import re

import pyte
import pytest

from herdr_pace.reading.content import reading_words
from herdr_pace.reading.playback import ReaderPlayback
from herdr_pace.terminal.palette import TerminalPalette


def visible_output(output):
    return re.sub(r"\x1b_G.*?\x1b\\", "", output.getvalue())


@pytest.mark.parametrize(
    "palette", [None, TerminalPalette((247, 246, 245), (193, 112, 19))]
)
async def test_controls_stay_fixed_through_reading_pause_restart_and_replay(
    reader, palette
):
    playback = ReaderPlayback(
        reading_words("First\n\nSecond  \nThird."), 2000, countdown_duration_seconds=0
    )
    async with reader(playback, palette) as running:
        opening = visible_output(running.output)
        assert "Space play/pause" in opening
        assert "3 words" in opening
        assert playback.paused
        await running.press(" ")
        await running.until(lambda: playback.finished)
        assert playback.finished
        await running.press(" ")
        await running.press(" ")
        await running.press("r")
        after = visible_output(running.output)[len(opening) :]
        assert "Space" not in after
        assert "WPM" not in after
        assert "3 words" not in after


@pytest.mark.parametrize("speed,countdown", [(50, 0), (950, 9), (1000, 10), (2000, 3)])
async def test_setting_labels_keep_their_columns(reader, speed, countdown):
    playback = ReaderPlayback(
        reading_words("Hello"), speed, countdown_duration_seconds=countdown
    )
    async with reader(playback) as running:
        heading = running.view.heading()
        assert heading.index("WPM") == 5
        assert heading.index("countdown") == 14
        assert "Paused" not in running.output.getvalue()
        await running.press("+]")
        assert playback.words_per_minute == min(2000, speed + 50)
        assert playback.countdown_duration_seconds == min(10, countdown + 1)


async def test_heading_and_total_are_centered_in_actual_terminal_output(reader):
    playback = ReaderPlayback(reading_words("First second third"), 400)
    async with reader(playback) as running:
        screen = pyte.Screen(61, 9)
        pyte.Stream(screen).feed(visible_output(running.output))
        heading = running.view.heading()
        assert screen.display[1].index("WPM") == (
            61 - len(heading)
        ) // 2 + heading.index("WPM")
        assert screen.display[5].index("3 words") == (61 - len("3 words")) // 2
