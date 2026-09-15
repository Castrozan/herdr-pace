from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.layout import HSplit, Window, WindowAlign
from prompt_toolkit.layout.containers import DynamicContainer
from prompt_toolkit.layout.controls import FormattedTextControl

from .graphics import clear_word_image, render_word_graphics
from .text import render_terminal_word


class ReaderView:
    def __init__(self, playback, geometry, palette=None):
        self.playback = playback
        self.geometry = geometry
        self.palette = palette
        self.previous_image = None
        self.image = ""
        self.layout = DynamicContainer(self.container)
        self.reading_layout = HSplit(
            [
                Window(
                    height=lambda: max(0, self.geometry().rows // 2 - 3),
                    always_hide_cursor=True,
                ),
                self.line(self.heading),
                Window(
                    FormattedTextControl(self.word),
                    height=3,
                    always_hide_cursor=True,
                    wrap_lines=False,
                ),
                self.line(
                    lambda: f"{len(playback.words)} word"
                    + ("" if len(playback.words) == 1 else "s")
                ),
                Window(always_hide_cursor=True),
                self.line(
                    "Space play/pause  +/- WPM  [/] countdown  R restart  Esc quit"
                ),
            ]
        )

    def line(self, text):
        return Window(
            FormattedTextControl(text),
            height=1,
            align=WindowAlign.CENTER,
            always_hide_cursor=True,
            wrap_lines=False,
        )

    def container(self):
        geometry = self.geometry()
        if geometry.columns < 12 or geometry.rows < 7:
            return self.line("Enlarge pane to read.")
        return self.reading_layout

    def heading(self):
        return (
            f"{self.playback.words_per_minute:4} WPM  "
            f"{self.playback.countdown_duration_seconds:2}s countdown"
        )

    def word(self):
        width = self.geometry().columns
        if not self.playback.words:
            return "\n" + "No completed reply in this pane yet.".center(width)
        if self.palette:
            return ""
        return ANSI("\n" + render_terminal_word(self.playback.reading_text, width))

    def before_render(self, application):
        geometry = self.geometry()
        signature = (self.playback.reading_text, geometry, self.palette)
        self.image = ""
        if (
            signature != self.previous_image
            or application.renderer.last_rendered_screen is None
        ):
            self.image = clear_word_image()
            if (
                self.palette
                and self.playback.words
                and geometry.columns >= 12
                and geometry.rows >= 7
            ):
                self.image = render_word_graphics(
                    self.playback.reading_text,
                    geometry.columns,
                    max(1, geometry.rows // 2 - 1),
                    geometry.cell_width,
                    geometry.cell_height,
                    self.palette,
                )
            self.previous_image = signature
        application.output.write_raw("\033[?2026h")

    def after_render(self, application):
        application.output.write_raw("\0337" + self.image + "\0338\033[?2026l")
        application.output.flush()
