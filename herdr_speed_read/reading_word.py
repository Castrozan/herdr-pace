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
