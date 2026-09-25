"""Forward OpenAI-compatible routes to llama-server and keep usage metadata."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable

import httpx
from fastapi import Request
from fastapi.responses import Response, StreamingResponse

from rp5_llm.history import History, RequestEvent, utc_now
from rp5_llm.settings import Settings
from rp5_llm.usage import extract_usage

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else ""
    if peer in {"127.0.0.1", "::1", "testclient"}:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip() or peer
    return peer


async def proxy_openai(
    request: Request,
    upstream_path: str,
    settings: Settings,
    history: History,
    client: httpx.AsyncClient,
    active_inc: Callable[[int], None],
) -> Response:
    body = await request.body()
    if len(body) > settings.max_body_bytes:
        return Response(
            content=b'{"error":"request body is too large"}',
            status_code=413,
            media_type="application/json",
        )
    request_id = str(uuid.uuid4())
    url = f"{settings.llama_url}/{upstream_path.lstrip('/')}"
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP
    }
    headers["x-request-id"] = request_id
    started = time.perf_counter()
    active_inc(1)
    try:
        if _wants_stream(body):
            return await _stream(
                request, url, headers, body, request_id, settings, history, client, active_inc, started
            )
        try:
            upstream = await client.request(request.method, url, content=body, headers=headers)
        except httpx.HTTPError:
            _record(history, settings, request, request_id, started, 502, False, body, b"", active_done=True, active_inc=active_inc)
            return Response(
                content=b'{"error":"llama-server is not reachable"}',
                status_code=502,
                media_type="application/json",
                headers={"x-request-id": request_id},
            )
        response_body = upstream.content
        _record(
            history,
            settings,
            request,
            request_id,
            started,
            upstream.status_code,
            200 <= upstream.status_code < 300,
            body,
            response_body,
            active_done=True,
            active_inc=active_inc,
        )
        response_headers = {
            key: value
            for key, value in upstream.headers.items()
            if key.lower() not in HOP_BY_HOP
        }
        response_headers["x-request-id"] = request_id
        return Response(content=response_body, status_code=upstream.status_code, headers=response_headers)
    except Exception:
        active_inc(-1)
        raise


async def _stream(
    request: Request,
    url: str,
    headers: dict,
    body: bytes,
    request_id: str,
    settings: Settings,
    history: History,
    client: httpx.AsyncClient,
    active_inc: Callable[[int], None],
    started: float,
) -> Response:
    try:
        upstream_cm = client.stream(request.method, url, content=body, headers=headers)
        upstream = await upstream_cm.__aenter__()
    except httpx.HTTPError:
        _record(history, settings, request, request_id, started, 502, False, body, b"", active_done=True, active_inc=active_inc)
        return Response(
            content=b'{"error":"llama-server is not reachable"}',
            status_code=502,
            media_type="application/json",
            headers={"x-request-id": request_id},
        )

    async def generate():
        # Keep only the tail so a long stream is not stored. Usage sits on the last event.
        tail = b""
        try:
            async for chunk in upstream.aiter_bytes():
                tail = (tail + chunk)[-65536:]
                yield chunk
        finally:
            _record(
                history,
                settings,
                request,
                request_id,
                started,
                upstream.status_code,
                200 <= upstream.status_code < 300,
                body,
                tail,
                active_done=True,
                active_inc=active_inc,
            )
            await upstream_cm.__aexit__(None, None, None)

    response_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() not in HOP_BY_HOP
    }
    response_headers["x-request-id"] = request_id
    return StreamingResponse(generate(), status_code=upstream.status_code, headers=response_headers)


def _record(
    history: History,
    settings: Settings,
    request: Request,
    request_id: str,
    started: float,
    status_code: int,
    ok: bool,
    request_body: bytes,
    response_body: bytes,
    active_done: bool,
    active_inc: Callable[[int], None],
) -> None:
    if active_done:
        active_inc(-1)
    prompt_tokens, generated_tokens = extract_usage(response_body)
    duration_ms = int((time.perf_counter() - started) * 1000)
    tokens_per_sec = None
    if generated_tokens and duration_ms > 0:
        tokens_per_sec = round(generated_tokens / (duration_ms / 1000), 2)
    model = ""
    if response_body:
        model = _json_model(response_body)
    history.record(
        RequestEvent(
            id=request_id,
            ts=utc_now(),
            source_ip=client_ip(request),
            model=model,
            backend=settings.backend if settings.backend != "auto" else "cpu",
            prompt_tokens=prompt_tokens,
            generated_tokens=generated_tokens,
            duration_ms=duration_ms,
            tokens_per_sec=tokens_per_sec,
            ok=ok,
            http_status=status_code,
            prompt_text=request_body.decode("utf-8", errors="replace") if settings.capture_content else None,
            response_text=response_body.decode("utf-8", errors="replace") if settings.capture_content else None,
        )
    )


def _wants_stream(body: bytes) -> bool:
    if not body:
        return False
    try:
        import json

        payload = json.loads(body)
    except json.JSONDecodeError:
        return False
    return isinstance(payload, dict) and payload.get("stream") is True


def _json_model(body: bytes) -> str:
    try:
        import json

        payload = json.loads(body.split(b"\n", 1)[0].removeprefix(b"data:").strip() or body)
    except (json.JSONDecodeError, ValueError):
        return ""
    if isinstance(payload, dict) and isinstance(payload.get("model"), str):
        return payload["model"]
    return ""
