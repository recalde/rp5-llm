from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from fastapi.testclient import TestClient

from rp5_llm.app import create_app
from rp5_llm.settings import Settings


class _LlamaHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path.startswith("/health"):
            body = b'{"status":"ok"}'
            self._send(200, body)
            return
        self._send(404, b"{}")

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        body = json.dumps(
            {
                "model": "qwen-test.gguf",
                "choices": [{"message": {"content": "secret-response"}}],
                "usage": {"prompt_tokens": 8, "completion_tokens": 3},
            }
        ).encode()
        self._send(200, body)

    def _send(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        return


def _llama_server() -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _LlamaHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    return server, f"http://{host}:{port}"


def test_status_shape_when_llama_is_down(client: TestClient):
    response = client.get("/api/status")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "offline"
    assert body["backend"] == "cpu"
    assert "requests" in body
    assert body["api"]["exposed"] is False
    assert "setupCode" in body


def test_health_stays_up_without_llama(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["llama"] == "offline"


def test_dashboard_is_served(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "RP5 Local LLM" in response.text


def test_gateway_records_usage_and_drops_the_prompt(settings: Settings):
    server, url = _llama_server()
    settings = Settings(
        bind=settings.bind,
        port=settings.port,
        llama_url=url,
        state_dir=settings.state_dir,
        config_dir=settings.config_dir,
        frontend_dir=settings.frontend_dir,
        models_path=settings.models_path,
        detect_script=settings.detect_script,
        user=settings.user,
        backend="cpu",
        kiosk=False,
        expose_lan=False,
        capture_content=False,
        history_limit=100,
        history_days=7,
        max_body_bytes=settings.max_body_bytes,
        allow_host_changes=False,
        allow_privileged_apply=False,
        ssh_home=None,
    )
    try:
        with TestClient(create_app(settings)) as client:
            response = client.post(
                "/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "TOP-SECRET-PROMPT"}]},
            )
            assert response.status_code == 200
            assert response.json()["usage"]["completion_tokens"] == 3
            assert response.headers["x-request-id"]
            listed = client.get("/api/requests").json()["requests"]
            assert listed[0]["promptTokens"] == 8
            assert listed[0]["generatedTokens"] == 3
            assert listed[0]["model"] == "qwen-test.gguf"
            raw = (settings.state_dir / "history.sqlite").read_bytes()
            assert b"TOP-SECRET-PROMPT" not in raw
            assert b"secret-response" not in raw
            status = client.get("/api/status").json()
            assert status["status"] == "online"
            assert status["requests"]["total"] == 1
    finally:
        server.shutdown()
