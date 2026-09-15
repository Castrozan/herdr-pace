import pytest

from herdr_pace.reading.actions import ReaderAction
from herdr_pace.reading.content import reading_words
from herdr_pace.reading.playback import ReaderPlayback
from herdr_pace.reading.word import ReadingBreak


@pytest.mark.parametrize(
    "source,expected",
    [
        ("First\n\n  Second", ["", "¶"]),
        ("First\nSecond", ["", ""]),
        ("First  \nSecond", ["", "↵"]),
        ("First\\\nSecond", ["", "↵"]),
        ("# Heading\n\nParagraph", ["", "¶"]),
        ("- First\n- Second\n\n> Quote", ["", "¶", "¶"]),
        ("Before\n\n```\nFirst\nSecond\n```\n\nAfter", ["", "¶", "↵", "¶"]),
        ("| A | B |\n| --- | --- |\n| C | D |", ["", "", "↵", ""]),
        ("First<br>Second", ["", "↵"]),
        ("<p>First</p><p>Second</p>", ["", "¶"]),
        ("\n\nFirst\n\n\n\nSecond\n\n", ["", "¶"]),
        ("**First** [Second](https://example.test)", ["", ""]),
        ("First\n\n---\n\nSecond", ["", "¶"]),
        ("Literal ¶ ↵", ["", "", ""]),
    ],
)
def test_markdown_boundaries_follow_document_structure(source, expected):
    assert [word.break_before.value for word in reading_words(source)] == expected


def test_long_word_carries_its_boundary_only_on_the_first_fragment():
    words = reading_words("First\n\n" + "界" * 30)
    assert "".join(word.text for word in words[1:]) == "界" * 30
    assert [word.break_before for word in words] == [
        ReadingBreak.NONE,
        ReadingBreak.PARAGRAPH,
        ReadingBreak.NONE,
        ReadingBreak.NONE,
    ]


@pytest.mark.parametrize("duration", [0, 3])
def test_pause_resume_restart_and_replay_at_a_paragraph(duration):
    playback = ReaderPlayback(
        reading_words("First\n\nSecond"), 400, countdown_duration_seconds=duration
    )
    playback.apply(ReaderAction.TOGGLE)
    for _ in range(duration + 1):
        playback.advance_frame()
    assert playback.reading_text == "¶"
    playback.apply(ReaderAction.TOGGLE)
    playback.advance_frame()
    assert playback.reading_text == "¶"
    playback.apply(ReaderAction.TOGGLE)
    for _ in range(duration):
        playback.advance_frame()
    assert playback.reading_text == "Second"
    assert playback.frame_delay == pytest.approx(0.15)
    playback.apply(ReaderAction.RESTART)
    for _ in range(duration):
        playback.advance_frame()
    assert playback.reading_text == "First"
    playback.advance_frame()
    playback.advance_frame()
    assert playback.reading_text == "Second"
    playback.advance_frame()
    assert playback.finished
    assert playback.reading_text == "Second"
    playback.apply(ReaderAction.TOGGLE)
    for _ in range(duration):
        playback.advance_frame()
    assert playback.reading_text == "First"


@pytest.mark.parametrize("words_per_minute", [50, 200, 400, 800, 2000])
@pytest.mark.parametrize("separator,word_intervals", [("\n\n", 4), ("  \n", 2)])
@pytest.mark.parametrize("next_word", ["Next", "Next."])
def test_break_pacing_follows_wpm_independently_of_word_punctuation(
    words_per_minute, separator, word_intervals, next_word
):
    playback = ReaderPlayback(
        reading_words("First" + separator + next_word),
        words_per_minute,
        paused=False,
    )
    playback.advance_frame()
    assert playback.showing_break
    assert playback.frame_delay == pytest.approx(60 / words_per_minute * word_intervals)
    playback.countdown_seconds = 3
    assert playback.frame_delay == 1.0
