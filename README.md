# Herdr Speed Reader

Read a completed AI reply one word at a time in a small centered Herdr popup. A stop hook captures the reply; you open the reader when you are ready. It never opens automatically or reads terminal scrollback.

## Install

Requires macOS or Linux, Nix with flakes enabled, and a Herdr build with plugin popup support. The plugin uses the `popup` placement API; a version number alone may not identify whether a fork includes that API.

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

| Key         | Action                                  |
| ----------- | --------------------------------------- |
| Space or P  | Pause or resume; replay after finishing |
| + or -      | Change speed by 50 words per minute     |
| R           | Restart the reply                       |
| Q or Escape | Close the popup                         |

The reader opens paused. Press Space to begin a three-second countdown: 3, 2, 1, then the first word. Resuming and restarting use the same countdown; Space cancels it and returns to paused. Changing speed during the countdown does not delay the start.

Reading starts at 400 words per minute, remembers your selected speed, and pauses longer at punctuation. Speed stays between 50 and 2,000 words per minute. The reader shows progress and waits at the end so you can replay or close it.

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

The hook inherits `HERDR_PANE_ID` and `HERDR_SOCKET_PATH` from the AI pane. Subagent events are ignored. If another stop guard can reject a draft, run capture after that guard accepts the reply. Capture failures never return a blocking exit status.

Only the latest reply per pane and server is stored, with at most 64 saved replies. Each reply is limited to 1 MiB; an oversized reply leaves the previous saved reply intact. Files are private to the user and live under Herdr's plugin state directory. The reader loads a snapshot when opened and does not poll transcripts or follow new replies while you read.

## Development

```sh
nix develop
python -m pytest tests
nix build
herdr plugin link ./result/share/herdr-plugin
```

The Nix package exports `herdr-speed-read` and a ready-to-link manifest under `share/herdr-plugin`.
