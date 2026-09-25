"""Bounded SQLite log of inference metadata. Bodies stay out unless capture is on."""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class RequestEvent:
    id: str
    ts: str
    source_ip: str
    model: str
    backend: str
    prompt_tokens: int | None
    generated_tokens: int | None
    duration_ms: int | None
    tokens_per_sec: float | None
    ok: bool
    http_status: int | None
    prompt_text: str | None = None
    response_text: str | None = None


class History:
    def __init__(self, path: Path, limit: int, days: int, capture: bool) -> None:
        self.path = path
        self.limit = limit
        self.days = days
        self.capture = capture
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY,
                ts TEXT NOT NULL,
                source_ip TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL DEFAULT '',
                backend TEXT NOT NULL DEFAULT '',
                prompt_tokens INTEGER,
                generated_tokens INTEGER,
                duration_ms INTEGER,
                tokens_per_sec REAL,
                ok INTEGER NOT NULL,
                http_status INTEGER,
                prompt_text TEXT,
                response_text TEXT
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS requests_ts ON requests (ts)")
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def record(self, event: RequestEvent) -> None:
        prompt = event.prompt_text if self.capture else None
        response = event.response_text if self.capture else None
        if prompt is not None:
            prompt = prompt[:65536]
        if response is not None:
            response = response[:65536]
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO requests (
                    id, ts, source_ip, model, backend, prompt_tokens, generated_tokens,
                    duration_ms, tokens_per_sec, ok, http_status, prompt_text, response_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.ts,
                    event.source_ip,
                    event.model,
                    event.backend,
                    event.prompt_tokens,
                    event.generated_tokens,
                    event.duration_ms,
                    event.tokens_per_sec,
                    1 if event.ok else 0,
                    event.http_status,
                    prompt,
                    response,
                ),
            )
            self._prune_locked()
            self._conn.commit()

    def _prune_locked(self) -> None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._conn.execute("DELETE FROM requests WHERE ts < ?", (cutoff,))
        self._conn.execute(
            """
            DELETE FROM requests WHERE id NOT IN (
                SELECT id FROM requests ORDER BY ts DESC LIMIT ?
            )
            """,
            (self.limit,),
        )

    def list_recent(self, limit: int = 50) -> list[dict]:
        limit = max(1, min(limit, 100))
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, ts, source_ip, model, backend, prompt_tokens, generated_tokens,
                       duration_ms, tokens_per_sec, ok, http_status
                FROM requests ORDER BY ts DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_public_row(row) for row in rows]

    def summary(self) -> dict:
        with self._lock:
            total, prompt_tokens, generated_tokens = self._conn.execute(
                """
                SELECT COUNT(*),
                       COALESCE(SUM(prompt_tokens), 0),
                       COALESCE(SUM(generated_tokens), 0)
                FROM requests
                """
            ).fetchone()
            last = self._conn.execute(
                """
                SELECT ts, prompt_tokens, generated_tokens, ok
                FROM requests ORDER BY ts DESC LIMIT 1
                """
            ).fetchone()
        last_payload = None
        if last is not None:
            last_payload = {
                "timestamp": last["ts"],
                "promptTokens": last["prompt_tokens"],
                "generatedTokens": last["generated_tokens"],
                "ok": bool(last["ok"]),
            }
        return {
            "total": int(total),
            "promptTokens": int(prompt_tokens),
            "generatedTokens": int(generated_tokens),
            "last": last_payload,
        }


def _public_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "timestamp": row["ts"],
        "sourceIp": row["source_ip"],
        "model": row["model"],
        "backend": row["backend"],
        "promptTokens": row["prompt_tokens"],
        "generatedTokens": row["generated_tokens"],
        "durationMs": row["duration_ms"],
        "tokensPerSec": row["tokens_per_sec"],
        "ok": bool(row["ok"]),
        "httpStatus": row["http_status"],
    }
