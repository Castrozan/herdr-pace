import json

import pytest

from herdr_pace.capture.installation import install_stop_hook


def test_installation_preserves_settings_and_is_idempotent(tmp_path):
    path = tmp_path / "settings.json"
    original = {
        "model": "chosen",
        "hooks": {
            "Stop": [{"hooks": [{"type": "command", "command": "existing-hook"}]}]
        },
    }
    path.write_text(json.dumps(original))
    install_stop_hook(path, "/nix/store/plugin/bin/herdr-pace capture")
    install_stop_hook(path, "/nix/store/plugin/bin/herdr-pace capture")
    updated = json.loads(path.read_text())
    assert updated["model"] == "chosen"
    assert len(updated["hooks"]["Stop"]) == 2
    assert updated["hooks"]["Stop"][0] == original["hooks"]["Stop"][0]
    assert (
        json.loads(path.with_name("settings.json.before-herdr-pace").read_text())
        == original
    )


def test_managed_configuration_is_not_overwritten(tmp_path):
    source = tmp_path / "source.json"
    source.write_text("{}")
    path = tmp_path / "settings.json"
    path.symlink_to(source)
    with pytest.raises(ValueError, match="managed"):
        install_stop_hook(path, "herdr-pace capture")
    assert source.read_text() == "{}"


def test_invalid_configuration_is_preserved(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("not json")
    with pytest.raises(ValueError):
        install_stop_hook(path, "herdr-pace capture")
    assert path.read_text() == "not json"


@pytest.mark.parametrize("executable", ["herdr-speed-read", "herdr-pace"])
def test_install_replaces_its_previous_capture_command(tmp_path, executable):
    path = tmp_path / "hooks.json"
    original = {
        "hooks": {
            "Stop": [
                {
                    "hooks": [
                        {"type": "command", "command": f"/old/bin/{executable} capture"}
                    ]
                }
            ]
        }
    }
    path.write_text(json.dumps(original))
    install_stop_hook(path, "/new/bin/herdr-pace capture")
    hooks = json.loads(path.read_text())["hooks"]["Stop"]
    assert len(hooks) == 1
    assert hooks[0]["hooks"][0]["command"] == "/new/bin/herdr-pace capture"
    assert (
        json.loads(path.with_name("hooks.json.before-herdr-pace").read_text())
        == original
    )
