import base64
import io
import re

import cairo
import pytest

from herdr_speed_read.word_graphics import render_word_graphics, render_word_image


def image_pixels(word, width=64, cell_width=11, cell_height=23):
    image = cairo.ImageSurface.create_from_png(
        io.BytesIO(render_word_image(word, width, cell_width, cell_height))
    )
    pixels = bytes(image.get_data())
    colored = []
    for row in range(image.get_height()):
        for column in range(image.get_width()):
            offset = row * image.get_stride() + column * 4
            blue, green, red, alpha = pixels[offset : offset + 4]
            if alpha:
                colored.append((column, row, red, green, blue))
    return image, colored


def test_word_is_three_rows_high_with_centered_red_focus():
    image, colored = image_pixels("Reading")
    assert image.get_width() == 64 * 11
    assert image.get_height() == 3 * 23
    assert max(pixel[1] for pixel in colored) - min(pixel[1] for pixel in colored) > 40
    red_columns = [
        column for column, _, red, green, blue in colored if red > blue > green
    ]
    assert (min(red_columns) + max(red_columns)) / 2 == pytest.approx(352, abs=3)


@pytest.mark.parametrize("word", ["ação", "cafe\u0301", "世界你好", "🍲", "W" * 24])
@pytest.mark.parametrize("width", [20, 64])
def test_unicode_and_long_words_fit_without_touching_edges(word, width):
    image, colored = image_pixels(word, width)
    assert colored
    assert min(pixel[0] for pixel in colored) > 0
    assert max(pixel[0] for pixel in colored) < image.get_width() - 1
    assert min(pixel[1] for pixel in colored) > 0
    assert max(pixel[1] for pixel in colored) < image.get_height() - 1


def test_graphics_transfer_reconstructs_image_and_replaces_previous_word():
    frame = render_word_graphics("Reading", 64, 4, 11, 23)
    commands = re.findall(r"\x1b_G(.*?)\x1b\\", frame)
    assert commands[0] == "a=d,d=I,i=1,q=2"
    assert "\x1b[4;1H" in frame
    assert "a=T,f=100,i=1,p=1,c=64,r=3,C=1,q=2" in commands[1]
    payloads = [command.split(";", 1)[1] for command in commands[1:]]
    assert all(len(payload) <= 4096 for payload in payloads)
    assert all("m=1;" in command for command in commands[1:-1])
    assert "m=0;" in commands[-1]
    assert base64.b64decode("".join(payloads)) == render_word_image(
        "Reading", 64, 11, 23
    )
