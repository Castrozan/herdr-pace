import json
import os
import subprocess

import click

from .reading.settings import ReaderSettings
from .storage.replies import MAX_REPLY_BYTES, load_reply
from .storage.settings import load_reader_settings, save_reader_settings


@click.group(help="Read completed AI replies at your own pace in Herdr.")
@click.version_option(package_name="herdr-pace", prog_name="Herdr Pace")
def cli():
    pass


@cli.command(help="Capture a completed reply from a JSON Stop event on stdin.")
def capture():
    from .capture.events import capture_hook

    try:
        payload = json.loads(
            click.get_binary_stream("stdin").read(MAX_REPLY_BYTES * 2 + 4096)
        )
        if isinstance(payload, dict):
            capture_hook(payload)
    except (OSError, ValueError, TypeError) as failure:
        click.echo(f"Herdr Pace: {failure}", err=True)


@cli.command(name="open", help="Open Herdr Pace for the current AI pane.")
def open_reader():
    from .capture.herdr import open_reader_pane

    try:
        open_reader_pane()
    except (OSError, ValueError, subprocess.SubprocessError) as failure:
        raise click.ClickException(str(failure)) from None


@cli.command(name="read", help="Read the captured reply inside the plugin popup.")
def read_reply():
    from .reading.content import reading_words
    from .reading.playback import ReaderPlayback
    from .terminal.application import display_popup

    original = load_reader_settings()
    playback = ReaderPlayback(
        reading_words(load_reply(os.environ.get("HERDR_PACE_REPLY_KEY", ""))),
        original.words_per_minute,
        countdown_duration_seconds=original.countdown_duration_seconds,
    )
    try:
        display_popup(playback)
    except OSError as failure:
        raise click.ClickException(str(failure)) from None
    finally:
        settings = ReaderSettings(
            playback.words_per_minute, playback.countdown_duration_seconds
        )
        if settings != original:
            save_reader_settings(settings)


@cli.command(
    help="Install capture hooks in existing Claude Code and Codex configurations."
)
def install_hooks():
    from .capture.installation import install_hooks as install

    try:
        install()
    except (OSError, ValueError, TypeError) as failure:
        raise click.ClickException(str(failure)) from None


def main():
    cli(prog_name="herdr-pace")
