"""Pull token counts out of an OpenAI-compatible llama.cpp response.

The rest of the payload, including any prompt or completion text, is ignored.
"""

from __future__ import annotations

import json
from typing import Any


def extract_usage(body: bytes) -> tuple[int | None, int | None]:
    if not body:
        return None, None
    text = body.decode("utf-8", errors="replace")
    if "data:" in text and text.lstrip().startswith("data:"):
        return _from_sse(text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        if "data:" in text:
            return _from_sse(text)
        return None, None
    return _from_payload(payload)


def _from_sse(text: str) -> tuple[int | None, int | None]:
    prompt_tokens = None
    generated_tokens = None
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data or data == "[DONE]":
            continue
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        found = _from_payload(payload)
        if found[0] is not None:
            prompt_tokens = found[0]
        if found[1] is not None:
            generated_tokens = found[1]
    return prompt_tokens, generated_tokens


def _from_payload(payload: Any) -> tuple[int | None, int | None]:
    if not isinstance(payload, dict):
        return None, None
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None, None
    return _count(usage.get("prompt_tokens")), _count(
        usage.get("completion_tokens", usage.get("generated_tokens"))
    )


def _count(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, float) and value.is_integer():
        return max(int(value), 0)
    return None
