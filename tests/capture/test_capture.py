import json

import pytest

from herdr_pace.capture.events import (
    capture_hook,
    completed_reply,
)
from herdr_pace.capture.transcripts import transcript_reply
from herdr_pace.storage.replies import load_reply, reply_key


@pytest.fixture
def captured_pane(tmp_path, monkeypatch):
    monkeypatch.setenv("HERDR_PLUGIN_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("HERDR_PANE_ID", "workspace:pane")
    monkeypatch.setenv("HERDR_SOCKET_PATH", "/tmp/reader-test.sock")
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    return reply_key("workspace:pane", "/tmp/reader-test.sock")


@pytest.mark.parametrize("field", ["reply_text", "last_assistant_message"])
def test_capture_direct_completed_reply(captured_pane, field):
    capture_hook({"hook_event_name": "Stop", field: "**Ready.**"})
    assert load_reply(captured_pane) == "**Ready.**"


@pytest.mark.parametrize(
    "payload",
    [
        {"hook_event_name": "SubagentStop", "reply_text": "Child"},
        {"hook_event_name": "Stop", "agent_id": "child", "reply_text": "Child"},
        {"hook_event_name": "PreToolUse", "reply_text": "Tool"},
        {"hook_event_name": "Stop", "reply_text": "  "},
    ],
)
def test_other_events_do_not_overwrite_reply(captured_pane, payload):
    capture_hook({"reply_text": "Keep this."})
    capture_hook(payload)
    assert load_reply(captured_pane) == "Keep this."


def test_nested_codex_session_cannot_replace_parent_reply(captured_pane, monkeypatch):
    monkeypatch.setenv("CODEX_THREAD_ID", "parent")
    capture_hook({"session_id": "child", "reply_text": "Child"})
    assert load_reply(captured_pane) == ""


@pytest.mark.parametrize(
    "saved_reply", ["", "The installed copy passed the Chrome check."]
)
def test_ephemeral_codex_recap_cannot_replace_completed_reply(
    captured_pane, saved_reply
):
    if saved_reply:
        capture_hook(
            {
                "session_id": "conversation",
                "transcript_path": "/conversation.jsonl",
                "last_assistant_message": saved_reply,
            }
        )
    capture_hook(
        {
            "hook_event_name": "Stop",
            "session_id": "temporary-recap",
            "transcript_path": None,
            "last_assistant_message": '{"recap":"The task is complete."}',
        }
    )
    assert load_reply(captured_pane) == saved_reply


def test_legitimate_json_reply_is_preserved(captured_pane):
    text = '{"recap":"The requested JSON response."}'
    capture_hook(
        {
            "session_id": "conversation",
            "transcript_path": "/conversation.jsonl",
            "last_assistant_message": text,
        }
    )
    assert load_reply(captured_pane) == text


def test_missing_pane_is_a_noop(tmp_path, monkeypatch):
    monkeypatch.setenv("HERDR_PLUGIN_STATE_DIR", str(tmp_path))
    monkeypatch.delenv("HERDR_PANE_ID", raising=False)
    capture_hook({"reply_text": "Do not persist this."})
    assert not list(tmp_path.iterdir())


def test_claude_transcript_ignores_tools_and_thinking(tmp_path):
    path = tmp_path / "transcript.jsonl"
    events = [
        {"type": "user", "message": {"content": "Fix it"}},
        {
            "type": "assistant",
            "message": {"content": [{"type": "thinking", "thinking": "Private"}]},
        },
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "Fixed."}]},
        },
    ]
    path.write_text("\n".join(map(json.dumps, events)))
    assert transcript_reply(str(path)) == "Fixed."


def test_new_user_turn_clears_old_reply(tmp_path):
    path = tmp_path / "transcript.jsonl"
    path.write_text(
        "\n".join(
            map(
                json.dumps,
                [
                    {"type": "assistant", "message": {"content": "Old reply"}},
                    {"type": "user", "message": {"content": "New request"}},
                ],
            )
        )
    )
    assert transcript_reply(str(path)) == ""


def test_transcript_tail_skips_large_old_records(tmp_path):
    path = tmp_path / "transcript.jsonl"
    path.write_text(
        "x" * (2 * 1024 * 1024)
        + "\n"
        + json.dumps({"type": "assistant", "message": {"content": "Latest."}})
    )
    assert transcript_reply(str(path)) == "Latest."


def test_direct_reply_does_not_read_transcript(monkeypatch):
    def unexpected_read(path):
        raise AssertionError("Direct replies must not scan transcripts")

    monkeypatch.setattr("herdr_pace.capture.events.transcript_reply", unexpected_read)
    assert (
        completed_reply(
            {"last_assistant_message": "Direct", "transcript_path": "unused"}
        )
        == "Direct"
    )
