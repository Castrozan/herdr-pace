import os

from herdr_pace.storage.replies import save_reply

from .transcripts import transcript_reply


def completed_reply(payload: dict) -> str:
    for field in ("reply_text", "last_assistant_message"):
        text = payload.get(field)
        if isinstance(text, str) and text.strip():
            return text.strip()
    return transcript_reply(payload.get("transcript_path", ""))


def capture_hook(payload: dict) -> None:
    if payload.get("hook_event_name", "Stop") != "Stop" or payload.get("agent_id"):
        return
    if (
        "last_assistant_message" in payload
        and "transcript_path" in payload
        and payload["transcript_path"] is None
    ):
        return
    pane_id = os.environ.get("HERDR_PANE_ID", "")
    socket_path = os.environ.get("HERDR_SOCKET_PATH", "")
    if not pane_id or not socket_path:
        return
    inherited_session = os.environ.get("CODEX_THREAD_ID")
    session_id = payload.get("session_id", "")
    if inherited_session and session_id and inherited_session != session_id:
        return
    save_reply(pane_id, socket_path, session_id, completed_reply(payload))
