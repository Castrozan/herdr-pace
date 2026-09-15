import pytest

from herdr_pace.reading.content import reading_words


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("## Result\n\n**Fixed** the _reader_.", "Result Fixed the reader."),
        ("- First\n- Second\n\n> Quoted", "First Second Quoted"),
        ("Read [the report](https://example.test/report).", "Read the report."),
        (
            "Use `git status`.\n\n```sh\ngit diff --stat\n```",
            "Use git status. git diff --stat",
        ),
        ("| Name | Count |\n| --- | --- |\n| Tests | 12 |", "Name Count Tests 12"),
        ("<b>Ready</b> &amp; done.", "Ready & done."),
        ("![System diagram](https://example.test/image.png)", "System diagram"),
        ("\033[31mFixed\033[0m.\x1b]0;private title\x07", "Fixed."),
        ("Olá 世界 😀\u200b", "Olá 世界 😀"),
        ("", ""),
    ],
)
def test_normalization_preserves_readable_content(source, expected):
    assert " ".join(word.text for word in reading_words(source)) == expected
