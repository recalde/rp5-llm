"""Dashboard, status API, and OpenAI-compatible gateway."""

from __future__ import annotations

import asyncio
import secrets
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from rp5_llm import __version__
from rp5_llm.hardware import checks, collect
from rp5_llm.history import History
from rp5_llm.models import find_model, load_models
from rp5_llm.proxy import proxy_openai
from rp5_llm.settings import Settings
from rp5_llm.setup import (
    SetupError,
    apply_plan,
    load_plan,
    mark_complete,
    setup_complete,
    validate_plan,
)

LOOPBACK = {"127.0.0.1", "::1", "localhost", "testclient"}


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    history = History(
        settings.state_dir / "history.sqlite",
        limit=settings.history_limit,
        days=settings.history_days,
        capture=settings.capture_content,
    )
    active = {"count": 0}
    active_lock = threading.Lock()
    started = time.monotonic()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.http = httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=2.0))
        yield
        await app.state.http.aclose()
        history.close()

    docs_url = "/docs" if settings.loopback_only else None
    app = FastAPI(
        title="rp5-llm",
        version=__version__,
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=None,
        openapi_url="/openapi.json" if docs_url else None,
    )
    app.state.settings = settings
    app.state.history = history
    app.state.active = active
    app.state.active_lock = active_lock
    app.state.started = started

    def bump(delta: int) -> None:
        with active_lock:
            active["count"] = max(0, active["count"] + delta)

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "request rejected"
        return JSONResponse({"error": detail}, status_code=exc.status_code)

    @app.get("/health")
    async def health() -> dict:
        llama = await _llama_status(app)
        return {"status": "ok", "llama": llama}

    @app.get("/api/status")
    async def status(request: Request) -> dict:
        return await _status_payload(app, request)

    @app.get("/api/hardware")
    async def hardware() -> dict:
        info = await asyncio.to_thread(collect, settings.detect_script)
        return {"hardware": info, "checks": checks(info)}

    @app.get("/api/model")
    async def model() -> dict:
        return _model_payload(settings)

    @app.get("/api/metrics")
    async def metrics() -> dict:
        summary = history.summary()
        summary["active"] = active["count"]
        return summary

    @app.get("/api/requests")
    async def requests(limit: int = 50) -> dict:
        return {"requests": history.list_recent(limit)}

    @app.get("/api/config")
    async def config() -> dict:
        plan = _current_plan(settings)
        return {
            "bind": settings.bind,
            "port": settings.port,
            "llamaUrl": settings.llama_url,
            "exposeLan": plan["exposeLan"],
            "kiosk": plan["kiosk"],
            "captureContent": settings.capture_content,
            "historyLimit": settings.history_limit,
            "historyDays": settings.history_days,
            "backend": plan["backend"],
            "model": plan["model"],
            "setupComplete": setup_complete(settings.state_dir / "setup-complete"),
        }

    @app.get("/api/setup/session")
    async def setup_session() -> JSONResponse:
        token = secrets.token_urlsafe(24)
        body = {"csrf": token, "setupRequired": not setup_complete(settings.state_dir / "setup-complete")}
        response = JSONResponse(body)
        response.set_cookie("rp5_csrf", token, httponly=False, samesite="strict", secure=False, path="/")
        return response

    @app.get("/api/setup/options")
    async def setup_options() -> dict:
        return {"models": load_models(settings.models_path), "backends": ["cpu", "vulkan", "auto"]}

    @app.get("/api/setup/check")
    async def setup_check() -> dict:
        info = await asyncio.to_thread(collect, settings.detect_script)
        return {"hardware": info, "checks": checks(info)}

    @app.post("/api/setup/install")
    async def setup_install(request: Request) -> dict:
        _require_setup_access(request, settings)
        payload = await _json_object(request)
        models = load_models(settings.models_path)
        try:
            plan = validate_plan(payload, models)
            steps = apply_plan(settings, plan, runner=_reject_commands)
        except SetupError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        info = await asyncio.to_thread(collect, settings.detect_script)
        return {"steps": [{"id": "hardware", "status": "pass", "detail": info.get("device") or "detected"}, *steps]}

    @app.post("/api/setup/complete")
    async def setup_done(request: Request) -> dict:
        _require_setup_access(request, settings)
        mark_complete(settings.state_dir / "setup-complete")
        return {"setupComplete": True}

    @app.post("/api/setup/unlock")
    async def setup_unlock(request: Request) -> dict:
        if not _is_loopback(request):
            raise HTTPException(status_code=403, detail="unlock is only available on the device")
        _require_tokens(request, settings)
        payload = await _json_object(request)
        if payload.get("confirm") != "unlock":
            raise HTTPException(status_code=400, detail="confirmation required")
        path = settings.state_dir / "setup-complete"
        if path.is_file():
            path.unlink()
        return {"setupComplete": False}

    @app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def gateway(path: str, request: Request) -> Response:
        return await proxy_openai(request, f"v1/{path}", settings, history, request.app.state.http, bump)

    frontend = settings.frontend_dir
    if frontend.is_dir():
        assets = frontend / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/")
        async def index() -> FileResponse:
            return FileResponse(frontend / "index.html")

        @app.get("/setup")
        async def setup_page() -> FileResponse:
            return FileResponse(frontend / "setup.html")

        @app.get("/app.css")
        async def css() -> FileResponse:
            return FileResponse(frontend / "app.css")

        @app.get("/app.js")
        async def js() -> FileResponse:
            return FileResponse(frontend / "app.js")

        @app.get("/setup.js")
        async def setup_js() -> FileResponse:
            return FileResponse(frontend / "setup.js")

    @app.get("/favicon.ico")
    async def favicon() -> Response:
        return Response(status_code=204)

    return app


