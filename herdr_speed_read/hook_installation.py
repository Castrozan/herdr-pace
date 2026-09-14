import json
import os
import shlex
import shutil
import sys
from pathlib import Path

from .reply_storage import atomic_write


def hook_command() -> str:
    plugin_root = os.environ.get("HERDR_PLUGIN_ROOT")
    executable = Path(sys.argv[0]).absolute().with_name("herdr-speed-read")
    if plugin_root:
        plugin_executable = Path(plugin_root) / ".plugin-build/bin/herdr-speed-read"
        if plugin_executable.is_file():
            executable = plugin_executable
    return f"{shlex.quote(str(executable))} capture"


def install_stop_hook(configuration_path: Path, command: str) -> None:
    if configuration_path.is_symlink():
        raise ValueError(
            f"{configuration_path} is managed; add the capture hook in its source"
        )
    configuration = (
        json.loads(configuration_path.read_text())
        if configuration_path.exists()
        else {}
    )
    if not isinstance(configuration, dict):
        raise ValueError("Hook configuration must be a JSON object")
    hooks = configuration.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("The hooks setting must be a JSON object")
    registrations = hooks.setdefault("Stop", [])
    if not isinstance(registrations, list):
        raise ValueError("Stop hook registrations must be a list")
    for registration in registrations:
        if any(
            hook.get("command") == command for hook in registration.get("hooks", [])
        ):
            return
    registrations.append(
        {"hooks": [{"type": "command", "command": command, "timeout": 5}]}
    )
    if configuration_path.exists():
        backup = configuration_path.with_name(
            configuration_path.name + ".before-speed-read"
        )
        if not backup.exists():
            shutil.copy2(configuration_path, backup)
    atomic_write(configuration_path, configuration)


def install_hooks() -> None:
    home = Path.home()
    targets = (
        (Path(os.environ.get("CLAUDE_CONFIG_DIR", home / ".claude")), "settings.json"),
        (Path(os.environ.get("CODEX_HOME", home / ".codex")), "hooks.json"),
    )
    installed = []
    for directory, filename in targets:
        if directory.is_dir():
            path = directory / filename
            install_stop_hook(path, hook_command())
            installed.append(str(path))
    if not installed:
        raise ValueError("No Claude Code or Codex configuration directory found")
    print("Installed capture hooks in " + ", ".join(installed))
