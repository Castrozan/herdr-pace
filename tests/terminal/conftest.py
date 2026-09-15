import asyncio
import io
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from prompt_toolkit.data_structures import Size
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output.vt100 import Vt100_Output

from herdr_pace.terminal.application import reader_application
from herdr_pace.terminal.geometry import TerminalGeometry


@pytest.fixture
def reader():
    @asynccontextmanager
    async def run(playback, palette=None, geometry=TerminalGeometry(61, 9)):
        rendered = asyncio.Event()
        output = io.StringIO()
        with create_pipe_input() as keyboard:
            application, view = reader_application(
                playback,
                keyboard,
                Vt100_Output(
                    output,
                    lambda: Size(geometry.rows, geometry.columns),
                    term="xterm-256color",
                    enable_cpr=False,
                ),
                lambda: geometry,
                palette,
            )
            application.after_render += lambda _: rendered.set()
            task = asyncio.create_task(
                application.run_async(set_exception_handler=False)
            )
            await asyncio.wait_for(rendered.wait(), 2)

            async def press(keys):
                rendered.clear()
                keyboard.send_text(keys)
                await asyncio.wait_for(rendered.wait(), 2)

            async def until(predicate):
                while not predicate():
                    rendered.clear()
                    await asyncio.wait_for(rendered.wait(), 2)

            try:
                yield SimpleNamespace(
                    application=application,
                    view=view,
                    output=output,
                    press=press,
                    until=until,
                    rendered=rendered,
                )
            finally:
                if not application.is_done:
                    application.exit()
                await asyncio.wait_for(task, 2)

    return run
