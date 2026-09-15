# Development and design

```sh
nix develop
ruff check herdr_pace tests tools
ruff format --check herdr_pace tests tools
nix build
herdr plugin link ./result/share/herdr-plugin --enabled
```

`nix build` runs the test suite before producing the package. For a focused edit, run its test file with `python -m pytest path/to/test_file.py`. Reopen the reader after linking a build.

The README preview is rendered from actual application output. Regenerate it with `PYTHONPATH=. python tools/capture_preview.py` inside the development shell.

## Architecture

Herdr Pace uses a functional core with an imperative shell and a presentation model. Reading state and deadline calculations are deterministic and independent of terminal, capture, and storage adapters. The command entrypoints compose these responsibilities.

Reading owns content normalization, playback actions, saved-preference values, and pacing. Capture selects completed replies and integrates with Herdr and harness hooks. Storage owns private files and the rename migration. Terminal presentation translates reading state into the popup.

[prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/full_screen_apps.html) owns keybindings, terminal modes, layout, differential rendering, and application lifecycle. [Click](https://click.palletsprojects.com/) owns command parsing, help, and exit handling. Markdown parsing remains with markdown-it-py.

The terminal protocol extension is deliberately narrow. prompt_toolkit does not expose OSC color reports or a Kitty image widget. A parser decorator separates color reports from keyboard input; render callbacks place the Pango/Cairo word image inside a synchronized frame. Palette negotiation finishes before the first application frame. These are terminal concerns, not reading rules.

Textual and Urwid were also considered. Textual's widgets and Pilot tests suit richer interfaces, but this popup still needs custom color negotiation and graphics handling. prompt_toolkit supplies the lifecycle and incremental rendering this reader needs with fewer moving parts.

## Tests at the right boundary

- Parameterized tests cover countdowns, word intervals, break cues, capture selection, storage, and migration.
- Hypothesis explores action sequences and Unicode fragmentation invariants.
- prompt_toolkit's pipe input and pytest-asyncio exercise actual bindings and application rendering.
- Pexpect launches the real command in a pseudo-terminal to verify opening, early input, quit, and graphics fallback.
- Pixel tests check focus placement, terminal colors, Unicode shaping, and clipping.

Ruff enforces the reading domain's dependency boundary. CI builds and tests on Linux and macOS. Graphics and terminal behavior require the real-process checks; an in-memory framework test cannot prove them.

## Presentation and naming references

[herdr-reviewr](https://github.com/persiyanov/herdr-reviewr) and [herdr-file-viewer](https://github.com/smarzban/herdr-file-viewer) informed the README's order: show the user workflow, show the interface, then provide a complete installation path.

The public name is **Herdr Pace**. Repository, distribution, and executable use `herdr-pace`; Python imports use `herdr_pace`; the Herdr plugin ID is `castrozan.pace`. The Herdr prefix distinguishes it from unrelated projects named Pace. Previous identifiers remain only where migration requires them.
