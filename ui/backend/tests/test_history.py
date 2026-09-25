from pathlib import Path

from rp5_llm.history import History, RequestEvent


def _event(event_id: str, ts: str, prompt: str = "hidden-prompt") -> RequestEvent:
    return RequestEvent(
        id=event_id,
        ts=ts,
        source_ip="127.0.0.1",
        model="demo",
        backend="cpu",
        prompt_tokens=3,
        generated_tokens=5,
        duration_ms=1000,
        tokens_per_sec=5.0,
        ok=True,
        http_status=200,
        prompt_text=prompt,
        response_text="hidden-reply",
    )


def test_capture_off_keeps_bodies_out_of_the_database(tmp_path: Path):
    path = tmp_path / "history.sqlite"
    history = History(path, limit=100, days=7, capture=False)
    history.record(_event("a", "2026-09-25T12:00:00Z"))
    history.close()
    raw = path.read_bytes()
    assert b"hidden-prompt" not in raw
    assert b"hidden-reply" not in raw


def test_capture_on_stores_bodies(tmp_path: Path):
    history = History(tmp_path / "history.sqlite", limit=100, days=7, capture=True)
    history.record(_event("a", "2026-09-25T12:00:00Z"))
    assert b"hidden-prompt" in (tmp_path / "history.sqlite").read_bytes()
    history.close()


def test_retention_keeps_the_newest_rows(tmp_path: Path):
    history = History(tmp_path / "history.sqlite", limit=2, days=7, capture=False)
    history.record(_event("old", "2026-09-25T12:00:00Z"))
    history.record(_event("mid", "2026-09-25T12:01:00Z"))
    history.record(_event("new", "2026-09-25T12:02:00Z"))
    ids = [row["id"] for row in history.list_recent(10)]
    history.close()
    assert ids == ["new", "mid"]


def test_old_rows_expire(tmp_path: Path):
    history = History(tmp_path / "history.sqlite", limit=100, days=7, capture=False)
    history.record(_event("stale", "2020-01-01T00:00:00Z"))
    history.record(_event("fresh", "2026-09-25T12:00:00Z"))
    ids = [row["id"] for row in history.list_recent(10)]
    history.close()
    assert ids == ["fresh"]
