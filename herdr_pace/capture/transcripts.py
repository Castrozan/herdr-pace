import json
import os
from pathlib import Path

from herdr_pace.storage.replies import MAX_REPLY_BYTES


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
        elif (
            role == "assistant"
            and message.get("channel") in (None, "final")
            and message.get("phase") in (None, "final_answer")
        ):
            text = content_text(message.get("content"))
            if text:
                reply = text
    return reply
