import re
import unicodedata
from html.parser import HTMLParser

from markdown_it import MarkdownIt
from wcwidth import wcwidth

from .reading_word import ReadingBreak, ReadingWord

TERMINAL_ESCAPE = re.compile(
    r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)|[@-_])"
)


class HtmlText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fragments = []

    def handle_data(self, data):
        self.fragments.append(data)

    def handle_starttag(self, tag, attributes):
        if tag == "br":
            self.fragments.append("\n")
        elif tag in ("p", "div"):
            self.fragments.append("\n\n")

    def handle_endtag(self, tag):
        if tag in ("p", "div"):
            self.fragments.append("\n\n")


def token_text(token) -> str:
    if token.children:
        return "".join(token_text(child) for child in token.children)
    if token.type in ("paragraph_open", "heading_open"):
        return "\n\n"
    if token.type in ("hardbreak", "tr_open"):
        return "\n"
    if token.type in ("softbreak", "th_close", "td_close"):
        return " "
    if token.type in ("html_inline", "html_block"):
        parser = HtmlText()
        parser.feed(token.content)
        return "".join(parser.fragments)
    if token.type in ("code_block", "fence"):
        return "\n\n" + token.content + "\n\n"
    if token.type in ("text", "code_inline"):
        return token.content
    return ""


def word_fragments(word: str) -> list[str]:
    fragments = []
    fragment = ""
    cells = 0
    for character in word:
        character_width = max(0, wcwidth(character))
        if cells + character_width > 24:
            fragments.append(fragment)
            fragment = ""
            cells = 0
        fragment += character
        cells += character_width
    if fragment:
        fragments.append(fragment)
    return fragments


def reading_words(markdown: str) -> list[ReadingWord]:
    text = TERMINAL_ESCAPE.sub("", markdown)
    text = "".join(
        character
        for character in text
        if character.isspace() or not unicodedata.category(character).startswith("C")
    )
    parser = MarkdownIt("commonmark").enable("table")
    normalized = "".join(token_text(token) for token in parser.parse(text))
    frames = []
    break_before = ReadingBreak.NONE
    for line in normalized.split("\n"):
        if not line.strip():
            if frames:
                break_before = ReadingBreak.PARAGRAPH
            continue
        for word in line.split():
            for fragment in word_fragments(word):
                frames.append(ReadingWord(fragment, break_before))
                break_before = ReadingBreak.NONE
        break_before = ReadingBreak.LINE
    return frames
