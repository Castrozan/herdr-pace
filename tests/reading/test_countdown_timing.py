import pytest

from herdr_pace.reading.actions import ReaderAction
from herdr_pace.reading.content import reading_words
from herdr_pace.reading.pacing import ReadingClock
from herdr_pace.reading.playback import ReaderPlayback


@pytest.mark.parametrize("duration", [0, 1, 3, 10])
def test_countdown_and_first_word_receive_full_intervals(duration):
    playback = ReaderPlayback(
        reading_words("First second"), 400, countdown_duration_seconds=duration
    )
    clock = ReadingClock(playback)
    clock.apply(ReaderAction.TOGGLE, 0)
    assert not clock.advance(100)
    clock.presented(100)
    for remaining in range(duration, 0, -1):
        assert playback.countdown_seconds == remaining
        assert not clock.advance(clock.deadline - 0.001)
        assert clock.advance(clock.deadline)
    assert playback.position == 0
    assert clock.deadline == pytest.approx(100 + duration + 0.15)
    clock.advance(clock.deadline)
    assert playback.position == 1


@pytest.mark.parametrize(
    "action",
    [
        ReaderAction.FASTER,
        ReaderAction.SLOWER,
        ReaderAction.LONGER_COUNTDOWN,
        ReaderAction.SHORTER_COUNTDOWN,
    ],
)
def test_adjusting_active_countdown_does_not_reset_its_tick(action):
    clock = ReadingClock(ReaderPlayback(reading_words("First second"), 400))
    clock.apply(ReaderAction.TOGGLE, 0)
    clock.presented(0)
    clock.apply(action, 0.5)
    assert clock.deadline == 1
    clock.advance(1)
    assert clock.deadline == 2


def test_removing_remaining_countdown_starts_a_full_word_interval():
    clock = ReadingClock(
        ReaderPlayback(reading_words("First second"), 400, countdown_duration_seconds=1)
    )
    clock.apply(ReaderAction.TOGGLE, 0)
    clock.presented(0)
    clock.apply(ReaderAction.SHORTER_COUNTDOWN, 0.5)
    assert clock.playback.countdown_seconds == 0
    assert clock.deadline == pytest.approx(0.65)


@pytest.mark.parametrize("separator,intervals", [("\n\n", 4), ("  \n", 2)])
@pytest.mark.parametrize(
    "action,speed", [(ReaderAction.FASTER, 450), (ReaderAction.SLOWER, 350)]
)
def test_changing_speed_during_break_preserves_elapsed_time(
    separator, intervals, action, speed
):
    clock = ReadingClock(
        ReaderPlayback(
            reading_words("First" + separator + "Second"),
            400,
            countdown_duration_seconds=0,
        )
    )
    clock.apply(ReaderAction.TOGGLE, 0)
    clock.presented(0)
    clock.advance(0.15)
    clock.apply(action, 0.25)
    assert clock.playback.showing_break
    assert clock.deadline == pytest.approx(0.15 + intervals * 60 / speed)
    clock.advance(clock.deadline)
    assert clock.playback.reading_text == "Second"
    assert clock.deadline == pytest.approx(0.15 + (intervals + 1) * 60 / speed)


def test_speed_change_can_finish_an_elapsed_break_immediately():
    clock = ReadingClock(
        ReaderPlayback(
            reading_words("First\n\nSecond"), 400, countdown_duration_seconds=0
        )
    )
    clock.apply(ReaderAction.TOGGLE, 0)
    clock.presented(0)
    clock.advance(0.15)
    for _ in range(32):
        clock.apply(ReaderAction.FASTER, 0.5)
    assert clock.advance(0.5)
    assert clock.playback.reading_text == "Second"
    assert clock.deadline == pytest.approx(0.53)
