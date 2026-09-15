from enum import Enum, auto


class ReaderAction(Enum):
    TOGGLE = auto()
    RESTART = auto()
    FASTER = auto()
    SLOWER = auto()
    SHORTER_COUNTDOWN = auto()
    LONGER_COUNTDOWN = auto()
