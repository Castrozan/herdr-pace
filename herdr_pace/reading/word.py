import re
from dataclasses import dataclass
from enum import Enum


class ReadingBreak(Enum):
    NONE = ""
    LINE = "↵"
    PARAGRAPH = "¶"


@dataclass(frozen=True)
class ReadingWord:
    text: str
    break_before: ReadingBreak = ReadingBreak.NONE


def has_trailing_punctuation(word: str) -> bool:
    return bool(re.search(r"[.!?,;:\u2014\u2013-]$", word))
