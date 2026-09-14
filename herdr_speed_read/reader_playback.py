from dataclasses import dataclass

from .reader_settings import MAX_WPM, MIN_WPM, PUNCTUATION_DELAY_MULTIPLIER, WPM_STEP
from .word_rendering import has_trailing_punctuation


@dataclass
class ReaderPlayback:
    words: list[str]
    words_per_minute: int
    position: int = 0
    paused: bool = False

    @property
    def finished(self) -> bool:
        return self.position >= len(self.words)

    @property
    def word(self) -> str:
        if not self.words:
            return ""
        return self.words[min(self.position, len(self.words) - 1)]

    @property
    def word_delay(self) -> float:
        multiplier = (
            PUNCTUATION_DELAY_MULTIPLIER if has_trailing_punctuation(self.word) else 1
        )
        return 60 / self.words_per_minute * multiplier

    def handle_key(self, key: str) -> bool:
        if key in ("q", "Q", "\x1b", "\x03"):
            return False
        if key in (" ", "p", "P"):
            if self.finished:
                self.position = 0
                self.paused = False
            else:
                self.paused = not self.paused
        elif key in ("+", "="):
            self.words_per_minute = min(MAX_WPM, self.words_per_minute + WPM_STEP)
        elif key in ("-", "_"):
            self.words_per_minute = max(MIN_WPM, self.words_per_minute - WPM_STEP)
        elif key in ("r", "R"):
            self.position = 0
            self.paused = False
        return True