def _reject_commands(_argv: list[str]) -> None:
    """The HTTP process never runs hostnamectl or systemctl."""
    return None


async def _llama_status(app: FastAPI) -> str:
    settings: Settings = app.state.settings
    try:
        response = await app.state.http.get(f"{settings.llama_url}/health")
    except httpx.HTTPError:
        return "offline"
    if response.status_code == 200:
        return "online"
    if response.status_code == 503:
        return "loading"
    return "offline"


async def _status_payload(app: FastAPI, request: Request) -> dict:
    settings: Settings = app.state.settings
    history: History = app.state.history
    info = await asyncio.to_thread(collect, settings.detect_script)
    llama = await _llama_status(app)
    summary = history.summary()
    plan = _current_plan(settings)
    model = _model_payload(settings)
    uptime = _system_uptime(app.state.started)
    api_base = f"http://{settings.bind}:{settings.port}"
    if settings.bind == "0.0.0.0":
        api_base = f"http://{info.get('ip') or '0.0.0.0'}:{settings.port}"
    payload = {
        "status": llama,
        "device": info.get("device") or "unknown",
        "ip": info.get("ip") or "",
        "model": model["file"] or "none",
        "modelName": model["name"],
        "backend": _display_backend(plan["backend"]),
        "uptimeSeconds": uptime,
        "requests": {"total": summary["total"], "active": app.state.active["count"]},
        "lastRequest": summary["last"],
        "api": {"base": api_base, "exposed": not settings.loopback_only},
        "setupRequired": not setup_complete(settings.state_dir / "setup-complete"),
        "version": __version__,
    }
    if _is_loopback(request) and payload["setupRequired"]:
        payload["setupCode"] = _setup_code(settings.state_dir)
    return payload


def _model_payload(settings: Settings) -> dict:
    plan = _current_plan(settings)
    models = load_models(settings.models_path)
    selected = find_model(models, plan["model"]) if plan["model"] else None
    return {
        "id": plan["model"],
        "name": selected["name"] if selected else "",
        "file": selected["file"] if selected else "",
        "backend": plan["backend"],
        "loaded": False,
    }


def _current_plan(settings: Settings) -> dict:
    models = load_models(settings.models_path)
    try:
        return load_plan(settings.state_dir / "desired.json", models)
    except SetupError:
        from rp5_llm.setup import empty_plan

        return empty_plan()


def _system_uptime(started: float) -> int:
    proc = Path("/proc/uptime")
    if proc.is_file():
        try:
            return int(float(proc.read_text().split()[0]))
        except (OSError, ValueError, IndexError):
            pass
    return int(time.monotonic() - started)


def _display_backend(backend: str) -> str:
    if backend == "vulkan":
        return "vulkan"
    return "cpu"


def _setup_code(state_dir: Path) -> str:
    path = state_dir / "setup-code"
    if path.is_file():
        return path.read_text().strip()
    code = secrets.token_hex(3)
    path.write_text(code + "\n")
    path.chmod(0o600)
    return code


def _is_loopback(request: Request) -> bool:
    host = request.client.host if request.client else ""
    return host in LOOPBACK


def _require_setup_access(request: Request, settings: Settings) -> None:
    if setup_complete(settings.state_dir / "setup-complete"):
        raise HTTPException(status_code=403, detail="setup is locked")
    _require_tokens(request, settings)


def _require_tokens(request: Request, settings: Settings) -> None:
    cookie = request.cookies.get("rp5_csrf", "")
    header = request.headers.get("x-csrf-token", "")
    if not cookie or not header or len(cookie) != len(header) or not secrets.compare_digest(cookie, header):
        raise HTTPException(status_code=403, detail="csrf token rejected")
    origin = request.headers.get("origin")
    if origin:
        host = request.headers.get("host", "")
        if origin not in {f"http://{host}", f"https://{host}"}:
            raise HTTPException(status_code=403, detail="origin rejected")
    expected = _setup_code(settings.state_dir)
    supplied = request.headers.get("x-setup-code", "")
    if not supplied or len(supplied) != len(expected) or not secrets.compare_digest(expected, supplied):
        raise HTTPException(status_code=403, detail="setup code rejected")


async def _json_object(request: Request) -> dict:
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="expected a JSON object") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="expected a JSON object")
    return payload
