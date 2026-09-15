from dataclasses import dataclass

from .reader_settings import (
    DEFAULT_COUNTDOWN_SECONDS,
    MAX_COUNTDOWN_SECONDS,
    MAX_WPM,
    MIN_WPM,
    PUNCTUATION_DELAY_MULTIPLIER,
    WPM_STEP,
)
from .word_rendering import has_trailing_punctuation


@dataclass
class ReaderPlayback:
    words: list[str]
    words_per_minute: int
    position: int = 0
    paused: bool = True
    countdown_seconds: int = 0
    countdown_duration_seconds: int = DEFAULT_COUNTDOWN_SECONDS

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

    @property
    def frame_delay(self) -> float:
        return 1.0 if self.countdown_seconds else self.word_delay

    def start_countdown(self) -> None:
        if not self.words:
            return
        self.paused = False
        self.countdown_seconds = self.countdown_duration_seconds

    def adjust_countdown(self, seconds: int) -> None:
        duration = max(
            0, min(MAX_COUNTDOWN_SECONDS, self.countdown_duration_seconds + seconds)
        )
        if self.countdown_seconds:
            self.countdown_seconds = max(
                0, self.countdown_seconds + duration - self.countdown_duration_seconds
            )
        self.countdown_duration_seconds = duration

    def advance_frame(self) -> None:
        if self.paused or self.finished:
            return
        if self.countdown_seconds:
            self.countdown_seconds -= 1
        else:
            self.position += 1

    def handle_key(self, key: str) -> bool:
        if key in ("q", "Q", "\x1b", "\x03"):
            return False
        if key in (" ", "p", "P"):
            if self.finished:
                self.position = 0
                self.start_countdown()
            elif self.paused:
                self.start_countdown()
            else:
                self.paused = True
                self.countdown_seconds = 0
        elif key in ("+", "="):
            self.words_per_minute = min(MAX_WPM, self.words_per_minute + WPM_STEP)
        elif key in ("-", "_"):
            self.words_per_minute = max(MIN_WPM, self.words_per_minute - WPM_STEP)
        elif key == "[":
            self.adjust_countdown(-1)
        elif key == "]":
            self.adjust_countdown(1)
        elif key in ("r", "R"):
            self.position = 0
            self.start_countdown()
        return True
