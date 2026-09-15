from herdr_pace.reading.content import reading_words
from herdr_pace.reading.playback import ReaderPlayback


async def test_framework_drives_countdown_and_keeps_first_word_visible(reader):
    playback = ReaderPlayback(
        reading_words("First second"), 50, countdown_duration_seconds=1
    )
    async with reader(playback) as running:
        await running.press(" ")
        assert playback.countdown_seconds == 1
        await running.press("+")
        assert playback.countdown_seconds == 1
        await running.until(lambda: playback.countdown_seconds == 0)
        assert playback.countdown_seconds == 0
        assert playback.position == 0
        await running.until(lambda: playback.position == 1)
        assert playback.position == 1
