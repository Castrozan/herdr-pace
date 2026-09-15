import json

from herdr_pace.storage.paths import state_directory
from herdr_pace.storage.replies import load_reply
from herdr_pace.storage.settings import load_reader_settings


def test_rename_preserves_settings_and_reply_without_overwriting_new_data(
    tmp_path, monkeypatch
):
    previous = tmp_path / "castrozan.speed-read"
    destination = tmp_path / "castrozan.pace"
    (previous / "replies").mkdir(parents=True)
    (previous / "settings.json").write_text(
        '{"words_per_minute":800,"countdown_duration_seconds":0}'
    )
    key = "a" * 64
    (previous / "replies" / f"{key}.json").write_text(
        json.dumps({"text": "Preserved reply"})
    )
    monkeypatch.setenv("HERDR_PLUGIN_STATE_DIR", str(destination))
    assert load_reader_settings().words_per_minute == 800
    assert load_reader_settings().countdown_duration_seconds == 0
    assert load_reply(key) == "Preserved reply"
    (destination / "settings.json").write_text(
        '{"words_per_minute":900,"countdown_duration_seconds":4}'
    )
    assert state_directory() == destination
    assert load_reader_settings().words_per_minute == 900
    assert (previous / "settings.json").exists()


def test_new_install_does_not_create_migration_files(tmp_path, monkeypatch):
    monkeypatch.setenv("HERDR_PLUGIN_STATE_DIR", str(tmp_path / "castrozan.pace"))
    assert not state_directory().exists()
