# Capture and managed configuration

`herdr-pace capture` accepts a JSON Stop event on standard input. The command inherits `HERDR_PANE_ID` and `HERDR_SOCKET_PATH` from the AI pane. Capture failures report an error without blocking the AI's completion.

Claude Code and Codex events can supply `last_assistant_message` or `transcript_path`. Other hook bridges, including OpenCode and Pi, can supply `reply_text`:

```json
{
  "hook_event_name": "Stop",
  "session_id": "session",
  "reply_text": "The completed reply."
}
```

The hook ignores subagent events and Codex temporary assistant runs with an explicitly null `transcript_path`. Transcript fallback selects completed answers and skips progress messages. Genuine JSON answers remain intact. If another Stop guard can reject a draft, capture only after that guard accepts the reply.

## Install the hook declaratively

Declare a command hook in your harness configuration with the command:

```sh
herdr-pace capture
```

Use the installed package's absolute executable path if the harness does not inherit your PATH. For Claude Code, the registration belongs in `settings.json`; for Codex, it belongs in `hooks.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "herdr-pace capture",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

Merge this registration with existing hooks. Restart the AI session after applying it. The interactive installer refuses symlinked configuration so it cannot overwrite a managed source.

## Nix package

The flake exports a default package for Linux and macOS on x86_64 and aarch64. Add that package to your environment, then register its manifest:

```sh
herdr plugin link /path/to/package/share/herdr-plugin --enabled
```

The package includes `bin/herdr-pace`. A Home Manager or system activation can perform the link after installing the package. Keep keybindings and hook registrations in their existing declarative owners.

## Storage and privacy

Only the latest reply per pane and server is saved, with at most 64 replies retained. Each reply is limited to 1 MiB; an oversized reply leaves the previous reply intact. Files are private to the user and live under Herdr's plugin state directory, or `$XDG_STATE_HOME/herdr/plugins/castrozan.pace` outside a plugin action.

The reader loads one snapshot when opened. It does not poll transcripts or follow new replies while you read. Markdown normalization, font rendering, and playback happen locally without network requests.

When migrating from `castrozan.speed-read`, Pace preserves existing destination files and imports missing saved settings and replies once. The hook installer replaces its own previous capture command, while preserving unrelated hooks. Unlinking the old plugin registration leaves its saved files available.
