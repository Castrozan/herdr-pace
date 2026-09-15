import base64
import io
from functools import lru_cache

import cairo
import gi

from herdr_pace.terminal.palette import TerminalPalette
from herdr_pace.terminal.text import compute_optimal_recognition_point

READER_IMAGE_ID = 1


@lru_cache(maxsize=64)
def render_word_image(
    word: str, columns: int, cell_width: int, cell_height: int, palette: TerminalPalette
) -> bytes:
    gi.require_version("Pango", "1.0")
    gi.require_version("PangoCairo", "1.0")
    gi.require_foreign("cairo")
    from gi.repository import Pango, PangoCairo

    width = columns * max(24, cell_width)
    height = 3 * max(48, cell_height)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    context = cairo.Context(surface)
    layout = PangoCairo.create_layout(context)
    layout.set_text(word, -1)
    font = Pango.FontDescription("DejaVu Sans Mono")
    font.set_absolute_size(height * Pango.SCALE)
    layout.set_font_description(font)
    focus_position = compute_optimal_recognition_point(word)
    focus_start = len(word[:focus_position].encode())
    focus_end = len(word[: focus_position + 1].encode())
    attributes = Pango.AttrList()
    highlight = Pango.attr_foreground_new(*(channel * 257 for channel in palette.focus))
    highlight.start_index = focus_start
    highlight.end_index = focus_end
    attributes.insert(highlight)
    layout.set_attributes(attributes)
    ink, logical = layout.get_pixel_extents()
    focus = layout.index_to_pos(focus_start)
    focus_center = (focus.x + focus.width / 2) / Pango.SCALE
    extent = max(focus_center - ink.x, ink.x + ink.width - focus_center, 1)
    scale = min(
        1, (height - 4) / max(logical.height, ink.height, 1), (width / 2 - 4) / extent
    )
    font.set_absolute_size(height * scale * Pango.SCALE)
    layout.set_font_description(font)
    ink, _ = layout.get_pixel_extents()
    focus = layout.index_to_pos(focus_start)
    focus_center = (focus.x + focus.width / 2) / Pango.SCALE
    context.translate(
        round(width / 2 - focus_center),
        round((height - ink.height) / 2 - ink.y),
    )
    context.set_source_rgb(*(channel / 255 for channel in palette.foreground))
    PangoCairo.show_layout(context, layout)
    output = io.BytesIO()
    surface.write_to_png(output)
    return output.getvalue()


def clear_word_image() -> str:
    return f"\033_Ga=d,d=I,i={READER_IMAGE_ID},q=2\033\\"


def render_word_graphics(
    word: str,
    columns: int,
    row: int,
    cell_width: int,
    cell_height: int,
    palette: TerminalPalette,
) -> str:
    payload = base64.b64encode(
        render_word_image(word, columns, cell_width, cell_height, palette)
    ).decode()
    commands = [clear_word_image(), f"\033[{row};1H"]
    for offset in range(0, len(payload), 4096):
        chunk = payload[offset : offset + 4096]
        more = int(offset + 4096 < len(payload))
        parameters = (
            f"a=T,f=100,i={READER_IMAGE_ID},p=1,c={columns},r=3,C=1,q=2,"
            if offset == 0
            else ""
        )
        commands.append(f"\033_G{parameters}m={more};{chunk}\033\\")
    return "".join(commands)
