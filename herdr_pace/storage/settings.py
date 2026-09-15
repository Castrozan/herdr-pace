import json
from dataclasses import asdict

from herdr_pace.reading.settings import (
    DEFAULT_COUNTDOWN_SECONDS,
    DEFAULT_WPM,
    MAX_COUNTDOWN_SECONDS,
    MAX_WPM,
    MIN_WPM,
    ReaderSettings,
)

from .files import atomic_write
from .paths import state_directory


def load_reader_settings() -> ReaderSettings:
    try:
        with (state_directory() / "settings.json").open("rb") as source:
            settings = json.loads(source.read(4096))
    except (OSError, ValueError):
        return ReaderSettings()
    if not isinstance(settings, dict):
        return ReaderSettings()
    speed = settings.get("words_per_minute")
    if type(speed) is not int or not MIN_WPM <= speed <= MAX_WPM:
        speed = DEFAULT_WPM
    countdown = settings.get("countdown_duration_seconds")
    if type(countdown) is not int or not 0 <= countdown <= MAX_COUNTDOWN_SECONDS:
        countdown = DEFAULT_COUNTDOWN_SECONDS
    return ReaderSettings(speed, countdown)


def save_reader_settings(settings: ReaderSettings) -> None:
    atomic_write(state_directory() / "settings.json", asdict(settings))
