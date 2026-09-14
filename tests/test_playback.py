import pytest

from herdr_speed_read.reader_playback import ReaderPlayback


def test_pause_resume_restart_and_replay():
    playback = ReaderPlayback(["One", "two."], 400)
    playback.handle_key(" ")
    assert playback.paused
    playback.handle_key(" ")
    assert not playback.paused
    playback.position = 1
    playback.handle_key("r")
    assert playback.position == 0
    playback.position = 2
    assert playback.finished
    playback.handle_key(" ")
    assert not playback.finished


def test_speed_changes_are_bounded():
    playback = ReaderPlayback(["Word"], 400)
    for _ in range(100):
        playback.handle_key("+")
    assert playback.words_per_minute == 2000
    for _ in range(100):
        playback.handle_key("-")
    assert playback.words_per_minute == 50


@pytest.mark.parametrize("key", ["q", "Q", "\x1b", "\x03"])
def test_quit_keys_close_reader(key):
    assert not ReaderPlayback(["Word"], 400).handle_key(key)


def test_sentence_punctuation_gets_a_reading_pause():
    playback = ReaderPlayback(["Word", "sentence."], 400)
    assert playback.word_delay == pytest.approx(0.15)
    playback.position = 1
    assert playback.word_delay == pytest.approx(0.375)


def test_empty_reply_is_finished():
    playback = ReaderPlayback([], 400)
    assert playback.finished
    assert playback.word == ""
