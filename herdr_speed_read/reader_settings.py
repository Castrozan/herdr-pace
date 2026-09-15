from dataclasses import dataclass

DEFAULT_WPM = 400
MIN_WPM = 50
MAX_WPM = 2000
WPM_STEP = 50
DEFAULT_FOCUS_COLOR = 1
DEFAULT_CENTER_WIDTH = 40
PUNCTUATION_DELAY_MULTIPLIER = 2.5
DEFAULT_COUNTDOWN_SECONDS = 3
MAX_COUNTDOWN_SECONDS = 10


@dataclass(frozen=True)
class ReaderSettings:
    words_per_minute: int = DEFAULT_WPM
    countdown_duration_seconds: int = DEFAULT_COUNTDOWN_SECONDS
