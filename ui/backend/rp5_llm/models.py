"""Model manifest. Entries without a sha256 cannot be downloaded."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")


def load_models(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    payload = yaml.safe_load(path.read_text()) or {}
    raw = payload.get("models") if isinstance(payload, dict) else None
    if isinstance(raw, dict):
        items = [{"id": key, **value} for key, value in raw.items() if isinstance(value, dict)]
    elif isinstance(raw, list):
        items = [item for item in raw if isinstance(item, dict)]
    else:
        return []
    models = []
    for item in items:
        model_id = str(item.get("id") or "")
        if not _ID.match(model_id):
            continue
        sha = str(item.get("sha256") or "").strip().lower()
        if sha and not _SHA.match(sha):
            sha = ""
        models.append(
            {
                "id": model_id,
                "name": str(item.get("name") or model_id),
                "profile": str(item.get("profile") or "custom"),
                "repo": str(item.get("repo") or ""),
                "file": _safe_file(str(item.get("file") or "")),
                "context": int(item.get("context") or 0),
                "ramGb": item.get("ram_gb"),
                "diskGb": item.get("disk_gb"),
                "sha256": sha,
                "note": str(item.get("note") or ""),
            }
        )
    return models


def find_model(models: list[dict], model_id: str) -> dict | None:
    for model in models:
        if model["id"] == model_id:
            return model
    return None


def _safe_file(name: str) -> str:
    if not name or "/" in name or name.startswith("."):
        return ""
    return name
