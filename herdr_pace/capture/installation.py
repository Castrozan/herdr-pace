import json
import os
import shlex
import shutil
import sys
from pathlib import Path

from herdr_pace.storage.files import atomic_write
from herdr_pace.storage.migration import PREVIOUS_EXECUTABLE


def hook_command() -> str:
    plugin_root = os.environ.get("HERDR_PLUGIN_ROOT")
    executable = Path(sys.argv[0]).absolute().with_name("herdr-pace")
    if plugin_root:
        plugin_executable = Path(plugin_root) / ".plugin-build/bin/herdr-pace"
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
    existing = False
    for registration in registrations:
        for hook in registration.get("hooks", []):
            installed_command = hook.get("command", "")
            if installed_command == command:
                existing = True
                continue
            try:
                arguments = shlex.split(installed_command)
            except ValueError:
                continue
            if (
                len(arguments) == 2
                and arguments[1] == "capture"
                and Path(arguments[0]).name in (PREVIOUS_EXECUTABLE, "herdr-pace")
            ):
                hook["command"] = command
                existing = True
    if not existing:
        registrations.append(
            {"hooks": [{"type": "command", "command": command, "timeout": 5}]}
        )
    if configuration_path.exists():
        backup = configuration_path.with_name(
            configuration_path.name + ".before-herdr-pace"
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
