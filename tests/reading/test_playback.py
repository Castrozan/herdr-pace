import pytest

from herdr_pace.reading.actions import ReaderAction
from herdr_pace.reading.playback import ReaderPlayback
from herdr_pace.reading.word import ReadingWord


def test_pause_resume_restart_and_replay():
    playback = ReaderPlayback([ReadingWord("One"), ReadingWord("two.")], 400)
    assert playback.paused
    playback.apply(ReaderAction.TOGGLE)
    assert not playback.paused
    assert playback.countdown_seconds == 3
    playback.apply(ReaderAction.TOGGLE)
    assert playback.paused
    assert playback.countdown_seconds == 0
    playback.apply(ReaderAction.TOGGLE)
    assert playback.countdown_seconds == 3
    playback.position = 1
    playback.apply(ReaderAction.RESTART)
    assert playback.position == 0
    assert playback.countdown_seconds == 3
    playback.position = 2
    assert playback.finished
    playback.apply(ReaderAction.TOGGLE)
    assert not playback.finished
    assert playback.countdown_seconds == 3


def test_countdown_finishes_before_advancing_the_first_word():
    playback = ReaderPlayback([ReadingWord("One"), ReadingWord("two.")], 400)
    playback.advance_frame()
    assert playback.position == 0
    playback.apply(ReaderAction.TOGGLE)
    for remaining in (3, 2, 1):
        assert playback.countdown_seconds == remaining
        assert playback.frame_delay == 1
        assert playback.position == 0
        playback.advance_frame()
    assert playback.countdown_seconds == 0
    assert playback.frame_delay == pytest.approx(0.15)
    playback.advance_frame()
    assert playback.position == 1


def test_pausing_during_reading_resumes_with_a_countdown():
    playback = ReaderPlayback(
        [ReadingWord("One"), ReadingWord("two.")], 400, paused=False, position=1
    )
    playback.apply(ReaderAction.TOGGLE)
    playback.advance_frame()
    assert playback.position == 1
    playback.apply(ReaderAction.TOGGLE)
    assert playback.countdown_seconds == 3
    assert playback.position == 1


def test_speed_changes_are_bounded():
    playback = ReaderPlayback([ReadingWord("Word")], 400)
    for _ in range(100):
        playback.apply(ReaderAction.FASTER)
    assert playback.words_per_minute == 2000
    for _ in range(100):
        playback.apply(ReaderAction.SLOWER)
    assert playback.words_per_minute == 50


def test_sentence_punctuation_gets_a_reading_pause():
    playback = ReaderPlayback([ReadingWord("Word"), ReadingWord("sentence.")], 400)
    assert playback.word_delay == pytest.approx(0.15)
    playback.position = 1
    assert playback.word_delay == pytest.approx(0.375)


def test_empty_reply_is_finished():
    playback = ReaderPlayback([], 400)
    assert playback.finished
    assert playback.word == ""
    playback.apply(ReaderAction.TOGGLE)
    playback.apply(ReaderAction.RESTART)
    assert playback.paused
    assert playback.countdown_seconds == 0


@pytest.mark.parametrize("duration", [0, 1, 5, 10])
def test_configured_countdown_applies_to_start_resume_restart_and_replay(duration):
    playback = ReaderPlayback(
        [ReadingWord("One"), ReadingWord("two")],
        400,
        countdown_duration_seconds=duration,
    )
    for action in (ReaderAction.TOGGLE, ReaderAction.RESTART):
        playback.apply(action)
        assert playback.countdown_seconds == duration
        assert not playback.paused
        playback.apply(ReaderAction.TOGGLE)
    playback.position = 2
    playback.apply(ReaderAction.TOGGLE)
    assert playback.position == 0
    assert playback.countdown_seconds == duration
    if duration == 0:
        assert playback.frame_delay == pytest.approx(0.15)


def test_countdown_adjustment_is_bounded_and_does_not_start_playback():
    playback = ReaderPlayback([ReadingWord("Word")], 400)
    for _ in range(20):
        playback.apply(ReaderAction.LONGER_COUNTDOWN)
    assert playback.countdown_duration_seconds == 10
    for _ in range(20):
        playback.apply(ReaderAction.SHORTER_COUNTDOWN)
    assert playback.countdown_duration_seconds == 0
    assert playback.paused
    assert playback.countdown_seconds == 0
    assert playback.words_per_minute == 400


def test_changing_active_countdown_preserves_elapsed_seconds():
    playback = ReaderPlayback([ReadingWord("Word")], 400)
    playback.apply(ReaderAction.TOGGLE)
    playback.advance_frame()
    playback.apply(ReaderAction.LONGER_COUNTDOWN)
    assert playback.countdown_duration_seconds == 4
    assert playback.countdown_seconds == 3
    for _ in range(3):
        playback.apply(ReaderAction.SHORTER_COUNTDOWN)
    assert playback.countdown_seconds == 0
    assert not playback.paused
    assert playback.position == 0
    playback.apply(ReaderAction.LONGER_COUNTDOWN)
    assert playback.countdown_seconds == 0
