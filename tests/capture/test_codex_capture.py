import json

import pytest

from herdr_pace.capture.transcripts import transcript_reply


@pytest.mark.parametrize(
    "metadata, final", [("channel", "final"), ("phase", "final_answer")]
)
def test_codex_transcript_uses_completed_answers_only(tmp_path, metadata, final):
    path = tmp_path / "transcript.jsonl"
    events = [
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                metadata: phase,
                "content": [{"type": "output_text", "text": text}],
            },
        }
        for phase, text in (
            ("analysis", "Private"),
            (final, "The completed reply."),
            ("commentary", "Progress from the next step."),
        )
    ]
    path.write_text("\n".join(map(json.dumps, events)))
    assert transcript_reply(str(path)) == "The completed reply."
