import asyncio
import sys
from functools import partial

from prompt_toolkit.application import Application
from prompt_toolkit.input import create_input
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Layout
from prompt_toolkit.output.vt100 import Vt100_Output

from herdr_pace.reading.actions import ReaderAction
from herdr_pace.reading.pacing import ReadingClock

from .geometry import TerminalGeometry
from .graphics import clear_word_image
from .palette import COLOR_QUERY, PaletteParser
from .startup import prepare_terminal
from .view import ReaderView


def reader_application(playback, terminal_input, output, geometry, palette=None):
    view = ReaderView(playback, geometry, palette)
    clock = ReadingClock(playback)
    bindings = KeyBindings()
    timer = None

    def schedule(application):
        nonlocal timer
        if timer:
            timer.cancel()
        if clock.active and not application.is_done:
            timer = asyncio.get_running_loop().call_at(
                clock.deadline, tick, application
            )

    def tick(application):
        if not application.is_done and clock.advance(asyncio.get_running_loop().time()):
            application.invalidate()
            schedule(application)

    def act(action, event):
        clock.apply(action, asyncio.get_running_loop().time())
        schedule(event.app)

    def rendered(application):
        view.after_render(application)
        clock.presented(asyncio.get_running_loop().time())
        schedule(application)

    for action, keys in (
        (ReaderAction.TOGGLE, (" ", "p", "P")),
        (ReaderAction.RESTART, ("r", "R")),
        (ReaderAction.FASTER, ("+", "=")),
        (ReaderAction.SLOWER, ("-", "_")),
        (ReaderAction.SHORTER_COUNTDOWN, ("[",)),
        (ReaderAction.LONGER_COUNTDOWN, ("]",)),
    ):
        for key in keys:
            bindings.add(key)(partial(act, action))
    for key in ("q", "Q", "escape", "c-c"):
        bindings.add(key)(lambda event: event.app.exit())
    application = Application(
        layout=Layout(view.layout),
        key_bindings=bindings,
        input=terminal_input,
        output=output,
        full_screen=True,
        erase_when_done=True,
        before_render=view.before_render,
        after_render=rendered,
        include_default_pygments_style=False,
        max_render_postpone_time=0,
        terminal_size_polling_interval=None,
    )
    application.ttimeoutlen = 0.05
    return application, view


async def run_reader(playback, terminal_input):
    parser = PaletteParser(terminal_input.vt100_parser)
    terminal_input.vt100_parser = parser
    output = Vt100_Output.from_pty(sys.stdout)
    output.enable_cpr = False

    def geometry():
        return TerminalGeometry.read(terminal_input.fileno())

    with terminal_input.raw_mode():
        keys = (
            await prepare_terminal(terminal_input, output, parser)
            if playback.words
            else []
        )
        if terminal_input.closed or any(
            key.key in ("q", "Q", Keys.Escape, Keys.ControlC) for key in keys
        ):
            return
        application, view = reader_application(
            playback, terminal_input, output, geometry, parser.palette
        )

        def palette_changed(palette):
            if view.palette and palette != view.palette:
                view.palette = palette
                application.invalidate()

        parser.changed = palette_changed

        async def refresh_palette():
            while True:
                await asyncio.sleep(1)
                output.write_raw(COLOR_QUERY)
                output.flush()

        def start():
            application.key_processor.feed_multiple(keys)
            if view.palette:
                application.create_background_task(refresh_palette())

        try:
            await application.run_async(pre_run=start, set_exception_handler=False)
        except EOFError:
            pass
        finally:
            output.write_raw(clear_word_image() + "\033[?2026l\033[?25h")
            output.flush()


def display_popup(playback):
    terminal_input = create_input(always_prefer_tty=True)
    try:
        asyncio.run(run_reader(playback, terminal_input))
    finally:
        terminal_input.close()
