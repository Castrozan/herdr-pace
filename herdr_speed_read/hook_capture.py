import json
import os
from pathlib import Path

from .reply_storage import MAX_REPLY_BYTES, save_reply


def content_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    return "\n".join(
        block["text"]
        for block in content
        if isinstance(block, dict)
        and block.get("type") in ("text", "output_text")
        and isinstance(block.get("text"), str)
    ).strip()


def transcript_reply(transcript_path: str) -> str:
    if not isinstance(transcript_path, str) or not transcript_path:
        return ""
    try:
        with Path(transcript_path).open("rb") as transcript:
            size = transcript.seek(0, os.SEEK_END)
            offset = max(0, size - MAX_REPLY_BYTES)
            transcript.seek(offset)
            lines = transcript.read(MAX_REPLY_BYTES).splitlines()
            if offset:
                lines = lines[1:]
    except OSError:
        return ""
    reply = ""
    for line in lines:
        try:
            event = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(event, dict):
            continue
        message = (
            event.get("payload")
            if event.get("type") == "response_item"
            else event.get("message")
        )
        if not isinstance(message, dict):
            continue
        role = message.get("role", event.get("type"))
        if role == "user":
            reply = ""
        elif role == "assistant" and message.get("channel") in (None, "final"):
            text = content_text(message.get("content"))
            if text:
                reply = text
    return reply


def completed_reply(payload: dict) -> str:
    for field in ("reply_text", "last_assistant_message"):
        text = payload.get(field)
        if isinstance(text, str) and text.strip():
            return text.strip()
    return transcript_reply(payload.get("transcript_path", ""))


def capture_hook(payload: dict) -> None:
    if payload.get("hook_event_name", "Stop") != "Stop" or payload.get("agent_id"):
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
