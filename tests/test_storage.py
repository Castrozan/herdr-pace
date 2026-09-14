import json
import stat

import pytest

from herdr_speed_read import reply_storage


@pytest.fixture(autouse=True)
def private_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("HERDR_PLUGIN_STATE_DIR", str(tmp_path))


def test_latest_reply_replaces_previous(tmp_path):
    reply_storage.save_reply("pane", "socket", "session", "First")
    reply_storage.save_reply("pane", "socket", "session", "Second")
    key = reply_storage.reply_key("pane", "socket")
    assert reply_storage.load_reply(key) == "Second"
    snapshots = list((tmp_path / "replies").iterdir())
    assert len(snapshots) == 1
    assert stat.S_IMODE(snapshots[0].stat().st_mode) == 0o600


def test_panes_and_servers_are_isolated():
    for pane, socket, text in (
        ("one", "local", "A"),
        ("two", "local", "B"),
        ("one", "remote", "C"),
    ):
        reply_storage.save_reply(pane, socket, "session", text)
    assert reply_storage.load_reply(reply_storage.reply_key("one", "local")) == "A"
    assert reply_storage.load_reply(reply_storage.reply_key("two", "local")) == "B"
    assert reply_storage.load_reply(reply_storage.reply_key("one", "remote")) == "C"


def test_retention_is_bounded(tmp_path):
    for number in range(reply_storage.MAX_SAVED_REPLIES + 3):
        reply_storage.save_reply(str(number), "socket", "session", "Reply")
    assert (
        len(list((tmp_path / "replies").glob("*.json")))
        == reply_storage.MAX_SAVED_REPLIES
    )


def test_oversized_reply_does_not_replace_valid_reply():
    reply_storage.save_reply("pane", "socket", "session", "Original")
    with pytest.raises(ValueError, match="1 MiB"):
        reply_storage.save_reply(
            "pane", "socket", "session", "a" * (reply_storage.MAX_REPLY_BYTES + 1)
        )
    assert (
        reply_storage.load_reply(reply_storage.reply_key("pane", "socket"))
        == "Original"
    )


@pytest.mark.parametrize("key", ["../../settings", "bad", "", "a" * 63])
def test_invalid_storage_key_is_rejected(key):
    assert reply_storage.load_reply(key) == ""


@pytest.mark.parametrize("content", ["{", "[]", "null", '{"text": 4}'])
def test_corrupt_reply_is_empty(tmp_path, content):
    directory = tmp_path / "replies"
    directory.mkdir()
    key = "a" * 64
    (directory / f"{key}.json").write_text(content)
    assert reply_storage.load_reply(key) == ""


@pytest.mark.parametrize("speed", [True, 0, 2001, "400", None])
def test_invalid_saved_speed_uses_default(tmp_path, speed):
    (tmp_path / "settings.json").write_text(json.dumps({"words_per_minute": speed}))
    assert reply_storage.load_reading_speed() == 400


def test_speed_preference_round_trip():
    reply_storage.save_reading_speed(650)
    assert reply_storage.load_reading_speed() == 650
