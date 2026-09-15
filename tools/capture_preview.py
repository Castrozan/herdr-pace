import base64
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import cairo
import pexpect
import pyte

from herdr_pace.terminal.palette import COLOR_QUERY


def capture():
    with tempfile.TemporaryDirectory(prefix="herdr-pace-preview-") as directory:
        state = Path(directory)
        key = "a" * 64
        (state / "replies").mkdir()
        (state / "replies" / f"{key}.json").write_text(
            json.dumps({"text": "Read this at your own pace.\n\nOne idea at a time."})
        )
        environment = dict(
            os.environ,
            HERDR_PLUGIN_STATE_DIR=directory,
            HERDR_PACE_REPLY_KEY=key,
            TERM="xterm-256color",
        )
        with pexpect.spawn(
            sys.executable,
            ["-m", "herdr_pace", "read"],
            env=environment,
            dimensions=(9, 61),
            encoding="utf-8",
            timeout=5,
        ) as terminal:
            terminal.expect_exact(COLOR_QUERY)
            terminal.send(
                "\x1b]10;rgb:f7f7/f6f6/f5f5\x07\x1b]4;1;rgb:c1c1/7070/1313\x07"
            )
            terminal.expect_exact("\x1b[?2026l")
            frame = terminal.before
            terminal.send("q")
            terminal.expect(pexpect.EOF)
    return frame


def render(frame, destination):
    screen = pyte.Screen(61, 9)
    pyte.Stream(screen).feed(re.sub(r"\x1b_G.*?\x1b\\", "", frame, flags=re.S))
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 732, 216)
    context = cairo.Context(surface)
    context.set_source_rgb(35 / 255, 59 / 255, 77 / 255)
    context.paint()
    context.select_font_face("DejaVu Sans Mono")
    context.set_font_size(18)
    context.set_source_rgb(247 / 255, 246 / 255, 245 / 255)
    for row, line in enumerate(screen.display):
        for column, character in enumerate(line):
            if character != " ":
                context.move_to(column * 12 + 1, row * 24 + 19)
                context.show_text(character)
    commands = re.findall(r"\x1b_G([^;\x1b]*);(.*?)\x1b\\", frame, re.S)
    payload = "".join(data for parameters, data in commands)
    image = cairo.ImageSurface.create_from_png(io.BytesIO(base64.b64decode(payload)))
    context.save()
    context.translate(0, 48)
    context.scale(732 / image.get_width(), 72 / image.get_height())
    context.set_source_surface(image)
    context.paint()
    context.restore()
    surface.write_to_png(str(destination))


if __name__ == "__main__":
    render(capture(), Path("docs/reader.png"))
