from hypothesis import given
from hypothesis import strategies as st
from wcwidth import wcswidth

from herdr_pace.reading.actions import ReaderAction
from herdr_pace.reading.content import reading_words, word_fragments
from herdr_pace.reading.playback import ReaderPlayback


@given(st.lists(st.sampled_from([*ReaderAction, None]), max_size=200))
def test_arbitrary_reading_actions_keep_state_in_bounds(actions):
    playback = ReaderPlayback(reading_words("First\n\nSecond  \nThird."), 400)
    for action in actions:
        if action is None:
            playback.advance_frame()
        else:
            playback.apply(action)
        assert 0 <= playback.position <= len(playback.words)
        assert 50 <= playback.words_per_minute <= 2000
        assert (
            0 <= playback.countdown_seconds <= playback.countdown_duration_seconds <= 10
        )
        assert playback.frame_delay > 0
        assert not (playback.finished and playback.showing_break)


@given(
    st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "M", "S")), max_size=200
    )
)
def test_word_fragmentation_preserves_unicode_without_overflow(word):
    fragments = word_fragments(word)
    assert "".join(fragments) == word
    assert all(wcswidth(fragment) <= 24 for fragment in fragments)
