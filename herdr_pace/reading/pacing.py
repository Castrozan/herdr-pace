from dataclasses import dataclass

from .actions import ReaderAction
from .playback import ReaderPlayback


@dataclass
class ReadingClock:
    playback: ReaderPlayback
    deadline: float = 0.0
    visible: bool = False

    @property
    def active(self) -> bool:
        return self.visible and not self.playback.paused and not self.playback.finished

    def presented(self, now: float) -> None:
        if not self.visible:
            self.visible = True
            self.deadline = now + self.playback.frame_delay

    def apply(self, action: ReaderAction, now: float) -> None:
        previous_delay = self.playback.frame_delay
        previous_countdown = self.playback.countdown_seconds
        self.playback.apply(action)
        if action in (ReaderAction.FASTER, ReaderAction.SLOWER):
            if self.playback.showing_break:
                self.deadline += self.playback.frame_delay - previous_delay
                return
            if self.playback.countdown_seconds:
                return
        elif action not in (ReaderAction.TOGGLE, ReaderAction.RESTART):
            if not previous_countdown or self.playback.countdown_seconds:
                return
        self.deadline = now + self.playback.frame_delay

    def advance(self, now: float) -> bool:
        if not self.active or now < self.deadline:
            return False
        self.playback.advance_frame()
        self.deadline = now + self.playback.frame_delay
        return True
