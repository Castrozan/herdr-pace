from contextlib import nullcontext

import pytest

from herdr_speed_read import reader_popup, word_graphics
from herdr_speed_read.markdown_text import reading_words
from herdr_speed_read.reader_playback import ReaderPlayback
from herdr_speed_read.reader_popup import render_frame
from herdr_speed_read.reader_terminal import TerminalGeometry
from herdr_speed_read.reading_word import ReadingBreak
from herdr_speed_read.terminal_colors import TerminalPalette


def test_paragraph_transition_is_visible_without_counting_as_a_word():
    playback = ReaderPlayback(
        reading_words("First\n\nSecond"), 400, countdown_duration_seconds=0
    )
    playback.handle_key(" ")
    playback.advance_frame()
    frame = render_frame(playback, TerminalGeometry(61, 9), None, True)
    assert "¶" in frame
    assert "2 words" in frame
    assert not playback.finished


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
    playback.handle_key(" ")
    for _ in range(duration + 1):
        playback.advance_frame()
    assert playback.reading_text == "¶"
    playback.handle_key(" ")
    playback.advance_frame()
    assert playback.reading_text == "¶"
    playback.handle_key(" ")
    for _ in range(duration):
        playback.advance_frame()
    assert playback.reading_text == "Second"
    assert playback.frame_delay == pytest.approx(0.15)
    playback.handle_key("r")
    for _ in range(duration):
        playback.advance_frame()
    assert playback.reading_text == "First"
    playback.advance_frame()
    playback.advance_frame()
    assert playback.reading_text == "Second"
    playback.advance_frame()
    assert playback.finished
    assert playback.reading_text == "Second"
    playback.handle_key(" ")
    for _ in range(duration):
        playback.advance_frame()
    assert playback.reading_text == "First"


@pytest.mark.parametrize("separator,marker", [("\n\n", "¶"), ("  \n", "↵")])
def test_break_uses_the_existing_large_font_and_terminal_palette(
    separator, marker, monkeypatch
):
    playback = ReaderPlayback(
        reading_words("First" + separator + "Second"), 400, paused=False
    )
    playback.advance_frame()
    rendered = []
    palette = TerminalPalette((247, 246, 245), (193, 112, 19))
    monkeypatch.setattr(
        word_graphics,
        "render_word_graphics",
        lambda *arguments: rendered.append(arguments) or "",
    )
    render_frame(playback, TerminalGeometry(61, 9), palette, True)
    assert rendered == [(marker, 61, 3, 8, 16, palette)]


@pytest.mark.parametrize(
    "adjustment,adjustment_at",
    [("", 0.6), ("+", 0.6), ("-", 0.6), ("]", 0.6), ("+" * 32, 0.9)],
)
def test_break_timing_keeps_full_word_intervals(monkeypatch, adjustment, adjustment_at):
    now = 0.0
    inputs = [(0.4, " "), (adjustment_at, adjustment), (2.8, "q")]
    frames = []

    def wait_for_input(readers, writers, errors, timeout):
        nonlocal now
        if inputs[0][0] <= now + timeout:
            now = inputs[0][0]
            return readers, [], []
        now += timeout
        return [], [], []

    def render(playback, geometry, palette, redraw_controls):
        frames.append((now, playback.reading_text, playback.paused))
        return ""

    monkeypatch.setattr(reader_popup, "open_keyboard_terminal", lambda: nullcontext(3))
    monkeypatch.setattr(reader_popup.time, "monotonic", lambda: now)
    monkeypatch.setattr(
        reader_popup.TerminalGeometry,
        "read",
        lambda descriptor: TerminalGeometry(61, 9),
    )
    monkeypatch.setattr(
        reader_popup.os, "read", lambda *args: (inputs.pop(0)[1] or "x").encode()
    )
    monkeypatch.setattr(reader_popup.select, "select", wait_for_input)
    monkeypatch.setattr(reader_popup, "render_frame", render)
    reader_popup.display_popup(
        ReaderPlayback(
            reading_words("First\n\nSecond  \nThird."),
            400,
            countdown_duration_seconds=0,
        )
    )
    words_per_minute = min(
        2000, 400 + 50 * adjustment.count("+") - 50 * adjustment.count("-")
    )
    interval = 60 / words_per_minute
    paragraph_end = max(0.55 + 4 * interval, adjustment_at)
    expected = [
        ("First", 0.4),
        ("¶", 0.55),
        ("Second", paragraph_end),
        ("↵", paragraph_end + interval),
        ("Third.", paragraph_end + 3 * interval),
    ]
    for text, timestamp in expected:
        assert next(
            time for time, word, paused in frames if word == text and not paused
        ) == pytest.approx(timestamp)


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
