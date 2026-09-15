import asyncio

from prompt_toolkit.keys import Keys

from .palette import COLOR_QUERY


async def prepare_terminal(terminal_input, output, palette_parser):
    keys = []
    ready = asyncio.Event()

    def receive():
        keys.extend(terminal_input.read_keys())
        if (
            terminal_input.closed
            or palette_parser.palette
            or any(key.key in ("q", "Q", Keys.ControlC) for key in keys)
        ):
            ready.set()

    output.write_raw(COLOR_QUERY)
    output.flush()
    with terminal_input.attach(receive):
        try:
            await asyncio.wait_for(ready.wait(), 0.25)
        except TimeoutError:
            pass
    keys.extend(terminal_input.flush_keys())
    return keys
