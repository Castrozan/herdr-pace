# Herdr Speed Reader

Read a completed AI reply one word at a time in a small centered Herdr popup. A stop hook captures the reply; you open the reader when you are ready. It never opens automatically or reads terminal scrollback.

## Install

Requires macOS or Linux, Nix with flakes enabled, a terminal supporting [Kitty graphics](https://sw.kovidgoyal.net/kitty/graphics-protocol/), and a Herdr build with plugin popup and popup graphics support. The plugin uses the `popup` placement API; a version number alone may not identify whether a fork includes that API. Herdr's `terminal.kitty_graphics` setting must be enabled; supported builds enable it by default.

```sh
herdr plugin install Castrozan/herdr-speed-read
herdr plugin action invoke castrozan.speed-read.install-hooks
```

The second command adds capture hooks to existing Claude Code and Codex configuration directories. It preserves other settings, creates a backup, and refuses to overwrite symlinked configuration. Restart the AI session after installing hooks. For configuration managed by Nix or another tool, declare the hook in that configuration instead of running the installer.

Add a binding to Herdr's `config.toml`, then run `herdr server reload-config`:

```toml
[[keys.command]]
key = "prefix+f"
type = "plugin_action"
command = "castrozan.speed-read.read"
description = "speed-read the latest AI reply"
```

With Herdr's default prefix, press **Ctrl+B**, release, then **F** in the AI pane. The action is also available through `herdr plugin action invoke castrozan.speed-read.read`.

## Reading

| Key         | Action                                     |
| ----------- | ------------------------------------------ |
| Space or P  | Pause or resume; replay after finishing     |
| + or -      | Change speed by 50 words per minute         |
| [ or ]      | Shorten or lengthen countdown by one second |
| R           | Restart the reply                          |
| Q or Escape | Close the popup                            |

The reader opens paused. Press Space to begin a countdown, then the first word. The default is three seconds: 3, 2, 1. Use `[` and `]` to adjust it from 0 to 10 seconds; 0 skips the countdown. The chosen duration appears beside WPM and is remembered when you close the reader, just like reading speed. Resuming and restarting use the same duration; Space cancels the countdown and returns to paused.

Adjusting an active countdown preserves elapsed time. Changing its duration while reading applies to the next start without delaying the current word. Changing speed during the countdown does not delay the start.

The word and countdown use a large font occupying three terminal rows. Controls and the total word count stay at normal size. The focus letter stays centered; long words shrink to fit without clipping. Text uses the terminal's foreground and ANSI red colors, refreshed once per second through OSC color queries. Before its first frame, the reader waits up to 250 milliseconds for those colors and prepares the font. If the terminal does not answer in time, the reader uses ordinary terminal text until closed, so a late response cannot cause a sudden zoom. Fonts are included, with Unicode shaping and CJK and emoji fallback. Resizing the terminal keeps the word inside the popup.

Reading starts at 400 words per minute, remembers your selected speed, and pauses longer at punctuation. Speed stays between 50 and 2,000 words per minute. The footer always says `Space play/pause`, including when Space will replay a finished reply. The total word count stays fixed. Only the central word, countdown, or break cue updates during playback; controls are redrawn when you change settings or resize the pane. Settings labels stay aligned when their values change. The last word stays visible at the end so you can replay or close the reader.

Paragraphs, headings, and list items are separated by a `¶` cue lasting four word intervals (`240 / WPM` seconds). Explicit Markdown line breaks, code lines, and table rows use `↵` for two word intervals (`120 / WPM` seconds). At 400 WPM, these pauses last 0.6 and 0.3 seconds; doubling WPM halves both pauses. Changing speed during a cue adjusts its duration while preserving elapsed time. Ordinary wrapped lines flow continuously. These cues do not count as words, and the next word receives its full reading interval. Pausing during a cue and resuming runs your chosen countdown, then shows the next word.

Markdown formatting and terminal escapes are removed. Link labels, code, list text, table content, and Unicode text remain. Long identifiers continue across successive frames instead of being cut off. The reply is normalized locally, never summarized by a model.

## Capture integration

`herdr-speed-read capture` accepts a JSON stop event on stdin. Claude Code and Codex events can provide `last_assistant_message` or `transcript_path`. Other hook bridges, including OpenCode and Pi, can provide `reply_text`:

```json
{
  "hook_event_name": "Stop",
  "session_id": "session",
  "reply_text": "The completed reply."
}
```

The hook inherits `HERDR_PANE_ID` and `HERDR_SOCKET_PATH` from the AI pane. Subagent events and Codex temporary assistant runs with an explicitly null `transcript_path` are ignored, so internal conversation recaps cannot replace the saved reply. Transcript fallback selects completed answers and skips progress messages. Legitimate JSON replies are preserved. If another stop guard can reject a draft, run capture after that guard accepts the reply. Capture failures never return a blocking exit status.

Only the latest reply per pane and server is stored, with at most 64 saved replies. Each reply is limited to 1 MiB; an oversized reply leaves the previous saved reply intact. Files are private to the user and live under Herdr's plugin state directory. The reader loads a snapshot when opened and does not poll transcripts or follow new replies while you read.

## Development

```sh
nix develop
python -m pytest tests
nix build
herdr plugin link ./result/share/herdr-plugin
```

The Nix package exports `herdr-speed-read` and a ready-to-link manifest under `share/herdr-plugin`.
