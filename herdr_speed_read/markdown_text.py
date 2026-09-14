import re
import unicodedata
from html.parser import HTMLParser

from markdown_it import MarkdownIt
from wcwidth import wcwidth

TERMINAL_ESCAPE = re.compile(
    r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)|[@-_])"
)


class HtmlText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fragments = []

    def handle_data(self, data):
        self.fragments.append(data)


def token_text(token) -> str:
    if token.children:
        return "".join(token_text(child) for child in token.children)
    if token.type in ("softbreak", "hardbreak"):
        return " "
    if token.type in ("html_inline", "html_block"):
        parser = HtmlText()
        parser.feed(token.content)
        return "".join(parser.fragments)
    if token.type in ("text", "code_inline", "code_block", "fence"):
        return token.content
    return ""


def reading_words(markdown: str) -> list[str]:
    text = TERMINAL_ESCAPE.sub("", markdown)
    text = "".join(
        character
        for character in text
        if character.isspace() or not unicodedata.category(character).startswith("C")
    )
    parser = MarkdownIt("commonmark").enable("table")
    words = " ".join(token_text(token) for token in parser.parse(text)).split()
    frames = []
    for word in words:
        fragment = ""
        cells = 0
        for character in word:
            character_width = max(0, wcwidth(character))
            if cells + character_width > 24:
                frames.append(fragment)
                fragment = ""
                cells = 0
            fragment += character
            cells += character_width
        if fragment:
            frames.append(fragment)
    return frames
